"""
Video Clipper - Potong video berdasarkan highlights JSON
Usage: python video_clipper.py <video_file> <highlights_json>
"""

import subprocess
import sys
import json
from pathlib import Path


def clip_video(video_path: str, highlights_path: str, output_dir: str = "clips"):
    """Potong video berdasarkan timestamps dari highlights JSON"""
    
    # Load highlights
    with open(highlights_path, "r", encoding="utf-8") as f:
        highlights = json.load(f)
    
    if not highlights:
        print("No highlights found!")
        return
    
    # Buat folder output
    Path(output_dir).mkdir(exist_ok=True)
    
    video_name = Path(video_path).stem
    
    print(f"Video: {video_path}")
    print(f"Clips: {len(highlights)}")
    print("-" * 50)
    
    for i, h in enumerate(highlights, 1):
        start = h["start_time"].replace(",", ".")
        end = h["end_time"].replace(",", ".")
        title = h["title"]
        
        # Sanitize title for filename
        safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title)[:50]
        output_file = f"{output_dir}/clip_{i:02d}_{safe_title}.mp4"
        
        print(f"\n[{i}/{len(highlights)}] {title}")
        print(f"  {start} → {end}")
        
        # FFmpeg command - accurate cut with re-encode for sync
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite
            "-i", video_path,
            "-ss", start,  # Start time (after -i for accuracy)
            "-to", end,    # End time
            "-c:v", "libx264",   # Re-encode video
            "-preset", "fast",   # Encoding speed
            "-crf", "18",        # Quality (lower = better, 18 is visually lossless)
            "-c:a", "aac",       # Re-encode audio to AAC
            "-b:a", "192k",      # Audio bitrate
            output_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"  ✓ Saved: {output_file}")
        else:
            print(f"  ✗ Failed: {result.stderr[:200]}")
    
    print("\n" + "-" * 50)
    print(f"Done! Clips saved to: {output_dir}/")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python video_clipper.py <video_file> <highlights_json>")
        print("Example: python video_clipper.py downloads/video.mp4 downloads/video.highlights.json")
        sys.exit(1)
    
    video_path = sys.argv[1]
    highlights_path = sys.argv[2]
    
    if not Path(video_path).exists():
        print(f"Error: Video not found: {video_path}")
        sys.exit(1)
    
    if not Path(highlights_path).exists():
        print(f"Error: Highlights not found: {highlights_path}")
        sys.exit(1)
    
    clip_video(video_path, highlights_path)
