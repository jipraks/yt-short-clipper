# Changelog

## [2.0.37-beta] - 2026-09-17
### Fixed
- **Progress bar sync bug** — progress bar now updates in real-time during video encoding (portrait conversion) and split-screen composition. Previously it stayed at 0% until the very end when "clip saved" log appeared.
- Added real-time encoding progress tracking via "Encoding portrait: XX%" log messages.
- Added split-screen composition progress detection.

### Updated
- Version bump to v2.0.37-beta across all config files.

## [2.0.36-beta] - 2026-09-17
### Added
- **`scripts/build-sidecar.sh`** — one-command PyInstaller build for the Windows sidecar binary (x86_64-pc-windows-msvc), outputs to `src-tauri/binaries/ytclip-sidecar-x86_64-pc-windows-msvc.exe`.
- **Face Landmarker task model** (`models/face_landmarker.task`, ~3.6 MB) bundled into Tauri bundle — enables on-device face detection for portrait/reframe mode without downloading at runtime.

### Updated
- `package.json` sidecar build script hook added (`npm run build:sidecar`).

## [2.0.35-beta] - 2026-09-16
### Updated
- Split‑screen layout changed to portrait mode 9:16 (1080×1920).
- Top pane now occupies **80 %** of the height (1536 px) with refined face‑tracking (MediaPipe Face Landmarker) ensuring the subject stays centered.
- Bottom pane occupies **20 %** (384 px) for the lenskep overlay, with a 6 px gold divider (`#fbbf24`) separating the panes.
- UI retains dark theme `#0c0c1c` with gold/emerald accents, no purple, using Space Grotesk + DM Sans fonts.
- Version bump in `package.json` and `src-tauri/Cargo.toml` to reflect this release.

### Fixed
- Updated version numbers to avoid confusion with previous builds.

### Note
This change affects the `yt_short_clipper_core/split_screen.py` constants (`TOP_RATIO = 0.80`, `DIVIDER_PX = 6`, `DIVIDER_COLOR = "0xFBBF24"`).