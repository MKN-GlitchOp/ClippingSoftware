import json
from pathlib import Path
from backend.services import storage
from backend.services.clip_analysis import analyze

pid=Path('tests/live_project.txt').read_text().strip()
p=storage.load(pid)
base=storage.folder(pid)
transcript=json.loads((base/'transcript'/'transcript.json').read_text(encoding='utf-8'))
signals=json.loads((base/'analysis'/'signals.json').read_text())
p['candidates']=analyze(transcript,p['settings'],signals,p['media']['duration'])
(base/'analysis'/'candidates.json').write_text(json.dumps(p['candidates'],indent=2),encoding='utf-8')
storage.save(p)
print(json.dumps([{k:c[k] for k in ('start','end','duration','score','title')} for c in p['candidates']],indent=2))
