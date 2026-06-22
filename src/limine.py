import shutil
import tarfile
import urllib.request
from pathlib import Path
from core import get_target_dir
from utils import status, finished, error, run_cmd


LIMINE_VERSION = "12.3.2"
LIMINE_URL = f"https://github.com/limine-bootloader/limine/releases/download/v{LIMINE_VERSION}/limine-binary.tar.gz"


def limine_dir(root: Path) -> Path:
    return get_target_dir(root) / "limine" / "limine-binary"


def limine_version_file(root: Path) -> Path:
    return get_target_dir(root) / "limine" / ".version"


def limine_binary(root: Path, name: str) -> Path:
    return limine_dir(root) / name


def prepare_limine(root: Path):
    version_file = limine_version_file(root)
    if limine_dir(root).is_dir() and version_file.exists():
        if version_file.read_text().strip() == LIMINE_VERSION:
            return

    limine_parent = get_target_dir(root) / "limine"
    if limine_parent.exists():
        shutil.rmtree(limine_parent)

    status("Fetching", f"limine v{LIMINE_VERSION}")
    archive = get_target_dir(root) / "limine.tgz"
    get_target_dir(root).mkdir(exist_ok=True)

    try:
        with urllib.request.urlopen(LIMINE_URL) as response, open(archive, "wb") as f:
            shutil.copyfileobj(response, f)
    except Exception as e:
        error(f"Failed to download Limine: {e}")

    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(path=limine_parent)

    status("Compiling", "limine")
    run_cmd(
        ["make", "-C", str(limine_dir(root)), "--no-print-directory", "-s"],
        cwd=limine_dir(root),
    )
    version_file.parent.mkdir(parents=True, exist_ok=True)
    version_file.write_text(LIMINE_VERSION + "\n")
    finished(f"limine v{LIMINE_VERSION}")
