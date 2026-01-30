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
    """Get yt-dlp executable path or check if module is available
    
    Checks in order:
    1. yt-dlp Python module (preferred - bundled with PyInstaller)
    2. Bundled yt-dlp.exe (Windows)
    3. yt-dlp in system PATH
    4. Default "yt-dlp" command
    
    Returns:
        str: Path to yt-dlp executable, or "yt_dlp_module" if using Python module
    """
    # First check if yt-dlp is available as Python module
    try:
        import yt_dlp
        return "yt_dlp_module"  # Special marker to use module instead of subprocess
    except ImportError:
        pass
    
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


def is_ytdlp_module_available():
    """Check if yt-dlp Python module is available"""
    try:
        import yt_dlp
        return True
    except ImportError:
        return False


def get_deno_path():
    """Get Deno executable path (required for yt-dlp --remote-components)
    
    Checks in order:
    1. Bundled deno.exe in bin/ folder (Windows)
    2. deno in system PATH
    3. None if not found
    """
    if getattr(sys, 'frozen', False):
        # Check bundled deno in bin folder
        bundled = get_app_dir() / "bin" / "deno.exe"
        if bundled.exists():
            return str(bundled)
    
    # Try to find deno in PATH
    deno_path = shutil.which("deno")
    if deno_path:
        return deno_path
    
    # Not found
    return None


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
