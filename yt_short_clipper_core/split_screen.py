"""Split-screen composition: stack two videos vertically into one 9:16 frame.

Layout (default): main video on TOP (host) reframed to a face-tracked portrait
pane (80%), local webcam/second video on BOTTOM (20%) as a landscape strip.
A thin gold divider separates the panes, matching the app's gold accent
(#fbbf24).

Uses ffmpeg ``vstack`` — the same filter proven in the split-screen spike.
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import Callable, Any

from .helpers import get_ffmpeg_path

LogFn = Callable[[str], None]

_SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920

# Default pane split: top gets 80% of the height (main video), bottom gets
# the rest minus the divider. Sums to exactly 1920.
TOP_RATIO = 0.80
DIVIDER_PX = 6
DIVIDER_COLOR = "0xFBBF24"  # gold #fbbf24


# Media probe cache: probe each file once per process.
_probe_cache: dict[str, tuple[float, bool]] = {}


def _probe_media(video_path: str) -> tuple[float, bool]:
    """Return ``(duration_seconds, has_audio)`` using only the bundled ffmpeg.

    ffprobe is NOT shipped in the portable bundle, so we parse ffmpeg's
    ``-i`` stderr instead (the classic no-ffprobe trick). ffmpeg exits
    non-zero here because we give it no output file — that is expected, so
    only stderr is parsed.
    """
    cached = _probe_cache.get(video_path)
    if cached is not None:
        return cached

    ffmpeg = Path(get_ffmpeg_path())
    cmd = [str(ffmpeg), "-hide_banner", "-i", video_path]
    result = subprocess.run(cmd, capture_output=True, text=True, creationflags=_SUBPROCESS_FLAGS)
    stderr = result.stderr or ""

    duration = 0.0
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", stderr)
    if m:
        h, mi, s = m.groups()
        duration = int(h) * 3600 + int(mi) * 60 + float(s)

    has_audio = bool(
        re.search(r"Stream\s+#\d+:\d+(?:\[[^\]]*\])?(?:\([^)]*\))?:\s*Audio:", stderr)
    )

    _probe_cache[video_path] = (duration, has_audio)
    return duration, has_audio


def _probe_duration(video_path: str) -> float:
    return _probe_media(video_path)[0]


def _probe_has_audio(video_path: str) -> bool:
    return _probe_media(video_path)[1]


def combine_split_screen(
    main_video_path: str,
    second_video_path: str,
    output_path: str,
    top_ratio: float = TOP_RATIO,
    main_volume: float = 1.0,
    second_volume: float = 1.0,
    log: LogFn | None = None,
    gpu_config: dict[str, Any] | None = None,
    position: str = "bottom",
) -> str:
    """Stack ``main_video_path`` (top) over ``second_video_path`` (bottom) as 9:16.

    - Top pane expects a face-tracked portrait crop (1080x{top_h}) that fills
      the pane edge-to-edge — typically produced by ``convert_to_portrait_pane``.
      Any other aspect is letterboxed to fit (graceful fallback).
    - Bottom pane is COVER-CROPPED to a landscape strip (1080x{bottom_h}) so a
      16:9 or even 9:16 webcam fills the strip with no bars.
    - A thin gold divider separates the panes.
    - Both audio tracks are mixed (amix); missing audio in either file is
      tolerated by falling back to whichever track exists.
    - Volume per-input can be set (0.0-1.0) to balance main vs. second audio.
    - Output duration follows the MAIN video; if the second video is shorter
      it is looped. If it is longer it is trimmed.
    - ``position``: "bottom" (default) = main video on top, webcam on bottom.
                    "top" = webcam on top, main video on bottom (portrait+face tracking).

    Returns the output path.
    """
    log = log or (lambda m: None)
    ffmpeg_path = get_ffmpeg_path()

    main_dur = _probe_duration(main_video_path)
    second_dur = _probe_duration(second_video_path)
    log(f"Split screen: main={main_dur:.1f}s top, second={second_dur:.1f}s bottom")
    if main_dur <= 0:
        raise RuntimeError("Cannot read duration of main video")

    top_h = int(round(OUTPUT_HEIGHT * top_ratio))
    # The divider is drawn INSIDE the bottom pane's top edge, so the pane
    # heights must sum to the full output height (divider overlays 6px).
    bottom_h = OUTPUT_HEIGHT - top_h

    main_has_audio = _probe_has_audio(main_video_path)
    second_has_audio = _probe_has_audio(second_video_path)

    inputs = ["-y", "-i", main_video_path]
    # stream_loop makes a short second video repeat; -t on the output trims it.
    inputs += ["-stream_loop", "-1", "-i", second_video_path]

    # Position determines stacking order:
    # - "bottom" (default): [0:v]=main on top, [1:v]=webcam on bottom
    # - "top": [1:v]=webcam on top, [0:v]=main on bottom (portrait+face tracking)
    webcam_on_top = position == "top"

    if webcam_on_top:
        # Webcam on top (landscape strip), main video on bottom (portrait)
        # Top pane = webcam (landscape cover-crop)
        filter_parts = [
            f"[1:v]scale={OUTPUT_WIDTH}:{top_h}:force_original_aspect_ratio=increase,"
            f"crop={OUTPUT_WIDTH}:{top_h},"
            f"drawbox=x=0:y=0:w=iw:h={DIVIDER_PX}:color={DIVIDER_COLOR}@1:t=fill,setsar=1[top]",
            # Bottom pane = main video (portrait, fit + center)
            f"[0:v]scale={OUTPUT_WIDTH}:{bottom_h}:force_original_aspect_ratio=decrease,"
            f"pad={OUTPUT_WIDTH}:{bottom_h}:(ow-iw)/2:(oh-ih)/2,setsar=1[bottom]",
            "[top][bottom]vstack=inputs=2,format=yuv420p[v]",
        ]
    else:
        # Default: main video on top (portrait), webcam on bottom (landscape strip)
        filter_parts = [
            # Top pane: fills the pane when the input is already the pane aspect
            # (1080x{top_h} face-tracked portrait). Otherwise fit + center with
            # black bars as a graceful fallback.
            f"[0:v]scale={OUTPUT_WIDTH}:{top_h}:force_original_aspect_ratio=decrease,"
            f"pad={OUTPUT_WIDTH}:{top_h}:(ow-iw)/2:(oh-ih)/2,setsar=1[top]",
            # Bottom pane: COVER-CROP into a landscape strip (any aspect fills the
            # 1080x{bottom_h} strip, no bars), then draw the gold divider on its
            # top edge.
            f"[1:v]scale={OUTPUT_WIDTH}:{bottom_h}:force_original_aspect_ratio=increase,"
            f"crop={OUTPUT_WIDTH}:{bottom_h},"
            f"drawbox=x=0:y=0:w=iw:h={DIVIDER_PX}:color={DIVIDER_COLOR}@1:t=fill,setsar=1[bottom]",
            "[top][bottom]vstack=inputs=2,format=yuv420p[v]",
        ]

    if main_has_audio and second_has_audio:
        filter_parts.append(f"[0:a]volume={main_volume:.2f},aresample=48000[a0];[1:a]volume={second_volume:.2f},aresample=48000[a1];[a0][a1]amix=inputs=2:duration=longest:dropout_transition=0[a]")
        audio_map = ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
    elif main_has_audio:
        filter_parts.append(f"[0:a]volume={main_volume:.2f},aresample=48000,anull[a]")
        audio_map = ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
    elif second_has_audio:
        filter_parts.append(f"[1:a]volume={second_volume:.2f},aresample=48000,anull[a]")
        audio_map = ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
    else:
        audio_map = ["-an"]

    # Select video encoder based on GPU config
    gpu_enabled = gpu_config and gpu_config.get("enabled", False) if gpu_config else False
    enc_name = gpu_config.get("encoder") if gpu_enabled else None
    enc_preset = gpu_config.get("preset") if gpu_enabled else None

    def build_video_enc_args(name: str | None, preset: str | None) -> list[str]:
        if name == "h264_nvenc":
            args = ["-c:v", name]
            if preset:
                args += ["-preset", preset]
            args += ["-rc", "vbr", "-cq", "23"]
            return args
        if name:
            args = ["-c:v", name]
            if preset:
                args += ["-preset", preset]
            return args
        return ["-c:v", "libx264", "-preset", "fast", "-crf", "18"]

    video_enc_args = build_video_enc_args(enc_name, enc_preset)
    if enc_name:
        log(f"Using GPU encoder: {enc_name} (preset={enc_preset})")
    else:
        log(f"Using CPU encoder: libx264")

    cmd = [
        ffmpeg_path,
        *inputs,
        "-filter_complex", ";".join(filter_parts),
        "-map", "[v]",
        *audio_map,
        *video_enc_args,
        "-t", f"{main_dur:.3f}",
        "-movflags", "+faststart",
        output_path,
    ]

    log(f"Composing split screen ({OUTPUT_WIDTH}x{OUTPUT_HEIGHT}, top {top_ratio:.0%})...")
    result = subprocess.run(cmd, capture_output=True, text=True, creationflags=_SUBPROCESS_FLAGS)

    if result.returncode != 0:
        raise RuntimeError(f"Split screen composition failed: {result.stderr[-500:]}")

    log("Split screen composition complete")
    return output_path