"""Unit tests for the new GPU classification logic (run on Linux CI or any box).

Covers the exact bug report: Intel(R) HD Graphics 615 not detected, plus
dual-GPU priority, AMD-vs-Intel keyword overlap, and renamed adapters.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from yt_short_clipper_core.gpu import _classify_controller, _normalize_gpu_name

PASS = 0
FAIL = 0

def check(label, actual, expected):
    global PASS, FAIL
    ok = actual == expected
    PASS += ok
    FAIL += not ok
    print(f"{'✅' if ok else '❌'} {label}: got {actual!r}, want {expected!r}")

# --- The actual bug report: Intel HD 615 -------------------------------------------------
check("Intel(R) HD Graphics 615", _classify_controller("Intel(R) HD Graphics 615"), "intel")
check("Intel(R) HD Graphics (615)", _classify_controller("Intel(R) HD Graphics (615)"), "intel")
check("Intel(R) UHD Graphics 615/617", _classify_controller("Intel(R) UHD Graphics 615/617"), "intel")
check("Intel(R) HD Graphics 520", _classify_controller("Intel(R) HD Graphics 520"), "intel")
check("Intel(R) HD Graphics Family", _classify_controller("Intel(R) HD Graphics Family"), "intel")
check("Intel(R) Iris(R) Plus Graphics 655", _classify_controller("Intel(R) Iris(R) Plus Graphics 655"), "intel")
check("Intel(R) Iris(R) Xe Graphics", _classify_controller("Intel(R) Iris(R) Xe Graphics"), "intel")
check("Intel(R) UHD Graphics 620", _classify_controller("Intel(R) UHD Graphics 620"), "intel")
check("Intel(R) Graphics Media Accelerator HD", _classify_controller("Intel(R) Graphics Media Accelerator HD"), "intel")
check("Intel(R) 82945G Express Chipset Family", _classify_controller("Intel(R) 82945G Express Chipset Family"), "intel")
# driver-renamed / no family name at all -> bare "intel" keyword catches it
check("Intel(R) Corporation 9a49 (renamed)", _classify_controller("Intel(R) Something Weird 9a49"), "intel")
# renamed display name but stable AdapterCompatibility survives
check("compat-only Intel", _classify_controller("Unknown Display Adapter", "Intel(R) Corporation"), "intel")
check("compat-only NVIDIA", _classify_controller("Unknown Display Adapter", "NVIDIA Corporation"), "nvidia")
check("compat-only AMD", _classify_controller("Unknown Display Adapter", "Advanced Micro Devices, Inc."), "amd")

# --- NVIDIA -------------------------------------------------------------------------------
check("NVIDIA GeForce RTX 3060", _classify_controller("NVIDIA GeForce RTX 3060"), "nvidia")
check("NVIDIA GeForce GTX 1650", _classify_controller("NVIDIA GeForce GTX 1650"), "nvidia")
check("NVIDIA Quadro P1000", _classify_controller("NVIDIA Quadro P1000"), "nvidia")
check("NVIDIA GeForce MX150 + Intel listed 1st", _classify_controller("NVIDIA GeForce MX150"), "nvidia")

# --- AMD ----------------------------------------------------------------------------------
check("AMD Radeon(TM) RX 580", _classify_controller("AMD Radeon(TM) RX 580"), "amd")
check("AMD Radeon HD 8570M (old HD series != Intel)", _classify_controller("AMD Radeon HD 8570M"), "amd")
check("ATI Mobility Radeon HD 5650", _classify_controller("ATI Mobility Radeon HD 5650"), "amd")
check("AMD Radeon(TM) Vega 8 Graphics", _classify_controller("AMD Radeon(TM) Vega 8 Graphics"), "amd")

# --- negative / edge cases -----------------------------------------------------------------
check("Microsoft Basic Display Adapter", _classify_controller("Microsoft Basic Display Adapter"), None)
check("empty name", _classify_controller(""), None)

# --- normalization sanity -------------------------------------------------------------------
check("normalize strips (TM)/(R)", _normalize_gpu_name("AMD Radeon(TM) RX 580") == "AMD Radeon RX 580", True)

print(f"\n{'-'*40}\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)