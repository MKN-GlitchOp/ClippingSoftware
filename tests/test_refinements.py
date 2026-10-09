import io
import json
import shutil
import time
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from backend.main import app, create, Settings
from backend.services import storage, pipeline
from backend.services.clip_analysis import analyze, speech_units
from backend.services.downloader import normalize_url, friendly_error
from backend.services.renderer import render_clip
from backend.services.media import probe, run

WORKSPACE = Path(__file__).resolve().parents[1]
EXAMPLE = WORKSPACE/'projects'/'69ba906302a84f838de887f408683b14'
if not EXAMPLE.exists() and (WORKSPACE/'tests'/'live_project.txt').exists():
    EXAMPLE = WORKSPACE/'projects'/(WORKSPACE/'tests'/'live_project.txt').read_text().strip()


def test_words_across_segment_boundary_remain_one_sentence():
    transcript = {'segments': [
        {'start': 0, 'end': 4, 'text': 'The trick is', 'words': [dict(word='The',start=0,end=1),dict(word='trick',start=1,end=2),dict(word='is',start=2,end=4)]},
        {'start': 4, 'end': 8, 'text': 'to start small.', 'words': [dict(word='to',start=4,end=5),dict(word='start',start=5,end=6),dict(word='small.',start=6,end=8)]},
    ]}
    units = speech_units(transcript)
    assert len(units) == 1
    assert units[0]['text'] == 'The trick is to start small.'
    assert units[0]['end'] == 8


def test_topic_transition_does_not_join_two_different_sections():
    transcript = {'segments': [
        dict(start=0,end=3,text='We learn to listen.'),
        dict(start=3,end=24,text='The secret is to let the other person finish their thought before you start speaking. This makes conversations much clearer.'),
        dict(start=25,end=28,text='We learn to explain.'),
        dict(start=28,end=51,text='Here is why giving one clear example can help somebody understand your idea. The best advice is to use familiar words.'),
    ]}
    clips = analyze(transcript,dict(min_length=20,max_length=50,num_clips=2,captions=True),dict(scenes=[],silence=[]),52)
    assert len(clips) == 2
    # A short lead-in handle may precede the next heading, but no clip joins both bodies.
    assert all(not (clip['start'] < 24 < 28 < clip['end']) for clip in clips)
    assert all(clip['score_breakdown'] for clip in clips)
    assert all(not (a['start'] < b['end'] and b['start'] < a['end']) for i,a in enumerate(clips) for b in clips[i+1:])


@pytest.mark.parametrize('url',[
    'https://www.youtube.com/watch?v=jNQXAC9IVRw&list=WL&t=13',
    'https://youtu.be/jNQXAC9IVRw?si=example',
    'https://www.youtube.com/shorts/jNQXAC9IVRw',
])
def test_single_video_links_are_normalized(url):
    assert normalize_url(url) == 'https://www.youtube.com/watch?v=jNQXAC9IVRw'


def test_download_error_is_actionable_without_terminal_codes():
    message = friendly_error('\x1b[0;31mERROR\x1b[0m HTTP Error 403: Forbidden')
    assert '\x1b' not in message and 'local copy' in message
    with pytest.raises(ValueError):
        normalize_url('https://www.youtube.com/playlist?list=123')


@pytest.fixture
def local_project(tmp_path, monkeypatch):
    if not (EXAMPLE/'source'/'video.mp4').exists():
        pytest.skip('Run the public-video smoke test to provide the local integration fixture.')
    root = tmp_path/'projects'
    root.mkdir()
    monkeypatch.setattr(storage,'ROOT',root)
    project = create(Settings(num_clips=1,min_length=3,max_length=19,model='tiny'),'Refinement check')
    base = storage.folder(project['id'])
    for filename in ('transcript.json','transcript.srt'):
        shutil.copyfile(EXAMPLE/'transcript'/filename,base/'transcript'/filename)
    shutil.copyfile(EXAMPLE/'analysis'/'signals.json',base/'analysis'/'signals.json')
    project.update(source_path=str(EXAMPLE/'source'/'video.mp4'),media=probe(EXAMPLE/'source'/'video.mp4'),status='ready')
    transcript = json.loads((base/'transcript'/'transcript.json').read_text(encoding='utf-8'))
    clip = analyze(transcript,project['settings'],dict(scenes=[],silence=[]),project['media']['duration'])[0]
    clip.update(start=1.04,end=6.04,duration=5,layout='blur',caption_position='upper')
    project['candidates']=[clip]
    storage.save(project)
    return project


def test_blur_upper_captions_export_metadata_and_bundle(local_project):
    p = local_project
    c = p['candidates'][0]
    progress=[]
    name = render_clip(p,c,progress.append)
    target = storage.folder(p['id'])/'exports'/name
    media = probe(target)
    assert (media['width'],media['height'],media['video_codec']) == (1080,1920,'h264')
    assert abs(media['duration']-5)<.2
    run(['ffmpeg','-v','error','-i',str(target),'-f','null','-'])
    assert progress[-1] == 1 and any(0 <= value < 1 for value in progress)
    ass = (storage.folder(p['id'])/'clips'/'1.ass').read_text(encoding='utf-8-sig')
    fields = next(line for line in ass.splitlines() if line.startswith('Format: Name')).split(':',1)[1].split(',')
    values = next(line for line in ass.splitlines() if line.startswith('Style:')).split(':',1)[1].split(',')
    style = dict(zip((field.strip() for field in fields), values))
    assert style['Alignment'] == '8' and int(style['MarginV']) > 0
    c.update(file=name,render_status='ready')
    storage.save(p)
    with TestClient(app) as client:
        endpoint = f'/api/projects/{p["id"]}'
        changed = client.post(endpoint+'/clips/1',json={'title':'A better title'}).json()['candidates'][0]
        assert changed['file'] == name and changed['render_status'] == 'ready'
        assert json.loads(target.with_suffix('.json').read_text())['title'] == 'A better title'
        selected = client.post(endpoint+'/clips/1',json={'selected':False}).json()['candidates'][0]
        assert selected['start']==1.04 and selected['captions'] and selected['layout']=='blur'
        assert client.post(endpoint+'/render',json={'ids':[]}).status_code == 400
        assert client.get(endpoint+'/bundle').status_code == 400
        assert client.post(endpoint+'/selection',json={'ids':['1']}).status_code == 200
        response = client.get(endpoint+'/bundle')
        assert response.status_code == 200
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            assert {name,target.with_suffix('.json').name}.issubset(set(archive.namelist()))
        assert not list(target.parent.glob('download_*.zip'))
        assert client.get(endpoint+'/thumbnail/1').content.startswith(b'\xff\xd8')
        assert '-->' in client.get(endpoint+'/transcript?format=srt').text
        assert client.post(endpoint+'/clips/1',json={'crop_x':101}).status_code == 422
        assert client.post(endpoint+'/clips/1',json={'title':'   '}).status_code == 400
        changed = client.post(endpoint+'/clips/1',json={'layout':'crop','crop_x':80,'caption_position':'lower'}).json()['candidates'][0]
        assert 'file' not in changed and changed['render_status']=='pending'


def test_retry_reuses_completed_work(local_project, monkeypatch):
    p=local_project
    (storage.folder(p['id'])/'audio'/'speech.wav').write_bytes(b'previously extracted audio')
    def unexpected(*args,**kwargs):
        raise AssertionError('A completed processing stage was repeated')
    for function in ('download','transcribe','extract_audio','detect'):
        monkeypatch.setattr(pipeline,function,unexpected)
    pipeline.process(p['id'])
    result=storage.load(p['id'])
    assert result['status']=='ready',result.get('error')
    assert result['analysis_version']==4 and result['candidates']


def test_interrupted_render_recovers_without_losing_clips(local_project):
    p=local_project
    p.update(status='rendering',last_operation='render')
    p['candidates'][0]['render_status']='rendering'
    storage.save(p)
    with TestClient(app) as client:
        result=client.get('/api/projects/'+p['id']).json()
        assert result['status']=='ready'
        assert result['candidates'][0]['render_status']=='error'
        assert 'interrupted' in result['warning']
