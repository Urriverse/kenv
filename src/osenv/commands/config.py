"""
Command: config – create/switch configuration and set variables.
"""
import os
from dotenv import set_key, dotenv_values
from ..core.confenv import get_config_path, set_active_config
from ..utils.log import *


def main(args):
    config_name = args.name
    config_path = get_config_path(config_name)

    # Create if not exists
    if not os.path.exists(config_path):
        with open(config_path, 'w') as f:
            f.write(f"# Configuration: {config_name}\n")

    # Set variables if provided
    if args.set:
        for key, value in args.set:
            set_key(config_path, key, value)

    # Activate this configuration
    set_active_config(config_name)
    ii(f"Active configuration set to: {config_name}")
