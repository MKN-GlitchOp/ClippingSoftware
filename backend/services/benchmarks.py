"""Public short-video metadata cached locally. No private analytics or video downloads."""
import json
import logging
import math
import re
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .downloader import normalize_url, friendly_error
from .discovery import search_shorts

DB_PATH = Path(__file__).resolve().parents[2] / 'data' / 'public_shorts.sqlite3'
LOCK = threading.Lock()
EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix='public-shorts')
STATE = dict(status='idle', processed=0, total=0, saved=0, skipped=0, errors=[], message='')
STOP = set('the and for you your this that with from what when where how why are was were have has just they them their about into can will not but all its our shorts short youtube viral trending video videos funny best gaming game clip clips watch like subscribe really very more most'.split())
STOP.update('streamer streamers streaming stream twitch moment moments reaction reactions laughter haha bro chat'.split())


def now():
    return datetime.now(timezone.utc)


def _open_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=15)
    db.row_factory = sqlite3.Row
    db.executescript('''
      CREATE TABLE IF NOT EXISTS videos (
        id TEXT PRIMARY KEY, title TEXT NOT NULL, channel TEXT, url TEXT NOT NULL,
        duration REAL, width INTEGER, height INTEGER, upload_date TEXT,
        views INTEGER, likes INTEGER, comments INTEGER, collected_at TEXT NOT NULL,
        profile TEXT, terms TEXT NOT NULL, query TEXT, performance REAL NOT NULL);
      CREATE TABLE IF NOT EXISTS snapshots (
        video_id TEXT NOT NULL, day TEXT NOT NULL, collected_at TEXT NOT NULL,
        views INTEGER, likes INTEGER, comments INTEGER, PRIMARY KEY(video_id, day));
    ''')
    return db


@contextmanager
def connect():
    db = _open_connection()
    try:
        with db:
            yield db
    finally:
        db.close()


def terms(text):
    return set(w for w in re.findall(r'[a-z][a-z0-9]{2,}', text.lower()) if w not in STOP)


def count(value):
    if isinstance(value, (int, float)) and math.isfinite(value) and value >= 0:
        return int(value)
    return None


def make_record(info, query='', profile='auto', clock=None):
    stamp = clock or now()
    vid = str(info.get('id', ''))
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', vid) or info.get('is_live'):
        return None
    duration = info.get('duration')
    if not isinstance(duration, (int, float)) or not 3 <= duration <= 180:
        return None
    width, height = info.get('width'), info.get('height')
    if not width or not height:
        formats = [f for f in info.get('formats', []) if f.get('width') and f.get('height')]
        if formats:
            best = max(formats, key=lambda f: f['width']*f['height'])
            width, height = best['width'], best['height']
    # A /shorts/ URL alone does not prove the video is vertical. Reject unknown shape.
    if not width or not height or width > height:
        return None
    uploaded = info.get('upload_date')
    try:
        date = datetime.strptime(uploaded, '%Y%m%d').replace(tzinfo=timezone.utc)
        days = max(1, (stamp-date).total_seconds()/86400)
    except (ValueError, TypeError):
        uploaded, days = None, None
    views, likes, comments = (count(info.get(k)) for k in ('view_count', 'like_count', 'comment_count'))
    # Lifetime average, not recent velocity. Log scale limits domination by huge channels.
    pace = views/days if views is not None and days is not None else 0
    reach = min(80, max(0, math.log10(1+pace)*16))
    engagement = min(20, 400*likes/(views+1000)) if likes is not None and views else 0
    title = str(info.get('title') or 'Untitled')[:300]
    tags = ' '.join(str(t) for t in (info.get('tags') or [])[:30])
    return dict(id=vid, title=title, channel=str(info.get('channel') or info.get('uploader') or '')[:200],
                url='https://www.youtube.com/shorts/'+vid, duration=duration, width=width, height=height,
                upload_date=uploaded, views=views, likes=likes, comments=comments,
                collected_at=stamp.isoformat(), profile=profile,
                terms=json.dumps(sorted(terms(title+' '+tags))), query=query,
                performance=round(reach+engagement, 1))


def save_record(record):
    with connect() as db:
        columns = list(record)
        updates = ','.join(f'{k}=excluded.{k}' for k in columns if k != 'id')
        db.execute(f"INSERT INTO videos ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)}) ON CONFLICT(id) DO UPDATE SET {updates}", list(record.values()))
        db.execute('INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?,?,?)',
                   (record['id'],record['collected_at'][:10],record['collected_at'],record['views'],record['likes'],record['comments']))


def list_records(query='', limit=100):
    with connect() as db:
        rows = db.execute('SELECT * FROM videos ORDER BY performance DESC, views DESC').fetchall()
        result = []
        for row in rows:
            item = dict(row)
            if query and query.casefold() not in (item['title']+' '+item['query']+' '+item['channel']).casefold():
                continue
            item.pop('terms')
            age = (now()-datetime.fromisoformat(item['collected_at'])).total_seconds()/86400
            item['stale'] = age > 30
            try:
                days = max(1, (now()-datetime.strptime(item['upload_date'],'%Y%m%d').replace(tzinfo=timezone.utc)).total_seconds()/86400)
                item['lifetime_views_per_day'] = round(item['views']/days) if item['views'] is not None else None
            except (ValueError, TypeError):
                item['lifetime_views_per_day'] = None
            prior = db.execute('SELECT * FROM snapshots WHERE video_id=? AND day<? AND views IS NOT NULL ORDER BY day DESC LIMIT 1', (item['id'], item['collected_at'][:10])).fetchone()
            item['observed_views_per_day'] = None
            if prior and item['views'] is not None:
                elapsed = (datetime.fromisoformat(item['collected_at'])-datetime.fromisoformat(prior['collected_at'])).total_seconds()/86400
                if elapsed >= 1 and item['views'] >= prior['views']:
                    item['observed_views_per_day'] = round((item['views']-prior['views'])/elapsed)
            result.append(item)
            if len(result) >= limit:
                break
        total = db.execute('SELECT count(*) FROM videos').fetchone()[0]
    return dict(total=total, videos=result)


class BenchmarkIndex:
    """One immutable lookup per analysis; never send the source transcript online."""
    def __init__(self, rows, clock=None):
        self.rows = []
        self.index = {}
        stamp = clock or now()
        for raw in rows:
            row = dict(raw)
            if (stamp-datetime.fromisoformat(row['collected_at'])).total_seconds() > 30*86400:
                continue
            row['tokens'] = set(json.loads(row['terms']))
            row['title_tokens'] = terms(row['title'])
            self.rows.append(row)
            for token in row['tokens']:
                self.index.setdefault(token, []).append(len(self.rows)-1)

    def match(self, text, profile):
        tokens = terms(text)
        ids = set(i for token in tokens for i in self.index.get(token, []))
        matches = []
        for i in ids:
            row = self.rows[i]
            if row['profile'] not in ('auto', 'balanced', profile):
                continue
            shared = tokens & row['tokens']
            if len(shared) < 2 or row['views'] is None or row['views'] < 1000:
                continue
            title_shared = tokens & row['title_tokens']
            if not title_shared:
                continue
            # Long tag lists must not drown out a precise title match.
            relevance = .8*len(title_shared)/max(1, len(row['title_tokens'])) + .2*len(shared)/max(1, len(row['tokens']))
            if relevance < .2:
                continue
            bonus = min(6, round(6*relevance*row['performance']/100))
            if bonus < 1:
                continue
            matches.append(dict(id=row['id'], title=row['title'], url=row['url'], views=row['views'],
                                collected_at=row['collected_at'], matched_terms=sorted(shared), bonus=bonus))
        matches.sort(key=lambda r: (-r['bonus'], -r['views']))
        # Correlated examples never stack into an unbounded score advantage.
        return dict(bonus=matches[0]['bonus'] if matches else 0, examples=matches[:3])


def load_index():
    if not DB_PATH.exists():
        return BenchmarkIndex([])
    with connect() as db:
        return BenchmarkIndex(db.execute('SELECT * FROM videos').fetchall())


def status():
    with LOCK:
        return {**STATE, 'errors':list(STATE['errors'])}


def update(**values):
    with LOCK:
        STATE.update(values)


def collect(query, urls, profile, refresh=False):
    from yt_dlp import YoutubeDL
    options = dict(quiet=True, no_warnings=True, skip_download=True, noplaylist=True,
                   socket_timeout=15, retries=1, extractor_retries=1,
                   js_runtimes={'node': {}}, remote_components=['ejs:github'])
    saved, skipped, errors = 0, 0, []
    try:
        if refresh:
            with connect() as db:
                urls = [r[0] for r in db.execute('SELECT url FROM videos ORDER BY collected_at LIMIT 20')]
        elif not urls:
            update(message='Searching public YouTube metadata…')
            # ytsearch defaults to the Videos tab, which excludes many actual Shorts.
            # YouTube's Shorts filter is supported by yt-dlp's search-URL extractor.
            entries=search_shorts(query,options,limit=15)
            entries=[e for e in entries if not e.get('duration') or 3 <= e['duration'] <= 180]
            urls = ['https://www.youtube.com/watch?v='+e['id'] for e in entries[:10]]
        urls = list(dict.fromkeys(urls))[:20]
        update(total=len(urls))
        with YoutubeDL(options) as dl:
            for i, url in enumerate(urls):
                update(message=f'Reading public counts {i+1} of {len(urls)}')
                try:
                    info = dl.extract_info(normalize_url(url), download=False)
                    record = make_record(info or {}, query, profile)
                    if record:
                        if refresh:
                            with connect() as db:
                                old = db.execute('SELECT query,profile FROM videos WHERE id=?',(record['id'],)).fetchone()
                            if old:
                                record.update(query=old['query'], profile=old['profile'])
                        save_record(record)
                        saved += 1
                    else:
                        skipped += 1
                except Exception as exc:
                    logging.warning('Public metadata collection failed: %s', type(exc).__name__)
                    errors.append(friendly_error(exc))
                update(processed=i+1, saved=saved, skipped=skipped, errors=errors[:3])
        update(status='done',message=f'{saved} examples saved; {skipped} non-short or unverified formats skipped; {len(errors)} unavailable.' if saved else 'No examples saved. Try a specific topic or public Shorts links.')
    except Exception as exc:
        logging.exception('Public benchmark collection failed')
        update(status='error',message=friendly_error(exc))


def start_collection(query='', urls=None, profile='auto', refresh=False):
    urls = [normalize_url(url.strip()) for url in (urls or [])]
    if not refresh and not urls and len(query.strip()) < 3:
        raise ValueError('Enter a topic with at least 3 characters or a public Shorts link.')
    with LOCK:
        if STATE['status']=='running':
            raise ValueError('A public-data collection is already running.')
        STATE.update(status='running', processed=0,total=0,saved=0,skipped=0,errors=[],message='Starting public-data collection…',scope='library',month=None)
    EXECUTOR.submit(collect,query.strip(),urls,profile,refresh)
    return status()
