from backend.services.subtitles import make_ass
from backend.services.clip_analysis import speech_units, clip_text


def test_caption_safe_text_and_clip_relative_timing(tmp_path):
    path=tmp_path/'clip.ass'
    t={'segments':[{'start':9,'end':15,'text':'Before Hello world. After','words':[dict(word='Before',start=9,end=9.5),dict(word='{Hello}',start=10,end=11),dict(word='world.',start=11,end=12),dict(word='After',start=14,end=15)]}]}
    make_ass(t,dict(start=10,end=12),path,1080,1920)
    text=path.read_text(encoding='utf-8-sig')
    assert 'Before' not in text and 'After' not in text
    assert '{Hello}' not in text
    assert '0:00:00.00,0:00:01.00' in text
    assert '0:00:01.00,0:00:02.00' in text


def test_sentence_boundaries_and_edited_transcript():
    t={'segments':[{'start':0,'end':9,'text':'First sentence. Second thought.','words':[dict(word='First',start=0,end=1),dict(word='sentence.',start=1,end=2),dict(word='Second',start=5,end=6),dict(word='thought.',start=6,end=9)]}]}
    units=speech_units(t)
    assert len(units)==2
    assert units[1]['start']==5
    assert clip_text(t,5,9)=='Second thought.'
