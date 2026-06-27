"""
Command: test – run tests for components.
"""
from ..core.component import load_all_components
from ..core.builder import test_components


def main(args):
    components = load_all_components()
    if args.component:
        components = [c for c in components if c.name in args.component]
    test_components(components)
