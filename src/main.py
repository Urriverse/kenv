import argparse

from core import find_project_root
from config import load_profiles, read_current_profile, write_current_profile, generate_cargo_toml
from build import build
from qemu import run_qemu
from ui import interactive_select
from utils import error, check_tools, run_cmd


def main():
    parser = argparse.ArgumentParser(description="Kernel build tool (kenv)")
    sub = parser.add_subparsers(dest="command", required=True)

    config_parser = sub.add_parser("config", help="Select profile and activate environment")
    config_parser.add_argument("profile", nargs="?", default=None, help="Profile name (e.g., dev, release)")

    sub.add_parser("build", help="Build kernel and ISO")

    sub.add_parser("run", help="Build and run in QEMU")

    sub.add_parser("clean", help="Clean build artifacts")

    try:
        root = find_project_root()
    except RuntimeError as e:
        error(str(e))

    args = parser.parse_args()

    required_tools = {
        "cargo": "Rust build tool",
        "xorriso": "ISO creation",
        "qemu-system-x86_64": "QEMU x86_64 emulator",
        "make": "build Limine",
    }
    check_tools(required_tools)

    if args.command == "config":
        profiles = load_profiles(root)
        if args.profile is None:
            chosen = interactive_select(profiles)
        else:
            if args.profile not in profiles:
                error(f"Profile '{args.profile}' does not exist.")
            chosen = args.profile

        write_current_profile(root, chosen)
        generate_cargo_toml(root, chosen)

    elif args.command == "build":
        build(root)

    elif args.command == "run":
        build(root)
        profile = read_current_profile(root)
        if profile is None:
            error("No profile selected. Run 'kenv config' first.")
        run_qemu(root, profile)

    elif args.command == "clean":
        run_cmd(["cargo", "clean"], cwd=root)

        import shutil
        from .core import get_target_dir
        limine_path = get_target_dir(root) / "limine"
        if limine_path.exists():
            shutil.rmtree(limine_path)

        profile_file = get_target_dir(root) / "current_profile"
        if profile_file.exists():
            profile_file.unlink()
        print("Cleaned.")


if __name__ == "__main__":
    main()
