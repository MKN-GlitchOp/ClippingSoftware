"""LocalCut MCP Server for ChatGPT and Claude integration.

Exposes LocalCut's video clipping, AI transcription, viral moment analysis,
caption styling, and rendering capabilities as Model Context Protocol (MCP) tools.
"""
import argparse
import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from mcp.server.mcpserver import MCPServer
from backend.services import storage
from backend.services.pipeline import process
from backend.services.downloader import normalize_url
from backend.services.social_generator import build_social_post
from backend.services.renderer import render_project
from backend.main import create, submit, jobs, Settings

server = MCPServer("LocalCut")


@server.tool()
def list_projects() -> list[dict]:
    """List all clipping projects in LocalCut with their ID, title, status, clip count, and progress."""
    result = []
    for path in sorted(storage.ROOT.glob('*/project.json'), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            p = storage.load(path.parent.name)
            result.append({
                'id': p.get('id'),
                'title': p.get('title'),
                'status': p.get('status'),
                'progress': p.get('progress'),
                'clip_count': len(p.get('candidates', [])),
                'duration': p.get('media', {}).get('duration')
            })
        except Exception:
            continue
    return result


@server.tool()
def get_project_details(project_id: str) -> dict:
    """Retrieve full project status, duration, and list of viral candidate clips with scores, hooks, and timestamps."""
    try:
        p = storage.load(project_id)
        candidates = []
        for c in p.get('candidates', []):
            candidates.append({
                'id': c.get('id'),
                'title': c.get('title'),
                'score': c.get('score'),
                'start': c.get('start'),
                'end': c.get('end'),
                'duration': c.get('duration'),
                'hook': c.get('hook'),
                'reason': c.get('reason'),
                'selected': c.get('selected', False),
                'render_status': c.get('render_status', 'pending'),
                'file': c.get('file'),
                'captions': c.get('captions', True),
                'caption_style': c.get('caption_style', 'hormozi'),
                'face_tracking': c.get('face_tracking', True)
            })
        return {
            'id': p.get('id'),
            'title': p.get('title'),
            'status': p.get('status'),
            'progress': p.get('progress'),
            'detail': p.get('detail'),
            'duration': p.get('media', {}).get('duration'),
            'candidates_count': len(candidates),
            'candidates': candidates
        }
    except Exception as e:
        return {'error': f"Failed to load project {project_id}: {str(e)}"}


@server.tool()
def create_clipping_project(
    url: str,
    num_clips: int = 10,
    auto_pilot: bool = False,
    ratio: str = "9:16",
    captions: bool = True,
    min_length: float = 20.0,
    max_length: float = 60.0,
    model: str = "base"
) -> dict:
    """Download a video from YouTube / stream URL, transcribe speech, and extract viral clips.
    
    If auto_pilot is True, it will automatically render the top clips once analysis completes.
    """
    try:
        clean_url = normalize_url(url)
    except Exception as e:
        return {'error': f"Invalid URL: {str(e)}"}

    settings_dict = {
        'num_clips': min(50, max(1, num_clips)),
        'min_length': min_length,
        'max_length': max_length,
        'ratio': ratio if ratio in ('9:16', '16:9', '1:1') else '9:16',
        'captions': captions,
        'model': model if model in ('tiny', 'base', 'small') else 'base',
        'auto_pilot': auto_pilot
    }
    settings_obj = Settings(**settings_dict)
    p = create(settings_obj, 'Web Video', clean_url)
    submit(p['id'], process)
    return {
        'status': 'started',
        'project_id': p['id'],
        'title': p['title'],
        'message': f"Project enqueued for analysis (target: {num_clips} clips). Check progress with get_project_details."
    }


@server.tool()
def edit_clip(
    project_id: str,
    clip_id: str,
    title: str | None = None,
    start: float | None = None,
    end: float | None = None,
    selected: bool | None = None,
    captions: bool | None = None,
    caption_style: str | None = None,
    caption_color: str | None = None,
    caption_bounce: bool | None = None,
    face_tracking: bool | None = None,
    ratio: str | None = None
) -> dict:
    """Update title, duration, caption style ('hormozi', 'beast', 'neon', 'boxed', 'minimal', 'classic'), or face tracking for a clip."""
    with storage.LOCK:
        try:
            p = storage.load(project_id)
        except Exception as e:
            return {'error': f"Project not found: {str(e)}"}

        c = next((c for c in p.get('candidates', []) if c['id'] == clip_id), None)
        if not c:
            return {'error': f"Clip {clip_id} not found in project."}

        if title is not None:
            c['title'] = title.strip()
        if start is not None:
            c['start'] = round(start, 3)
        if end is not None:
            c['end'] = round(end, 3)
        if start is not None or end is not None:
            c['duration'] = round(c['end'] - c['start'], 3)
            c['edited'] = True
            c['render_status'] = 'pending'
            c.pop('file', None)
        if selected is not None:
            c['selected'] = selected
        if captions is not None:
            c['captions'] = captions
        if caption_style is not None:
            c['caption_style'] = caption_style
        if caption_color is not None:
            c['caption_color'] = caption_color
        if caption_bounce is not None:
            c['caption_bounce'] = caption_bounce
        if face_tracking is not None:
            c['face_tracking'] = face_tracking
        if ratio is not None:
            c['ratio'] = ratio

        storage.save(p)
        return {'status': 'updated', 'clip': c}


@server.tool()
def render_clips(
    project_id: str,
    clip_ids: list[str] | None = None,
    ratio: str = "9:16",
    resolution: str = "1080p",
    captions: bool | None = None,
    face_tracking: bool | None = None
) -> dict:
    """Render one or more clips into finished MP4 shorts with face tracking, loudnorm audio, and burned-in viral captions."""
    with storage.LOCK:
        try:
            p = storage.load(project_id)
        except Exception as e:
            return {'error': f"Project not found: {str(e)}"}

        if p.get('status') not in ('ready', 'complete') or project_id in jobs:
            return {'error': 'Project is busy or not ready for rendering.'}

        submit(
            project_id,
            lambda pid: render_project(
                pid,
                ids=clip_ids,
                ratio=ratio,
                resolution=resolution,
                captions=captions,
                face_tracking=face_tracking
            ),
            kind='render'
        )
        return {'status': 'render_started', 'project_id': project_id, 'message': 'Rendering enqueued.'}


@server.tool()
def generate_social_post_metadata(project_id: str, clip_id: str) -> dict:
    """Generate ready-to-post viral titles, descriptions, and hashtag stacks for TikTok, YouTube Shorts, and Instagram Reels."""
    try:
        p = storage.load(project_id)
        clip = next((c for c in p.get('candidates', []) if c['id'] == clip_id), None)
        if not clip:
            return {'error': f"Clip {clip_id} not found."}
        post_data = build_social_post(clip, project_title=p.get('title', ''))
        if clip.get('file'):
            post_data['export_video_path'] = str(storage.folder(project_id) / 'exports' / clip['file'])
        return post_data
    except Exception as e:
        return {'error': str(e)}


@server.tool()
def open_export_folder(project_id: str) -> dict:
    """Open Windows File Explorer showing the exported videos and subtitles for the project."""
    folder = storage.folder(project_id) / 'exports'
    folder.mkdir(parents=True, exist_ok=True)
    if os.name == 'nt':
        import subprocess
        subprocess.Popen(['explorer', str(folder)])
    return {'status': 'opened', 'folder': str(folder)}


def main():
    parser = argparse.ArgumentParser(description="LocalCut MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse", "streamable-http"], default="stdio", help="MCP transport protocol")
    parser.add_argument("--host", default="127.0.0.1", help="Host for SSE/HTTP transport")
    parser.add_argument("--port", type=int, default=8001, help="Port for SSE/HTTP transport")
    args = parser.parse_args()

    if args.transport == "stdio":
        server.run(transport="stdio")
    else:
        server.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
