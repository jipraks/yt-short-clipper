"""Download subtitle-only (no video) for a YouTube URL via yt-dlp."""

import json
import os
from pathlib import Path
from typing import Any, Callable

from .cookies import validate_cookies
from .helpers import debug_log, get_deno_path, get_ffmpeg_path
from .json3_parser import find_orig_caption_code, parse_json3_words

LogFn = Callable[[str], None]


def _base_ydl_opts(cookies_path: str, deno_path: str | None, ffmpeg_path: str | None) -> dict[str, Any]:
    """Shared yt-dlp options (cookies + deno + ffmpeg) for subtitle work."""
    opts: dict[str, Any] = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": False,
        "cookiefile": str(cookies_path),
    }
    if deno_path and Path(deno_path).exists():
        opts["js_runtimes"] = {"deno": {"path": deno_path}}
        opts["remote_components"] = ["ejs:github"]
    if ffmpeg_path and Path(ffmpeg_path).exists():
        opts["ffmpeg_location"] = str(Path(ffmpeg_path).parent)
    return opts


def download_caption_words(
    url: str,
    temp_dir: str | Path,
    cookies_path: str,
    log: LogFn | None = None,
) -> str | None:
    """Download the original-language auto-caption track as json3 and parse it.

    Captions are built from the original ASR track (``*-orig``), which is the
    only track with genuine per-word timing. Writes ``words.json`` (a flat
    word list with absolute timestamps) into ``temp_dir``.

    Returns:
        Path to the written ``words.json``, or None if the video has no
        original auto-caption track (caller should then skip captions).
    """
    log = log or debug_log

    is_valid, error_msg = validate_cookies(cookies_path)
    if not is_valid:
        raise RuntimeError(error_msg)

    import yt_dlp

    temp_dir = Path(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    deno_path = get_deno_path()
    ffmpeg_path = get_ffmpeg_path()
    if deno_path and Path(deno_path).exists():
        os.environ["PATH"] = f"{Path(deno_path).parent}{os.pathsep}{os.environ.get('PATH', '')}"

    # Step 1: discover the original-language auto-caption code.
    probe_opts = _base_ydl_opts(cookies_path, deno_path, ffmpeg_path)
    try:
        with yt_dlp.YoutubeDL(probe_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        log(f"Caption probe failed: {str(e)[:200]} — captions will be skipped")
        return None

    orig_code = find_orig_caption_code((info or {}).get("automatic_captions"))
    if not orig_code:
        log("No original-language subtitle track — captions will be skipped")
        return None

    log(f"Original caption track: {orig_code} (downloading word-level timing)...")

    # Step 2: download just that track in json3.
    dl_opts = _base_ydl_opts(cookies_path, deno_path, ffmpeg_path)
    dl_opts.update(
        {
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": [orig_code],
            "subtitlesformat": "json3",
            "outtmpl": str(temp_dir / "caption_src.%(ext)s"),
        }
    )
    try:
        with yt_dlp.YoutubeDL(dl_opts) as ydl:
            ydl.extract_info(url, download=True)
    except Exception as e:
        log(f"Caption track download failed: {str(e)[:200]} — captions will be skipped")
        return None

    json3_files = list(temp_dir.glob("caption_src.*.json3"))
    if not json3_files:
        log("Caption json3 file not produced — captions will be skipped")
        return None

    try:
        words = parse_json3_words(str(json3_files[0]))
    except Exception as e:
        log(f"Failed to parse caption json3: {str(e)[:200]} — captions will be skipped")
        return None
    finally:
        # The parsed word list (words.json) is the artifact we keep; drop the raw track.
        for f in json3_files:
            try:
                f.unlink()
            except Exception:
                pass

    if not words:
        log("Caption track had no usable words — captions will be skipped")
        return None

    words_path = temp_dir / "words.json"
    with open(words_path, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False)

    log(f"Caption word-timing ready: {len(words)} words")
    return str(words_path)


def download_subtitle_only(
    url: str,
    subtitle_language: str,
    temp_dir: str | Path,
    cookies_path: str,
    log: LogFn | None = None,
) -> tuple[str | None, dict[str, Any]]:
    """Download only the subtitle for a video.

    Returns:
        (srt_path, video_info) — srt_path is None if no subtitle was found.
    """
    log = log or debug_log

    is_valid, error_msg = validate_cookies(cookies_path)
    if not is_valid:
        raise RuntimeError(error_msg)

    import yt_dlp

    log(f"yt-dlp module v{yt_dlp.version.__version__}")

    temp_dir = Path(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    deno_path = get_deno_path()
    ffmpeg_path = get_ffmpeg_path()

    if deno_path and Path(deno_path).exists():
        deno_dir = str(Path(deno_path).parent)
        os.environ["PATH"] = f"{deno_dir}{os.pathsep}{os.environ.get('PATH', '')}"
        log("Deno runtime ready (remote-components enabled)")
    else:
        log("Deno not found — some formats may be unavailable")

    ydl_opts: dict[str, Any] = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": [subtitle_language],
        "subtitlesformat": "srt",
        "outtmpl": str(temp_dir / "source.%(ext)s"),
        "quiet": True,
        "no_warnings": False,
        "cookiefile": str(cookies_path),
    }

    if deno_path and Path(deno_path).exists():
        ydl_opts["js_runtimes"] = {"deno": {"path": deno_path}}
        ydl_opts["remote_components"] = ["ejs:github"]

    if ffmpeg_path and Path(ffmpeg_path).exists():
        ydl_opts["ffmpeg_location"] = str(Path(ffmpeg_path).parent)
        ydl_opts["postprocessors"] = [{"key": "FFmpegSubtitlesConvertor", "format": "srt"}]

    video_info: dict[str, Any] = {}
    try:
        log(f"Fetching video info and {subtitle_language.upper()} subtitle via yt-dlp...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info:
                video_info = {
                    "title": info.get("title", ""),
                    "description": (info.get("description", "") or "")[:2000],
                    "channel": info.get("channel", ""),
                }
    except Exception as e:
        last_error = str(e)
        log(f"Subtitle download failed: {last_error[:200]}")
        if "403" in last_error or "Forbidden" in last_error:
            raise RuntimeError(
                "YouTube rejected access (HTTP 403). Your cookies may have expired. "
                "Please export fresh cookies while logged into YouTube."
            )
        raise RuntimeError(f"Subtitle download failed: {last_error}")

    srt_path = temp_dir / f"source.{subtitle_language}.srt"
    if not srt_path.exists():
        available = list(temp_dir.glob("source.*.srt"))
        if available:
            srt_path = available[0]
            detected = srt_path.stem.split(".")[-1]
            log(f"{subtitle_language.upper()} not found, using detected subtitle: {detected}")
        else:
            log(f"No subtitle file produced for language: {subtitle_language}")
            return None, video_info

    return str(srt_path), video_info
