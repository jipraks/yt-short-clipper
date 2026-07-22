"""
Auto Clipper Core - Processing logic
Refactored to use OpenAI Whisper API instead of local model
"""

import subprocess
import os
import re
import threading
import json
import cv2
import numpy as np
import tempfile
import sys
import time
from pathlib import Path
from datetime import datetime
from openai import OpenAI, APIError, APIConnectionError, RateLimitError, APIStatusError
from utils.logger import debug_log
from utils.helpers import get_deno_path, get_ffmpeg_path, is_ytdlp_module_available

# Setup Deno and FFmpeg in PATH before importing yt-dlp
_deno_path = get_deno_path()
_ffmpeg_path = get_ffmpeg_path()

if _deno_path and Path(_deno_path).exists():
    _deno_dir = str(Path(_deno_path).parent)
    if "PATH" in os.environ:
        if _deno_dir not in os.environ["PATH"]:
            os.environ["PATH"] = f"{_deno_dir}{os.pathsep}{os.environ['PATH']}"
    else:
        os.environ["PATH"] = _deno_dir
    debug_log(f"Deno added to PATH: {_deno_dir}")

if _ffmpeg_path and Path(_ffmpeg_path).exists():
    _ffmpeg_dir = str(Path(_ffmpeg_path).parent)
    if "PATH" in os.environ:
        if _ffmpeg_dir not in os.environ["PATH"]:
            os.environ["PATH"] = f"{_ffmpeg_dir}{os.pathsep}{os.environ['PATH']}"
    else:
        os.environ["PATH"] = _ffmpeg_dir
    debug_log(f"FFmpeg added to PATH: {_ffmpeg_dir}")

# Import yt-dlp module if available
try:
    import yt_dlp
    YTDLP_MODULE_AVAILABLE = True
except ImportError:
    YTDLP_MODULE_AVAILABLE = False


# Hide console window on Windows
SUBPROCESS_FLAGS = 0
if sys.platform == "win32":
    SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW


class SubtitleNotFoundError(Exception):
    """Raised when no subtitle is available for the video.
    
    Carries context needed to offer Whisper transcription fallback.
    """
    def __init__(self, message: str, video_path: str = None, video_info: dict = None, session_dir: str = None):
        super().__init__(message)
        self.video_path = video_path
        self.video_info = video_info or {}
        self.session_dir = session_dir


def _hex_to_rgb(hex_color: str):
    """Convert a #RRGGBB or #RGB string to an (R, G, B) tuple. Falls back to white on bad input."""
    if not isinstance(hex_color, str):
        return (255, 255, 255)
    s = hex_color.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) != 6:
        return (255, 255, 255)
    try:
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except ValueError:
        return (255, 255, 255)


class AutoClipperCore:
    """Core processing logic for Auto Clipper"""
    
    def __init__(
        self,
        client: OpenAI,
        ffmpeg_path: str = "ffmpeg",
        ytdlp_path: str = "yt-dlp",
        output_dir: str = "output",
        model: str = "gpt-4.1",
        tts_model: str = "tts-1",
        temperature: float = 1.0,
        system_prompt: str = None,
        watermark_settings: dict = None,
        credit_watermark_settings: dict = None,
        hook_style_settings: dict = None,
        face_tracking_mode: str = "opencv",
        mediapipe_settings: dict = None,
        ai_providers: dict = None,
        subtitle_language: str = "id",
        log_callback=None,
        progress_callback=None,
        token_callback=None,
        cancel_check=None
    ):
        # Multi-provider support
        self.ai_providers = ai_providers or {}
        
        # Create separate clients for each provider
        if self.ai_providers:
            # Highlight Finder client
            hf_config = self.ai_providers.get("highlight_finder", {})
            self.highlight_client = OpenAI(
                api_key=hf_config.get("api_key", ""),
                base_url=hf_config.get("base_url", "https://api.openai.com/v1")
            )
            self.model = hf_config.get("model", model)
            
            # Caption Maker client (Whisper) — use longer timeout for large audio uploads
            cm_config = self.ai_providers.get("caption_maker", {})
            self.caption_client = OpenAI(
                api_key=cm_config.get("api_key", ""),
                base_url=cm_config.get("base_url", "https://api.openai.com/v1"),
                timeout=600.0  # 10 minutes for large audio files
            )
            self.whisper_model = cm_config.get("model", "whisper-1")
            
            # Hook Maker client (TTS)
            hm_config = self.ai_providers.get("hook_maker", {})
            self.tts_client = OpenAI(
                api_key=hm_config.get("api_key", ""),
                base_url=hm_config.get("base_url", "https://api.openai.com/v1")
            )
            self.tts_model = hm_config.get("model", tts_model)
        else:
            # Fallback to single client (backward compatibility)
            self.highlight_client = client
            self.caption_client = client
            self.tts_client = client
            self.model = model
            self.tts_model = tts_model
            self.whisper_model = "whisper-1"
        
        # Keep original client for backward compatibility
        self.client = client
        
        self.ffmpeg_path = ffmpeg_path
        self.ytdlp_path = ytdlp_path
        self.output_dir = Path(output_dir)
        self.temperature = temperature
        self.system_prompt = system_prompt or self.get_default_prompt()
        self.watermark_settings = watermark_settings or {"enabled": False}
        self.credit_watermark_settings = credit_watermark_settings or {"enabled": False}
        self.hook_style_settings = hook_style_settings or {}
        self.channel_name = ""  # Will be set after download
        self.face_tracking_mode = face_tracking_mode
        self.mediapipe_settings = mediapipe_settings or {
            "lip_activity_threshold": 0.15,
            "switch_threshold": 0.3,
            "min_shot_duration": 90,
            "center_weight": 0.3
        }
        self.subtitle_language = subtitle_language
        self.log = log_callback or print
        self.set_progress = progress_callback or (lambda s, p: None)
        self.report_tokens = token_callback or (lambda gi, go, w, t: None)
        self.is_cancelled = cancel_check or (lambda: False)
        
        # GPU acceleration settings
        self.gpu_enabled = False
        self.gpu_encoder_args = []
        
        # MediaPipe Face Mesh (lazy loaded)
        self.mp_face_mesh = None
        self.mp_drawing = None
        
        # Create temp directory
        self.temp_dir = self.output_dir / "_temp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def enable_gpu_acceleration(self, enabled: bool = True):
        """Enable or disable GPU acceleration for video encoding"""
        self.gpu_enabled = enabled
        
        if enabled:
            try:
                from utils.gpu_detector import GPUDetector
                detector = GPUDetector(self.ffmpeg_path)
                self.gpu_encoder_args = detector.get_encoder_args(use_gpu=True)
                self.log(f"  ⚡ GPU Acceleration: ENABLED")
                self.log(f"  Encoder args: {' '.join(self.gpu_encoder_args)}")
            except Exception as e:
                self.log(f"  ⚠ GPU Acceleration failed to initialize: {e}")
                self.log(f"  Falling back to CPU encoding")
                self.gpu_enabled = False
                self.gpu_encoder_args = []
        else:
            self.log(f"  💻 GPU Acceleration: DISABLED (using CPU)")
            self.gpu_encoder_args = []
    
    def get_video_encoder_args(self) -> list:
        """Get video encoder arguments based on GPU settings"""
        if self.gpu_enabled and self.gpu_encoder_args:
            return self.gpu_encoder_args
        else:
            # Default CPU encoding
            return ['-c:v', 'libx264', '-preset', 'fast', '-crf', '18']

    # ------------------------------------------------------------------
    # GPU encoder safety net
    # ------------------------------------------------------------------
    # Some GPU encoders (h264_qsv, h264_nvenc, h264_amf) reject specific
    # preset/option combinations depending on the FFmpeg build, driver
    # version, or GPU model. When that happens, the FFmpeg call fails very
    # early with messages like:
    #   "Unable to parse "preset" option value ..."
    #   "Error setting option preset to value ..."
    #   "Error applying encoder options"
    # We detect these signatures, swap the GPU encoder args inside the
    # command for plain libx264 (CPU), and retry once. Subsequent calls in
    # the same session also fall back to CPU automatically.
    _CPU_FALLBACK_ARGS = ['-c:v', 'libx264', '-preset', 'fast', '-crf', '18']

    _GPU_ENCODER_NAMES = (
        'h264_nvenc', 'hevc_nvenc',
        'h264_qsv', 'hevc_qsv',
        'h264_amf', 'hevc_amf',
        'h264_videotoolbox', 'hevc_videotoolbox',
        'h264_mf', 'hevc_mf',
    )

    @classmethod
    def _is_gpu_encoder_error(cls, stderr: str) -> bool:
        """Heuristically detect FFmpeg failures caused by GPU encoder options."""
        if not stderr:
            return False
        text = stderr.lower()
        # Mention of any hardware encoder + a known option/init failure phrase
        mentions_hw = any(enc in text for enc in cls._GPU_ENCODER_NAMES)
        failure_phrases = (
            'error applying encoder options',
            'error setting option',
            'unable to parse',
            'no nvenc capable devices found',
            'cannot load nvcuda',
            'cannot load nvencodeapi',
            'failed loading nvenc',
            'device creation failed',
            'no device available',
            'impossible to convert between',
            'function not implemented',
        )
        mentions_failure = any(p in text for p in failure_phrases)
        return mentions_hw and mentions_failure

    @classmethod
    def _swap_cmd_to_cpu_encoder(cls, cmd: list) -> list:
        """Return a copy of cmd with any GPU encoder block replaced by CPU args.

        This walks the command, finds every ``-c:v <hw_encoder>`` and removes
        the encoder + any GPU-specific options that follow it (until the next
        FFmpeg flag or input/output token). It then injects the CPU fallback
        args in the same position. Audio codec args (``-c:a``) are preserved.
        """
        if not cmd:
            return cmd

        # Options that are known to belong to GPU encoders. We strip them
        # together with their value so libx264 doesn't choke on them.
        gpu_only_opts = {
            '-preset', '-rc', '-cq', '-qp', '-qp_i', '-qp_p', '-qp_b',
            '-quality', '-global_quality', '-look_ahead', '-rc_lookahead',
            '-spatial_aq', '-temporal_aq', '-aq-strength', '-tune',
            '-profile:v', '-level', '-b:v', '-maxrate', '-bufsize',
            '-pix_fmt',
        }

        new_cmd = []
        i = 0
        replaced = False
        while i < len(cmd):
            token = cmd[i]
            if token == '-c:v' and i + 1 < len(cmd) and cmd[i + 1] in cls._GPU_ENCODER_NAMES:
                # Inject CPU fallback once
                if not replaced:
                    new_cmd.extend(cls._CPU_FALLBACK_ARGS)
                    replaced = True
                # Skip '-c:v <hw_encoder>'
                i += 2
                # Skip any trailing GPU-specific options
                while i < len(cmd) - 1 and cmd[i] in gpu_only_opts:
                    i += 2
                continue
            new_cmd.append(token)
            i += 1

        # If no GPU encoder was present in cmd but caller still asked for
        # fallback, leave cmd untouched (nothing to swap).
        return new_cmd if replaced else list(cmd)

    def _disable_gpu_acceleration_runtime(self, reason: str = ""):
        """Disable GPU encoding for the rest of this processing session."""
        if not self.gpu_enabled:
            return
        self.gpu_enabled = False
        self.gpu_encoder_args = []
        msg = "  ⚠ GPU encoding disabled for the rest of this session"
        if reason:
            msg += f" ({reason})"
        self.log(msg)
        self.log("  💻 Continuing with CPU encoding (libx264)")

    def _run_ffmpeg_subprocess(self, cmd: list, **kwargs):
        """Run an FFmpeg command with automatic CPU fallback on GPU encoder errors.

        Wraps ``subprocess.run`` and, if the command fails with a signature
        that looks like a GPU encoder problem, rewrites the command to use
        libx264 and retries once. Returns the final ``CompletedProcess``.
        """
        kwargs.setdefault('capture_output', True)
        kwargs.setdefault('text', True)
        kwargs.setdefault('creationflags', SUBPROCESS_FLAGS)

        result = subprocess.run(cmd, **kwargs)
        if result.returncode == 0:
            return result

        stderr = result.stderr or ''
        if not self._is_gpu_encoder_error(stderr):
            return result

        # Looks like a GPU encoder issue: swap to CPU and retry once.
        fallback_cmd = self._swap_cmd_to_cpu_encoder(cmd)
        if fallback_cmd == list(cmd):
            # No GPU encoder found in cmd to swap; return original failure.
            return result

        self.log("  ⚠ FFmpeg failed with GPU encoder error, retrying on CPU...")
        # Pull a short reason line from stderr for the log
        reason_line = next(
            (ln.strip() for ln in stderr.splitlines()
             if 'error' in ln.lower() or 'unable' in ln.lower()),
            ''
        )
        self._disable_gpu_acceleration_runtime(reason_line[:120])

        retry = subprocess.run(fallback_cmd, **kwargs)
        return retry

    def log_ffmpeg_command(self, cmd: list, description: str = "FFmpeg"):
        """Log FFmpeg command for debugging"""
        # Format command nicely
        cmd_str = ' '.join(f'"{arg}"' if ' ' in str(arg) else str(arg) for arg in cmd)
        self.log(f"  🎬 {description} Command:")
        self.log(f"     {cmd_str}")
    
    def _find_system_font_bold(self) -> str:
        """Find a bold system font across platforms"""
        if sys.platform == "win32":
            candidates = [
                "C:/Windows/Fonts/arialbd.ttf",
                "C:/Windows/Fonts/arial.ttf",
                "C:/Windows/Fonts/segoeui.ttf",
            ]
        elif sys.platform == "darwin":
            candidates = [
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/Library/Fonts/Arial Bold.ttf",
                "/Library/Fonts/Arial.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/SFNS.ttf",
            ]
        else:
            candidates = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
            ]
        
        for font in candidates:
            if os.path.exists(font):
                return font
        return None
    
    def _get_ffmpeg_font_path(self) -> str:
        """Get fontfile argument for FFmpeg drawtext filter, platform-aware"""
        font = self._find_system_font_bold()
        if font:
            if sys.platform == "win32":
                # Escape colon for FFmpeg filter on Windows
                escaped = font.replace("\\", "/").replace(":", "\\:")
                return f"fontfile='{escaped}':"
            else:
                return f"fontfile='{font}':"
        # Fallback: let FFmpeg use fontconfig default
        return "font='Arial':"
    
    @staticmethod
    def get_default_prompt():
        """Get default system prompt for highlight detection"""
        return """Kamu adalah EDITOR SHORT-FORM TIER A untuk konten PODCAST viral (TikTok / Reels / Shorts).

OUTPUT ANDA AKAN LANGSUNG DIGUNAKAN UNTUK PRODUKSI.
Kesalahan durasi atau format = GAGAL TOTAL.

==================================================
TUGAS UTAMA (NON-NEGOTIABLE)
============================

Dari transcript di bawah, HASILKAN TEPAT {num_clips} segment.

* TIDAK BOLEH kurang.
* TIDAK BOLEH lebih.
* ARRAY KOSONG DILARANG DALAM KONDISI APAPUN.

Jika kesulitan menemukan segmen bagus, WAJIB tetap menghasilkan {num_clips} dengan strategi penggabungan/perpanjangan.

==================================================
PRINSIP PEMILIHAN CLIP (WAJIB DIPRIORITASKAN)
=============================================

Prioritaskan segmen dengan karakteristik berikut:

1. Ada KONFLIK, ketegangan, kontroversi.
2. Ada PENGAKUAN personal / vulnerability.
3. Ada STATEMENT tajam / opini berani.
4. Ada punchline atau momen lucu kuat.
5. Ada cerita lengkap (setup → buildup → payoff).
6. Ada kalimat yang bisa berdiri sendiri sebagai hook viral.

Hindari:

* Obrolan filler
* Basa-basi
* Transisi topik tanpa payoff
* Penjelasan teknis panjang tanpa emosi

Jika harus memilih, utamakan EMOSI & KONFLIK dibanding edukasi netral.

==================================================
ATURAN DURASI (KRITIS – TIDAK BOLEH DILANGGAR)
==============================================

* Setiap clip HARUS 60–120 detik.
* Target ideal: 85–95 detik.
* Hitung durasi dari timestamp transcript.
* JANGAN estimasi berdasarkan panjang teks.

Jika durasi < 60 detik:
→ PERPANJANG dengan konteks sebelum atau sesudahnya.

Jika durasi > 120 detik:
→ Pangkas bagian yang tidak relevan TANPA merusak alur cerita.

==================================================
STRATEGI WAJIB JIKA SEGMENT IDEAL TIDAK ADA
===========================================

Lakukan salah satu atau kombinasi berikut:

1. Gabungkan beberapa bagian berurutan yang masih satu topik.
2. Tambahkan setup sebelum punchline agar dramatis.
3. Tambahkan payoff setelah cerita agar terasa lengkap.
4. Pangkas filler tapi jaga minimal 60 detik.

DILARANG:

* Menghasilkan clip < 60 detik
* Mengurangi jumlah clip
* Mengabaikan timestamp asli
* Mengarang timestamp

==================================================
STRUKTUR NARATIF YANG DIWAJIBKAN
================================

Setiap clip harus terasa seperti mini-story:

• Awal: Setup / pernyataan pemicu
• Tengah: Konflik / insight / cerita
• Akhir: Punchline / payoff / statement kuat

Jika tidak ada payoff, tambahkan konteks hingga ada.

==================================================
FIELD WAJIB (PERSIS 6 FIELD – TIDAK BOLEH LEBIH/KURANG)
=======================================================

Setiap object HARUS memiliki:

1. "start_time" (string) → Format: "HH:MM:SS,mmm"
2. "end_time" (string) → Format: "HH:MM:SS,mmm"
3. "title" (string) → Maks 60 karakter, padat & click-worthy
4. "description" (string) → Maks 150 karakter, jelaskan kenapa viral
5. "virality_score" (integer) → 1–10 (HARUS ANGKA, BUKAN STRING)
6. "hook_text" (string) → Maks 15 kata

DILARANG:

* Field tambahan
* Field "reason"
* virality_score dalam bentuk string
* Komentar atau teks di luar JSON

==================================================
VIRALITY SCORE (WAJIB OBJEKTIF)
===============================

8–10:

* Kontroversial
* Emosional kuat
* Confession pribadi
* Statement berani
* Punchline keras

5–7:

* Insight menarik
* Cerita cukup engaging
* Momen lucu ringan

1–4:

* Informasi biasa
* Tidak ada emosi
* Tidak ada hook kuat

Jangan kasih semua clip skor tinggi.
Nilai dengan rasional.

==================================================
HOOK TEXT (HARUS TAJAM & MENJUAL)
=================================

WAJIB:

* Maksimal 15 kata
* Bahasa Indonesia casual
* TANPA emoji
* WAJIB menyebut NAMA ORANG yang berbicara
* Harus berupa kutipan, statement tajam, atau punchline

Contoh benar:
"Andre Taulany: Gua hampir bangkrut gara-gara ini"
"Deddy Corbuzier: Banyak podcaster cuma pura-pura sukses"

Hook harus bisa berdiri sendiri sebagai headline viral.

==================================================
SELF-VALIDATION (WAJIB SEBELUM RETURN)
======================================

Periksa:

1. Jumlah segment = {num_clips} ?
2. Semua durasi 60–120 detik ?
3. Semua punya tepat 6 field ?
4. virality_score berupa integer 1–10 ?
5. Tidak ada field lain ?
6. Tidak ada teks di luar JSON ?

Jika ada kesalahan → PERBAIKI sebelum output.

==================================================
OUTPUT FORMAT (STRICT)
======================

Return HANYA JSON array.
Tanpa markdown.
Tanpa penjelasan.
Tanpa komentar.

Format EXACT seperti ini:

[{{"start_time":"HH:MM:SS,mmm","end_time":"HH:MM:SS,mmm","title":"...","description":"...","virality_score":8,"hook_text":"..."}}]

==================================================
KONTEN
======

{video_context}

Transcript:
{transcript}"""
    
    def process(self, url: str, num_clips: int = 5, add_captions: bool = True, add_hook: bool = True):
        """Main processing pipeline"""
        
        # Step 1: Download video
        self.set_progress("Downloading video...", 0.1)
        video_path, srt_path, video_info = self.download_video(url)
        
        # Store channel name for credit watermark
        self.channel_name = video_info.get("channel", "") if video_info else ""
        
        if self.is_cancelled():
            return
        
        if not srt_path:
            raise SubtitleNotFoundError(
                f"No subtitle available for language: {self.subtitle_language.upper()}",
                video_path=video_path,
                video_info=video_info
            )
        
        # Step 2: Find highlights
        self.set_progress("Finding highlights...", 0.3)
        transcript = self.parse_srt(srt_path)
        highlights = self.find_highlights(transcript, video_info, num_clips)
        
        if self.is_cancelled():
            return
        
        if not highlights:
            raise Exception("No valid highlights found!")
        
        # Step 3: Process each clip
        total_clips = len(highlights)
        for i, highlight in enumerate(highlights, 1):
            if self.is_cancelled():
                return
            self.process_clip(video_path, highlight, i, total_clips, add_captions=add_captions, add_hook=add_hook)
        
        # Cleanup
        self.set_progress("Cleaning up...", 0.95)
        self.cleanup()
        
        self.set_progress("Complete!", 1.0)
        self.log(f"\n✅ Created {total_clips} clips in: {self.output_dir}")
    
    def download_video(self, url: str) -> tuple:
        """Download video and subtitle with progress using yt-dlp module or executable"""
        self.log("[1/4] Downloading video & subtitle...")
        
        # Check if using yt-dlp module
        use_module = YTDLP_MODULE_AVAILABLE and self.ytdlp_path == "yt_dlp_module"
        
        if use_module:
            return self._download_video_module(url)
        else:
            return self._download_video_subprocess(url)
    
    def _download_video_module(self, url: str) -> tuple:
        """Download video using yt-dlp Python module API"""
        self.log(f"  Using yt-dlp module v{yt_dlp.version.__version__}")
        
        video_info = {}
        
        # Get FFmpeg and Deno paths
        ffmpeg_path = get_ffmpeg_path()
        deno_path = get_deno_path()
        
        self.log(f"  FFmpeg path: {ffmpeg_path}")
        self.log(f"  Deno path: {deno_path}")
        
        # Setup environment with Deno in PATH
        if deno_path and Path(deno_path).exists():
            deno_dir = str(Path(deno_path).parent)
            if "PATH" in os.environ:
                os.environ["PATH"] = f"{deno_dir}{os.pathsep}{os.environ['PATH']}"
            else:
                os.environ["PATH"] = deno_dir
            self.log(f"  Deno added to PATH: {deno_dir}")
        else:
            self.log(f"  WARNING: Deno not found!")
        
        # Progress hook for yt-dlp
        def progress_hook(d):
            if self.is_cancelled():
                raise Exception("Cancelled by user")
            
            if d['status'] == 'downloading':
                percent_str = d.get('_percent_str', '0%').strip()
                # Extract numeric percent
                match = re.search(r'(\d+\.?\d*)%', percent_str)
                if match:
                    percent = float(match.group(1))
                    self.set_progress(f"Downloading video... {percent:.1f}%", 0.05 + percent / 100 * 0.2)
            elif d['status'] == 'finished':
                self.log("  Download finished, processing...")
                self.set_progress("Processing downloaded file...", 0.25)
        
        # High-quality format selector
        format_selector = "bestvideo[height>=720][height<=2160]+bestaudio/best[height>=720][height<=2160]/bestvideo+bestaudio/best"
        
        # Base yt-dlp options
        ydl_opts = {
            'format': format_selector,
            'format_sort': ['res', 'br'],
            'merge_output_format': 'mp4',
            'outtmpl': str(self.temp_dir / 'source.%(ext)s'),
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': False,
            'extract_flat': False,
        }
        
        # Only request subtitles if a real language is selected (skip for AI transcription mode)
        if self.subtitle_language and self.subtitle_language != "none":
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True
            ydl_opts['subtitleslangs'] = [self.subtitle_language]
            ydl_opts['subtitlesformat'] = 'srt'
        else:
            self.log("  Skipping subtitle download (AI transcription mode)")
        
        # Add Deno JS runtime if available
        if deno_path and Path(deno_path).exists():
            ydl_opts['js_runtimes'] = {'deno': {'path': deno_path}}
            ydl_opts['remote_components'] = ['ejs:github']
            self.log(f"  JS runtime: deno at {deno_path}")
        else:
            self.log(f"  WARNING: Deno not found - some formats may be missing!")
        
        # Add FFmpeg location if available
        if ffmpeg_path and Path(ffmpeg_path).exists():
            ydl_opts['ffmpeg_location'] = str(Path(ffmpeg_path).parent)
            self.log(f"  FFmpeg location: {ydl_opts['ffmpeg_location']}")
            
            # Only add subtitle converter postprocessor if FFmpeg is available AND subtitles requested
            if self.subtitle_language and self.subtitle_language != "none":
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegSubtitlesConvertor',
                    'format': 'srt',
                }]
        else:
            self.log(f"  WARNING: FFmpeg not found - subtitle conversion disabled")
        
        # Add cookies (required)
        from utils.helpers import get_app_dir
        app_dir = get_app_dir()
        cookies_locations = [
            Path("cookies.txt"),  # Current directory
            app_dir / "cookies.txt",  # App directory
        ]
        
        cookies_path = None
        for loc in cookies_locations:
            self.log(f"  Checking cookies at: {loc} - exists: {loc.exists()}")
            if loc.exists():
                cookies_path = loc
                break
        
        if not cookies_path:
            raise Exception("cookies.txt not found!\n\nPlease upload cookies.txt file from home page.")
        
        ydl_opts['cookiefile'] = str(cookies_path)
        self.log(f"  Using cookies from: {cookies_path}")
        
        # Single download attempt (no browser cookies fallback)
        last_error = None
        try:
            self.log(f"  Starting download...")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # First get video info
                self.log("  Fetching video info...")
                info = ydl.extract_info(url, download=False)
                
                if info:
                    video_info = {
                        "title": info.get("title", ""),
                        "description": (info.get("description", "") or "")[:2000],
                        "channel": info.get("channel", ""),
                    }
                    self.log(f"  Title: {video_info['title'][:50]}...")
                
                # Now download
                if self.subtitle_language and self.subtitle_language != "none":
                    self.log(f"  Downloading video with {self.subtitle_language} subtitle...")
                else:
                    self.log(f"  Downloading video (no subtitle, AI transcription mode)...")
                ydl.download([url])
            
            self.log(f"  ✓ Download successful!")
                
        except Exception as e:
            last_error = str(e)
            self.log(f"  ✗ Failed: {last_error[:100]}")
            
            # Provide helpful error message for common issues
            if "403" in last_error or "Forbidden" in last_error:
                raise Exception(
                    "❌ ERROR: YouTube menolak akses (HTTP 403 Forbidden)\n\n"
                    "PENYEBAB:\n"
                    "• Cookies sudah EXPIRED (biasanya 1-2 minggu)\n"
                    "• Cookies tidak lengkap atau tidak valid\n"
                    "• Browser tidak login ke YouTube saat export cookies\n\n"
                    "SOLUSI:\n"
                    "1. Buka youtube.com di browser\n"
                    "2. PASTIKAN sudah LOGIN ke akun YouTube/Google\n"
                    "3. Export cookies BARU menggunakan extension:\n"
                    "   - Chrome/Edge: 'Get cookies.txt LOCALLY'\n"
                    "   - Firefox: 'cookies.txt'\n"
                    "4. Upload cookies.txt yang baru di halaman Home\n\n"
                    "📖 Lihat COOKIES.md untuk panduan lengkap"
                )
            elif "downloaded file is empty" in last_error.lower() or "file is empty" in last_error.lower():
                raise Exception(
                    "❌ ERROR: File video kosong (0 bytes)\n\n"
                    "PENYEBAB:\n"
                    "• YouTube mendeteksi aktivitas BOT\n"
                    "• Cookies tidak cukup kuat untuk akses video content\n"
                    "• Video mungkin memiliki proteksi khusus\n\n"
                    "SOLUSI:\n"
                    "1. Buka browser INCOGNITO/PRIVATE mode\n"
                    "2. Buka youtube.com dan LOGIN ke akun Google\n"
                    "3. Tonton 2-3 video LENGKAP (bukan skip)\n"
                    "4. Buka video yang ingin di-download, tonton sebentar\n"
                    "5. Export cookies BARU dengan extension:\n"
                    "   - Chrome/Edge: 'Get cookies.txt LOCALLY'\n"
                    "   - Firefox: 'cookies.txt'\n"
                    "6. Upload cookies.txt yang baru\n\n"
                    "💡 TIP: Gunakan akun yang aktif menonton YouTube\n"
                    "📖 Lihat COOKIES.md untuk panduan lengkap"
                )
            elif "Sign in to confirm" in last_error or "bot" in last_error.lower():
                raise Exception(
                    "❌ ERROR: YouTube meminta verifikasi bot\n\n"
                    "PENYEBAB:\n"
                    "• Cookies sudah tidak valid\n"
                    "• YouTube mendeteksi aktivitas mencurigakan\n\n"
                    "SOLUSI:\n"
                    "1. Buka youtube.com di browser INCOGNITO/PRIVATE\n"
                    "2. Login ke akun YouTube/Google\n"
                    "3. Tonton 1-2 video untuk 'warm up' akun\n"
                    "4. Export cookies baru\n"
                    "5. Upload cookies.txt yang baru\n\n"
                    "📖 Lihat COOKIES.md untuk panduan lengkap"
                )
            else:
                raise Exception(f"Download failed!\n\n{last_error}")
        
        video_path = self.temp_dir / "source.mp4"
        srt_path = self.temp_dir / f"source.{self.subtitle_language}.srt"
        
        if not srt_path.exists():
            # Check if any subtitle was downloaded (fallback to other languages)
            available_subs = list(self.temp_dir.glob("source.*.srt"))
            if available_subs:
                srt_path = available_subs[0]
                detected_lang = srt_path.stem.split('.')[-1]
                self.log(f"  ⚠ {self.subtitle_language} subtitle not found, using {detected_lang} instead")
            else:
                srt_path = None
                self.log(f"  ✗ No subtitle found for language: {self.subtitle_language}")
        
        return str(video_path), str(srt_path) if srt_path else None, video_info
    
    def _download_video_subprocess(self, url: str) -> tuple:
        """Download video using yt-dlp subprocess (fallback)"""
        # Validate yt-dlp is available
        try:
            version_check = subprocess.run(
                [self.ytdlp_path, "--version"],
                capture_output=True,
                text=True,
                creationflags=SUBPROCESS_FLAGS,
                timeout=5
            )
            if version_check.returncode != 0:
                raise Exception(f"yt-dlp not working properly. Path: {self.ytdlp_path}")
            self.log(f"  Using yt-dlp version: {version_check.stdout.strip()}")
        except FileNotFoundError:
            raise Exception(f"yt-dlp not found at: {self.ytdlp_path}\n\nPlease install yt-dlp or check the path in settings.")
        except subprocess.TimeoutExpired:
            raise Exception(f"yt-dlp not responding. Path: {self.ytdlp_path}")
        except Exception as e:
            raise Exception(f"Failed to validate yt-dlp: {str(e)}")
        
        base_args = []
        try:
            help_result = subprocess.run(
                [self.ytdlp_path, "--help"],
                capture_output=True,
                text=True,
                creationflags=SUBPROCESS_FLAGS,
                timeout=5
            )
            if help_result.returncode == 0:
                help_text = help_result.stdout
                if "--no-impersonate" in help_text:
                    base_args.append("--no-impersonate")
        except Exception:
            pass
        
        # Get video metadata
        self.log("  Fetching video info...")
        meta_cmd = [self.ytdlp_path, "--dump-json", "--no-download", *base_args, url]
        
        result = subprocess.run(
            meta_cmd, 
            capture_output=True, 
            text=True,
            creationflags=SUBPROCESS_FLAGS
        )
        video_info = {}
        
        if result.returncode == 0:
            try:
                yt_data = json.loads(result.stdout)
                video_info = {
                    "title": yt_data.get("title", ""),
                    "description": yt_data.get("description", "")[:2000],
                    "channel": yt_data.get("channel", ""),
                }
                self.log(f"  Title: {video_info['title'][:50]}...")
            except json.JSONDecodeError:
                self.log("  Warning: Could not parse metadata")
        
        # Download video + subtitle with progress
        if self.subtitle_language and self.subtitle_language != "none":
            self.log(f"  Downloading video with {self.subtitle_language} subtitle...")
        else:
            self.log(f"  Downloading video (no subtitle, AI transcription mode)...")
        
        # Try multiple download strategies (fallback on failure)
        download_strategies = [
            {
                "name": "Browser cookies (Chrome)",
                "extra_args": ["--cookies-from-browser", "chrome"]
            },
            {
                "name": "Browser cookies (Edge)",
                "extra_args": ["--cookies-from-browser", "edge"]
            },
            {
                "name": "Simple format (no auth)",
                "extra_args": []
            }
        ]
        
        # High-quality format selector (prioritize 720p+ with fallback)
        format_selector = "bestvideo[height>=720][height<=2160]+bestaudio/best[height>=720][height<=2160]/bestvideo+bestaudio/best"
        
        last_error = None
        for strategy in download_strategies:
            if self.is_cancelled():
                raise Exception("Cancelled by user")
            
            self.log(f"  Trying: {strategy['name']}...")
            
            cmd = [
                self.ytdlp_path,
                "-f", format_selector,
                "--format-sort", "res,br",
                *base_args,
                *strategy["extra_args"],
            ]
            
            # Only request subtitles if a real language is selected
            if self.subtitle_language and self.subtitle_language != "none":
                cmd.extend([
                    "--write-sub", "--write-auto-sub",
                    "--sub-lang", self.subtitle_language,
                    "--convert-subs", "srt",
                ])
            
            cmd.extend([
                "--merge-output-format", "mp4",
                "--newline",
                "-o", str(self.temp_dir / "source.%(ext)s"),
                url
            ])
            
            # Run with realtime progress output
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=SUBPROCESS_FLAGS
            )
            
            last_progress = ""
            output_lines = []
            
            while True:
                if self.is_cancelled():
                    process.terminate()
                    process.wait()
                    raise Exception("Cancelled by user")
                
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                
                line = line.strip()
                output_lines.append(line)
                
                if not line:
                    continue
                    
                # Parse download progress
                if "[download]" in line and "%" in line:
                    match = re.search(r'(\d+\.?\d*)%', line)
                    if match:
                        percent = match.group(1)
                        progress_text = f"  Downloading: {percent}%"
                        if progress_text != last_progress:
                            self.set_progress(f"Downloading video... {percent}%", 0.05 + float(percent) / 100 * 0.2)
                            last_progress = progress_text
                elif "[Merger]" in line or "Merging" in line:
                    self.log("  Merging video & audio...")
                    self.set_progress("Merging video & audio...", 0.25)
            
            # Check if successful
            if process.returncode == 0:
                self.log(f"  ✓ Download successful using: {strategy['name']}")
                break
            else:
                # Capture error for logging
                stderr_output = process.stderr.read() if process.stderr else ""
                error_lines = []
                
                for line in output_lines + stderr_output.split('\n'):
                    line = line.strip()
                    if line and ('ERROR' in line or 'error' in line):
                        error_lines.append(line)
                
                last_error = '\n'.join(error_lines[-5:]) if error_lines else f"Return code {process.returncode}"
                self.log(f"  ✗ Failed: {last_error.split(chr(10))[0][:80]}")  # First line only
                
                # Continue to next strategy
                continue
        else:
            # All strategies failed - provide helpful error message
            if last_error and ("403" in last_error or "Forbidden" in last_error):
                raise Exception(
                    "❌ ERROR: YouTube menolak akses (HTTP 403 Forbidden)\n\n"
                    "PENYEBAB:\n"
                    "• Cookies sudah EXPIRED (biasanya 1-2 minggu)\n"
                    "• Cookies tidak lengkap atau tidak valid\n"
                    "• Browser tidak login ke YouTube saat export cookies\n\n"
                    "SOLUSI:\n"
                    "1. Buka youtube.com di browser\n"
                    "2. PASTIKAN sudah LOGIN ke akun YouTube/Google\n"
                    "3. Export cookies BARU menggunakan extension:\n"
                    "   - Chrome/Edge: 'Get cookies.txt LOCALLY'\n"
                    "   - Firefox: 'cookies.txt'\n"
                    "4. Upload cookies.txt yang baru di halaman Home\n\n"
                    "📖 Lihat COOKIES.md untuk panduan lengkap\n\n"
                    f"Detail error:\n{last_error}"
                )
            elif last_error and ("downloaded file is empty" in last_error.lower() or "file is empty" in last_error.lower()):
                raise Exception(
                    "❌ ERROR: File video kosong (0 bytes)\n\n"
                    "PENYEBAB:\n"
                    "• YouTube mendeteksi aktivitas BOT\n"
                    "• Cookies tidak cukup kuat untuk akses video content\n"
                    "• Video mungkin memiliki proteksi khusus\n\n"
                    "SOLUSI:\n"
                    "1. Buka browser INCOGNITO/PRIVATE mode\n"
                    "2. Buka youtube.com dan LOGIN ke akun Google\n"
                    "3. Tonton 2-3 video LENGKAP (bukan skip)\n"
                    "4. Buka video yang ingin di-download, tonton sebentar\n"
                    "5. Export cookies BARU dengan extension:\n"
                    "   - Chrome/Edge: 'Get cookies.txt LOCALLY'\n"
                    "   - Firefox: 'cookies.txt'\n"
                    "6. Upload cookies.txt yang baru\n\n"
                    "💡 TIP: Gunakan akun yang aktif menonton YouTube\n"
                    "📖 Lihat COOKIES.md untuk panduan lengkap\n\n"
                    f"Detail error:\n{last_error}"
                )
            elif last_error and ("Sign in to confirm" in last_error or "bot" in last_error.lower()):
                raise Exception(
                    "❌ ERROR: YouTube meminta verifikasi bot\n\n"
                    "PENYEBAB:\n"
                    "• Cookies sudah tidak valid\n"
                    "• YouTube mendeteksi aktivitas mencurigakan\n\n"
                    "SOLUSI:\n"
                    "1. Buka youtube.com di browser INCOGNITO/PRIVATE\n"
                    "2. Login ke akun YouTube/Google\n"
                    "3. Tonton 1-2 video untuk 'warm up' akun\n"
                    "4. Export cookies baru\n"
                    "5. Upload cookies.txt yang baru\n\n"
                    "📖 Lihat COOKIES.md untuk panduan lengkap\n\n"
                    f"Detail error:\n{last_error}"
                )
            else:
                raise Exception(f"Download failed after trying all methods!\n\nLast error:\n{last_error}")
        
        video_path = self.temp_dir / "source.mp4"
        srt_path = self.temp_dir / f"source.{self.subtitle_language}.srt"
        
        if not srt_path.exists():
            # Check if any subtitle was downloaded (fallback to other languages)
            available_subs = list(self.temp_dir.glob("source.*.srt"))
            if available_subs:
                srt_path = available_subs[0]
                detected_lang = srt_path.stem.split('.')[-1]
                self.log(f"  ⚠ {self.subtitle_language} subtitle not found, using {detected_lang} instead")
            else:
                srt_path = None
                self.log(f"  ✗ No subtitle found for language: {self.subtitle_language}")
        
        return str(video_path), str(srt_path) if srt_path else None, video_info

    @staticmethod
    def get_available_subtitles(url: str, ytdlp_path: str = "yt-dlp", cookies_path: str = None) -> dict:
        """Get list of available subtitles for a YouTube video
        
        Args:
            url: YouTube video URL
            ytdlp_path: Path to yt-dlp executable or "yt_dlp_module" for module
            cookies_path: Path to cookies.txt file (required)
        
        Returns:
            dict with keys:
                - 'subtitles': list of manual subtitle languages
                - 'automatic_captions': list of auto-generated subtitle languages
                - 'error': error message if failed
        """
        # Language name mapping (common ones)
        lang_names = {
            "en": "English",
            "id": "Indonesian",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "pt": "Portuguese",
            "ru": "Russian",
            "ja": "Japanese",
            "ko": "Korean",
            "zh": "Chinese",
            "ar": "Arabic",
            "hi": "Hindi",
            "it": "Italian",
            "nl": "Dutch",
            "pl": "Polish",
            "tr": "Turkish",
            "vi": "Vietnamese",
            "th": "Thai",
        }
        
        # Check if using yt-dlp module
        use_module = YTDLP_MODULE_AVAILABLE and ytdlp_path == "yt_dlp_module"
        
        if use_module:
            return AutoClipperCore._get_subtitles_module(url, cookies_path, lang_names)
        else:
            return AutoClipperCore._get_subtitles_subprocess(url, ytdlp_path, cookies_path, lang_names)
    
    @staticmethod
    def _get_subtitles_module(url: str, cookies_path: str, lang_names: dict) -> dict:
        """Get subtitles using yt-dlp Python module API"""
        try:
            # Check if cookies.txt exists
            if not cookies_path or not Path(cookies_path).exists():
                return {
                    "error": "cookies.txt not found. Please upload cookies.txt file.",
                    "subtitles": [],
                    "automatic_captions": []
                }
            
            # Validate cookies file has YouTube auth cookies
            # Check both plain cookies (SID, HSID, etc.) and __Secure- prefixed variants
            # Modern browsers/extensions often export only __Secure- versions
            required_cookies = ['SID', 'HSID', 'SSID', 'APISID', 'SAPISID', 'LOGIN_INFO']
            secure_prefixes = ['__Secure-1P', '__Secure-3P']
            found_cookies = []
            try:
                with open(cookies_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for cookie in required_cookies:
                        # Check plain cookie name (tab-separated format)
                        if f"\t{cookie}\t" in content or content.endswith(f"\t{cookie}"):
                            found_cookies.append(cookie)
                        else:
                            # Check __Secure- prefixed variants (e.g. __Secure-3PSID)
                            for prefix in secure_prefixes:
                                secure_name = f"{prefix}{cookie}"
                                if f"\t{secure_name}\t" in content or content.endswith(f"\t{secure_name}"):
                                    found_cookies.append(secure_name)
                                    break
                
                if not found_cookies:
                    debug_log(f"Cookies file missing required auth cookies. Found: {found_cookies}")
                    return {
                        "error": "Invalid cookies.txt - missing YouTube authentication cookies.\n\n"
                                 "Please export fresh cookies from your browser while logged into YouTube.\n\n"
                                 "Required cookies: SID, HSID, SSID, APISID, SAPISID, LOGIN_INFO\n\n"
                                 "Use a browser extension like 'Get cookies.txt LOCALLY' to export.",
                        "subtitles": [],
                        "automatic_captions": []
                    }
                debug_log(f"Found auth cookies: {found_cookies}")
            except Exception as e:
                debug_log(f"Error reading cookies file: {e}")
            
            debug_log(f"Using yt-dlp module v{yt_dlp.version.__version__}")
            debug_log(f"Cookies path: {cookies_path} (exists: {Path(cookies_path).exists()})")
            
            # Setup Deno in PATH if available
            deno_path = get_deno_path()
            ffmpeg_path = get_ffmpeg_path()
            
            if deno_path and Path(deno_path).exists():
                deno_dir = str(Path(deno_path).parent)
                if "PATH" in os.environ:
                    if deno_dir not in os.environ["PATH"]:
                        os.environ["PATH"] = f"{deno_dir}{os.pathsep}{os.environ['PATH']}"
                else:
                    os.environ["PATH"] = deno_dir
                debug_log(f"Deno path added: {deno_dir}")
            
            # yt-dlp options for fetching info only
            # NOTE: Don't use player_client=android with cookies - it bypasses cookie auth
            ydl_opts = {
                'skip_download': True,
                'quiet': False,  # Show warnings for debugging
                'no_warnings': False,
                'cookiefile': str(cookies_path),  # Ensure string path
            }
            
            # Add Deno JS runtime if available
            if deno_path and Path(deno_path).exists():
                ydl_opts['js_runtimes'] = {'deno': {'path': deno_path}}
                ydl_opts['remote_components'] = ['ejs:github']
                debug_log(f"JS runtime: deno at {deno_path}")
            
            # Add FFmpeg location if available
            if ffmpeg_path and Path(ffmpeg_path).exists():
                ydl_opts['ffmpeg_location'] = str(Path(ffmpeg_path).parent)
                debug_log(f"FFmpeg location: {ydl_opts['ffmpeg_location']}")
            
            debug_log(f"yt-dlp opts: cookiefile={ydl_opts['cookiefile']}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                video_data = ydl.extract_info(url, download=False)
            
            if not video_data:
                return {"error": "Failed to fetch video info", "subtitles": [], "automatic_captions": []}
            
            # Extract subtitles (exclude live_chat)
            subtitles = []
            auto_captions = []
            
            # Get manual subtitles
            if "subtitles" in video_data and video_data["subtitles"]:
                for lang_code in video_data["subtitles"].keys():
                    if "live_chat" in lang_code:
                        continue
                    lang_name = lang_names.get(lang_code, lang_code.upper())
                    subtitles.append({"code": lang_code, "name": lang_name})
            
            # Get automatic captions
            if "automatic_captions" in video_data and video_data["automatic_captions"]:
                for lang_code in video_data["automatic_captions"].keys():
                    if "live_chat" in lang_code:
                        continue
                    lang_name = lang_names.get(lang_code, lang_code.upper())
                    auto_captions.append({"code": lang_code, "name": lang_name})
            
            return {
                "subtitles": subtitles,
                "automatic_captions": auto_captions,
                "error": None
            }
            
        except Exception as e:
            debug_log(f"yt-dlp module error: {e}")
            return {"error": str(e), "subtitles": [], "automatic_captions": []}
    
    @staticmethod
    def _get_subtitles_subprocess(url: str, ytdlp_path: str, cookies_path: str, lang_names: dict) -> dict:
        """Get subtitles using yt-dlp subprocess (fallback)"""
        try:
            # Check if cookies.txt exists
            if not cookies_path or not Path(cookies_path).exists():
                return {
                    "error": "cookies.txt not found. Please upload cookies.txt file.",
                    "subtitles": [],
                    "automatic_captions": []
                }
            
            # Setup environment with Deno path if available
            env = os.environ.copy()
            deno_path = get_deno_path()
            if deno_path:
                deno_dir = str(Path(deno_path).parent)
                if "PATH" in env:
                    env["PATH"] = f"{deno_dir}{os.pathsep}{env['PATH']}"
                else:
                    env["PATH"] = deno_dir
                debug_log(f"Deno found at: {deno_path}")
            else:
                debug_log("Deno not found - remote-components may not work")
            
            # Use --dump-json to get structured data
            # NOTE: Don't use player_client=android with cookies - it bypasses cookie auth
            cmd = [ytdlp_path, "--dump-json", "--skip-download", 
                   "--cookies", cookies_path]
            
            # Check for remote-components support (requires Deno)
            try:
                help_result = subprocess.run(
                    [ytdlp_path, "--help"],
                    capture_output=True,
                    text=True,
                    creationflags=SUBPROCESS_FLAGS,
                    timeout=5
                )
                if help_result.returncode == 0:
                    help_text = help_result.stdout
                    
                    # Add remote-components if supported AND Deno is available
                    if "--remote-components" in help_text and deno_path:
                        cmd.extend(["--remote-components", "ejs:github"])
                        debug_log("Added --remote-components ejs:github")
                    
                    # Add no-impersonate if supported
                    if "--no-impersonate" in help_text:
                        cmd.append("--no-impersonate")
                        debug_log("Added --no-impersonate flag")
            except Exception as e:
                debug_log(f"Error checking yt-dlp features: {e}")
            
            # Add URL at the end
            cmd.append(url)
            
            # Log command for debugging
            debug_log(f"Running command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=SUBPROCESS_FLAGS,
                env=env,  # Use modified environment with Deno path
                timeout=30  # Add timeout to prevent hanging
            )
            
            if result.returncode != 0:
                # Log stderr for debugging
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                debug_log(f"yt-dlp stderr: {error_msg}")
                return {"error": f"Failed to fetch video info: {error_msg[:100]}", "subtitles": [], "automatic_captions": []}
            
            # Parse JSON output
            video_data = json.loads(result.stdout)
            
            # Extract subtitles (exclude live_chat)
            subtitles = []
            auto_captions = []
            
            # Get manual subtitles
            if "subtitles" in video_data and video_data["subtitles"]:
                for lang_code in video_data["subtitles"].keys():
                    if "live_chat" in lang_code:
                        continue
                    lang_name = lang_names.get(lang_code, lang_code.upper())
                    subtitles.append({"code": lang_code, "name": lang_name})
            
            # Get automatic captions
            if "automatic_captions" in video_data and video_data["automatic_captions"]:
                for lang_code in video_data["automatic_captions"].keys():
                    if "live_chat" in lang_code:
                        continue
                    lang_name = lang_names.get(lang_code, lang_code.upper())
                    auto_captions.append({"code": lang_code, "name": lang_name})
            
            return {
                "subtitles": subtitles,
                "automatic_captions": auto_captions,
                "error": None
            }
            
        except subprocess.TimeoutExpired:
            return {"error": "Timeout fetching subtitles", "subtitles": [], "automatic_captions": []}
        except json.JSONDecodeError:
            return {"error": "Failed to parse video data", "subtitles": [], "automatic_captions": []}
        except Exception as e:
            return {"error": str(e), "subtitles": [], "automatic_captions": []}
    
    def parse_srt(self, srt_path: str) -> str:
        """Parse SRT to text with timestamps"""
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        pattern = r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\n|\Z)"
        matches = re.findall(pattern, content, re.DOTALL)
        
        lines = []
        for idx, start, end, text in matches:
            clean_text = text.replace("\n", " ").strip()
            lines.append(f"[{start} - {end}] {clean_text}")
        
        return "\n".join(lines)
    
    def extract_transcript_for_highlight(self, srt_path: str, highlight: dict) -> str:
        """Extract subtitle text within a highlight's time range.
        
        Args:
            srt_path: Path to SRT file
            highlight: Dict with start_time and end_time keys
            
        Returns:
            str: Concatenated subtitle text within the time range
        """
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        pattern = r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\n|\Z)"
        matches = re.findall(pattern, content, re.DOTALL)
        
        start_sec = self.parse_timestamp(highlight["start_time"])
        end_sec = self.parse_timestamp(highlight["end_time"])
        
        lines = []
        for idx, start, end, text in matches:
            sub_start = self.parse_timestamp(start)
            sub_end = self.parse_timestamp(end)
            
            # Include subtitle if it overlaps with highlight range
            if sub_end >= start_sec and sub_start <= end_sec:
                clean_text = text.replace("\n", " ").strip()
                if clean_text:
                    lines.append(clean_text)
        
        return " ".join(lines)
    
    def download_subtitle_only(self, url: str) -> tuple:
        """Download only subtitle (no video) using yt-dlp.
        
        Returns:
            tuple: (srt_path, video_info) where srt_path is str or None
        """
        self.log("[1/2] Downloading subtitle only...")
        
        use_module = YTDLP_MODULE_AVAILABLE and self.ytdlp_path == "yt_dlp_module"
        
        if use_module:
            return self._download_subtitle_only_module(url)
        else:
            return self._download_subtitle_only_subprocess(url)
    
    def _download_subtitle_only_module(self, url: str) -> tuple:
        """Download subtitle only using yt-dlp Python module API"""
        self.log(f"  Using yt-dlp module v{yt_dlp.version.__version__}")
        
        video_info = {}
        
        # Get Deno path
        deno_path = get_deno_path()
        ffmpeg_path = get_ffmpeg_path()
        
        # Setup environment with Deno in PATH
        if deno_path and Path(deno_path).exists():
            deno_dir = str(Path(deno_path).parent)
            if "PATH" in os.environ:
                os.environ["PATH"] = f"{deno_dir}{os.pathsep}{os.environ['PATH']}"
            else:
                os.environ["PATH"] = deno_dir
        
        # yt-dlp options: skip video download, only get subtitle
        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': [self.subtitle_language],
            'subtitlesformat': 'srt',
            'outtmpl': str(self.temp_dir / 'source.%(ext)s'),
            'quiet': True,
            'no_warnings': False,
        }
        
        # Add Deno JS runtime if available
        if deno_path and Path(deno_path).exists():
            ydl_opts['js_runtimes'] = {'deno': {'path': deno_path}}
            ydl_opts['remote_components'] = ['ejs:github']
        
        # Add FFmpeg location for subtitle conversion
        if ffmpeg_path and Path(ffmpeg_path).exists():
            ydl_opts['ffmpeg_location'] = str(Path(ffmpeg_path).parent)
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegSubtitlesConvertor',
                'format': 'srt',
            }]
        
        # Add cookies
        from utils.helpers import get_app_dir
        app_dir = get_app_dir()
        cookies_locations = [
            Path("cookies.txt"),
            app_dir / "cookies.txt",
        ]
        
        cookies_path = None
        for loc in cookies_locations:
            if loc.exists():
                cookies_path = loc
                break
        
        if not cookies_path:
            raise Exception("cookies.txt not found!\n\nPlease upload cookies.txt file from home page.")
        
        ydl_opts['cookiefile'] = str(cookies_path)
        
        try:
            self.log(f"  Downloading {self.subtitle_language} subtitle...")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Get video info + download subtitle
                info = ydl.extract_info(url, download=True)
                
                if info:
                    video_info = {
                        "title": info.get("title", ""),
                        "description": (info.get("description", "") or "")[:2000],
                        "channel": info.get("channel", ""),
                    }
                    self.log(f"  Title: {video_info['title'][:50]}...")
            
            self.log(f"  ✓ Subtitle download complete!")
            
        except Exception as e:
            last_error = str(e)
            self.log(f"  ✗ Failed: {last_error[:100]}")
            
            if "403" in last_error or "Forbidden" in last_error:
                raise Exception(
                    "❌ ERROR: YouTube menolak akses (HTTP 403 Forbidden)\n\n"
                    "Cookies sudah EXPIRED. Silakan export cookies baru.\n\n"
                    "📖 Lihat COOKIES.md untuk panduan lengkap"
                )
            else:
                raise Exception(f"Subtitle download failed!\n\n{last_error}")
        
        # Find downloaded subtitle file
        srt_path = self.temp_dir / f"source.{self.subtitle_language}.srt"
        
        if not srt_path.exists():
            available_subs = list(self.temp_dir.glob("source.*.srt"))
            if available_subs:
                srt_path = available_subs[0]
                detected_lang = srt_path.stem.split('.')[-1]
                self.log(f"  ⚠ {self.subtitle_language} subtitle not found, using {detected_lang} instead")
            else:
                srt_path = None
                self.log(f"  ✗ No subtitle found for language: {self.subtitle_language}")
        
        return str(srt_path) if srt_path else None, video_info
    
    def _download_subtitle_only_subprocess(self, url: str) -> tuple:
        """Download subtitle only using yt-dlp subprocess (fallback)"""
        # Validate yt-dlp
        try:
            version_check = subprocess.run(
                [self.ytdlp_path, "--version"],
                capture_output=True, text=True,
                creationflags=SUBPROCESS_FLAGS, timeout=5
            )
            if version_check.returncode != 0:
                raise Exception(f"yt-dlp not working properly. Path: {self.ytdlp_path}")
            self.log(f"  Using yt-dlp version: {version_check.stdout.strip()}")
        except FileNotFoundError:
            raise Exception(f"yt-dlp not found at: {self.ytdlp_path}")
        
        # Get video metadata first
        self.log("  Fetching video info...")
        meta_cmd = [self.ytdlp_path, "--dump-json", "--no-download", url]
        
        # Add cookies
        from utils.helpers import get_app_dir
        app_dir = get_app_dir()
        cookies_path = None
        for loc in [Path("cookies.txt"), app_dir / "cookies.txt"]:
            if loc.exists():
                cookies_path = str(loc)
                break
        
        if cookies_path:
            meta_cmd.extend(["--cookies", cookies_path])
        
        result = subprocess.run(
            meta_cmd, capture_output=True, text=True,
            creationflags=SUBPROCESS_FLAGS, timeout=30
        )
        
        video_info = {}
        if result.returncode == 0:
            try:
                yt_data = json.loads(result.stdout)
                video_info = {
                    "title": yt_data.get("title", ""),
                    "description": yt_data.get("description", "")[:2000],
                    "channel": yt_data.get("channel", ""),
                }
                self.log(f"  Title: {video_info['title'][:50]}...")
            except json.JSONDecodeError:
                self.log("  Warning: Could not parse metadata")
        
        # Download subtitle only
        self.log(f"  Downloading {self.subtitle_language} subtitle...")
        cmd = [
            self.ytdlp_path,
            "--skip-download",
            "--write-sub", "--write-auto-sub",
            "--sub-lang", self.subtitle_language,
            "--convert-subs", "srt",
            "-o", str(self.temp_dir / "source.%(ext)s"),
        ]
        
        if cookies_path:
            cmd.extend(["--cookies", cookies_path])
        
        cmd.append(url)
        
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            creationflags=SUBPROCESS_FLAGS, timeout=30
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            self.log(f"  ✗ Failed: {error_msg[:100]}")
            raise Exception(f"Subtitle download failed!\n\n{error_msg}")
        
        self.log(f"  ✓ Subtitle download complete!")
        
        # Find downloaded subtitle file
        srt_path = self.temp_dir / f"source.{self.subtitle_language}.srt"
        
        if not srt_path.exists():
            available_subs = list(self.temp_dir.glob("source.*.srt"))
            if available_subs:
                srt_path = available_subs[0]
                detected_lang = srt_path.stem.split('.')[-1]
                self.log(f"  ⚠ {self.subtitle_language} subtitle not found, using {detected_lang} instead")
            else:
                srt_path = None
                self.log(f"  ✗ No subtitle found for language: {self.subtitle_language}")
        
        return str(srt_path) if srt_path else None, video_info
    
    def download_video_section(self, url: str, start_time: str, end_time: str, output_path: str) -> str:
        """Download a specific section of a video using yt-dlp --download-sections.
        
        Args:
            url: YouTube video URL
            start_time: Start timestamp (HH:MM:SS,mmm or HH:MM:SS.mmm)
            end_time: End timestamp (HH:MM:SS,mmm or HH:MM:SS.mmm)
            output_path: Path to save the downloaded section
            
        Returns:
            str: Path to downloaded video file
        """
        # Normalize timestamps (replace comma with dot for yt-dlp)
        start_clean = start_time.replace(",", ".")
        end_clean = end_time.replace(",", ".")
        
        use_module = YTDLP_MODULE_AVAILABLE and self.ytdlp_path == "yt_dlp_module"
        
        if use_module:
            return self._download_section_module(url, start_clean, end_clean, output_path)
        else:
            return self._download_section_subprocess(url, start_clean, end_clean, output_path)
    
    def _download_section_module(self, url: str, start_time: str, end_time: str, output_path: str) -> str:
        """Download video section using yt-dlp Python module"""
        self.log(f"  Downloading section {start_time} → {end_time}...")
        
        # Get paths
        ffmpeg_path = get_ffmpeg_path()
        deno_path = get_deno_path()
        
        # Setup Deno in PATH
        if deno_path and Path(deno_path).exists():
            deno_dir = str(Path(deno_path).parent)
            if "PATH" in os.environ:
                if deno_dir not in os.environ["PATH"]:
                    os.environ["PATH"] = f"{deno_dir}{os.pathsep}{os.environ['PATH']}"
            else:
                os.environ["PATH"] = deno_dir
        
        # Progress hook
        def progress_hook(d):
            if self.is_cancelled():
                raise Exception("Cancelled by user")
            
            if d['status'] == 'downloading':
                percent_str = d.get('_percent_str', '0%').strip()
                match = re.search(r'(\d+\.?\d*)%', percent_str)
                if match:
                    percent = float(match.group(1))
                    self.set_progress(f"Downloading video section... {percent:.1f}%", 0)
            elif d['status'] == 'finished':
                self.log("  Section download finished, processing...")
        
        # Format selector
        format_selector = "bestvideo[height>=720][height<=2160]+bestaudio/best[height>=720][height<=2160]/bestvideo+bestaudio/best"
        
        ydl_opts = {
            'format': format_selector,
            'format_sort': ['res', 'br'],
            'merge_output_format': 'mp4',
            'outtmpl': output_path,
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': False,
            'download_ranges': yt_dlp.utils.download_range_func(None, [(
                self.parse_timestamp(start_time),
                self.parse_timestamp(end_time)
            )]),
            'force_keyframes_at_cuts': True,
        }
        
        # Add Deno JS runtime
        if deno_path and Path(deno_path).exists():
            ydl_opts['js_runtimes'] = {'deno': {'path': deno_path}}
            ydl_opts['remote_components'] = ['ejs:github']
        
        # Add FFmpeg location
        if ffmpeg_path and Path(ffmpeg_path).exists():
            ydl_opts['ffmpeg_location'] = str(Path(ffmpeg_path).parent)
        
        # Add cookies
        from utils.helpers import get_app_dir
        app_dir = get_app_dir()
        cookies_path = None
        for loc in [Path("cookies.txt"), app_dir / "cookies.txt"]:
            if loc.exists():
                cookies_path = loc
                break
        
        if not cookies_path:
            raise Exception("cookies.txt not found!")
        
        ydl_opts['cookiefile'] = str(cookies_path)
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            self.log(f"  ✓ Section downloaded!")
            
        except Exception as e:
            last_error = str(e)
            self.log(f"  ✗ Section download failed: {last_error[:100]}")
            raise Exception(f"Failed to download video section!\n\n{last_error}")
        
        # Find the actual output file (yt-dlp may add extension)
        output_dir = Path(output_path).parent
        output_stem = Path(output_path).stem
        
        # Check for exact match first
        if Path(output_path).exists():
            return output_path
        
        # Check for .mp4 variant
        mp4_path = output_dir / f"{output_stem}.mp4"
        if mp4_path.exists():
            return str(mp4_path)
        
        # Search for any file with the stem
        candidates = list(output_dir.glob(f"{output_stem}.*"))
        video_candidates = [c for c in candidates if c.suffix in ('.mp4', '.mkv', '.webm')]
        if video_candidates:
            return str(video_candidates[0])
        
        raise Exception(f"Downloaded section file not found at: {output_path}")
    
    def _download_section_subprocess(self, url: str, start_time: str, end_time: str, output_path: str) -> str:
        """Download video section using yt-dlp subprocess (fallback)"""
        self.log(f"  Downloading section {start_time} → {end_time}...")
        
        # Build section string for yt-dlp
        section_str = f"*{start_time}-{end_time}"
        
        format_selector = "bestvideo[height>=720][height<=2160]+bestaudio/best[height>=720][height<=2160]/bestvideo+bestaudio/best"
        
        cmd = [
            self.ytdlp_path,
            "-f", format_selector,
            "--format-sort", "res,br",
            "--download-sections", section_str,
            "--force-keyframes-at-cuts",
            "--merge-output-format", "mp4",
            "-o", output_path,
        ]
        
        # Add cookies
        from utils.helpers import get_app_dir
        app_dir = get_app_dir()
        cookies_path = None
        for loc in [Path("cookies.txt"), app_dir / "cookies.txt"]:
            if loc.exists():
                cookies_path = str(loc)
                break
        
        if cookies_path:
            cmd.extend(["--cookies", cookies_path])
        
        cmd.append(url)
        
        self.log(f"  Running: {' '.join(cmd[:6])}...")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=SUBPROCESS_FLAGS
        )
        
        while True:
            if self.is_cancelled():
                process.terminate()
                process.wait()
                raise Exception("Cancelled by user")
            
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            
            line = line.strip()
            if "[download]" in line and "%" in line:
                match = re.search(r'(\d+\.?\d*)%', line)
                if match:
                    percent = match.group(1)
                    self.set_progress(f"Downloading video section... {percent}%", 0)
        
        if process.returncode != 0:
            stderr_output = process.stderr.read() if process.stderr else ""
            self.log(f"  ✗ Section download failed: {stderr_output[:200]}")
            raise Exception(f"Failed to download video section!\n\n{stderr_output[:200]}")
        
        self.log(f"  ✓ Section downloaded!")
        
        # Find the actual output file
        output_dir = Path(output_path).parent
        output_stem = Path(output_path).stem
        
        if Path(output_path).exists():
            return output_path
        
        mp4_path = output_dir / f"{output_stem}.mp4"
        if mp4_path.exists():
            return str(mp4_path)
        
        candidates = list(output_dir.glob(f"{output_stem}.*"))
        video_candidates = [c for c in candidates if c.suffix in ('.mp4', '.mkv', '.webm')]
        if video_candidates:
            return str(video_candidates[0])
        
        raise Exception(f"Downloaded section file not found at: {output_path}")
    
    def transcribe_full_video(self, video_path: str) -> str:
        """Transcribe full video audio using Whisper API (Caption Maker).
        
        Extracts audio from the video, compresses to mp3, splits into chunks
        if needed (Whisper API has ~25MB limit), and returns a transcript
        formatted like parse_srt output so find_highlights can consume it directly.
        
        Returns:
            str: Transcript with timestamps in SRT-like format:
                 [HH:MM:SS,mmm - HH:MM:SS,mmm] text
        """
        self.log("[AI Transcription] Transcribing full video with Whisper API...")
        
        # Check Caption Maker is configured
        cm_config = self.ai_providers.get("caption_maker", {})
        if not cm_config.get("api_key"):
            raise Exception(
                "Caption Maker is not configured!\n\n"
                "Please set up Caption Maker in:\n"
                "Settings → AI API Settings → Caption Maker"
            )
        
        # Extract audio as compressed mp3 to minimize file size
        audio_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False).name
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", video_path,
            "-vn",
            "-acodec", "libmp3lame",
            "-ar", "16000",
            "-ac", "1",
            "-b:a", "64k",
            audio_file
        ]
        self.log("  Extracting audio from video...")
        result = subprocess.run(cmd, capture_output=True, text=True, creationflags=SUBPROCESS_FLAGS)
        
        if result.returncode != 0:
            if os.path.exists(audio_file):
                os.unlink(audio_file)
            raise Exception(f"Failed to extract audio from video:\n{result.stderr[:200]}")
        
        file_size_mb = os.path.getsize(audio_file) / (1024 * 1024)
        self.log(f"  Audio file size: {file_size_mb:.1f} MB")
        
        # Get total audio duration
        probe_cmd = [self.ffmpeg_path, "-i", audio_file, "-f", "null", "-"]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, creationflags=SUBPROCESS_FLAGS)
        duration_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", probe_result.stderr)
        total_duration = 0
        if duration_match:
            h, m, s = duration_match.groups()
            total_duration = int(h) * 3600 + int(m) * 60 + float(s)
        
        self.log(f"  Audio duration: {total_duration:.0f}s ({total_duration/60:.1f} min)")
        
        # Report Whisper usage
        self.report_tokens(0, 0, total_duration, 0)
        
        # Split into chunks if file is too large (>4MB to avoid proxy timeout)
        MAX_CHUNK_SIZE_MB = 4
        all_segments = []
        
        if file_size_mb <= MAX_CHUNK_SIZE_MB:
            # Single file, transcribe directly
            self.log("  Sending to Whisper API...")
            self.set_progress("Transcribing audio with AI...", 0.3)
            segments = self._whisper_transcribe_file(audio_file, 0)
            all_segments.extend(segments)
        else:
            # Split into chunks by duration
            chunk_count = int(file_size_mb / MAX_CHUNK_SIZE_MB) + 1
            chunk_duration = total_duration / chunk_count
            self.log(f"  File too large, splitting into {chunk_count} chunks (~{chunk_duration:.0f}s each)...")
            
            for i in range(chunk_count):
                if self.is_cancelled():
                    os.unlink(audio_file)
                    return ""
                
                chunk_start = i * chunk_duration
                chunk_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False).name
                
                cmd = [
                    self.ffmpeg_path, "-y",
                    "-i", audio_file,
                    "-ss", str(chunk_start),
                    "-t", str(chunk_duration),
                    "-acodec", "libmp3lame",
                    "-ar", "16000",
                    "-ac", "1",
                    "-b:a", "64k",
                    chunk_file
                ]
                subprocess.run(cmd, capture_output=True, text=True, creationflags=SUBPROCESS_FLAGS)
                
                chunk_size = os.path.getsize(chunk_file) / (1024 * 1024)
                self.log(f"  Transcribing chunk {i+1}/{chunk_count} ({chunk_size:.1f}MB, ~{chunk_duration:.0f}s)...")
                self.set_progress(f"Transcribing audio chunk {i+1}/{chunk_count}...", 
                                  0.3 + (0.2 * (i + 1) / chunk_count))
                
                segments = self._whisper_transcribe_file(chunk_file, chunk_start)
                all_segments.extend(segments)
                
                try:
                    os.unlink(chunk_file)
                except Exception:
                    pass
        
        # Cleanup main audio file
        try:
            os.unlink(audio_file)
        except Exception:
            pass
        
        if not all_segments:
            raise Exception("Whisper API returned empty transcription. The video may have no speech.")
        
        # Format segments into SRT-like transcript (same format as parse_srt output)
        lines = []
        for seg in all_segments:
            start_ts = self._seconds_to_srt_timestamp(seg["start"])
            end_ts = self._seconds_to_srt_timestamp(seg["end"])
            text = seg["text"].strip()
            if text:
                lines.append(f"[{start_ts} - {end_ts}] {text}")
        
        transcript = "\n".join(lines)
        self.log(f"  ✓ Transcription complete: {len(lines)} segments")
        
        return transcript
    
    def _whisper_transcribe_file(self, audio_path: str, time_offset: float = 0) -> list:
        """Transcribe a single audio file with Whisper API.
        
        Uses raw httpx POST instead of OpenAI SDK for better proxy compatibility.
        
        Args:
            audio_path: Path to audio file
            time_offset: Offset in seconds to add to all timestamps (for chunked files)
        
        Returns:
            list of dicts with 'start', 'end', 'text' keys
        """
        import time as _time
        import requests as _requests
        
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        base_url = str(self.caption_client.base_url).rstrip("/")
        api_key = self.caption_client.api_key
        
        self.log(f"    Uploading {file_size_mb:.1f}MB to Whisper API ({self.whisper_model})...")
        self.log(f"    Base URL: {base_url}")
        
        # Build multipart form data
        url = f"{base_url}/audio/transcriptions"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        form_data = {
            "model": self.whisper_model,
            "response_format": "verbose_json",
        }
        if self.subtitle_language and self.subtitle_language != "none":
            form_data["language"] = self.subtitle_language
        
        # Run API call in a thread so we can log heartbeat while waiting
        response_data = None
        api_error = None
        
        def _call_api():
            nonlocal response_data, api_error
            try:
                with open(audio_path, "rb") as f:
                    files = {"file": (os.path.basename(audio_path), f, "audio/mpeg")}
                    resp = _requests.post(url, headers=headers, data=form_data, files=files, timeout=600)
                    resp.raise_for_status()
                    response_data = resp.json()
            except Exception as e:
                api_error = e
        
        api_thread = threading.Thread(target=_call_api, daemon=True)
        start_time = _time.time()
        api_thread.start()
        
        # Heartbeat: log every 15s so user knows it's still working
        TIMEOUT_SECONDS = 300  # 5 minutes max per chunk
        while api_thread.is_alive():
            api_thread.join(timeout=15)
            if api_thread.is_alive():
                elapsed = _time.time() - start_time
                
                # Check cancellation
                if self.is_cancelled():
                    self.log(f"    ⚠️ Cancelled by user during Whisper API call")
                    return []
                
                if elapsed > TIMEOUT_SECONDS:
                    self.log(f"    ⏱️ Whisper API timed out after {TIMEOUT_SECONDS}s")
                    raise Exception(
                        f"Whisper API timed out after {TIMEOUT_SECONDS}s.\n\n"
                        "Possible causes:\n"
                        "1. Your AI API provider may not support the Whisper audio endpoint\n"
                        "2. The server may be overloaded or unreachable\n"
                        "3. Network connection issue\n\n"
                        "Try:\n"
                        "- Check if your Caption Maker API supports audio transcription\n"
                        "- Try again later\n"
                        "- Use a different API provider for Caption Maker"
                    )
                self.log(f"    ⏳ Waiting for Whisper API response... ({elapsed:.0f}s elapsed)")
                self.set_progress(f"Transcribing with AI... waiting for response ({elapsed:.0f}s)", 0.35)
        
        elapsed = _time.time() - start_time
        
        if api_error:
            self.log(f"  ❌ Whisper API error after {elapsed:.1f}s: {api_error}")
            raise Exception(f"Whisper transcription failed:\n{str(api_error)}")
        
        if response_data is None:
            self.log(f"  ❌ Whisper API returned no response after {elapsed:.1f}s")
            raise Exception("Whisper API returned no response. The endpoint may not support audio transcription.")
        
        self.log(f"    ✓ Whisper API responded in {elapsed:.1f}s")
        
        segments = []
        if "segments" in response_data and response_data["segments"]:
            for seg in response_data["segments"]:
                segments.append({
                    "start": seg.get("start", 0) + time_offset,
                    "end": seg.get("end", 0) + time_offset,
                    "text": seg.get("text", "")
                })
        
        return segments
    
    def _whisper_transcribe_words_api(self, audio_path: str):
        """Transcribe an audio file with word-level timestamps using raw HTTP.

        Compresses the audio to MP3 before uploading (the ytclip proxy drops
        connections for large WAV files >~1MB). Uses ``requests`` instead of
        the OpenAI SDK for proxy compatibility. Tries with
        ``timestamp_granularities[]=word`` first; if the proxy rejects it
        (400), retries without that field (still gets segments).

        Returns an object exposing ``.words`` and ``.segments`` (mirroring the
        SDK response shape consumed by ``create_ass_subtitle_capcut``), or
        raises on failure.
        """
        import requests as _requests
        from types import SimpleNamespace

        base_url = str(self.caption_client.base_url).rstrip("/")
        api_key = self.caption_client.api_key
        url = f"{base_url}/audio/transcriptions"
        headers = {"Authorization": f"Bearer {api_key}"}

        lang = getattr(self, "subtitle_language", None) or "id"

        # Compress WAV → MP3 to reduce upload size (proxy rejects large bodies)
        upload_path = audio_path
        mp3_tmp = None
        if audio_path.lower().endswith(".wav"):
            mp3_tmp = audio_path.rsplit(".", 1)[0] + "_upload.mp3"
            cmd = [
                self.ffmpeg_path, "-y",
                "-i", audio_path,
                "-acodec", "libmp3lame",
                "-b:a", "64k",
                "-ar", "16000",
                "-ac", "1",
                mp3_tmp
            ]
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    creationflags=SUBPROCESS_FLAGS)
            if result.returncode == 0 and os.path.exists(mp3_tmp):
                upload_path = mp3_tmp
                self.log(f"  [Caption] Compressed WAV→MP3: "
                         f"{os.path.getsize(audio_path)/1024:.0f}KB → "
                         f"{os.path.getsize(mp3_tmp)/1024:.0f}KB")
            else:
                self.log("  [Caption] MP3 compression failed, uploading WAV as-is")
                mp3_tmp = None

        file_size_mb = os.path.getsize(upload_path) / (1024 * 1024)
        mime = "audio/mpeg" if upload_path.endswith(".mp3") else "audio/wav"
        self.log(f"  [Caption] Uploading {file_size_mb:.2f}MB to Whisper ({self.whisper_model})...")

        # Attempt 1: with word-level granularity
        form_data = [
            ("model", self.whisper_model),
            ("response_format", "verbose_json"),
            ("timestamp_granularities[]", "word"),
            ("timestamp_granularities[]", "segment"),
        ]
        if lang and lang != "none":
            form_data.append(("language", lang))

        resp = None
        for attempt in range(2):
            with open(upload_path, "rb") as f:
                files = {"file": (os.path.basename(upload_path), f, mime)}
                resp = _requests.post(url, headers=headers, data=form_data,
                                      files=files, timeout=600)

            if resp.status_code == 200:
                break

            # Log the actual error body for debugging
            self.log(f"  [Caption] Attempt {attempt+1} failed: HTTP {resp.status_code}")
            try:
                self.log(f"  [Caption] Response: {resp.text[:300]}")
            except Exception:
                pass

            if attempt == 0:
                # Retry without timestamp_granularities (proxy may not support it)
                self.log("  [Caption] Retrying without timestamp_granularities...")
                form_data = [
                    ("model", self.whisper_model),
                    ("response_format", "verbose_json"),
                ]
                if lang and lang != "none":
                    form_data.append(("language", lang))
            else:
                # Both attempts failed — clean up and raise
                if mp3_tmp and os.path.exists(mp3_tmp):
                    os.unlink(mp3_tmp)
                raise Exception(
                    f"Whisper API returned HTTP {resp.status_code}: "
                    f"{resp.text[:300]}"
                )

        # Clean up temp mp3
        if mp3_tmp and os.path.exists(mp3_tmp):
            os.unlink(mp3_tmp)

        data = resp.json()
        self.log(f"  [Caption] Whisper OK, text length: {len(data.get('text', ''))}")

        words = [
            SimpleNamespace(
                word=w.get("word", ""),
                start=w.get("start", 0.0),
                end=w.get("end", 0.0),
            )
            for w in (data.get("words") or [])
        ]
        segments = data.get("segments") or []
        self.log(f"  [Caption] Got {len(words)} words, {len(segments)} segments")
        return SimpleNamespace(words=words, segments=segments,
                               text=data.get("text", ""))
    
    @staticmethod
    def _seconds_to_srt_timestamp(seconds: float) -> str:
        """Convert seconds to SRT timestamp format HH:MM:SS,mmm"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        ms = int((s - int(s)) * 1000)
        return f"{h:02d}:{m:02d}:{int(s):02d},{ms:03d}"
    
    def find_highlights_with_transcription(self, video_path: str, video_info: dict, 
                                            num_clips: int, session_dir: str = None) -> dict:
        """Find highlights by first transcribing the video with Whisper API.
        
        This is the fallback path when no subtitle is available.
        Uses Caption Maker (Whisper) to generate transcript, then feeds it
        to Highlight Finder (GPT) as usual.
        
        Returns:
            dict: Same session_data format as find_highlights_only
        """
        from datetime import datetime
        
        # Use existing session_dir or create new one
        if session_dir:
            session_dir = Path(session_dir)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_dir = self.output_dir / "sessions" / timestamp
            session_dir.mkdir(parents=True, exist_ok=True)
        
        # Update temp_dir to session-specific temp
        self.temp_dir = session_dir / "_temp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Step 1: Transcribe with Whisper
        self.set_progress("Transcribing video with AI...", 0.3)
        transcript = self.transcribe_full_video(video_path)
        
        if self.is_cancelled():
            return None
        
        # Step 2: Find highlights using the transcript
        self.set_progress("Finding highlights with AI...", 0.6)
        highlights = self.find_highlights(transcript, video_info, num_clips)
        
        if self.is_cancelled():
            return None
        
        if not highlights:
            raise Exception(
                "No valid highlights found!\n\n"
                "Possible causes:\n"
                "1. AI model failed to generate highlights\n"
                "2. Video transcript too short or not suitable\n"
                "3. AI model configuration issue\n\n"
                "Try:\n"
                "- Using a different AI model\n"
                "- Checking AI API settings\n"
                "- Using a longer video with more content"
            )
        
        self.set_progress("Highlights found!", 1.0)
        self.log(f"\n✅ Found {len(highlights)} highlights (via AI transcription)")
        
        # Save session data
        session_data_file = session_dir / "session_data.json"
        session_data = {
            "session_dir": str(session_dir),
            "video_path": video_path,
            "srt_path": None,
            "highlights": highlights,
            "video_info": video_info,
            "created_at": datetime.now().isoformat(),
            "status": "highlights_found",
            "transcription_method": "whisper_api"
        }
        
        with open(session_data_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        self.log(f"Session data saved to: {session_data_file}")
        
        return session_data
    
    def find_highlights(self, transcript: str, video_info: dict, num_clips: int) -> list:
        """Find highlights using AI (OpenAI-compatible API)"""
        self.log(f"[2/4] Finding highlights (using {self.model})...")
        
        request_clips = num_clips + 3
        
        video_context = ""
        if video_info:
            video_context = f"""INFO VIDEO:
- Judul: {video_info.get('title', 'Unknown')}
- Channel: {video_info.get('channel', 'Unknown')}
- Deskripsi: {video_info.get('description', '')[:500]}"""
        
        # Replace placeholders safely (avoid .format() which breaks on user's curly braces)
        prompt = self.system_prompt.replace("{num_clips}", str(request_clips))
        prompt = prompt.replace("{video_context}", video_context)
        prompt = prompt.replace("{transcript}", transcript)
        
        # Warn if required placeholders are missing
        if "{transcript}" in self.system_prompt and "{transcript}" in prompt:
            self.log("  ⚠ Warning: {transcript} placeholder not replaced - check your system prompt")
        if "{num_clips}" in self.system_prompt and "{num_clips}" in prompt:
            self.log("  ⚠ Warning: {num_clips} placeholder not replaced - check your system prompt")

        # Use OpenAI-compatible API for all providers
        self.log(f"  Using API: {self.highlight_client.base_url}")
        try:
            response = self.highlight_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
            )
            
            # Validate response structure
            if not response:
                raise Exception("API returned empty response")
            
            if not hasattr(response, 'choices') or not response.choices:
                # Log response structure for debugging
                self.log(f"  ⚠ Unexpected API response structure: {type(response)}")
                self.log(f"  Response attributes: {dir(response)}")
                raise Exception(
                    "API response missing 'choices' field.\n\n"
                    "This usually happens with custom API providers that don't follow OpenAI format.\n\n"
                    "Please check:\n"
                    "1. API key is valid and has credits\n"
                    "2. Base URL is correct for your provider\n"
                    "3. Model name is supported by your provider\n"
                    "4. Provider follows OpenAI-compatible API format"
                )
            
            if not response.choices[0].message or not response.choices[0].message.content:
                raise Exception(
                    "API returned empty content.\n\n"
                    "Possible causes:\n"
                    "1. Model refused to generate content (content filter)\n"
                    "2. API quota exceeded\n"
                    "3. Model doesn't support this type of request"
                )
            
            # Report token usage (input and output separately)
            if hasattr(response, 'usage') and response.usage:
                self.report_tokens(response.usage.prompt_tokens, response.usage.completion_tokens, 0, 0)
            
            result = response.choices[0].message.content.strip()
            
        except Exception as e:
            # Check if it's our custom exception
            if "API response missing" in str(e) or "API returned empty" in str(e):
                raise
            
            # Otherwise, wrap with more context
            self.log(f"  ❌ API Error: {e}")
            raise Exception(
                f"Failed to get highlights from AI model.\n\n"
                f"Error: {str(e)}\n\n"
                f"Please check:\n"
                f"1. API key is valid: {self.highlight_client.api_key[:20]}...\n"
                f"2. Base URL is correct: {self.highlight_client.base_url}\n"
                f"3. Model exists: {self.model}\n"
                f"4. You have sufficient credits/quota"
            )
        
        # Log raw response for debugging
        self.log(f"  Raw AI response (first 500 chars):\n{result[:500]}")
        
        if result.startswith("```"):
            result = re.sub(r"```json?\n?", "", result)
            result = re.sub(r"```\n?", "", result)
        
        try:
            highlights = json.loads(result)
        except json.JSONDecodeError as e:
            # Log full response on error
            self.log(f"\n❌ JSON Parse Error: {e}")
            self.log(f"\n📄 Full GPT Response:\n{result}")
            self.log(f"\n💡 Error position: line {e.lineno}, column {e.colno}")
            raise Exception(f"Failed to parse GPT response as JSON: {e}\n\nFull response logged above.")
        
        # Filter by duration (min 58s, max 120s)
        valid = []
        for h in highlights:
            # Fallback: convert "reason" to "description" if exists
            if "reason" in h and "description" not in h:
                h["description"] = h.pop("reason")
                self.log(f"  ⚠ Converted 'reason' to 'description' for '{h.get('title', 'Unknown')}'")
            
            duration = self.parse_timestamp(h["end_time"]) - self.parse_timestamp(h["start_time"])
            h["duration_seconds"] = round(duration, 1)
            
            # Ensure virality_score exists (default to 5 if missing)
            if "virality_score" not in h:
                h["virality_score"] = 5
                self.log(f"  ⚠ Missing virality_score for '{h.get('title', 'Unknown')}', defaulting to 5")
            
            # Ensure description exists
            if "description" not in h:
                h["description"] = h.get("title", "No description")
                self.log(f"  ⚠ Missing description for '{h.get('title', 'Unknown')}', using title")
            
            if 58 <= duration <= 120:
                valid.append(h)
                virality = h.get("virality_score", 5)
                self.log(f"  ✓ {h['title']} ({duration:.0f}s) [🔥 {virality}/10]")
            elif duration > 120:
                self.log(f"  ✗ {h['title']} ({duration:.0f}s) - Too long, skipped")
            elif duration < 58:
                self.log(f"  ✗ {h['title']} ({duration:.0f}s) - Too short, skipped")
            
            if len(valid) >= num_clips:
                break
        
        # If we don't have enough valid clips, warn user
        if len(valid) < num_clips:
            self.log(f"\n⚠️ WARNING: Only found {len(valid)} valid clips out of {num_clips} requested!")
            self.log(f"   AI returned many segments that were too short (< 58s).")
            self.log(f"   Consider using a better AI model or adjusting the prompt.")
        
        return valid[:num_clips]
    
    def process_clip(self, video_path: str, highlight: dict, index: int, total_clips: int = 1, add_captions: bool = True, add_hook: bool = True, pre_cut: bool = False):
        """Process a single clip: cut, portrait, hook (optional), captions (optional)
        
        Args:
            video_path: Path to source video (full video or pre-cut section)
            highlight: Highlight dict with metadata
            index: Clip index (1-based)
            total_clips: Total number of clips being processed
            add_captions: Whether to add captions
            add_hook: Whether to add hook
            pre_cut: If True, video_path is already a pre-cut section (skip cutting step)
        """
        
        # Check cancel before starting
        if self.is_cancelled():
            return
        
        # Create output folder with unique timestamp per clip
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S") + f"-{index:02d}"
        clip_dir = self.output_dir / timestamp
        clip_dir.mkdir(parents=True, exist_ok=True)
        
        self.log(f"  Output folder: {clip_dir}")
        
        start = highlight["start_time"].replace(",", ".")
        end = highlight["end_time"].replace(",", ".")
        
        self.log(f"\n[Clip {index}] {highlight['title']}")
        
        # Calculate total steps based on options
        total_steps = 1  # Re-encode/Cut is always 1 step
        total_steps += 1  # Portrait conversion always
        if add_hook:
            total_steps += 1
        if add_captions:
            total_steps += 1
        
        # Helper to report sub-progress with percentage
        def clip_progress(step_name: str, step_num: int, sub_progress: float = 0):
            # Calculate overall progress: base (30%) + clip progress (60%)
            clip_base = 0.3 + (0.6 * (index - 1) / total_clips)
            clip_portion = 0.6 / total_clips
            step_progress = clip_portion * ((step_num + sub_progress) / total_steps)
            overall = clip_base + step_progress
            
            # Format with percentage
            percent = int(sub_progress * 100)
            if percent > 0:
                status = f"Clip {index}/{total_clips}: {step_name} ({percent}%)"
            else:
                status = f"Clip {index}/{total_clips}: {step_name}"
            
            print(f"[DEBUG] clip_progress: {status} (overall: {overall*100:.1f}%)")
            self.set_progress(status, overall)
        
        current_step = 0
        
        # Step 1: Cut video (skip if pre-cut section from --download-sections)
        if self.is_cancelled():
            return
        
        landscape_file = clip_dir / "temp_landscape.mp4"
        duration = self.parse_timestamp(end) - self.parse_timestamp(start)
        
        if pre_cut:
            # Video is already cut to the right section, just re-encode for consistency
            clip_progress("Re-encoding video...", current_step, 0)
            
            encoder_args = self.get_video_encoder_args()
            
            cmd = [
                self.ffmpeg_path, "-y",
                "-i", video_path,
                *encoder_args,
                "-c:a", "aac", "-b:a", "192k",
                "-progress", "pipe:1",
                str(landscape_file)
            ]
            
            self.log_ffmpeg_command(cmd, "Re-encode Pre-cut Section")
            
            self.run_ffmpeg_with_progress(cmd, duration, 
                lambda p: clip_progress("Re-encoding video...", current_step, p))
            
            self.log("  ✓ Re-encoded pre-cut section")
        else:
            # Original flow: cut from full video
            clip_progress("Cutting video...", current_step, 0)
            
            encoder_args = self.get_video_encoder_args()
            
            cmd = [
                self.ffmpeg_path, "-y",
                "-i", video_path,
                "-ss", start, "-to", end,
                *encoder_args,
                "-c:a", "aac", "-b:a", "192k",
                "-progress", "pipe:1",
                str(landscape_file)
            ]
            
            self.log_ffmpeg_command(cmd, "Cut Video")
            
            self.run_ffmpeg_with_progress(cmd, duration, 
                lambda p: clip_progress("Cutting video...", current_step, p))
            
            self.log("  ✓ Cut video")
        
        current_step += 1
        
        # Step 2: Convert to portrait with progress
        if self.is_cancelled():
            return
        clip_progress("Converting to portrait...", current_step, 0)
        portrait_file = clip_dir / "temp_portrait.mp4"
        self.convert_to_portrait_with_progress(str(landscape_file), str(portrait_file), 
            lambda p: clip_progress("Converting to portrait...", current_step, p))
        self.log("  ✓ Portrait conversion")
        current_step += 1
        
        # Track which file is the current output
        current_output = portrait_file
        hook_duration = 0
        
        # Step 3: Add hook (optional)
        if add_hook:
            if self.is_cancelled():
                return
            clip_progress("Adding hook...", current_step, 0)
            hooked_file = clip_dir / "temp_hooked.mp4"
            hook_text = highlight.get("hook_text", highlight["title"])
            hook_duration = self.add_hook_with_progress(str(current_output), hook_text, str(hooked_file),
                lambda p: clip_progress("Adding hook...", current_step, p))
            
            # Verify hooked file was created
            if not hooked_file.exists():
                raise Exception(f"Failed to create hooked video: {hooked_file}")
            
            self.log(f"  ✓ Added hook ({hook_duration:.1f}s)")
            current_output = hooked_file
            current_step += 1
        else:
            self.log("  ⊘ Skipped hook (disabled)")
        
        # Step 4: Add captions (optional)
        final_file = clip_dir / "master.mp4"
        if add_captions:
            if self.is_cancelled():
                return
            clip_progress("Adding captions...", current_step, 0)
            
            # Use portrait_file (without hook) as audio source for transcription
            audio_source = str(portrait_file) if add_hook else None
            
            # If watermark enabled, add captions to temp file first
            if self.watermark_settings.get("enabled"):
                temp_captioned = clip_dir / "temp_captioned.mp4"
                self.add_captions_api_with_progress(str(current_output), str(temp_captioned), audio_source, hook_duration,
                    lambda p: clip_progress("Adding captions...", current_step, p))
                
                if not temp_captioned.exists():
                    raise Exception(f"Failed to create captioned video: {temp_captioned}")
                
                current_output = temp_captioned
            else:
                # No watermark, captions go directly to final
                self.add_captions_api_with_progress(str(current_output), str(final_file), audio_source, hook_duration,
                    lambda p: clip_progress("Adding captions...", current_step, p))
                
                if not final_file.exists():
                    raise Exception(f"Failed to create final video: {final_file}")
            
            self.log("  ✓ Added captions")
            current_step += 1
        else:
            self.log("  ⊘ Skipped captions (disabled)")
        
        # Step 5: Add watermark (if enabled)
        if self.watermark_settings.get("enabled"):
            if self.is_cancelled():
                return
            
            # Check if we need to add watermark step to progress
            if not add_captions:
                # Watermark is a new step
                total_steps += 1
            
            clip_progress("Adding watermark...", current_step, 0)
            
            # Apply watermark to current output
            self.add_watermark_with_progress(str(current_output), str(final_file),
                lambda p: clip_progress("Adding watermark...", current_step, p))
            
            if not final_file.exists():
                raise Exception(f"Failed to create final video with watermark: {final_file}")
            
            self.log("  ✓ Added watermark")
            current_output = final_file
            current_step += 1
            
            # Cleanup temp captioned file if exists
            if add_captions:
                try:
                    temp_captioned = clip_dir / "temp_captioned.mp4"
                    if temp_captioned.exists():
                        temp_captioned.unlink()
                except Exception as e:
                    self.log(f"  Warning: Could not delete temp_captioned.mp4: {e}")
        elif not add_captions:
            # No captions and no watermark, just copy current output to final
            import shutil
            shutil.copy(str(current_output), str(final_file))
            current_output = final_file
        
        # Step 6: Add credit watermark (if enabled)
        if self.credit_watermark_settings.get("enabled") and self.channel_name:
            if self.is_cancelled():
                return
            
            total_steps += 1
            clip_progress("Adding credit...", current_step, 0)
            
            # If current_output is already final_file, we need a temp file
            if str(current_output) == str(final_file):
                temp_credit_input = clip_dir / "temp_before_credit.mp4"
                import shutil
                shutil.copy(str(final_file), str(temp_credit_input))
                current_output = temp_credit_input
            
            self.add_credit_watermark_with_progress(str(current_output), str(final_file),
                lambda p: clip_progress("Adding credit...", current_step, p))
            
            if not final_file.exists():
                raise Exception(f"Failed to create final video with credit: {final_file}")
            
            self.log(f"  ✓ Added credit: Source: {self.channel_name}")
            current_step += 1
            
            # Cleanup temp file
            try:
                temp_credit_input = clip_dir / "temp_before_credit.mp4"
                if temp_credit_input.exists():
                    temp_credit_input.unlink()
            except Exception as e:
                self.log(f"  Warning: Could not delete temp_before_credit.mp4: {e}")
        
        # Mark complete
        clip_progress("Done", total_steps, 0)
        
        # Cleanup temp files
        try:
            if landscape_file.exists():
                landscape_file.unlink()
        except Exception as e:
            self.log(f"  Warning: Could not delete {landscape_file.name}: {e}")
        
        try:
            if portrait_file.exists():
                portrait_file.unlink()
        except Exception as e:
            self.log(f"  Warning: Could not delete {portrait_file.name}: {e}")
        
        if add_hook:
            try:
                hooked_file = clip_dir / "temp_hooked.mp4"
                if hooked_file.exists():
                    hooked_file.unlink()
            except Exception as e:
                self.log(f"  Warning: Could not delete temp_hooked.mp4: {e}")
        
        # Save metadata
        metadata = {
            "title": highlight["title"],
            "hook_text": highlight.get("hook_text", highlight["title"]),
            "start_time": highlight["start_time"],
            "end_time": highlight["end_time"],
            "duration_seconds": highlight["duration_seconds"],
            "has_hook": add_hook,
            "has_captions": add_captions,
            "has_watermark": self.watermark_settings.get("enabled", False),
            "has_credit": self.credit_watermark_settings.get("enabled", False),
            "channel_name": self.channel_name,
        }
        
        with open(clip_dir / "data.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    def convert_to_portrait(self, input_path: str, output_path: str):
        """Convert landscape to 9:16 portrait with speaker tracking (router method)"""
        try:
            if self.face_tracking_mode == "mediapipe":
                self.log("  Using MediaPipe (Active Speaker Detection)")
                return self.convert_to_portrait_mediapipe(input_path, output_path)
            else:
                self.log("  Using OpenCV (Fast Mode)")
                return self.convert_to_portrait_opencv(input_path, output_path)
        except Exception as e:
            # Fallback to OpenCV if MediaPipe fails
            if self.face_tracking_mode == "mediapipe":
                self.log(f"  ⚠ MediaPipe failed: {e}")
                self.log("  Falling back to OpenCV mode...")
                return self.convert_to_portrait_opencv(input_path, output_path)
            else:
                raise
    
    def convert_to_portrait_opencv(self, input_path: str, output_path: str):
        """Convert landscape to 9:16 portrait with speaker tracking (OpenCV Haar Cascade)"""
        
        cap = cv2.VideoCapture(input_path)
        orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Calculate crop dimensions
        target_ratio = 9 / 16
        crop_w = int(orig_h * target_ratio)
        crop_h = orig_h
        out_w, out_h = 1080, 1920
        
        # Face detector
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)
        use_face_detection = not face_cascade.empty()
        
        # First pass: analyze frames
        crop_positions = []
        current_target = orig_w / 2
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(50, 50)) if use_face_detection else []
            
            if len(faces) > 0:
                # Find largest face
                largest = max(faces, key=lambda f: f[2] * f[3])
                current_target = largest[0] + largest[2] / 2
            
            crop_x = int(current_target - crop_w / 2)
            crop_x = max(0, min(crop_x, orig_w - crop_w))
            crop_positions.append(crop_x)
        
        # Stabilize positions
        crop_positions = self.stabilize_positions(crop_positions)
        
        # Second pass: create video
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False).name
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_video, fourcc, fps, (out_w, out_h))
        
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            crop_x = crop_positions[frame_idx] if frame_idx < len(crop_positions) else crop_positions[-1]
            cropped = frame[0:crop_h, crop_x:crop_x+crop_w]
            resized = cv2.resize(cropped, (out_w, out_h), interpolation=cv2.INTER_LANCZOS4)
            out.write(resized)
            frame_idx += 1
        
        cap.release()
        out.release()
        
        # Merge with audio using GPU/CPU encoder
        encoder_args = self.get_video_encoder_args()
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", temp_video,
            "-i", input_path,
            *encoder_args,
            "-c:a", "aac", "-b:a", "192k",
            "-map", "0:v:0", "-map", "1:a:0",
            "-shortest",
            output_path
        ]
        self.log_ffmpeg_command(cmd, "Portrait Merge Audio (OpenCV)")
        self._run_ffmpeg_subprocess(cmd)
        os.unlink(temp_video)
    
    def stabilize_positions(self, positions: list) -> list:
        """Stabilize crop positions - reduce jitter and sudden movements"""
        if not positions:
            return positions
        
        # Use longer window for smoother movement
        window_size = 60  # ~2 seconds at 30fps - longer window = smoother
        stabilized = []
        
        for i in range(len(positions)):
            # Get window around current position
            start = max(0, i - window_size // 2)
            end = min(len(positions), i + window_size // 2)
            window = positions[start:end]
            
            # Use median for stability (resistant to outliers)
            avg = int(np.median(window))
            stabilized.append(avg)
        
        # Second pass: detect shot changes and lock position per shot
        # A shot change is when position jumps significantly
        # Use very high threshold to minimize scene switches
        final = []
        shot_start = 0
        threshold = 250  # pixels - very high threshold = less scene switches
        min_shot_duration = 90  # minimum frames (~3 seconds) before allowing switch
        
        for i in range(len(stabilized)):
            frames_since_last_switch = i - shot_start
            
            # Only allow switch if enough time has passed AND position changed significantly
            if i > 0 and frames_since_last_switch >= min_shot_duration:
                if abs(stabilized[i] - stabilized[shot_start]) > threshold:
                    # Shot change detected - lock previous shot to median
                    shot_positions = stabilized[shot_start:i]
                    if shot_positions:
                        shot_median = int(np.median(shot_positions))
                        final.extend([shot_median] * len(shot_positions))
                    shot_start = i
        
        # Handle last shot
        shot_positions = stabilized[shot_start:]
        if shot_positions:
            shot_median = int(np.median(shot_positions))
            final.extend([shot_median] * len(shot_positions))
        
        return final if final else stabilized
    
    def _init_mediapipe(self):
        """Initialize MediaPipe Face Mesh (lazy loading)"""
        if self.mp_face_mesh is None:
            try:
                import mediapipe as mp
                self.mp_face_mesh = mp.solutions.face_mesh
                self.mp_drawing = mp.solutions.drawing_utils
                self.log("  MediaPipe initialized successfully")
            except ImportError:
                raise Exception("MediaPipe not installed. Run: pip install mediapipe")
    
    def convert_to_portrait_mediapipe(self, input_path: str, output_path: str):
        """Convert landscape to 9:16 portrait with active speaker detection (MediaPipe)"""
        
        # Initialize MediaPipe
        self._init_mediapipe()
        
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise Exception(f"Failed to open video: {input_path}")
        
        orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if total_frames == 0 or fps == 0:
            cap.release()
            raise Exception(f"Invalid video properties: {total_frames} frames, {fps} fps")
        
        # Calculate crop dimensions
        target_ratio = 9 / 16
        crop_w = int(orig_h * target_ratio)
        crop_h = orig_h
        out_w, out_h = 1080, 1920
        
        # MediaPipe Face Mesh settings
        lip_threshold = self.mediapipe_settings.get("lip_activity_threshold", 0.15)
        switch_threshold = self.mediapipe_settings.get("switch_threshold", 0.3)
        min_shot_duration = self.mediapipe_settings.get("min_shot_duration", 90)
        center_weight = self.mediapipe_settings.get("center_weight", 0.3)
        
        # First pass: analyze frames with MediaPipe
        self.log("  Pass 1: Analyzing lip movements...")
        crop_positions = []
        face_activities = []  # Store activity scores per frame
        
        with self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=3,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        ) as face_mesh:
            
            frame_count = 0
            prev_lip_distances = {}  # Track previous lip distances per face
            
            while True:
                if self.is_cancelled():
                    cap.release()
                    raise Exception("Cancelled by user")
                
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Convert to RGB for MediaPipe
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = face_mesh.process(rgb_frame)
                
                best_face_x = orig_w / 2  # Default to center
                max_activity = 0
                
                if results.multi_face_landmarks:
                    faces_data = []
                    
                    for face_id, face_landmarks in enumerate(results.multi_face_landmarks):
                        # Calculate lip activity
                        activity = self._calculate_lip_activity(
                            face_landmarks, 
                            orig_w, 
                            orig_h,
                            prev_lip_distances.get(face_id, None)
                        )
                        
                        # Get face center position
                        face_x = face_landmarks.landmark[1].x * orig_w  # Nose tip
                        
                        # Calculate combined score (activity + center position)
                        center_score = 1.0 - abs(face_x - orig_w / 2) / (orig_w / 2)
                        combined_score = (activity * (1 - center_weight)) + (center_score * center_weight)
                        
                        faces_data.append({
                            'x': face_x,
                            'activity': activity,
                            'combined_score': combined_score
                        })
                        
                        # Update previous lip distance
                        upper_lip = face_landmarks.landmark[13]  # Upper lip center
                        lower_lip = face_landmarks.landmark[14]  # Lower lip center
                        lip_distance = abs(upper_lip.y - lower_lip.y)
                        prev_lip_distances[face_id] = lip_distance
                    
                    # Select face with highest combined score
                    if faces_data:
                        best_face = max(faces_data, key=lambda f: f['combined_score'])
                        best_face_x = best_face['x']
                        max_activity = best_face['activity']
                
                # Calculate crop position
                crop_x = int(best_face_x - crop_w / 2)
                crop_x = max(0, min(crop_x, orig_w - crop_w))
                crop_positions.append(crop_x)
                face_activities.append(max_activity)
                
                frame_count += 1
                
                if frame_count % 30 == 0:
                    self.log(f"    Analyzed {frame_count}/{total_frames} frames...")
        
        self.log(f"  Analyzed {frame_count} frames with MediaPipe")
        
        # Stabilize positions with shot-based switching
        crop_positions = self._stabilize_positions_with_activity(
            crop_positions, 
            face_activities,
            min_shot_duration,
            switch_threshold
        )
        
        # Second pass: create video
        self.log("  Pass 2: Creating portrait video...")
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False).name
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_video, fourcc, fps, (out_w, out_h))
        
        if not out.isOpened():
            cap.release()
            raise Exception(f"Failed to create VideoWriter: {temp_video}")
        
        frame_idx = 0
        while True:
            if self.is_cancelled():
                cap.release()
                out.release()
                try:
                    os.unlink(temp_video)
                except:
                    pass
                raise Exception("Cancelled by user")
            
            ret, frame = cap.read()
            if not ret:
                break
            
            crop_x = crop_positions[frame_idx] if frame_idx < len(crop_positions) else crop_positions[-1]
            cropped = frame[0:crop_h, crop_x:crop_x+crop_w]
            resized = cv2.resize(cropped, (out_w, out_h), interpolation=cv2.INTER_LANCZOS4)
            out.write(resized)
            
            frame_idx += 1
            
            if frame_idx % 30 == 0:
                self.log(f"    Created {frame_idx}/{total_frames} frames...")
        
        cap.release()
        out.release()
        
        # Verify temp video was created
        if not os.path.exists(temp_video) or os.path.getsize(temp_video) < 1000:
            raise Exception(f"Failed to create temp video: {temp_video}")
        
        # Merge with audio using GPU/CPU encoder
        self.log("  Pass 3: Merging audio...")
        encoder_args = self.get_video_encoder_args()
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", temp_video,
            "-i", input_path,
            *encoder_args,
            "-c:a", "aac", "-b:a", "192k",
            "-map", "0:v:0", "-map", "1:a:0",
            "-shortest",
            output_path
        ]
        self.log_ffmpeg_command(cmd, "Portrait Merge Audio (MediaPipe)")
        self._run_ffmpeg_subprocess(cmd)
        
        # Cleanup
        try:
            os.unlink(temp_video)
        except:
            pass
    
    def _calculate_lip_activity(self, face_landmarks, frame_width, frame_height, prev_lip_distance=None):
        """Calculate lip movement activity score"""
        
        # Key lip landmarks (MediaPipe Face Mesh indices)
        # Upper lip: 13, Lower lip: 14
        upper_lip = face_landmarks.landmark[13]
        lower_lip = face_landmarks.landmark[14]
        
        # Mouth corners: 61 (left), 291 (right)
        mouth_left = face_landmarks.landmark[61]
        mouth_right = face_landmarks.landmark[291]
        
        # Calculate mouth openness (vertical distance)
        mouth_height = abs(upper_lip.y - lower_lip.y)
        
        # Calculate mouth width (horizontal distance)
        mouth_width = abs(mouth_left.x - mouth_right.x)
        
        # Aspect ratio (height/width) - higher when mouth is open
        if mouth_width > 0:
            aspect_ratio = mouth_height / mouth_width
        else:
            aspect_ratio = 0
        
        # Calculate movement delta (change from previous frame)
        delta = 0
        if prev_lip_distance is not None:
            delta = abs(mouth_height - prev_lip_distance)
        
        # Activity score: combination of openness and movement
        # Weight movement more heavily (0.6) than static openness (0.4)
        activity_score = (aspect_ratio * 0.4) + (delta * 0.6)
        
        return activity_score
    
    def _stabilize_positions_with_activity(self, positions, activities, min_shot_duration, switch_threshold):
        """Stabilize crop positions based on activity scores"""
        if not positions:
            return positions
        
        # First pass: smooth positions with moving median
        window_size = 30
        smoothed = []
        
        for i in range(len(positions)):
            start = max(0, i - window_size // 2)
            end = min(len(positions), i + window_size // 2)
            window = positions[start:end]
            smoothed.append(int(np.median(window)))
        
        # Second pass: lock positions per shot based on activity
        final = []
        shot_start = 0
        current_position = smoothed[0] if smoothed else 0
        
        for i in range(len(smoothed)):
            frames_since_switch = i - shot_start
            
            # Only allow switch if:
            # 1. Minimum shot duration has passed
            # 2. Position changed significantly
            # 3. Activity is high enough (speaker is talking)
            if frames_since_switch >= min_shot_duration:
                position_diff = abs(smoothed[i] - current_position)
                activity = activities[i] if i < len(activities) else 0
                
                # Switch if position changed significantly AND there's activity
                if position_diff > 200 and activity > switch_threshold:
                    # Lock previous shot
                    shot_positions = smoothed[shot_start:i]
                    if shot_positions:
                        shot_median = int(np.median(shot_positions))
                        final.extend([shot_median] * len(shot_positions))
                    
                    shot_start = i
                    current_position = smoothed[i]
        
        # Handle last shot
        shot_positions = smoothed[shot_start:]
        if shot_positions:
            shot_median = int(np.median(shot_positions))
            final.extend([shot_median] * len(shot_positions))
        
        return final if final else smoothed
    
    def add_hook(self, input_path: str, hook_text: str, output_path: str) -> float:
        """Add hook scene at the beginning with multi-line yellow text (Fajar Sadboy style)"""
        
        # Report TTS character usage
        self.report_tokens(0, 0, 0, len(hook_text))
        
        # Generate TTS audio
        try:
            tts_response = self.tts_client.audio.speech.create(
                model=self.tts_model,
                voice="nova",
                input=hook_text,
                speed=1.0
            )
        except APIConnectionError as e:
            self.log(f"  ❌ TTS API Connection Error: Could not connect to {self.tts_client.base_url}")
            raise Exception(f"TTS API connection failed!\n\nCould not connect to: {self.tts_client.base_url}\nError: {e}")
        except RateLimitError as e:
            self.log(f"  ❌ TTS API Rate Limit: {e}")
            raise Exception(f"TTS API rate limit exceeded!\n\nPlease wait a moment and try again.\nDetails: {e}")
        except APIStatusError as e:
            self.log(f"  ❌ TTS API Error (HTTP {e.status_code}): {e.message}")
            self.log(f"     Model: {self.tts_model}, Base URL: {self.tts_client.base_url}")
            raise Exception(
                f"TTS (Hook) API Error!\n\n"
                f"Status: {e.status_code}\n"
                f"Message: {e.message}\n"
                f"Model: {self.tts_model}\n"
                f"Base URL: {self.tts_client.base_url}\n\n"
                f"Check your Hook Maker API settings."
            )
        except Exception as e:
            self.log(f"  ❌ TTS API Unexpected Error: {type(e).__name__}: {e}")
            raise Exception(f"TTS (Hook) generation failed!\n\nError: {type(e).__name__}: {e}\nModel: {self.tts_model}")
        
        tts_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False).name
        with open(tts_file, 'wb') as f:
            f.write(tts_response.content)
        
        # Get TTS duration using ffprobe
        probe_cmd = [
            self.ffmpeg_path, "-i", tts_file,
            "-f", "null", "-"
        ]
        result = subprocess.run(probe_cmd, capture_output=True, text=True, creationflags=SUBPROCESS_FLAGS)
        duration_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
        
        if duration_match:
            h, m, s = duration_match.groups()
            hook_duration = int(h) * 3600 + int(m) * 60 + float(s) + 0.5
        else:
            hook_duration = 3.0
        
        # Format hook text: uppercase, split into lines (max 3 words per line for better visibility)
        hook_upper = hook_text.upper()
        words = hook_upper.split()
        
        # Split into lines (max 3 words per line - Fajar Sadboy style)
        lines = []
        current_line = []
        for word in words:
            current_line.append(word)
            if len(current_line) >= 3:
                lines.append(' '.join(current_line))
                current_line = []
        if current_line:
            lines.append(' '.join(current_line))
        
        # Get input video info
        probe_cmd = [self.ffmpeg_path, "-i", input_path]
        result = subprocess.run(probe_cmd, capture_output=True, text=True, creationflags=SUBPROCESS_FLAGS)
        
        # Extract fps
        fps_match = re.search(r'(\d+(?:\.\d+)?)\s*fps', result.stderr)
        fps = float(fps_match.group(1)) if fps_match else 30
        
        # Extract resolution
        res_match = re.search(r'(\d{3,4})x(\d{3,4})', result.stderr)
        if res_match:
            width, height = int(res_match.group(1)), int(res_match.group(2))
        else:
            width, height = 1080, 1920
        
        # Create hook video: freeze first frame + TTS audio + text overlay
        hook_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False).name
        
        # Build drawtext filter for each line
        # Style: Yellow/gold text on white background box
        drawtext_filters = []
        line_height = 85  # pixels between lines
        font_size = 58
        total_text_height = len(lines) * line_height
        start_y = (height // 3) - (total_text_height // 2)  # Position at upper third
        
        for i, line in enumerate(lines):
            # Escape special characters for FFmpeg drawtext
            escaped_line = line.replace("'", "'\\''").replace(":", "\\:").replace("\\", "\\\\")
            y_pos = start_y + (i * line_height)
            
            # Yellow/gold text with white box background
            font_path = self._get_ffmpeg_font_path()
            drawtext_filters.append(
                f"drawtext=text='{escaped_line}':"
                f"{font_path}"
                f"fontsize={font_size}:"
                f"fontcolor=#FFD700:"  # Golden yellow
                f"box=1:"
                f"boxcolor=white@0.95:"  # White background
                f"boxborderw=12:"  # Padding around text
                f"x=(w-text_w)/2:"
                f"y={y_pos}"
            )
        
        filter_chain = ",".join(drawtext_filters)
        
        # Get encoder args
        encoder_args = self.get_video_encoder_args()
        
        # Step 1: Create hook video with frozen frame + text + TTS audio
        # Use -t to set exact duration, freeze first frame
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", input_path,
            "-i", tts_file,
            "-filter_complex",
            f"[0:v]trim=0:0.04,loop=loop=-1:size=1:start=0,setpts=N/{fps}/TB,{filter_chain},trim=0:{hook_duration},setpts=PTS-STARTPTS[v];"
            f"[1:a]aresample=44100,apad=whole_dur={hook_duration}[a]",
            "-map", "[v]",
            "-map", "[a]",
            *encoder_args,
            "-r", str(fps),
            "-s", f"{width}x{height}",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "44100",
            "-ac", "2",
            "-t", str(hook_duration),
            hook_video
        ]
        self.log_ffmpeg_command(cmd, "Create Hook Video")
        result = self._run_ffmpeg_subprocess(cmd)
        
        if result.returncode != 0:
            error_lines = result.stderr.split('\n') if result.stderr else []
            actual_errors = [line for line in error_lines if 'error' in line.lower()]
            error_msg = '\n'.join(actual_errors[-3:]) if actual_errors else "Unknown error"
            raise Exception(f"Failed to create hook video: {error_msg}")
        
        # Step 2: Re-encode main video to EXACT same format (critical for concat)
        main_reencoded = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False).name
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", input_path,
            *encoder_args,
            "-r", str(fps),
            "-s", f"{width}x{height}",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "44100",
            "-ac", "2",
            main_reencoded
        ]
        self.log_ffmpeg_command(cmd, "Re-encode Main Video")
        result = self._run_ffmpeg_subprocess(cmd)
        
        if result.returncode != 0:
            error_lines = result.stderr.split('\n') if result.stderr else []
            actual_errors = [line for line in error_lines if 'error' in line.lower()]
            error_msg = '\n'.join(actual_errors[-3:]) if actual_errors else "Unknown error"
            raise Exception(f"Failed to re-encode main video: {error_msg}")
        
        # Step 3: Concatenate using concat demuxer (more reliable than filter_complex)
        concat_list = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False).name
        with open(concat_list, 'w') as f:
            f.write(f"file '{hook_video.replace(chr(92), '/')}'\n")
            f.write(f"file '{main_reencoded.replace(chr(92), '/')}'\n")
        
        cmd = [
            self.ffmpeg_path, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list,
            "-c", "copy",
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, creationflags=SUBPROCESS_FLAGS)
        
        # If concat demuxer fails, try filter_complex as fallback
        if result.returncode != 0:
            # Extract actual error message (skip ffmpeg version info)
            error_lines = result.stderr.split('\n') if result.stderr else []
            actual_errors = [line for line in error_lines if 'error' in line.lower() or 'invalid' in line.lower() or 'failed' in line.lower()]
            error_summary = '\n'.join(actual_errors[-3:]) if actual_errors else "Unknown concat error"
            
            self.log(f"  Concat demuxer failed: {error_summary[:100]}")
            self.log(f"  Trying filter_complex fallback...")
            
            cmd = [
                self.ffmpeg_path, "-y",
                "-i", hook_video,
                "-i", main_reencoded,
                "-filter_complex",
                "[0:v:0][0:a:0][1:v:0][1:a:0]concat=n=2:v=1:a=1[outv][outa]",
                "-map", "[outv]",
                "-map", "[outa]",
                *encoder_args,
                "-c:a", "aac",
                "-b:a", "192k",
                output_path
            ]
            self.log_ffmpeg_command(cmd, "Concat Hook (filter_complex fallback)")
            result = self._run_ffmpeg_subprocess(cmd)
            
            if result.returncode != 0:
                # Extract actual error, not version info
                error_lines = result.stderr.split('\n') if result.stderr else []
                actual_errors = [line for line in error_lines if 'error' in line.lower() or 'invalid' in line.lower() or 'failed' in line.lower()]
                error_msg = '\n'.join(actual_errors[-3:]) if actual_errors else result.stderr[-200:] if result.stderr else "Unknown error"
                raise Exception(f"Failed to concatenate hook video: {error_msg}")
        
        # Cleanup
        try:
            os.unlink(tts_file)
        except Exception as e:
            pass  # Ignore cleanup errors
        
        try:
            os.unlink(hook_video)
        except Exception as e:
            pass
        
        try:
            os.unlink(main_reencoded)
        except Exception as e:
            pass
        
        try:
            os.unlink(concat_list)
        except Exception as e:
            pass
        
        # Verify output was created
        if not os.path.exists(output_path):
            raise Exception(f"Failed to create hook video at {output_path}")
        
        return hook_duration
    
    def add_captions_api(self, input_path: str, output_path: str, audio_source: str = None, time_offset: float = 0):
        """Add CapCut-style captions using OpenAI Whisper API
        
        Args:
            input_path: Video to burn captions into (with hook)
            output_path: Output video path
            audio_source: Video to extract audio from for transcription (without hook)
            time_offset: Offset to add to all timestamps (hook duration)
        """
        
        # Use audio_source if provided, otherwise use input_path
        transcribe_source = audio_source if audio_source else input_path
        
        # Extract audio from video - use WAV format for better compatibility
        audio_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", transcribe_source,
            "-vn",
            "-acodec", "pcm_s16le",  # PCM 16-bit WAV
            "-ar", "16000",  # 16kHz sample rate
            "-ac", "1",  # Mono
            audio_file
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, creationflags=SUBPROCESS_FLAGS)
        
        if result.returncode != 0:
            self.log(f"  Warning: Audio extraction failed")
            import shutil
            shutil.copy(input_path, output_path)
            return
        
        # Check if audio file exists and has content
        if not os.path.exists(audio_file) or os.path.getsize(audio_file) < 1000:
            self.log(f"  Warning: Audio file too small or missing")
            import shutil
            shutil.copy(input_path, output_path)
            if os.path.exists(audio_file):
                os.unlink(audio_file)
            return
        
        # Get audio duration for token reporting
        probe_cmd = [self.ffmpeg_path, "-i", audio_file, "-f", "null", "-"]
        result = subprocess.run(probe_cmd, capture_output=True, text=True, creationflags=SUBPROCESS_FLAGS)
        duration_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
        audio_duration = 0
        if duration_match:
            h, m, s = duration_match.groups()
            audio_duration = int(h) * 3600 + int(m) * 60 + float(s)
            self.report_tokens(0, 0, audio_duration, 0)
        
        # Transcribe using Whisper API with word-level timestamps
        # (raw HTTP for proxy compatibility)
        try:
            transcript = self._whisper_transcribe_words_api(audio_file)
        except Exception as e:
            self.log(f"  Warning: Whisper API error: {e}")
            import shutil
            shutil.copy(input_path, output_path)
            os.unlink(audio_file)
            return
        
        os.unlink(audio_file)
        
        # Create ASS subtitle file with time offset for hook
        ass_file = tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8').name
        self.create_ass_subtitle_capcut(transcript, ass_file, time_offset)
        
        # Burn subtitles into video using GPU/CPU encoder
        # Escape path for FFmpeg on Windows
        ass_path_escaped = ass_file.replace('\\', '/').replace(':', '\\:')
        
        encoder_args = self.get_video_encoder_args()
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", input_path,
            "-vf", f"ass='{ass_path_escaped}'",
            *encoder_args,
            "-c:a", "copy",
            output_path
        ]
        
        self.log_ffmpeg_command(cmd, "Burn Captions")
        result = self._run_ffmpeg_subprocess(cmd)
        os.unlink(ass_file)
        
        if result.returncode != 0:
            self.log(f"  Warning: Caption burn failed, copying without captions")
            import shutil
            shutil.copy(input_path, output_path)
    
    def create_ass_subtitle_capcut(self, transcript, output_path: str, time_offset: float = 0):
        """Create ASS subtitle file with CapCut-style word-by-word highlighting"""
        
        # ASS header - CapCut style: white text, yellow highlight, black outline
        ass_content = """[Script Info]
Title: Auto-generated captions
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,65,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,50,50,400,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        
        events = []
        
        # Check if we have word-level timestamps
        if hasattr(transcript, 'words') and transcript.words:
            words = transcript.words
            
            # Group words into chunks (3-4 words per line for readability)
            chunk_size = 4
            
            for i in range(0, len(words), chunk_size):
                chunk = words[i:i + chunk_size]
                if not chunk:
                    continue
                
                # For each word in the chunk, create a subtitle event with that word highlighted
                for j, current_word in enumerate(chunk):
                    # Add time_offset to account for hook duration
                    word_start = current_word.start + time_offset
                    word_end = current_word.end + time_offset
                    
                    # Build text with current word highlighted in yellow
                    text_parts = []
                    for k, w in enumerate(chunk):
                        word_text = w.word.strip().upper()
                        if k == j:
                            # Highlight current word (yellow: &H00FFFF in BGR)
                            text_parts.append(f"{{\\c&H00FFFF&}}{word_text}{{\\c&HFFFFFF&}}")
                        else:
                            text_parts.append(word_text)
                    
                    text = " ".join(text_parts)
                    
                    events.append({
                        'start': self.format_time(word_start),
                        'end': self.format_time(word_end),
                        'text': text
                    })
        
        # Fallback: use segment-level timestamps if no word timestamps
        elif hasattr(transcript, 'segments') and transcript.segments:
            for segment in transcript.segments:
                start = segment.get('start', 0) + time_offset
                end = segment.get('end', 0) + time_offset
                text = segment.get('text', '').strip().upper()
                
                if text:
                    events.append({
                        'start': self.format_time(start),
                        'end': self.format_time(end),
                        'text': text
                    })
        
        # Write events to ASS file
        for event in events:
            ass_content += f"Dialogue: 0,{event['start']},{event['end']},Default,,0,0,0,,{event['text']}\n"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(ass_content)
    
    def format_time(self, seconds: float) -> str:
        """Convert seconds to ASS time format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centisecs = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"
    
    def parse_timestamp(self, ts: str) -> float:
        """Convert timestamp to seconds"""
        ts = ts.replace(",", ".")
        parts = ts.split(":")
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    
    def cleanup(self):
        """Clean up temp files"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def run_ffmpeg_with_progress(self, cmd: list, duration: float, progress_callback):
        """Run ffmpeg command and parse progress"""
        print(f"[DEBUG] Running ffmpeg command: {' '.join(cmd[:5])}...")
        print(f"[DEBUG] Expected duration: {duration}s")
        
        # Just run ffmpeg normally without progress parsing for now
        # Progress parsing from ffmpeg is complex due to carriage returns
        # _run_ffmpeg_subprocess auto-falls-back to libx264 if a GPU encoder
        # error is detected (e.g. invalid preset on h264_qsv).
        result = self._run_ffmpeg_subprocess(cmd)
        
        # Set to 100% when done
        progress_callback(1.0)
        print(f"[DEBUG] FFmpeg completed with return code: {result.returncode}")
        
        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else "Unknown FFmpeg error"
            
            # Extract the actual error (usually at the end)
            error_lines = error_msg.split('\n')
            relevant_errors = [line for line in error_lines if any(keyword in line.lower() for keyword in 
                ['error', 'invalid', 'failed', 'cannot', 'unable', 'not found', 'does not exist'])]
            
            # Get last 10 lines which usually contain the actual error
            last_lines = '\n'.join(error_lines[-10:])
            
            print(f"[FFMPEG ERROR] Full stderr:\n{error_msg}")
            self.log(f"FFmpeg command failed: {' '.join(cmd)}")
            self.log(f"FFmpeg full error output:\n{error_msg}")
            
            # Show relevant error or last lines
            if relevant_errors:
                error_summary = '\n'.join(relevant_errors[-5:])
            else:
                error_summary = last_lines
            
            raise Exception(f"FFmpeg process failed:\n{error_summary}")
    
    def convert_to_portrait_with_progress(self, input_path: str, output_path: str, progress_callback):
        """Convert landscape to 9:16 portrait with speaker tracking and progress (router method)"""
        try:
            if self.face_tracking_mode == "mediapipe":
                self.log("  Using MediaPipe (Active Speaker Detection)")
                return self.convert_to_portrait_mediapipe_with_progress(input_path, output_path, progress_callback)
            else:
                self.log("  Using OpenCV (Fast Mode)")
                return self.convert_to_portrait_opencv_with_progress(input_path, output_path, progress_callback)
        except Exception as e:
            # Fallback to OpenCV if MediaPipe fails
            if self.face_tracking_mode == "mediapipe":
                self.log(f"  ⚠ MediaPipe failed: {e}")
                self.log("  Falling back to OpenCV mode...")
                return self.convert_to_portrait_opencv_with_progress(input_path, output_path, progress_callback)
            else:
                raise
    
    def convert_to_portrait_opencv_with_progress(self, input_path: str, output_path: str, progress_callback):
        """Convert landscape to 9:16 portrait with speaker tracking and progress (OpenCV)"""
        
        self.log("[DEBUG] Starting portrait conversion...")
        print("[DEBUG] Starting portrait conversion...")
        print(f"[DEBUG] Input: {input_path}")
        print(f"[DEBUG] Output: {output_path}")
        sys.stdout.flush()
        
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise Exception(f"Failed to open video: {input_path}")
        
        orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        self.log(f"[DEBUG] Video: {orig_w}x{orig_h}, {fps}fps, {total_frames} frames")
        print(f"[DEBUG] Video: {orig_w}x{orig_h}, {fps}fps, {total_frames} frames")
        sys.stdout.flush()
        
        if total_frames == 0 or fps == 0:
            cap.release()
            raise Exception(f"Invalid video properties: {total_frames} frames, {fps} fps")
        
        # Calculate crop dimensions
        target_ratio = 9 / 16
        crop_w = int(orig_h * target_ratio)
        crop_h = orig_h
        out_w, out_h = 1080, 1920
        
        # Face detector
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)
        use_face_detection = not face_cascade.empty()
        if not use_face_detection:
            self.log(f"  ⚠ Face cascade not loaded (path: {cascade_path}), falling back to center crop")
            print(f"[DEBUG] Face cascade empty, using center crop fallback")
            sys.stdout.flush()
        
        # First pass: analyze frames (0-40%)
        print("[DEBUG] Pass 1: Analyzing frames...")
        sys.stdout.flush()
        
        crop_positions = []
        current_target = orig_w / 2
        frame_count = 0
        last_log_time = 0
        import time
        
        while True:
            # Check for cancellation
            if self.is_cancelled():
                cap.release()
                raise Exception("Cancelled by user")
            
            ret, frame = cap.read()
            if not ret:
                break
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(50, 50)) if use_face_detection else []
            
            if len(faces) > 0:
                # Find largest face
                largest = max(faces, key=lambda f: f[2] * f[3])
                current_target = largest[0] + largest[2] / 2
            
            crop_x = int(current_target - crop_w / 2)
            crop_x = max(0, min(crop_x, orig_w - crop_w))
            crop_positions.append(crop_x)
            
            frame_count += 1
            
            # Update progress more frequently with time-based logging
            current_time = time.time()
            if frame_count % 30 == 0 or (current_time - last_log_time) > 2:  # Every 30 frames or 2 seconds
                progress = (frame_count / total_frames) * 0.4  # 0-40%
                print(f"[DEBUG] Pass 1 progress: {progress*100:.1f}% ({frame_count}/{total_frames} frames)")
                sys.stdout.flush()
                progress_callback(progress)
                last_log_time = current_time
        
        print(f"[DEBUG] Analyzed {frame_count} frames")
        
        # Stabilize positions
        crop_positions = self.stabilize_positions(crop_positions)
        progress_callback(0.45)
        
        # Second pass: create video (45-85%)
        print("[DEBUG] Pass 2: Creating portrait video...")
        sys.stdout.flush()  # Force output
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False).name
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_video, fourcc, fps, (out_w, out_h))
        
        if not out.isOpened():
            cap.release()
            raise Exception(f"Failed to create VideoWriter: {temp_video}")
        
        frame_idx = 0
        last_log_time = 0
        last_frame_time = time.time()
        import time
        
        while True:
            # Check for cancellation
            if self.is_cancelled():
                cap.release()
                out.release()
                try:
                    os.unlink(temp_video)
                except:
                    pass
                raise Exception("Cancelled by user")
            
            # Watchdog: check if we're stuck (no frame processed in 30 seconds)
            current_time = time.time()
            if current_time - last_frame_time > 30:
                cap.release()
                out.release()
                raise Exception(f"Portrait conversion timeout: stuck at frame {frame_idx}/{total_frames}")
            
            ret, frame = cap.read()
            if not ret:
                break
            
            last_frame_time = current_time  # Update watchdog timer
            
            crop_x = crop_positions[frame_idx] if frame_idx < len(crop_positions) else crop_positions[-1]
            cropped = frame[0:crop_h, crop_x:crop_x+crop_w]
            resized = cv2.resize(cropped, (out_w, out_h), interpolation=cv2.INTER_LANCZOS4)
            
            # Write frame with error checking
            success = out.write(resized)
            if not success:
                print(f"[WARNING] Failed to write frame {frame_idx}")
                sys.stdout.flush()
            
            frame_idx += 1
            
            # Update progress more frequently and with time-based logging
            if frame_idx % 30 == 0 or (current_time - last_log_time) > 2:  # Every 30 frames or 2 seconds
                progress = 0.45 + (frame_idx / total_frames) * 0.4  # 45-85%
                print(f"[DEBUG] Pass 2 progress: {progress*100:.1f}% ({frame_idx}/{total_frames} frames)")
                sys.stdout.flush()
                progress_callback(progress)
                last_log_time = current_time
        
        print(f"[DEBUG] Created {frame_idx} frames")
        sys.stdout.flush()
        
        cap.release()
        print("[DEBUG] Released VideoCapture")
        sys.stdout.flush()
        
        out.release()
        print("[DEBUG] Released VideoWriter")
        sys.stdout.flush()
        
        # Verify temp video was created
        if not os.path.exists(temp_video) or os.path.getsize(temp_video) < 1000:
            raise Exception(f"Failed to create temp video: {temp_video}")
        
        print(f"[DEBUG] Temp video size: {os.path.getsize(temp_video)} bytes")
        sys.stdout.flush()
        
        progress_callback(0.85)
        
        # Merge with audio (85-100%) using GPU/CPU encoder
        print("[DEBUG] Pass 3: Merging audio...")
        sys.stdout.flush()
        
        duration = total_frames / fps if fps > 0 else 60
        encoder_args = self.get_video_encoder_args()
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", temp_video,
            "-i", input_path,
            *encoder_args,
            "-c:a", "aac", "-b:a", "192k",
            "-map", "0:v:0", "-map", "1:a:0",
            "-shortest",
            output_path
        ]
        
        # Run without progress parsing for audio merge (quick operation)
        print(f"[DEBUG] Running audio merge command...")
        sys.stdout.flush()
        
        self.log_ffmpeg_command(cmd, "Portrait Merge Audio (with progress)")
        result = self._run_ffmpeg_subprocess(cmd)
        
        if result.returncode != 0:
            print(f"[FFMPEG ERROR] {result.stderr}")
            sys.stdout.flush()
            raise Exception("Audio merge failed")
        
        print("[DEBUG] Audio merge complete")
        sys.stdout.flush()
        
        progress_callback(1.0)
        print("[DEBUG] Portrait conversion complete")
        sys.stdout.flush()
        
        # Cleanup temp video
        try:
            os.unlink(temp_video)
            print("[DEBUG] Cleaned up temp video")
            sys.stdout.flush()
        except Exception as e:
            print(f"[WARNING] Failed to cleanup temp video: {e}")
            sys.stdout.flush()
    
    def convert_to_portrait_mediapipe_with_progress(self, input_path: str, output_path: str, progress_callback):
        """Convert landscape to 9:16 portrait with active speaker detection and progress (MediaPipe)"""
        
        # Initialize MediaPipe
        self._init_mediapipe()
        
        self.log("[DEBUG] Starting MediaPipe portrait conversion...")
        print("[DEBUG] Starting MediaPipe portrait conversion...")
        sys.stdout.flush()
        
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise Exception(f"Failed to open video: {input_path}")
        
        orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        self.log(f"[DEBUG] Video: {orig_w}x{orig_h}, {fps}fps, {total_frames} frames")
        print(f"[DEBUG] Video: {orig_w}x{orig_h}, {fps}fps, {total_frames} frames")
        sys.stdout.flush()
        
        if total_frames == 0 or fps == 0:
            cap.release()
            raise Exception(f"Invalid video properties: {total_frames} frames, {fps} fps")
        
        # Calculate crop dimensions
        target_ratio = 9 / 16
        crop_w = int(orig_h * target_ratio)
        crop_h = orig_h
        out_w, out_h = 1080, 1920
        
        # MediaPipe settings
        lip_threshold = self.mediapipe_settings.get("lip_activity_threshold", 0.15)
        switch_threshold = self.mediapipe_settings.get("switch_threshold", 0.3)
        min_shot_duration = self.mediapipe_settings.get("min_shot_duration", 90)
        center_weight = self.mediapipe_settings.get("center_weight", 0.3)
        
        # First pass: analyze frames with MediaPipe (0-40%)
        print("[DEBUG] Pass 1: Analyzing lip movements with MediaPipe...")
        sys.stdout.flush()
        
        crop_positions = []
        face_activities = []
        frame_count = 0
        last_log_time = 0
        import time
        
        with self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=3,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        ) as face_mesh:
            
            prev_lip_distances = {}
            
            while True:
                if self.is_cancelled():
                    cap.release()
                    raise Exception("Cancelled by user")
                
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Convert to RGB for MediaPipe
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = face_mesh.process(rgb_frame)
                
                best_face_x = orig_w / 2
                max_activity = 0
                
                if results.multi_face_landmarks:
                    faces_data = []
                    
                    for face_id, face_landmarks in enumerate(results.multi_face_landmarks):
                        # Calculate lip activity
                        activity = self._calculate_lip_activity(
                            face_landmarks,
                            orig_w,
                            orig_h,
                            prev_lip_distances.get(face_id, None)
                        )
                        
                        # Get face center position
                        face_x = face_landmarks.landmark[1].x * orig_w
                        
                        # Combined score
                        center_score = 1.0 - abs(face_x - orig_w / 2) / (orig_w / 2)
                        combined_score = (activity * (1 - center_weight)) + (center_score * center_weight)
                        
                        faces_data.append({
                            'x': face_x,
                            'activity': activity,
                            'combined_score': combined_score
                        })
                        
                        # Update previous lip distance
                        upper_lip = face_landmarks.landmark[13]
                        lower_lip = face_landmarks.landmark[14]
                        lip_distance = abs(upper_lip.y - lower_lip.y)
                        prev_lip_distances[face_id] = lip_distance
                    
                    if faces_data:
                        best_face = max(faces_data, key=lambda f: f['combined_score'])
                        best_face_x = best_face['x']
                        max_activity = best_face['activity']
                
                crop_x = int(best_face_x - crop_w / 2)
                crop_x = max(0, min(crop_x, orig_w - crop_w))
                crop_positions.append(crop_x)
                face_activities.append(max_activity)
                
                frame_count += 1
                
                current_time = time.time()
                if frame_count % 30 == 0 or (current_time - last_log_time) > 2:
                    progress = (frame_count / total_frames) * 0.4
                    print(f"[DEBUG] Pass 1 progress: {progress*100:.1f}% ({frame_count}/{total_frames} frames)")
                    sys.stdout.flush()
                    progress_callback(progress)
                    last_log_time = current_time
        
        print(f"[DEBUG] Analyzed {frame_count} frames with MediaPipe")
        sys.stdout.flush()
        
        # Stabilize positions (40-45%)
        progress_callback(0.4)
        crop_positions = self._stabilize_positions_with_activity(
            crop_positions,
            face_activities,
            min_shot_duration,
            switch_threshold
        )
        progress_callback(0.45)
        
        # Second pass: create video (45-85%)
        print("[DEBUG] Pass 2: Creating portrait video...")
        sys.stdout.flush()
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False).name
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_video, fourcc, fps, (out_w, out_h))
        
        if not out.isOpened():
            cap.release()
            raise Exception(f"Failed to create VideoWriter: {temp_video}")
        
        frame_idx = 0
        last_log_time = 0
        last_frame_time = time.time()
        
        while True:
            if self.is_cancelled():
                cap.release()
                out.release()
                try:
                    os.unlink(temp_video)
                except:
                    pass
                raise Exception("Cancelled by user")
            
            current_time = time.time()
            if current_time - last_frame_time > 30:
                cap.release()
                out.release()
                raise Exception(f"Portrait conversion timeout: stuck at frame {frame_idx}/{total_frames}")
            
            ret, frame = cap.read()
            if not ret:
                break
            
            last_frame_time = current_time
            
            crop_x = crop_positions[frame_idx] if frame_idx < len(crop_positions) else crop_positions[-1]
            cropped = frame[0:crop_h, crop_x:crop_x+crop_w]
            resized = cv2.resize(cropped, (out_w, out_h), interpolation=cv2.INTER_LANCZOS4)
            
            success = out.write(resized)
            if not success:
                print(f"[WARNING] Failed to write frame {frame_idx}")
                sys.stdout.flush()
            
            frame_idx += 1
            
            if frame_idx % 30 == 0 or (current_time - last_log_time) > 2:
                progress = 0.45 + (frame_idx / total_frames) * 0.4
                print(f"[DEBUG] Pass 2 progress: {progress*100:.1f}% ({frame_idx}/{total_frames} frames)")
                sys.stdout.flush()
                progress_callback(progress)
                last_log_time = current_time
        
        print(f"[DEBUG] Created {frame_idx} frames")
        sys.stdout.flush()
        
        cap.release()
        out.release()
        
        if not os.path.exists(temp_video) or os.path.getsize(temp_video) < 1000:
            raise Exception(f"Failed to create temp video: {temp_video}")
        
        print(f"[DEBUG] Temp video size: {os.path.getsize(temp_video)} bytes")
        sys.stdout.flush()
        
        progress_callback(0.85)
        
        # Merge with audio (85-100%) using GPU/CPU encoder
        print("[DEBUG] Pass 3: Merging audio...")
        sys.stdout.flush()
        
        encoder_args = self.get_video_encoder_args()
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", temp_video,
            "-i", input_path,
            *encoder_args,
            "-c:a", "aac", "-b:a", "192k",
            "-map", "0:v:0", "-map", "1:a:0",
            "-shortest",
            output_path
        ]
        
        self.log_ffmpeg_command(cmd, "MediaPipe Portrait Merge Audio")
        result = self._run_ffmpeg_subprocess(cmd)
        
        if result.returncode != 0:
            print(f"[FFMPEG ERROR] {result.stderr}")
            sys.stdout.flush()
            raise Exception("Audio merge failed")
        
        print("[DEBUG] Audio merge complete")
        sys.stdout.flush()
        
        progress_callback(1.0)
        print("[DEBUG] MediaPipe portrait conversion complete")
        sys.stdout.flush()
        
        # Cleanup
        try:
            os.unlink(temp_video)
            print("[DEBUG] Cleaned up temp video")
            sys.stdout.flush()
        except Exception as e:
            print(f"[WARNING] Failed to cleanup temp video: {e}")
            sys.stdout.flush()
    
    def add_hook_with_progress(self, input_path: str, hook_text: str, output_path: str, progress_callback) -> float:
        """Add hook scene at the beginning with progress tracking"""
        
        # Report TTS character usage
        self.report_tokens(0, 0, 0, len(hook_text))
        
        # Generate TTS audio (10% progress)
        progress_callback(0.1)
        try:
            tts_response = self.tts_client.audio.speech.create(
                model=self.tts_model,
                voice="nova",
                input=hook_text,
                speed=1.0
            )
        except APIConnectionError as e:
            self.log(f"  ❌ TTS API Connection Error: Could not connect to {self.tts_client.base_url}")
            raise Exception(f"TTS API connection failed!\n\nCould not connect to: {self.tts_client.base_url}\nError: {e}")
        except RateLimitError as e:
            self.log(f"  ❌ TTS API Rate Limit: {e}")
            raise Exception(f"TTS API rate limit exceeded!\n\nPlease wait a moment and try again.\nDetails: {e}")
        except APIStatusError as e:
            self.log(f"  ❌ TTS API Error (HTTP {e.status_code}): {e.message}")
            self.log(f"     Model: {self.tts_model}, Base URL: {self.tts_client.base_url}")
            raise Exception(
                f"TTS (Hook) API Error!\n\n"
                f"Status: {e.status_code}\n"
                f"Message: {e.message}\n"
                f"Model: {self.tts_model}\n"
                f"Base URL: {self.tts_client.base_url}\n\n"
                f"Check your Hook Maker API settings."
            )
        except Exception as e:
            self.log(f"  ❌ TTS API Unexpected Error: {type(e).__name__}: {e}")
            raise Exception(f"TTS (Hook) generation failed!\n\nError: {type(e).__name__}: {e}\nModel: {self.tts_model}")
        
        tts_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False).name
        with open(tts_file, 'wb') as f:
            f.write(tts_response.content)
        
        progress_callback(0.2)
        
        # Get TTS duration using ffprobe
        probe_cmd = [
            self.ffmpeg_path, "-i", tts_file,
            "-f", "null", "-"
        ]
        result = subprocess.run(probe_cmd, capture_output=True, text=True, creationflags=SUBPROCESS_FLAGS)
        duration_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
        
        if duration_match:
            h, m, s = duration_match.groups()
            hook_duration = int(h) * 3600 + int(m) * 60 + float(s) + 0.5
        else:
            hook_duration = 3.0
        
        # Format hook text
        hook_upper = hook_text.upper()
        words = hook_upper.split()
        
        lines = []
        current_line = []
        for word in words:
            current_line.append(word)
            if len(current_line) >= 3:
                lines.append(' '.join(current_line))
                current_line = []
        if current_line:
            lines.append(' '.join(current_line))
        
        # Get input video info
        probe_cmd = [self.ffmpeg_path, "-i", input_path]
        result = subprocess.run(probe_cmd, capture_output=True, text=True, creationflags=SUBPROCESS_FLAGS)
        
        fps_match = re.search(r'(\d+(?:\.\d+)?)\s*fps', result.stderr)
        fps = float(fps_match.group(1)) if fps_match else 30
        
        res_match = re.search(r'(\d{3,4})x(\d{3,4})', result.stderr)
        if res_match:
            width, height = int(res_match.group(1)), int(res_match.group(2))
        else:
            width, height = 1080, 1920
        
        progress_callback(0.3)
        
        # Create hook video in our temp directory
        hook_video = str(self.temp_dir / f"hook_{int(time.time() * 1000)}.mp4")
        
        # Use a simpler approach: create static image with text, then combine with audio
        # This avoids complex FFmpeg filter escaping issues
        
        # First, create a simple background video from first frame using GPU/CPU encoder
        bg_video = str(self.temp_dir / f"hook_bg_{int(time.time() * 1000)}.mp4")
        
        encoder_args = self.get_video_encoder_args()
        bg_cmd = [
            self.ffmpeg_path, "-y",
            "-i", input_path,
            "-vf", f"trim=0:0.04,loop=loop=-1:size=1:start=0,setpts=N/{fps}/TB",
            "-t", str(hook_duration),
            *encoder_args,
            "-r", str(fps),
            "-s", f"{width}x{height}",
            "-pix_fmt", "yuv420p",
            "-an",
            bg_video
        ]
        
        self.log_ffmpeg_command(bg_cmd, "Create Hook Background")
        result = self._run_ffmpeg_subprocess(bg_cmd)
        if result.returncode != 0:
            self.log(f"Failed to create background video: {result.stderr}")
            raise Exception("Failed to create background video")
        
        # Verify background video was created successfully
        if not os.path.exists(bg_video) or os.path.getsize(bg_video) < 1000:
            raise Exception("Background video was not created properly")
        
        # === Render hook overlay using PIL (supports user-customized font, colors, corners) ===
        from PIL import Image, ImageDraw, ImageFont

        style = self.hook_style_settings or {}
        font_size_frac = float(style.get("font_size", 0.054))
        font_color_hex = style.get("font_color", "#FFD700")
        bg_color_hex = style.get("bg_color", "#FFFFFF")
        corner_radius = int(style.get("corner_radius", 0))
        pos_x = float(style.get("position_x", 0.5))
        pos_y = float(style.get("position_y", 0.333))
        user_font_path = style.get("font_path") or ""

        # Resolve font path with sensible fallbacks
        font_candidates = [user_font_path, self._find_system_font_bold()]
        pil_font = None
        font_px = max(20, int(font_size_frac * width))
        for candidate in font_candidates:
            if not candidate or not os.path.exists(candidate):
                continue
            try:
                pil_font = ImageFont.truetype(candidate, font_px)
                self.log(f"  Hook font: {candidate} @ {font_px}px")
                break
            except Exception as e:
                self.log(f"  ⚠ Failed to load font {candidate}: {e}")
        if pil_font is None:
            self.log("  ⚠ No usable TTF font found, using PIL default (will look basic)")
            pil_font = ImageFont.load_default()

        font_color_rgb = _hex_to_rgb(font_color_hex)
        bg_color_rgb = _hex_to_rgb(bg_color_hex)

        # Per-line geometry
        padding = max(10, int(font_px * 0.22))
        line_spacing = max(6, int(font_px * 0.25))

        line_metrics = []
        for line in lines:
            try:
                bbox = pil_font.getbbox(line)
            except AttributeError:
                w, h = pil_font.getsize(line)
                bbox = (0, 0, w, h)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            line_metrics.append({
                "text": line,
                "bbox": bbox,
                "box_w": text_w + padding * 2,
                "box_h": text_h + padding * 2,
            })

        total_h = sum(m["box_h"] for m in line_metrics)
        if len(line_metrics) > 1:
            total_h += line_spacing * (len(line_metrics) - 1)

        center_x = int(pos_x * width)
        center_y = int(pos_y * height)
        block_top = center_y - total_h // 2

        # Compose the static overlay (transparent everywhere except the hook boxes)
        overlay_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay_img)

        cur_y = block_top
        for m in line_metrics:
            box_w = m["box_w"]
            box_h = m["box_h"]
            box_x1 = center_x - box_w // 2
            box_y1 = cur_y
            box_x2 = box_x1 + box_w
            box_y2 = box_y1 + box_h

            if corner_radius > 0 and hasattr(draw, "rounded_rectangle"):
                # Clamp radius so it never exceeds half the smaller dimension
                r = min(corner_radius, box_w // 2, box_h // 2)
                draw.rounded_rectangle(
                    [box_x1, box_y1, box_x2, box_y2],
                    radius=r,
                    fill=(*bg_color_rgb, 255),
                )
            else:
                draw.rectangle(
                    [box_x1, box_y1, box_x2, box_y2],
                    fill=(*bg_color_rgb, 255),
                )

            # PIL draws text at the top-left of the glyph bounding box;
            # subtract bbox[0]/[1] so the glyphs sit cleanly inside the padding.
            text_x = box_x1 + padding - m["bbox"][0]
            text_y = box_y1 + padding - m["bbox"][1]
            draw.text(
                (text_x, text_y),
                m["text"],
                font=pil_font,
                fill=(*font_color_rgb, 255),
            )

            cur_y = box_y2 + line_spacing

        overlay_png = str(self.temp_dir / f"hook_overlay_{int(time.time() * 1000)}.png")
        overlay_img.save(overlay_png, "PNG")
        progress_callback(0.4)

        # Composite overlay on the (frozen) background video in one FFmpeg pass
        overlay_video = str(self.temp_dir / f"hook_overlay_video_{int(time.time() * 1000)}.mp4")
        encoder_args = self.get_video_encoder_args()
        overlay_cmd = [
            self.ffmpeg_path, "-y",
            "-i", bg_video,
            "-i", overlay_png,
            "-filter_complex", "[0:v][1:v]overlay=0:0[v]",
            "-map", "[v]",
            *encoder_args,
            "-pix_fmt", "yuv420p",
            "-an",
            overlay_video,
        ]
        self.log_ffmpeg_command(overlay_cmd, "Composite Hook Overlay (PIL)")
        result = self._run_ffmpeg_subprocess(overlay_cmd)
        if result.returncode != 0:
            self.log(f"Failed to composite hook overlay: {result.stderr}")
            raise Exception("Failed to composite hook overlay video")

        if not os.path.exists(overlay_video) or os.path.getsize(overlay_video) < 1000:
            raise Exception("Hook overlay video was not created properly")

        progress_callback(0.55)

        # Both names point at the same file so the rest of the pipeline (audio mux,
        # cleanup) keeps working without further changes.
        current_video = overlay_video
        reencoded_video = overlay_video

        
        # Finally, add audio to re-encoded video
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", reencoded_video,
            "-i", tts_file,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "44100",
            "-ac", "2",
            "-shortest",
            hook_video
        ]
        
        # Hook creation is 30-60%
        self.run_ffmpeg_with_progress(cmd, hook_duration, 
            lambda p: progress_callback(0.3 + p * 0.3))
        
        # Re-encode main video (60-80%) using GPU/CPU encoder
        progress_callback(0.6)
        main_reencoded = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False).name
        
        # Get main video duration
        probe_cmd = [self.ffmpeg_path, "-i", input_path, "-f", "null", "-"]
        result = subprocess.run(probe_cmd, capture_output=True, text=True, creationflags=SUBPROCESS_FLAGS)
        duration_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
        main_duration = 60
        if duration_match:
            h, m, s = duration_match.groups()
            main_duration = int(h) * 3600 + int(m) * 60 + float(s)
        
        encoder_args = self.get_video_encoder_args()
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", input_path,
            *encoder_args,
            "-r", str(fps),
            "-s", f"{width}x{height}",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "44100",
            "-ac", "2",
            "-progress", "pipe:1",
            main_reencoded
        ]
        
        self.log_ffmpeg_command(cmd, "Re-encode Main Video for Hook Concat")
        self.run_ffmpeg_with_progress(cmd, main_duration,
            lambda p: progress_callback(0.6 + p * 0.2))
        
        # Concatenate (80-100%)
        progress_callback(0.8)
        concat_list = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False).name
        with open(concat_list, 'w') as f:
            f.write(f"file '{hook_video.replace(chr(92), '/')}'\n")
            f.write(f"file '{main_reencoded.replace(chr(92), '/')}'\n")
        
        cmd = [
            self.ffmpeg_path, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list,
            "-c", "copy",
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, creationflags=SUBPROCESS_FLAGS)
        
        if result.returncode != 0:
            # Fallback to filter_complex using GPU/CPU encoder
            encoder_args = self.get_video_encoder_args()
            cmd = [
                self.ffmpeg_path, "-y",
                "-i", hook_video,
                "-i", main_reencoded,
                "-filter_complex",
                "[0:v:0][0:a:0][1:v:0][1:a:0]concat=n=2:v=1:a=1[outv][outa]",
                "-map", "[outv]",
                "-map", "[outa]",
                *encoder_args,
                "-c:a", "aac",
                "-b:a", "192k",
                "-progress", "pipe:1",
                output_path
            ]
            self.log_ffmpeg_command(cmd, "Concat Hook (filter_complex fallback - old)")
            total_duration = hook_duration + main_duration
            self.run_ffmpeg_with_progress(cmd, total_duration,
                lambda p: progress_callback(0.8 + p * 0.2))
        else:
            progress_callback(1.0)
        
        # Cleanup
        for path in (tts_file, hook_video, main_reencoded, concat_list,
                     bg_video, overlay_video, overlay_png):
            try:
                if path and os.path.exists(path):
                    os.unlink(path)
            except Exception:
                pass
        
        return hook_duration
    
    def add_captions_api_with_progress(self, input_path: str, output_path: str, audio_source: str = None, time_offset: float = 0, progress_callback=None):
        """Add CapCut-style captions using OpenAI Whisper API with progress"""
        
        if progress_callback:
            progress_callback(0.1)
        
        # Use audio_source if provided, otherwise use input_path
        transcribe_source = audio_source if audio_source else input_path
        
        # Extract audio from video
        audio_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", transcribe_source,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            audio_file
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, creationflags=SUBPROCESS_FLAGS)
        
        if result.returncode != 0:
            self.log(f"  Warning: Audio extraction failed")
            import shutil
            shutil.copy(input_path, output_path)
            return
        
        if progress_callback:
            progress_callback(0.2)
        
        # Check if audio file exists
        if not os.path.exists(audio_file) or os.path.getsize(audio_file) < 1000:
            self.log(f"  Warning: Audio file too small or missing")
            import shutil
            shutil.copy(input_path, output_path)
            if os.path.exists(audio_file):
                os.unlink(audio_file)
            return
        
        # Get audio duration for token reporting
        probe_cmd = [self.ffmpeg_path, "-i", audio_file, "-f", "null", "-"]
        result = subprocess.run(probe_cmd, capture_output=True, text=True, creationflags=SUBPROCESS_FLAGS)
        duration_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
        audio_duration = 0
        if duration_match:
            h, m, s = duration_match.groups()
            audio_duration = int(h) * 3600 + int(m) * 60 + float(s)
            self.report_tokens(0, 0, audio_duration, 0)
        
        if progress_callback:
            progress_callback(0.3)
        
        # Transcribe using Whisper API (raw HTTP for proxy compatibility)
        try:
            transcript = self._whisper_transcribe_words_api(audio_file)
        except Exception as e:
            self.log(f"  Warning: Whisper API error: {e}")
            import shutil
            shutil.copy(input_path, output_path)
            os.unlink(audio_file)
            return
        
        os.unlink(audio_file)
        
        if progress_callback:
            progress_callback(0.5)
        
        # Create ASS subtitle file
        ass_file = tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8').name
        self.create_ass_subtitle_capcut(transcript, ass_file, time_offset)
        
        if progress_callback:
            progress_callback(0.6)
        
        # Burn subtitles into video using GPU/CPU encoder
        ass_path_escaped = ass_file.replace('\\', '/').replace(':', '\\:')
        
        # Get video duration for progress
        probe_cmd = [self.ffmpeg_path, "-i", input_path, "-f", "null", "-"]
        result = subprocess.run(probe_cmd, capture_output=True, text=True, creationflags=SUBPROCESS_FLAGS)
        duration_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
        video_duration = 60
        if duration_match:
            h, m, s = duration_match.groups()
            video_duration = int(h) * 3600 + int(m) * 60 + float(s)
        
        encoder_args = self.get_video_encoder_args()
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", input_path,
            "-vf", f"ass='{ass_path_escaped}'",
            *encoder_args,
            "-c:a", "copy",
            "-progress", "pipe:1",
            output_path
        ]
        
        self.log_ffmpeg_command(cmd, "Burn Captions (old function)")
        
        # Caption burn is 60-100%
        self.run_ffmpeg_with_progress(cmd, video_duration,
            lambda p: progress_callback(0.6 + p * 0.4) if progress_callback else None)
        
        os.unlink(ass_file)

    def add_watermark_with_progress(self, input_path: str, output_path: str, progress_callback):
        """Add watermark overlay to video with progress tracking"""
        
        watermark_path = self.watermark_settings.get("image_path", "")
        if not watermark_path or not Path(watermark_path).exists():
            self.log("  Warning: Watermark image not found, skipping")
            import shutil
            shutil.copy(input_path, output_path)
            return
        
        progress_callback(0.1)
        
        # Get video dimensions
        probe_cmd = [self.ffmpeg_path, "-i", input_path]
        result = subprocess.run(probe_cmd, capture_output=True, text=True, creationflags=SUBPROCESS_FLAGS)
        
        res_match = re.search(r'(\d{3,4})x(\d{3,4})', result.stderr)
        if res_match:
            video_width, video_height = int(res_match.group(1)), int(res_match.group(2))
        else:
            video_width, video_height = 1080, 1920
        
        progress_callback(0.2)
        
        # Calculate watermark size and position
        scale = self.watermark_settings.get("scale", 0.15)
        pos_x = self.watermark_settings.get("position_x", 0.85)
        pos_y = self.watermark_settings.get("position_y", 0.05)
        opacity = self.watermark_settings.get("opacity", 0.8)
        
        # Calculate watermark width in pixels
        watermark_width = int(video_width * scale)
        
        # Calculate position in pixels
        x_pixels = int(pos_x * video_width)
        y_pixels = int(pos_y * video_height)
        
        # Escape watermark path for FFmpeg (Windows paths)
        watermark_escaped = watermark_path.replace('\\', '/').replace(':', '\\:')
        
        # Build FFmpeg overlay filter with proper opacity control
        # Scale watermark, apply opacity via colorchannelmixer, then overlay
        filter_complex = (
            f"[1:v]scale={watermark_width}:-1,format=rgba,"
            f"colorchannelmixer=aa={opacity}[wm];"
            f"[0:v][wm]overlay={x_pixels}:{y_pixels}"
        )
        
        progress_callback(0.3)
        
        # Get video duration for progress
        duration_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
        video_duration = 60
        if duration_match:
            h, m, s = duration_match.groups()
            video_duration = int(h) * 3600 + int(m) * 60 + float(s)
        
        # Apply watermark using GPU/CPU encoder
        encoder_args = self.get_video_encoder_args()
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", input_path,
            "-i", watermark_path,
            "-filter_complex", filter_complex,
            *encoder_args,
            "-pix_fmt", "yuv420p",  # Ensure compatibility
            "-c:a", "copy",
            "-movflags", "+faststart",  # Enable streaming
            "-progress", "pipe:1",
            output_path
        ]
        
        self.log_ffmpeg_command(cmd, "Apply Watermark")
        
        # Watermark application is 30-100%
        self.run_ffmpeg_with_progress(cmd, video_duration,
            lambda p: progress_callback(0.3 + p * 0.7))
        
        if not Path(output_path).exists():
            raise Exception("Failed to apply watermark")

    def add_credit_watermark_with_progress(self, input_path: str, output_path: str, progress_callback):
        """Add credit text watermark (channel name) to video with progress tracking"""
        
        if not self.channel_name:
            self.log("  Warning: No channel name available, skipping credit")
            import shutil
            shutil.copy(input_path, output_path)
            return
        
        progress_callback(0.1)
        
        # Get video dimensions
        probe_cmd = [self.ffmpeg_path, "-i", input_path]
        result = subprocess.run(probe_cmd, capture_output=True, text=True, creationflags=SUBPROCESS_FLAGS)
        
        res_match = re.search(r'(\d{3,4})x(\d{3,4})', result.stderr)
        if res_match:
            video_width, video_height = int(res_match.group(1)), int(res_match.group(2))
        else:
            video_width, video_height = 1080, 1920
        
        progress_callback(0.2)
        
        # Get credit watermark settings
        size = self.credit_watermark_settings.get("size", 0.03)
        pos_x = self.credit_watermark_settings.get("position_x", 0.5)
        pos_y = self.credit_watermark_settings.get("position_y", 0.95)
        opacity = self.credit_watermark_settings.get("opacity", 0.7)
        
        # Calculate font size in pixels (based on video height)
        font_size = int(video_height * size)
        
        # Calculate position in pixels
        x_pixels = int(pos_x * video_width)
        y_pixels = int(pos_y * video_height)
        
        # Prepare credit text
        credit_text = f"Source: {self.channel_name}"
        # Escape special characters for FFmpeg drawtext
        credit_text_escaped = credit_text.replace("'", "'\\''").replace(":", "\\:")
        
        # Build FFmpeg drawtext filter
        # Use fontfile for portable FFmpeg (avoids fontconfig dependency)
        # Try to find a system font, fallback to built-in if not available
        font_file = None
        if sys.platform == "win32":
            # Windows fonts directory
            windows_fonts = [
                "C:/Windows/Fonts/arial.ttf",
                "C:/Windows/Fonts/segoeui.ttf",
                "C:/Windows/Fonts/tahoma.ttf",
            ]
            for font in windows_fonts:
                if Path(font).exists():
                    font_file = font.replace("\\", "/").replace(":", "\\:")
                    break
        
        # Build filter string
        if font_file:
            filter_str = (
                f"drawtext=fontfile='{font_file}':"
                f"text='{credit_text_escaped}':"
                f"fontsize={font_size}:"
                f"fontcolor=white@{opacity}:"
                f"borderw=2:"
                f"bordercolor=black@{opacity}:"
                f"x={x_pixels}-(text_w/2):"
                f"y={y_pixels}-(text_h/2)"
            )
        else:
            # Fallback without fontfile (may cause fontconfig warning but should still work)
            filter_str = (
                f"drawtext=text='{credit_text_escaped}':"
                f"fontsize={font_size}:"
                f"fontcolor=white@{opacity}:"
                f"borderw=2:"
                f"bordercolor=black@{opacity}:"
                f"x={x_pixels}-(text_w/2):"
                f"y={y_pixels}-(text_h/2)"
            )
        
        progress_callback(0.3)
        
        # Get video duration for progress
        duration_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
        video_duration = 60
        if duration_match:
            h, m, s = duration_match.groups()
            video_duration = int(h) * 3600 + int(m) * 60 + float(s)
        
        # Apply credit text using GPU/CPU encoder
        encoder_args = self.get_video_encoder_args()
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", input_path,
            "-vf", filter_str,
            *encoder_args,
            "-c:a", "copy",
            "-movflags", "+faststart",
            "-progress", "pipe:1",
            output_path
        ]
        
        self.log_ffmpeg_command(cmd, "Apply Credit Watermark")
        
        # Credit application is 30-100%
        self.run_ffmpeg_with_progress(cmd, video_duration,
            lambda p: progress_callback(0.3 + p * 0.7))
        
        if not Path(output_path).exists():
            raise Exception("Failed to apply credit watermark")

    def find_highlights_only(self, url: str, num_clips: int = 5) -> dict:
        """Phase 1: Download subtitle only and find highlights (no video download)
        
        Returns:
            dict with keys:
                - 'session_dir': Path to session directory
                - 'url': YouTube video URL (for later section download)
                - 'srt_path': Path to subtitle file
                - 'highlights': List of highlight dicts with metadata + transcript
                - 'video_info': Video metadata (title, channel, etc.)
        """
        # Create session directory with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = self.output_dir / "sessions" / timestamp
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Update temp_dir to session-specific temp
        self.temp_dir = session_dir / "_temp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        self.log(f"Session directory: {session_dir}")
        
        # Step 1: Download subtitle only (no video!)
        self.set_progress("Downloading subtitle...", 0.1)
        srt_path, video_info = self.download_subtitle_only(url)
        
        # Store channel name for credit watermark
        self.channel_name = video_info.get("channel", "") if video_info else ""
        
        if self.is_cancelled():
            return None
        
        if not srt_path:
            raise SubtitleNotFoundError(
                f"No subtitle available for language: {self.subtitle_language.upper()}",
                video_path=None,
                video_info=video_info,
                session_dir=str(session_dir)
            )
        
        # Step 2: Find highlights
        self.set_progress("Finding highlights with AI...", 0.5)
        transcript = self.parse_srt(srt_path)
        highlights = self.find_highlights(transcript, video_info, num_clips)
        
        if self.is_cancelled():
            return None
        
        if not highlights:
            raise Exception(
                "❌ No valid highlights found!\n\n"
                "Possible causes:\n"
                "1. AI model failed to generate highlights\n"
                "2. Video transcript too short or not suitable\n"
                "3. AI model configuration issue\n\n"
                "Try:\n"
                "- Using a different AI model (GPT-4, Gemini, etc.)\n"
                "- Checking AI API settings\n"
                "- Using a longer video with more content"
            )
        
        # Extract transcript text for each highlight
        for h in highlights:
            h["transcript_text"] = self.extract_transcript_for_highlight(srt_path, h)
        
        self.set_progress("Highlights found!", 1.0)
        self.log(f"\n✅ Found {len(highlights)} highlights")
        
        # Save session data to JSON for resume capability
        session_data_file = session_dir / "session_data.json"
        session_data = {
            "session_dir": str(session_dir),
            "url": url,
            "srt_path": srt_path,
            "highlights": highlights,
            "video_info": video_info,
            "created_at": datetime.now().isoformat(),
            "status": "highlights_found"
        }
        
        with open(session_data_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        self.log(f"Session data saved to: {session_data_file}")
        
        return session_data
    
    def process_selected_highlights(self, url: str, selected_highlights: list, 
                                   session_dir: Path, add_captions: bool = True, 
                                   add_hook: bool = True):
        """Phase 2: Download video sections and process selected highlights
        
        Args:
            url: YouTube video URL (for downloading sections)
            selected_highlights: List of highlight dicts to process
            session_dir: Session directory for output
            add_captions: Whether to add captions
            add_hook: Whether to add hook
        """
        if not selected_highlights:
            raise Exception("No highlights selected for processing")
        
        self.log(f"\n[Processing {len(selected_highlights)} selected clips]")
        
        # Ensure session_dir is Path object
        if isinstance(session_dir, str):
            session_dir = Path(session_dir)
        
        # Update output_dir to session clips folder
        clips_dir = session_dir / "clips"
        clips_dir.mkdir(parents=True, exist_ok=True)
        
        # Update temp_dir to session-specific temp
        self.temp_dir = session_dir / "_temp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Process each selected clip
        total_clips = len(selected_highlights)
        for i, highlight in enumerate(selected_highlights, 1):
            if self.is_cancelled():
                return
            
            # Step A: Download video section for this clip
            self.set_progress(f"Clip {i}/{total_clips}: Downloading video section...", 
                            0.05 + (0.9 * (i - 1) / total_clips))
            self.log(f"\n[Clip {i}/{total_clips}] Downloading: {highlight.get('title', 'Untitled')}")
            
            section_filename = f"section_{i:03d}.mp4"
            section_path = str(self.temp_dir / section_filename)
            
            try:
                video_path = self.download_video_section(
                    url, 
                    highlight["start_time"], 
                    highlight["end_time"],
                    section_path
                )
            except Exception as e:
                self.log(f"  ✗ Failed to download section: {e}")
                raise Exception(
                    f"Failed to download video section for clip {i}!\n\n"
                    f"Title: {highlight.get('title', 'Untitled')}\n"
                    f"Time: {highlight['start_time']} → {highlight['end_time']}\n\n"
                    f"Error: {str(e)}"
                )
            
            # Step B: Process the downloaded section
            # Create clip-specific folder
            clip_folder = clips_dir / f"clip_{i:03d}"
            clip_folder.mkdir(parents=True, exist_ok=True)
            
            # Temporarily override output_dir for this clip
            original_output_dir = self.output_dir
            self.output_dir = clip_folder.parent
            
            try:
                # Pass pre_cut=True since we downloaded the section already
                self.process_clip(video_path, highlight, i, total_clips, 
                                add_captions=add_captions, add_hook=add_hook,
                                pre_cut=True)
            finally:
                # Restore original output_dir
                self.output_dir = original_output_dir
            
            # Clean up section file after processing
            try:
                if Path(video_path).exists():
                    os.remove(video_path)
            except Exception:
                pass
        
        # Cleanup temp files
        self.set_progress("Cleaning up...", 0.95)
        self.cleanup()
        
        # Update session status to completed
        session_data_file = session_dir / "session_data.json"
        if session_data_file.exists():
            with open(session_data_file, "r", encoding="utf-8") as f:
                session_data = json.load(f)
            
            session_data["status"] = "completed"
            session_data["completed_at"] = datetime.now().isoformat()
            session_data["clips_processed"] = total_clips
            
            with open(session_data_file, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        self.set_progress("Complete!", 1.0)
        self.log(f"\n✅ Created {total_clips} clips in: {clips_dir}")
