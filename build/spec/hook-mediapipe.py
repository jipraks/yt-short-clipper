"""Custom PyInstaller hook for mediapipe to ensure all submodules and data files are collected."""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Force import of mediapipe.solutions before collect_submodules runs
# This ensures lazy-loaded modules are discovered
try:
    import mediapipe
    import mediapipe.python.solutions
    import mediapipe.python.solutions.face_mesh
    import mediapipe.python.solutions.face_detection
    import mediapipe.python.solutions.drawing_utils
    import mediapipe.python.solutions.drawing_styles
    import mediapipe.tasks.python
    import mediapipe.tasks.python.vision
except ImportError:
    pass

hiddenimports = collect_submodules('mediapipe')
datas = collect_data_files('mediapipe', include_py_files=False)

# Also collect the protobuf model files
datas += collect_data_files('mediapipe_model_maker')
