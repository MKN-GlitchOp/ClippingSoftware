"""Real download and full transcription integration check; requires internet on first run."""
import json
import uuid
import argparse
from backend.services import storage
from backend.services.pipeline import process

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url',default='https://www.youtube.com/watch?v=jNQXAC9IVRw')
    parser.add_argument('--min',type=float,default=5)
    parser.add_argument('--max',type=float,default=19)
    parser.add_argument('--count',type=int,default=1)
    args = parser.parse_args()
    pid = uuid.uuid4().hex
    base = storage.folder(pid)
    for name in ('source','audio','transcript','analysis','clips','exports'):
        (base/name).mkdir(parents=True, exist_ok=True)
    project = dict(id=pid, url=args.url, title='Public YouTube smoke test', status='queued', progress=0, candidates=[], settings=dict(num_clips=args.count,min_length=args.min,max_length=args.max,captions=True,ratio='9:16',model='tiny',ollama_model=''))
    storage.save(project)
    process(pid)
    result = storage.load(pid)
    assert result['status'] == 'ready', result.get('error')
    assert result['candidates']
    for c in result['candidates']:
        assert 0 <= c['start'] < c['end'] <= result['media']['duration']
    Path = __import__('pathlib').Path
    Path('tests/live_project.txt').write_text(pid)
    print(json.dumps(dict(project=pid, media=result['media'], candidates=result['candidates']), indent=2))

if __name__ == '__main__':
    main()
