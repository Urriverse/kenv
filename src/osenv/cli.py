"""
Command-line interface using argparse with subparsers.
"""
import argparse

from .commands import build, config, fetch, run, test
from .commands import clean


def main():
    parser = argparse.ArgumentParser(
        "osenv",
        description="OS building and running suite.",
        prefix_chars="-/",
        fromfile_prefix_chars="@",
    )
    subparsers = parser.add_subparsers(dest="VERB", required=True, help="What to do.")

    # --- config ---
    p_config = subparsers.add_parser(
        "config", aliases=["c"],
        help="Configure build parameters."
    )
    p_config.add_argument(
        "name",
        help="Configuration name (creates or switches to it)."
    )
    p_config.add_argument(
        "--set", "-s", action="append", nargs=2, metavar=("KEY", "VALUE"),
        help="Set variable in the config (can be used multiple times)."
    )
    p_config.set_defaults(func=config.main)

    # --- fetch ---
    p_fetch = subparsers.add_parser(
        "fetch", aliases=["f"],
        help="Fetch all components."
    )
    p_fetch.add_argument(
        "--no-git", "-G", action="store_true",
        help="Skip fetching Git-based components."
    )
    p_fetch.add_argument(
        "--component", "-c", action="append",
        help="Fetch only specific component (by name)."
    )
    p_fetch.set_defaults(func=fetch.main)

    # --- build ---
    p_build = subparsers.add_parser(
        "build", aliases=["b"],
        help="Build the OS image."
    )
    p_build.add_argument(
        "--clean", action="store_true",
        help="Clean before build."
    )
    p_build.set_defaults(func=build.main)

    # --- test ---
    p_test = subparsers.add_parser(
        "test", aliases=["t"],
        help="Run tests for components."
    )
    p_test.add_argument(
        "--component", "-c", action="append",
        help="Test only specific component."
    )
    p_test.set_defaults(func=test.main)

    # --- run ---
    p_run = subparsers.add_parser(
        "run", aliases=["r"],
        help="Run the latest built image in QEMU."
    )
    p_run.add_argument(
        "--image", "-i",
        help="Path to image file (default: latest built)."
    )
    p_run.add_argument(
        "--qemu-args", "-a",
        help="Extra arguments for QEMU (will be appended)."
    )
    p_run.set_defaults(func=run.main)

    # --- clean ---
    p_clean = subparsers.add_parser(
        "clean",
        help="Clean build artifacts."
    )
    p_clean.add_argument(
        "--all", "-a", action="store_true",
        help="Also remove cached sources (.cache/)."
    )
    p_clean.set_defaults(func=clean.main)

    args = parser.parse_args()
    # Each handler receives the Namespace object
    args.func(args)
