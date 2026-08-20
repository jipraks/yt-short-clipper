"""Convert landscape video to portrait (9:16).

Two modes:
  * ``convert_to_portrait``           – face-tracked dynamic crop (MediaPipe)
  * ``convert_to_portrait_centered``  – static center crop, no face detection
"""

import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable

import cv2
import numpy as np

# Explicit import of MediaPipe Tasks API (not lazy-loaded, works with PyInstaller)
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from .helpers import get_face_landmarker_model_path, get_ffmpeg_path

LogFn = Callable[[str], None]

_SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920

# If the encode makes no frame progress for this long, treat it as a hang,
# kill ffmpeg, and surface a logged error instead of blocking indefinitely.
# Generous on purpose: a single libx264 frame is sub-second even on CPU, so
# this only trips on a genuine stall, never on slow-but-alive encoding.
ENCODE_STALL_TIMEOUT_S = 300

# --- Reframe tracking tuning ---
EMA_ALPHA = 0.15          # how fast the crop follows the target (higher = snappier)
DEADZONE_FRAC = 0.02      # ignore target moves smaller than this * crop_w (anti-jitter)
SNAP_FRAC = 0.35          # target jump larger than this * crop_w = scene cut, snap instantly
CONTINUITY_WEIGHT = 0.4   # penalty for choosing a face far from the current crop (subject stickiness)
SPEAKER_BONUS = 2.0       # how much active speaking boosts a face's selection score
MIN_SPEAK_RATIO = 0.18    # (mouth opening / face height) above this counts as "speaking"

# Lip landmark indices for mouth openness
LIP_INDICES = {13, 14, 78, 81, 82, 84, 87, 88, 95, 146, 178, 181, 185, 191, 308, 312, 317, 318, 324, 375, 402, 405, 409, 415}


def convert_to_portrait(
    input_path: str,
    output_path: str,
    log: LogFn | None = None,
) -> str:
    log = log or (lambda m: None)
    log("Converting to portrait (9:16) with MediaPipe Face Landmarker...")

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {input_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    log(f"Source: {orig_w}x{orig_h} @ {fps:.1f}fps, {total_frames} frames")

    # 9:16 crop keeps full height; width = height * (1080/1920). Clamp so a
    # source narrower than 9:16 just uses the full width (no negative range).
    crop_h = orig_h
    crop_w = min(orig_w, max(2, int(round(orig_h * OUTPUT_WIDTH / OUTPUT_HEIGHT))))
    log(f"Crop window: {crop_w}x{crop_h} (horizontal tracking range: {orig_w - crop_w}px)")

    # Create Face Landmarker using Tasks API
    model_path = get_face_landmarker_model_path()
    log(f"Using face landmarker model: {model_path}")
    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_faces=10,
        min_face_detection_confidence=0.35,
    )
    face_landmarker = vision.FaceLandmarker.create_from_options(options)

    import mediapipe as mp

    positions: list[tuple[int, int]] = []
    half_w = crop_w / 2.0
    max_x = max(0, orig_w - crop_w)
    smoothed_cx = orig_w / 2.0          # current crop centre (smoothed)
    last_face_cx: float | None = None   # last centre we actually saw a face at
    no_face_frames = 0                  # diagnostic: frames where no face was detected

    deadzone = DEADZONE_FRAC * crop_w
    snap_dist = SNAP_FRAC * crop_w

    cap = cv2.VideoCapture(input_path)
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # cv2 reads frames as BGR; MediaPipe expects RGB. Without this
        # conversion the R/B channels are swapped and detection accuracy
        # collapses (skin tones read as blue). The original BGR `frame` is
        # still used for encoding below, which is correct (raw bgr24 output).
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        ts = int(frame_idx / fps * 1000)
        results = face_landmarker.detect_for_video(mp_image, ts)

        h_img, w_img = frame.shape[:2]
        target_cx: float | None = None

        if results.face_landmarks:
            # Pick the primary subject every frame by scoring each face on
            # prominence (size), speaking activity, and continuity with the
            # current crop. No hard gate on speaking -> the face is always tracked.
            best_score = -1e9
            for landmarks in results.face_landmarks:
                xs = [lm.x * w_img for lm in landmarks]
                ys = [lm.y * h_img for lm in landmarks]
                fx_min, fx_max = min(xs), max(xs)
                fy_min, fy_max = min(ys), max(ys)
                face_cx = (fx_min + fx_max) / 2.0
                face_w = max(fx_max - fx_min, 1.0)
                face_h = max(fy_max - fy_min, 1.0)

                lip_ys = [lm.y * h_img for i, lm in enumerate(landmarks) if i in LIP_INDICES]
                openness_ratio = (max(lip_ys) - min(lip_ys)) / face_h if len(lip_ys) >= 2 else 0.0
                speak_term = openness_ratio if openness_ratio > MIN_SPEAK_RATIO else 0.0

                size_term = face_w / orig_w
                cont_term = abs(face_cx - smoothed_cx) / orig_w
                score = size_term * (1.0 + SPEAKER_BONUS * speak_term) - CONTINUITY_WEIGHT * cont_term

                if score > best_score:
                    best_score = score
                    target_cx = face_cx

            last_face_cx = target_cx
        else:
            # No face this frame: hold the last known subject position.
            no_face_frames += 1
            target_cx = last_face_cx if last_face_cx is not None else orig_w / 2.0

        # Smooth the crop towards the target, snapping on big jumps (cuts /
        # speaker switches) and ignoring tiny moves (anti-jitter).
        delta = target_cx - smoothed_cx
        if abs(delta) > snap_dist:
            smoothed_cx = target_cx
        elif abs(delta) > deadzone:
            smoothed_cx += EMA_ALPHA * delta

        x = int(round(smoothed_cx - half_w))
        x = max(0, min(x, max_x))
        positions.append((x, 0))
        frame_idx += 1

    cap.release()
    face_landmarker.close()
    detected = len(positions) - no_face_frames
    pct = (no_face_frames / len(positions) * 100) if positions else 0.0
    log(f"Face tracking complete: {len(positions)} positions computed "
        f"({detected} with face, {no_face_frames} without = {pct:.0f}% no-face)")

    _encode_with_positions(input_path, output_path, positions, crop_w, crop_h, get_ffmpeg_path(), fps, log)
    log(f"Portrait conversion complete: {output_path}")
    return output_path


def _encode_with_positions(input_path, output_path, positions, crop_w, crop_h, ffmpeg_path, fps, log):
    cap = cv2.VideoCapture(input_path)
    out_h, out_w = OUTPUT_HEIGHT, OUTPUT_WIDTH

    audio_path = Path(output_path).parent / "_temp_audio.aac"
    audio_proc = subprocess.run([
        ffmpeg_path, "-y", "-i", input_path,
        "-vn", "-c:a", "aac", "-b:a", "192k", str(audio_path),
    ], capture_output=True, creationflags=_SUBPROCESS_FLAGS)
    if audio_proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg audio extraction failed (exit code {audio_proc.returncode}). "
            f"stderr:\n{(audio_proc.stderr or b'').decode(errors='replace')[-2000:]}"
        )

    cmd = [
        ffmpeg_path, "-y",
        "-f", "rawvideo", "-pix_fmt", "bgr24",
        "-s", f"{out_w}x{out_h}", "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "copy",
        output_path,
    ]
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        creationflags=_SUBPROCESS_FLAGS,
    )

    # Drain ffmpeg's stderr on a background thread. We feed raw frames into
    # ffmpeg's stdin in the loop below; if nobody reads stderr, ffmpeg blocks
    # once the OS pipe buffer (~64KB on Windows) fills with its encoding stats,
    # which stops it reading stdin, which blocks our stdin.write() forever — a
    # silent deadlock (the "stuck for hours with no error" symptom).
    stderr_chunks: list[bytes] = []

    def _drain_stderr() -> None:
        assert proc.stderr is not None
        for line in iter(proc.stderr.readline, b""):
            stderr_chunks.append(line)

    stderr_thread = threading.Thread(target=_drain_stderr, daemon=True, name="ffmpeg-stderr")
    stderr_thread.start()

    total_positions = len(positions)
    frame_idx = 0
    log_interval = max(1, total_positions // 10)  # Log every ~10%

    # Watchdog: if no frame is written for ENCODE_STALL_TIMEOUT_S, kill ffmpeg
    # so the blocking stdin.write() unblocks (BrokenPipeError) and we raise a
    # clear error rather than hanging forever. `last_progress` is the monotonic
    # timestamp of the most recent successful frame write.
    last_progress = [time.monotonic()]
    stop_watchdog = threading.Event()
    stalled = threading.Event()

    def _watchdog() -> None:
        while not stop_watchdog.wait(10):
            idle = time.monotonic() - last_progress[0]
            if idle > ENCODE_STALL_TIMEOUT_S:
                stalled.set()
                log(f"❌ Portrait encoding stalled: no frame progress for {int(idle)}s. Terminating ffmpeg.")
                try:
                    proc.kill()
                except OSError:
                    pass
                return

    watchdog_thread = threading.Thread(target=_watchdog, daemon=True, name="ffmpeg-watchdog")
    watchdog_thread.start()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            x, y = positions[frame_idx] if frame_idx < len(positions) else (0, 0)
            resized = cv2.resize(frame[y:y + crop_h, x:x + crop_w], (out_w, out_h), interpolation=cv2.INTER_LINEAR)
            try:
                proc.stdin.write(resized.tobytes())
            except (BrokenPipeError, OSError):
                break
            last_progress[0] = time.monotonic()
            frame_idx += 1
            if frame_idx % log_interval == 0:
                pct = int(frame_idx / total_positions * 100)
                log(f"Encoding portrait: {pct}% ({frame_idx}/{total_positions} frames)")
    finally:
        stop_watchdog.set()
        watchdog_thread.join(timeout=2)

    cap.release()
    if proc.stdin:
        try:
            proc.stdin.close()
        except OSError:
            pass
    proc.wait()
    stderr_thread.join(timeout=5)

    if stalled.is_set():
        err = b"".join(stderr_chunks).decode(errors="replace")
        raise RuntimeError(
            f"Portrait encoding stalled with no progress for over "
            f"{ENCODE_STALL_TIMEOUT_S}s and was terminated (reached "
            f"{frame_idx}/{total_positions} frames). "
            f"ffmpeg stderr:\n{err.strip()[-2000:]}"
        )

    if proc.returncode != 0:
        err = b"".join(stderr_chunks).decode(errors="replace")
        raise RuntimeError(
            f"ffmpeg portrait encoding failed (exit code {proc.returncode}). "
            f"stderr:\n{err.strip()[-2000:]}"
        )

    if audio_path.exists():
        final_path = str(Path(output_path).parent / "_final.mp4")
        mux_proc = subprocess.run([
            ffmpeg_path, "-y", "-i", output_path, "-i", str(audio_path),
            "-c:v", "copy", "-c:a", "copy", "-shortest", final_path,
        ], capture_output=True, creationflags=_SUBPROCESS_FLAGS)
        if mux_proc.returncode != 0:
            raise RuntimeError(
                f"ffmpeg mux (video+audio) failed (exit code {mux_proc.returncode}). "
                f"stderr:\n{(mux_proc.stderr or b'').decode(errors='replace')[-2000:]}"
            )
        Path(output_path).unlink()
        Path(final_path).rename(output_path)
        audio_path.unlink()

    log(f"Encoded {frame_idx} frames -> {output_path}")


# ---------------------------------------------------------------------------
# Centered mode — no face tracking, single-pass ffmpeg
# ---------------------------------------------------------------------------


def convert_to_portrait_centered(
    input_path: str,
    output_path: str,
    background: str = "black",
    log: LogFn | None = None,
) -> str:
    """Convert landscape video to 9:16 portrait with the source centered.

    No MediaPipe, no OpenCV frame loop — a single ffmpeg pass that scales the
    16:9 source to fit within 1080x1920 and pads the vertical space.

    ``background``:
      * "black"   – solid black bars (fastest)
      * "blurred" – stretched + blurred copy of the source behind the video
    """
    log = log or (lambda m: None)
    log(f"Converting to portrait (centered, bg={background}) — single-pass ffmpeg...")

    ffmpeg_path = get_ffmpeg_path()

    # Probe source duration for progress reporting
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {input_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0.0
    cap.release()
    log(f"Source: {fps:.1f}fps, {total_frames} frames, {duration:.1f}s")

    # Build filtergraph
    if background == "blurred":
        vf = (
            "[0:v]split=2[bg][fg];"
            "[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,gblur=sigma=20[bgblur];"
            "[fg]scale=1080:1920:force_original_aspect_ratio=decrease[fgfit];"
            "[bgblur][fgfit]overlay=(W-w)/2:(H-h)/2[v]"
        )
        filter_flags = ["-filter_complex", vf, "-map", "[v]", "-map", "0:a?"]
    else:
        vf = (
            "scale=1080:1920:force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black"
        )
        filter_flags = ["-vf", vf]

    # Pick encoder — prefer GPU hardware encoder when available
    from .gpu import detect_gpu
    gpu_info = detect_gpu()
    enc = gpu_info.get("encoder", {})
    enc_name = enc.get("name") if enc.get("available") else None
    enc_preset = enc.get("preset")

    def build_video_enc_args(name: str | None, preset: str | None) -> list[str]:
        if name == "h264_nvenc":
            args = ["-c:v", name]
            if preset:
                args += ["-preset", preset]
            args += ["-rc", "vbr", "-cq", "23"]
            return args
        if name:
            args = ["-c:v", name]
            if preset:
                args += ["-preset", preset]
            return args
        return ["-c:v", "libx264", "-preset", "fast", "-crf", "18"]

    if enc_name:
        log(f"Using GPU encoder: {enc_name} (preset={enc_preset}) — {gpu_info['gpu']['name']}")
    else:
        log(f"Using CPU encoder: libx264 ({enc.get('reason', 'No GPU detected')})")

    def run_encode(video_enc_args: list[str], tag: str) -> tuple[int, str]:
        cmd = [
            ffmpeg_path, "-y", "-nostats", "-i", input_path,
            *filter_flags,
            *video_enc_args,
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            "-progress", "pipe:2",
            output_path,
        ]

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            creationflags=_SUBPROCESS_FLAGS,
            text=True,
        )

        stderr_chunks: list[str] = []
        last_pct = -1
        assert proc.stderr is not None
        for line in proc.stderr:
            stderr_chunks.append(line)
            line = line.strip()
            if line.startswith("out_time_us=") and duration > 0:
                cur = int(line.split("=", 1)[1]) / 1_000_000
                pct = min(99, int(cur / duration * 100))
                if pct > last_pct and pct % 10 == 0:
                    last_pct = pct
                    log(f"Encoding centered ({tag}): {pct}%")

        proc.wait()
        return proc.returncode, "".join(stderr_chunks)

    video_enc = build_video_enc_args(enc_name, enc_preset)
    tag = enc_name or "libx264"
    returncode, stderr_text = run_encode(video_enc, tag)

    # Self-heal: if the hardware encoder failed at runtime (despite passing
    # the build-time `-encoders` check and even the one-frame probe — driver
    # state can still flip mid-encode on Optimus/old Maxwell parts), retry
    # exactly once with the software encoder so the user still gets a clip.
    if returncode != 0 and enc_name and enc_name != "libx264":
        err_tail = "\n".join(stderr_text.strip().splitlines()[-12:])
        log(
            f"❌ GPU encoder {enc_name} failed (exit code {returncode}). "
            f"Retrying with CPU libx264. ffmpeg stderr:\n{err_tail}"
        )
        video_enc = build_video_enc_args(None, None)
        returncode, stderr_text = run_encode(video_enc, "libx264")

    if returncode != 0:
        err_tail = "\n".join(stderr_text.strip().splitlines()[-20:])
        raise RuntimeError(
            f"ffmpeg encoding failed (exit code {returncode}). ffmpeg stderr:\n{err_tail}"
        )

    log(f"Centered portrait conversion complete: {output_path}")
    return output_path
