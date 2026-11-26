"""Download a low-resolution proxy of the whole source video.

The highlight editor plays this proxy so the user can scrub the source and
drag a clip's start/end before anything is rendered. The proxy is only for
previewing: rendering still downloads each clip at full quality.
"""

import os
import threading
import time
from pathlib import Path
from typing import Callable

from .helpers import get_deno_path, get_ffmpeg_path, is_ytdlp_module_available
from .video_processor import _YTDlpLogger, _extract_progress, _find_downloaded_file, _setup_ytdlp_env

LogFn = Callable[[str], None]
ProgressFn = Callable[[float], None]

PROXY_NAME = "proxy.mp4"

# H.264 + AAC in MP4 so WebView2 can play it without transcoding. At 360p a
# 29-minute test video came to 78 MB, so roughly 160 MB an hour.
FORMAT_SELECTOR = (
    "bestvideo[height<=360][vcodec^=avc1]+bestaudio[ext=m4a]"
    "/best[height<=360][ext=mp4]"
    "/bestvideo[height<=480][vcodec^=avc1]+bestaudio[ext=m4a]"
    "/best[ext=mp4]/best"
)

# yt-dlp downloads video and audio as two streams. Video is the bulk of it, so
# it gets most of the progress bar.
_VIDEO_SHARE = 85.0


def proxy_path_for(session_dir: str) -> Path:
    return Path(session_dir) / PROXY_NAME


def download_proxy(
    url: str,
    session_dir: str,
    cookies_path: str,
    log: LogFn,
    progress: ProgressFn,
) -> dict:
    final_path = proxy_path_for(session_dir)
    if final_path.exists() and final_path.stat().st_size > 0:
        progress(100.0)
        return {"path": str(final_path), "cached": True}

    if not is_ytdlp_module_available():
        raise RuntimeError("yt-dlp Python module is required to download the preview video.")
    if not cookies_path or not Path(cookies_path).exists():
        raise RuntimeError("cookies.txt not found. Please upload cookies first.")

    import yt_dlp

    _setup_ytdlp_env()

    ffmpeg_path = get_ffmpeg_path()
    if not ffmpeg_path or not Path(ffmpeg_path).exists():
        raise RuntimeError("FFmpeg is required to download the preview video but was not found.")
    ffmpeg_dir = str(Path(ffmpeg_path).parent)
    os.environ["PATH"] = f"{ffmpeg_dir}{os.pathsep}{os.environ.get('PATH', '')}"

    # Download under a temp name so an interrupted run never leaves a
    # half-written proxy.mp4 that the next run would treat as finished.
    temp_stem = Path(session_dir) / "proxy_download"
    for stale in Path(session_dir).glob("proxy_download*"):
        try:
            stale.unlink()
        except OSError:
            pass

    state = {"stream": 0, "streams": 1, "last_sent": -1.0, "last_activity": time.time()}

    def overall(stream_pct: float) -> float:
        if state["streams"] <= 1:
            return stream_pct
        if state["stream"] == 0:
            return stream_pct * _VIDEO_SHARE / 100.0
        return _VIDEO_SHARE + stream_pct * (100.0 - _VIDEO_SHARE) / 100.0

    def hook(d: dict) -> None:
        state["last_activity"] = time.time()
        info = d.get("info_dict") or {}
        requested = info.get("requested_formats")
        if requested:
            state["streams"] = len(requested)
        status = d.get("status")
        if status == "downloading":
            pct, _detail = _extract_progress(d)
            if pct is None:
                return
            value = min(99.0, overall(float(pct)))
            if value - state["last_sent"] >= 0.5:
                state["last_sent"] = value
                progress(round(value, 1))
        elif status == "finished":
            state["stream"] += 1

    ydl_opts = {
        "format": FORMAT_SELECTOR,
        "merge_output_format": "mp4",
        "outtmpl": f"{temp_stem}.%(ext)s",
        "quiet": True,
        "no_warnings": False,
        "noplaylist": True,
        "socket_timeout": 30,
        "retries": 5,
        "fragment_retries": 5,
        "concurrent_fragment_downloads": 4,
        "cookiefile": cookies_path,
        "ffmpeg_location": ffmpeg_dir,
        # Index at the front so the player can seek before reading the file end.
        "postprocessor_args": {"merger+ffmpeg": ["-movflags", "+faststart"]},
        "logger": _YTDlpLogger(log),
        "progress_hooks": [hook],
    }

    deno_path = get_deno_path()
    if deno_path and Path(deno_path).exists():
        ydl_opts["js_runtimes"] = {"deno": {"path": deno_path}}
        ydl_opts["remote_components"] = ["ejs:github"]

    stop = threading.Event()

    def heartbeat() -> None:
        while not stop.wait(15):
            if time.time() - state["last_activity"] >= 15:
                log("⏳ Still downloading the preview video...")

    threading.Thread(target=heartbeat, daemon=True).start()

    log("Downloading preview video (360p)...")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        msg = str(e)
        if "403" in msg or "Forbidden" in msg:
            raise RuntimeError(
                "YouTube refused the download (403). Your cookies may have expired; "
                "upload fresh cookies and try again."
            ) from e
        raise
    finally:
        stop.set()

    downloaded = Path(_find_downloaded_file(f"{temp_stem}.mp4"))
    if downloaded.suffix.lower() != ".mp4":
        log(f"⚠️ Preview came back as {downloaded.suffix}; it may not play in the editor.")
    os.replace(downloaded, final_path)
    progress(100.0)
    log("Preview video ready.")
    return {"path": str(final_path), "cached": False}
