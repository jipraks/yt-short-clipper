# YT-Short-Clipper

🎬 **Automated YouTube to Short-Form Content Pipeline**

Transform long-form YouTube videos (podcasts, interviews, vlogs) into engaging short-form content for TikTok, Instagram Reels, and YouTube Shorts — all with a single command.

## ✨ Features

- **🎥 Auto Download** - Downloads YouTube videos with Indonesian subtitles using yt-dlp
- **🔍 AI Highlight Detection** - Uses GPT-4 to identify the most engaging segments (60-120 seconds)
- **✂️ Smart Clipping** - Automatically cuts video at optimal timestamps
- **📱 Portrait Conversion** - Converts landscape (16:9) to portrait (9:16) with intelligent speaker tracking
- **🎯 Face Detection** - Tracks speakers and switches focus based on who's talking
- **🪝 Hook Generation** - Creates attention-grabbing intro scenes with AI-generated text and TTS voiceover
- **📝 Auto Captions** - Adds CapCut-style word-by-word highlighted captions using Whisper
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

## 📋 Requirements

### System Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| Python | 3.10+ | Runtime |
| FFmpeg | 4.4+ | Video processing |
| yt-dlp | Latest | YouTube downloading |

### Python Dependencies

```
openai>=1.0.0
python-dotenv>=1.0.0
opencv-python>=4.8.0
numpy>=1.24.0
openai-whisper>=20231117
```

### API Keys

- **OpenAI API Key** - Required for GPT-4 (highlight detection) and TTS (hook voiceover)

## 🚀 Installation

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
pip install openai python-dotenv opencv-python numpy openai-whisper
```

Or using requirements.txt:
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
OPENAI_APIKEY=your_openai_api_key_here
```

## 📖 Usage

### Quick Start (All-in-One)

The main script handles the entire pipeline:

```bash
# Interactive mode
python auto-clipper/main.py

# Command line mode
python auto-clipper/main.py <youtube_url> [num_clips]

# Example
python auto-clipper/main.py "https://www.youtube.com/watch?v=xxxxx" 5
```

### Individual Modules

You can also use each module separately:

#### 1. Download Video + Subtitle

```bash
python auto-clipper/downloader.py <youtube_url>
```

**Output:** `downloads/video_title.mp4` + `downloads/video_title.id.srt`

#### 2. Find Highlights

```bash
python auto-clipper/highlight_finder.py <srt_file> [num_clips]
```

**Output:** `downloads/video_title.highlights.json`

#### 3. Clip Video

```bash
python auto-clipper/video_clipper.py <video_file> <highlights_json>
```

**Output:** `clips/clip_01_title.mp4`, `clips/clip_02_title.mp4`, ...

#### 4. Convert to Portrait

```bash
python auto-clipper/portrait_converter.py <input_video> [output_video]
```

**Output:** `input_portrait.mp4`

#### 5. Add Captions

```bash
python auto-clipper/caption_generator.py <input_video> [output_video] [model_size]
```

**Model sizes:** `tiny`, `base`, `small`, `medium`, `large`

**Output:** `input_captioned.mp4`

#### 6. Add Hook Scene

```bash
python auto-clipper/hook_generator.py <clip_path> "<hook_text>"
```

**Output:** `clip_hooked.mp4`

## 📁 Output Structure

```
output/
├── _temp/                          # Temporary files (source video, subtitles)
│   ├── source.mp4
│   ├── source.id.srt
│   └── video_info.json
│
├── 20240115-143001/               # Clip folder (timestamp-based)
│   ├── master.mp4                 # Final clip (portrait + hook + captions)
│   └── data.json                  # Metadata (title, description, timestamps)
│
├── 20240115-143002/
│   ├── master.mp4
│   └── data.json
│
└── ...
```

### data.json Structure

```json
{
  "title": "🔥 Momen Kocak Saat Pembully Datang Minta Maaf",
  "description": "Siapa sangka mantan pembully malah datang minta endorse! 😂 #podcast #viral #fyp",
  "original_title": "Mantan Pembully Datang ke Rumah",
  "hook_text": "Mantan pembully TIARA datang ke rumah minta endorse salad buah",
  "hook_duration": 3.5,
  "start_time": "00:15:23,000",
  "end_time": "00:17:05,000",
  "duration_seconds": 102.0,
  "hook_added": true
}
```

## ⚙️ Configuration

### Highlight Detection Parameters

In `main.py` and `highlight_finder.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `num_clips` | 5 | Number of clips to generate |
| `min_duration` | 60s | Minimum clip duration |
| `max_duration` | 120s | Maximum clip duration |
| `target_duration` | 90s | Ideal clip duration |

### Portrait Conversion Parameters

In `portrait_converter.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `output_resolution` | 1080x1920 | Output video resolution |
| `min_frames_before_switch` | 210 | Frames before speaker switch (~7s at 30fps) |
| `switch_threshold` | 3.0 | Movement multiplier to trigger switch |

### Caption Parameters

In `caption_generator.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `model_size` | base | Whisper model (tiny/base/small/medium/large) |
| `language` | id | Transcription language |
| `chunk_size` | 4 | Words per caption line |

### Hook Generation Parameters

In `hook_generator.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `tts_voice` | nova | OpenAI TTS voice (nova/shimmer/alloy) |
| `tts_speed` | 1.0 | Speech speed |
| `max_words` | 15 | Maximum words in hook text |

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

### Common Issues

**1. "No Indonesian subtitle found"**
- The video might not have auto-generated Indonesian subtitles
- Try a different video or manually provide an SRT file

**2. "FFmpeg not found"**
- Ensure FFmpeg is installed and in your system PATH
- Run `ffmpeg -version` to verify

**3. "OpenAI API error"**
- Check your API key in `.env`
- Ensure you have sufficient API credits
- Verify internet connection

**4. "Face detection not working"**
- Ensure OpenCV is properly installed
- The video might not have clear face visibility
- Try adjusting `minNeighbors` parameter in face detection

**5. "Whisper model download failed"**
- Check internet connection
- Try a smaller model size (tiny/base)
- Manually download model: `whisper --model base`

### Performance Tips

- Use `base` Whisper model for faster processing (vs `large`)
- Process videos under 2 hours for optimal memory usage
- Use SSD storage for faster video I/O
- Close other applications during processing

## 📊 API Usage & Costs

Estimated OpenAI API costs per video:

| Feature | Model | Est. Cost |
|---------|-------|-----------|
| Highlight Detection | GPT-4 | ~$0.10-0.30 |
| Hook Text Generation | GPT-4o-mini | ~$0.01 |
| SEO Metadata | GPT-4o-mini | ~$0.01/clip |
| TTS Voiceover | TTS-1 | ~$0.015/clip |

**Total estimate:** ~$0.15-0.40 per video (5 clips)

## 🤝 Contributing

Contributions are welcome! Kami sangat menghargai kontribusi dari siapapun.

### Quick Start untuk Kontributor

```bash
# 1. Fork repo ini (klik tombol Fork di GitHub)

# 2. Clone fork kamu
git clone https://github.com/USERNAME-KAMU/yt-short-clipper.git
cd yt-short-clipper

# 3. Tambahkan upstream remote
git remote add upstream https://github.com/OWNER/yt-short-clipper.git

# 4. Buat branch baru
git checkout -b feature/fitur-baru-kamu

# 5. Lakukan perubahan, lalu commit
git add .
git commit -m "feat: deskripsi perubahan"

# 6. Push ke fork kamu
git push origin feature/fitur-baru-kamu

# 7. Buat Pull Request di GitHub
```

### Cara Kontribusi

| Jenis | Deskripsi |
|-------|-----------|
| 🐛 **Bug Report** | Laporkan bug di tab [Issues](../../issues) |
| 💡 **Feature Request** | Request fitur baru di [Issues](../../issues) |
| 📖 **Documentation** | Improve docs, fix typo, tambah contoh |
| 🔧 **Code** | Fix bug, tambah fitur, improve performance |

📚 **Panduan lengkap ada di [CONTRIBUTING.md](CONTRIBUTING.md)** - termasuk tutorial Git untuk pemula!

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
| 🎬 | [Aji Prakoso's YouTube](https://youtube.com/@jipraks) |
| 🌐 | [About Aji Prakoso](https://www.jipraks.com) |