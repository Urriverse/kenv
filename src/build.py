import shutil
import subprocess
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

    shutil.copy2(get_limine_conf(root), boot_dir / "limine.conf")

    for fname in ["limine-bios.sys", "limine-bios-cd.bin", "limine-uefi-cd.bin"]:
        src = limine_binary(root, fname)
        if not src.is_file():
            error(f"Missing Limine file: {src}")
        shutil.copy2(src, boot_dir)

    efi_src = limine_binary(root, "BOOTX64.EFI")
    if not efi_src.is_file():
        error(f"Missing Limine EFI file: {efi_src}")
    shutil.copy2(efi_src, efi_dir)

    shutil.copy2(kernel_bin, iso_root / "boot" / KERNEL_NAME)

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
