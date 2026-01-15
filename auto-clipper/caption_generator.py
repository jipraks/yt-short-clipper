"""
Caption Generator - Add CapCut-style captions using Whisper
Usage: python caption_generator.py <input_video> [output_video]
"""

import sys
import whisper
import subprocess
import json
from pathlib import Path
import tempfile


def transcribe_video(video_path: str, model_size: str = "base"):
    """Transcribe video using Whisper with word-level timestamps"""
    print(f"Loading Whisper model: {model_size}")
    model = whisper.load_model(model_size)
    
    print("Transcribing...")
    result = model.transcribe(
        video_path,
        language="id",  # Indonesian
        word_timestamps=True,  # Get per-word timing
        verbose=False
    )
    
    return result


def create_ass_subtitle(words_data, output_path: str):
    """Create ASS subtitle file with CapCut-style word highlighting"""
    
    # ASS header with CapCut-style formatting
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
Style: Highlight,Arial Black,70,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,50,50,350,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    # Extract words with timestamps from Whisper result
    events = []
    
    for segment in words_data['segments']:
        if 'words' not in segment:
            continue
            
        words = segment['words']
        
        # Group words into chunks (3-5 words per line)
        chunk_size = 4
        for i in range(0, len(words), chunk_size):
            chunk = words[i:i + chunk_size]
            
            if not chunk:
                continue
            
            start_time = chunk[0]['start']
            end_time = chunk[-1]['end']
            
            # Create text with word-by-word highlighting
            for j, word in enumerate(chunk):
                word_start = word['start']
                word_end = word['end']
                
                # Build text with current word highlighted
                text_parts = []
                for k, w in enumerate(chunk):
                    if k == j:
                        # Highlight current word (yellow)
                        text_parts.append(f"{{\\c&H00FFFF&}}{w['word'].strip()}{{\\c&HFFFFFF&}}")
                    else:
                        text_parts.append(w['word'].strip())
                
                text = " ".join(text_parts)
                
                # Add event
                events.append({
                    'start': format_time(word_start),
                    'end': format_time(word_end),
                    'text': text
                })
    
    # Write events
    for event in events:
        ass_content += f"Dialogue: 0,{event['start']},{event['end']},Default,,0,0,0,,{event['text']}\n"
    
    # Save ASS file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(ass_content)
    
    print(f"Created subtitle file: {output_path}")


def format_time(seconds: float) -> str:
    """Convert seconds to ASS time format (H:MM:SS.CC)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centisecs = int((seconds % 1) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"


def add_captions_to_video(video_path: str, ass_path: str, output_path: str):
    """Burn captions into video using ffmpeg"""
    print("Adding captions to video...")
    
    # Escape path for ffmpeg
    ass_path_escaped = ass_path.replace('\\', '/').replace(':', '\\:')
    
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", f"ass='{ass_path_escaped}'",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "copy",
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✓ Saved: {output_path}")
        return True
    else:
        print(f"✗ Error: {result.stderr[:500]}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python caption_generator.py <input_video> [output_video] [model_size]")
        print("Model sizes: tiny, base, small, medium, large")
        print("Example: python caption_generator.py video.mp4 video_captioned.mp4 base")
        sys.exit(1)
    
    input_video = sys.argv[1]
    output_video = sys.argv[2] if len(sys.argv) > 2 else None
    model_size = sys.argv[3] if len(sys.argv) > 3 else "base"
    
    if not Path(input_video).exists():
        print(f"Error: File not found: {input_video}")
        sys.exit(1)
    
    if output_video is None:
        p = Path(input_video)
        output_video = str(p.parent / f"{p.stem}_captioned{p.suffix}")
    
    print(f"Input: {input_video}")
    print(f"Output: {output_video}")
    print("-" * 50)
    
    # Step 1: Transcribe
    result = transcribe_video(input_video, model_size)
    
    # Step 2: Create ASS subtitle
    temp_ass = tempfile.NamedTemporaryFile(suffix='.ass', delete=False, mode='w', encoding='utf-8')
    temp_ass.close()
    
    create_ass_subtitle(result, temp_ass.name)
    
    # Step 3: Burn captions
    success = add_captions_to_video(input_video, temp_ass.name, output_video)
    
    # Cleanup
    Path(temp_ass.name).unlink()
    
    if success:
        print("\n✓ Done!")
    else:
        print("\n✗ Failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
