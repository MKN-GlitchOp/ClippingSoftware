from backend.services.audience import choose_profile, replay_evidence, refine_score
from backend.services.clip_analysis import analyze
from backend.main import Settings, AnalysisOptions
import pytest


def test_profile_detects_topics_without_treating_slang_as_training():
    assert choose_profile('The research study explains this scientific solution.') == 'education'
    assert choose_profile('The game boss is down. The teammate wins the round.') == 'gaming'
    assert choose_profile('An ordinary conversation.', 'story') == 'story'
    assert choose_profile('Hello there.') == 'balanced'


def test_replay_weights_coverage_and_caps_influence():
    heatmap = [dict(start_time=0,end_time=10,value=.1),dict(start_time=10,end_time=20,value=.9)]
    assert replay_evidence(heatmap,10,20)['bonus'] > 0
    assert replay_evidence(heatmap,0,10)['bonus'] == 0
    assert replay_evidence(heatmap,30,40) is None
    assert replay_evidence([dict(start_time=0,end_time=20,value=float('nan'))],0,20) is None


def test_profile_caps_loudness_and_penalizes_slow_opening():
    breakdown={'High vocal energy':12,'Climactic reaction / punchline':10,'High-energy opening hook':6}
    caution=[]
    result=refine_score([dict(start=0,end=20,text='Um before we start let me explain everything about this discovery.')],breakdown,caution,'education',None)
    assert breakdown['Audio evidence cap']==-24
    assert breakdown['Slow opening']==-8 and caution
    assert result['replay'] is None


def test_audience_settings_and_candidate_explanations():
    assert Settings(content_profile='gaming').content_profile=='gaming'
    with pytest.raises(ValueError):
        AnalysisOptions(content_profile='invented')
    transcript={'segments':[dict(start=0,end=20,text='Here is why the research found a solution. You can learn this useful technique and finally fix the problem.')]}
    clip=analyze(transcript,dict(min_length=10,max_length=30,num_clips=1,captions=True,content_profile='education'),{},20)[0]
    assert clip['audience']['profile']=='education'
    assert clip['score_breakdown']['Content fit']>0
    assert 0 <= clip['score'] <= 100
