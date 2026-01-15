"""
YouTube Video + Subtitle Downloader
Usage: python downloader.py <youtube_url>
"""

import subprocess
import sys
import os
from pathlib import Path


def download_video_with_subtitle(url: str, output_dir: str = "downloads"):
    """Download video dan subtitle dari YouTube"""
    
    # Buat folder output
    Path(output_dir).mkdir(exist_ok=True)
    
    # yt-dlp command
    # - Download video best quality (tapi max 1080p biar gak kegedean)
    # - Download subtitle (auto-generated atau manual)
    # - Convert subtitle ke SRT
    cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "--write-sub",
        "--write-auto-sub",
        "--sub-lang", "id",  # Indonesia only
        "--convert-subs", "srt",
        "--merge-output-format", "mp4",
        "--ignore-errors",  # Lanjut walau subtitle error
        "-o", f"{output_dir}/%(title)s.%(ext)s",
        url
    ]
    
    print(f"Downloading: {url}")
    print(f"Output folder: {output_dir}")
    print("-" * 50)
    
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode == 0:
        print("-" * 50)
        print("Download complete!")
        # List downloaded files
        for f in Path(output_dir).iterdir():
            print(f"  → {f.name}")
    else:
        print("Download failed!")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python downloader.py <youtube_url>")
        print("Example: python downloader.py https://www.youtube.com/watch?v=xxxxx")
        sys.exit(1)
    
    url = sys.argv[1]
    download_video_with_subtitle(url)
