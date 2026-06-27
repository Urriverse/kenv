#!/usr/bin/env python3
"""
Entry point for the Osenv package.
"""
from osenv.cli import main

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
