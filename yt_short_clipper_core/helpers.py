"""Path resolution helpers and debug logging.

Standalone — does NOT depend on the Tkinter app. Can be used by the Tauri sidecar.
"""

import os
import sys
import shutil
from pathlib import Path

# ---------------------------------------------------------------------------
# Debug logging
# ---------------------------------------------------------------------------

DEBUG_MODE = not getattr(sys, "frozen", False)


def debug_log(msg: str) -> None:
    """Log to stderr only in debug mode (running from terminal).

    IMPORTANT: writes to stderr, never stdout — stdout is reserved for the
    machine-readable JSON payload consumed by the Tauri/Rust layer.
    """
    if DEBUG_MODE:
        print(f"[DEBUG] {msg}", file=sys.stderr, flush=True)


def setup_debug_mode(enabled: bool) -> None:
    """Override debug mode at runtime (useful for sidecar)."""
    global DEBUG_MODE
    DEBUG_MODE = enabled


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _get_app_dir() -> Path:
    """Get application data directory."""
    if getattr(sys, "frozen", False):
        if sys.platform == "darwin":
            app_support = Path.home() / "Library" / "Application Support" / "YTShortClipper"
            app_support.mkdir(parents=True, exist_ok=True)
            return app_support
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def _tauri_app_data_dir() -> Path | None:
    """Return the Tauri app-data directory if it exists, else None."""
    try:
        import platform
        if platform.system() == "Windows":
            base = Path(os.environ.get("APPDATA", ""))
        elif platform.system() == "Darwin":
            base = Path.home() / "Library" / "Application Support"
        else:
            base = Path.home() / ".config"
        data_dir = base / "com.jipraks.ytshortclipper-v2"
        return data_dir if data_dir.exists() else None
    except Exception:
        return None


def _resource_dirs() -> list[Path]:
    """Candidate base directories where bundled resources may live.

    Covers both dev (binaries/ next to the frozen sidecar or src-tauri/binaries
    in the source tree) and the various layouts Tauri uses when the app is
    installed (resources/ subfolder next to the executable, or one level up),
    plus the PyInstaller onefile extraction dir and the Tauri per-user app-data
    dir for installs that put resources there.
    """
    app_dir = _get_app_dir()
    candidates = [
        app_dir,
        app_dir / "resources",
        app_dir.parent,
        app_dir.parent / "resources",
        app_dir.parent.parent,
        app_dir.parent.parent / "resources",
        # Dev source-tree layout (when running via `py -m ...`)
        app_dir / "src-tauri" / "binaries",
    ]

    # PyInstaller onefile: sys._MEIPASS is the temp extraction dir holding
    # bundled binaries/resources. Critical for the WebGL/mediapipe one-file
    # sidecar build where everything lives in a temp dir at runtime.
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates += [
            Path(meipass),
            Path(meipass) / "resources",
            Path(meipass).parent,
            Path(meipass).parent / "resources",
        ]

    # Tauri installer layouts where the .exe sits in a *bin/* subdir and
    # resources live next to the bin/ folder, and per-user app-data layouts.
    candidates += [
        app_dir.parent / "bin" / "resources",
        app_dir / "bin" / "resources",
    ]
    app_data = _tauri_app_data_dir()
    if app_data:
        candidates += [app_data, app_data / "resources"]

    # De-duplicate while preserving order
    seen: set[str] = set()
    result: list[Path] = []
    for c in candidates:
        key = str(c)
        if key not in seen:
            seen.add(key)
            result.append(c)
    return result


def _find_bundled(rel_path: str) -> Path | None:
    """Find a bundled resource file by trying all candidate resource dirs."""
    for base in _resource_dirs():
        candidate = base / rel_path
        if candidate.exists():
            return candidate
    return None


def get_ffmpeg_path() -> str:
    """Get FFmpeg executable path.

    Checks in order:
    1. Bundled ffmpeg in any resource dir (ffmpeg/ffmpeg.exe)
    2. ffmpeg in system PATH
    3. Default "ffmpeg" command
    """
    exe_name = "ffmpeg.exe" if sys.platform.startswith("win") else "ffmpeg"
    bundled = _find_bundled(f"ffmpeg/{exe_name}")
    if bundled:
        return str(bundled)

    ffmpeg_in_path = shutil.which("ffmpeg")
    if ffmpeg_in_path:
        return ffmpeg_in_path

    return "ffmpeg"


def get_ytdlp_path() -> str:
    """Get yt-dlp path.

    Checks in order:
    1. yt-dlp Python module (preferred)
    2. Bundled yt-dlp.exe
    3. yt-dlp in system PATH
    4. Default "yt-dlp" command

    Returns:
        "yt_dlp_module" marker or path string.
    """
    try:
        import yt_dlp  # noqa: F401
        return "yt_dlp_module"
    except ImportError:
        pass

    bundled = _find_bundled("yt-dlp.exe")
    if bundled:
        return str(bundled)

    yt_dlp_path = shutil.which("yt-dlp")
    if yt_dlp_path:
        return yt_dlp_path

    return "yt-dlp"


def get_deno_path() -> str | None:
    """Get Deno executable path (required for yt-dlp --remote-components).

    Checks in order:
    1. Bundled deno in any resource dir (bin/deno.exe)
    2. deno in system PATH
    3. None if not found
    """
    exe_name = "deno.exe" if sys.platform.startswith("win") else "deno"
    bundled = _find_bundled(f"bin/{exe_name}")
    if bundled:
        return str(bundled)

    deno_path = shutil.which("deno")
    if deno_path:
        return deno_path

    return None


def is_ytdlp_module_available() -> bool:
    """Check if yt-dlp Python module is available."""
    try:
        import yt_dlp  # noqa: F401
        return True
    except ImportError:
        return False


def get_face_landmarker_model_path() -> str:
    """Get path to the MediaPipe face_landmarker.task model file.

    Checks in order:
    1. Bundled model in any resource dir (models/face_landmarker.task)
    2. Cached model in app data dir (downloaded previously)
    3. Downloads the model and caches it in the app data directory.
    Returns the absolute path to the .task file.
    """
    import urllib.request

    # 1. Bundled model
    bundled = _find_bundled("models/face_landmarker.task")
    if bundled:
        return str(bundled)

    # 2 & 3. Cached or download
    app_dir = _get_app_dir()
    models_dir = app_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    model_path = models_dir / "face_landmarker.task"

    if model_path.exists():
        return str(model_path)

    url = (
        "https://storage.googleapis.com/mediapipe-models/"
        "face_landmarker/face_landmarker/float16/latest/face_landmarker.task"
    )
    debug_log(f"Downloading face_landmarker model from {url}")
    urllib.request.urlretrieve(url, str(model_path))
    debug_log(f"Model saved to {model_path}")
    return str(model_path)
