# 🚀 Cara Menjalankan YT Short Clipper

## Prerequisites ✅

Pastikan sudah terinstall:
- Python 3.8+ (kami menggunakan 3.12.3)
- pip (package manager Python)

## Step 1: Persiapan (First Time Only)

### Buka Terminal di folder project
```bash
cd /home/mahdev/Automation/yt-short-clipper
```

### Install Dependencies
```bash
pip install --break-system-packages -r requirements.txt
```

**Output yang diharapkan:**
```
Successfully installed customtkinter openai opencv-python numpy Pillow mediapipe requests google-api-python-client google-auth-oauthlib google-auth-httplib2 yt-dlp
```

**Note:** Jika ada error "externally-managed-environment", gunakan `--break-system-packages` flag

## Step 2: Jalankan Aplikasi

### Cara 1: Dengan Python (Recommended)
```bash
python app.py
```

### Cara 2: Dengan Python Explicit
```bash
python3 app.py
```

### Cara 3: Background Mode (Optional)
```bash
nohup python app.py > app.log 2>&1 &
```

## Step 3: Menggunakan Aplikasi

### Pertama Kali (Setup)

1. **Klik tombol "Settings" (⚙️)**
2. **Tab: AI API Settings**
   - Pilih provider AI Anda (OpenAI, Google Gemini, Groq, dll)
   - Masukkan API key
   - Klik "Save"
3. **Tab: YouTube Settings** (Optional)
   - Masukkan YouTube credentials untuk upload otomatis
4. **Kembali ke Home**

### Proses Video

1. **Klik "Browse"** atau paste YouTube URL
2. **Masukkan jumlah clips yang ingin dibuat** (default: 3)
3. **Klik "Generate"**
4. **Tunggu proses selesai:**
   - [1/4] Fetch transcript
   - [2/4] Finding highlights
   - [3/4] Cut & generate captions
   - [4/4] Render video
5. **Lihat hasil di tab "Results"**
6. **Klik tombol hasil untuk preview/download**

## Troubleshooting 🔧

### Error: `ModuleNotFoundError: No module named 'customtkinter'`
**Solution:**
```bash
pip install --break-system-packages -r requirements.txt
```

### Error: `Failed to call Gemini API: 403 Forbidden`
**Solution:**
1. Buka Settings → AI API Settings → Google Gemini
2. Generate API key baru dari https://aistudio.google.com/app/apikey
3. Paste key baru
4. Klik Save
5. Restart aplikasi

### Error: `yt-dlp not found`
**Solution:**

Option 1 (Recommended - Install as user package):
```bash
pip install --user yt-dlp
```

Option 2 (System-wide):
```bash
pip install --break-system-packages yt-dlp
```

Option 3 (Using run.sh wrapper):
```bash
bash run.sh
```

The app automatically detects yt-dlp in:
1. Bundled location (yt-dlp.exe on Windows)
2. User package directory (~/.local/bin/)
3. System PATH

### Aplikasi jalan tapi blank/tidak load
**Solution:**
1. Tunggu 3-5 detik (loading UI)
2. Jika masih blank, tutup dan jalankan lagi
3. Check logs: `tail -f error.log` (jika ada)

## Advanced: Custom Settings

### Edit Config Manual
```bash
nano ~/.config/yt-short-clipper/config.json
```

### Field-field penting:
```json
{
  "ai_providers": {
    "default": "openai",
    "openai": {"api_key": "sk-...", "model": "gpt-4"},
    "google": {"api_key": "AIza...", "model": "gemini-2.5-flash"},
    "groq": {"api_key": "gsk-...", "model": "mixtral-8x7b-32768"}
  },
  "temperature": 1.0,
  "system_prompt": "...",
  "output_directory": "./output"
}
```

## File Structure

```
yt-short-clipper/
├── app.py                 ← Main application (run this!)
├── clipper_core.py        ← Core video processing logic
├── requirements.txt       ← Dependencies
├── config/
│   └── config_manager.py  ← Configuration handler
├── pages/
│   ├── browse_page.py
│   ├── settings_page.py
│   ├── results_page.py
│   └── status_pages.py
├── dialogs/
├── components/
├── utils/
└── output/                ← Generated videos go here
```

## Useful Commands

### Check if app is running
```bash
ps aux | grep "python app.py"
```

### Stop background app
```bash
pkill -f "python app.py"
```

### View application logs
```bash
tail -f ~/.config/yt-short-clipper/error.log
```

### Clear old output files
```bash
rm -rf ~/Automation/yt-short-clipper/output/*
```

### Reinstall dependencies (clean)
```bash
pip uninstall --break-system-packages -y customtkinter openai opencv-python numpy Pillow mediapipe requests
pip install --break-system-packages -r requirements.txt
```

## UI Overview

### Main Screens

1. **Home** 🏠
   - Paste YouTube URL atau pilih video file
   - Tentukan jumlah clips
   - Klik "Generate"

2. **Settings** ⚙️
   - AI API Configuration
   - YouTube Settings
   - Output Format
   - Watermark & Visual Effects
   - Social Media Accounts

3. **Status** 📊
   - Check API provider status
   - View current configuration
   - Refresh status

4. **Results** 📁
   - Preview & download generated clips
   - Reorder/delete clips
   - Direct upload to YouTube/TikTok

5. **Contact** 📧
   - Get help & support info

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Q` | Quit application |
| `Ctrl+S` | Save current config |
| `Ctrl+R` | Refresh status |
| `F1` | Open help |
| `F5` | Refresh current page |

## System Requirements

- **OS**: Windows, macOS, Linux
- **Python**: 3.8+
- **RAM**: 4GB minimum (8GB recommended)
- **Storage**: 5GB for dependencies + output
- **Internet**: Required (for API calls & YouTube)
- **GPU**: Optional (improves performance)

## Performance Tips

1. **Close other applications** untuk hemat RAM
2. **Gunakan OpenAI GPT-4** untuk hasil terbaik (berbayar)
3. **Gunakan Groq API** untuk proses super cepat (gratis)
4. **Set temperature lebih rendah** untuk consistency
5. **Process satu video sekaligus** (jangan parallel)

## Support & Help

- **GitHub Issues**: https://github.com/jipraks/yt-short-clipper/issues
- **Documentation**: Baca CONTRIBUTING.md
- **Error Log**: Check ~/.config/yt-short-clipper/error.log
- **API Status**: Buka Settings → Status tab

---

**Status**: ✅ Aplikasi siap dijalankan!
