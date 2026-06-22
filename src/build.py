import shutil
import subprocess
import tarfile
from pathlib import Path
from core import get_target_dir, get_limine_conf
from limine import prepare_limine, limine_binary, limine_version_file
from config import read_current_profile, generate_cargo_toml, load_profiles
from utils import status, finished, error, run_cmd
import os


KERNEL_NAME = "kernel"


def build_kernel(root: Path, profile: dict):
    cargo_opts = profile["cargo"]
    env = dict(os.environ)
    env.update(profile.get("env", {}))
    
    cmd = [
        "cargo", "build",
        "--profile", cargo_opts["profile"],
    ]
    features = cargo_opts.get("features")
    if features:
        cmd.extend(["--features", ",".join(features)])

    run_cmd(cmd, env=env)


def create_initramfs(root: Path, iso_root: Path) -> None:
    """Pack image/ directory into a tar archive inside the ISO root."""
    image_dir = root / "image"
    if not image_dir.is_dir():
        return

    tar_path = iso_root / "boot" / "initramfs.tar"
    tar_path.parent.mkdir(parents=True, exist_ok=True)

    with tarfile.open(tar_path, "w") as tar:
        for item in image_dir.rglob("*"):
            if item.is_file():
                arcname = item.relative_to(image_dir)
                tar.add(item, arcname=arcname)

    status("Created", "initramfs.tar from image/")


def add_module_to_limine_conf(original_conf: Path, iso_conf: Path, root: Path) -> None:
    """
    Copy limine.conf to ISO, adding MODULE_PATH for initramfs.tar
    only if the image/ directory exists.
    """
    # If no image directory, just copy the original
    if not (root / "image").is_dir():
        shutil.copy2(original_conf, iso_conf)
        return

    content = original_conf.read_text().splitlines()
    module_line = "MODULE_PATH=boot:///boot/initramfs.tar"

    # Avoid duplication if the line already exists
    if any("MODULE_PATH" in line and "initramfs.tar" in line for line in content):
        shutil.copy2(original_conf, iso_conf)
        return

    # Insert after the first KERNEL_PATH line (fallback: append at end)
    insert_idx = -1
    for i, line in enumerate(content):
        if "KERNEL_PATH" in line:
            insert_idx = i + 1
            break
    if insert_idx == -1:
        insert_idx = len(content)

    content.insert(insert_idx, module_line)
    iso_conf.write_text("\n".join(content))


def setup_iso(root: Path, profile_name: str):
    target_dir = get_target_dir(root)
    iso_root = target_dir / "x86_64-unknown-none" / profile_name / "iso-root"
    
    if profile_name == "dev":
        binary_dir = target_dir / "x86_64-unknown-none" / "debug"
    else:
        binary_dir = target_dir / "x86_64-unknown-none" / profile_name
    kernel_bin = binary_dir / KERNEL_NAME

    if not kernel_bin.is_file():
        error(f"Kernel binary not found: {kernel_bin}")

    status("Preparing", "ISO filesystem")
    boot_dir = iso_root / "boot" / "limine"
    efi_dir = iso_root / "EFI" / "BOOT"
    boot_dir.mkdir(parents=True, exist_ok=True)
    efi_dir.mkdir(parents=True, exist_ok=True)

    # Copy Limine binaries
    for fname in ["limine-bios.sys", "limine-bios-cd.bin", "limine-uefi-cd.bin"]:
        src = limine_binary(root, fname)
        if not src.is_file():
            error(f"Missing Limine file: {src}")
        shutil.copy2(src, boot_dir)

    efi_src = limine_binary(root, "BOOTX64.EFI")
    if not efi_src.is_file():
        error(f"Missing Limine EFI file: {efi_src}")
    shutil.copy2(efi_src, efi_dir)

    # Copy kernel
    shutil.copy2(kernel_bin, iso_root / "boot" / KERNEL_NAME)

    # Create initramfs from image/ if it exists
    create_initramfs(root, iso_root)

    # Copy and possibly augment limine.conf
    iso_conf_path = boot_dir / "limine.conf"
    add_module_to_limine_conf(get_limine_conf(root), iso_conf_path, root)

    finished("ISO filesystem")


def build_iso(root: Path, profile_name: str):
    target_dir = get_target_dir(root)
    iso_root = target_dir / "x86_64-unknown-none" / profile_name / "iso-root"
    iso_name = target_dir / "x86_64-unknown-none" / profile_name / "image.iso"

    status("Compiling", "ISO image")
    run_cmd([
        "xorriso", "-as", "mkisofs",
        "-R", "-r", "-J", "-quiet",
        "-b", "boot/limine/limine-bios-cd.bin",
        "-no-emul-boot", "-boot-load-size", "4", "-boot-info-table",
        "-hfsplus", "-apm-block-size", "2048",
        "--efi-boot", "boot/limine/limine-uefi-cd.bin",
        "-efi-boot-part", "--efi-boot-image",
        str(iso_root),
        "-o", str(iso_name),
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    run_cmd([str(limine_binary(root, "limine")), "bios-install", str(iso_name)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    finished("ISO image")


def iso_needs_rebuild(root: Path, profile_name: str) -> bool:
    target_dir = get_target_dir(root)
    iso = target_dir / "x86_64-unknown-none" / profile_name / "image.iso"
    if not iso.exists():
        return True
    
    binary_dir = target_dir / "x86_64-unknown-none" / ("debug" if profile_name == "dev" else profile_name)
    kernel_bin = binary_dir / KERNEL_NAME
    if not kernel_bin.exists():
        return True
    
    iso_mtime = iso.stat().st_mtime
    for src in [
        kernel_bin,
        get_limine_conf(root),
        limine_binary(root, "limine-bios.sys"),
        limine_binary(root, "limine-bios-cd.bin"),
        limine_binary(root, "limine-uefi-cd.bin"),
        limine_binary(root, "BOOTX64.EFI"),
        limine_binary(root, "limine"),
        limine_version_file(root),
    ]:
        if not src.exists() or src.stat().st_mtime > iso_mtime:
            return True

    # Check image/ directory and initramfs.tar
    image_dir = root / "image"
    if image_dir.is_dir():
        initramfs_tar = target_dir / "x86_64-unknown-none" / profile_name / "iso-root" / "boot" / "initramfs.tar"
        if not initramfs_tar.exists():
            return True
        # Get the newest file modification time in image/
        latest = 0
        for p in image_dir.rglob("*"):
            if p.is_file() and p.stat().st_mtime > latest:
                latest = p.stat().st_mtime
        if latest > initramfs_tar.stat().st_mtime:
            return True

    return False


def build(root: Path):
    profile_name = read_current_profile(root)
    if profile_name is None:
        error("No profile selected. Run 'kenv config' first.")

    profiles = load_profiles(root)
    if profile_name not in profiles:
        error(f"Profile '{profile_name}' does not exist.")

    generate_cargo_toml(root, profile_name)

    prepare_limine(root)

    build_kernel(root, profiles[profile_name])

    if iso_needs_rebuild(root, profile_name):
        setup_iso(root, profile_name)
        build_iso(root, profile_name)
    else:
        finished("ISO image (up-to-date)")
