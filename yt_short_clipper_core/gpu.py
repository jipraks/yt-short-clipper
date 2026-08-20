"""GPU detection and FFmpeg hardware encoder support.

Standalone — usable from the Tauri sidecar. Returns a single dict combining
detected GPU info and the recommended FFmpeg encoder.
"""

import re
import subprocess
import sys

from .constants import SUBPROCESS_FLAGS
from .helpers import get_ffmpeg_path

ENCODER_MAP = {
    "nvidia": "h264_nvenc",
    "amd": "h264_amf",
    "intel": "h264_qsv",
    "apple": "h264_videotoolbox",
}

PRESET_MAP = {
    "nvidia": "p4",
    "amd": "balanced",
    "intel": "faster",
    "apple": None,
}


def _run(cmd: list[str], timeout: int = 5) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=SUBPROCESS_FLAGS,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


def _windows_video_controllers() -> list[str]:
    result = _run(
        [
            "powershell",
            "-Command",
            "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name",
        ],
        timeout=10,
    )
    if result and result.returncode == 0 and result.stdout.strip():
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return []


def _detect_nvidia() -> dict:
    result = _run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"])
    if result and result.returncode == 0 and result.stdout.strip():
        name = result.stdout.strip().splitlines()[0]
        return {"type": "nvidia", "name": name, "available": True}

    if sys.platform == "win32":
        for line in _windows_video_controllers():
            if any(k in line for k in ("NVIDIA", "GeForce", "Quadro", "RTX", "GTX")):
                return {"type": "nvidia", "name": line, "available": True}

    return {"type": None, "name": "", "available": False}


def _detect_from_controllers(keywords: tuple[str, ...], gpu_type: str) -> dict:
    if sys.platform == "win32":
        for line in _windows_video_controllers():
            if any(k in line for k in keywords):
                return {"type": gpu_type, "name": line, "available": True}
    elif sys.platform.startswith("linux"):
        result = _run(["lspci"])
        if result and result.returncode == 0:
            for line in result.stdout.splitlines():
                if "VGA" in line and any(k in line for k in keywords):
                    match = re.search(r":\s*(.+)$", line)
                    if match:
                        return {"type": gpu_type, "name": match.group(1).strip(), "available": True}
    return {"type": None, "name": "", "available": False}


def _detect_apple() -> dict:
    if sys.platform != "darwin":
        return {"type": None, "name": "", "available": False}
    result = _run(["system_profiler", "SPDisplaysDataType"], timeout=10)
    if result and result.returncode == 0:
        for line in result.stdout.splitlines():
            line = line.strip()
            if "Chipset Model" in line or "Chip" in line:
                name = line.split(":", 1)[-1].strip()
                if "Apple" in name or name.startswith("M"):
                    return {"type": "apple", "name": name, "available": True}
    return {"type": None, "name": "", "available": False}


def _detect_gpu_hardware() -> dict:
    for detector in (
        _detect_nvidia,
        lambda: _detect_from_controllers(("AMD", "Radeon"), "amd"),
        lambda: _detect_from_controllers(("Intel HD", "Intel UHD", "Iris", "Arc"), "intel"),
        _detect_apple,
    ):
        info = detector()
        if info["available"]:
            return info
    return {"type": None, "name": "No GPU detected", "available": False}


def _available_encoders(ffmpeg_path: str) -> list[str]:
    result = _run([ffmpeg_path, "-encoders"], timeout=10)
    if not result:
        return []
    output = (result.stdout or "") + (result.stderr or "")
    encoders = []
    known = ("h264_nvenc", "h264_amf", "h264_qsv", "h264_mf", "h264_videotoolbox")
    for line in output.splitlines():
        line = line.strip()
        if any(enc in line for enc in known):
            parts = line.split()
            if len(parts) >= 2 and parts[1].startswith("h264_"):
                encoders.append(parts[1])
    return encoders


def _probe_encoder(ffmpeg_path: str, encoder_name: str, timeout: int = 20) -> tuple[bool, str | None]:
    """Actually try encoding one tiny frame with the given hardware encoder.

    Many GPU/video-controller WMI entries exist alongside an inactive or
    incompatible device (e.g. NVIDIA Optimus laptops with a primary Intel
    iGPU, or old Maxwell mobile parts whose NVENC isn't supported by modern
    FFmpeg builds). The `ffmpeg -encoders` list only confirms the encoder was
    compiled *into* FFmpeg — not that it can actually initialise on this GPU
    at runtime. Running a single-frame encode is the only reliable check.

    Returns (ok, error_snippet).
    """
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
        out_path = tf.name
    try:
        result = subprocess.run(
            [
                ffmpeg_path, "-y", "-hide_banner", "-f", "lavfi",
                "-i", "color=black:s=64x64:d=0.04",
                "-frames:v", "1",
                "-c:v", encoder_name,
                out_path,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=SUBPROCESS_FLAGS,
        )
        if result.returncode == 0:
            return True, None
        snippet = (result.stderr or "").strip().splitlines()
        snippet_str = "\n".join(snippet[-8:]) if snippet else f"exit code {result.returncode}"
        return False, snippet_str
    except (subprocess.TimeoutExpired, OSError, FileNotFoundError) as e:
        return False, str(e)
    finally:
        try:
            import os as _os
            _os.unlink(out_path)
        except OSError:
            pass


def detect_gpu() -> dict:
    """Detect GPU and recommended FFmpeg encoder.

    Returns dict:
        {
          "gpu": {"type", "name", "available"},
          "encoder": {"name", "preset", "available", "reason"}
        }
    """
    ffmpeg_path = get_ffmpeg_path()
    gpu = _detect_gpu_hardware()

    if not gpu["available"]:
        return {
            "gpu": gpu,
            "encoder": {
                "name": None,
                "preset": None,
                "available": False,
                "reason": "No GPU detected — will use CPU (libx264)",
            },
        }

    encoders = _available_encoders(ffmpeg_path)
    recommended = ENCODER_MAP.get(gpu["type"])

    if recommended and recommended in encoders:
        # Run a one-frame probe to verify the encoder can actually initialise
        # on this device at runtime. Many older GPUs (Maxwell/Pascal mobile
        # NVENC parts) ship an `ffmpeg -encoders` entry but fail to open the
        # device, returning exit code -1. The authoritative check is the probe.
        ok, err = _probe_encoder(ffmpeg_path, recommended)
        if ok:
            encoder = {
                "name": recommended,
                "preset": PRESET_MAP.get(gpu["type"]),
                "available": True,
                "reason": f"Using {gpu['name']}",
            }
        else:
            snippet = (err or "")[:240]
            encoder = {
                "name": None,
                "preset": None,
                "available": False,
                "reason": (
                    f"GPU detected ({gpu['name']}) and FFmpeg has "
                    f"{recommended} but runtime probe failed — will use CPU "
                    f"(libx264). Probe stderr: {snippet}"
                ),
            }
    else:
        missing = recommended if recommended else "a matching hardware encoder"
        encoder = {
            "name": None,
            "preset": None,
            "available": False,
            "reason": f"GPU detected ({gpu['name']}) but FFmpeg lacks {missing}",
        }

    return {"gpu": gpu, "encoder": encoder}
