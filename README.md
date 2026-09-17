# yt-short-clipper v2

Desktop app that turns long-form YouTube videos into 9:16 short-form clips, with AI highlight detection, face-tracking reframe, and word-by-word captions.

## Latest Release

- **Version:** 2.0.35-beta (see [CHANGELOG](./CHANGELOG.md))
- **License:** MIT
- **Repository:** https://github.com/jipraks/yt-short-clipper

## Features

- AI-powered highlight detection (YouTube heatmap / LLM)
- Face‑tracking portrait reframing (MediaPipe) – top pane 80 % of 9:16 frame
- Split‑screen layout: portrait main video (80 %) + lenskep/webcam preview (20 %)
- Word‑by‑word captions (Whisper‑based)
- Dark theme `#0c0c1c` with gold/emerald accents, Space Grotesk + DM Sans fonts
- Portable Windows build (Tauri + PyInstaller sidecar)

## Build & Release

See the skill `yt-short-clipper` for detailed steps:

```bash
# Install dependencies
npm run deps

# Build sidecar (Windows PowerShell required)
npm run build:sidecar

# Build frontend
npm run build

# Build Tauri binary
npm run tauri build

# Package portable zip
npm run package
```

Or run the full release pipeline:

```bash
npm run release
```

## Development

```bash
npm run dev   # Vite dev server
```

## Changelog

Full changelog is available in [CHANGELOG.md](./CHANGELOG.md).

## Contributing

Feel free to open issues or submit pull requests. Please follow the existing code style and add tests where applicable.

---
*Built with ❤️ for Jiwa's Studio.*