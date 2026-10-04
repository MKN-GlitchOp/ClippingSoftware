from backend.services.clip_analysis import analyze
from backend.main import Settings
import pytest


def test_complete_bounds_and_non_overlap():
    transcript = {'segments':[dict(start=i*5,end=i*5+4,text=('Here is the secret. You learn why this works.' if i%3==0 else 'The story finally has an amazing result.')) for i in range(20)]}
    results = analyze(transcript, dict(min_length=10,max_length=25,num_clips=5,captions=True),dict(scenes=[9.8,24.2],silence=[[40,43]]),100)
    assert results
    for c in results:
        assert 0 <= c['start'] < c['end'] <= 100
        assert 10 <= c['duration'] <= 25
        assert 0 <= c['score'] <= 100
    for i,a in enumerate(results):
        for b in results[i+1:]:
            overlap=max(0,min(a['end'],b['end'])-max(a['start'],b['start']))
            assert overlap < .25*min(a['duration'],b['duration'])


def test_sponsor_penalty():
    def score(text):
        return analyze({'segments':[dict(start=0,end=20,text=text)]},dict(min_length=10,max_length=30,num_clips=1,captions=False),dict(scenes=[],silence=[]),20)[0]['score']
    normal='Here is the secret. You learn why this amazing result works so well.'
    assert score(normal+' Use our sponsor promo code.') < score(normal)


def test_length_validation():
    with pytest.raises(ValueError):
        Settings(min_length=60,max_length=20)
