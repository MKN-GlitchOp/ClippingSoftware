import json
from pathlib import Path
from backend.services import storage
from backend.services.renderer import render_clip
from backend.services.media import probe, run

def main():
    pid = Path('tests/live_project.txt').read_text().strip()
    project = storage.load(pid)
    clip = project['candidates'][0]
    filename = render_clip(project, clip)
    target = storage.folder(pid)/'exports'/filename
    info = probe(target)
    run(['ffmpeg','-v','error','-i',str(target),'-f','null','-'])
    assert abs(info['duration']-clip['duration'])<.3
    assert info['width']==1080 and info['height']==1920
    clip.update(file=filename,render_status='ready')
    storage.save(project)
    print(json.dumps(dict(file=str(target),media=info),indent=2))

if __name__ == '__main__': main()
