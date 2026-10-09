from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services import trends as t, benchmarks as b


@pytest.fixture
def database(tmp_path,monkeypatch):
    monkeypatch.setattr(b,'DB_PATH',tmp_path/'trends.sqlite3')
    monkeypatch.setattr(b,'now',lambda:datetime(2026,10,5,tzinfo=timezone.utc))


def add(id,title,views=1000,uploaded='20261002',channel='Channel',likes=10):
    record=b.make_record(dict(id=id,title=title,view_count=views,like_count=likes,
                             duration=35,width=1080,height=1920,upload_date=uploaded,channel=channel))
    b.save_record(record)


def test_month_filters_upload_date_not_collection_date(database):
    add('october0001','Top 5 Minecraft games',5000)
    add('september01','Top 5 Minecraft games',900000,uploaded='20260930')
    add('october0002','Minecraft highlights',8000)
    result=t.report('2026-10')
    assert result['total']==1 and result['videos'][0]['id']=='october0001'
    assert t.report('2026-10',format='all')['total']==2
    assert t.report('2026-09')['total']==1


def test_topics_use_title_evidence_medians_and_sample_sizes(database):
    add('example0001','Top 5 Minecraft games',1000000,channel='One')
    add('example0002','Ranking the best games',100,channel='Two')
    add('example0003','Top five gaming moments',200,channel='Three')
    add('example0004','Top 5 animals',10000,channel='Four')
    result=t.report('2026-10')
    assert result['topics'][0]['id']=='animals'  # Median resists one giant outlier.
    gaming=next(x for x in result['topics'] if x['id']=='gaming')
    assert gaming['count']==3 and gaming['median_views']==200 and gaming['channels']==3
    assert gaming['evidence']=='Multiple examples'
    assert result['topics'][0]['evidence']=='Limited sample'
    assert result['videos'][0]['views']==1000000
    assert t.report('2026-10',format='top5')['total']==3


def test_unknown_counts_sort_last_and_do_not_become_zero(database):
    add('example0001','Top 5 dogs',None,likes=None)
    add('example0002','Top 5 cats',10)
    result=t.report('2026-10')
    assert result['videos'][-1]['views'] is None
    assert result['missing_views']==1 and result['total_views']==10
    assert result['topics'][0]['low_reach'] is True
    assert t.TOP_FIVE.search('Top-5 ranking of cats')


def test_month_and_filters_are_validated(database):
    with TestClient(app) as client:
        assert client.get('/api/trends?month=2026-13').status_code==400
        assert client.get('/api/trends?month=2027-01').status_code==400
        assert client.get('/api/trends?sort=madeup').status_code==422
        assert client.get('/api/trends?month=2026-10&topic=gaming&format=ranking').json()['total']==0
        assert client.post('/api/trends/scan',json={'month':'2026-99'}).status_code==400
    start,end=t.month_bounds('2025-12')
    assert end.year==2026 and end.month==1


def test_scan_postfilters_real_upload_dates_and_deduplicates(database,monkeypatch):
    import yt_dlp
    calls=[]
    class Downloader:
        def __init__(self,opts): self.opts=opts
        def __enter__(self): return self
        def __exit__(self,*a): pass
        def extract_info(self,url,download=False):
            assert not download and self.opts['skip_download']
            if 'results?' in url:
                assert 'after%3A2026-10-01' in url
                return {'entries':[{'id':'example0001'},{'id':'example0001'},{'id':'example0002'}]}
            calls.append(url)
            return dict(id=url.split('=')[-1],title='Top 5 gaming clips',view_count=1000,
                        width=1080,height=1920,duration=30,
                        upload_date='20261002' if url.endswith('1') else '20260930')
    monkeypatch.setattr(yt_dlp,'YoutubeDL',Downloader)
    t.scan('2026-10','gaming')
    assert len(calls)==2 and b.status()['saved']==1 and t.report('2026-10')['total']==1
    assert b.list_records()['total']==2  # Older record remains useful in its own month.
