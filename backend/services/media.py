import json
import shutil
import subprocess
import logging
import tempfile
import math
import time
from pathlib import Path


def run(args, cwd=None):
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode:
        logging.error('Media command failed: %s', result.stderr[-3000:])
        raise RuntimeError('Media processing failed. Check that the video is readable and sufficient disk space is available.')
    return result.stdout, result.stderr


def render_with_progress(args, duration, progress=None, cwd=None):
    """Drain FFmpeg progress continuously; keep error output off the pipe to avoid deadlocks."""
    command = [args[0], '-nostats', '-progress', 'pipe:1', *args[1:]]
    with tempfile.TemporaryFile(mode='w+b') as errors:
        process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=errors,
                                   text=True, encoding='utf-8', errors='replace')
        last_update = 0
        try:
            for line in process.stdout:
                key, _, value = line.strip().partition('=')
                if key == 'out_time_us' and value.lstrip('-').isdigit() and time.monotonic()-last_update >= .35:
                    seconds = max(0, int(value)/1_000_000)
                    if progress:
                        progress(min(.99, seconds/max(duration, .01)))
                    last_update = time.monotonic()
            if process.wait():
                errors.seek(0)
                logging.error('FFmpeg render failed: %s', errors.read().decode('utf-8', errors='replace')[-3000:])
                raise RuntimeError('Rendering failed. Check free disk space and that FFmpeg supports H.264 and ASS captions.')
            if progress:
                progress(1)
        finally:
            process.stdout.close()
            if process.poll() is None:
                process.terminate()
                process.wait()


def require_tools():
    for tool in ('ffmpeg', 'ffprobe'):
        if not shutil.which(tool):
            raise RuntimeError(f'{tool} is missing. Install FFmpeg and reopen the app.')


def probe(path):
    require_tools()
    out, _ = run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)])
    data = json.loads(out)
    video = next((s for s in data['streams'] if s['codec_type'] == 'video'), None)
    if not video or not any(s['codec_type'] == 'audio' for s in data['streams']):
        raise ValueError('Choose a video containing both video and spoken audio.')
    duration = float(data.get('format', {}).get('duration', 0))
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('This video has no usable duration. Choose a complete video file rather than a live stream.')
    return dict(duration=duration, width=video['width'], height=video['height'], fps=video.get('avg_frame_rate'),
                format=data['format'].get('format_name', ''), video_codec=video.get('codec_name'))


def extract_audio(source, target):
    temporary = target.with_name(target.stem+'.partial.wav')
    try:
        run(['ffmpeg', '-y', '-i', str(source), '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(temporary)])
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def compute_audio_energy(audio_path, window_sec=0.5):
    """
    Computes RMS audio energy profile across 16kHz mono PCM WAV.
    Returns:
        dict with window_sec, energies list, mean, median, p75, p90.
    """
    import wave
    import numpy as np
    try:
        path = Path(audio_path)
        if not path.is_file():
            return {}
        with wave.open(str(path), 'rb') as wf:
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            if n_frames == 0 or framerate == 0:
                return {}
            frames = wf.readframes(n_frames)
            samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32)

            samples_per_window = max(1, int(framerate * window_sec))
            n_windows = len(samples) // samples_per_window
            if n_windows == 0:
                return {}

            truncated = samples[:n_windows * samples_per_window].reshape(n_windows, samples_per_window)
            rms = np.sqrt(np.mean(truncated ** 2, axis=1))

            p99 = float(np.percentile(rms, 99)) if len(rms) > 10 else float(np.max(rms) or 1.0)
            p99 = max(p99, 1.0)
            norm_rms = np.clip(rms / p99, 0.0, 1.0)

            return dict(
                window_sec=window_sec,
                energies=[round(float(v), 3) for v in norm_rms],
                mean=round(float(np.mean(norm_rms)), 3),
                median=round(float(np.median(norm_rms)), 3),
                p75=round(float(np.percentile(norm_rms, 75)), 3),
                p90=round(float(np.percentile(norm_rms, 90)), 3)
            )
    except Exception as e:
        logging.warning('Audio energy extraction skipped: %s', e)
        return {}


def detect(source, duration, audio_path=None):
    _, log = run(['ffmpeg', '-hide_banner', '-i', str(source), '-vf', "scale=320:-2,select='gt(scene,0.35)',showinfo", '-af', 'silencedetect=noise=-32dB:d=0.8', '-f', 'null', '-'])
    import re
    scenes = [float(x) for x in re.findall(r'pts_time:([\d.]+)', log)]
    silence = []
    start = None
    for line in log.splitlines():
        a = re.search(r'silence_start: ([\d.]+)', line)
        b = re.search(r'silence_end: ([\d.]+)', line)
        if a:
            start = float(a[1])
        if b and start is not None:
            silence.append([start, float(b[1])])
            start = None
    if start is not None:
        silence.append([start, duration])
    result = dict(scenes=scenes, silence=silence)
    if audio_path:
        result['audio_energy'] = compute_audio_energy(audio_path)
    return result
