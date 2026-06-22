import shutil
import subprocess
import sys


GREEN = "\033[32;1m"
BLUE = "\033[34;1m"
YELLOW = "\033[33;1m"
RED = "\033[31;1m"
BOLD = "\033[1m"
NC = "\033[0m"
CLEAR = "\033[H\033[2J"
INVERSE = "\033[7m"


def status(action: str, target: str):
    print(f"   {GREEN}{action}{NC} {target}")


def finished(target: str):
    print(f"    {GREEN}Finished{NC} {target}")


def warn(msg: str):
    print(f"{YELLOW}{BOLD}warning{NC}{BOLD}:{NC} {msg}")


def error(msg: str, exit_code: int = 1):
    print(f"{RED}{BOLD}error{NC}{BOLD}:{NC} {msg}", file=sys.stderr)
    sys.exit(exit_code)


def run_cmd(cmd: list[str], **kwargs):
    try:
        subprocess.run(cmd, check=True, **kwargs)
    except subprocess.CalledProcessError as e:
        error(f"Command failed with exit code {e.returncode}: {' '.join(cmd)}")


def check_tools(required: dict[str, str]):
    missing = []
    
    for cmd, desc in required.items():
        if shutil.which(cmd) is None:
            missing.append(f"{cmd} ({desc})")
    if missing:
        error("Missing required tools: " + ", ".join(missing) + ".\nPlease install them and try again.")


def get_terminal_width(default: int = 80) -> int:
    try:
        import shutil
        return shutil.get_terminal_size((default, 20)).columns
    except:
        return default
