"""
Manage configuration files (.env) in configs/ directory.
"""
import os
from dotenv import dotenv_values

CONFIG_DIR = "configs"
ACTIVE_FILE = ".osenv_active"


def get_config_path(name: str) -> str:
    """Return filesystem path for a given configuration name."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    return os.path.join(CONFIG_DIR, f"{name}.env")


def set_active_config(name: str):
    """Store the active configuration name in the project root."""
    with open(ACTIVE_FILE, 'w') as f:
        f.write(name.strip())


def get_active_config_name() -> str:
    """Read the active configuration name; if none, return 'default'."""
    if os.path.exists(ACTIVE_FILE):
        with open(ACTIVE_FILE, 'r') as f:
            name = f.read().strip()
            if name:
                return name
    return "default"


def load_active_config() -> dict:
    """Load variables from the active .env file."""
    name = get_active_config_name()
    path = get_config_path(name)
    if os.path.exists(path):
        return dotenv_values(path)
    return {}
