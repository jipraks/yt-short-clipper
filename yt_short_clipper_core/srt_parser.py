"""SRT subtitle parsing and timestamp helpers."""

import re

_SRT_PATTERN = r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\n|\Z)"


def parse_timestamp(ts: str) -> float:
    """Convert an SRT timestamp (HH:MM:SS,mmm) to seconds."""
    ts = ts.replace(",", ".")
    parts = ts.split(":")
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])


def parse_srt(srt_path: str) -> str:
    """Parse an SRT file into a timestamped transcript string."""
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()

    matches = re.findall(_SRT_PATTERN, content, re.DOTALL)

    lines = []
    for _idx, start, end, text in matches:
        clean_text = text.replace("\n", " ").strip()
        lines.append(f"[{start} - {end}] {clean_text}")

    return "\n".join(lines)


def extract_transcript_for_highlight(srt_path: str, start_time: str, end_time: str) -> str:
    """Extract subtitle text overlapping a highlight's time range."""
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()

    matches = re.findall(_SRT_PATTERN, content, re.DOTALL)

    start_sec = parse_timestamp(start_time)
    end_sec = parse_timestamp(end_time)

    lines = []
    for _idx, start, end, text in matches:
        sub_start = parse_timestamp(start)
        sub_end = parse_timestamp(end)

        if sub_end >= start_sec and sub_start <= end_sec:
            clean_text = text.replace("\n", " ").strip()
            if clean_text:
                lines.append(clean_text)

    return " ".join(lines)
