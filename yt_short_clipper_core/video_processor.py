"""Download video sections from YouTube via yt-dlp."""

import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable

from .cookies import validate_cookies
from .helpers import debug_log, get_deno_path, get_ffmpeg_path, is_ytdlp_module_available
from .helpers import _get_app_dir

LogFn = Callable[[str], None]


def _parse_timestamp(ts: str) -> float:
    """Convert timestamp HH:MM:SS,mmm or HH:MM:SS.mmm to seconds."""
    ts = ts.replace(",", ".")
    parts = ts.split(":")
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])


def _find_downloaded_file(output_path: str) -> str:
    """yt-dlp may change the extension; find the actual file."""
    if Path(output_path).exists():
        return output_path
    output_dir = Path(output_path).parent
    output_stem = Path(output_path).stem
    mp4 = output_dir / f"{output_stem}.mp4"
    if mp4.exists():
        return str(mp4)
    candidates = [
        c for c in output_dir.glob(f"{output_stem}.*")
        if c.suffix in (".mp4", ".mkv", ".webm")
    ]
    if candidates:
        return str(candidates[0])
    raise RuntimeError(f"Downloaded section file not found: {output_path}")


def _setup_ytdlp_env() -> None:
    """Ensure Deno is in PATH for yt-dlp remote components."""
    deno_path = get_deno_path()
    if deno_path and Path(deno_path).exists():
        deno_dir = str(Path(deno_path).parent)
        os.environ["PATH"] = f"{deno_dir}{os.pathsep}{os.environ.get('PATH', '')}"


def _extract_progress(d: dict) -> tuple[str | None, str]:
    """Normalize a yt-dlp progress dict into ``(percent, detail)``.

    yt-dlp only fills ``_percent_str`` for some transports. For DASH/range
    downloads (e.g. ``271+140``) it's usually empty, so we compute the
    percentage ourselves from the raw byte counters, then fall back to
    fragment counts (HLS/DASH manifests). ``percent`` is a bare number string
    without the ``%`` sign, or ``None`` if nothing usable is available.
    """
    pct: str | None = None

    # 1) yt-dlp's own formatted percent, when present
    raw_pct = (d.get("_percent_str") or "").strip()
    match = re.search(r"(\d+\.?\d*)%", raw_pct)
    if match:
        pct = match.group(1)
    else:
        # 2) compute from raw byte counters (total may only be an estimate)
        downloaded = d.get("downloaded_bytes")
        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        if isinstance(downloaded, (int, float)) and isinstance(total, (int, float)) and total > 0:
            pct = f"{min(100.0, downloaded / total * 100):.1f}"
        else:
            # 3) fall back to fragment progress for segmented downloads
            frag_i = d.get("fragment_index")
            frag_n = d.get("fragment_count")
            if isinstance(frag_i, (int, float)) and isinstance(frag_n, (int, float)) and frag_n > 0:
                pct = f"{frag_i / frag_n * 100:.0f}"

    downloaded_str = d.get("_downloaded_bytes_str") or d.get("downloaded_bytes")
    speed = d.get("_speed_str") or d.get("speed")
    eta = d.get("_eta_str") or d.get("eta")
    parts = []
    if downloaded_str:
        parts.append(f"{downloaded_str}")
    if speed:
        parts.append(f"@ {speed}")
    if eta is not None:
        parts.append(f"eta {eta}")
    detail = " ".join(str(p) for p in parts)
    return pct, detail


def _yt_dlp_progress_hook(d: dict, log: LogFn) -> None:
    """Report yt-dlp download progress.

    yt-dlp's progress dict uses different keys depending on the transport
    (direct HTTP, HLS fragments, DASH). ``_percent_str`` can be empty during
    the first fragment or when the total size is unknown — in that case we
    compute the percentage from raw counters (see ``_extract_progress``) and,
    failing that, surface bytes downloaded and speed instead of staying silent
    (silent = looks like a hang to the user).
    """
    status = d.get("status")
    if status == "downloading":
        pct, detail = _extract_progress(d)
        if pct is not None:
            suffix = f" ({detail})" if detail else ""
            log(f"Download progress: {pct}%{suffix}")
        elif detail:
            log(f"Download progress: {detail}")
        else:
            log("Download progress: starting...")
    elif status == "finished":
        total = d.get("_total_bytes_str") or d.get("total_bytes") or ""
        elapsed = d.get("_elapsed_str") or d.get("elapsed") or ""
        tail = f" ({total}, {elapsed})" if (total or elapsed) else ""
        log(f"Download complete, merging...{tail}")


class _YTDlpLogger:
    """Forward yt-dlp's own log lines to our sidecar log fn.

    yt-dlp emits a lot of useful messages (extractor selection, format
    probing, fragment retries, 403s, merge steps) that are silenced by
    ``quiet: True``. Passing an instance of this class via ``ydl_opts[
    "logger"]`` surfaces info/warning/error lines so the user can see what
    yt-dlp is actually doing while a section download is in flight — instead
    of a silent hang at "FFmpeg path resolved: ...".
    """

    def __init__(self, log: LogFn) -> None:
        self._log = log

    def debug(self, msg: str) -> None:
        # yt-dlp's debug channel is extremely noisy (per-fragment bytes),
        # so we only surface the lines that hint at *what* yt-dlp is doing
        # right now, not the byte counters.
        if any(k in msg for k in ("Downloading ", "Downloading item ", "[download]", "Extracting", "Downloading fragment", "Resuming", "Merging", "Deleting")):
            self._log(msg)

    def info(self, msg: str) -> None:
        self._log(msg)

    def warning(self, msg: str) -> None:
        self._log(f"⚠️ {msg}")

    def error(self, msg: str) -> None:
        self._log(f"❌ {msg}")


def _get_cookies_path() -> str:
    """Find cookies.txt in cwd, app dir, or Tauri app data dir."""
    app_dir = _get_app_dir()
    for loc in [Path("cookies.txt"), app_dir / "cookies.txt"]:
        if loc.exists():
            return str(loc)
    # Tauri app data dir
    try:
        import platform
        if platform.system() == "Windows":
            data_dir = Path(os.environ.get("APPDATA", ""))
        elif platform.system() == "Darwin":
            data_dir = Path.home() / "Library" / "Application Support"
        else:
            data_dir = Path.home() / ".config"
        app_data = data_dir / "com.jipraks.ytshortclipper-v2"
        ck = app_data / "cookies.txt"
        if ck.exists():
            return str(ck)
    except Exception:
        pass
    raise RuntimeError("cookies.txt not found. Please upload cookies first.")


def download_video_section(
    url: str,
    start_time: str,
    end_time: str,
    output_path: str,
    log: LogFn | None = None,
) -> str:
    """Download a specific section of a YouTube video.

    Returns path to the downloaded file.
    """
    log = log or debug_log
    start_clean = start_time.replace(",", ".")
    end_clean = end_time.replace(",", ".")

    if is_ytdlp_module_available():
        return _download_section_module(url, start_clean, end_clean, output_path, log)
    else:
        raise RuntimeError(
            "yt-dlp Python module is required for downloading video sections. "
            "Install it with: pip install yt-dlp"
        )


def _download_section_module(
    url: str,
    start_time: str,
    end_time: str,
    output_path: str,
    log: LogFn,
) -> str:
    import yt_dlp

    log(f"Downloading section {start_time} -> {end_time}...")

    _setup_ytdlp_env()
    ffmpeg_path = get_ffmpeg_path()
    cookies_path = _get_cookies_path()

    # Cap at 1080p and strongly prefer H.264 (avc1) video + m4a audio.
    # YouTube's >1080p tiers are VP9/AV1 only; picking those forces ffmpeg to
    # decode VP9/AV1 and re-encode to H.264 during the section cut, which on a
    # 1440p/2160p source crawls at ~1-2x realtime on CPU (the "stuck for hours"
    # symptom). H.264 1080p keeps the cut cheap and speeds up the later portrait
    # encode too (smaller input). Falls back progressively if avc1 is absent.
    format_selector = (
        "bestvideo[height<=1080][vcodec^=avc1]+bestaudio[acodec^=mp4a]/"
        "bestvideo[height<=1080][vcodec^=avc1]+bestaudio/"
        "bestvideo[height<=1080]+bestaudio/"
        "best[height<=1080]/best"
    )

    ydl_opts: dict[str, Any] = {
        "format": format_selector,
        "format_sort": ["res", "br"],
        "merge_output_format": "mp4",
        "outtmpl": output_path,
        "quiet": True,
        "no_warnings": False,
        "hls_prefer_native": True,
        "concurrent_fragment_downloads": 1,
        "socket_timeout": 30,
        "retries": 5,
        "fragment_retries": 5,
        "download_ranges": yt_dlp.utils.download_range_func(
            None, [(_parse_timestamp(start_time), _parse_timestamp(end_time))]
        ),
        "force_keyframes_at_cuts": True,
        "cookiefile": cookies_path,
        "logger": _YTDlpLogger(log),
        "progress_hooks": [
            lambda d: _yt_dlp_progress_hook(d, log)
        ],
    }

    deno_path = get_deno_path()
    if deno_path and Path(deno_path).exists():
        ydl_opts["js_runtimes"] = {"deno": {"path": deno_path}}
        ydl_opts["remote_components"] = ["ejs:github"]

    if ffmpeg_path and Path(ffmpeg_path).exists():
        ffmpeg_dir = str(Path(ffmpeg_path).parent)
        ydl_opts["ffmpeg_location"] = ffmpeg_dir
        os.environ["PATH"] = f"{ffmpeg_dir}{os.pathsep}{os.environ.get('PATH', '')}"
        log(f"FFmpeg path resolved: {ffmpeg_path}")
    else:
        raise RuntimeError(
            f"FFmpeg is required for downloading video sections but was not found. "
            f"Last path checked: {ffmpeg_path!r}. "
            "Please ensure ffmpeg is bundled with the app (ffmpeg/ffmpeg.exe next to "
            "the sidecar) or installed on the system PATH."
        )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    download_state = {
        "last_log_ts": time.monotonic(),
        "last_pct": None,
        "last_detail": "",
    }

    def _hook_with_heartbeat(d: dict) -> None:
        # Update heartbeat timestamp whenever yt-dlp reports activity
        download_state["last_log_ts"] = time.monotonic()
        if d.get("status") == "downloading":
            pct, detail = _extract_progress(d)
            if pct is not None:
                download_state["last_pct"] = pct
            if detail:
                download_state["last_detail"] = detail
        _yt_dlp_progress_hook(d, log)

    ydl_opts["progress_hooks"] = [_hook_with_heartbeat]

    stop_evt = threading.Event()

    def heartbeat() -> None:
        started = time.monotonic()
        every = 15
        while not stop_evt.wait(every):
            elapsed = int(time.monotonic() - started)
            since_last_log = int(time.monotonic() - download_state["last_log_ts"])
            pct = download_state["last_pct"]
            detail = download_state["last_detail"]
            if pct is not None:
                log(f"⏳ Still downloading: {pct}% ({detail}), {elapsed}s elapsed")
            elif detail:
                log(f"⏳ Still downloading: {detail}, {elapsed}s elapsed (no progress % yet)")
            else:
                log(
                    f"⏳ Still waiting for download data... {elapsed}s elapsed, "
                    f"{since_last_log}s since last activity"
                )

    hb_thread = threading.Thread(target=heartbeat, daemon=True, name="yt-dlp-heartbeat")
    hb_thread.start()

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        msg = str(e)
        log(f"Section download failed: {msg[:200]}")
        if "403" in msg or "Forbidden" in msg:
            raise RuntimeError(
                "YouTube rejected access (HTTP 403). Your cookies may have expired. "
                "Please export fresh cookies while logged into YouTube."
            )

        # Retry with fallback: simple format, no download_ranges
        if "ffmpeg" in msg.lower():
            log("Retrying with fallback options (simple format + no ranges)...")
            fallback_opts = dict(ydl_opts)
            fallback_opts.pop("download_ranges", None)
            fallback_opts.pop("force_keyframes_at_cuts", None)
            fallback_opts["format"] = "best[height>=720][height<=2160]/bestvideo+bestaudio/best"
            download_state["last_log_ts"] = time.monotonic()
            download_state["last_pct"] = None
            download_state["last_detail"] = "(fallback retry)"
            try:
                with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                    ydl.download([url])
            except Exception as e2:
                msg2 = str(e2)
                log(f"Fallback download also failed: {msg2[:200]}")
                raise RuntimeError(f"Failed to download video section: {msg2}")

            # Manually cut with ffmpeg since we downloaded the full video
            stop_evt.set()
            log("Cutting downloaded video to requested section...")
            cut_output = output_path + ".cut.mp4"
            full_path = _find_downloaded_file(output_path)
            ffmpeg_path = get_ffmpeg_path()
            cut_cmd = [
                str(ffmpeg_path), "-y",
                "-ss", start_time,
                "-to", end_time,
                "-i", full_path,
                "-c", "copy",
                "-avoid_negative_ts", "make_zero",
                str(cut_output),
            ]
            import subprocess
            import sys
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            result = subprocess.run(cut_cmd, capture_output=True, text=True, creationflags=flags)
            if result.returncode != 0:
                raise RuntimeError(f"Failed to cut video section with ffmpeg: {result.stderr[:500]}")
            import shutil
            shutil.move(cut_output, output_path)
            return output_path

        raise RuntimeError(f"Failed to download video section: {msg}")
    finally:
        stop_evt.set()
        hb_thread.join(timeout=2)

    return _find_downloaded_file(output_path)
