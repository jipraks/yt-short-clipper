"""
Hook Generator - Generate hook scene with TTS for video clips
Creates an intro scene with first frame + hook text + AI voice
"""

import subprocess
import sys
import os
import json
import tempfile
import cv2
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
client = OpenAI(api_key=os.getenv("OPENAI_APIKEY"))


def extract_first_frame(video_path: str, output_path: str) -> bool:
    """Extract first frame from video"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return False
    
    ret, frame = cap.read()
    cap.release()
    
    if ret:
        cv2.imwrite(output_path, frame)
        return True
    return False


def generate_hook_text(title: str, context: str) -> str:
    """Generate catchy hook text using GPT"""
    prompt = f"""Buat teks hook yang singkat dan menarik untuk video short/reels.

Topik video: {title}
Konteks: {context}

Rules:
- Maksimal 15 kata
- Harus bikin penasaran/clickbait tapi tidak bohong
- Bahasa Indonesia casual
- Jangan pakai emoji
- Langsung ke poin, tanpa kata pembuka

Contoh format yang bagus:
- "Mantan pembully TIARA datang ke rumah minta endorse salad buah"
- "Ternyata ini alasan dia putus sama pacarnya"
- "Gue kaget pas tau gajinya segini"

Return HANYA teks hook, tanpa tanda kutip atau penjelasan."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
    )
    
    return response.choices[0].message.content.strip().strip('"\'')


def generate_tts_audio(text: str, output_path: str) -> bool:
    """Generate TTS audio using OpenAI (female voice)"""
    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice="nova",  # Female voice options: nova, shimmer, alloy
            input=text,
            speed=1.0
        )
        
        response.stream_to_file(output_path)
        return True
    except Exception as e:
        print(f"  TTS Error: {e}")
        return False


def get_audio_duration(audio_path: str) -> float:
    """Get audio duration in seconds"""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip()) if result.returncode == 0 else 3.0


def get_video_info(video_path: str) -> dict:
    """Get video resolution and fps"""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate",
        "-of", "json",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        import json
        data = json.loads(result.stdout)
        if data.get('streams'):
            stream = data['streams'][0]
            # Parse frame rate (e.g., "30000/1001" -> 29.97)
            fps_parts = stream.get('r_frame_rate', '30/1').split('/')
            fps = int(fps_parts[0]) / int(fps_parts[1]) if len(fps_parts) == 2 else 30
            return {
                'width': stream.get('width', 1080),
                'height': stream.get('height', 1920),
                'fps': fps
            }
    return {'width': 1080, 'height': 1920, 'fps': 30}


def create_hook_video(
    frame_path: str,
    audio_path: str,
    hook_text: str,
    output_path: str,
    duration: float = None,
    target_resolution: tuple = (1080, 1920),
    target_fps: float = 30
) -> bool:
    """Create hook video with frame, text overlay, and TTS audio"""
    
    if duration is None:
        duration = get_audio_duration(audio_path) + 0.5  # Add padding
    
    width, height = target_resolution
    
    # Split text into lines (max ~25 chars per line for readability)
    words = hook_text.split()
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        if len(" ".join(current_line)) > 25:
            if len(current_line) > 1:
                current_line.pop()
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                lines.append(" ".join(current_line))
                current_line = []
    
    if current_line:
        lines.append(" ".join(current_line))
    
    # Create drawtext filter for each line
    text_filters = []
    line_height = 80
    total_height = len(lines) * line_height
    start_y = f"(h-{total_height})/2"
    
    for i, line in enumerate(lines):
        escaped_line = line.replace("'", "'\\''").replace(":", "\\:").replace("\\", "\\\\")
        y_pos = f"({start_y})+{i * line_height}"
        
        text_filter = (
            f"drawtext=text='{escaped_line}':"
            f"fontfile='C\\:/Windows/Fonts/arialbd.ttf':"
            f"fontsize=60:"
            f"fontcolor=yellow:"
            f"borderw=3:"
            f"bordercolor=black:"
            f"x=(w-text_w)/2:"
            f"y={y_pos}:"
            f"box=1:"
            f"boxcolor=black@0.7:"
            f"boxborderw=15"
        )
        text_filters.append(text_filter)
    
    # Scale image to target resolution and add text
    filter_complex = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
    if text_filters:
        filter_complex += "," + ",".join(text_filters)
    
    # FFmpeg command: image + audio -> video with text
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", frame_path,
        "-i", audio_path,
        "-vf", filter_complex,
        "-r", str(target_fps),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"  FFmpeg error: {result.stderr[-500:]}")
        return False
    
    return True


def concat_videos(hook_path: str, main_path: str, output_path: str) -> bool:
    """Concatenate hook video with main video using filter_complex for compatibility"""
    
    # Use filter_complex concat instead of demuxer concat for better compatibility
    # This re-encodes both videos to ensure matching formats
    cmd = [
        "ffmpeg", "-y",
        "-i", hook_path,
        "-i", main_path,
        "-filter_complex", "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]",
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"  Concat error: {result.stderr[-500:]}")
        return False
    
    return True


def add_hook_to_clip(
    clip_path: str,
    hook_text: str,
    output_path: str = None
) -> float:
    """Main function: Add hook scene to beginning of clip
    
    Args:
        clip_path: Path to the main video clip
        hook_text: Pre-generated hook text to display
        output_path: Output path for final video (optional)
    
    Returns:
        float: Duration of hook in seconds, or 0 if failed
    """
    
    if output_path is None:
        p = Path(clip_path)
        output_path = str(p.parent / f"{p.stem}_hooked{p.suffix}")
    
    print(f"  Adding hook to: {Path(clip_path).name}")
    
    # Get main video info for matching resolution/fps
    video_info = get_video_info(clip_path)
    target_resolution = (video_info['width'], video_info['height'])
    target_fps = video_info['fps']
    
    # Create temp files
    temp_dir = tempfile.mkdtemp()
    frame_path = f"{temp_dir}/first_frame.jpg"
    audio_path = f"{temp_dir}/hook_audio.mp3"
    hook_video_path = f"{temp_dir}/hook_video.mp4"
    
    hook_duration = 0
    
    try:
        # Step 1: Extract first frame
        if not extract_first_frame(clip_path, frame_path):
            print("  ✗ Failed to extract first frame")
            return 0
        
        # Step 2: Generate TTS audio from hook text
        if not generate_tts_audio(hook_text, audio_path):
            print("  ✗ Failed to generate TTS")
            return 0
        
        # Get hook duration (audio duration + padding)
        hook_duration = get_audio_duration(audio_path) + 0.5
        
        # Step 3: Create hook video with matching resolution/fps
        if not create_hook_video(
            frame_path, audio_path, hook_text, hook_video_path,
            duration=hook_duration,
            target_resolution=target_resolution,
            target_fps=target_fps
        ):
            print("  ✗ Failed to create hook video")
            return 0
        
        # Step 4: Concatenate with main clip
        if not concat_videos(hook_video_path, clip_path, output_path):
            print("  ✗ Failed to concatenate videos")
            return 0
        
        print(f"  ✓ Saved: {output_path}")
        return hook_duration
        
    finally:
        # Cleanup temp files
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python hook_generator.py <clip_path> <hook_text>")
        print("Example: python hook_generator.py clips/clip_01.mp4 'TIARA kaget pas tau mantan pembully nya datang'")
        sys.exit(1)
    
    clip_path = sys.argv[1]
    hook_text = sys.argv[2]
    
    if not Path(clip_path).exists():
        print(f"Error: File not found: {clip_path}")
        sys.exit(1)
    
    duration = add_hook_to_clip(clip_path, hook_text)
    if duration > 0:
        print(f"Hook duration: {duration:.1f}s")
