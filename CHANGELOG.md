# Changelog

## [2.0.35-beta] - 2026-09-17
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