"""
Command: fetch – download/clone component sources.
"""
from ..core.component import load_all_components
from ..core.builder import fetch_components
from ..utils.log import *


def main(args):
    components = load_all_components()
    if args.component:
        # Keep only those with matching names (case-sensitive)
        components = [c for c in components if c.name in args.component]

    fetch_components(components, skip_git=args.no_git)
    i("Fetch", "completed")
