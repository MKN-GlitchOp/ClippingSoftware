import json
import logging
import shutil
import uuid
import tempfile
import zipfile
import threading
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.background import BackgroundTask
from pydantic import BaseModel, Field, model_validator
from typing import Literal
from backend.services import storage
from backend.services.pipeline import process
from backend.services.downloader import normalize_url, friendly_error


@asynccontextmanager
async def lifespan(app):
    # A saved progress label isn't evidence that a worker survived an app restart.
    for path in storage.ROOT.glob('*/project.json'):
        try:
            p = storage.load(path.parent.name)
            if p.get('status') == 'error' and p.get('url') and ('\x1b' in p.get('error','') or 'HTTP Error 403' in p.get('error','')):
                p['error'] = friendly_error(p['error'])
                storage.save(p)
            if p['status'] not in ('ready','error') and p['id'] not in jobs:
                if p.get('last_operation') == 'render' or p['status'] == 'rendering':
                    p.update(status='ready', progress=0, warning='Rendering was interrupted. You can retry the unfinished clips.')
                    for c in p.get('candidates',[]):
                        if c.get('render_status') == 'rendering':
                            c.update(render_status='error', render_error='Rendering was interrupted. Render this clip again.')
                else:
                    p.update(status='error', error='Analysis was interrupted. Retry to reuse completed downloads and transcripts.', progress=0)
                storage.save(p)
        except (OSError, ValueError, KeyError):
            logging.warning('Could not recover project %s',path.parent.name)
    yield

app = FastAPI(title='LocalCut', lifespan=lifespan)
from backend.api.benchmarks import router as benchmarks_router
app.include_router(benchmarks_router)
from backend.api.trends import router as trends_router
app.include_router(trends_router)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1','localhost','testserver'])
worker = ThreadPoolExecutor(max_workers=1)
jobs = set()
thumbnail_lock = threading.Lock()


@app.middleware('http')
async def local_requests(request, call_next):
    if request.method not in ('GET','HEAD','OPTIONS'):
        origin=request.headers.get('origin')
        if origin and origin not in ('http://127.0.0.1:8000','http://localhost:8000','http://127.0.0.1:5173','http://localhost:5173'):
            return JSONResponse(status_code=403,content={'detail':'Use the app from its local address.'})
    return await call_next(request)


class Settings(BaseModel):
    use_public_benchmarks: bool = True
    content_profile: Literal['auto','streamer','gaming','education','podcast','story'] = 'auto'
    num_clips: int = Field(default=10, ge=1, le=50)
    auto_pilot: bool = False
    caption_style: Literal['hormozi','beast','neon','boxed','minimal','classic'] = 'hormozi'
    caption_bounce: bool = True
    caption_chunk_size: Literal['single','phrase'] = 'phrase'
    min_length: float = Field(default=20, ge=3, le=180)
    max_length: float = Field(default=60, ge=3, le=180)
    ratio: Literal['9:16','1:1','16:9'] = '9:16'
    layout: Literal['crop','blur'] = 'crop'
    captions: bool = True
    model: Literal['tiny','base','small'] = 'base'
    ollama_model: str = Field(default='', max_length=100)
    summarize_mode: bool = False

    @model_validator(mode='after')
    def lengths(self):
        if self.min_length > self.max_length:
            raise ValueError('Minimum length must not exceed maximum length.')
        return self


class URLInput(BaseModel):
    url: str
    settings: Settings = Field(default_factory=Settings)


def create(settings, title, url=None):
    pid = uuid.uuid4().hex
    for name in ('source','audio','transcript','analysis','clips','exports'):
        (storage.folder(pid)/name).mkdir(parents=True, exist_ok=True)
    project = dict(id=pid, title=title, url=url, settings=settings.model_dump(), status='queued', progress=0, candidates=[])
    storage.save(project)
    return project


def submit(pid, operation, kind='analysis'):
    with storage.LOCK:
        if pid in jobs:
            raise HTTPException(409, 'This project is already processing.')
        jobs.add(pid)
        p = storage.load(pid)
        p.update(status='queued', progress=0, last_operation=kind, detail='Waiting for the local worker')
        storage.save(p)
    def task():
        try:
            operation(pid)
        except Exception:
            logging.exception('Background job failed for %s',pid)
            p = storage.load(pid)
            p.update(status='error',error='Processing stopped unexpectedly. Retry the project to reuse saved work.')
            storage.save(p)
        finally:
            with storage.LOCK:
                jobs.discard(pid)
    worker.submit(task)


def get_project(pid):
    try:
        return storage.load(pid)
    except (ValueError, FileNotFoundError):
        raise HTTPException(404, 'Project not found.')


@app.exception_handler(Exception)
async def error_handler(request, exc):
    logging.exception('Request failed')
    return JSONResponse(status_code=500, content={'detail':'The request could not be completed. Check disk space and the application log.'})


@app.get('/api/health')
def health():
    cache = Path(__file__).resolve().parents[1]/'models'
    cached = [name for name in ('tiny','base','small') if any((cache/f'models--Systran--faster-whisper-{name}'/'snapshots').glob('*/model.bin'))]
    return dict(ffmpeg=bool(shutil.which('ffmpeg')), ffprobe=bool(shutil.which('ffprobe')), device='CPU / INT8',
                cached_models=cached, free_gb=round(shutil.disk_usage(storage.ROOT).free/1024**3,1), version='0.2.0')


@app.get('/api/projects')
def projects():
    result = []
    for path in sorted(storage.ROOT.glob('*/project.json'), key=lambda p:p.stat().st_mtime, reverse=True):
        try:
            p = storage.load(path.parent.name)
            result.append({**{k:p.get(k) for k in ('id','title','status','progress')},
                           'clip_count':len(p.get('candidates',[])), 'duration':p.get('media',{}).get('duration')})
        except (ValueError, OSError):
            continue
    return result


@app.post('/api/projects/url')
def from_url(data: URLInput):
    try:
        url = normalize_url(data.url)
    except ValueError as exc:
        raise HTTPException(400,str(exc))
    p = create(data.settings, 'YouTube video', url)
    submit(p['id'], process)
    return p


@app.post('/api/projects/upload')
async def upload(file: UploadFile = File(...), settings: str = Form(...)):
    try:
        options = Settings.model_validate_json(settings)
    except ValueError:
        raise HTTPException(400, 'Invalid clip settings. Check minimum and maximum lengths.')
    p = create(options, Path(file.filename or 'Local video').name)
    target = storage.folder(p['id'])/'source'/'video.bin'
    try:
        with target.open('wb') as output:
            while chunk := await file.read(1024*1024):
                if shutil.disk_usage(target.parent).free < len(chunk) + 512*1024**2:
                    raise HTTPException(400, 'Insufficient disk space for this upload.')
                output.write(chunk)
        p['source_path'] = str(target)
        storage.save(p)
        submit(p['id'], process)
    except Exception:
        target.unlink(missing_ok=True)
        p.update(status='error', error='Upload failed. Check disk space and try again.')
        storage.save(p)
        raise
    finally:
        await file.close()
    return p


@app.get('/api/projects/{pid}')
def project(pid: str):
    return get_project(pid)


@app.post('/api/projects/{pid}/delete')
@app.delete('/api/projects/{pid}')
def delete_project(pid: str):
    with storage.LOCK:
        if pid in jobs:
            raise HTTPException(409, 'Cannot delete a project that is currently processing.')
        folder = storage.folder(pid)
        if not folder.exists():
            raise HTTPException(404, 'Project not found.')
        import time
        for attempt in range(5):
            try:
                shutil.rmtree(folder, ignore_errors=False)
                break
            except Exception:
                time.sleep(0.08)
                if attempt == 4:
                    shutil.rmtree(folder, ignore_errors=True)
        return {'status': 'deleted', 'id': pid}


class RenameInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)


@app.post('/api/projects/{pid}/rename')
def rename_project(pid: str, data: RenameInput):
    with storage.LOCK:
        p = get_project(pid)
        p['title'] = data.title.strip()
        storage.save(p)
        return p


@app.post('/api/projects/{pid}/retry')
def retry(pid: str):
    with storage.LOCK:
        p = get_project(pid)
        if pid in jobs:
            raise HTTPException(409, 'This project is already processing.')
        p.pop('error', None)
        storage.save(p)
        submit(pid, process)
        return storage.load(pid)


class AnalysisOptions(BaseModel):
    use_public_benchmarks: bool = True
    content_profile: Literal['auto','streamer','gaming','education','podcast','story'] = 'auto'
    num_clips: int = Field(default=10, ge=1, le=50)
    min_length: float = Field(default=20, ge=3, le=180)
    max_length: float = Field(default=60, ge=3, le=180)
    summarize_mode: bool = False


@app.post('/api/projects/{pid}/analyze')
def reanalyze(pid: str, data: AnalysisOptions):
    with storage.LOCK:
        p = get_project(pid)
        if pid in jobs:
            raise HTTPException(409,'Wait for the current job to finish.')
        if data.min_length > data.max_length:
            raise HTTPException(400,'Minimum length must not exceed maximum length.')
        p['settings'].update(data.model_dump())
        p.pop('error',None)
        storage.save(p)
        submit(pid, process)
        return storage.load(pid)


@app.get('/api/projects/{pid}/source')
def source(pid: str):
    p = get_project(pid)
    if not p.get('source_path'):
        raise HTTPException(404, 'Source is not ready.')
    if not Path(p['source_path']).is_file():
        raise HTTPException(404,'The source file is missing. Import the video again.')
    container = p.get('media',{}).get('format','')
    return FileResponse(p['source_path'], media_type='video/webm' if 'webm' in container else 'video/mp4')


class ClipEdit(BaseModel):
    start: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    end: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    captions: bool | None = None
    selected: bool | None = None
    title: str | None = Field(default=None, min_length=1, max_length=160)
    hook: str | None = Field(default=None, max_length=500)
    layout: Literal['crop','blur'] | None = None
    crop_x: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    caption_position: Literal['lower','middle','upper'] | None = None
    caption_color: Literal['yellow','mint','green','cyan','gold','red','magenta','orange','white'] | None = None
    caption_style: Literal['hormozi','beast','neon','boxed','minimal','classic'] | None = None
    caption_bounce: bool | None = None
    caption_chunk_size: Literal['single','phrase'] | None = None
    caption_font: str | None = None
    caption_offset_y: float | None = None
    caption_size: int | None = None
    caption_uppercase: bool | None = None
    resolution: Literal['720p','1080p','4k'] | None = None
    ratio: Literal['9:16', '16:9', '1:1'] | None = None
    export_srt: bool | None = None
    export_dir: str | None = None
    face_tracking: bool | None = None
    teaser_enabled: bool | None = None
    teaser_start: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    teaser_end: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    teaser_text: str | None = Field(default=None, max_length=500)
    teaser_badge: str | None = Field(default=None, max_length=100)
    cliffhanger_cut: bool | None = None


class CreateClipInput(BaseModel):
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    title: str | None = None


@app.post('/api/projects/{pid}/clips')
def add_clip(pid: str, data: CreateClipInput):
    with storage.LOCK:
        p = get_project(pid)
        if pid in jobs or p['status'] != 'ready':
            raise HTTPException(409, 'Wait for processing to finish before adding clips.')
        if not 3 <= data.end - data.start <= 180 or data.end > p['media']['duration']:
            raise HTTPException(400, 'Choose a range within the video, between 3 and 180 seconds.')
        from backend.services.clip_analysis import clip_text, keywords
        transcript_path = storage.folder(pid) / 'transcript' / 'transcript.json'
        transcript_text = ''
        tags = []
        if transcript_path.is_file():
            try:
                t_data = json.loads(transcript_path.read_text(encoding='utf-8'))
                transcript_text = clip_text(t_data, data.start, data.end)
                tags = keywords(transcript_text)
            except Exception:
                pass
        existing_ids = [int(c['id']) for c in p['candidates'] if str(c.get('id','')).isdigit()]
        new_id = str(max(existing_ids or [0]) + 1)
        new_clip = {
            'id': new_id,
            'start': round(data.start, 3),
            'end': round(data.end, 3),
            'duration': round(data.end - data.start, 3),
            'score': 80,
            'reason': 'Custom clip created manually in editor',
            'score_breakdown': {'Manual clip': 80},
            'cautions': [],
            'title': (data.title or f'Clip {new_id}').strip(),
            'hook': transcript_text[:120] if transcript_text else '',
            'tags': tags,
            'transcript': transcript_text,
            'selected': True,
            'captions': p['settings'].get('captions', True),
            'layout': p['settings'].get('layout', 'crop'),
            'crop_x': 50,
            'face_tracking': True,
            'caption_position': 'lower',
            'caption_color': 'yellow',
            'caption_uppercase': False,
            'render_status': 'pending',
            'analysis_version': 2
        }
        p['candidates'].append(new_clip)
        storage.save(p)
        return p


@app.post('/api/projects/{pid}/clips/{cid}/delete')
@app.delete('/api/projects/{pid}/clips/{cid}')
def delete_clip(pid: str, cid: str):
    with storage.LOCK:
        p = get_project(pid)
        if pid in jobs or p['status'] != 'ready':
            raise HTTPException(409, 'Wait for processing to finish before deleting clips.')
        initial_len = len(p['candidates'])
        p['candidates'] = [c for c in p['candidates'] if c['id'] != cid]
        if len(p['candidates']) == initial_len:
            raise HTTPException(404, 'Clip not found.')
        storage.save(p)
        return p


@app.post('/api/projects/{pid}/clips/{cid}')
def edit_clip(pid: str, cid: str, data: ClipEdit):
    with storage.LOCK:
        p = get_project(pid)
        if pid in jobs or p['status'] != 'ready':
            raise HTTPException(409, 'Wait for processing to finish before editing.')
        c = next((c for c in p['candidates'] if c['id']==cid), None)
        if c is None:
            raise HTTPException(404, 'Clip not found.')
        changes = data.model_dump(exclude_unset=True, exclude_none=True)
        if 'title' in changes:
            changes['title'] = changes['title'].strip()
            if not changes['title']:
                raise HTTPException(400,'Give the clip a title.')
        start, end = changes.get('start',c['start']), changes.get('end',c['end'])
        if not 3 <= end-start <= 180 or end > p['media']['duration']:
            raise HTTPException(400, 'Choose a range within the video, between 3 and 180 seconds.')
        if changes.get('teaser_enabled'):
            t_s = changes.get('teaser_start', c.get('teaser_start', 0.0))
            t_e = changes.get('teaser_end', c.get('teaser_end', 0.0))
            if t_s is not None and t_e is not None and t_e > 0:
                if t_s >= t_e or t_e > p['media']['duration']:
                    raise HTTPException(400, 'Teaser hook range must be valid and within video duration.')
        defaults = dict(
            layout='crop', crop_x=50, caption_position='lower', caption_color='yellow',
            caption_uppercase=False, face_tracking=True, ratio='9:16', resolution='1080p',
            caption_style='hormozi', caption_bounce=True, caption_chunk_size='phrase',
            teaser_enabled=False, teaser_start=0.0, teaser_end=0.0, teaser_text='',
            teaser_badge='⚡ WAIT FOR IT...', cliffhanger_cut=False
        )
        changed = any(c.get(k, defaults.get(k)) != changes[k] for k in (
            'start', 'end', 'captions', 'layout', 'crop_x', 'caption_position',
            'caption_color', 'caption_uppercase', 'face_tracking', 'ratio', 'resolution',
            'caption_style', 'caption_bounce', 'caption_chunk_size', 'caption_font',
            'caption_offset_y', 'caption_size', 'teaser_enabled', 'teaser_start',
            'teaser_end', 'teaser_text', 'teaser_badge', 'cliffhanger_cut'
        ) if k in changes)
        c.update(changes,duration=round(end-start,3))
        if changed:
            from backend.services.clip_analysis import clip_text
            transcript = json.loads((storage.folder(pid)/'transcript'/'transcript.json').read_text(encoding='utf-8'))
            c['transcript'] = clip_text(transcript,start,end)
            c['edited'] = True
            c.pop('file',None)
            c.pop('render_error',None)
            c['render_status']='pending'
        elif c.get('file'):
            from backend.services.renderer import write_metadata
            write_metadata(p,c,storage.folder(pid)/'exports'/c['file'])
        storage.save(p)
        return p


@app.post('/api/projects/{pid}/clips/{cid}/detect-teaser')
def detect_clip_teaser(pid: str, cid: str):
    with storage.LOCK:
        p = get_project(pid)
        c = next((c for c in p['candidates'] if c['id'] == cid), None)
        if not c:
            raise HTTPException(404, 'Clip not found.')
        transcript_path = storage.folder(pid) / 'transcript' / 'transcript.json'
        if not transcript_path.is_file():
            raise HTTPException(400, 'Transcript not available.')
        t_data = json.loads(transcript_path.read_text(encoding='utf-8'))
        signals_file = storage.folder(pid) / 'analysis' / 'signals.json'
        audio_energy = {}
        if signals_file.is_file():
            try:
                sig = json.loads(signals_file.read_text(encoding='utf-8'))
                audio_energy = sig.get('audio_energy', {})
            except Exception:
                pass
        from backend.services.clip_analysis import detect_teaser_hook
        passage = [
            w for seg in t_data.get('segments', [])
            for w in seg.get('words', [])
            if c['start'] <= w.get('start', 0) <= c['end']
        ]
        total_dur = p.get('media', {}).get('duration', 0)
        teaser_info = detect_teaser_hook(passage, audio_energy, total_dur)
        if teaser_info:
            c.update(teaser_info)
            c['teaser_enabled'] = True
            c['edited'] = True
            c.pop('file', None)
            c.pop('render_error', None)
            c['render_status'] = 'pending'
            storage.save(p)
            return {'clip': c, 'teaser': teaser_info}
        else:
            return {'clip': c, 'teaser': None, 'message': 'No punchy reaction found in clip passage.'}


class RenderInput(BaseModel):
    ids: list[str] | None = None
    ratio: Literal['9:16', '16:9', '1:1'] | None = None
    resolution: Literal['720p', '1080p', '4k'] | None = None
    captions: bool | None = None
    export_srt: bool | None = None
    export_dir: str | None = None
    face_tracking: bool | None = None


@app.post('/api/projects/{pid}/render')
def render(pid: str, data: RenderInput | None = None):
    from backend.services.renderer import render_project
    with storage.LOCK:
        p = get_project(pid)
        if p['status'] != 'ready' or pid in jobs:
            raise HTTPException(409, 'Wait for analysis or rendering to finish.')
        ids = data.ids if data else None
        ratio = data.ratio if data else None
        resolution = data.resolution if data else None
        captions = data.captions if data else None
        export_srt = data.export_srt if data else None
        export_dir = data.export_dir.strip() if (data and data.export_dir and data.export_dir.strip()) else None
        face_tracking = data.face_tracking if data else None

        if ids is not None and any(cid not in {c['id'] for c in p['candidates']} for cid in ids):
            raise HTTPException(400, 'A requested clip does not exist.')
        chosen = [c for c in p['candidates'] if c['id'] in ids] if ids is not None else [c for c in p['candidates'] if c['selected']]
        if not chosen:
            raise HTTPException(400, 'Select at least one clip to export.')
        submit(pid, lambda project_id: render_project(project_id, ids, ratio=ratio, export_dir=export_dir, resolution=resolution, captions=captions, export_srt=export_srt, face_tracking=face_tracking), kind='render')
        return storage.load(pid)


@app.get('/api/projects/{pid}/clips/{cid}/srt')
def clip_srt(pid: str, cid: str):
    p = get_project(pid)
    c = next((c for c in p['candidates'] if c['id'] == cid), None)
    if not c:
        raise HTTPException(404, 'Clip not found.')
    base = storage.folder(pid)
    srt_path = None
    if c.get('srt_file'):
        candidate = base / 'exports' / c['srt_file']
        if candidate.is_file():
            srt_path = candidate
    if not srt_path and c.get('file'):
        candidate = (base / 'exports' / c['file']).with_suffix('.srt')
        if candidate.is_file():
            srt_path = candidate
    if not srt_path:
        transcript_path = base / 'transcript' / 'transcript.json'
        if transcript_path.is_file():
            from backend.services.subtitles import make_clip_srt
            t_data = json.loads(transcript_path.read_text(encoding='utf-8'))
            slug = re.sub(r'[^a-z0-9]+', '_', c['title'].lower()).strip('_')[:65] or 'moment'
            srt_name = f'{int(cid):02}_{slug}.srt'
            srt_path = base / 'exports' / srt_name
            make_clip_srt(t_data, c, srt_path)
    if not srt_path or not srt_path.is_file():
        raise HTTPException(404, 'Subtitle file not available.')
    return FileResponse(srt_path, media_type='application/x-subrip', filename=srt_path.name)


@app.get('/api/system-directories')
def system_directories():
    home = Path.home()
    return {
        'home': str(home),
        'videos': str(home / 'Videos') if (home / 'Videos').is_dir() else str(home),
        'downloads': str(home / 'Downloads') if (home / 'Downloads').is_dir() else str(home),
        'desktop': str(home / 'Desktop') if (home / 'Desktop').is_dir() else str(home),
    }


@app.get('/api/projects/{pid}/waveform')
def project_waveform(pid: str):
    p = get_project(pid)
    base = storage.folder(pid)
    signals_file = base / 'analysis' / 'signals.json'
    if signals_file.is_file():
        try:
            signals = json.loads(signals_file.read_text(encoding='utf-8'))
            if 'audio_energy' in signals and signals['audio_energy'].get('energies'):
                return signals['audio_energy']
        except Exception:
            pass
    audio_path = base / 'audio' / 'speech.wav'
    if audio_path.is_file():
        from backend.services.media import compute_audio_energy
        data = compute_audio_energy(audio_path)
        if data:
            return data
    return {'energies': [], 'window_sec': 0.5}


class OpenFolderInput(BaseModel):
    path: str | None = None


@app.post('/api/projects/{pid}/open-folder')
def open_folder(pid: str, data: OpenFolderInput | None = None):
    p = get_project(pid)
    base = storage.folder(pid)
    target = None
    if data and data.path:
        p_path = Path(data.path)
        if p_path.is_dir():
            target = p_path
    if not target:
        last_dir = p.get('export_dir')
        if last_dir and Path(last_dir).is_dir():
            target = Path(last_dir)
        else:
            target = base / 'exports'
    target.mkdir(parents=True, exist_ok=True)
    if os.name == 'nt':
        import subprocess
        subprocess.Popen(['explorer', str(target)])
    return {'status': 'opened', 'folder': str(target)}


@app.get('/api/projects/{pid}/thumbnail/{cid}')
def thumbnail(pid: str, cid: str):
    from backend.services.media import run
    p = get_project(pid)
    clip = next((c for c in p['candidates'] if c['id']==cid),None)
    if not clip or not p.get('source_path'):
        raise HTTPException(404,'Thumbnail not available.')
    target = storage.folder(pid)/'clips'/f'thumb_{int(cid)}_{round(clip["start"]*1000)}.jpg'
    with thumbnail_lock:
        if not target.exists():
            run(['ffmpeg','-y','-loglevel','error','-ss',str(clip['start']+.5),'-i',p['source_path'],
                 '-frames:v','1','-vf','scale=320:-2','-update','1',str(target)])
    return FileResponse(target,media_type='image/jpeg')


class SelectionInput(BaseModel):
    ids: list[str]


@app.post('/api/projects/{pid}/selection')
def select_clips(pid: str, data: SelectionInput):
    with storage.LOCK:
        p = get_project(pid)
        if pid in jobs or p['status'] != 'ready':
            raise HTTPException(409,'Wait for processing to finish before changing the selection.')
        valid = {c['id'] for c in p['candidates']}
        if any(cid not in valid for cid in data.ids):
            raise HTTPException(400,'A requested clip does not exist.')
        for c in p['candidates']:
            c['selected'] = c['id'] in data.ids
        storage.save(p)
        return p


@app.get('/api/projects/{pid}/transcript')
def transcript_download(pid: str, format: Literal['json','srt'] = 'json'):
    get_project(pid)
    target = storage.folder(pid)/'transcript'/f'transcript.{format}'
    if not target.is_file():
        raise HTTPException(404,'The transcript is not ready yet.')
    return FileResponse(target,media_type='application/json' if format == 'json' else 'application/x-subrip',filename=target.name)


@app.get('/api/projects/{pid}/bundle')
def bundle(pid: str):
    p = get_project(pid)
    chosen = [c for c in p['candidates'] if c.get('selected') and c.get('file') and c.get('render_status')=='ready']
    if not chosen:
        raise HTTPException(400,'Render at least one selected clip first.')
    base = storage.folder(pid)/'exports'
    files = [base/c['file'] for c in chosen]
    if not all(path.is_file() for path in files):
        raise HTTPException(404,'An export file is missing. Regenerate the affected clip.')
    if shutil.disk_usage(base).free < sum(path.stat().st_size for path in files)+128*1024**2:
        raise HTTPException(400,'Not enough disk space to package the clips. Download them individually.')
    with tempfile.NamedTemporaryFile(prefix='download_',suffix='.zip',dir=base,delete=False) as temp:
        target = Path(temp.name)
    try:
        with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_STORED) as archive:
            for path in files:
                archive.write(path,path.name)
                if path.with_suffix('.json').exists():
                    archive.write(path.with_suffix('.json'),path.with_suffix('.json').name)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return FileResponse(target,media_type='application/zip',filename=f'localcut_{pid[:8]}.zip',
                        background=BackgroundTask(target.unlink,missing_ok=True))


@app.get('/api/projects/{pid}/files/{name}')
def exported(pid: str, name: str, download: bool = False):
    p = get_project(pid)
    if not any(c.get('file')==name for c in p['candidates']):
        raise HTTPException(404, 'Export not found.')
    target = storage.folder(pid)/'exports'/name
    if not target.is_file():
        raise HTTPException(404, 'Export file is missing. Regenerate the clip.')
    return FileResponse(target, media_type='video/mp4', filename=name if download else None)


@app.get('/api/projects/{pid}/clips/{cid}/social')
def clip_social_post(pid: str, cid: str):
    p = get_project(pid)
    c = next((c for c in p['candidates'] if c['id'] == cid), None)
    if not c:
        raise HTTPException(404, 'Clip not found.')
    from backend.services.social_generator import build_social_post
    post_data = build_social_post(c, project_title=p.get('title', ''))
    if c.get('file'):
        post_data['export_video_path'] = str(storage.folder(pid) / 'exports' / c['file'])
    return post_data


@app.get('/api/subtitle-presets')
def subtitle_presets():
    from backend.services.subtitles import PRESETS, HIGHLIGHT_COLORS
    return {
        'presets': PRESETS,
        'colors': list(HIGHLIGHT_COLORS.keys()),
        'fonts': ['Impact', 'Arial Black', 'Montserrat', 'Segoe UI', 'JetBrains Mono', 'Rubik']
    }


dist = Path(__file__).resolve().parents[1] / 'frontend' / 'dist'
if dist.exists():
    app.mount('/', StaticFiles(directory=dist, html=True), name='frontend')
