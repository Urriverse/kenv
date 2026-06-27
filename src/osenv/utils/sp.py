"""
Wrapper for subprocess calls with logging.
"""
import subprocess
from ..utils.log import *


def run_command(cmd: list[str], cwd: str | None = None,
                env: dict[str, str] | None = None,
                check: bool = True, quiet: bool = False):
    """Run a command, print its output, return exit code."""
    try:
        if quiet:
            pargs = { 'stdout': subprocess.DEVNULL, 'stderr': subprocess.DEVNULL }
        else:
            pargs = {}
        result = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            check=check,
            **pargs
        )
        if result.stdout:
            print(result.stdout)
        return result.returncode
    except subprocess.CalledProcessError as e:
        e(f"Command failed with exit {e.returncode}")
        if check:
            raise
        return e.returncode
