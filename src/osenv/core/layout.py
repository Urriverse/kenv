"""
Layout copying with conflict resolution (layout files override generated ones).
"""
import os
import shutil


def copy_layout(src_dir: str, dst_dir: str):
    """
    Recursively copy contents from src_dir to dst_dir.
    """
    if not os.path.isdir(src_dir):
        return
    os.makedirs(dst_dir, exist_ok=True)
    for root, _, files in os.walk(src_dir):
        rel_path = os.path.relpath(root, src_dir)
        target_root = os.path.join(dst_dir, rel_path)
        os.makedirs(target_root, exist_ok=True)
        for f in files:
            src_file = os.path.join(root, f)
            dst_file = os.path.join(target_root, f)
            shutil.copy2(src_file, dst_file)
