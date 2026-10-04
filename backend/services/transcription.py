import os
from pathlib import Path
from faster_whisper import WhisperModel
from faster_whisper.utils import download_model


def timestamp(t):
    ms = round(t * 1000)
    return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'


def transcribe(audio, folder, duration, progress, model_name='base'):
    cache = str(Path(__file__).resolve().parents[2] / 'models')
    try:
        model_path = download_model(model_name, cache_dir=cache, local_files_only=True)
    except Exception:
        model_path = download_model(model_name, cache_dir=cache)
    model = WhisperModel(model_path, device='cpu', compute_type='int8', cpu_threads=min(8, os.cpu_count() or 4))
    segments, info = model.transcribe(str(audio), word_timestamps=True, vad_filter=True)
    result = []
    for s in segments:
        result.append(dict(start=s.start, end=s.end, text=s.text.strip(), words=[dict(start=w.start, end=w.end, word=w.word.strip(), probability=w.probability) for w in s.words or []]))
        progress('transcribing', 30 + int(40 * min(1, s.end / duration)))
    if not result:
        raise RuntimeError('No speech was detected. Try a video with clearer spoken audio.')
    import json
    payload = dict(language=info.language, segments=result)
    temporary = folder/'transcript.partial.json'
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    temporary.replace(folder/'transcript.json')
    (folder / 'transcript.srt').write_text('\n\n'.join(f'{i+1}\n{timestamp(s["start"])} --> {timestamp(s["end"])}\n{s["text"]}' for i, s in enumerate(result)), encoding='utf-8')
    return payload
