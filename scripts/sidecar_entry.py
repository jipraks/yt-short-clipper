"""PyInstaller entry point for the YT Short Clipper Python sidecar.

This thin wrapper exists so PyInstaller has a single top-level script to
freeze. All real logic lives in yt_short_clipper_core.sidecar.
"""

from yt_short_clipper_core.sidecar import main

if __name__ == "__main__":
    main()
