import json
import logging
import re
import shutil
from pathlib import Path
from .media import render_with_progress, probe
from . import storage
from .reframing import video_filter, get_dimensions, SIZES
from .subtitles import make_ass, make_clip_srt


def write_metadata(project, clip, target):
    metadata = dict(
        original_source=project.get('url') or project['title'],
        **{k: clip.get(k) for k in ('start', 'end', 'duration', 'title', 'hook', 'score', 'transcript', 'tags',
                                    'score_breakdown', 'cautions', 'score_source', 'edited', 'audience')},
        format=project['settings']['ratio'], layout=clip.get('layout', 'crop'),
        crop_x=clip.get('crop_x', 50), captions=clip.get('captions', True),
        caption_position=clip.get('caption_position', 'lower'),
        caption_style=clip.get('caption_style', 'hormozi'),
        caption_bounce=clip.get('caption_bounce', True),
        caption_chunk_size=clip.get('caption_chunk_size', 'phrase'),
        caption_font=clip.get('caption_font'),
        caption_offset_y=clip.get('caption_offset_y'),
        caption_color=clip.get('caption_color', 'yellow'),
        caption_uppercase=clip.get('caption_uppercase', False),
        resolution=clip.get('resolution') or project['settings'].get('resolution', '1080p'),
        export_srt=clip.get('export_srt', True),
        face_tracking=clip.get('face_tracking', False)
    )
    target.with_suffix('.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding='utf-8')


def render_clip(project, clip, progress=None, export_dir=None, face_tracking=None, ratio=None):
    base = storage.folder(project['id'])
    slug = re.sub(r'[^a-z0-9]+', '_', clip['title'].lower()).strip('_')[:65] or 'moment'
    resolution = clip.get('resolution') or project['settings'].get('resolution', '1080p')
    ratio = ratio or clip.get('ratio') or project['settings'].get('ratio', '9:16')
    layout = clip.get('layout', 'crop')
    crop_x = clip.get('crop_x', 50)
    use_face_tracking = face_tracking if face_tracking is not None else clip.get('face_tracking', False)

    name = f'{int(clip["id"]):02}_{slug}.mp4'
    target = base / 'exports' / name
    version = 2
    while target.exists():
        name = f'{int(clip["id"]):02}_{slug}_v{version}.mp4'
        target = base / 'exports' / name
        version += 1
    temporary = target.with_name(target.stem + '.rendering.mp4')

    if use_face_tracking and layout != 'blur':
        try:
            from .face_tracker import track_clip_faces, build_face_tracking_filter
            keyframes = track_clip_faces(project['source_path'], clip['start'], clip['end'], default_crop_x=crop_x)
            filters = build_face_tracking_filter(keyframes, ratio=ratio, layout=layout, resolution=resolution, default_crop_x=crop_x)
            clip['face_tracking'] = True
        except Exception as e:
            logging.warning("Face tracking failed, falling back to static framing: %s", e)
            filters = video_filter(ratio, layout, crop_x, resolution=resolution)
            clip['face_tracking'] = False
    else:
        filters = video_filter(ratio, layout, crop_x, resolution=resolution)
        clip['face_tracking'] = False

    transcript_path = base / 'transcript' / 'transcript.json'
    t_data = None
    if transcript_path.is_file():
        try:
            t_data = json.loads(transcript_path.read_text(encoding='utf-8'))
        except Exception:
            pass

    width, height = get_dimensions(ratio, resolution)

    # Burn-in subtitles if captions is True
    if clip.get('captions') and t_data:
        subtitle_path = base / 'clips' / f'{clip["id"]}.ass'
        make_ass(t_data, clip, subtitle_path, width, height)
        # Relative filename avoids Windows drive-colon escaping inside filters.
        filters += f",ass=../clips/{clip['id']}.ass"

    # Standalone SRT file whenever requested or when rendering without burned-in captions
    srt_file_name = target.with_suffix('.srt').name
    srt_target = base / 'exports' / srt_file_name
    if t_data and (not clip.get('captions') or clip.get('export_srt', True)):
        make_clip_srt(t_data, clip, srt_target)
        clip['srt_file'] = srt_file_name

    try:
        render_with_progress(['ffmpeg', '-y', '-ss', str(clip['start']), '-i', project['source_path'],
                              '-t', str(clip['end'] - clip['start']), '-filter_complex_threads', '2',
                              '-filter_complex', filters + '[out]', '-map', '[out]', '-map', '0:a:0',
                              '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11',
                              '-c:v', 'libx264', '-threads', '4', '-preset', 'veryfast', '-crf', '21',
                              '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', str(temporary)],
                             clip['end'] - clip['start'], progress, cwd=base / 'exports')
        media = probe(temporary)
        if abs(media['duration'] - (clip['end'] - clip['start'])) > 0.3:
            raise RuntimeError('The rendered duration did not match the chosen timestamps.')
        temporary.replace(target)
        write_metadata(project, clip, target)

        # Copy to custom destination folder if specified
        dest_dir = export_dir or clip.get('export_dir') or project.get('export_dir')
        if dest_dir:
            try:
                dest_path = Path(dest_dir)
                dest_path.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, dest_path / target.name)
                if srt_target.is_file():
                    shutil.copy2(srt_target, dest_path / srt_target.name)
                json_meta = target.with_suffix('.json')
                if json_meta.is_file():
                    shutil.copy2(json_meta, dest_path / json_meta.name)
                clip['exported_path'] = str(dest_path / target.name)
            except Exception as e:
                logging.warning("Failed to copy export to %s: %s", dest_dir, e)

        return name
    finally:
        temporary.unlink(missing_ok=True)


def render_project(pid, ids=None, ratio=None, export_dir=None, resolution=None, captions=None, export_srt=None, face_tracking=None):
    project = storage.load(pid)
    if export_dir:
        project['export_dir'] = export_dir

    chosen = [c for c in project['candidates'] if c['id'] in ids] if ids is not None else [c for c in project['candidates'] if c['selected']]

    for c in chosen:
        if ratio:
            c['ratio'] = ratio
        if resolution:
            c['resolution'] = resolution
        if captions is not None:
            c['captions'] = captions
        if export_srt is not None:
            c['export_srt'] = export_srt
        if export_dir:
            c['export_dir'] = export_dir
        if face_tracking is not None:
            c['face_tracking'] = face_tracking

    project.pop('warning', None)
    project.update(status='rendering', progress=0)
    storage.save(project)

    for index, clip in enumerate(chosen):
        clip['render_status'] = 'rendering'
        storage.save(project)
        try:
            def progress(fraction):
                project.update(progress=round((index + fraction) / len(chosen) * 100),
                               detail=f'Rendering clip {index + 1} of {len(chosen)} · {round(fraction * 100)}%')
                storage.save(project)
            clip['file'] = render_clip(project, clip, progress, export_dir=export_dir, face_tracking=face_tracking, ratio=ratio)
            clip['render_status'] = 'ready'
            clip.pop('render_error', None)
        except Exception as exc:
            clip.update(render_status='error', render_error=str(exc))
        project['progress'] = int((index + 1) / len(chosen) * 100)
        storage.save(project)

    project.update(status='ready', progress=100)
    failures = sum(c['render_status'] == 'error' for c in chosen)
    project['detail'] = f'{len(chosen) - failures} of {len(chosen)} clips exported'
    if failures:
        project['warning'] = f'{failures} clip(s) could not render. Open the marked clips to see the error and retry.'
    storage.save(project)
