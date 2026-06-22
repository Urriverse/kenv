from pathlib import Path


def find_project_root() -> Path:
    cwd = Path.cwd()
    
    for parent in [cwd] + list(cwd.parents):
        if (parent / "src" / "main.rs").exists():
            return parent
    raise RuntimeError("Not in a kernel project (no src/main.rs found)")


def get_profiles_dir(root: Path) -> Path:
    return root / "etc" / "profiles"


def get_cargo_in(root: Path) -> Path:
    return root / "etc" / "Cargo.in"


def get_limine_conf(root: Path) -> Path:
    return root / "etc" / "limine.conf"


def get_linker_ld(root: Path) -> Path:
    return root / "etc" / "linker.ld"


def get_target_dir(root: Path) -> Path:
    return root / "target"


def get_current_profile_file(root: Path) -> Path:
    return get_target_dir(root) / "current_profile"
