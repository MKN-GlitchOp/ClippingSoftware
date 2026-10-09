import json
import logging
import shutil
import copy
from . import storage
from .media import probe, extract_audio, detect, require_tools
from .downloader import download
from .transcription import transcribe
from .clip_analysis import analyze, improve_with_ollama, ANALYSIS_VERSION


def process(pid):
    project = storage.load(pid)
    base = storage.folder(pid)
    def progress(stage, value, detail=None):
        project.update(status=stage, progress=value, detail=detail or stage.capitalize())
        storage.save(project)
    try:
        require_tools()
        if shutil.disk_usage(base).free < 1024**3:
            raise RuntimeError('Less than 1 GB of free space remains. Free disk space before processing.')
        from pathlib import Path
        if project.get('url') and not Path(project.get('source_path','')).is_file():
            progress('downloading', 5)
            source, title = download(project['url'], base / 'source', progress)
            project.update(source_path=str(source), title=title)
        source = project['source_path']
        project['media'] = probe(source)
        duration = project['media']['duration']
        # PCM audio alone requires about 32 KB per second; leave space for exports.
        if shutil.disk_usage(base).free < duration*32000 + 512*1024**2:
            raise RuntimeError('Insufficient disk space for audio and exports.')
        progress('extracting audio', 26)
        audio = base / 'audio' / 'speech.wav'
        if not audio.exists():
            extract_audio(source, audio)
        transcript_file = base/'transcript'/'transcript.json'
        if transcript_file.exists():
            progress('loading transcript', 70, 'Reusing the saved transcript')
            transcript = json.loads(transcript_file.read_text(encoding='utf-8'))
        else:
            progress('loading speech model', 29, 'Loading the local speech model. First use requires a download.')
            transcript = transcribe(audio, base / 'transcript', duration, progress, project['settings']['model'])
        signals_file = base/'analysis'/'signals.json'
        if signals_file.exists():
            signals = json.loads(signals_file.read_text(encoding='utf-8'))
        else:
            progress('detecting scenes and silence', 72)
            signals = detect(source, duration, audio_path=audio)
            signals_file.write_text(json.dumps(signals, indent=2), encoding='utf-8')
        if 'audio_energy' not in signals and audio.exists():
            from .media import compute_audio_energy
            signals['audio_energy'] = compute_audio_energy(audio)
            signals_file.write_text(json.dumps(signals, indent=2), encoding='utf-8')
        audience_file = base/'source'/'audience.json'
        if audience_file.exists():
            try:
                signals['heatmap'] = json.loads(audience_file.read_text(encoding='utf-8')).get('heatmap', [])
            except (ValueError, OSError):
                pass
        progress('analyzing moments', 85)
        if project['settings'].get('use_public_benchmarks', True):
            from .benchmarks import load_index
            try:
                signals['benchmark_index'] = load_index()
            except Exception:
                logging.warning('Public benchmark database unavailable; using local analysis', exc_info=True)
        analysis_settings = dict(project['settings'])
        if analysis_settings.get('content_profile','auto') == 'auto':
            from .streamer import public_moment
            if public_moment(project.get('title','')):
                analysis_settings['content_profile'] = 'streamer'
        candidates = analyze(transcript, analysis_settings, signals, duration)
        project.pop('warning',None)
        if project['settings'].get('ollama_model'):
            progress('local LLM review', 90)
            try:
                candidates = improve_with_ollama(copy.deepcopy(candidates), project['settings']['ollama_model'])
            except Exception:
                project['warning'] = 'Ollama was unavailable or returned an invalid result. Heuristic selection is ready.'
        project['candidates'] = candidates
        project['analysis_version'] = ANALYSIS_VERSION
        (base / 'analysis' / 'candidates.json').write_text(json.dumps(candidates, indent=2), encoding='utf-8')
        progress('ready', 100, f'{len(candidates)} moments ready to review')
    except Exception as exc:
        logging.exception('Project processing failed')
        project.update(status='error', error=str(exc), progress=0)
        storage.save(project)
