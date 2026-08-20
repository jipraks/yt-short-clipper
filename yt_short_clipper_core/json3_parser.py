"""Parse YouTube json3 caption tracks into word-level timing.

json3 is YouTube's timed-text format. For *auto-generated* captions in the
*original* language it carries genuine per-word timestamps, which we use to
build CapCut-style word-by-word captions without Whisper.

Event shape (relevant fields):
    {
      "tStartMs": 6040,            # event start, ms
      "dDurationMs": 5559,         # event duration, ms
      "segs": [
        {"utf8": "Soon ", "tOffsetMs": 0},   # tOffsetMs optional on first seg
        {"utf8": "you ", "tOffsetMs": 392},
        ...
      ]
    }

Rolling-caption artifacts (events whose only seg is a newline, marked with
``aAppend``) carry no real words and are skipped.
"""

import json
from typing import Any

# A single word lasting longer than this (seconds) is almost certainly a gap
# between sentences, not real speech — clamp it so captions don't linger.
_MAX_WORD_DURATION = 1.2
# Fallback duration for the very last word, which has no following word.
_LAST_WORD_DURATION = 0.5


def find_orig_caption_code(automatic_captions: dict[str, Any] | None) -> str | None:
    """Return the original-language auto-caption code (the ``*-orig`` track).

    Only the original-language ASR track carries genuine per-word timing;
    translated tracks have evenly interpolated offsets. Returns None if no
    original track is present.
    """
    if not automatic_captions:
        return None
    for code in automatic_captions.keys():
        if code.endswith("-orig"):
            return code
    return None


def parse_json3_words(path: str) -> list[dict[str, Any]]:
    """Parse a json3 file into a flat, time-ordered word list.

    Returns a list of ``{"word": str, "start": float, "end": float}`` with
    absolute timestamps (seconds) relative to the full source video.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw: list[dict[str, Any]] = []
    for event in data.get("events") or []:
        segs = event.get("segs")
        if not segs:
            continue
        event_start_ms = event.get("tStartMs", 0) or 0
        for seg in segs:
            text = seg.get("utf8", "")
            if not text or not text.strip():
                # Whitespace / newline filler (rolling-window artifact)
                continue
            start_ms = event_start_ms + (seg.get("tOffsetMs") or 0)
            raw.append({"word": text.strip(), "start_ms": start_ms})

    if not raw:
        return []

    # Sort by start time; some events overlap due to rolling captions.
    raw.sort(key=lambda w: w["start_ms"])

    words: list[dict[str, Any]] = []
    for i, w in enumerate(raw):
        start = w["start_ms"] / 1000.0
        if i + 1 < len(raw):
            end = raw[i + 1]["start_ms"] / 1000.0
        else:
            end = start + _LAST_WORD_DURATION
        # Guard against zero/negative spans from duplicate timestamps.
        if end <= start:
            end = start + _LAST_WORD_DURATION
        if end - start > _MAX_WORD_DURATION:
            end = start + _MAX_WORD_DURATION
        words.append({"word": w["word"], "start": start, "end": end})

    return words
