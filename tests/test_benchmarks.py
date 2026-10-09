from datetime import datetime, timedelta, timezone
import json

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services import benchmarks as b
from backend.services.clip_analysis import analyze

STAMP = datetime(2026,10,5,tzinfo=timezone.utc)


def sample(**changes):
    return dict(id='abcdefghijk',title='Minecraft boat clutch tutorial',channel='Example',duration=35,
                width=1080,height=1920,upload_date='20261001',view_count=1_000_000,
                like_count=50_000,comment_count=350,tags=['minecraft','boat','clutch'],**changes)


@pytest.fixture
def database(tmp_path,monkeypatch):
    monkeypatch.setattr(b,'DB_PATH',tmp_path/'benchmarks.sqlite3')
    monkeypatch.setattr(b,'now',lambda:STAMP)


def test_rejects_non_short_formats_and_preserves_missing_counts():
    info=sample()
    for changes in ({'duration':181},{'width':1920,'height':1080},{'width':None,'height':None},{'is_live':True}):
        assert b.make_record({**info,**changes},clock=STAMP) is None
    record=b.make_record({**info,'like_count':None,'comment_count':None},clock=STAMP)
    assert record['likes'] is None and record['comments'] is None
    assert record['views']==1_000_000
    assert 'retention' not in record


def test_refresh_deduplicates_and_measures_only_real_elapsed_growth(database):
    first=b.make_record(sample(),clock=STAMP-timedelta(days=2))
    b.save_record(first)
    b.save_record(first)
    result=b.list_records()
    assert result['total']==1 and result['videos'][0]['observed_views_per_day'] is None
    second=b.make_record({**sample(),'view_count':1_040_000},clock=STAMP)
    b.save_record(second)
    result=b.list_records()['videos'][0]
    assert result['observed_views_per_day']==20_000
    assert result['lifetime_views_per_day']==260_000
    with b.connect() as db:
        assert db.execute('SELECT count(*) FROM snapshots').fetchone()[0]==2


def test_matches_require_relevance_freshness_and_category():
    row=b.make_record(sample(),profile='gaming',clock=STAMP)
    index=b.BenchmarkIndex([row],clock=STAMP)
    result=index.match('The Minecraft boat clutch saved the round.', 'gaming')
    assert 1<=result['bonus']<=6 and result['examples'][0]['id']=='abcdefghijk'
    assert index.match('This cooking recipe makes delicious pasta.', 'gaming')['bonus']==0
    assert index.match('Minecraft boat clutch', 'education')['bonus']==0
    assert b.BenchmarkIndex([row],clock=STAMP+timedelta(days=31)).match('Minecraft boat clutch','gaming')['bonus']==0


def test_benchmark_integration_can_be_disabled():
    row=b.make_record(sample(),profile='gaming',clock=STAMP)
    index=b.BenchmarkIndex([row],clock=STAMP)
    transcript={'segments':[dict(start=0,end=20,text='Here is how this Minecraft boat clutch works. You can practice the technique and finally win the round.') ]}
    settings=dict(min_length=10,max_length=25,num_clips=1,captions=True,content_profile='gaming')
    enabled=analyze(transcript,settings,{'benchmark_index':index},20)[0]
    disabled=analyze(transcript,{**settings,'use_public_benchmarks':False},{'benchmark_index':index},20)[0]
    assert enabled['score_breakdown']['Relevant public Shorts']>0
    assert 'Relevant public Shorts' not in disabled['score_breakdown']
    assert enabled['audience']['benchmarks']['examples']


def test_many_tags_do_not_dilute_precise_title_matches():
    info=sample()
    info['tags'] += [f'unrelatedtag{i}' for i in range(25)]
    index=b.BenchmarkIndex([b.make_record(info,profile='gaming',clock=STAMP)],clock=STAMP)
    assert index.match('Minecraft boat clutch tutorial', 'gaming')['bonus']>=3


def test_topic_search_uses_shorts_filter_and_is_bounded(database,monkeypatch):
    import yt_dlp
    seen=[]
    class FakeDownload:
        def __init__(self,settings): self.settings=settings
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def extract_info(self,url,download):
            seen.append(url)
            if 'results?' in url:
                assert self.settings['playlistend']==15
                assert 'sp=EgIQCQ%253D%253D' in url
                return {'entries':[{'id':'abcdefghijk','duration':35,'view_count':1000000}]}
            return sample()
    monkeypatch.setattr(yt_dlp,'YoutubeDL',FakeDownload)
    b.collect('Minecraft boat clutch',[],'gaming')
    assert len(seen)==2 and b.list_records()['total']==1


def test_api_database_and_export_are_readable(database):
    b.save_record(b.make_record(sample(),clock=STAMP))
    with TestClient(app) as client:
        result=client.get('/api/benchmarks').json()
        assert result['total']==1
        assert client.get('/api/benchmarks?q=pasta').json()['videos']==[]
        export=client.get('/api/benchmarks/export')
        assert export.status_code==200 and 'attachment' in export.headers['content-disposition']
        assert client.post('/api/benchmarks/collect',json={'urls':['https://example.com/private']}).status_code==400
        assert client.post('/api/benchmarks/collect',json={'query':'x'}).status_code==400
        assert client.post('/api/benchmarks/collect',json={'urls':['https://youtu.be/abcdefghijk']*11}).status_code==422


def test_collection_is_metadata_only_and_keeps_partial_success(database,monkeypatch):
    import yt_dlp
    options=[]
    class FakeDownload:
        def __init__(self, settings): options.append(settings)
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def extract_info(self,url,download):
            assert download is False
            if 'badbadbad00' in url: raise RuntimeError('unavailable')
            return sample()
    monkeypatch.setattr(yt_dlp,'YoutubeDL',FakeDownload)
    b.collect('minecraft',['https://youtu.be/abcdefghijk','https://youtu.be/badbadbad00'],'gaming')
    assert all(option['skip_download'] for option in options)
    assert b.list_records()['total']==1
    assert b.status()['saved']==1 and b.status()['errors']
