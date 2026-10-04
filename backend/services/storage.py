import json
import threading
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / 'projects'
ROOT.mkdir(exist_ok=True)
LOCK = threading.RLock()


def folder(pid):
    import re
    if not re.fullmatch(r'[a-f0-9]{32}', pid):
        raise ValueError('Invalid project identifier.')
    return ROOT / pid


def save(project):
    with LOCK:
        target = folder(project['id']) / 'project.json'
        temporary = target.with_suffix('.'+uuid.uuid4().hex+'.tmp')
        temporary.write_text(json.dumps(project, indent=2, ensure_ascii=False), encoding='utf-8')
        try:
            for attempt in range(8):
                try:
                    temporary.replace(target)
                    break
                except PermissionError:
                    if attempt==7:
                        raise
                    time.sleep(.05*(attempt+1))
        finally:
            temporary.unlink(missing_ok=True)


def load(pid):
    with LOCK:
        return json.loads((folder(pid) / 'project.json').read_text(encoding='utf-8'))
