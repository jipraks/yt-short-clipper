"""Hook generation: render hook text as an overlay on the opening seconds of the clip."""

import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

from .helpers import get_ffmpeg_path

LogFn = Callable[[str], None]

_SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

# Default hook style
DEFAULT_HOOK_STYLE = {
    "font_name": "Arial",
    "font_path": "",
    "font_size": 0.054,
    "font_color": "#FFD700",
    "bg_color": "#FFFFFF",
    "corner_radius": 0,
    "position_x": 0.5,
    "position_y": 0.333,
    "duration_seconds": 5.0,
}

DEFAULT_HOOK_DURATION = 5.0


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    return (int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))


def _find_system_font_bold() -> str:
    """Find a bold system font as fallback."""
    if sys.platform == "win32":
        candidates = [
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\segoeui.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]

    for c in candidates:
        if Path(c).exists():
            return c
    return ""


def generate_hook(
    input_video_path: str,
    hook_text: str,
    output_path: str,
    duration: float = DEFAULT_HOOK_DURATION,
    hook_style: dict[str, Any] | None = None,
    log: LogFn | None = None,
) -> str:
    """Overlay hook text on top of the opening seconds of the input video.

    The video keeps playing (and keeps its audio) underneath the text. The
    hook text is shown from t=0 until ``duration`` seconds, then disappears.

    Steps:
    1. Probe the input video resolution
    2. Render the hook text overlay with PIL (transparent PNG)
    3. Burn the overlay onto the video for the first ``duration`` seconds

    Returns the output path.
    """
    log = log or (lambda m: None)
    style = {**DEFAULT_HOOK_STYLE, **(hook_style or {})}
    ffmpeg_path = get_ffmpeg_path()
    temp_dir = Path(output_path).parent

    try:
        duration = float(duration)
    except (TypeError, ValueError):
        duration = DEFAULT_HOOK_DURATION
    if duration <= 0:
        duration = DEFAULT_HOOK_DURATION

    # Step 1: Probe input video resolution
    probe_cmd = [ffmpeg_path, "-i", input_video_path]
    result = subprocess.run(probe_cmd, capture_output=True, text=True, creationflags=_SUBPROCESS_FLAGS)

    res_match = re.search(r"(\d{3,4})x(\d{3,4})", result.stderr)
    if res_match:
        width, height = int(res_match.group(1)), int(res_match.group(2))
    else:
        width, height = 1080, 1920

    # Step 2: Render text overlay with PIL
    log(f"Rendering hook text overlay ({duration:.1f}s)...")
    from PIL import Image, ImageDraw, ImageFont

    font_size_frac = float(style.get("font_size", 0.054))
    font_color_hex = style.get("font_color", "#FFD700")
    bg_color_hex = style.get("bg_color", "#FFFFFF")
    corner_radius = int(style.get("corner_radius", 0))
    pos_x = float(style.get("position_x", 0.5))
    pos_y = float(style.get("position_y", 0.333))
    user_font_path = style.get("font_path") or ""

    # Resolve font
    font_px = max(20, int(font_size_frac * width))
    pil_font = None
    for candidate in [user_font_path, _find_system_font_bold()]:
        if not candidate or not Path(candidate).exists():
            continue
        try:
            pil_font = ImageFont.truetype(candidate, font_px)
            break
        except Exception:
            pass
    if pil_font is None:
        pil_font = ImageFont.load_default()

    font_color_rgb = _hex_to_rgb(font_color_hex)
    bg_color_rgb = _hex_to_rgb(bg_color_hex)

    # Format hook text into lines (3 words per line)
    hook_upper = hook_text.upper()
    words = hook_upper.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        if len(current_line) >= 3:
            lines.append(" ".join(current_line))
            current_line = []
    if current_line:
        lines.append(" ".join(current_line))

    # Calculate line metrics
    padding = max(10, int(font_px * 0.22))
    line_spacing = max(6, int(font_px * 0.25))

    line_metrics = []
    for line in lines:
        try:
            bbox = pil_font.getbbox(line)
        except AttributeError:
            w_t, h_t = pil_font.getsize(line)
            bbox = (0, 0, w_t, h_t)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        line_metrics.append({
            "text": line,
            "bbox": bbox,
            "box_w": text_w + padding * 2,
            "box_h": text_h + padding * 2,
        })

    total_h = sum(m["box_h"] for m in line_metrics)
    if len(line_metrics) > 1:
        total_h += line_spacing * (len(line_metrics) - 1)

    center_x = int(pos_x * width)
    center_y = int(pos_y * height)
    block_top = center_y - total_h // 2

    # Compose overlay image
    overlay_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay_img)

    cur_y = block_top
    for m in line_metrics:
        box_w = m["box_w"]
        box_h = m["box_h"]
        box_x1 = center_x - box_w // 2
        box_y1 = cur_y
        box_x2 = box_x1 + box_w
        box_y2 = box_y1 + box_h

        if corner_radius > 0 and hasattr(draw, "rounded_rectangle"):
            r = min(corner_radius, box_w // 2, box_h // 2)
            draw.rounded_rectangle(
                [box_x1, box_y1, box_x2, box_y2],
                radius=r,
                fill=(*bg_color_rgb, 255),
            )
        else:
            draw.rectangle(
                [box_x1, box_y1, box_x2, box_y2],
                fill=(*bg_color_rgb, 255),
            )

        text_x = box_x1 + padding - m["bbox"][0]
        text_y = box_y1 + padding - m["bbox"][1]
        draw.text(
            (text_x, text_y),
            m["text"],
            font=pil_font,
            fill=(*font_color_rgb, 255),
        )

        cur_y = box_y2 + line_spacing

    overlay_png = str(temp_dir / f"hook_overlay_{int(time.time() * 1000)}.png")
    overlay_img.save(overlay_png, "PNG")

    # Step 3: Overlay text onto the video for the first `duration` seconds.
    # The underlying video keeps playing and keeps its audio track.
    log("Burning hook text onto video...")
    overlay_cmd = [
        ffmpeg_path, "-y",
        "-i", input_video_path,
        "-i", overlay_png,
        "-filter_complex",
        f"[0:v][1:v]overlay=0:0:enable='lte(t,{duration})'[v]",
        "-map", "[v]",
        "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        output_path,
    ]
    result = subprocess.run(overlay_cmd, capture_output=True, text=True, creationflags=_SUBPROCESS_FLAGS)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to overlay hook text: {result.stderr[-500:]}")

    # Cleanup temp files
    try:
        Path(overlay_png).unlink(missing_ok=True)
    except Exception:
        pass

    log("Hook generation complete")
    return output_path
