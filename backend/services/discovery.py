"""Bounded public Shorts discovery, with a search-page fallback for yt-dlp gaps."""
import json
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def search_url(query):
    # Exact Shorts link exposed by YouTube's Search filters UI (checked 2026-10-09).
    return 'https://www.youtube.com/results?'+urlencode({'search_query':query,'sp':'EgIQCQ%3D%3D','hl':'en'})


def page_entries(html, limit=30):
    marker=re.search(r'(?:var\s+)?ytInitialData\s*=\s*',html)
    if not marker:
        raise ValueError('YouTube did not return readable public search results.')
    data,_=json.JSONDecoder().raw_decode(html[marker.end():])
    entries={}
    stack=[data]
    while stack:
        value=stack.pop()
        if isinstance(value,list):
            stack.extend(reversed(value))
            continue
        if not isinstance(value,dict):
            continue
        card=value.get('shortsLockupViewModel')
        if isinstance(card,dict):
            endpoint=card.get('onTap',{}).get('innertubeCommand',{}).get('reelWatchEndpoint',{})
            vid=endpoint.get('videoId','')
            overlay=card.get('overlayMetadata',{})
            title=overlay.get('primaryText',{}).get('content','')
            count_text=overlay.get('secondaryText',{}).get('content','').lower().replace(',','')
            match=re.search(r'(\d+(?:\.\d+)?)\s*([kmb]?)\s*(?:views|view)',count_text)
            count=int(float(match[1])*{'':1,'k':1000,'m':1000000,'b':1000000000}[match[2]]) if match else None
            if re.fullmatch(r'[A-Za-z0-9_-]{11}',vid) and isinstance(title,str):
                entries[vid]=dict(id=vid,title=title,view_count=count,url='https://www.youtube.com/shorts/'+vid)
            # Do not traverse recommendation/sequence data inside a result card.
            if len(entries)>=limit:
                break
        else:
            stack.extend(reversed(list(value.values())))
    return list(entries.values())


def search_shorts(query,options,limit=30):
    from yt_dlp import YoutubeDL
    url=search_url(query)
    try:
        with YoutubeDL({**options,'extract_flat':True,'playlistend':limit}) as search:
            result=search.extract_info(url,download=False) or {}
        entries=[e for e in result.get('entries',[]) if e and re.fullmatch(r'[A-Za-z0-9_-]{11}',e.get('id',''))]
    except Exception:
        entries=[]
    if not entries:
        # Read the public, unauthenticated HTML. No browser cookies or credentials.
        with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0','Accept-Language':'en-US,en;q=0.9'}),timeout=20) as response:
            raw=response.read(8*1024*1024+1)
        if len(raw)>8*1024*1024:
            raise ValueError('Public search response was too large. Try a narrower topic.')
        entries=page_entries(raw.decode('utf-8',errors='replace'),limit)
    return sorted(entries,key=lambda e:e.get('view_count') or 0,reverse=True)
