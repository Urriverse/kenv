"""
Main build orchestrator with incremental build support and ARTEFACT_PATH export.
"""
import os
import shutil
import tarfile
import json
import glob

from .component import Component, load_all_components
from .layout import copy_layout
from .confenv import load_active_config, get_active_config_name
from .hooks import run_hooks
from ..utils.git import clone_or_update
from ..utils.fetch import download_and_extract
from ..utils.file import compute_dir_hash
from ..utils.sp import run_command
from ..utils.log import *


CACHE_DIR = ".cache"
BUILD_DIR = "build"
STAGING_IMAGE = os.path.join(BUILD_DIR, "staging", "image")
STAGING_INITRAMFS = os.path.join(BUILD_DIR, "staging", "initramfs")
INITRAMFS_TAR = os.path.join(BUILD_DIR, "initramfs.tar")
FINAL_IMAGE = os.path.join(BUILD_DIR, "osenv.iso")
STATE_FILE = os.path.join(BUILD_DIR, ".build_state.json")


def fetch_components(components: list[Component], skip_git: bool = False):
    """Fetch sources for all components."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    config_env = load_active_config()

    for comp in components:
        run_hooks('pre_fetch', config_env, component=comp)
        target_dir = os.path.join(CACHE_DIR, comp.name)

        if comp.source == "git":
            if skip_git:
                n(f"Skipping git fetch for {comp.name}")
                continue
            url = comp.get_git_url()
            if not url:
                w(f"{comp.name} missing git.url")
                continue
            filter_mode = comp.get_git_filter()
            clone_or_update(url, target_dir, filter_mode)
            i("Fetched", comp.name)

        elif comp.source == "fetch":
            url = comp.get_fetch_url(config_env)
            if not url:
                w(f"{comp.name} missing fetch.url")
                continue
            download_and_extract(url, target_dir, config_env)
            i("Fetched", comp.name)

        else:
            w(f"{comp.name} has unknown source '{comp.source}'")

        run_hooks('post_fetch', config_env, component=comp)


def get_component_hash(comp: Component) -> str | None:
    """
    Compute a hash representing the current source state of the component.
    For git repos, use HEAD commit hash; for others, hash all files in cache.
    """
    source_path = os.path.join(CACHE_DIR, comp.name)
    if not os.path.isdir(source_path):
        return None
    # If it's a git repo, get HEAD commit hash
    git_dir = os.path.join(source_path, '.git')
    if os.path.exists(git_dir):
        try:
            from git import Repo
            repo = Repo(source_path)
            return repo.head.commit.hexsha
        except Exception:
            # fallback to file hash
            pass
    # Fallback: hash all files
    return compute_dir_hash(source_path)


def load_build_state() -> dict:
    """Load the build state JSON if exists."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_build_state(state: dict):
    """Save build state JSON."""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def build_os(clean: bool, config_env: dict[str, str]):
    """
    Full OS build with incremental support.
    If clean=True, remove build directory and state before building.
    """
    if clean:
        if os.path.exists(BUILD_DIR):
            shutil.rmtree(BUILD_DIR)
            ii("Cleaned build directory")

    os.makedirs(BUILD_DIR, exist_ok=True)

    # Load previous build state
    state = load_build_state()
    components = load_all_components()

    # Ensure all components are fetched (skip if already cached)
    fetch_components(components, skip_git=False)

    # Determine which components need rebuilding
    components_to_build = []
    for comp in components:
        current_hash = get_component_hash(comp)
        old_hash = state.get('components', {}).get(comp.name)
        if current_hash is None:
            components_to_build.append(comp)
        elif old_hash is None or old_hash != current_hash:
            components_to_build.append(comp)

    # dictionary to hold artefact paths for each component (if any)
    artifact_paths = {}

    # Build each component that changed
    for comp in components_to_build:
        run_hooks('pre_build', config_env, component=comp)
        if comp.has_command('build'):
            cmd = comp.get_command('build')
            # Determine if we need to use ARTEFACT_PATH (only for components without subtype)
            use_artefact_path = (comp.subtype is None)
            artefact_file = None
            if use_artefact_path:
                artefact_dir = os.path.join(BUILD_DIR, "artefacts")
                os.makedirs(artefact_dir, exist_ok=True)
                comp_hash = get_component_hash(comp) or "unknown"
                artefact_file = os.path.join(artefact_dir, f"{comp.name}_{comp_hash[:8]}.path")
                if os.path.exists(artefact_file):
                    os.remove(artefact_file)
                with open(artefact_file, "wt") as f:
                    f.write("")

            # Build environment
            build_env = os.environ.copy()
            build_env.update(config_env)
            build_env["ARTEFACT_PATH"] = os.path.abspath(artefact_file)
            build_env["BUILD_PATH"] = os.path.abspath(BUILD_DIR)

            # Run the build command
            run_command(cmd, cwd=os.path.join(CACHE_DIR, comp.name), env=build_env)

            # If we exported ARTEFACT_PATH, read the file to get the actual artefact path
            if use_artefact_path and artefact_file and os.path.exists(artefact_file):
                with open(artefact_file, 'r') as f:
                    artefact_path = f.read().strip()
                if artefact_path and os.path.exists(artefact_path):
                    artifact_paths[comp.name] = artefact_path
                else:
                    w(f"{comp.name} wrote invalid artefact path '{artefact_path}'")
            elif use_artefact_path:
                w(f"{comp.name} did not create artefact file at {artefact_file}")
        elif comp.subtype is None:
            w(f"{comp.name} has no 'build' command.")
        run_hooks('post_build', config_env, component=comp)
        # Update hash in state after successful build
        new_hash = get_component_hash(comp)
        if new_hash:
            state.setdefault('components', {})[comp.name] = new_hash

    # For components that were not rebuilt, try to retrieve artefact paths from state or from existing files
    for comp in components:
        if comp.subtype is None:  # only for non-subtyped components
            if comp.name in artifact_paths:
                continue
            # Try from state
            stored_path = state.get('artefact_paths', {}).get(comp.name)
            if stored_path and os.path.exists(stored_path):
                artifact_paths[comp.name] = stored_path
            else:
                # Try to find artefact file in build/artefacts/
                artefact_dir = os.path.join(BUILD_DIR, "artefacts")
                pattern = os.path.join(artefact_dir, f"{comp.name}_*.path")
                files = glob.glob(pattern)
                if files:
                    files.sort(key=os.path.getmtime, reverse=True)
                    with open(files[0], 'r') as f:
                        artefact_path = f.read().strip()
                    if artefact_path and os.path.exists(artefact_path):
                        artifact_paths[comp.name] = artefact_path

    # Save artefact paths to state
    state['artefact_paths'] = artifact_paths

    # Check if layout or config changed
    layout_hash = compute_dir_hash("layout") if os.path.isdir("layout") else ""
    config_name = get_active_config_name()
    config_path = os.path.join("configs", f"{config_name}.env")
    config_hash = compute_dir_hash(config_path) if os.path.exists(config_path) else ""

    global_triggers_changed = (
        state.get('layout_hash') != layout_hash or
        state.get('config_hash') != config_hash
    )

    need_image_rebuild = (
        bool(components_to_build) or
        global_triggers_changed or
        not os.path.exists(FINAL_IMAGE)
    )

    if need_image_rebuild:
        assemble_image(components, artifact_paths=artifact_paths)
        state['layout_hash'] = layout_hash
        state['config_hash'] = config_hash

    save_build_state(state)
    i("Build complete", FINAL_IMAGE)


def assemble_image(components: list[Component], artifact_paths: dict[str, str]):
    """
    Assemble the final image from staged files.
    artifact_paths: dict mapping component name to artefact path.
    """
    staging_image = STAGING_IMAGE
    staging_initramfs = STAGING_INITRAMFS

    # Remove old staging dirs
    if os.path.exists(staging_image):
        shutil.rmtree(staging_image)
    if os.path.exists(staging_initramfs):
        shutil.rmtree(staging_initramfs)
    os.makedirs(staging_image, exist_ok=True)
    os.makedirs(staging_initramfs, exist_ok=True)

    # Copy layout files (these have highest priority)
    copy_layout("layout/image", staging_image)
    copy_layout("layout/initramfs", staging_initramfs)

    # Deploy artifacts from components, now using artifact_paths
    deploy_artifacts(components, staging_image, staging_initramfs, artifact_paths)

    # Create initramfs.tar (uncompressed)
    create_initramfs_tar(staging_initramfs, INITRAMFS_TAR)

    # Copy initramfs into image/boot
    os.makedirs(os.path.join(staging_image, "boot"), exist_ok=True)
    shutil.copy(INITRAMFS_TAR, os.path.join(staging_image, "boot", "initramfs.tar"))

    # Create bootable image (ISO)
    create_bootable_image(staging_image, FINAL_IMAGE, components)


def deploy_artifacts(components: list[Component], image_dir: str, initramfs_dir: str, artifact_paths: dict[str, str]):
    """
    Copy component build outputs to the staging directories.
    For components with subtype (e.g., bootloader/limine), we use known paths.
    For others, we use artifact_paths provided by the build commands.
    """
    for comp in components:
        if comp.subtype is not None:
            # Handle special subtypes (like limine)
            if comp.kind == "bootloader" and comp.subtype == "limine":
                # Handled separately below
                pass
            else:
                w(f"unknown subtype '{comp.subtype}' for component {comp.name}")
        else:
            # Component without subtype – use artifact path from build
            artefact = artifact_paths.get(comp.name)
            if not artefact or not os.path.exists(artefact):
                w(f"no artefact found for {comp.name}")
                continue

            if comp.kind == "kernel":
                dest = os.path.join(image_dir, "boot", "kernel")
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy2(artefact, dest)
                i("Deployed", comp.name)
            elif comp.kind == "kernel-module":
                modules_dest = os.path.join(initramfs_dir, "modules")
                os.makedirs(modules_dest, exist_ok=True)
                shutil.copy2(artefact, os.path.join(modules_dest, os.path.basename(artefact)))
                i("Deployed", comp.name)
            else:
                w(f"unknown kind '{comp.kind}' for component {comp.name}, artefact {artefact} not deployed")

    # Handle limine (subtype) separately
    limine_comp = next((c for c in components if c.kind == "bootloader" and c.subtype == "limine"), None)
    if limine_comp:
        limine_dir = os.path.join(CACHE_DIR, limine_comp.name, "limine-binary")
        prepare_cmd = limine_comp.get_prepare_command()
        if prepare_cmd:
            run_command(prepare_cmd, cwd=limine_dir)
        for f in limine_comp.get_cpy_root():
            src = os.path.join(limine_dir, f)
            if os.path.exists(src):
                shutil.copy2(src, image_dir)
        efi_boot = limine_comp.get_efi_boot()
        if efi_boot:
            src = os.path.join(limine_dir, efi_boot)
            if os.path.exists(src):
                efi_dir = os.path.join(image_dir, "EFI", "BOOT")
                os.makedirs(efi_dir, exist_ok=True)
                shutil.copy2(src, os.path.join(efi_dir, os.path.basename(efi_boot)))
        i("Deployed", limine_comp.name)


def create_initramfs_tar(source_dir: str, output_path: str):
    """Create uncompressed tar archive (ustar format)."""
    with tarfile.open(output_path, 'w', format=tarfile.USTAR_FORMAT) as tar:
        for root, _, files in os.walk(source_dir):
            for f in files:
                full_path = os.path.join(root, f)
                arcname = os.path.relpath(full_path, source_dir)
                tar.add(full_path, arcname=arcname)


def create_bootable_image(image_dir: str, output_path: str,
                          components: list[Component]):
    """
    Create a bootable ISO using xorriso.
    For Limine, we will also run bios-install after the ISO is created.
    """
    # Use xorriso to create hybrid ISO
    cmd = [
        "xorriso", "-as", "mkisofs",
        "-R", "-r", "-J", "-quiet",
        "-b", "limine-bios-cd.bin",
        "-no-emul-boot", "-boot-load-size",
        "4", "-boot-info-table",
        "-hfsplus", "-apm-block-size", "2048",
        "--efi-boot", "limine-uefi-cd.bin",
        "-efi-boot-part", "--efi-boot-image",
        "-o", output_path, image_dir
    ]
    run_command(cmd, quiet=1)

    limine_comp = next((c for c in components if c.kind == "bootloader" and c.subtype == "limine"), None)
    if limine_comp:
        bios_install_cmd = limine_comp.get_bios_install()
        if bios_install_cmd:
            full_cmd = bios_install_cmd + [output_path]
            run_command(full_cmd, quiet=1)


def test_components(components: list[Component]):
    """Run test commands for selected components."""
    config_env = load_active_config()
    for comp in components:
        if comp.has_command('test'):
            run_hooks('pre_test', config_env, component=comp)
            cmd = comp.get_command('test')
            run_command(cmd, cwd=os.path.join(CACHE_DIR, comp.name))
            run_hooks('post_test', config_env, component=comp)
