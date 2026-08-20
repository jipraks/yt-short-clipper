"""Fetch available subtitles for a YouTube video using yt-dlp.

Public API:
    get_available_subtitles(url, ytdlp_path, cookies_path) -> dict

Returned dict:
    - "subtitles":          list of {"code": str, "name": str}  (manual)
    - "automatic_captions": list of {"code": str, "name": str}  (auto-generated)
    - "error":              str | None
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from .constants import LANG_NAMES, SUBPROCESS_FLAGS
from .cookies import validate_cookies
from .helpers import debug_log, get_ffmpeg_path, get_deno_path, is_ytdlp_module_available


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_available_subtitles(
    url: str,
    ytdlp_path: str = "yt-dlp",
    cookies_path: str | None = None,
) -> dict[str, Any]:
    """Get list of available subtitles for a YouTube video.

    Args:
        url: YouTube video URL.
        ytdlp_path: Path to yt-dlp executable, or "yt_dlp_module" for module API.
        cookies_path: Path to cookies.txt file (required).

    Returns:
        dict with keys: "subtitles", "automatic_captions", "error".
    """
    use_module = is_ytdlp_module_available() and ytdlp_path == "yt_dlp_module"

    if use_module:
        return _get_subtitles_module(url, cookies_path)
    else:
        return _get_subtitles_subprocess(url, ytdlp_path, cookies_path)


# ---------------------------------------------------------------------------
# Module-based (yt-dlp Python API)
# ---------------------------------------------------------------------------


def _get_subtitles_module(url: str, cookies_path: str | None) -> dict[str, Any]:
    """Get subtitles using yt-dlp Python module API."""
    try:
        # Validate cookies
        is_valid, error_msg = validate_cookies(cookies_path)
        if not is_valid:
            return {
                "error": error_msg,
                "subtitles": [],
                "automatic_captions": [],
            }

        debug_log(f"Cookies path: {cookies_path}")

        # Setup Deno in PATH if available
        deno_path = get_deno_path()
        ffmpeg_path = get_ffmpeg_path()

        if deno_path and Path(deno_path).exists():
            deno_dir = str(Path(deno_path).parent)
            os.environ["PATH"] = f"{deno_dir}{os.pathsep}{os.environ.get('PATH', '')}"
            debug_log(f"Deno path added: {deno_dir}")

        import yt_dlp

        debug_log(f"Using yt-dlp module v{yt_dlp.version.__version__}")

        ydl_opts: dict[str, Any] = {
            "skip_download": True,
            "quiet": False,
            "no_warnings": False,
            "cookiefile": str(cookies_path),
        }

        if deno_path and Path(deno_path).exists():
            ydl_opts["js_runtimes"] = {"deno": {"path": deno_path}}
            ydl_opts["remote_components"] = ["ejs:github"]
            debug_log(f"JS runtime: deno at {deno_path}")

        if ffmpeg_path and Path(ffmpeg_path).exists():
            ydl_opts["ffmpeg_location"] = str(Path(ffmpeg_path).parent)
            debug_log(f"FFmpeg location: {ydl_opts['ffmpeg_location']}")

        debug_log(f"yt-dlp opts: cookiefile={ydl_opts['cookiefile']}")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            video_data = ydl.extract_info(url, download=False)

        if not video_data:
            return {"error": "Failed to fetch video info", "subtitles": [], "automatic_captions": []}

        return _extract_subtitle_lists(video_data)

    except Exception as e:
        debug_log(f"yt-dlp module error: {e}")
        return {"error": str(e), "subtitles": [], "automatic_captions": []}


# ---------------------------------------------------------------------------
# Subprocess-based (yt-dlp CLI)
# ---------------------------------------------------------------------------


def _get_subtitles_subprocess(
    url: str,
    ytdlp_path: str,
    cookies_path: str | None,
) -> dict[str, Any]:
    """Get subtitles using yt-dlp subprocess (fallback)."""
    try:
        # Validate cookies
        is_valid, error_msg = validate_cookies(cookies_path)
        if not is_valid:
            return {
                "error": error_msg,
                "subtitles": [],
                "automatic_captions": [],
            }

        # Build environment with Deno path
        env = os.environ.copy()
        deno_path = get_deno_path()
        if deno_path:
            deno_dir = str(Path(deno_path).parent)
            env["PATH"] = f"{deno_dir}{os.pathsep}{env.get('PATH', '')}"
            debug_log(f"Deno found at: {deno_path}")
        else:
            debug_log("Deno not found - remote-components may not work")

        # Build command
        cmd = [ytdlp_path, "--dump-json", "--skip-download", "--cookies", str(cookies_path)]

        # Check for feature flags
        try:
            help_result = subprocess.run(
                [ytdlp_path, "--help"],
                capture_output=True,
                text=True,
                creationflags=SUBPROCESS_FLAGS,
                timeout=5,
            )
            if help_result.returncode == 0:
                help_text = help_result.stdout
                if "--remote-components" in help_text and deno_path:
                    cmd.extend(["--remote-components", "ejs:github"])
                    debug_log("Added --remote-components ejs:github")
                if "--no-impersonate" in help_text:
                    cmd.append("--no-impersonate")
                    debug_log("Added --no-impersonate flag")
        except Exception as e:
            debug_log(f"Error checking yt-dlp features: {e}")

        cmd.append(url)
        debug_log(f"Running command: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=SUBPROCESS_FLAGS,
            env=env,
            timeout=30,
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            debug_log(f"yt-dlp stderr: {error_msg}")
            return {
                "error": f"Failed to fetch video info: {error_msg[:100]}",
                "subtitles": [],
                "automatic_captions": [],
            }

        video_data = json.loads(result.stdout)
        return _extract_subtitle_lists(video_data)

    except subprocess.TimeoutExpired:
        return {"error": "Timeout fetching subtitles", "subtitles": [], "automatic_captions": []}
    except json.JSONDecodeError:
        return {"error": "Failed to parse video data", "subtitles": [], "automatic_captions": []}
    except Exception as e:
        return {"error": str(e), "subtitles": [], "automatic_captions": []}


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------


def _extract_subtitle_lists(video_data: dict) -> dict[str, Any]:
    """Extract subtitle and automatic_caption lists from yt-dlp video data."""
    from .json3_parser import find_orig_caption_code

    subtitles: list[dict[str, str]] = []
    auto_captions: list[dict[str, str]] = []

    for key, dest in [("subtitles", subtitles), ("automatic_captions", auto_captions)]:
        source = video_data.get(key) or {}
        for lang_code in source.keys():
            if "live_chat" in lang_code:
                continue
            lang_name = LANG_NAMES.get(lang_code, lang_code.upper())
            dest.append({"code": lang_code, "name": lang_name})

    # The original-language auto-caption track is the only source of genuine
    # per-word timing, so it drives whether word-by-word captions are possible.
    caption_orig_code = find_orig_caption_code(video_data.get("automatic_captions"))

    return {
        "subtitles": subtitles,
        "automatic_captions": auto_captions,
        "caption_orig_code": caption_orig_code,
        "error": None,
    }
