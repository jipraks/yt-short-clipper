"""CLI entry point for yt_short_clipper_core — callable from Tauri sidecar.

Usage:
    python -m yt_short_clipper_core.cli get_subtitles <url> <cookies_path>

Output: JSON on stdout, one line.
Exit code: 0 on success (even if subtitles empty), 1 on error.
"""

import json
import sys


def main() -> None:
    args = sys.argv[1:]
    if len(args) < 3 or args[0] != "get_subtitles":
        print(
            json.dumps(
                {
                    "error": "Usage: yt_short_clipper_core.cli get_subtitles <url> <cookies_path>",
                    "subtitles": [],
                    "automatic_captions": [],
                }
            ),
            flush=True,
        )
        sys.exit(1)

    url = args[1]
    cookies_path = args[2]

    try:
        from yt_short_clipper_core.subtitle_fetcher import get_available_subtitles

        result = get_available_subtitles(url, cookies_path=cookies_path)
    except Exception as e:
        result = {"error": str(e), "subtitles": [], "automatic_captions": []}

    print(json.dumps(result, ensure_ascii=False), flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
