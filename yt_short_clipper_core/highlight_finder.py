"""AI highlight detection from a transcript via OpenAI-compatible API."""

import json
import re
import time
from typing import Any, Callable

from .constants import SAME_AS_TRANSCRIPT
from .helpers import debug_log
from .prompts import (
    DEFAULT_HIGHLIGHT_PROMPT,
    USER_DIRECTION_BLOCK,
    USER_DIRECTION_REMINDER,
)
from .srt_parser import parse_timestamp

LogFn = Callable[[str], None]

# Upper bound on the free-text direction we forward to the model. The UI caps
# input at 1000 chars; this is the backend guard for CLI/older callers.
MAX_USER_DIRECTION_CHARS = 2000

# Sampling temperature. Without a direction, variety is welcome. With one,
# adherence matters more than creativity: at 1.0 the same direction was followed
# on one run and ignored on the next, so directed runs sample much colder.
DEFAULT_TEMPERATURE = 1.0
DIRECTED_TEMPERATURE = 0.3

# Placeholders the prompt template owns — stripped from the user's text so a
# direction can't smuggle a second transcript (or blank one out) into the prompt.
_PLACEHOLDER_RE = re.compile(
    r"\{(?:num_clips|video_context|transcript|user_direction|output_language)\}"
)

# The fences the direction is wrapped in. Stripped from the user text so it
# cannot close its own block and speak as the prompt.
_DELIMITER_RE = re.compile(r"---\s*USER DIRECTION (?:START|END)\s*---", re.IGNORECASE)

# "2:00 - 2:50", "dari 21:30 sampai 22:25", "1:05:00 s/d 1:06:30". Only pairs of
# colon-formatted clock times count, so prose like "60-120 detik" cannot match.
_TIME_RANGE_RE = re.compile(
    r"(\d{1,2}:\d{2}(?::\d{2})?)"
    r"\s*(?:-|–|—|s/d|sd|sampai|hingga|ke|to|until)\s*"
    r"(\d{1,2}:\d{2}(?::\d{2})?)",
    re.IGNORECASE,
)

# How far a returned segment may sit from the range the user asked for and still
# count as "the one they asked for". Models snap to subtitle cue boundaries, so
# an exact string match would almost never hold.
RANGE_MATCH_TOLERANCE_SECONDS = 8.0


def _clock_to_seconds(value: str) -> float:
    """"2:50" -> 170.0, "1:05:00" -> 3900.0."""
    parts = [int(p) for p in value.split(":")]
    if len(parts) == 2:
        return float(parts[0] * 60 + parts[1])
    return float(parts[0] * 3600 + parts[1] * 60 + parts[2])


def parse_requested_ranges(user_direction: str | None) -> list[tuple[float, float]]:
    """Clock ranges the user spelled out, as (start, end) seconds pairs.

    These are exempt from the 58-120s duration filter: the user asked for that
    exact span, so a 50-second clip is the correct answer rather than a reject.
    """
    ranges: list[tuple[float, float]] = []
    for raw_start, raw_end in _TIME_RANGE_RE.findall(sanitize_direction(user_direction)):
        start, end = _clock_to_seconds(raw_start), _clock_to_seconds(raw_end)
        if end > start:
            ranges.append((start, end))
    return ranges


def _matches_requested_range(
    start: float,
    end: float,
    ranges: list[tuple[float, float]],
) -> bool:
    tol = RANGE_MATCH_TOLERANCE_SECONDS
    return any(abs(start - a) <= tol and abs(end - b) <= tol for a, b in ranges)


def sanitize_direction(user_direction: str | None) -> str:
    """Clean a user's free-text direction for prompt embedding, or "" if empty."""
    text = (user_direction or "").strip()
    if not text:
        return ""

    text = _PLACEHOLDER_RE.sub("", text)
    # Keep the text from closing its own delimiter and escaping the block.
    text = _DELIMITER_RE.sub("", text).strip()
    if not text:
        return ""

    if len(text) > MAX_USER_DIRECTION_CHARS:
        text = text[:MAX_USER_DIRECTION_CHARS].rstrip() + " ..."

    return text


def build_direction_block(user_direction: str | None) -> str:
    """The full direction section, or "" if there is no direction."""
    text = sanitize_direction(user_direction)
    return USER_DIRECTION_BLOCK.replace("{direction}", text) if text else ""


def build_direction_reminder(user_direction: str | None) -> str:
    """The short re-anchor appended after the transcript, or "" if no direction."""
    text = sanitize_direction(user_direction)
    return USER_DIRECTION_REMINDER.replace("{direction}", text) if text else ""


def _provider_error_detail(e: Exception) -> str:
    """Best-effort raw error payload from the provider, for user messages."""
    body = getattr(e, "body", None)
    if body:
        try:
            return json.dumps(body, ensure_ascii=False)[:600]
        except Exception:
            return str(body)[:600]
    status = getattr(e, "status_code", None)
    if status:
        return f"HTTP {status}"
    return ""


def _build_ai_error(e: Exception, model: str) -> RuntimeError:
    """Build a user-facing RuntimeError with the provider's actual message."""
    msg = str(e)
    detail = _provider_error_detail(e)
    lowered = msg.lower()
    is_server_issue = (
        "500" in msg
        or "internalservererror" in lowered
        or "connection error" in lowered
        or "overload" in lowered
        or "timeout" in lowered
        or getattr(e, "status_code", None) in (429, 500, 502, 503, 504, 520, 522, 524)
    )
    if is_server_issue:
        text = (
            "The AI provider returned a server error while processing model "
            f"'{model}'.\n\n"
            "This is an upstream/provider issue, not a problem with your input. "
            "The proxy could not reach the model (no fallback configured).\n\n"
            "Try:\n"
            "1. Retry in a moment\n"
            "2. Switch to a different model in AI Models settings\n"
            "3. Use a shorter video (this transcript was large)"
        )
    else:
        text = f"AI request failed: {msg}"
    if detail:
        text += f"\n\nProvider detail: {detail}"
    return RuntimeError(text)


def _should_retry(e: Exception) -> bool:
    """True when retrying can plausibly help. Never retry bad-request/auth errors."""
    status = getattr(e, "status_code", None)
    if status in (400, 401, 402, 403, 404, 422):
        return False
    return True


def find_highlights(
    transcript: str,
    video_info: dict[str, Any],
    num_clips: int,
    api_key: str,
    base_url: str,
    model: str,
    system_prompt: str | None = None,
    temperature: float | None = None,
    user_direction: str | None = None,
    output_language: str | None = None,
    log: LogFn | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Call the AI model and return (highlights, token_usage).

    Each highlight has: start_time, end_time, title, description,
    virality_score, hook_text, duration_seconds.
    """
    log = log or debug_log
    system_prompt = system_prompt or DEFAULT_HIGHLIGHT_PROMPT

    # Request a few extra clips so we can drop invalid-duration ones
    request_clips = num_clips + 3

    video_context = ""
    if video_info:
        video_context = (
            "INFO VIDEO:\n"
            f"- Judul: {video_info.get('title', 'Unknown')}\n"
            f"- Channel: {video_info.get('channel', 'Unknown')}\n"
            f"- Deskripsi: {(video_info.get('description', '') or '')[:500]}"
        )

    direction_block = build_direction_block(user_direction)
    has_placeholder = "{user_direction}" in system_prompt

    prompt = system_prompt.replace("{num_clips}", str(request_clips))
    prompt = prompt.replace("{output_language}", output_language or SAME_AS_TRANSCRIPT)
    prompt = prompt.replace("{video_context}", video_context)
    prompt = prompt.replace("{user_direction}", direction_block)
    prompt = prompt.replace("{transcript}", transcript)

    if direction_block:
        # The transcript can run past 100k chars, and whatever sits before it
        # loses to recency — so re-anchor the direction after it. A custom system
        # message with no placeholder gets the full block here instead, since
        # that is the only copy it will have.
        tail = build_direction_reminder(user_direction) if has_placeholder else direction_block
        prompt = prompt.rstrip() + "\n" + tail

    if temperature is None:
        temperature = DIRECTED_TEMPERATURE if direction_block else DEFAULT_TEMPERATURE

    from openai import OpenAI

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        # Transcripts routinely run 100k+ chars (~30k tokens). On local /
        # mid-size models a single highlight pass can take several minutes,
        # and the old 180s cap made every heavy video fail after ~15 min of
        # futile retries (log showed exactly 02:23:50 -> 02:38:58). 900s per
        # attempt clears even the slowest single-pass generations; 2 retries
        # still cover transient connection drops without multiplying wall
        # time into the tens of minutes.
        timeout=900.0,
        max_retries=2,
    )
    log(f"Finding highlights using {model} at {base_url} (temperature {temperature})")

    # Stream the response. Transcripts are large and the gateway (Hermes /
    # custom OpenAI-compatible server) can take many minutes on a single
    # pass. A plain non-streamed request that sits idle for 10+ minutes gets
    # killed by NAT/firewall timeouts and the truncated body comes back
    # without 'choices' — observed as: request at 08:56:11, "API response
    # missing 'choices'" at 09:07:08. Streaming keeps the connection active
    # (hermes gateway sends SSE keep-alives ~every 30s), so long runs
    # survive. One retry covers transient upstream overloads.
    response_chunks: list[str] = []
    usage = None
    last_error: Exception | None = None

    for attempt in (1, 2):
        try:
            stream = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                stream=True,
            )
            response_chunks = []
            usage = None
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    response_chunks.append(chunk.choices[0].delta.content)
                if getattr(chunk, "usage", None):
                    usage = chunk.usage
            last_error = None
            break
        except Exception as e:
            msg = str(e)
            log(f"AI request failed: {msg[:300]}")
            last_error = e
            if attempt == 1 and _should_retry(e):
                log("AI provider hiccup — retrying once after a short pause...")
                time.sleep(8)
                continue
            raise _build_ai_error(e, model)

    if last_error is None and not response_chunks and not usage:
        raise RuntimeError(
            "The AI returned an empty response. The model may have refused the "
            "request or your quota is exceeded."
        )

    result = "".join(response_chunks).strip()
    if not result:
        raise RuntimeError(
            "The AI returned an empty response. The model may have refused the "
            "request or your quota is exceeded."
        )

    token_usage = {
        "prompt_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
        "completion_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
    }
    if result.startswith("```"):
        result = re.sub(r"```json?\n?", "", result)
        result = re.sub(r"```\n?", "", result)

    raw_highlights = parse_highlights_json(result, log)
    valid = _validate_highlights(
        raw_highlights, num_clips, log, parse_requested_ranges(user_direction)
    )
    return valid, token_usage


def _error_context(raw: str, err: json.JSONDecodeError, width: int = 120) -> str:
    """The text around a decode failure, for a log line that is actually useful."""
    start = max(0, err.pos - width)
    end = min(len(raw), err.pos + width)
    return f"...{raw[start:err.pos]} >>>HERE>>> {raw[err.pos:end]}..."


def parse_highlights_json(raw: str, log: LogFn) -> list[dict[str, Any]]:
    """Parse the model's JSON array, salvaging what is readable if it is broken.

    Models routinely emit an unescaped double quote inside one field, which makes
    `json.loads` reject the whole response. Since we deliberately over-request
    clips, dropping the one malformed object is far better than failing the run.
    """
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError as first_error:
        log(f"JSON parse error: {first_error}")
        log(f"Near the error: {_error_context(raw, first_error)}")

    # Salvage: walk the text and decode one object at a time, skipping any that
    # will not parse. Highlight objects are flat, so a nested brace cannot fool
    # the scanner.
    decoder = json.JSONDecoder()
    recovered: list[dict[str, Any]] = []
    dropped = 0
    index = 0
    while True:
        start = raw.find("{", index)
        if start == -1:
            break
        try:
            obj, end = decoder.raw_decode(raw, start)
        except json.JSONDecodeError:
            dropped += 1
            index = start + 1
            continue
        if isinstance(obj, dict):
            recovered.append(obj)
        index = end

    if recovered:
        log(
            f"Recovered {len(recovered)} clip object(s) from the malformed response"
            + (f", dropped {dropped} broken one(s)" if dropped else "")
        )
        return recovered

    raise RuntimeError(
        "Failed to parse the AI response as JSON, and no clip objects could be "
        "recovered from it. The model likely emitted an unescaped quote or was "
        "cut off. Try again, or switch models in AI Models settings.\n\n"
        f"Response length: {len(raw)} chars\n"
        f"Starts with: {raw[:300]}"
    )


def _validate_highlights(
    highlights: list[dict[str, Any]],
    num_clips: int,
    log: LogFn,
    requested_ranges: list[tuple[float, float]] | None = None,
) -> list[dict[str, Any]]:
    valid: list[dict[str, Any]] = []
    requested_ranges = requested_ranges or []

    for h in highlights:
        if "reason" in h and "description" not in h:
            h["description"] = h.pop("reason")

        try:
            duration = parse_timestamp(h["end_time"]) - parse_timestamp(h["start_time"])
        except (KeyError, ValueError, IndexError):
            log(f"Skipping highlight with invalid timestamps: {h.get('title', 'Unknown')}")
            continue

        h["duration_seconds"] = round(duration, 1)

        if "virality_score" not in h:
            h["virality_score"] = 5
        if "description" not in h:
            h["description"] = h.get("title", "No description")

        title = h.get("title", "Untitled")
        exact = _matches_requested_range(
            parse_timestamp(h["start_time"]), parse_timestamp(h["end_time"]), requested_ranges
        )

        if 58 <= duration <= 120 or exact:
            valid.append(h)
            note = " - exact range from your direction" if exact and not 58 <= duration <= 120 else ""
            log(f"OK {title} ({duration:.0f}s) [score {h['virality_score']}/10]{note}")
        else:
            log(f"Skip {title} ({duration:.0f}s) - outside 58-120s")

        if len(valid) >= num_clips:
            break

    return valid[:num_clips]
