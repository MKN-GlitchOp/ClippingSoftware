import pytest
from backend.services.clip_analysis import detect_teaser_hook
from backend.services.subtitles import make_ass, make_clip_srt
from backend.services.social_generator import build_social_post


def test_detect_teaser_hook():
    passage = [
        {'word': 'So', 'start': 10.0, 'end': 10.5},
        {'word': 'we', 'start': 10.5, 'end': 10.8},
        {'word': 'were', 'start': 10.8, 'end': 11.0},
        {'word': 'talking', 'start': 11.0, 'end': 11.5},
        # Climax reaction in second half
        {'word': 'Wait', 'start': 30.0, 'end': 30.4},
        {'word': 'what?!', 'start': 30.4, 'end': 30.8},
        {'word': 'Are', 'start': 30.8, 'end': 31.0},
        {'word': 'you', 'start': 31.0, 'end': 31.2},
        {'word': 'serious?!', 'start': 31.2, 'end': 32.5},
        {'word': 'No', 'start': 32.5, 'end': 32.8},
        {'word': 'way!', 'start': 32.8, 'end': 33.2},
    ]
    audio_energy = {
        'window_sec': 0.5,
        'energies': [0.1] * 60 + [0.9, 0.95, 0.9] + [0.2] * 20
    }
    teaser = detect_teaser_hook(passage, audio_energy, total_duration=50.0)
    assert teaser is not None
    assert teaser['teaser_enabled'] is True
    assert 2.0 <= (teaser['teaser_end'] - teaser['teaser_start']) <= 4.0
    assert 'Wait' in teaser['teaser_text'] or 'serious' in teaser['teaser_text']
    assert teaser['teaser_badge'] == '⚡ WAIT FOR IT...'


def test_make_ass_with_teaser(tmp_path):
    ass_path = tmp_path / 'teaser.ass'
    transcript = {
        'segments': [{
            'start': 10, 'end': 35,
            'text': 'We started walking then wait what?! Are you serious?!',
            'words': [
                {'word': 'We', 'start': 10.0, 'end': 10.5},
                {'word': 'started', 'start': 10.5, 'end': 11.2},
                {'word': 'walking', 'start': 11.2, 'end': 12.0},
                {'word': 'Wait', 'start': 30.0, 'end': 30.5},
                {'word': 'what?!', 'start': 30.5, 'end': 32.5},
            ]
        }]
    }
    clip = {
        'start': 10.0,
        'end': 12.0,  # 2.0s main clip
        'teaser_enabled': True,
        'teaser_start': 30.0,
        'teaser_end': 32.5,  # 2.5s teaser
        'teaser_text': 'Wait what?!',
        'teaser_badge': '⚡ WAIT FOR IT...'
    }
    make_ass(transcript, clip, ass_path, 1080, 1920)
    content = ass_path.read_text(encoding='utf-8-sig')

    # TopBadge style should be registered
    assert 'Style: TopBadge' in content
    # TopBadge dialogue should appear
    assert '⚡ WAIT FOR IT...' in content
    # Teaser word should appear
    assert 'WAIT' in content
    # Main clip words should be shifted by +2.5s teaser duration (10.0s -> 2.5s)
    assert '0:00:02.50' in content


def test_social_post_with_teaser():
    clip = {
        'id': '1',
        'title': 'Awkward Blind Date',
        'start': 10.0,
        'end': 25.0,
        'score': 88,
        'tags': ['blinddate', 'dropouts', 'funny'],
        'teaser_enabled': True,
        'teaser_text': 'Did you just bring your mom?!',
        'hook': 'So we showed up to the date...'
    }
    post = build_social_post(clip, project_title='Dropouts Blind Date')
    assert 'Wait for it' in post['tiktok']['title']
    assert 'Wait till you see what happened' in post['tiktok']['caption']
    assert 'Did you just bring your mom?!' in post['tiktok']['caption']
    assert 'Wait for the end' in post['youtube']['title']
