"""Caption generation: build word-by-word ASS captions from word-level timing
(sourced from the YouTube original-language subtitle) and burn them into video."""

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

from .helpers import get_ffmpeg_path

LogFn = Callable[[str], None]

_SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def _format_ass_time(seconds: float) -> str:
    """Convert seconds to ASS time format H:MM:SS.cc"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centisecs = int((seconds % 1) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"


def _create_ass_subtitle(transcript: SimpleNamespace, output_path: str, time_offset: float = 0) -> None:
    """Create ASS subtitle file with CapCut-style word-by-word highlighting."""

    ass_content = """[Script Info]
Title: Auto-generated captions
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,65,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,50,50,400,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events = []

    if transcript.words:
        # Word-level: group into chunks of 4 words, highlight each word in turn
        chunk_size = 4
        words = transcript.words

        for i in range(0, len(words), chunk_size):
            chunk = words[i:i + chunk_size]
            if not chunk:
                continue

            for j, current_word in enumerate(chunk):
                word_start = current_word.start + time_offset
                word_end = current_word.end + time_offset

                text_parts = []
                for k, w in enumerate(chunk):
                    word_text = w.word.strip().upper()
                    if k == j:
                        # Yellow highlight for current word (BGR: &H00FFFF)
                        text_parts.append(f"{{\\c&H00FFFF&}}{word_text}{{\\c&HFFFFFF&}}")
                    else:
                        text_parts.append(word_text)

                text = " ".join(text_parts)
                events.append({"start": _format_ass_time(word_start), "end": _format_ass_time(word_end), "text": text})

    elif transcript.segments:
        # Fallback: segment-level
        for segment in transcript.segments:
            start = segment.get("start", 0) + time_offset
            end = segment.get("end", 0) + time_offset
            text = segment.get("text", "").strip().upper()
            if text:
                events.append({"start": _format_ass_time(start), "end": _format_ass_time(end), "text": text})

    for event in events:
        ass_content += f"Dialogue: 0,{event['start']},{event['end']},Default,,0,0,0,,{event['text']}\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_content)


def generate_captions_from_words(
    input_video_path: str,
    output_path: str,
    words: list[dict[str, Any]],
    log: LogFn | None = None,
) -> str:
    """Burn word-by-word captions into a video from pre-computed word timing.

    Args:
        words: list of ``{"word": str, "start": float, "end": float}`` with
            timestamps already relative to this clip (t=0 at clip start).

    Returns the output path. If ``words`` is empty the input is copied through
    unchanged (caller treats this as "no captions").
    """
    log = log or (lambda m: None)

    if not words:
        log("No caption words for this clip — skipping captions")
        import shutil
        shutil.copy2(input_video_path, output_path)
        return output_path

    ffmpeg_path = get_ffmpeg_path()
    temp_dir = Path(output_path).parent

    transcript = SimpleNamespace(
        words=[SimpleNamespace(word=w["word"], start=w["start"], end=w["end"]) for w in words],
        segments=[],
    )

    # Step 1: Generate ASS subtitle
    log("Generating subtitle file...")
    ass_file = str(temp_dir / "captions.ass")
    _create_ass_subtitle(transcript, ass_file, time_offset=0)

    # Step 2: Burn subtitles into video
    log("Burning captions into video...")
    ass_path_escaped = ass_file.replace("\\", "/").replace(":", "\\:")

    burn_cmd = [
        ffmpeg_path, "-y",
        "-i", input_video_path,
        "-vf", f"ass='{ass_path_escaped}'",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "copy",
        output_path,
    ]
    result = subprocess.run(burn_cmd, capture_output=True, text=True, creationflags=_SUBPROCESS_FLAGS)

    # Clean up ASS file
    try:
        os.unlink(ass_file)
    except Exception:
        pass

    if result.returncode != 0:
        raise RuntimeError(f"Caption burn-in failed: {result.stderr[-500:]}")

    log("Caption generation complete")
    return output_path
