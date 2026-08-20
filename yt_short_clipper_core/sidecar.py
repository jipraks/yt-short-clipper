"""YT Short Clipper Python sidecar.

Protocol: JSON Lines over stdin/stdout.

Request:
    {"id":"...","command":"get_subtitles","payload":{"url":"...","cookies_path":"..."}}

Response:
    {"id":"...","ok":true,"result":{...}}
    {"id":"...","ok":false,"error":"..."}
"""

import json
import sys
import traceback
from typing import Any


class SidecarError(Exception):
    pass


def _session_output_language(session_dir: Any) -> str:
    """The language a session was generated in, or a neutral fallback."""
    from yt_short_clipper_core.constants import SAME_AS_TRANSCRIPT

    fallback = "the same language as the input above"
    if not session_dir:
        return fallback

    import os

    try:
        with open(
            os.path.join(str(session_dir), "session_data.json"), encoding="utf-8"
        ) as f:
            name = json.load(f).get("output_language_name")
    except (OSError, ValueError):
        return fallback
    if not name or name == SAME_AS_TRANSCRIPT:
        return fallback
    return name


def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    command = request.get("command")
    payload = request.get("payload") or {}

    if command == "get_subtitles":
        from yt_short_clipper_core.subtitle_fetcher import get_available_subtitles
        from yt_short_clipper_core.helpers import get_ytdlp_path

        url = payload.get("url")
        cookies_path = payload.get("cookies_path")
        ytdlp_path = payload.get("ytdlp_path") or get_ytdlp_path()

        if not url:
            raise SidecarError("Missing payload.url")
        if not cookies_path:
            raise SidecarError("Missing payload.cookies_path")

        return get_available_subtitles(
            url=url,
            ytdlp_path=ytdlp_path,
            cookies_path=cookies_path,
        )

    if command == "list_ai_models":
        api_key = payload.get("api_key")
        base_url = payload.get("base_url") or "https://api.openai.com/v1"

        if not api_key:
            raise SidecarError("Missing payload.api_key")

        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=base_url)
        models_response = client.models.list()
        models = sorted([m.id for m in models_response.data])
        return models

    if command == "ping":
        return {"pong": True}

    if command == "repliz_list_accounts":
        from yt_short_clipper_core.repliz import list_accounts

        access_key = payload.get("access_key")
        secret_key = payload.get("secret_key")

        if not access_key or not secret_key:
            raise SidecarError("Missing Repliz access_key/secret_key")

        return list_accounts(access_key=access_key, secret_key=secret_key)

    if command == "repliz_upload":
        from yt_short_clipper_core.repliz import upload_clip

        access_key = payload.get("access_key")
        secret_key = payload.get("secret_key")
        video_path = payload.get("video_path")
        title = payload.get("title", "")
        description = payload.get("description", "")
        account_ids = payload.get("account_ids") or []
        schedule_at = payload.get("schedule_at")

        if not access_key or not secret_key:
            raise SidecarError("Missing Repliz access_key/secret_key")
        if not video_path:
            raise SidecarError("Missing video_path")
        if not account_ids:
            raise SidecarError("No accounts selected")

        def emit_log(message: str) -> None:
            write_json({"event": "log", "message": message})

        return upload_clip(
            access_key=access_key,
            secret_key=secret_key,
            video_path=video_path,
            title=title,
            description=description,
            account_ids=account_ids,
            schedule_at=schedule_at,
            log=emit_log,
        )

    if command == "generate_social_title":
        import json as _json
        from openai import OpenAI

        title = payload.get("title", "")
        hook_text = payload.get("hook_text", "")
        description = payload.get("description", "")
        api_key = payload.get("api_key")
        base_url = payload.get("base_url") or "https://api.openai.com/v1"
        model = payload.get("model")

        if not api_key or not model:
            raise SidecarError("Missing api_key or model for title generation")

        # Match the language the clip's own title and hook were written in. It is
        # recorded on the session, so this also works for clips opened from the
        # Library; sessions made before the setting existed fall back gracefully.
        language = payload.get("output_language") or _session_output_language(
            payload.get("session_dir")
        )

        client = OpenAI(api_key=api_key, base_url=base_url)

        prompt = f"""Generate a catchy social media post title and description for this short video clip.

Video Title: {title}
Hook/Content: {hook_text}
Context: {description}

Requirements:
- title: Max 100 characters, engaging and clickable, casual {language}
- description: 2-3 sentences with relevant hashtags, casual {language}, viral-worthy

Return ONLY valid JSON in this exact format:
{{"title": "...", "description": "..."}}"""

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": f"You are a social media expert who creates viral content for TikTok/Reels/Shorts in {language}. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.8,
                max_tokens=500,
                response_format={"type": "json_object"},
            )
        except Exception:
            # Retry without response_format for providers that don't support it
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": f"You are a social media expert who creates viral content for TikTok/Reels/Shorts in {language}. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.8,
                max_tokens=500,
            )

        raw = response.choices[0].message.content.strip() if response.choices else "{}"

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1] if "```" in raw[3:] else raw
            raw = raw.replace("json", "", 1).strip() if raw.lower().startswith("json") else raw

        try:
            parsed = _json.loads(raw)
            return {
                "title": parsed.get("title", ""),
                "description": parsed.get("description", ""),
            }
        except Exception:
            # Fallback: return raw text as title
            return {"title": raw, "description": ""}

    if command == "detect_gpu":
        from yt_short_clipper_core.gpu import detect_gpu

        return detect_gpu()

    if command == "process_selected_highlights":
        from yt_short_clipper_core.clip_processor import process_selected_highlights

        url = payload.get("url")
        highlights = payload.get("highlights")
        session_dir = payload.get("session_dir")
        options = payload.get("options", {})
        ai = payload.get("ai") or {}

        if not url or not highlights or not session_dir:
            raise SidecarError("Missing url, highlights, or session_dir")
        # No AI key needed here: captions come from the YouTube subtitle track
        # and hook text is rendered locally from pre-generated highlight data.

        def emit_log(message: str) -> None:
            write_json({"event": "log", "message": message})

        return process_selected_highlights(
            url=url,
            highlights=highlights,
            session_dir=session_dir,
            options=options,
            ai=ai,
            log=emit_log,
        )

    if command == "find_highlights":
        from yt_short_clipper_core.session import find_highlights_only

        url = payload.get("url")
        cookies_path = payload.get("cookies_path")
        ai = payload.get("ai") or {}

        if not url:
            raise SidecarError("Missing payload.url")
        if not cookies_path:
            raise SidecarError("Missing payload.cookies_path")
        if not ai.get("api_key") or not ai.get("model"):
            raise SidecarError("Missing AI api_key/model. Configure Highlight Finder first.")

        def emit_log(message: str) -> None:
            write_json({"event": "log", "message": message})

        return find_highlights_only(
            url=url,
            num_clips=int(payload.get("num_clips", 5)),
            subtitle_language=payload.get("subtitle_language", "id"),
            output_dir=payload.get("output_dir"),
            cookies_path=cookies_path,
            ai=ai,
            user_direction=payload.get("user_direction"),
            output_language=payload.get("output_language"),
            log=emit_log,
        )

    raise SidecarError(f"Unknown command: {command}")


def make_response(request_id: Any, ok: bool, result: Any = None, error: str | None = None) -> dict[str, Any]:
    response = {"id": request_id, "ok": ok}
    if ok:
        response["result"] = result
    else:
        response["error"] = error or "Unknown sidecar error"
    return response


def write_json(obj: dict[str, Any]) -> None:
    # Force UTF-8 to avoid Windows cp1252 encoding errors with Unicode chars
    raw = json.dumps(obj, ensure_ascii=False)
    sys.stdout.buffer.write(raw.encode("utf-8"))
    sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.flush()


def run_loop() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        request_id = None
        try:
            request = json.loads(line)
            request_id = request.get("id")
            result = handle_request(request)
            write_json(make_response(request_id, True, result=result))
        except Exception as e:
            print(traceback.format_exc(), file=sys.stderr, flush=True)
            write_json(make_response(request_id, False, error=str(e)))


def main() -> None:
    run_loop()


if __name__ == "__main__":
    main()
