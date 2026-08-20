"""Subprocess entry point for portrait conversion.

Invoked by the frozen sidecar via:
    python -m yt_short_clipper_core.portrait_run <input> <output>
"""

import sys
from .portrait import convert_to_portrait

def main():
    if len(sys.argv) < 3:
        print("Usage: python -m yt_short_clipper_core.portrait_run <input.mp4> <output.mp4>")
        sys.exit(1)
    convert_to_portrait(sys.argv[1], sys.argv[2], log=lambda m: print(m, flush=True))

if __name__ == "__main__":
    main()
