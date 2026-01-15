"""
Auto Clipper - All in one: Download, Highlight, Clip, Portrait, Caption
Usage: python main.py <youtube_url> [num_clips]
"""

import subprocess
import sys
import os
import re
import json
import cv2
import numpy as np
import whisper
import tempfile
from pathlib import Path
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
from hook_generator import add_hook_to_clip

load_dotenv(Path(__file__).parent.parent / ".env")
client = OpenAI(api_key=os.getenv("OPENAI_APIKEY"))


def download_video(url: str, output_dir: str) -> tuple[str, str, dict]:
    """Download video, subtitle, dan metadata. Return (video_path, srt_path, video_info)"""
    print("\n[1/4] DOWNLOADING VIDEO & SUBTITLE")
    print("-" * 50)
    
    # First, get video metadata (title, description, channel)
    print("  Fetching video info...")
    meta_cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-download",
        url
    ]
    
    meta_result = subprocess.run(meta_cmd, capture_output=True, text=True)
    video_info = {}
    if meta_result.returncode == 0:
        try:
            yt_data = json.loads(meta_result.stdout)
            video_info = {
                "title": yt_data.get("title", ""),
                "description": yt_data.get("description", "")[:2000],  # Limit description
                "channel": yt_data.get("channel", ""),
                "uploader": yt_data.get("uploader", ""),
            }
            print(f"  Title: {video_info['title'][:60]}...")
            print(f"  Channel: {video_info['channel']}")
        except json.JSONDecodeError:
            print("  Warning: Could not parse video metadata")
    
    # Download video + subtitle
    print("  Downloading video...")
    cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "--write-sub", "--write-auto-sub",
        "--sub-lang", "id",
        "--convert-subs", "srt",
        "--merge-output-format", "mp4",
        "--ignore-errors",
        "-o", f"{output_dir}/source.%(ext)s",
        url
    ]
    
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        print("Download failed!")
        sys.exit(1)
    
    video_path = f"{output_dir}/source.mp4"
    srt_path = f"{output_dir}/source.id.srt"
    
    if not Path(srt_path).exists():
        print("Warning: No Indonesian subtitle found")
        srt_path = None
    
    # Save video info to file
    info_path = f"{output_dir}/video_info.json"
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(video_info, f, ensure_ascii=False, indent=2)
    
    return video_path, srt_path, video_info


def parse_srt(srt_path: str) -> str:
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


class SpeakerTracker:
    def __init__(self):
        # Face detector
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        # For lip movement detection
        self.prev_faces = {}
        self.movement_threshold = 500
        
        # For cut-based switching (no panning)
        self.current_target = None
        self.frames_since_switch = 0
        self.min_frames_before_switch = 210  # ~7 sec at 30fps
        self.switch_threshold = 3.0  # Movement must be 3x more to trigger switch
    
    def detect_faces(self, frame):
        """Detect all faces and return list with movement info"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50)
        )
        
        result = []
        for (x, y, w, h) in faces:
            center_x = x + w / 2
            face_id = "left" if center_x < frame.shape[1] / 2 else "right"
            
            # Get lower half of face (mouth area) for movement detection
            mouth_region = gray[y + h//2:y + h, x:x + w]
            
            # Calculate movement
            movement = 0
            if face_id in self.prev_faces and self.prev_faces[face_id] is not None:
                prev = self.prev_faces[face_id]
                if prev.shape == mouth_region.shape:
                    diff = cv2.absdiff(prev, mouth_region)
                    movement = np.sum(diff)
            
            self.prev_faces[face_id] = mouth_region.copy()
            
            result.append({
                'id': face_id,
                'center_x': center_x,
                'movement': movement
            })
        
        return result
    
    def get_target_position(self, frame, frame_width):
        """Get target X position - switches between faces like camera cuts"""
        faces = self.detect_faces(frame)
        self.frames_since_switch += 1
        
        if len(faces) == 0:
            return self.current_target if self.current_target else frame_width / 2
        
        if len(faces) == 1:
            self.current_target = faces[0]['center_x']
            return self.current_target
        
        # Multiple faces - find who's speaking most
        faces_by_id = {f['id']: f for f in faces}
        
        # Initialize target if not set
        if self.current_target is None:
            # Start with whoever is moving more
            speaker = max(faces, key=lambda f: f['movement'])
            self.current_target = speaker['center_x']
            self.current_speaker_id = speaker['id']
            return self.current_target
        
        # Check if we should switch
        current_id = "left" if self.current_target < frame_width / 2 else "right"
        other_id = "right" if current_id == "left" else "left"
        
        if current_id in faces_by_id and other_id in faces_by_id:
            current_movement = faces_by_id[current_id]['movement']
            other_movement = faces_by_id[other_id]['movement']
            
            # Switch if: enough time passed AND other person is speaking significantly more
            should_switch = (
                self.frames_since_switch > self.min_frames_before_switch and
                other_movement > current_movement * self.switch_threshold and
                other_movement > self.movement_threshold
            )
            
            if should_switch:
                self.current_target = faces_by_id[other_id]['center_x']
                self.frames_since_switch = 0
        
        return self.current_target


def convert_to_portrait(input_path: str, output_path: str):
    """Convert landscape video to 9:16 portrait with speaker tracking"""
    
    print("Converting to portrait...")
    
    # Open video
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print("Error: Cannot open video")
        return False
    
    # Get video properties
    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Calculate 9:16 crop dimensions
    target_ratio = 9 / 16
    crop_w = int(orig_h * target_ratio)
    crop_h = orig_h
    out_w, out_h = 1080, 1920
    
    # Initialize speaker tracker
    tracker = SpeakerTracker()
    
    # First pass: analyze frames
    crop_positions = []
    frame_idx = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        target_x = tracker.get_target_position(frame, orig_w)
        crop_x = int(target_x - crop_w / 2)
        crop_x = max(0, min(crop_x, orig_w - crop_w))
        crop_positions.append(crop_x)
        
        frame_idx += 1
        if frame_idx % 100 == 0:
            print(f"  Analyzed {frame_idx}/{total_frames} frames")
    
    # Stabilize shots
    crop_positions = stabilize_shots(crop_positions)
    
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
        
        crop_x = crop_positions[frame_idx]
        cropped = frame[0:crop_h, crop_x:crop_x+crop_w]
        resized = cv2.resize(cropped, (out_w, out_h), interpolation=cv2.INTER_LANCZOS4)
        out.write(resized)
        
        frame_idx += 1
        if frame_idx % 100 == 0:
            print(f"  Processed {frame_idx}/{total_frames} frames")
    
    cap.release()
    out.release()
    
    # Merge with audio
    cmd = [
        "ffmpeg", "-y",
        "-i", temp_video,
        "-i", input_path,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-map", "0:v:0", "-map", "1:a:0",
        "-shortest",
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    os.unlink(temp_video)
    
    return result.returncode == 0


def stabilize_shots(positions):
    """Stabilize positions within each shot"""
    if not positions:
        return positions
    
    stabilized = []
    shot_start = 0
    threshold = 100
    
    for i in range(len(positions)):
        if i > 0 and abs(positions[i] - positions[i-1]) > threshold:
            shot_positions = positions[shot_start:i]
            if shot_positions:
                avg = int(np.median(shot_positions))
                stabilized.extend([avg] * len(shot_positions))
            shot_start = i
    
    # Handle last shot
    shot_positions = positions[shot_start:]
    if shot_positions:
        avg = int(np.median(shot_positions))
        stabilized.extend([avg] * len(shot_positions))
    
    return stabilized


def add_captions(input_path: str, output_path: str, caption_offset: float = 0):
    """Add CapCut-style captions using Whisper
    
    Args:
        input_path: Input video path
        output_path: Output video path
        caption_offset: Time offset in seconds (for hook duration)
    """
    
    print("  Adding captions...")
    
    # Load Whisper model
    model = whisper.load_model("base")
    
    # Transcribe - if there's an offset, we need to transcribe only the main part
    # But since we're transcribing the combined video, we offset the timestamps
    result = model.transcribe(
        input_path,
        language="id",
        word_timestamps=True,
        verbose=False
    )
    
    # Create ASS subtitle in same directory as output to avoid path issues
    output_dir = Path(output_path).parent
    temp_ass_path = str(output_dir / "temp_captions.ass")
    
    create_ass_subtitle(result, temp_ass_path, time_offset=caption_offset)
    
    # For Windows FFmpeg, use forward slashes and proper escaping
    abs_ass_path = str(Path(temp_ass_path).absolute()).replace('\\', '/')
    ass_path_escaped = abs_ass_path.replace(':', '\\:')
    
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", f"ass='{ass_path_escaped}'",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "copy",
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Cleanup temp ASS file
    Path(temp_ass_path).unlink(missing_ok=True)
    
    if result.returncode != 0:
        print(f"  FFmpeg error: {result.stderr[-500:]}")
        return False
    
    return True


def create_ass_subtitle(words_data, output_path: str, time_offset: float = 0):
    """Create ASS subtitle file with CapCut-style word highlighting
    
    Args:
        words_data: Whisper transcription result
        output_path: Output ASS file path
        time_offset: Time offset in seconds to skip (for hook duration)
    """
    
    ass_content = """[Script Info]
Title: Auto-generated captions
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,70,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,50,50,350,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    events = []
    
    for segment in words_data['segments']:
        if 'words' not in segment:
            continue
        
        # Skip segments that are within the hook duration
        if segment['start'] < time_offset:
            continue
            
        words = segment['words']
        chunk_size = 4
        
        for i in range(0, len(words), chunk_size):
            chunk = words[i:i + chunk_size]
            if not chunk:
                continue
            
            for j, word in enumerate(chunk):
                word_start = word['start']
                word_end = word['end']
                
                # Skip words within hook duration
                if word_start < time_offset:
                    continue
                
                text_parts = []
                for k, w in enumerate(chunk):
                    if k == j:
                        text_parts.append(f"{{\\c&H00FFFF&}}{w['word'].strip()}{{\\c&HFFFFFF&}}")
                    else:
                        text_parts.append(w['word'].strip())
                
                text = " ".join(text_parts)
                
                events.append({
                    'start': format_time(word_start),
                    'end': format_time(word_end),
                    'text': text
                })
    
    # Write events to ASS content
    for event in events:
        ass_content += f"Dialogue: 0,{event['start']},{event['end']},Default,,0,0,0,,{event['text']}\n"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(ass_content)


def format_time(seconds: float) -> str:
    """Convert seconds to ASS time format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centisecs = int((seconds % 1) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"


def parse_timestamp(ts: str) -> float:
    """Convert timestamp to seconds"""
    ts = ts.replace(",", ".")
    parts = ts.split(":")
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])


def find_highlights(transcript: str, video_info: dict, num_clips: int = 5) -> list:
    """Find highlights and generate hook text using GPT"""
    print("\n[2/4] FINDING HIGHLIGHTS & GENERATING HOOKS")
    print("-" * 50)
    
    request_clips = num_clips + 3
    
    # Build context from video info
    video_context = ""
    if video_info:
        video_context = f"""
INFO VIDEO:
- Judul: {video_info.get('title', 'Unknown')}
- Channel: {video_info.get('channel', 'Unknown')}
- Deskripsi: {video_info.get('description', '')[:500]}
"""
    
    prompt = f"""Kamu adalah editor video profesional untuk konten PODCAST. Dari transcript video berikut, pilih {request_clips} segment yang paling menarik untuk dijadikan short-form content (TikTok/Reels/Shorts).
{video_context}
Kriteria segment yang bagus:
- Ada punchline atau momen lucu
- Ada insight atau informasi menarik  
- Ada momen emosional atau dramatis
- Ada quote yang memorable
- Cerita atau topik yang lengkap (ada awal, tengah, akhir)

⚠️ ATURAN DURASI - SANGAT PENTING, WAJIB DIIKUTI:
- Setiap clip WAJIB berdurasi MINIMAL 60 detik dan MAKSIMAL 120 detik
- TARGET durasi ideal: 90 detik (1.5 menit)
- Contoh: jika start 00:01:00,000 maka end sekitar 00:02:30,000
- HITUNG DULU selisih waktunya sebelum menentukan end_time
- Clip yang kurang dari 60 detik akan DITOLAK

⚠️ ATURAN KONTEN PODCAST - SANGAT PENTING:
- HANYA pilih segment dimana orang TERUS BERBICARA tanpa jeda
- HINDARI segment yang mengandung:
  - Jeda panjang (gap > 3 detik antara subtitle)
  - Musik/bumper/jingle (biasanya ditandai [Musik], [Music], [Tepuk tangan], atau gap tanpa dialog)
  - Transisi antar segmen acara
- Pastikan dari start sampai end, dialog KONTINYU tanpa interupsi
- Cek timestamp di transcript - jika ada gap besar antara baris subtitle, JANGAN pilih segment itu

⚠️ HOOK TEXT - SANGAT PENTING:
Untuk setiap segment, buat juga "hook_text" yang akan ditampilkan di awal video sebagai teaser.
Rules untuk hook_text:
- Maksimal 15 kata, singkat dan catchy
- Harus bikin penasaran (clickbait tapi tidak bohong)
- Bahasa Indonesia casual/gaul
- JANGAN pakai emoji
- USAHAKAN include NAMA ORANG yang disebut di segment (lihat dari transcript dan info video)
- Contoh bagus: "Mantan pembully TIARA datang ke rumah minta endorse salad buah"
- Contoh bagus: "DEDDY CORBUZIER kaget pas tau gaji asisten rumah tangga"
- Contoh bagus: "Alasan RAFFI AHMAD ga mau nikah lagi ternyata ini"

Transcript:
{transcript}

Return dalam format JSON array seperti ini:
[
  {{
    "start_time": "00:01:23,000",
    "end_time": "00:02:15,000", 
    "title": "Judul singkat untuk clip ini",
    "reason": "Alasan kenapa segment ini menarik",
    "hook_text": "Teks hook yang catchy dengan nama orang kalau ada"
  }}
]

PENTING: 
- Pastikan start_time dan end_time sesuai dengan timestamp di transcript
- Jangan overlap antar segment
- Return HANYA JSON array, tanpa text lain"""

    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    
    result = response.choices[0].message.content.strip()
    if result.startswith("```"):
        result = re.sub(r"```json?\n?", "", result)
        result = re.sub(r"```\n?", "", result)
    
    highlights = json.loads(result)
    
    # Filter by duration and limit to requested number
    valid = []
    for h in highlights:
        duration = parse_timestamp(h["end_time"]) - parse_timestamp(h["start_time"])
        h["duration_seconds"] = round(duration, 1)
        if duration >= 58:
            valid.append(h)
            print(f"  ✓ {h['title']} ({duration:.0f}s)")
            print(f"    Hook: \"{h.get('hook_text', 'N/A')}\"")
        else:
            print(f"  ⚠ Skipped: {h['title']} ({duration:.0f}s)")
        
        # Stop once we have enough valid clips
        if len(valid) >= num_clips:
            break
    
    return valid[:num_clips]  # Ensure we don't exceed requested amount


def generate_seo_metadata(title: str, reason: str) -> dict:
    """Generate SEO-friendly title and description"""
    prompt = f"""Buat title dan description yang SEO-friendly untuk video short/reels dengan topik:
Title: {title}
Konteks: {reason}

Rules:
- Title: maksimal 60 karakter, menarik, ada emoji, bahasa Indonesia
- Description: 2-3 kalimat, include hashtags relevan, bahasa Indonesia

Return JSON format:
{{"title": "...", "description": "..."}}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    
    result = response.choices[0].message.content.strip()
    if result.startswith("```"):
        result = re.sub(r"```json?\n?", "", result)
        result = re.sub(r"```\n?", "", result)
    
    return json.loads(result)


def clip_video(video_path: str, highlights: list, output_base: str):
    """Clip video, convert to portrait, add hook, and add captions"""
    print("\n[3/5] CLIPPING VIDEO")
    print("-" * 50)
    
    for i, h in enumerate(highlights, 1):
        # Create folder with timestamp
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S") + f"{i:02d}"
        clip_dir = f"{output_base}/{timestamp}"
        Path(clip_dir).mkdir(parents=True, exist_ok=True)
        
        start = h["start_time"].replace(",", ".")
        end = h["end_time"].replace(",", ".")
        
        print(f"\n[{i}/{len(highlights)}] {h['title']}")
        
        # Step 1: Cut video (landscape)
        landscape_file = f"{clip_dir}/temp_landscape.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-ss", start, "-to", end,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            landscape_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ✗ Failed to cut video")
            continue
        
        print(f"  ✓ Cut: {landscape_file}")
        
        # Step 2: Convert to portrait
        portrait_file = f"{clip_dir}/temp_portrait.mp4"
        if convert_to_portrait(landscape_file, portrait_file):
            print(f"  ✓ Portrait: {portrait_file}")
        else:
            print(f"  ✗ Failed portrait conversion")
            continue
        
        # Step 3: Add hook scene at the beginning (before captions)
        hooked_file = f"{clip_dir}/temp_hooked.mp4"
        hook_text = h.get("hook_text", h["title"])
        print(f"  Adding hook: \"{hook_text}\"")
        hook_duration = add_hook_to_clip(portrait_file, hook_text, hooked_file)
        
        if hook_duration > 0:
            print(f"  ✓ Hooked: {hooked_file} (hook: {hook_duration:.1f}s)")
        else:
            # Fallback: use portrait file without hook
            print(f"  ⚠ Hook failed, continuing without hook")
            hooked_file = portrait_file
            hook_duration = 0
        
        # Step 4: Add captions (with offset for hook duration)
        final_file = f"{clip_dir}/master.mp4"
        if add_captions(hooked_file, final_file, caption_offset=hook_duration):
            print(f"  ✓ Final: {final_file}")
        else:
            print(f"  ✗ Failed to add captions, using hooked version")
            if hooked_file != portrait_file:
                Path(hooked_file).rename(final_file)
            else:
                Path(portrait_file).rename(final_file)
        
        # Cleanup temp files
        Path(landscape_file).unlink(missing_ok=True)
        Path(portrait_file).unlink(missing_ok=True)
        if hooked_file != portrait_file:
            Path(hooked_file).unlink(missing_ok=True)
        
        # Generate SEO metadata
        metadata = generate_seo_metadata(h["title"], h["reason"])
        metadata["original_title"] = h["title"]
        metadata["hook_text"] = h.get("hook_text", "")
        metadata["hook_duration"] = hook_duration
        metadata["start_time"] = h["start_time"]
        metadata["end_time"] = h["end_time"]
        metadata["duration_seconds"] = h["duration_seconds"]
        metadata["hook_added"] = hook_duration > 0
        
        # Save data.json
        data_file = f"{clip_dir}/data.json"
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        print(f"  ✓ Data: {data_file}")


def main():
    print("=" * 60)
    print("  AUTO CLIPPER - YouTube to Short-Form Content")
    print("=" * 60)
    print()
    
    # Interactive mode or CLI args
    if len(sys.argv) >= 2:
        url = sys.argv[1]
        num_clips = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    else:
        # Interactive prompts
        url = input("🔗 Masukkan link YouTube: ").strip()
        if not url:
            print("Error: Link YouTube tidak boleh kosong!")
            sys.exit(1)
        
        num_input = input("🎬 Mau berapa clip? (default: 5): ").strip()
        num_clips = int(num_input) if num_input.isdigit() else 5
    
    print()
    print(f"  URL: {url}")
    print(f"  Jumlah clip: {num_clips}")
    print()
    
    # Setup output directory (relative to project root, not script location)
    project_root = Path(__file__).parent.parent
    output_base = project_root / "output"
    temp_dir = output_base / "_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Convert to string for compatibility
    output_base = str(output_base)
    temp_dir = str(temp_dir)
    
    # Step 1: Download
    video_path, srt_path, video_info = download_video(url, temp_dir)
    
    if not srt_path:
        print("Error: Subtitle required for highlight detection")
        sys.exit(1)
    
    # Step 2: Find highlights (with hook text generation)
    transcript = parse_srt(srt_path)
    highlights = find_highlights(transcript, video_info, num_clips)
    
    if not highlights:
        print("No valid highlights found!")
        sys.exit(1)
    
    # Step 3: Clip videos
    clip_video(video_path, highlights, output_base)
    
    print("\n[4/4] DONE!")
    print("-" * 50)
    print(f"Created {len(highlights)} clips in: {output_base}/")


if __name__ == "__main__":
    main()
