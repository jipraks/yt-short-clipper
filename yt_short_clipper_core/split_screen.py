"""Split-screen composition: stack two videos vertically into one 9:16 frame.

Layout (default): main video on TOP (host), second video/webcam on BOTTOM
(narasumber/reaction). Ratio 55:45 with a thin gold divider between the panes,
matching the app's gold accent (#fbbf24).

Uses ffmpeg ``vstack`` — the same filter proven in the split-screen spike.
"""

import subprocess
import sys
from pathlib import Path
from typing import Callable

from .helpers import get_ffmpeg_path

LogFn = Callable[[str], None]

_SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920

# Default pane split: top gets 55% of the height, bottom gets the rest minus
# the divider. Sums to exactly 1920.
TOP_RATIO = 0.55
DIVIDER_PX = 6
DIVIDER_COLOR = "0xFBBF24"  # gold #fbbf24


def _ffprobe_path() -> str:
    """ffprobe usually sits next to ffmpeg; fall back to PATH."""
    ffmpeg = Path(get_ffmpeg_path())
    exe_name = "ffprobe.exe" if sys.platform.startswith("win") else "ffprobe"
    sibling = ffmpeg.parent / exe_name
    if sibling.exists():
        return str(sibling)
    import shutil

    return shutil.which("ffprobe") or "ffprobe"


def _probe_duration(video_path: str) -> float:
    """Return media duration in seconds via ffprobe."""
    cmd = [
        _ffprobe_path(), "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0", video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, creationflags=_SUBPROCESS_FLAGS)
    try:
        return float(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return 0.0


def _probe_has_audio(video_path: str) -> bool:
    """True if the file has at least one audio stream."""
    cmd = [
        _ffprobe_path(), "-v", "error",
        "-select_streams", "a",
        "-show_entries", "stream=codec_type",
        "-of", "csv=p=0", video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, creationflags=_SUBPROCESS_FLAGS)
    return "audio" in result.stdout


def combine_split_screen(
    main_video_path: str,
    second_video_path: str,
    output_path: str,
    top_ratio: float = TOP_RATIO,
    log: LogFn | None = None,
) -> str:
    """Stack ``main_video_path`` (top) over ``second_video_path`` (bottom) as 9:16.

    - Each pane is padded (black bars) to keep the full source visible.
    - A thin gold divider separates the panes.
    - Both audio tracks are mixed (amix); missing audio in either file is
      tolerated by falling back to whichever track exists.
    - Output duration follows the MAIN video; if the second video is shorter
      it is looped. If it is longer it is trimmed.

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

    filter_parts = [
        # Top pane: fit inside top_h, centered (letterbox/pillarbox with black bars)
        f"[0:v]scale={OUTPUT_WIDTH}:{top_h}:force_original_aspect_ratio=decrease,"
        f"pad={OUTPUT_WIDTH}:{top_h}:(ow-iw)/2:(oh-ih)/2,setsar=1[top]",
        # Bottom pane: same treatment, then draw the gold divider on its top edge
        f"[1:v]scale={OUTPUT_WIDTH}:{bottom_h}:force_original_aspect_ratio=decrease,"
        f"pad={OUTPUT_WIDTH}:{bottom_h}:(ow-iw)/2:(oh-ih)/2,"
        f"drawbox=x=0:y=0:w=iw:h={DIVIDER_PX}:color={DIVIDER_COLOR}@1:t=fill,setsar=1[bottom]",
        "[top][bottom]vstack=inputs=2,format=yuv420p[v]",
    ]

    if main_has_audio and second_has_audio:
        filter_parts.append("[0:a]aresample=48000[a0];[1:a]aresample=48000[a1];[a0][a1]amix=inputs=2:duration=longest:dropout_transition=0[a]")
        audio_map = ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
    elif main_has_audio:
        filter_parts.append("[0:a]aresample=48000,anull[a]")
        audio_map = ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
    elif second_has_audio:
        filter_parts.append("[1:a]aresample=48000,anull[a]")
        audio_map = ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
    else:
        audio_map = ["-an"]

    cmd = [
        ffmpeg_path,
        *inputs,
        "-filter_complex", ";".join(filter_parts),
        "-map", "[v]",
        *audio_map,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
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