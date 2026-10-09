"""Monthly discovery over public Shorts. Month means upload cohort, not monthly views."""
import logging
import re
from collections import defaultdict
from datetime import datetime, timezone
from statistics import median

from . import benchmarks as b
from .streamer import MOMENTS, public_moment
from .discovery import search_shorts

TOPICS = {
    'gaming': ('Gaming', r'\b(?:gaming|games?|minecraft|fortnite|roblox|gta|clutch|valorant|free fire|pubg)\b', 'top 5 gaming moments'),
    'animals': ('Animals & pets', r'\b(?:animals?|pets?|dogs?|cats?|wildlife|sharks?|snakes?|birds?)\b', 'top 5 animals'),
    'sports': ('Sports', r'\b(?:sports?|football|soccer|basketball|nba|goals?|athletes?|messi|ronaldo)\b', 'top 5 sports moments'),
    'entertainment': ('Movies & entertainment', r'\b(?:movies?|films?|anime|characters?|cartoons?|celebrities|songs?|singers?)\b', 'top 5 movies'),
    'tech': ('Tech & gadgets', r'\b(?:tech|gadgets?|phones?|iphone|android|apps?|robots?|inventions?)\b', 'top 5 gadgets'),
    'food': ('Food', r'\b(?:food|foods|meals?|recipes?|snacks?|burgers?|pizza|cooking|restaurants?)\b', 'top 5 foods'),
    'places': ('Places & facts', r'\b(?:places?|countries|cities|travel|facts?|space|planets?|mysteries|scariest)\b', 'top 5 amazing facts'),
}
RANKING = re.compile(r'\b(?:top\s*(?:\d{1,2}|five|ten|three)|rank(?:ing|ed|ings)?|(?:best|worst)\s*\d{1,2})\b', re.I)
TOP_FIVE = re.compile(r'\btop[\s-]*(?:5|five)\b|\branking\s*(?:the\s*)?(?:5|five)\b', re.I)


def month_bounds(month):
    if not re.fullmatch(r'\d{4}-\d{2}', month):
        raise ValueError('Choose a month in YYYY-MM format.')
    try:
        start = datetime.strptime(month, '%Y-%m').replace(tzinfo=timezone.utc)
        end = start.replace(year=start.year+1, month=1) if start.month == 12 else start.replace(month=start.month+1)
    except ValueError:
        raise ValueError('Choose a valid month.')
    if start > b.now():
        raise ValueError('Choose the current month or an earlier month.')
    return start, end


def classify(title):
    # Infer topic from the public title, never from our search query.
    for key, (_, pattern, _) in TOPICS.items():
        if re.search(pattern, title, re.I):
            return key
    return 'other'


def report(month, format='ranking', topic='all', sort='views', period='month', min_views=0):
    start, end = month_bounds(month)
    with b.connect() as db:
        rows = (db.execute('SELECT * FROM videos') if period=='all' else
                db.execute('SELECT * FROM videos WHERE upload_date>=? AND upload_date<?',
                           (start.strftime('%Y%m%d'),end.strftime('%Y%m%d')))).fetchall()
    videos=[]
    below_threshold=0
    for row in rows:
        item = dict(row)
        item.pop('terms')
        moment = public_moment(item['title'],item['channel']) if format=='streamer' else None
        if format=='streamer' and moment is None:
            continue
        item['topic'] = moment if format=='streamer' else classify(item['title'])
        item['format'] = 'top5' if TOP_FIVE.search(item['title']) else 'ranking' if RANKING.search(item['title']) else 'other'
        if format == 'ranking' and item['format'] == 'other' or format == 'top5' and item['format'] != 'top5':
            continue
        if topic != 'all' and item['topic'] != topic:
            continue
        if min_views and (item['views'] is None or item['views'] < min_views):
            below_threshold+=1
            continue
        collected = datetime.fromisoformat(item['collected_at'])
        uploaded = datetime.strptime(item['upload_date'],'%Y%m%d').replace(tzinfo=timezone.utc) if item['upload_date'] else None
        days = max(1, (collected-uploaded).total_seconds()/86400) if uploaded else None
        item['views_per_day'] = round(item['views']/days) if item['views'] is not None and days else None
        item['like_rate'] = round(100*item['likes']/item['views'],2) if item['likes'] is not None and item['views'] else None
        item['stale'] = (b.now()-collected).total_seconds() > 30*86400
        videos.append(item)
    metric = {'views':'views','pace':'views_per_day','likes':'likes'}[sort]
    videos.sort(key=lambda v: (-(v[metric] if v[metric] is not None else -1),v['id']))
    groups=defaultdict(list)
    for video in videos:
        groups[video['topic']].append(video)
    topics=[]
    for key, examples in groups.items():
        counted=[v for v in examples if v['views'] is not None]
        values=[v[metric] for v in examples if v[metric] is not None]
        channels={v['channel'] for v in examples if v['channel']}
        catalog = MOMENTS if format=='streamer' else TOPICS
        topic_label=catalog[key][0] if key in catalog else 'Other topics'
        topics.append(dict(id=key,label=topic_label,count=len(examples),channels=len(channels),
                           total_views=sum(v['views'] for v in counted),
                           median_views=round(median(v['views'] for v in counted)) if counted else None,
                           metric_median=round(median(values)) if values else None,
                           low_reach=max((v['views'] for v in counted),default=0)<1000,
                           evidence='Limited sample' if len(examples)<3 or len(channels)<2 else 'Multiple examples',
                           examples=examples[:3]))
    topics.sort(key=lambda t: (-(t['metric_median'] if t['metric_median'] is not None else -1), -t['count']))
    return dict(month=month,format=format,topic=topic,sort=sort,period=period,min_views=min_views,
                below_threshold=below_threshold,total=len(videos),
                total_views=sum(v['views'] for v in videos if v['views'] is not None),
                missing_views=sum(v['views'] is None for v in videos),
                stale_count=sum(v['stale'] for v in videos),
                latest_collection=max((v['collected_at'] for v in videos),default=None),
                topics=topics,videos=videos[:100],job=b.status(),
                topic_options=[dict(id=key,label=value[0]) for key,value in (MOMENTS if format=='streamer' else TOPICS).items()])


def scan(month, topic='all', format='ranking', period='month'):
    from yt_dlp import YoutubeDL
    start,end=month_bounds(month)
    # Use exact upload dates as the authority; search text is only discovery guidance.
    catalog = MOMENTS if format=='streamer' else TOPICS
    keys=list(catalog) if topic=='all' else [topic]
    saved=skipped=checked=0
    errors=[]
    seen=set()
    opts=dict(quiet=True,no_warnings=True,skip_download=True,noplaylist=True,
              socket_timeout=15,retries=1,extractor_retries=1,
              js_runtimes={'node':{}},remote_components=['ejs:github'])
    try:
        with YoutubeDL(opts) as detail:
            for key in keys:
                label,_,base_query=catalog[key]
                phrase=base_query if format!='all' else label+' shorts'
                query=phrase if period=='all' else f'{phrase} after:{start:%Y-%m-%d} before:{end:%Y-%m-%d}'
                b.update(message=f'Discovering {label.lower()} · '+('all upload dates' if period=='all' else month),scope='trends',month=month,period=period)
                try:
                    entries=search_shorts(query,opts)
                except Exception as exc:
                    logging.warning('Trend discovery failed: %s',type(exc).__name__)
                    errors.append(f'{label}: public search was unavailable.')
                    continue
                for entry in entries[:8 if format=='streamer' else 6]:
                    if entry['id'] in seen:
                        continue
                    seen.add(entry['id'])
                    b.update(message=f'Checking {label.lower()} · {checked+1} public videos')
                    try:
                        info=detail.extract_info('https://www.youtube.com/watch?v='+entry['id'],download=False)
                        record=b.make_record(info or {},query,'auto')
                        if record:
                            # Keep usable metadata for other months in the shared library too.
                            b.save_record(record)
                            matches = format!='streamer' or public_moment(record['title'],record['channel']) is not None
                            if matches and (period=='all' or record['upload_date'] and start.strftime('%Y%m%d') <= record['upload_date'] < end.strftime('%Y%m%d')):
                                saved+=1
                            else:
                                skipped+=1
                        else:
                            skipped+=1
                    except Exception as exc:
                        logging.warning('Trend example unavailable: %s',type(exc).__name__)
                        errors.append('A public video was unavailable; other results were kept.')
                    checked+=1
                    b.update(processed=checked,saved=saved,skipped=skipped,errors=errors[:3])
        scope='all upload dates' if period=='all' else month
        failed = bool(errors and not checked)
        b.update(status='error' if failed else 'done',errors=errors[:3],
                 message='Public search was unavailable. Saved examples are safe; try again later.' if failed else f'Scan complete: {saved} matching Shorts from {scope}; {checked} videos checked. Filters may show fewer results.',total=checked)
    except Exception:
        logging.exception('Monthly discovery failed')
        b.update(status='error',message='Monthly discovery stopped. Saved examples are safe; retry when your connection is available.')


def start_scan(month,topic='all',format='ranking',period='month'):
    month_bounds(month)
    with b.LOCK:
        if b.STATE['status']=='running':
            raise ValueError('A public-data collection is already running.')
        b.STATE.update(status='running',processed=0,total=0,saved=0,skipped=0,errors=[],
                       message='Starting public Shorts discovery…',scope='trends',month=month,period=period)
    b.EXECUTOR.submit(scan,month,topic,format,period)
    return b.status()
