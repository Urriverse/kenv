"""
Command: clean – remove build artifacts (and optionally source cache).
"""
import os
import shutil
from ..core.builder import BUILD_DIR, CACHE_DIR, INITRAMFS_TAR, STATE_FILE
from ..utils.log import *


def main(args):
    # Remove build directory
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    # Remove initramfs tar if exists
    if os.path.exists(INITRAMFS_TAR):
        os.remove(INITRAMFS_TAR)
    # Remove state file
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
    if args.all:
        if os.path.exists(CACHE_DIR):
            shutil.rmtree(CACHE_DIR)
    i("Clean", "completed")
