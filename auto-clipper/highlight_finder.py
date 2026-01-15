"""
Highlight Finder - Parse SRT dan cari poin menarik pakai OpenAI
Usage: python highlight_finder.py <srt_file>
"""

import sys
import re
import json
import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent.parent / ".env")

client = OpenAI(api_key=os.getenv("OPENAI_APIKEY"))


def parse_srt(srt_path: str) -> str:
    """Parse SRT file dan return sebagai plain text dengan timestamp"""
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Parse SRT format
    pattern = r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\n|\Z)"
    matches = re.findall(pattern, content, re.DOTALL)
    
    transcript_lines = []
    for idx, start, end, text in matches:
        # Clean up text (remove newlines within subtitle)
        clean_text = text.replace("\n", " ").strip()
        transcript_lines.append(f"[{start} - {end}] {clean_text}")
    
    return "\n".join(transcript_lines)


def parse_timestamp(ts: str) -> float:
    """Convert SRT timestamp to seconds"""
    # Handle both comma and dot as decimal separator
    ts = ts.replace(",", ".")
    parts = ts.split(":")
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    return hours * 3600 + minutes * 60 + seconds


def find_highlights(transcript: str, num_clips: int = 5) -> list:
    """Kirim transcript ke OpenAI untuk cari highlight moments"""
    
    # Request more clips to account for filtering
    request_clips = num_clips + 3
    
    prompt = f"""Kamu adalah editor video profesional. Dari transcript video berikut, pilih {request_clips} segment yang paling menarik untuk dijadikan short-form content (TikTok/Reels/Shorts).

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

Transcript:
{transcript}

Return dalam format JSON array seperti ini:
[
  {{
    "start_time": "00:01:23,000",
    "end_time": "00:02:15,000", 
    "title": "Judul singkat untuk clip ini",
    "reason": "Alasan kenapa segment ini menarik"
  }}
]

PENTING: 
- Pastikan start_time dan end_time sesuai dengan timestamp di transcript
- Jangan overlap antar segment
- Return HANYA JSON array, tanpa text lain"""

    response = client.chat.completions.create(
        model="gpt-5.2",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    
    result = response.choices[0].message.content.strip()
    
    # Clean up response (remove markdown code blocks if any)
    if result.startswith("```"):
        result = re.sub(r"```json?\n?", "", result)
        result = re.sub(r"```\n?", "", result)
    
    highlights = json.loads(result)
    
    # Validate duration - filter out clips shorter than 60 seconds
    valid_highlights = []
    for h in highlights:
        start = parse_timestamp(h["start_time"])
        end = parse_timestamp(h["end_time"])
        duration = end - start
        h["duration_seconds"] = round(duration, 1)
        
        if duration >= 58:  # Allow slight tolerance
            valid_highlights.append(h)
        else:
            print(f"  ⚠ Skipped '{h['title']}' - too short ({duration:.0f}s)")
    
    return valid_highlights


def main():
    if len(sys.argv) < 2:
        print("Usage: python highlight_finder.py <srt_file> [num_clips]")
        print("Example: python highlight_finder.py downloads/video.id.srt 5")
        sys.exit(1)
    
    srt_path = sys.argv[1]
    num_clips = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    if not Path(srt_path).exists():
        print(f"Error: File not found: {srt_path}")
        sys.exit(1)
    
    print(f"Parsing: {srt_path}")
    transcript = parse_srt(srt_path)
    
    print(f"Finding {num_clips} highlights...")
    highlights = find_highlights(transcript, num_clips)
    
    print("\n" + "=" * 60)
    print("HIGHLIGHTS FOUND:")
    print("=" * 60)
    
    for i, h in enumerate(highlights, 1):
        print(f"\n[Clip {i}] {h['title']}")
        print(f"  Time: {h['start_time']} → {h['end_time']} ({h['duration_seconds']}s)")
        print(f"  Why: {h['reason']}")
    
    # Save to JSON
    output_path = Path(srt_path).with_suffix(".highlights.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(highlights, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Saved to: {output_path}")


if __name__ == "__main__":
    main()
