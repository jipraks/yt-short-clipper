"""Watermark overlay: logo image and/or credit text burned into video."""

import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from .helpers import get_ffmpeg_path
from .gpu import build_video_enc_args

LogFn = Callable[[str], None]

_SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def apply_watermark(
    input_video_path: str,
    output_path: str,
    watermark: dict[str, Any] | None = None,
    credit_watermark: dict[str, Any] | None = None,
    log: LogFn | None = None,
    gpu_config: dict[str, Any] | None = None,
) -> str:
    """Apply logo watermark and/or credit text overlay to video.

    watermark keys: image_path, position_x, position_y, opacity, scale
    credit_watermark keys: text, color, font_size, opacity, position_x, position_y

    Returns the output path.
    """
    log = log or (lambda m: None)
    ffmpeg_path = get_ffmpeg_path()

    has_logo = watermark and watermark.get("image_path") and Path(watermark["image_path"]).exists()
    has_credit = credit_watermark and credit_watermark.get("text")

    if not has_logo and not has_credit:
        log("No watermark configured, skipping")
        import shutil
        shutil.copy2(input_video_path, output_path)
        return output_path

    # Select video encoder based on GPU config
    video_enc_args = build_video_enc_args(gpu_config)
    if gpu_config and gpu_config.get("available"):
        log(f"Using GPU encoder: {gpu_config.get('name')} (preset={gpu_config.get('preset')})")
    else:
        log(f"Using CPU encoder: libx264")

    # Build ffmpeg filter chain with explicit labels and a fallback font
    inputs = ["-i", input_video_path]
    filter_parts = []

    # Determine a safe font path (fallback to DejaVuSans if available)
    default_font = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    font_path = default_font if Path(default_font).exists() else None

    if has_logo:
        logo_path = watermark["image_path"]
        pos_x = watermark.get("position_x", 0.85)
        pos_y = watermark.get("position_y", 0.05)
        opacity = watermark.get("opacity", 0.8)
        scale = watermark.get("scale", 0.15)

        inputs.extend(["-i", logo_path])

        # Scale logo relative to video width, then overlay on base video
        logo_filter = (
            f"[1:v]format=rgba,colorchannelmixer=aa={opacity},"
            f"scale=iw*{scale}:-1[logo];"
            f"[0:v][logo]overlay=W*{pos_x}-overlay_w/2:H*{pos_y}-overlay_h/2[watermarked]"
        )
        filter_parts.append(logo_filter)

    if has_credit:
        text = credit_watermark["text"]
        color = credit_watermark.get("color", "#FFFFFF")
        font_size = credit_watermark.get("font_size", 24)
        opacity = credit_watermark.get("opacity", 0.7)
        pos_x = credit_watermark.get("position_x", 0.03)
        pos_y = credit_watermark.get("position_y", 0.92)

        # Convert hex color to ffmpeg format (remove #)
        ff_color = color.lstrip("#")
        # Calculate alpha as hex (two‑digit)
        alpha_hex = format(int(opacity * 255), "02x")
        # Escape special characters for ffmpeg drawtext
        escaped_text = text.replace("'", "\\'").replace(":", "\\:")

        # Choose the correct input label: if logo was added we have [watermarked], otherwise base is [0:v]
        input_label = "[watermarked]" if has_logo else "[0:v]"
        # Truncate overly long credit text to avoid overflow
        max_len = 80
        display_text = text if len(text) <= max_len else text[:max_len-3] + "..."
        # Escape for ffmpeg
        escaped_display = display_text.replace("'", "\\'").replace(":", "\\:")
        # Build drawtext filter with background box for readability
        fontfile_part = f":fontfile={font_path}" if font_path else ""
        credit_filter = (
            f"{input_label}drawtext="
            f"text='{escaped_display}':"
            f"fontsize={font_size}:"
            f"fontcolor=0x{ff_color}{alpha_hex}{fontfile_part}:"
            f"x=w*{pos_x}:y=h*{pos_y}:"
            f"box=1:boxcolor=black@0.5:boxborderw=5:"
            f"shadowcolor=black@0.5:shadowx=1:shadowy=1"
        )
        filter_parts.append(credit_filter)

    filter_complex = ";".join(filter_parts)

    log("Applying watermark overlay...")
    cmd = [
        ffmpeg_path, "-y",
        *inputs,
        "-filter_complex", filter_complex,
        *video_enc_args,
        "-c:a", "copy",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, creationflags=_SUBPROCESS_FLAGS)

    if result.returncode != 0:
        raise RuntimeError(f"Watermark overlay failed: {result.stderr[-500:]}")

    log("Watermark overlay complete")
    return output_path
