import logging
import math
import urllib.request
from pathlib import Path

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

from .reframing import get_dimensions, crop_filter, video_filter

MODEL_DIR = Path(__file__).resolve().parents[2] / 'models' / 'face_detection'
MODEL_PATH = MODEL_DIR / 'face_detection_yunet.onnx'
MODEL_URL = 'https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx'


def ensure_model() -> bool:
    """Ensure the YuNet ONNX face detection model is available locally."""
    if not CV2_AVAILABLE:
        return False
    if MODEL_PATH.is_file() and MODEL_PATH.stat().st_size > 50_000:
        return True
    try:
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        logging.info("Downloading YuNet face detection model (232KB)...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        return MODEL_PATH.is_file() and MODEL_PATH.stat().st_size > 50_000
    except Exception as e:
        logging.warning("Could not download face detection model: %s", e)
        return False


def get_detector(width: int = 640, height: int = 360):
    if not ensure_model():
        return None
    try:
        return cv2.FaceDetectorYN.create(
            model=str(MODEL_PATH),
            config='',
            input_size=(width, height),
            score_threshold=0.55,
            nms_threshold=0.3
        )
    except Exception as e:
        logging.warning("Failed to initialize FaceDetectorYN: %s", e)
        return None


def track_clip_faces(video_path: str, start: float, end: float, default_crop_x: float = 50.0,
                     sample_interval: float = 0.5):
    """
    Samples video frames between start and end, detects the primary face position,
    and returns smoothed keypoints [(relative_time, normalized_x_fraction), ...].
    """
    fallback_fraction = max(0.0, min(1.0, default_crop_x / 100.0))
    if not CV2_AVAILABLE or not ensure_model():
        return [(0.0, fallback_fraction), (max(0.1, end - start), fallback_fraction)]

    detector = get_detector(640, 360)
    if detector is None:
        return [(0.0, fallback_fraction), (max(0.1, end - start), fallback_fraction)]

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return [(0.0, fallback_fraction), (max(0.1, end - start), fallback_fraction)]

    raw_samples = []  # [(rel_t, detected_x)]
    t = start
    duration = max(0.1, end - start)
    last_known_x = fallback_fraction
    miss_count = 0

    try:
        while t <= end:
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
            ret, frame = cap.read()
            if not ret:
                break

            small = cv2.resize(frame, (640, 360))
            detector.setInputSize((640, 360))
            _, faces = detector.detect(small)

            rel_t = round(t - start, 2)

            if faces is not None and len(faces) > 0:
                # Score faces: prefer larger area (w*h) and closeness to last_known_x
                best_face = None
                best_score = -1.0
                for f in faces:
                    fx, fy, fw, fh = f[:4]
                    conf = float(f[-1])
                    cx = (fx + fw / 2.0) / 640.0
                    area = (fw * fh) / (640.0 * 360.0)
                    dist = abs(cx - last_known_x)
                    # Closeness weight: penalize drastic jumps
                    score = (area * 0.7 + (1.0 - dist) * 0.3) * conf
                    if score > best_score:
                        best_score = score
                        best_face = (cx, conf)

                if best_face:
                    cx = best_face[0]
                    last_known_x = cx
                    miss_count = 0
                    raw_samples.append((rel_t, cx))
                else:
                    miss_count += 1
                    drift = fallback_fraction if miss_count > 4 else last_known_x
                    raw_samples.append((rel_t, drift))
            else:
                miss_count += 1
                # If face not found, gently drift to center if missing for more than 2 seconds (4 samples)
                drift = (last_known_x * 0.7 + fallback_fraction * 0.3) if miss_count > 4 else last_known_x
                raw_samples.append((rel_t, drift))

            t += sample_interval
    except Exception as e:
        logging.warning("Error during face tracking extraction: %s", e)
    finally:
        cap.release()

    if not raw_samples:
        return [(0.0, fallback_fraction), (duration, fallback_fraction)]

    # Smooth the trajectory using exponential moving average with deadband
    smoothed = []
    current_x = raw_samples[0][1]

    for rel_t, target_x in raw_samples:
        delta = target_x - current_x
        # Deadband: ignore tiny jitters under 2.5%
        if abs(delta) < 0.025:
            target_x = current_x
        else:
            # Smoothly pan towards target
            current_x = current_x + delta * 0.4

        current_x = max(0.05, min(0.95, current_x))
        smoothed.append((rel_t, round(current_x, 3)))

    # Ensure start and end bounds
    if smoothed[0][0] > 0.0:
        smoothed.insert(0, (0.0, smoothed[0][1]))
    if smoothed[-1][0] < duration:
        smoothed.append((round(duration, 2), smoothed[-1][1]))

    # Keypoint reduction: eliminate redundant points with negligible change (< 0.015)
    reduced = [smoothed[0]]
    for i in range(1, len(smoothed) - 1):
        prev = reduced[-1]
        curr = smoothed[i]
        nxt = smoothed[i + 1]
        # Keep if significant slope change or position delta
        if abs(curr[1] - prev[1]) >= 0.018 or abs(nxt[1] - curr[1]) >= 0.018:
            reduced.append(curr)
    reduced.append(smoothed[-1])

    return reduced


def build_face_tracking_filter(keyframes: list[tuple[float, float]], ratio: str = '9:16',
                               layout: str = 'crop', resolution: str = '1080p',
                               default_crop_x: float = 50.0) -> str:
    """
    Generates an FFmpeg video filter string using time-based nested piecewise interpolation
    for smooth camera panning following the speaker's face.
    """
    width, height = get_dimensions(ratio, resolution)

    if layout == 'blur':
        # Blur layout shows the full frame, no horizontal crop tracking needed
        return video_filter(ratio, 'blur', default_crop_x, resolution)

    if not keyframes or len(keyframes) <= 1:
        x_val = (keyframes[0][1] * 100.0) if keyframes else default_crop_x
        return video_filter(ratio, layout, x_val, resolution)

    # Build nested if expression: if(lt(t\,t1)\,lerp1\,if(lt(t\,t2)\,lerp2\,last))
    expr = str(keyframes[-1][1])
    for i in range(len(keyframes) - 2, -1, -1):
        t0, p0 = keyframes[i]
        t1, p1 = keyframes[i + 1]
        dt = max(0.01, t1 - t0)
        # Linear interpolation expression
        lerp = f'{p0:.3f}+({p1 - p0:.3f})*(t-{t0:.2f})/{dt:.2f}'
        expr = f'if(lt(t\\,{t1:.2f})\\,{lerp}\\,{expr})'

    return f'[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}:(iw-ow)*({expr}):(ih-oh)/2,setsar=1'
