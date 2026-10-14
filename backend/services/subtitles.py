"""ASS word highlight events on a clip-relative timeline with viral styling presets."""
import re

HIGHLIGHT_COLORS = {
    'yellow': '&H00FFFF&',
    'mint': '&H99FFBB&',
    'green': '&H00FF66&',
    'cyan': '&HFFFF00&',
    'gold': '&H00D7FF&',
    'red': '&H0000FF&',
    'magenta': '&HFF00FF&',
    'orange': '&H0080FF&',
    'white': '&HFFFFFF&'
}

PRESETS = {
    'hormozi': {
        'name': 'Hormozi Pop',
        'font': 'Impact',
        'bold': -1,
        'color': 'yellow',
        'outline': 5,
        'shadow': 2,
        'border_style': 1,
        'bounce': True,
        'uppercase': True,
        'chunk_size': 'phrase'
    },
    'beast': {
        'name': 'MrBeast Punch',
        'font': 'Arial Black',
        'bold': -1,
        'color': 'yellow',
        'outline': 6,
        'shadow': 3,
        'border_style': 1,
        'bounce': True,
        'uppercase': True,
        'chunk_size': 'single'
    },
    'neon': {
        'name': 'Cyber Neon',
        'font': 'Montserrat',
        'bold': -1,
        'color': 'cyan',
        'outline': 4,
        'shadow': 4,
        'border_style': 1,
        'bounce': True,
        'uppercase': True,
        'chunk_size': 'phrase'
    },
    'boxed': {
        'name': 'Boxed Karaoke',
        'font': 'Montserrat',
        'bold': -1,
        'color': 'yellow',
        'outline': 0,
        'shadow': 0,
        'border_style': 3,
        'back_color': '&H90000000',
        'bounce': False,
        'uppercase': False,
        'chunk_size': 'phrase'
    },
    'minimal': {
        'name': 'Minimalist',
        'font': 'Segoe UI',
        'bold': -1,
        'color': 'mint',
        'outline': 2,
        'shadow': 1,
        'border_style': 1,
        'bounce': False,
        'uppercase': False,
        'chunk_size': 'phrase'
    },
    'classic': {
        'name': 'Classic',
        'font': 'Segoe UI',
        'bold': -1,
        'color': 'yellow',
        'outline': 4,
        'shadow': 1,
        'border_style': 1,
        'bounce': False,
        'uppercase': False,
        'chunk_size': 'phrase'
    }
}


def ass_time(seconds):
    cs = max(0, round(seconds * 100))
    return f'{cs // 360000}:{cs // 6000 % 60:02}:{cs // 100 % 60:02}.{cs % 100:02}'


def srt_time(seconds):
    ms = max(0, round(seconds * 1000))
    return f'{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}'


def safe(text):
    return re.sub(r'[{}\\\r\n]', '', text).strip()


def extract_clip_words(transcript, clip, is_uppercase=False):
    """
    Extracts words for a clip, supporting cold-open teaser hook (summarize mode).
    If teaser_enabled is True and teaser_dur >= 0.5s:
      - Teaser words are emitted first for 0.0 to teaser_dur
      - Main clip words are emitted next, offset by +teaser_dur
    Otherwise, standard words are emitted for 0.0 to clip_dur.
    """
    teaser_enabled = bool(clip.get('teaser_enabled'))
    teaser_start = float(clip.get('teaser_start', clip['start']))
    teaser_end = float(clip.get('teaser_end', clip['start']))
    teaser_dur = max(0.0, teaser_end - teaser_start) if teaser_enabled else 0.0

    def collect_range(start_bound, end_bound, time_offset):
        collected = []
        for segment in transcript.get('segments', []):
            source_words = segment.get('words')
            if not source_words:
                tokens = segment['text'].split()
                length = (segment['end'] - segment['start']) / max(1, len(tokens))
                source_words = [dict(word=w, start=segment['start'] + i * length, end=segment['start'] + (i + 1) * length) for i, w in enumerate(tokens)]
            for word in source_words:
                clean_word = safe(word['word'])
                if word['end'] > start_bound and word['start'] < end_bound and clean_word:
                    if is_uppercase:
                        clean_word = clean_word.upper()
                    w_start = time_offset + max(0.0, word['start'] - start_bound)
                    w_end = time_offset + min(end_bound - start_bound, word['end'] - start_bound)
                    if w_end > w_start:
                        collected.append(dict(word=clean_word, start=round(w_start, 3), end=round(w_end, 3)))
        return collected

    if teaser_enabled and teaser_dur >= 0.5:
        teaser_words = collect_range(teaser_start, teaser_end, 0.0)
        main_words = collect_range(clip['start'], clip['end'], teaser_dur)
        return teaser_words + main_words, teaser_dur
    else:
        return collect_range(clip['start'], clip['end'], 0.0), 0.0


def make_clip_srt(transcript, clip, path):
    """Generate an SRT subtitle file aligned to the clip's local timeline (starting at 00:00:00)."""
    words, _ = extract_clip_words(transcript, clip, is_uppercase=False)
    if not words:
        path.write_text('', encoding='utf-8')
        return

    # Group into natural phrases (3 to 6 words or punctuation pause)
    chunks, chunk = [], []
    for word in words:
        if chunk and (len(chunk) >= 5 or sum(len(w['word']) + 1 for w in chunk) + len(word['word']) > 28 or word['start'] - chunk[-1]['end'] > 0.6):
            chunks.append(chunk)
            chunk = []
        chunk.append(word)
        if word['word'].endswith(('.', '!', '?')):
            chunks.append(chunk)
            chunk = []
    if chunk:
        chunks.append(chunk)

    srt_entries = []
    for i, ch in enumerate(chunks, 1):
        start_t = srt_time(ch[0]['start'])
        end_t = srt_time(ch[-1]['end'])
        text = ' '.join(w['word'] for w in ch)
        srt_entries.append(f'{i}\n{start_t} --> {end_t}\n{text}\n')

    path.write_text('\n'.join(srt_entries), encoding='utf-8')


def make_ass(transcript, clip, path, width, height):
    style_key = clip.get('caption_style', 'hormozi')
    preset = PRESETS.get(style_key, PRESETS['hormozi'])

    font_name = clip.get('caption_font') or preset['font']
    border_style = preset.get('border_style', 1)
    outline = preset.get('outline', 5)
    shadow = preset.get('shadow', 2)
    back_colour = preset.get('back_color', '&H80000000')

    # Font sizing adapted to resolution and orientation
    if width > height:
        # Landscape
        base_size = round(56 * height / 1080)
        default_bottom = round(height * (0.08 if clip.get('caption_position') == 'upper' else 0.12))
        margin_lr = round(width * 0.08)
    else:
        # Vertical or Square
        base_size = round(72 * width / 1080)
        default_bottom = round(height * (0.12 if clip.get('caption_position') == 'upper' else 0.22))
        margin_lr = round(width * 0.08)

    font_size = clip.get('caption_size') or base_size

    pos = clip.get('caption_position', 'lower')
    if pos == 'upper':
        alignment = 8
        bottom = default_bottom
    elif pos == 'middle':
        alignment = 5
        bottom = 0
    else:
        alignment = 2
        bottom = default_bottom

    if clip.get('caption_offset_y') is not None:
        try:
            bottom = round(height * (float(clip['caption_offset_y']) / 100.0))
        except (ValueError, TypeError):
            pass

    color_key = clip.get('caption_color') or preset.get('color', 'yellow')
    highlight_code = HIGHLIGHT_COLORS.get(color_key, '&H00FFFF&')

    # Uppercase setting
    is_uppercase = clip.get('caption_uppercase')
    if is_uppercase is None:
        is_uppercase = preset.get('uppercase', False)
    is_uppercase = bool(is_uppercase)

    # Word bounce / scale pop setting
    bounce = clip.get('caption_bounce')
    if bounce is None:
        bounce = preset.get('bounce', True)
    bounce = bool(bounce)

    # Chunk mode: single (1-2 words) vs phrase (3-5 words)
    chunk_mode = clip.get('caption_chunk_size') or preset.get('chunk_size', 'phrase')
    max_chunk_words = 2 if chunk_mode == 'single' else 4
    max_chunk_chars = 14 if chunk_mode == 'single' else 24

    header = f'''[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H0000FFFF,&H00101010,{back_colour},-1,0,0,0,100,100,0,0,{border_style},{outline},{shadow},{alignment},{margin_lr},{margin_lr},{bottom},1
Style: TopBadge,{font_name},{round(font_size * 0.65)},&H0000FFFF,&H000000FF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,8,30,30,{round(height * 0.08)},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''

    words, teaser_dur = extract_clip_words(transcript, clip, is_uppercase=is_uppercase)

    chunks, chunk = [], []
    for word in words:
        if chunk and (len(chunk) >= max_chunk_words or sum(len(w['word']) + 1 for w in chunk) + len(word['word']) > max_chunk_chars or word['start'] - chunk[-1]['end'] > 0.65):
            chunks.append(chunk)
            chunk = []
        chunk.append(word)
        if word['word'].endswith(('.', '!', '?')):
            chunks.append(chunk)
            chunk = []
    if chunk:
        chunks.append(chunk)

    events = []
    if teaser_dur >= 0.5:
        badge_text = str(clip.get('teaser_badge', 'WAIT FOR IT...')).strip()
        if badge_text and badge_text.lower() != 'clean':
            events.append(f'Dialogue: 1,{ass_time(0.0)},{ass_time(teaser_dur)},TopBadge,,0,0,0,,⚡ {badge_text}')
    for chunk in chunks:
        for i, word in enumerate(chunk):
            end = chunk[i + 1]['start'] if i + 1 < len(chunk) else word['end']
            if end <= word['start']:
                continue
            if bounce:
                # Signature active word scale bounce: enlarged to 118% then resets to standard size
                active_str = rf'{{\fscx118\fscy118\c{highlight_code}}}' + word['word'] + rf'{{\fscx100\fscy100\c&HFFFFFF&}}'
            else:
                active_str = rf'{{\c{highlight_code}}}' + word['word'] + r'{\c&HFFFFFF&}'

            text = ' '.join(active_str if n == i else w['word'] for n, w in enumerate(chunk))
            events.append(f'Dialogue: 0,{ass_time(word["start"])},{ass_time(end)},Default,,0,0,0,,{text}')

    path.write_text(header + '\n'.join(events) + '\n', encoding='utf-8-sig')
