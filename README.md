# YT-Short-Clipper

[![Discord](https://img.shields.io/badge/Join-Discord-5865F2?logo=discord&logoColor=white)](https://s.id/ytsdiscord)
[![GitHub Stars](https://img.shields.io/github/stars/jipraks/yt-short-clipper?style=social)](https://github.com/jipraks/yt-short-clipper)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

🎬 **Automated YouTube to Short-Form Content Pipeline**

Transform long-form YouTube videos (podcasts, interviews, vlogs) into engaging short-form content for TikTok, Instagram Reels, and YouTube Shorts — all with a single command.

## 🖥️ Desktop App (Recommended)

Download the portable desktop app — no Python or FFmpeg installation required!

### Quick Start

1. Download `AutoClipper-v1.0.zip` from [Releases](../../releases)
2. Extract to any folder
3. Run `AutoClipper.exe`
4. Enter your OpenAI API key and click "Validate"
5. Paste YouTube URL, set number of clips, and click "Start Processing"

### Desktop App Features

- ✅ **No installation required** — portable single folder
- ✅ **Simple GUI** — just paste URL and click process
- ✅ **API key validation** — instant feedback if key is valid
- ✅ **Real-time progress** — download percentage, processing status
- ✅ **Token usage tracking** — see GPT tokens, Whisper minutes, TTS chars used
- ✅ **Cost estimation** — estimated API cost per session
- ✅ **YouTube Upload** — direct upload to YouTube with SEO-optimized titles & descriptions
- ✅ **Custom AI Prompts** — customize how AI selects highlights (see [SYSTEM_PROMPT.md](SYSTEM_PROMPT.md))
- ✅ **Debug Mode** — console logging when running from terminal (`python app.py`)

### YouTube Upload Setup (Optional)

To enable direct YouTube upload from the app, you need to set up Google Cloud credentials:

#### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Name it "YT Short Clipper" → Click "Create"

#### Step 2: Enable YouTube Data API

1. In sidebar, click "APIs & Services" → "Library"
2. Search for "YouTube Data API v3"
3. Click on it → Click "Enable"

#### Step 3: Configure OAuth Consent Screen

1. Go to "APIs & Services" → "OAuth consent screen"
2. Select "External" → Click "Create"
3. Fill in required fields:
   - **App name:** YT Short Clipper
   - **User support email:** Your email
   - **Developer contact:** Your email
4. Click "Save and Continue"
5. On Scopes page, click "Add or Remove Scopes"
6. Find and select: `https://www.googleapis.com/auth/youtube.upload`
7. Click "Save and Continue"
8. On Test Users page, click "Add Users"
9. Add your Google/YouTube email address
10. Click "Save and Continue"

#### Step 4: Create OAuth Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Application type: **Desktop app**
4. Name: "YT Short Clipper Desktop"
5. Click "Create"
6. Click "Download JSON"
7. Rename the downloaded file to `client_secret.json`
8. Place it in the same folder as `AutoClipper.exe`

#### Step 5: Connect YouTube in App

1. Open YT Short Clipper app
2. Go to Settings (⚙️ button)
3. Click "Connect YouTube"
4. A browser window will open for Google login
5. Select your YouTube channel account
6. Grant permission to upload videos
7. Done! You can now upload directly from the Results page

> **Note:** Your app will be in "Testing" mode, which limits to 100 users. This is fine for personal use. For public distribution, you'd need to submit for Google verification.

### Desktop App Contents

```
AutoClipper/
├── AutoClipper.exe     # Main application
├── ffmpeg/
│   └── ffmpeg.exe      # Bundled FFmpeg
├── yt-dlp.exe          # Bundled yt-dlp
├── output/             # Output clips folder
└── config.json         # Saved settings (auto-created)
```

## ✨ Features

- **🎥 Auto Download** - Downloads YouTube videos with Indonesian subtitles using yt-dlp
- **🔍 AI Highlight Detection** - Uses GPT-4 to identify the most engaging segments (60-120 seconds)
- **✂️ Smart Clipping** - Automatically cuts video at optimal timestamps
- **📱 Portrait Conversion** - Converts landscape (16:9) to portrait (9:16) with intelligent speaker tracking
- **🎯 Face Detection** - Two modes available:
  - **OpenCV (Fast)** - Crops to largest face, faster processing
  - **MediaPipe (Smart)** - Tracks active speaker via lip movement detection, more accurate but 2-3x slower
- **🪝 Hook Generation** - Creates attention-grabbing intro scenes with AI-generated text and TTS voiceover
- **📝 Auto Captions** - Adds CapCut-style word-by-word highlighted captions using Whisper
- **🖼️ Watermark Support** - Add custom watermark with adjustable position, size, and opacity
- **📊 SEO Metadata** - Generates optimized titles and descriptions for each clip

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        YT-Short-Clipper                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    ┌──────────────┐    ┌─────────────┐           │
│  │ YouTube  │───▶│  Downloader  │───▶│  Subtitle   │           │
│  │   URL    │    │   (yt-dlp)   │    │   Parser    │           │
│  └──────────┘    └──────────────┘    └─────────────┘           │
│                                              │                  │
│                                              ▼                  │
│                                    ┌─────────────────┐         │
│                                    │ Highlight Finder│         │
│                                    │    (GPT-4)      │         │
│                                    └─────────────────┘         │
│                                              │                  │
│                                              ▼                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Video Processing                       │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐  │  │
│  │  │   Clipper  │─▶│  Portrait  │─▶│  Hook Generator    │  │  │
│  │  │  (FFmpeg)  │  │ Converter  │  │  (TTS + Overlay)   │  │  │
│  │  └────────────┘  └────────────┘  └────────────────────┘  │  │
│  │                                              │            │  │
│  │                                              ▼            │  │
│  │                                    ┌────────────────┐     │  │
│  │                                    │Caption Generator│    │  │
│  │                                    │   (Whisper)    │     │  │
│  │                                    └────────────────┘     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                              │                  │
│                                              ▼                  │
│                                    ┌─────────────────┐         │
│                                    │  Output Clips   │         │
│                                    │  + Metadata     │         │
│                                    └─────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

## 📋 Requirements (For Development)

### System Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| Python | 3.10+ | Runtime |
| FFmpeg | 4.4+ | Video processing |
| yt-dlp | Latest | YouTube downloading |

### Python Dependencies

```
customtkinter>=5.2.0
openai>=1.0.0
opencv-python>=4.8.0
numpy>=1.24.0
Pillow>=10.0.0
google-api-python-client>=2.100.0
google-auth-oauthlib>=1.1.0
google-auth-httplib2>=0.1.1
```

> **Note:** The app uses OpenAI Whisper API instead of local Whisper model.

### API Keys

- **OpenAI API Key** - Required for GPT-4 (highlight detection), Whisper (captions), and TTS (hook voiceover)

## 🚀 Installation (For Development)

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/yt-short-clipper.git
cd yt-short-clipper
```

### 2. Install System Dependencies

**Windows (using Chocolatey):**
```powershell
choco install ffmpeg yt-dlp
```

**macOS (using Homebrew):**
```bash
brew install ffmpeg yt-dlp
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
pip install yt-dlp
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the App

```bash
python app.py
```

The app will create a `config.json` file on first run where you can save your OpenAI API key and other settings.

## 📁 Project Structure

```
yt-short-clipper/
├── app.py                      # Main GUI application
├── clipper_core.py             # Core processing logic
├── youtube_uploader.py         # YouTube upload functionality
├── requirements.txt            # Python dependencies
├── build.spec                  # PyInstaller build config
├── config.json                 # App settings (auto-created)
├── SYSTEM_PROMPT.md            # AI prompt customization guide
├── BUILD.md                    # Build instructions
├── DEBUG.md                    # Debugging guide
├── assets/                     # App icons
│   ├── icon.png
│   └── icon.ico
└── output/                     # Output clips (auto-created)
    ├── _temp/                  # Temporary files
    │   ├── source.mp4
    │   └── source.id.srt
    └── 20240115-143001/        # Clip folder (timestamp-based)
        ├── master.mp4          # Final clip
        └── data.json           # Metadata
```

### data.json Structure

Each clip folder contains a `data.json` file with metadata:

```json
{
  "title": "🔥 Momen Kocak Saat Pembully Datang Minta Maaf",
  "hook_text": "Mantan pembully TIARA datang ke rumah minta endorse salad buah",
  "start_time": "00:15:23,000",
  "end_time": "00:17:05,000",
  "duration_seconds": 102.0,
  "has_hook": true,
  "has_captions": true,
  "youtube_title": "🔥 Momen Kocak Saat Pembully Datang Minta Maaf",
  "youtube_description": "Siapa sangka mantan pembully malah datang minta endorse! 😂 #podcast #viral #fyp",
  "youtube_tags": ["shorts", "viral", "podcast"],
  "youtube_url": "https://youtube.com/watch?v=xxxxx",
  "youtube_video_id": "xxxxx"
}
```

## ⚙️ Configuration

All settings can be configured through the GUI Settings page (⚙️ button in the app).

### 🎯 AI Provider Selection (NEW! ✨)

The app now features **intelligent AI provider selection** with auto-fill:

**Supported Providers (10+):**
- 🔴 **OpenAI** - GPT-4o, GPT-4, GPT-3.5-turbo (recommended for quality)
- 🔵 **Google Gemini** - Gemini-2.5-flash, Gemini-1.5-pro (free tier available)
- ⚡ **Groq** - Mixtral-8x7b, Llama2-70b (fastest + free)
- 🤖 **Anthropic Claude** - Claude-3-5-sonnet, Claude-3-opus
- And 6 more providers...

**How it works:**
1. Open Settings → AI API Settings
2. Choose any tab (Highlight Finder, Caption Maker, etc.)
3. Click AI Provider dropdown
4. Select your provider
5. ✨ **URL auto-fills** | ✨ **Model auto-loads**
6. Just paste API key and save!

**Setup time: 60 seconds** (vs 5-10 minutes manual setup)

For detailed guide, see: [AI_PROVIDER_SELECTOR.md](AI_PROVIDER_SELECTOR.md)

### Highlight Detection Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `num_clips` | 5 | Number of clips to generate |
| `min_duration` | 60s | Minimum clip duration |
| `max_duration` | 120s | Maximum clip duration |
| `target_duration` | 90s | Ideal clip duration |
| `temperature` | 1.0 | AI creativity (0.0-2.0) |

### Portrait Conversion Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `output_resolution` | 1080x1920 | Output video resolution |
| `min_frames_before_switch` | 210 | Frames before speaker switch (~7s at 30fps) |
| `switch_threshold` | 3.0 | Movement multiplier to trigger switch |

### Caption Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `language` | id | Transcription language |
| `chunk_size` | 4 | Words per caption line |

### Hook Generation Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `tts_voice` | nova | OpenAI TTS voice (nova/shimmer/alloy) |
| `tts_speed` | 1.0 | Speech speed |
| `max_words` | 15 | Maximum words in hook text |
| `tts_model` | tts-1 | TTS model (tts-1 or tts-1-hd) |

## 🔧 How It Works

### 1. Video Download
- Uses yt-dlp to download video in best quality (max 1080p)
- Automatically fetches Indonesian auto-generated subtitles
- Extracts video metadata (title, description, channel)

### 2. Highlight Detection
- Parses SRT subtitle file with timestamps
- Sends transcript to GPT-4 with specific criteria:
  - Punchlines and funny moments
  - Interesting insights
  - Emotional/dramatic moments
  - Memorable quotes
  - Complete story arcs
- Validates duration (60-120 seconds)
- Generates hook text for each highlight

### 3. Portrait Conversion
- Uses OpenCV Haar Cascade for face detection
- Tracks lip movement to identify active speaker
- Implements "camera cut" style switching (not smooth panning)
- Stabilizes crop position within each "shot"
- Maintains 9:16 aspect ratio at 1080x1920

### 4. Hook Generation
- Extracts first frame from clip
- Generates TTS audio using OpenAI's voice API
- Creates intro scene with:
  - Blurred/dimmed first frame background
  - Centered hook text with yellow highlight
  - AI voiceover reading the hook
- Concatenates hook with main clip

### 5. Caption Generation
- Transcribes audio using OpenAI Whisper
- Creates ASS subtitle file with:
  - Word-by-word timing
  - Yellow highlight on current word
  - Black outline and semi-transparent background
- Burns captions into video using FFmpeg

## 🎨 Caption Styling

The captions use CapCut-style formatting:

```
Font: Arial Black
Size: 70px
Color: White (#FFFFFF)
Highlight: Yellow (#00FFFF)
Outline: 4px Black
Shadow: 2px
Position: Lower third (350px from bottom)
```

## 🐛 Troubleshooting

**1. "FFmpeg not found" or "yt-dlp not found"**
- Make sure `ffmpeg/ffmpeg.exe` and `yt-dlp.exe` are in the same folder as `AutoClipper.exe`
- For development: Install FFmpeg and yt-dlp system-wide

**2. "API key tidak valid"**
- Double-check your OpenAI API key
- Ensure you have API credits available
- Check internet connection

**3. App won't start / crashes**
- Try running as Administrator
- Check if antivirus is blocking the app (add exception)
- Make sure you extracted all files from the zip

**4. "No Indonesian subtitle found"**
- The video might not have auto-generated Indonesian subtitles
- Try a different video

**5. "Face detection not working"**
- Ensure OpenCV is properly installed
- The video might not have clear face visibility

### Performance Tips

- Process videos under 2 hours for optimal memory usage
- Use SSD storage for faster video I/O
- Close other applications during processing
- The app uses OpenAI Whisper API for faster transcription

## 📊 API Usage & Costs

Estimated OpenAI API costs per video (5 clips):

| Feature | Model | Est. Cost |
|---------|-------|-----------|
| Highlight Detection | GPT-4.1 | ~$0.05-0.15 |
| TTS Voiceover | TTS-1 | ~$0.01/clip |
| Captions | Whisper API | ~$0.01/clip |

**Total estimate:** ~$0.10-0.25 per video (5 clips)

The desktop app shows real-time token usage and cost estimation during processing.

## 🤝 Contributing

Contributions are welcome! We greatly appreciate contributions from anyone.

### 🔨 Building Desktop App from Source

For developers who want to build the .exe themselves, see the complete guide in [BUILD.md](BUILD.md).

Quick steps:
```bash
# Install dependencies
pip install -r requirements.txt
pip install pyinstaller

# Build
pyinstaller build.spec

# Output: dist/AutoClipper.exe
```

### Quick Start for Contributors

```bash
# 1. Fork this repo (click the Fork button on GitHub)

# 2. Clone your fork
git clone https://github.com/YOUR-USERNAME/yt-short-clipper.git
cd yt-short-clipper

# 3. Add upstream remote
git remote add upstream https://github.com/OWNER/yt-short-clipper.git

# 4. Create a new branch
git checkout -b feature/your-new-feature

# 5. Make changes, then commit
git add .
git commit -m "feat: description of changes"

# 6. Push to your fork
git push origin feature/your-new-feature

# 7. Create a Pull Request on GitHub
```

### How to Contribute

| Type | Description |
|-------|-----------|
| 🐛 **Bug Report** | Report bugs in the [Issues](../../issues) tab |
| 💡 **Feature Request** | Request new features in [Issues](../../issues) |
| 📖 **Documentation** | Improve docs, fix typos, add examples |
| 🔧 **Code** | Fix bugs, add features, improve performance |

📚 **Complete guide available in [CONTRIBUTING.md](CONTRIBUTING.md)** - includes Git tutorial for beginners!

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

- This tool is for personal/educational use only
- Respect YouTube's Terms of Service
- Ensure you have rights to use the content you're processing
- The AI-generated content should be reviewed before publishing

## 🙏 Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube downloading
- [OpenAI Whisper](https://github.com/openai/whisper) - Speech recognition
- [OpenCV](https://opencv.org/) - Computer vision
- [FFmpeg](https://ffmpeg.org/) - Video processing
- [OpenAI API](https://openai.com/) - GPT-4 and TTS

---

## 👨‍💻 Credits

Made with ☕ by **Aji Prakoso** for content creators

| | |
|---|---|
| 🎓 | [n8n & Automation eCourse](https://classroom.jipraks.com) |
| 📸 | [@jipraks on Instagram](https://instagram.com/jipraks) |
| 🎬 | [Aji Prakoso on YouTube](https://youtube.com/@jipraks) |
| 🌐 | [About Aji Prakoso](https://www.jipraks.com) |