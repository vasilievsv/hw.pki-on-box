#!/usr/bin/env python
# pki.py — CLI entrypoint
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.cli import pki_cli

if __name__ == "__main__":
    pki_cli()
