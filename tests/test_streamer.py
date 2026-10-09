from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from backend.main import app, Settings, AnalysisOptions
from backend.services import benchmarks as b, trends as t
from backend.services.streamer import public_moment, refine_moment
from backend.services.clip_analysis import analyze


def unit(start,end,text):
    return dict(start=start,end=end,text=text,complete=True,confidence=.95)


def settings(**kw):
    return dict(min_length=10,max_length=25,num_clips=2,captions=True,content_profile='streamer',**kw)


def test_setup_reaction_beats_isolated_repeated_shouting():
    transcript={'segments':[
        unit(0,6,'Watch this, I bet you cannot open this trapped chest.'),
        unit(6,11,'You told me it was completely safe to open.'),
        unit(11,16,'No way! You got me, I fell for that prank!'),
        unit(40,46,'Bro bro bro! Chat chat chat!'),
        unit(46,56,'Bro bro bro! Chat chat chat!'),
    ]}
    clips=analyze(transcript,settings(),{},60)
    best=clips[0]
    assert best['start'] <= 6 and best['end'] >= 16
    assert best['audience']['moment']['setup']
    assert best['score']>clips[1]['score']
    assert all(10 <= c['duration'] <= 25 for c in clips)
    assert best['score_breakdown']['Setup before reaction']==12


def test_long_gap_never_stitches_unrelated_speech():
    transcript={'segments':[unit(0,8,'Watch this, this chest has a prank inside and you will laugh.'),
                            unit(30,38,'No way, this is a completely different scene from much later on.') ]}
    with pytest.raises(ValueError,match='No complete speech'):
        analyze(transcript,settings(),{},40)


def test_followup_reaction_is_preserved_and_tail_stays_within_next_speech():
    units=[unit(0,6,'Watch this, I have hidden something inside your new backpack.'),
           unit(6,12,'You got me! That was a really good prank.'),
           unit(12.2,15,'No way, I cannot believe that worked!'),
           unit(18,25,'Let us move along to the next topic for today.')]
    breakdown={}; cautions=[]
    refine_moment(units,0,1,breakdown,cautions)
    assert breakdown['Cuts before follow-up reaction']==-18
    clips=analyze({'segments':units},settings(),{},30)
    assert clips[0]['end']>=15 and clips[0]['end']<=18
    assert 'Cuts before follow-up reaction' not in clips[0]['score_breakdown']


def test_timing_pause_is_not_removed_or_scored_like_long_dead_air():
    transcript={'segments':[unit(0,8,'Watch this, I bet the next door has a surprise inside.'),
                            unit(9.5,15,'No way, you got me with that hilarious prank!')]}
    clip=analyze(transcript,settings(),{'silence':[[8,9.5]]},20)[0]
    assert clip['score_breakdown']['Comedic pause allowance']>0
    assert clip['start']<=0 and clip['end']>=15
    assert Settings(content_profile='streamer').content_profile=='streamer'
    assert AnalysisOptions(content_profile='streamer').content_profile=='streamer'


def test_streamer_classification_requires_identity_and_humor():
    assert public_moment('Stable Ronaldo Does NOT Listen! 😂')=='reactions'
    assert public_moment('Fanum Really Fell For It! 😂')=='banter'
    assert public_moment('Funny cats and dogs! 😂') is None
    assert public_moment('Top 5 football goals Ronaldo') is None
    assert public_moment('Kai Cenat buys a house') is None
    assert public_moment('Scared by a horror prank 😂','IShowSpeed')=='banter'
    assert not b.terms('bro chat streamer reactions funny moments')


@pytest.fixture
def database(tmp_path,monkeypatch):
    monkeypatch.setattr(b,'DB_PATH',tmp_path/'public.sqlite3')
    monkeypatch.setattr(b,'now',lambda:datetime(2026,10,9,tzinfo=timezone.utc))
    for id,title,views,date in [('streamer001','Kai Cenat funny reaction 😂',100000,'20260801'),
                               ('streamer002','Fanum fell for this prank 😂',15000,'20261001'),
                               ('streamer003','IShowSpeed hilarious fail',15,'20261002'),
                               ('notstream01','Funny cats 😂',5000000,'20261002')]:
        b.save_record(b.make_record(dict(id=id,title=title,view_count=views,duration=30,
                                        width=1080,height=1920,upload_date=date)))


def test_streamer_dashboard_scope_threshold_and_api_validation(database):
    all_dates=t.report('2026-10',format='streamer',period='all',min_views=1000)
    assert all_dates['total']==2 and all_dates['videos'][0]['views']==100000
    assert all_dates['below_threshold']==1
    monthly=t.report('2026-10',format='streamer',period='month',min_views=1000)
    assert monthly['total']==1 and monthly['videos'][0]['topic']=='banter'
    with TestClient(app) as client:
        assert client.get('/api/trends?month=2026-10&period=all&min_views=1000').json()['total']==2
        assert client.get('/api/trends?format=streamer&topic=animals').status_code==400
        assert client.post('/api/trends/scan',json={'month':'2026-10','format':'streamer','topic':'animals'}).status_code==400
        assert client.get('/api/trends?min_views=-1').status_code==422


def test_public_page_fallback_ignores_recommendations_and_deduplicates(monkeypatch):
    import json
    import yt_dlp
    from backend.services import discovery as d
    nested={'shortsLockupViewModel':{'onTap':{'innertubeCommand':{'reelWatchEndpoint':{'videoId':'notshown001'}}}}}
    card={'shortsLockupViewModel':{
        'onTap':{'innertubeCommand':{'reelWatchEndpoint':{'videoId':'example0001'}}},
        'overlayMetadata':{'primaryText':{'content':'Fanum prank 😂'},'secondaryText':{'content':'1.2m views'}},
        'recommendation':nested}}
    html='<script>var ytInitialData = '+json.dumps({'contents':[card,card]})+';</script>'
    class EmptySearch:
        def __init__(self,opts): pass
        def __enter__(self): return self
        def __exit__(self,*a): pass
        def extract_info(self,*a,**kw): return {'entries':[]}
    class Response:
        def __enter__(self): return self
        def __exit__(self,*a): pass
        def read(self,size): return html.encode()
    monkeypatch.setattr(yt_dlp,'YoutubeDL',EmptySearch)
    def public_page(request,timeout):
        assert request.full_url.startswith('https://www.youtube.com/results?')
        assert not request.has_header('Cookie')
        return Response()
    monkeypatch.setattr(d,'urlopen',public_page)
    rows=d.search_shorts('funny streamer',{})
    assert len(rows)==1 and rows[0]['id']=='example0001'
    assert rows[0]['view_count']==1200000
    with pytest.raises(ValueError): d.page_entries('<html>not search results</html>')
