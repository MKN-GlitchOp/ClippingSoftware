"""Full offline local upload API flow using a previously downloaded test source."""
import json
import time
from unittest.mock import patch
from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import app
from backend.services import storage
from backend.services.media import probe, run


def wait(client,pid):
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        p=client.get('/api/projects/'+pid).json()
        if p['status'] in ('ready','error'):
            assert p['status']=='ready',p.get('error')
            return p
        time.sleep(.25)
    raise AssertionError('Processing timed out')


def main():
    sources = list(storage.ROOT.glob('*/source/video.mp4'))
    source_path = min(sources, key=lambda p:p.stat().st_size)
    with TestClient(app) as client:
        assert client.post('/api/projects/url',json={'url':'https://example.com/video'}).status_code==400
        assert client.post('/api/projects/url',headers={'Origin':'https://example.com'},json={'url':'https://youtu.be/x'}).status_code==403
        assert client.post('/api/projects/url',json={'url':'https://youtu.be/x','settings':{'min_length':60,'max_length':20}}).status_code==422
        with patch('backend.services.pipeline.improve_with_ollama',side_effect=ConnectionError('Ollama unavailable')):
            with source_path.open('rb') as source:
                r=client.post('/api/projects/upload',files={'file':('local-test.mp4',source,'video/mp4')},data={'settings':json.dumps(dict(num_clips=1,min_length=5,max_length=19,captions=True,ratio='9:16',model='tiny',ollama_model='test-unavailable'))})
            assert r.status_code==200,r.text
            pid=r.json()['id']
            p=wait(client,pid)
        assert 'Ollama' in p.get('warning','')
        c=p['candidates'][0]
        assert client.post(f'/api/projects/{pid}/clips/{c["id"]}',json={**c,'end':9999}).status_code==400
        # Editing invalidates prior render; captions-off must also work.
        r=client.post(f'/api/projects/{pid}/clips/{c["id"]}',json={**c,'start':max(0,c['start']-.2),'captions':False})
        assert r.status_code==200,r.text
        c=r.json()['candidates'][0]
        assert c['render_status']=='pending'
        assert client.post(f'/api/projects/{pid}/render',json={'ids':[c['id']]}).status_code==200
        p=wait(client,pid)
        c=p['candidates'][0]
        assert c['render_status']=='ready',c.get('render_error')
        target=storage.folder(pid)/'exports'/c['file']
        media=probe(target)
        assert media['width']==1080 and media['height']==1920
        assert abs(media['duration']-c['duration'])<.3
        run(['ffmpeg','-v','error','-i',str(target),'-f','null','-'])
        response=client.get(f'/api/projects/{pid}/files/{c["file"]}?download=true')
        assert response.status_code==200
        assert 'attachment' in response.headers['content-disposition']
        assert target.with_suffix('.json').exists()
        assert client.post(f'/api/projects/{pid}/render',json={'ids':[c['id']]}).status_code==200
        regenerated=wait(client,pid)['candidates'][0]
        assert regenerated['render_status']=='ready',regenerated.get('render_error')
        assert regenerated['file']!=c['file'] and target.exists()
        # Broken files receive a clear project error rather than crashing the API.
        r=client.post('/api/projects/upload',files={'file':('broken.mp4',b'not video','video/mp4')},data={'settings':'{}'})
        broken_id=r.json()['id']
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            broken=client.get('/api/projects/'+broken_id).json()
            if broken['status']=='error':break
            time.sleep(.1)
        assert broken['status']=='error'
        Path('tests/upload_project.txt').write_text(pid)
        print(json.dumps(dict(project=pid,export=str(target),media=media,checks='upload, full speech, edits, captions off, rendering, regeneration versions, download, metadata, Ollama fallback, invalid URL/range/file, foreign origin rejection'),indent=2))

if __name__=='__main__':main()
