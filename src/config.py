import tomllib
from pathlib import Path
from core import get_profiles_dir, get_cargo_in, get_current_profile_file
from utils import error


def load_profiles(root: Path) -> dict[str, dict]:
    profiles_dir = get_profiles_dir(root)
    if not profiles_dir.is_dir():
        error(f"Profiles directory not found: {profiles_dir}")

    profiles = {}
    for entry in profiles_dir.iterdir():
        if entry.suffix != ".toml":
            continue
        name = entry.stem
        with entry.open("rb") as f:
            profiles[name] = tomllib.load(f)
    if not profiles:
        error("No profile files found in " + str(profiles_dir))
    return profiles


def read_current_profile(root: Path) -> str | None:
    f = get_current_profile_file(root)
    if f.exists():
        return f.read_text().strip()
    return None


def write_current_profile(root: Path, profile: str):
    f = get_current_profile_file(root)
    f.parent.mkdir(exist_ok=True)
    f.write_text(profile + "\n")


def generate_cargo_toml(root: Path, profile_name: str, kernel_name: str = "kernel"):
    template_path = get_cargo_in(root)
    if not template_path.is_file():
        error(f"Template file missing: {template_path}")

    template = template_path.read_text()
    rendered = template.replace("{KERNEL_NAME}", kernel_name)
    rendered = rendered.replace("{profile_name}", profile_name)
    rendered = rendered.replace("{{", "{").replace("}}", "}")

    target = root / "Cargo.toml"
    target.write_text(rendered)
