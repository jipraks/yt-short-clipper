"""Session orchestration for the find-highlights phase."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .constants import resolve_output_language
from .helpers import debug_log
from .highlight_finder import find_highlights, parse_requested_ranges
from .srt_parser import extract_transcript_for_highlight, parse_srt
from .subtitle_downloader import download_caption_words, download_subtitle_only

LogFn = Callable[[str], None]


def find_highlights_only(
    url: str,
    num_clips: int,
    subtitle_language: str,
    output_dir: str | Path,
    cookies_path: str,
    ai: dict[str, Any],
    user_direction: str | None = None,
    output_language: str | None = None,
    log: LogFn | None = None,
) -> dict[str, Any]:
    """Phase 1: download subtitle, run AI highlight detection, save session.

    Args:
        ai: dict with keys api_key, base_url, model, system_message (optional),
            temperature (optional).
        user_direction: optional free-text steer from the Create page (time
            range, topic to chase, things to avoid) injected into the prompt.
        output_language: language code for titles/hooks, or "auto"/None to
            follow the video's subtitle language.

    Returns session data dict.
    """
    log = log or debug_log

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(output_dir)
    session_dir = output_dir / "sessions" / timestamp
    session_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = session_dir / "_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    log(f"Session directory: {session_dir}")

    # Step 1: subtitle only
    log(f"Downloading {subtitle_language.upper()} subtitle (no video)...")
    srt_path, video_info = download_subtitle_only(
        url=url,
        subtitle_language=subtitle_language,
        temp_dir=temp_dir,
        cookies_path=cookies_path,
        log=log,
    )

    if not srt_path:
        raise RuntimeError(
            f"No subtitle available for language: {subtitle_language.upper()}. "
            "Try another subtitle language or a video that has subtitles."
        )

    if video_info.get("title"):
        log(f"Video: {video_info['title']}")
    if video_info.get("channel"):
        log(f"Channel: {video_info['channel']}")
    log(f"Subtitle download success: {srt_path}")

    # Step 1b: original-language caption word-timing (for word-by-word captions).
    # Independent of the highlight subtitle language; skipped silently if the
    # video has no original auto-caption track.
    caption_words_path: str | None = None
    try:
        caption_words_path = download_caption_words(
            url=url,
            temp_dir=session_dir,
            cookies_path=cookies_path,
            log=log,
        )
    except Exception as e:
        log(f"Caption word-timing unavailable: {str(e)[:200]}")

    # Step 2: AI highlights
    transcript = parse_srt(srt_path)
    transcript_lines = transcript.count("\n") + 1 if transcript else 0
    log(f"Parsed transcript: {transcript_lines} lines, {len(transcript)} chars")

    # find_highlights() logs the model, endpoint and temperature itself.
    resolved_language = resolve_output_language(output_language, subtitle_language)
    log(f"Writing titles and hooks in {resolved_language}")
    log("Finding highlights with AI...")
    log(f"Requesting {num_clips} clips (AI may return extra for filtering)...")
    if (user_direction or "").strip():
        log(f"Applying AI direction: {' '.join(user_direction.split())[:200]}")
        exact = parse_requested_ranges(user_direction)
        if exact:
            spans = ", ".join(f"{a:.0f}s-{b:.0f}s" for a, b in exact)
            log(f"Exact time range(s) requested, exempt from the 58-120s rule: {spans}")
    highlights, token_usage = find_highlights(
        transcript=transcript,
        video_info=video_info,
        num_clips=num_clips,
        api_key=ai["api_key"],
        base_url=ai.get("base_url", "https://api.openai.com/v1"),
        model=ai["model"],
        system_prompt=ai.get("system_message") or None,
        # None lets find_highlights pick: colder when a direction must be obeyed.
        temperature=ai.get("temperature"),
        user_direction=user_direction,
        output_language=resolved_language,
        log=log,
    )

    if not highlights:
        raise RuntimeError(
            "No valid highlights found. The AI may have failed, or the transcript "
            "is too short. Try a different model or a longer video."
        )

    if token_usage:
        log(
            f"AI token usage: {token_usage.get('prompt_tokens', 0)} prompt + "
            f"{token_usage.get('completion_tokens', 0)} completion"
        )

    log("Extracting transcript text for each highlight...")
    for h in highlights:
        h["transcript_text"] = extract_transcript_for_highlight(
            srt_path, h["start_time"], h["end_time"]
        )

    log(f"Found {len(highlights)} valid highlights")

    session_data = {
        "session_dir": str(session_dir),
        "url": url,
        "srt_path": srt_path,
        "subtitle_language": subtitle_language,
        "user_direction": (user_direction or "").strip() or None,
        "output_language": (output_language or "auto").strip().lower(),
        "output_language_name": resolved_language,
        "caption_words_path": caption_words_path,
        "caption_available": bool(caption_words_path),
        "highlights": highlights,
        "video_info": video_info,
        "token_usage": token_usage,
        "created_at": datetime.now().isoformat(),
        "status": "highlights_found",
    }

    session_data_file = session_dir / "session_data.json"
    with open(session_data_file, "w", encoding="utf-8") as f:
        json.dump(session_data, f, indent=2, ensure_ascii=False)

    log(f"Session data saved to: {session_data_file}")

    return session_data
