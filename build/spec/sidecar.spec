# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Force import MediaPipe Tasks API modules BEFORE collecting submodules
# This ensures PyInstaller discovers the explicit imports used by portrait.py
try:
    import mediapipe
    import mediapipe.tasks
    import mediapipe.tasks.python
    import mediapipe.tasks.python.vision
    import mediapipe.tasks.python.vision.face_landmarker
    print(f"[sidecar.spec] MediaPipe Tasks API pre-imported successfully")
except ImportError as e:
    print(f"[sidecar.spec] WARNING: Could not pre-import mediapipe: {e}")

# Collect ALL mediapipe and cv2 data and submodules
mediapipe_data = collect_data_files('mediapipe', include_py_files=False)
mediapipe_submodules = collect_submodules('mediapipe')

opencv_data = collect_data_files('cv2')
opencv_submodules = collect_submodules('cv2')

numpy_submodules = collect_submodules('numpy')
ytdlp_submodules = collect_submodules('yt_dlp')

# Pillow
pillow_data = collect_data_files('PIL', include_py_files=False)
pillow_submodules = collect_submodules('PIL')

a = Analysis(
    ['../../scripts/sidecar_entry.py'],
    pathex=['../..'],
    binaries=[],
    datas=[
        *mediapipe_data,
        *opencv_data,
        *pillow_data,
    ],
    hiddenimports=[
        'openai',
        'certifi',
        'urllib3',
        'requests',
        'charset_normalizer',
        'idna',
        # PIL/Pillow for hook text overlay
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        # Force MediaPipe Tasks API imports
        'mediapipe.tasks',
        'mediapipe.tasks.python',
        'mediapipe.tasks.python.vision',
        'mediapipe.tasks.python.vision.face_landmarker',
        'mediapipe.tasks.python.vision.face_detector',
        'mediapipe.tasks.python.vision.image_classifier',
        'mediapipe.tasks.python.vision.object_detector',
        'mediapipe.python',
        *mediapipe_submodules,
        *opencv_submodules,
        *numpy_submodules,
        *ytdlp_submodules,
        *pillow_submodules,
    ],
    hookspath=['../../build/spec'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch',
        'torchvision',
        'tensorflow',
        'transformers',
        'datasets',
        'pandas',
        'scipy',
        'sklearn',
        'matplotlib',
        'numba',
        'llvmlite',
        'onnxruntime',
        'pyarrow',
        'sounddevice',
        'sentry_sdk',
        'boto3',
        'botocore',
        'uvicorn',
        'tkinter',
        'IPython',
        'notebook',
        'jedi',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ytclip-sidecar-x86_64-pc-windows-msvc',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
