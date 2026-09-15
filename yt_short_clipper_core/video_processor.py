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

    Rate-limited: HLS fires this hook per fragment (thousands of times), which
    would flood the sidecar stdout. We cap at ~1 progress line per second and
    always pass "finished" through.
    """
    status = d.get("status")
    if status == "finished":
        total = d.get("_total_bytes_str") or d.get("total_bytes") or ""
        elapsed = d.get("_elapsed_str") or d.get("elapsed") or ""
        tail = f" ({total}, {elapsed})" if (total or elapsed) else ""
        log(f"Download complete, merging...{tail}")
        return

    if status != "downloading":
        return

    now = time.monotonic()
    last = _progress_hook_state.get("last_ts", 0.0)
    if now - last < 1.0 and _progress_hook_state.get("last_pct") is not None:
        # suppress duplicate rapid-fire progress lines; heartbeat covers the gap
        return
    _progress_hook_state["last_ts"] = now

    pct, detail = _extract_progress(d)
    if pct is not None:
        _progress_hook_state["last_pct"] = pct
        suffix = f" ({detail})" if detail else ""
        log(f"Download progress: {pct}%{suffix}")
        _maybe_warn_throttled(d, log)
    elif detail:
        log(f"Download progress: {detail}")
    else:
        log("Download progress: starting...")


def _maybe_warn_throttled(d: dict, log: LogFn) -> None:
    """Warn once per download when YouTube is throttling the connection.

    Speed < ~100 KiB/s sustained is NOT a normal slow network — it is
    YouTube's deliberate per-connection cap for non-browser clients (or a
    missing cookies.txt). We surface it once so the user knows what's going
    on instead of watching a crawling percentage.
    """
    speed = d.get("speed")
    if not speed:
        return
    kiB_s = speed / 1024.0
    if kiB_s >= 100:
        return  # healthy speed
    now = time.monotonic()
    if _progress_hook_state.get("throttle_warned_ts", 0.0) and now - _progress_hook_state["throttle_warned_ts"] < 60:
        return  # already warned recently
    _progress_hook_state["throttle_warned_ts"] = now
    log(
        f"⚠️ YouTube throttling detected: only {kiB_s:.0f} KiB/s. This is "
        "YouTube's per-connection cap for non-browser clients, not your "
        "network. Mitigations active: parallel fragments (×8). Adding a "
        "cookies.txt from a logged-in YouTube session usually removes the cap."
    )


_progress_hook_state: dict = {"last_ts": 0.0, "last_pct": None, "throttle_warned_ts": 0.0}


class _YTDlpLogger:
    """Forward yt-dlp's own log lines to our sidecar log fn.

    yt-dlp emits a lot of useful messages (extractor selection, format
    probing, fragment retries, 403s, merge steps) that are silenced by
    ``quiet: True``. Passing an instance of this class via ``ydl_opts[
    "logger"]`` surfaces info/warning/error lines so the user can see what
    yt-dlp is actually doing while a section download is in flight — instead
    of a silent hang at "FFmpeg path resolved: ...".
    """

    def __init__(self, log: LogFn, state: dict | None = None) -> None:
        self._log = log
        self._state = state

    def debug(self, msg: str) -> None:
        # When yt-dlp starts fetching m3u8 manifests or fragments, extraction
        # is DONE and the download phase has begun.  Signal the watchdog so
        # it doesn't fire during slow CDN connections (>90s on throttled
        # Indonesian links).
        if self._state is not None and (
            "Downloading m3u8" in msg or "Downloading item" in msg
        ):
            self._state["download_phase_active"] = True
        # yt-dlp's debug channel is extremely noisy (per-fragment bytes),
        # so we only surface the lines that hint at *what* yt-dlp is doing
        # right now, not the byte counters. "Downloading fragment" is
        # excluded on purpose — on HLS it fires per fragment (thousands
        # of times) and would flood the sidecar stdout pipe.
        # CRITICAL (v2.0.28): "[download] X% of ~ YMiB at ZKiB/s (frag N/M)"
        # progress lines must NEVER be forwarded. With
        # concurrent_fragment_downloads=8, yt-dlp emits one per fragment per
        # thread (~10-30 lines/sec), flooding the log AND hammering CPU on
        # low-end machines (Celeron 2-core). Progress belongs to
        # _yt_dlp_progress_hook only (rate-limited to 1 line/sec). Keep only
        # the lifecycle lines: Destination, already-downloaded skips.
        if "[download]" in msg:
            if "[download] Destination" in msg or "[download] has already" in msg:
                self._log(msg)
            return
        if any(k in msg for k in ("Downloading ", "Downloading item ", "Extracting", "Resuming", "Merging", "Deleting")):
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

    download_state = {
        "last_log_ts": time.monotonic(),
        "last_pct": None,
        "last_detail": "",
        "first_activity_ts": None,
        "download_phase_active": False,  # set by _YTDlpLogger when m3u8/frag seen
    }

    ydl_opts: dict[str, Any] = {
        "format": format_selector,
        "format_sort": ["res", "br"],
        "merge_output_format": "mp4",
        "outtmpl": output_path,
        "quiet": True,
        "no_warnings": False,
        # v2.0.28: suppress yt-dlp's OWN progress rendering entirely
        # ("[download] X% of ~ YMiB ... (frag N/M)" lines). With 8 parallel
        # fragments those fire ~10-30x/sec and hammer CPU on low-end machines.
        # progress_hooks still fire (watchdog + UI progress keep working), only
        # the raw console/logger rendering is disabled.
        "noprogress": True,
        "hls_prefer_native": True,
        # Parallel fragment connections: YouTube throttles non-browser
        # clients per-connection (~a few hundred B/s). Browsers open many
        # parallel connections; we mimic that to bypass the per-connection cap.
        "concurrent_fragment_downloads": 8,
        # Fail fast on dead connections (ISP NAT drops, throttled YouTube):
        "socket_timeout": 10,
        "retries": 3,
        "fragment_retries": 3,
        "extractor_retries": 2,
        # CRITICAL (2026-09): force player clients that do NOT require the
        # BotGuard JS challenge. The defaults for authenticated sessions are
        # ('tv_downgraded', 'web') — the 'web' client needs a po_token and
        # a JS runtime, and yt-dlp lazily downloads the 'ejs' challenge
        # component from GitHub to solve it. On networks where GitHub is
        # slow/blocked (common in Indonesia), extraction HANGS forever after
        # "Downloading webpage" with no error. visionos/ios/android return
        # stream info directly without any JavaScript challenge.
        "extractor_args": {
            "youtube": {
                "player_client": ["visionos", "ios", "android", "tv_downgraded"],
                "player_skip": ["js"],
            },
        },
        # Overall extraction timeout (seconds). yt-dlp hangs here if YouTube
        # blocks or the connection silently dies mid-handshake.
        "extractor_timeout": 30,
        # NO download_ranges / force_keyframes_at_cuts here on purpose: ranged
        # downloads hand the network I/O to FFmpegFD (ffmpeg, single
        # connection), and YouTube throttles non-browser clients per-connection
        # (~10-20 KiB/s on Indonesian lines — an 85s section would take hours).
        # Native download + concurrent_fragment_downloads=8 opens 8 parallel
        # connections, bypassing the per-connection cap (measured ~100-190
        # KiB/s, 6-11x faster on the same throttle). The section is cut locally
        # afterwards with ffmpeg -c copy (no network involved).
        "cookiefile": cookies_path,
        "logger": _YTDlpLogger(log, download_state),
        "progress_hooks": [
            lambda d: _yt_dlp_progress_hook(d, log)
        ],
    }

    deno_path = get_deno_path()
    if deno_path and Path(deno_path).exists():
        ydl_opts["js_runtimes"] = {"deno": {"path": deno_path}}
        # NOTE: deliberately NOT setting remote_components=["ejs:github"] —
        # yt-dlp lazily fetches the ejs challenge solver from GitHub at
        # runtime, which can HANG extraction on slow/blocked networks. We
        # force JS-less player clients instead (see extractor_args above),
        # so the ejs solver is never needed.

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

    def _hook_with_heartbeat(d: dict) -> None:
        # Update heartbeat timestamp whenever yt-dlp reports activity
        download_state["last_log_ts"] = time.monotonic()
        if download_state["first_activity_ts"] is None:
            download_state["first_activity_ts"] = time.monotonic()
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
            first = download_state["first_activity_ts"]
            if first is None:
                log(
                    f"⏳ Preparing download... {elapsed}s elapsed "
                    "(fetching stream info / connecting). Can take a while on slow networks."
                )
            elif pct is not None:
                log(f"⏳ Still downloading: {pct}% ({detail}), {elapsed}s elapsed")
            elif detail:
                log(f"⏳ Still downloading: {detail}, {elapsed}s elapsed (no progress % yet)")
            elif since_last_log > 120:
                log(
                    f"⚠️ Download appears stalled — no data for {since_last_log}s. "
                    "If the connection is dead, the app will retry automatically with a simpler method."
                )
            else:
                log(
                    f"⏳ Waiting for download data... {elapsed}s elapsed, "
                    f"{since_last_log}s since last activity"
                )

    hb_thread = threading.Thread(target=heartbeat, daemon=True, name="yt-dlp-heartbeat")
    hb_thread.start()

    # --- Extraction watchdog ---
    # If yt-dlp never calls the progress hook (extraction stuck), abort after
    # _EXTRACT_ABORT seconds so the app doesn't hang forever.
    _EXTRACT_ABORT = 90  # 90s: extraction normally takes <15s with JS-less clients
    # Once extraction is done (m3u8 manifest / download phase seen), the
    # watchdog above must NOT kill a legitimately slow CDN fetch — but it also
    # must not exit permanently: if the m3u8/manifest fetch then STALLS forever
    # (dead NAT on throttled links — no progress hook fires, no debug lines),
    # nothing else would ever abort. Keep watching; abort only after this much
    # time with ZERO log/hook activity. Legit m3u8 fetches take 90-100s on
    # Indonesian throttled links, so 150s gives margin without hanging forever.
    _DOWNLOAD_STALL_ABORT = 150
    _abort = threading.Event()

    def _extraction_watchdog() -> None:
        """Guard extraction AND download phases from silent stalls.

        Phase 1 (extraction): abort after _EXTRACT_ABORT with no progress-hook
        activity. Phase 2 (download): extraction is done (progress hook fired
        or \"Downloading m3u8\"/\"Downloading item\" debug seen) — keep
        watching, but only abort once _DOWNLOAD_STALL_ABORT passes with no
        data/log activity at all. Both phases share one loop.
        """
        while not _abort.wait(15):
            first = download_state.get("first_activity_ts")
            dl_active = download_state.get("download_phase_active", False)
            if first is not None or dl_active:
                # Download phase: extraction finished. Last-resort guard for a
                # manifest (m3u8) fetch that hangs forever — no progress hook
                # fires, the connection may be dead. Fall through only when
                # data truly stalled; real downloads refresh last_log_ts via
                # the progress hook on every fragment.
                last_activity = download_state.get("last_log_ts") or _download_start
                idle_for = int(time.monotonic() - last_activity)
                if idle_for < _DOWNLOAD_STALL_ABORT:
                    continue  # still alive — keep watching
                log(
                    f"⚠️ Download phase stalled — no data for {idle_for}s. "
                    "Aborting and retrying with fallback options..."
                )
                _abort.set()
                return
            elapsed = int(time.monotonic() - _download_start)
            if elapsed >= _EXTRACT_ABORT:
                log(
                    f"⚠️ Extraction stuck for {elapsed}s with no response — "
                    "aborting and retrying with fallback options..."
                )
                _abort.set()
                return

    _download_start = time.monotonic()
    _watchdog = threading.Thread(target=_extraction_watchdog, daemon=True, name="yt-dlp-watchdog")
    _watchdog.start()

    def _run_download(ydl_opts_local: dict, label: str) -> None:
        """Run yt-dlp download in a thread, aborting if watchdog fires."""
        dl_thread = threading.Thread(
            target=lambda: yt_dlp.YoutubeDL(ydl_opts_local).download([url]),
            daemon=True, name=f"yt-dlp-dl-{label}",
        )
        dl_thread.start()
        while dl_thread.is_alive():
            if _abort.is_set():
                raise RuntimeError(
                    f"Download ({label}) aborted: extraction timed out after "
                    f"{_EXTRACT_ABORT}s with no activity. Check your network or try again."
                )
            dl_thread.join(timeout=5)

    def _cut_section(full_path: str) -> str:
        """Cut a full downloaded video to [start_time, end_time] with ffmpeg.

        Local-only operation, no network. `-c copy` avoids re-encoding (also
        means NO GPU/CPU encode cost here — the earlier section-download video
        was never re-encoded, only trimmed).
        """
        stop_evt.set()  # download phase done — stop the heartbeat thread
        log("Cutting downloaded video to requested section...")
        cut_output = output_path + ".cut.mp4"
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

    def _do_download() -> str:
        """Primary native full-download + local cut → fallback (simpler format).

        Primary does NOT use download_ranges: ranged downloads route the network
        I/O through FFmpegFD (ffmpeg, one connection) which gets per-connection
        throttled (~10-20 KiB/s on Indonesian ISPs). Native download with
        concurrent_fragment_downloads=8 opens 8 parallel connections and cuts
        the section locally with ffmpeg -c copy — the throttle is bypassed and
        the local cut never touches the network.
        """
        # Retry-on-WinError-32 loop: the final .part → .mp4 rename can fail on
        # Windows when antivirus / search-indexer briefly locks the file. The
        # re-download is cheap relative to a stuck session, so retry a few times.
        e_download: Exception | None = None
        for attempt in range(1, 4):
            try:
                _run_download(ydl_opts, f"primary-{attempt}")
                return _cut_section(_find_downloaded_file(output_path))
            except Exception as e:
                e_download = e
                msg = str(e)
                rename_locked = (
                    "Unable to rename file" in msg
                    or "WinError 32" in msg
                    or "being used by another process" in msg
                )
                if rename_locked and attempt < 3:
                    log(
                        f"⚠️ Rename lock (WinError 32) on attempt {attempt}/3 — "
                        "file busy (antivirus?), retrying in 5s..."
                    )
                    time.sleep(5)
                    continue
                break  # real failure → fallback path below

        msg = str(e_download)
        log(f"Section download failed: {msg[:200]}")
        if "403" in msg or "Forbidden" in msg:
            raise RuntimeError(
                "YouTube rejected access (HTTP 403). Your cookies may have expired. "
                "Please export fresh cookies while logged into YouTube."
            )

        # Retry with fallback on ANY failure (dead connection, HLS range quirk, etc.):
        # simple format + no download_ranges (full video, cut locally with ffmpeg).
        # IMPORTANT: keep the SAME avc1-1080p preference as the primary — on a
        # throttled link, picking 2160p VP9 (the generic "best" fallback) turns
        # a 60 MB download into a 200 MB one and effectively never finishes.
        log("Retrying with fallback options (simple format + no ranges)...")
        fallback_opts = dict(ydl_opts)
        fallback_opts.pop("download_ranges", None)
        fallback_opts.pop("force_keyframes_at_cuts", None)
        fallback_opts["format"] = (
            "bestvideo[height<=1080][vcodec^=avc1]+bestaudio[acodec^=mp4a]/"
            "bestvideo[height<=1080][vcodec^=avc1]+bestaudio/"
            "bestvideo[height<=1080]+bestaudio/"
            "best[height<=1080]/best"
        )
        download_state["last_log_ts"] = time.monotonic()
        download_state["last_pct"] = None
        download_state["last_detail"] = "(fallback retry)"
        download_state["download_phase_active"] = False
        # Reset watchdog for the fallback attempt
        _abort.clear()
        download_state["first_activity_ts"] = None
        _watchdog_fallback = threading.Thread(
            target=_extraction_watchdog, daemon=True, name="yt-dlp-watchdog-fallback"
        )
        _watchdog_fallback.start()
        try:
            _run_download(fallback_opts, "fallback")
        except Exception as e2:
            msg2 = str(e2)
            log(f"Fallback download also failed: {msg2[:200]}")
            raise RuntimeError(f"Failed to download video section: {msg2}")

        # Fallback downloaded the full video — cut locally (same helper as primary)
        return _cut_section(_find_downloaded_file(output_path))

    try:
        result_path = _do_download()
    finally:
        stop_evt.set()
        hb_thread.join(timeout=2)

    return result_path
