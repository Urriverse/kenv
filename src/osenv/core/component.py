"""
Component loading and representation.
"""
import os
import tomllib
from ..utils.file import compute_dir_hash
from ..utils.log import *


class Component:
    """
    Represents a single component (kernel, bootloader, module, etc.)
    """
    def __init__(self, name: str, data: dict[str]):
        self.name = name
        self.data = data
        self.general = data.get('general', {})
        self.type_str = self.general.get('type', '')
        self.kind, self.subtype = self._parse_type(self.type_str)
        self.source = self.general.get('source', '')
        self.commands = data.get('commands', {})
        self.hooks = data.get('hooks', {})
        # Special fields for limine subtype
        self.limine_cfg = data.get('limine', {})

    def _parse_type(self, type_str: str):
        if '/' in type_str:
            kind, subtype = type_str.split('/', 1)
            return kind.strip(), subtype.strip()
        else:
            return type_str.strip(), None
    
    def get_source_hash(self) -> str | None:
        """Compute hash of the source directory (cache)."""
        source_path = os.path.join(".cache", self.name)
        if not os.path.isdir(source_path):
            return None
        # If git repo, use HEAD commit
        if os.path.exists(os.path.join(source_path, '.git')):
            try:
                from git import Repo
                repo = Repo(source_path)
                return repo.head.commit.hexsha
            except Exception:
                pass
        # Fallback to file hash
        return compute_dir_hash(source_path)

    def get_fetch_url(self, config_env: dict[str, str]) -> str | None:
        """Return the URL to fetch (for source='fetch') with env substitution."""
        fetch_data = self.data.get('fetch', {})
        url_template = fetch_data.get('url')
        if not url_template:
            return None
        # Substitute variables from config_env
        try:
            url = url_template.format(**config_env)
        except KeyError as e:
            w(f"missing variable {e} in URL for {self.name}")
            url = url_template
        return url

    def get_git_url(self) -> str | None:
        git_data = self.data.get('git', {})
        return git_data.get('url')

    def get_git_filter(self) -> str:
        git_data = self.data.get('git', {})
        return git_data.get('filter', 'latest-cached')

    def get_defaults(self) -> dict[str, str]:
        """Return defaults from [fetch.defaults] section."""
        fetch_data = self.data.get('fetch', {})
        return fetch_data.get('defaults', {})

    def has_command(self, cmd: str) -> bool:
        return cmd in self.commands

    def get_command(self, cmd: str) -> list[str]:
        return self.commands.get(cmd, [])

    def get_prepare_command(self) -> list[str]:
        """For limine subtype: prepare command."""
        return self.limine_cfg.get('prepare', [])

    def get_cpy_root(self) -> list[str]:
        return self.limine_cfg.get('cpy-root', [])

    def get_efi_boot(self) -> str | None:
        return self.limine_cfg.get('efi-boot')

    def get_bios_install(self) -> list[str]:
        return self.limine_cfg.get('bios-install', [])


def load_all_components(components_dir: str = "components") -> list[Component]:
    """Load all .toml files from components/ directory."""
    components = []
    if not os.path.isdir(components_dir):
        w(f"components directory '{components_dir}' not found.")
        return components

    for file in os.listdir(components_dir):
        if file.endswith('.toml'):
            path = os.path.join(components_dir, file)
            with open(path, 'rb') as f:
                data = tomllib.load(f)
            name = os.path.splitext(file)[0]
            comp = Component(name, data)
            components.append(comp)
    return components
