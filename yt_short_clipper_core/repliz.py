"""Repliz integration: list accounts, upload video, schedule posts."""

import uuid
from pathlib import Path
from typing import Any, Callable

LogFn = Callable[[str], None]

REPLIZ_API_BASE = "https://api.repliz.com/public"
PRESIGNED_URL_ENDPOINT = "https://api.ytclip.org/webhook/yt-clipper/presigned-url"


def list_accounts(access_key: str, secret_key: str) -> list[dict[str, Any]]:
    """List connected Repliz social media accounts."""
    import requests
    from requests.auth import HTTPBasicAuth

    url = f"{REPLIZ_API_BASE}/account"
    response = requests.get(
        url,
        params={"page": 1, "limit": 50},
        auth=HTTPBasicAuth(access_key, secret_key),
        timeout=15,
    )

    if response.status_code != 200:
        msg = f"HTTP {response.status_code}"
        try:
            msg = response.json().get("message", msg)
        except Exception:
            pass
        raise RuntimeError(f"Failed to load Repliz accounts: {msg}")

    data = response.json()
    accounts = data.get("docs", [])

    # Normalize to a clean shape for the frontend
    return [
        {
            "id": acc.get("_id", ""),
            "name": acc.get("name", "Unknown"),
            "username": acc.get("username", ""),
            "type": acc.get("type", "unknown"),
            "is_connected": acc.get("isConnected", False),
        }
        for acc in accounts
    ]


def _upload_video_to_storage(video_path: str, log: LogFn) -> str:
    """Upload video to S3 via pre-signed URL, return the public URL."""
    import requests

    file_size_mb = Path(video_path).stat().st_size / (1024 * 1024)
    log(f"Uploading video to storage ({file_size_mb:.1f} MB)...")

    # Step 1: Request pre-signed URL
    filename = f"{uuid.uuid4()}.mp4"
    response = requests.post(
        PRESIGNED_URL_ENDPOINT,
        json={"filename": filename},
        timeout=30,
    )
    if response.status_code != 200:
        raise RuntimeError(f"Failed to get pre-signed URL: HTTP {response.status_code}")

    data = response.json()
    presigned_url = data.get("url")
    public_url = data.get("publicUrl")

    if not presigned_url or not public_url:
        raise RuntimeError("Invalid response from pre-signed URL endpoint")

    # Step 2: Upload to S3
    log("Uploading to cloud storage...")
    with open(video_path, "rb") as f:
        upload_response = requests.put(
            presigned_url,
            data=f,
            headers={"Content-Type": "video/mp4", "x-amz-acl": "public-read"},
            timeout=1800,  # 30 minutes for large files
        )

    if upload_response.status_code not in (200, 204):
        raise RuntimeError(f"Storage upload failed: HTTP {upload_response.status_code}")

    log("Video uploaded to storage")
    return public_url


def _schedule_post(
    access_key: str,
    secret_key: str,
    account_id: str,
    title: str,
    description: str,
    video_url: str,
    schedule_at: str | None,
) -> tuple[bool, str]:
    """Schedule a post for one account. Returns (success, message)."""
    import requests
    from requests.auth import HTTPBasicAuth

    url = f"{REPLIZ_API_BASE}/schedule"
    payload: dict[str, Any] = {
        "title": title,
        "description": description,
        "topic": "",
        "type": "video",
        "medias": [{"type": "video", "thumbnail": "", "url": video_url}],
        "accountId": account_id,
    }
    if schedule_at:
        payload["scheduleAt"] = schedule_at

    response = requests.post(
        url,
        json=payload,
        auth=HTTPBasicAuth(access_key, secret_key),
        headers={"accept": "application/json", "Content-Type": "application/json"},
        timeout=30,
    )

    if response.status_code in (200, 201):
        return True, "Scheduled successfully"

    msg = f"HTTP {response.status_code}"
    try:
        msg = response.json().get("message", msg)
    except Exception:
        pass
    return False, msg


def upload_clip(
    access_key: str,
    secret_key: str,
    video_path: str,
    title: str,
    description: str,
    account_ids: list[str],
    schedule_at: str | None,
    log: LogFn,
) -> dict[str, Any]:
    """Upload a clip to storage and schedule posts to the given accounts.

    Returns {"video_url": "...", "results": [{"account_id": ..., "success": bool, "message": ...}]}
    """
    if not account_ids:
        raise RuntimeError("No accounts selected")

    # Step 1: Upload video once
    video_url = _upload_video_to_storage(video_path, log)

    # Step 2: Schedule for each account
    results = []
    for account_id in account_ids:
        log(f"Scheduling post for account {account_id}...")
        success, message = _schedule_post(
            access_key=access_key,
            secret_key=secret_key,
            account_id=account_id,
            title=title,
            description=description,
            video_url=video_url,
            schedule_at=schedule_at,
        )
        results.append({"account_id": account_id, "success": success, "message": message})
        log(f"Account {account_id}: {'OK' if success else 'FAILED'} - {message}")

    return {"video_url": video_url, "results": results}
