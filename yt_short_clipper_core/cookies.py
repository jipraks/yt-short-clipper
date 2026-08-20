"""YouTube cookie validation."""

from pathlib import Path

from .constants import REQUIRED_COOKIES, SECURE_COOKIE_PREFIXES
from .helpers import debug_log


def validate_cookies(cookies_path: str | Path | None) -> tuple[bool, str]:
    """Validate that a cookies.txt file exists and contains YouTube auth cookies.

    Returns:
        (is_valid, error_message) — error_message is empty string when valid.
    """
    if not cookies_path:
        return False, "cookies.txt not found. Please upload cookies.txt file."

    path = Path(cookies_path)
    if not path.exists():
        return False, "cookies.txt not found. Please upload cookies.txt file."

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        debug_log(f"Error reading cookies file: {e}")
        return False, f"Failed to read cookies file: {e}"

    found_cookies: list[str] = []
    for cookie in REQUIRED_COOKIES:
        # Check plain cookie name (tab-separated format)
        if f"\t{cookie}\t" in content or content.endswith(f"\t{cookie}"):
            found_cookies.append(cookie)
            continue
        # Check __Secure- prefixed variants
        for prefix in SECURE_COOKIE_PREFIXES:
            secure_name = f"{prefix}{cookie}"
            if f"\t{secure_name}\t" in content or content.endswith(f"\t{secure_name}"):
                found_cookies.append(secure_name)
                break

    if not found_cookies:
        debug_log(f"Cookies file missing required auth cookies. Found: {found_cookies}")
        return False, (
            "Invalid cookies.txt - missing YouTube authentication cookies.\n\n"
            "Please export fresh cookies from your browser while logged into YouTube.\n\n"
            "Required cookies: SID, HSID, SSID, APISID, SAPISID, LOGIN_INFO\n\n"
            "Use a browser extension like 'Get cookies.txt LOCALLY' to export."
        )

    debug_log(f"Found auth cookies: {found_cookies}")
    return True, ""
