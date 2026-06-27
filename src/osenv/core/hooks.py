"""
Hook execution: global and component-specific.
"""
import os
import subprocess
from .component import Component
from ..utils.log import *


def run_hooks(hook_name: str, config_env: dict[str, str],
              component: Component | None = None):
    """
    Run hooks for a given hook name (e.g., 'pre_build').
    Global hooks are read from .osenv.toml in the project root.
    Component hooks are read from component.hooks.
    """
    # Global hooks (from .osenv.toml)
    global_hooks = load_global_hooks()
    for cmd in global_hooks.get(hook_name, []):
        n(f"Running global hook: {cmd}")
        subprocess.run(cmd, shell=True, env=os.environ)

    # Component-specific hooks
    if component:
        for cmd in component.hooks.get(hook_name, []):
            n(f"Running hook for {component.name}: {cmd}")
            subprocess.run(cmd, shell=True, cwd=os.path.join(".cache", component.name),
                           env=os.environ)


def load_global_hooks() -> dict[str, list]:
    """Load global hooks from .osenv.toml if present."""
    import tomllib
    hooks = {}
    if os.path.exists(".osenv.toml"):
        with open(".osenv.toml", "rb") as f:
            data = tomllib.load(f)
            hooks = data.get("hooks", {})
    return hooks
