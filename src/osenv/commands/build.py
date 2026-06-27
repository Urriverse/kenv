"""
Command: build – assemble the OS image.
"""
from ..core.builder import build_os
from ..core.confenv import load_active_config


def main(args):
    config_env = load_active_config()
    build_os(
        clean=args.clean,
        config_env=config_env,
    )
