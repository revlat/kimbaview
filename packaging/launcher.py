"""Startskript für PyInstaller (Windows) und py2app (macOS)."""

import sys

from kimbaview.app import main

if __name__ == "__main__":
    sys.exit(main())
