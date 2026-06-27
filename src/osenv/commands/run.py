"""
Command: run – launch the OS image in QEMU.
"""
import os
import subprocess
from ..core.confenv import load_active_config
from ..core.qemu import build_qemu_command, find_latest_image
from ..core.hooks import run_hooks
from ..utils.log import *


def main(args):
    config_env = load_active_config()
    image_path = args.image or find_latest_image()
    if not image_path or not os.path.exists(image_path):
        f("No image found. Build one first with 'osenv build'.")

    # Run global pre-run hooks
    run_hooks('pre_run', config_env)

    qemu_cmd = build_qemu_command(image_path, config_env, extra_args=args.qemu_args)
    i("Running", "QEMU")
    subprocess.run(qemu_cmd, check=True)

    # Post-run hooks
    run_hooks('post_run', config_env)
