# Font Licenses

Fonts used for hook text overlays. **Must verify license before bundling for distribution.**

## Fonts

| Font | Files | License Status |
|------|-------|---------------|
| Capo Sfogliato | `Capo_Sfogliato.ttf` | Unknown — not found on DaFont, FontSpace, or CreativeFabrica |
| Gatchina | `Gatchina Regular.ttf`, `Gatchina Bold.ttf`, `Gatchina Regular Italic.ttf`, `Gatchina Bold Italic.ttf` | Unknown — not found on major font sites. Metadata: FontCreator 14.0, Feb 2026 |
| Super Hockey | `Super Hockey.ttf` | Unknown — not found on DaFont. FontSpace shows unrelated fonts |
| Super Kidpop | `Super Kidpop.ttf` | Unknown — not found on major font sites |
| Super Starfish | `Super Starfish.ttf` | Found on DaFont, listed as "100% Free" by fsuarez913 |

## Note

Fonts are currently NOT bundled as Tauri resources (`tauri.conf.json` resources section).
They are only available during development. Before bundling for distribution, either:

1. Verify and document license for each font, then add to `tauri.conf.json` resources
2. Or replace with open-licensed alternatives (e.g., OFL fonts from Google Fonts)

## OFL Font Alternatives (free for commercial use)

- Google Fonts: https://fonts.google.com/
- Font Squirrel (100% Free Commercial): https://www.fontsquirrel.com/
