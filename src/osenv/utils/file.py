"""
File and directory helpers.
"""
import os
import shutil
import hashlib


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def copy_with_override(src: str, dst: str, override: bool = True):
    """Copy file, optionally overwriting."""
    if os.path.exists(dst) and not override:
        return
    shutil.copy2(src, dst)


def compute_dir_hash(directory: str) -> str:
    """
    Compute SHA1 hash of all files in directory recursively.
    If directory is a file, hash that file only.
    """
    hasher = hashlib.sha1()
    if not os.path.exists(directory):
        return ""
    if os.path.isfile(directory):
        with open(directory, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                hasher.update(chunk)
        return hasher.hexdigest()

    for root, _, files in sorted(os.walk(directory)):
        for f in sorted(files):
            path = os.path.join(root, f)
            with open(path, 'rb') as file:
                for chunk in iter(lambda: file.read(65536), b''):
                    hasher.update(chunk)
    return hasher.hexdigest()
