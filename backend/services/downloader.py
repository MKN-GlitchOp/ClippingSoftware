from urllib.parse import urlparse, parse_qs
from pathlib import Path
import time
import re
import shutil
import logging
from yt_dlp import YoutubeDL


def normalize_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or parsed.hostname not in ('youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be'):
        raise ValueError('Enter a valid YouTube video URL.')
    parts = parsed.path.strip('/').split('/')
    video_id = parts[0] if parsed.hostname == 'youtu.be' else parse_qs(parsed.query).get('v', [''])[0]
    if not video_id and len(parts) == 2 and parts[0] in ('shorts', 'live', 'embed'):
        video_id = parts[1]
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
        raise ValueError('Paste a link to one YouTube video, not a channel or playlist.')
    return 'https://www.youtube.com/watch?v=' + video_id


def friendly_error(error):
    message = re.sub(r'\x1b\[[0-9;]*m', '', str(error)).lower()
    if '403' in message or 'forbidden' in message or 'confirm you' in message or 'bot' in message:
        return 'YouTube refused this download. Try updating yt-dlp, retry later, or upload a local copy of the video.'
    if 'private' in message or 'sign in' in message or 'members-only' in message:
        return 'This video requires account access. Choose a public video or upload a local copy.'
    if 'unavailable' in message or 'removed' in message:
        return 'This YouTube video is unavailable. Check the link or choose another video.'
    if 'disk' in message or 'space' in message:
        return 'There is not enough free disk space to download this video.'
    return 'The download could not finish. Check your internet connection and try again. Partial downloads are kept for retry.'


def download(url, folder, progress):
    url = normalize_url(url)
    last_update = 0
    def hook(data):
        nonlocal last_update
        if data['status'] == 'downloading':
            if time.monotonic()-last_update < .5:
                return
            last_update=time.monotonic()
            if shutil.disk_usage(folder).free < 256*1024**2:
                raise RuntimeError('Insufficient disk space for download')
            total = data.get('total_bytes') or data.get('total_bytes_estimate') or 0
            progress('downloading', min(24, 5 + int(19 * data.get('downloaded_bytes', 0) / total)) if total else 10)
    options = dict(format='bv*[height<=1080][vcodec^=avc]+ba[acodec^=mp4a]/b[height<=1080]/bv*[height<=1080]+ba',
                   outtmpl=str(folder / 'video.%(ext)s'), merge_output_format='mp4', noplaylist=True,
                   progress_hooks=[hook], quiet=True, noprogress=True, no_color=True,
                   socket_timeout=25, retries=3, fragment_retries=3,
                   js_runtimes={'node': {}}, remote_components=['ejs:github'])
    try:
        with YoutubeDL(options) as dl:
            info = dl.extract_info(url, download=False)
            if info.get('is_live'):
                raise ValueError('Live streams are not supported. Wait until the video has finished.')
            info = dl.process_ie_result(info, download=True)
    except Exception as exc:
        logging.exception('YouTube download failed')
        if isinstance(exc, ValueError):
            raise
        raise RuntimeError(friendly_error(exc)) from exc
    files = [p for p in folder.glob('video.*') if p.stem == 'video' and p.suffix in ('.mp4', '.mkv', '.webm')]
    if not files:
        raise RuntimeError('Download completed without a usable video.')
    return files[0], info.get('title', 'YouTube video')
