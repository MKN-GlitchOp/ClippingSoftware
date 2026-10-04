"""ASS word highlight events on a clip-relative timeline."""
import re

HIGHLIGHT_COLORS = {
    'yellow': '&H00FFFF&',
    'mint': '&H99FFBB&',
    'green': '&H00FF66&',
    'cyan': '&HFFFF00&',
    'gold': '&H00D7FF&',
    'white': '&HFFFFFF&'
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
    if width > height:
        # Landscape (e.g. 1920x1080): comfortable readable font in lower third
        font_size = clip.get('caption_size') or round(54 * height / 1080)
        bottom = round(height * (0.08 if clip.get('caption_position') == 'upper' else 0.12))
        margin_lr = round(width * 0.08)
    else:
        # Vertical (e.g. 1080x1920) or Square
        font_size = clip.get('caption_size') or round(68 * width / 1080)
        bottom = round(height * (0.12 if clip.get('caption_position') == 'upper' else 0.22))
        margin_lr = round(width * 0.08)

    upper = clip.get('caption_position') == 'upper'
    alignment = 8 if upper else 2
    highlight_code = HIGHLIGHT_COLORS.get(clip.get('caption_color', 'yellow'), '&H00FFFF&')
    is_uppercase = bool(clip.get('caption_uppercase', False))

    header = f'''[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Segoe UI,{font_size},&H00FFFFFF,&H0000FFFF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,4,1,{alignment},{margin_lr},{margin_lr},{bottom},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    words = []
    for segment in transcript['segments']:
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
                words.append(dict(word=clean_word, start=max(0, word['start'] - clip['start']), end=min(clip['end'] - clip['start'], word['end'] - clip['start'])))

    chunks, chunk = [], []
    for word in words:
        if chunk and (len(chunk) >= 4 or sum(len(w['word']) + 1 for w in chunk) + len(word['word']) > 24 or word['start'] - chunk[-1]['end'] > 0.65):
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
            text = ' '.join((rf'{{\c{highlight_code}}}' + w['word'] + r'{\c&HFFFFFF&}') if n == i else w['word'] for n, w in enumerate(chunk))
            events.append(f'Dialogue: 0,{ass_time(word["start"])},{ass_time(end)},Default,,0,0,0,,{text}')
    path.write_text(header + '\n'.join(events) + '\n', encoding='utf-8-sig')
