"""Shared constants for yt_short_clipper_core."""

import subprocess
import sys

SUBPROCESS_FLAGS = 0
if sys.platform == "win32":
    SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW

LANG_NAMES = {
    "en": "English",
    "id": "Indonesian",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "pt": "Portuguese",
    "ru": "Russian",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "ar": "Arabic",
    "hi": "Hindi",
    "it": "Italian",
    "nl": "Dutch",
    "pl": "Polish",
    "tr": "Turkish",
    "vi": "Vietnamese",
    "th": "Thai",
}

REQUIRED_COOKIES = ["SID", "HSID", "SSID", "APISID", "SAPISID", "LOGIN_INFO"]
SECURE_COOKIE_PREFIXES = ["__Secure-1P", "__Secure-3P"]


# Used when we cannot name a language: the model can still tell what the
# transcript is in, so this keeps the instruction workable for any code.
SAME_AS_TRANSCRIPT = "the same language as the transcript"


def language_name(code: str | None) -> str | None:
    """Map a subtitle code to a language name, or None if we do not know it.

    Handles the suffixed forms YouTube hands us: "id-orig" -> Indonesian,
    "pt-BR" -> Portuguese, "en_US" -> English.
    """
    if not code:
        return None
    base = code.strip().lower().replace("_", "-").split("-")[0]
    return LANG_NAMES.get(base)


def resolve_output_language(choice: str | None, subtitle_language: str | None) -> str:
    """Decide which language the model should write titles and hooks in.

    ``choice`` is the user's pick from the Create page: a language code, or
    "auto"/empty to follow the video. Auto is the right default because the
    burned-in captions come from the video's own track — a hook in a different
    language than the captions under it looks broken.
    """
    picked = (choice or "auto").strip().lower()
    if picked and picked != "auto":
        return language_name(picked) or picked
    return language_name(subtitle_language) or SAME_AS_TRANSCRIPT
