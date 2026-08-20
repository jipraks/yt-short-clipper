"""Process selected highlights: download → portrait → hook → caption → watermark."""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .video_processor import download_video_section
from .portrait import convert_to_portrait, convert_to_portrait_centered
from .hook_generator import generate_hook
from .caption_generator import generate_captions_from_words
from .srt_parser import parse_timestamp
from .watermark import apply_watermark

LogFn = Callable[[str], None]


def _load_caption_words(session_path: Path, log: LogFn) -> list[dict[str, Any]]:
    """Load the full-video word-timing list saved during the find-highlights phase.

    Returns an empty list when the video had no original subtitle track (in
    which case captions are skipped but clips are still produced).
    """
    words_file = session_path / "words.json"
    if not words_file.exists():
        log("No words.json in session — captions will be skipped for all clips")
        return []
    try:
        with open(words_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log(f"Failed to read words.json: {str(e)[:200]} — captions will be skipped")
        return []


def _words_for_clip(
    all_words: list[dict[str, Any]],
    clip_start: float,
    clip_end: float,
) -> list[dict[str, Any]]:
    """Slice words overlapping [clip_start, clip_end] and shift to clip-relative time."""
    sliced: list[dict[str, Any]] = []
    for w in all_words:
        if w["end"] < clip_start or w["start"] > clip_end:
            continue
        rel_start = max(0.0, w["start"] - clip_start)
        rel_end = w["end"] - clip_start
        if rel_end <= 0:
            continue
        sliced.append({"word": w["word"], "start": rel_start, "end": rel_end})
    return sliced


def _run_portrait(input_path: str, output_path: str, options: dict[str, Any], log: LogFn) -> str:
    """Run portrait conversion — face-tracked or centered, based on reframeMode."""
    reframe_mode = options.get("reframeMode", "face")
    if reframe_mode == "centered":
        background = options.get("centeredBackground", "black")
        return convert_to_portrait_centered(input_path, output_path, background=background, log=log)
    return convert_to_portrait(input_path, output_path, log)


def process_selected_highlights(
    url: str,
    highlights: list[dict[str, Any]],
    session_dir: str,
    options: dict[str, Any],
    ai: dict[str, Any],
    log: LogFn,
) -> dict[str, Any]:
    """Process selected highlights and return output info.

    options keys: addCaptions, addHook, addWatermark, addCreditWatermark
    ai keys: api_key, base_url, model, hook_style (dict, includes duration_seconds)
    """
    session_path = Path(session_dir)
    clips_dir = session_path / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    temp_dir = session_path / "_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    total = len(highlights)
    results: list[dict[str, Any]] = []

    add_hook = options.get("addHook", False)
    add_captions = options.get("addCaptions", False)
    add_watermark = options.get("addWatermark", False)
    add_credit_watermark = options.get("addCreditWatermark", False)

    # Word-level caption timing for the full source video (from the original
    # subtitle track). Empty if unavailable — captions are then skipped.
    caption_words = _load_caption_words(session_path, log) if add_captions else []
    if add_captions and not caption_words:
        log("Captions requested but no subtitle word-timing available — clips will have no captions")

    for i, h in enumerate(highlights, 1):
        log(f"Processing clip {i}/{total}: {h.get('title', 'Untitled')}")

        # Use highlight_index from the highlight data if available (for dedup)
        highlight_index = h.get("_highlight_index", i - 1)

        # Check if this highlight was already processed
        clip_folder = clips_dir / f"clip_{highlight_index:03d}"
        existing_master = clip_folder / "master.mp4"
        if existing_master.exists():
            log(f"[{i}/{total}] Already processed (clip_{highlight_index:03d}), skipping")
            results.append({
                "clip_index": highlight_index,
                "output_path": str(existing_master),
                "title": h.get("title", ""),
                "skipped": True,
            })
            continue

        section_path = str(temp_dir / f"section_{i:03d}.mp4")

        # Step 1: Download video section
        log(f"[{i}/{total}] Downloading video section {h['start_time']} -> {h['end_time']}...")
        video_path = download_video_section(
            url=url,
            start_time=h["start_time"],
            end_time=h["end_time"],
            output_path=section_path,
            log=log,
        )
        log(f"[{i}/{total}] Section downloaded: {video_path}")

        # Step 2: Portrait conversion
        portrait_path = str(temp_dir / f"portrait_{i:03d}.mp4")
        video_path = _run_portrait(video_path, portrait_path, options, log)
        log(f"[{i}/{total}] Portrait conversion complete")

        # Step 3: Hook generation (text overlay on the opening seconds)
        if add_hook:
            hook_text = h.get("hook_text", "")
            if hook_text:
                hook_style = ai.get("hook_style") or {}
                hook_duration = hook_style.get("duration_seconds", 5.0)

                hook_output_path = str(temp_dir / f"hooked_{i:03d}.mp4")
                video_path = generate_hook(
                    input_video_path=video_path,
                    hook_text=hook_text,
                    output_path=hook_output_path,
                    duration=hook_duration,
                    hook_style=hook_style,
                    log=log,
                )
                log(f"[{i}/{total}] Hook generation complete")
            else:
                log(f"[{i}/{total}] No hook text, skipping hook generation")
        else:
            log(f"[{i}/{total}] Hook generation skipped (disabled)")

        # Step 4: Caption generation (word-by-word, from original subtitle track)
        clip_had_captions = False
        if add_captions and caption_words:
            clip_start = parse_timestamp(h["start_time"])
            clip_end = parse_timestamp(h["end_time"])
            clip_words = _words_for_clip(caption_words, clip_start, clip_end)

            if clip_words:
                caption_output_path = str(temp_dir / f"captioned_{i:03d}.mp4")
                video_path = generate_captions_from_words(
                    input_video_path=video_path,
                    output_path=caption_output_path,
                    words=clip_words,
                    log=log,
                )
                clip_had_captions = True
                log(f"[{i}/{total}] Caption generation complete ({len(clip_words)} words)")
            else:
                log(f"[{i}/{total}] No subtitle words in this clip's range — captions skipped")
        elif add_captions:
            log(f"[{i}/{total}] Caption generation skipped (no subtitle word-timing)")
        else:
            log(f"[{i}/{total}] Caption generation skipped (disabled)")

        # Step 5: Watermark overlay (logo + credit text)
        if add_watermark or add_credit_watermark:
            wm_config = ai.get("watermark") if add_watermark else None
            credit_config = ai.get("credit_watermark") if add_credit_watermark else None

            watermark_output_path = str(temp_dir / f"watermarked_{i:03d}.mp4")
            video_path = apply_watermark(
                input_video_path=video_path,
                output_path=watermark_output_path,
                watermark=wm_config,
                credit_watermark=credit_config,
                log=log,
            )
            log(f"[{i}/{total}] Watermark overlay complete")
        else:
            log(f"[{i}/{total}] Watermark overlay skipped (disabled)")

        # Save the final video as output
        clip_folder = clips_dir / f"clip_{highlight_index:03d}"
        clip_folder.mkdir(parents=True, exist_ok=True)
        output_file = clip_folder / "master.mp4"
        shutil.copy2(video_path, output_file)

        # Save metadata
        data = {
            "highlight_index": highlight_index,
            "title": h.get("title", "Untitled"),
            "hook_text": h.get("hook_text", ""),
            "start_time": h["start_time"],
            "end_time": h["end_time"],
            "duration_seconds": h.get("duration_seconds", 0),
            "has_hook": add_hook and bool(h.get("hook_text")),
            "has_captions": clip_had_captions,
            "youtube_title": h.get("title", ""),
            "youtube_description": h.get("description", ""),
            "processed_at": datetime.now().isoformat(),
        }
        with open(clip_folder / "data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        log(f"[{i}/{total}] Clip saved: {output_file}")
        results.append({
            "clip_index": highlight_index,
            "output_path": str(output_file),
            "title": h.get("title", ""),
        })

        # Cleanup temp files for this clip
        for temp_file in temp_dir.glob(f"*_{i:03d}.*"):
            try:
                temp_file.unlink()
            except Exception:
                pass

    # Update session status
    session_data_file = session_path / "session_data.json"
    if session_data_file.exists():
        with open(session_data_file, "r", encoding="utf-8") as f:
            session_data = json.load(f)
        session_data["status"] = "completed"
        session_data["completed_at"] = datetime.now().isoformat()
        session_data["clips_processed"] = total

        # Track which highlight indices have been processed
        processed_indices = session_data.get("processed_highlights", [])
        for r in results:
            idx = r.get("clip_index")
            if idx is not None and idx not in processed_indices and not r.get("skipped"):
                processed_indices.append(idx)
        session_data["processed_highlights"] = sorted(set(processed_indices))

        with open(session_data_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

    log(f"All {total} clips processed successfully!")

    return {
        "session_dir": session_dir,
        "clips_dir": str(clips_dir),
        "total_clips": total,
        "results": results,
    }
