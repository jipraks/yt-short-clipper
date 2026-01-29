"""
Helper utility functions for YT Short Clipper
"""

import sys
import re
import shutil
from pathlib import Path


def get_app_dir():
    """Get application directory"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


def get_bundle_dir():
    """Get bundled resources directory"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else get_app_dir()
    return get_app_dir()


def get_ffmpeg_path():
    """Get FFmpeg executable path"""
    if getattr(sys, 'frozen', False):
        bundled = get_app_dir() / "ffmpeg" / "ffmpeg.exe"
        if bundled.exists():
            return str(bundled)
    return "ffmpeg"


def get_ytdlp_path():
    """Get yt-dlp executable path
    
    Checks in order:
    1. Bundled yt-dlp.exe (Windows)
    2. yt-dlp in system PATH
    3. Default "yt-dlp" command
    """
    if getattr(sys, 'frozen', False):
        bundled = get_app_dir() / "yt-dlp.exe"
        if bundled.exists():
            return str(bundled)
    
    # Try to find yt-dlp in PATH
    yt_dlp_path = shutil.which("yt-dlp")
    if yt_dlp_path:
        return yt_dlp_path
    
    # Fallback to command name (will work if it's in system PATH)
    return "yt-dlp"


def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from URL"""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None
