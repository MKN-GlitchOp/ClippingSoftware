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


def make_clip_srt(transcript, clip, path):
    """Generate an SRT subtitle file aligned to the clip's local timeline (starting at 00:00:00)."""
    words = []
    for segment in transcript.get('segments', []):
        source_words = segment.get('words')
        if not source_words:
            tokens = segment['text'].split()
            length = (segment['end'] - segment['start']) / max(1, len(tokens))
            source_words = [dict(word=w, start=segment['start'] + i * length, end=segment['start'] + (i + 1) * length) for i, w in enumerate(tokens)]
        for word in source_words:
            clean_word = safe(word['word'])
            if word['end'] > clip['start'] and word['start'] < clip['end'] and clean_word:
                words.append(dict(
                    word=clean_word,
                    start=max(0.0, word['start'] - clip['start']),
                    end=min(clip['end'] - clip['start'], word['end'] - clip['start'])
                ))
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

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''

    words = []
    for segment in transcript.get('segments', []):
        source_words = segment.get('words')
        if not source_words:
            tokens = segment['text'].split()
            length = (segment['end'] - segment['start']) / max(1, len(tokens))
            source_words = [dict(word=w, start=segment['start'] + i * length, end=segment['start'] + (i + 1) * length) for i, w in enumerate(tokens)]
        for word in source_words:
            clean_word = safe(word['word'])
            if word['end'] > clip['start'] and word['start'] < clip['end'] and clean_word:
                if is_uppercase:
                    clean_word = clean_word.upper()
                words.append(dict(
                    word=clean_word,
                    start=max(0.0, word['start'] - clip['start']),
                    end=min(clip['end'] - clip['start'], word['end'] - clip['start'])
                ))

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
