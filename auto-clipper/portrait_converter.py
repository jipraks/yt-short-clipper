"""
Portrait Converter - Convert landscape video to 9:16 with speaker cut (no panning)
Usage: python portrait_converter.py <input_video> [output_video]
"""

import sys
import cv2
import numpy as np
from pathlib import Path
import subprocess
import tempfile
import os


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
        self.current_target = None  # Current face we're focused on
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


def convert_to_portrait(input_path: str, output_path: str = None):
    """Convert landscape video to 9:16 portrait with face tracking"""
    
    if output_path is None:
        p = Path(input_path)
        output_path = str(p.parent / f"{p.stem}_portrait{p.suffix}")
    
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    
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
    
    # Calculate 9:16 crop dimensions (keep full height, crop width)
    target_ratio = 9 / 16
    crop_w = int(orig_h * target_ratio)
    crop_h = orig_h
    
    # Output dimensions (1080x1920 for shorts)
    out_w, out_h = 1080, 1920
    
    print(f"Original: {orig_w}x{orig_h}")
    print(f"Crop area: {crop_w}x{crop_h}")
    print(f"Output: {out_w}x{out_h}")
    print(f"Frames: {total_frames}")
    print("-" * 50)
    
    # Initialize speaker tracker
    tracker = SpeakerTracker()
    
    # First pass: analyze all frames to get crop positions
    print("Pass 1/2: Analyzing speakers...")
    crop_positions = []
    frame_idx = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Get target position (instant cut, no smoothing)
        target_x = tracker.get_target_position(frame, orig_w)
        
        # Calculate crop X (ensure within bounds)
        crop_x = int(target_x - crop_w / 2)
        crop_x = max(0, min(crop_x, orig_w - crop_w))
        
        crop_positions.append(crop_x)
        
        frame_idx += 1
        if frame_idx % 100 == 0:
            print(f"  Analyzed {frame_idx}/{total_frames} frames")
    
    print(f"  Done! {len(crop_positions)} frames analyzed")
    
    # NO smoothing - we want instant cuts
    # Just stabilize within each "shot" (same target)
    print("  Stabilizing shots...")
    crop_positions = stabilize_shots(crop_positions)
    
    # Second pass: create cropped video (frames only, no audio)
    print("Pass 2/2: Creating portrait video...")
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    
    # Use temp file for video without audio
    temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False).name
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_video, fourcc, fps, (out_w, out_h))
    
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Crop
        crop_x = crop_positions[frame_idx]
        cropped = frame[0:crop_h, crop_x:crop_x+crop_w]
        
        # Resize to output dimensions
        resized = cv2.resize(cropped, (out_w, out_h), interpolation=cv2.INTER_LANCZOS4)
        
        out.write(resized)
        
        frame_idx += 1
        if frame_idx % 100 == 0:
            print(f"  Processed {frame_idx}/{total_frames} frames")
    
    cap.release()
    out.release()
    
    print(f"  Done! Merging audio...")
    
    # Merge with original audio using ffmpeg
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
    
    # Cleanup temp file
    os.unlink(temp_video)
    
    if result.returncode == 0:
        print(f"\n✓ Saved: {output_path}")
        return True
    else:
        print(f"\n✗ FFmpeg error: {result.stderr[:200]}")
        return False


def stabilize_shots(positions):
    """Stabilize positions within each shot (between cuts)"""
    if not positions:
        return positions
    
    stabilized = []
    shot_start = 0
    threshold = 100  # Minimum position change to be considered a "cut"
    
    for i in range(len(positions)):
        # Detect cut (big position change)
        if i > 0 and abs(positions[i] - positions[i-1]) > threshold:
            # End of shot - stabilize previous shot
            shot_positions = positions[shot_start:i]
            if shot_positions:
                avg = int(np.median(shot_positions))  # Use median for stability
                stabilized.extend([avg] * len(shot_positions))
            shot_start = i
    
    # Handle last shot
    shot_positions = positions[shot_start:]
    if shot_positions:
        avg = int(np.median(shot_positions))
        stabilized.extend([avg] * len(shot_positions))
    
    return stabilized


def smooth_positions(positions, window=15):
    """Apply moving average smoothing"""
    smoothed = []
    for i in range(len(positions)):
        start = max(0, i - window)
        end = min(len(positions), i + window + 1)
        smoothed.append(int(np.mean(positions[start:end])))
    return smoothed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python portrait_converter.py <input_video> [output_video]")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not Path(input_path).exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)
    
    convert_to_portrait(input_path, output_path)
