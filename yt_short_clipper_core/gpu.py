"""GPU detection and FFmpeg hardware encoder support.

Standalone — usable from the Tauri sidecar. Returns a single dict combining
detected GPU info and the recommended FFmpeg encoder.
"""

import json
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

# Detection priority: a discrete GPU beats an integrated one, *regardless of
# the order* WMI/lspci happens to list the adapters in. Optimus laptops often
# report the Intel iGPU first, so a naive "first match wins" loop could label
# a machine with an NVIDIA dGPU as plain "intel" and drop NVENC.
PRIORITY = ("nvidia", "amd", "intel")


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


def _normalize_gpu_name(name: str) -> str:
    """Strip trademark noise so keyword matching is reliable.

    WMI reports iGPUs as "Intel(R) HD Graphics 520" and "AMD Radeon(TM)
    Graphics", so a literal "Intel HD" keyword never matches and every
    Intel integrated GPU looked like "No GPU detected". Drop (R)/(TM)/(C)
    and the ®/™ glyphs, then collapse the leftover whitespace.
    """
    cleaned = re.sub(r"\((?:R|TM|C)\)|[®™]", " ", name, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", cleaned).strip()


def _classify_controller(name: str, compatibility: str = "") -> str | None:
    """Map one video controller to a vendor ("nvidia"/"amd"/"intel") or None.

    ``compatibility`` is WMI's AdapterCompatibility field — a stable vendor
    string that survives odd or locale-renamed display names (e.g. a machine
    whose DriverName got mangled but still reports "Intel(R) Corporation").

    Keyword order matters: AMD's older Radeon HD series ("AMD Radeon HD 8570M")
    contains "HD Graphics"-adjacent text, so Radeon/AMD must win before the
    Intel-specific "hd graphics / uhd graphics" checks run.
    """
    haystack = (
        _normalize_gpu_name(name).casefold()
        + " "
        + _normalize_gpu_name(compatibility).casefold()
    )
    checks = (
        ("nvidia", ("nvidia", "geforce", "quadro", "rtx", "gtx", "titan")),
        ("amd", ("amd", "radeon", "ati ", "advanced micro devices")),
        # Bare "intel" is safe here: the only display controllers whose vendor
        # is Intel are actual Intel iGPUs (HD/UHD/Iris/Arc/GMA/Xe families).
        # This catches every WMI/lspci wording, including driver-renamed
        # variants like "Intel(R) HD Graphics 615" or bare "Intel Corporation
        # Device 9a49" that carry no family name at all.
        (
            "intel",
            (
                "intel",
                "iris",
                "arc",
                "gma",
                "graphics media accelerator",
                "hd graphics",
                "uhd graphics",
                "xe graphics",
                "express chipset",
            ),
        ),
    )
    for vendor, keywords in checks:
        if any(k in haystack for k in keywords):
            return vendor
    return None


def _windows_video_controllers() -> list[dict]:
    """Return [{"name", "compatibility"}] for every Win32_VideoController.

    Uses Get-CimInstance with JSON output (plain-text parsing broke on names
    containing commas/quotes), and falls back to Get-WmiObject on systems
    without the CIM cmdlets. -NoProfile skips slow PowerShell profile loading.
    """
    scripts = (
        "Get-CimInstance Win32_VideoController | Select-Object Name,AdapterCompatibility "
        "| ConvertTo-Json -Compress",
        "Get-WmiObject Win32_VideoController | Select-Object Name,AdapterCompatibility "
        "| ConvertTo-Json -Compress",
    )
    for script in scripts:
        result = _run(["powershell", "-NoProfile", "-Command", script], timeout=10)
        if not result or result.returncode != 0 or not result.stdout.strip():
            continue
        try:
            data = json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            data = [data]
        controllers = []
        for item in data:
            name = (item.get("Name") or "").strip()
            compat = (item.get("AdapterCompatibility") or "").strip()
            if name:
                controllers.append({"name": name, "compatibility": compat})
        if controllers:
            return controllers
    return []


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
    # nvidia-smi is the most reliable NVIDIA signal when the driver is present.
    nv_smi = _run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"])
    if nv_smi and nv_smi.returncode == 0 and nv_smi.stdout.strip():
        name = nv_smi.stdout.strip().splitlines()[0].strip()
        return {"type": "nvidia", "name": name, "available": True}

    if sys.platform == "win32":
        controllers = _windows_video_controllers()
        for vendor in PRIORITY:
            for c in controllers:
                if _classify_controller(c["name"], c["compatibility"]) == vendor:
                    return {"type": vendor, "name": c["name"], "available": True}
    elif sys.platform.startswith("linux"):
        result = _run(["lspci"])
        if result and result.returncode == 0:
            lines = [
                ln
                for ln in result.stdout.splitlines()
                if any(cls in ln for cls in ("VGA", "3D controller", "Display controller"))
            ]
            for vendor in PRIORITY:
                for line in lines:
                    if _classify_controller(line) == vendor:
                        match = re.search(r":\s*(.+)$", line)
                        name = match.group(1).strip() if match else line.strip()
                        return {"type": vendor, "name": name, "available": True}
    else:
        apple = _detect_apple()
        if apple["available"]:
            return apple

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

    The probe frame must stay above every vendor's minimum encode dimensions.
    AMF in particular refuses anything smaller than ~128x128 and fails with
    AVERROR_BUG, which used to make a working Radeon encoder look broken and
    pushed every render onto libx264. 320x240 clears all vendor minimums and
    still encodes instantly.

    Intel Quick Sync is attempted twice: plain `-c:v h264_qsv` first (FFmpeg
    auto-init only covers some setups), then with an explicit `-init_hw_device
    qsv=hw` chain, which is what fixes the classic "Device creation failed:
    -17" on Intel HD/UHD iGPUs such as HD Graphics 615.

    Returns (ok, error_snippet).
    """
    import tempfile

    filter_hw = [
        ffmpeg_path, "-y", "-hide_banner",
        "-init_hw_device", "qsv=hw", "-filter_hw_device", "hw",
    ]
    attempts = [
        [ffmpeg_path, "-y", "-hide_banner"],
    ]
    if encoder_name == "h264_qsv":
        attempts.append(filter_hw)
    last_err: str | None = None
    for head in attempts:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
            out_path = tf.name
        try:
            result = subprocess.run(
                head
                + ["-f", "lavfi", "-i", "color=black:s=320x240:d=0.04",
                   "-frames:v", "1", "-c:v", encoder_name, out_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=SUBPROCESS_FLAGS,
            )
            if result.returncode == 0:
                return True, None
            lines = [ln.strip() for ln in (result.stderr or "").splitlines() if ln.strip()]
            last_err = " | ".join(lines[-3:]) if lines else f"exit code {result.returncode}"
        except (subprocess.TimeoutExpired, OSError, FileNotFoundError) as e:
            last_err = str(e)
        finally:
            try:
                import os as _os
                _os.unlink(out_path)
            except OSError:
                pass
    return False, last_err


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


def build_video_enc_args(gpu_config: dict | None) -> list[str]:
    """Build ffmpeg video encoder args from gpu_config.

    gpu_config is the dict returned by detect_gpu()['encoder'], or None for CPU.
    Returns list of ffmpeg args (e.g. ['-c:v', 'h264_nvenc', '-preset', 'p4', '-rc', 'vbr', '-cq', '23']).
    """
    if not gpu_config or not gpu_config.get("available"):
        return ["-c:v", "libx264", "-preset", "fast", "-crf", "18"]

    name = gpu_config.get("name")
    preset = gpu_config.get("preset")

    if name == "h264_nvenc":
        args = ["-c:v", name]
        if preset:
            args += ["-preset", preset]
        args += ["-rc", "vbr", "-cq", "23"]
        return args

    if name:
        args = ["-c:v", name]
        if preset:
            args += ["-preset", preset]
        return args

    return ["-c:v", "libx264", "-preset", "fast", "-crf", "18"]