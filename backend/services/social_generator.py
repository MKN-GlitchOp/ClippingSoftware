"""Generates viral social media post copy (titles, captions, hashtags) for TikTok, YouTube Shorts, and Instagram Reels."""
import re

GENERIC_HASHTAGS = ["#shorts", "#viral", "#fyp", "#trending", "#foryou", "#contentcreator"]

PLATFORM_SPECIFIC_TAGS = {
    "tiktok": ["#tiktokviral", "#fypシ", "#blowthisup", "#trend"],
    "youtube": ["#youtubeshorts", "#shortsfeed", "#subscribe"],
    "instagram": ["#reels", "#reelsinstagram", "#viralreels", "#instareels"]
}


def clean_hook(text: str) -> str:
    """Extract a clean, punchy hook statement from transcript or hook text."""
    if not text:
        return ""
    text = re.sub(r'^(?:well|okay|alright|you know|i mean|basically|like)[, ]+', '', text, flags=re.I).strip()
    sentences = re.split(r'[.!?]+', text)
    if sentences and sentences[0].strip():
        first = sentences[0].strip()
        if len(first.split()) <= 15:
            return first[0].upper() + first[1:]
    return text[:80].strip()


def build_social_post(clip: dict, project_title: str = "") -> dict:
    """Create ready-to-post copy for TikTok, YouTube Shorts, and Instagram Reels."""
    clip_title = clip.get('title') or "Viral Highlight"
    hook = clean_hook(clip.get('hook') or clip.get('transcript', '')[:100])
    tags = clip.get('tags', [])
    score = clip.get('score', 85)

    # Generate topic-specific hashtags from keywords
    topic_hashtags = [f"#{re.sub(r'[^a-zA-Z0-9]', '', tag)}" for tag in tags if len(tag) > 2][:5]
    all_hashtags = list(dict.fromkeys(topic_hashtags + GENERIC_HASHTAGS))

    # TikTok Copy: Short, curiosity-driven hook, question, hashtags
    tiktok_title = f"{clip_title} 🤯" if score > 80 else clip_title
    tiktok_caption = f"{hook}\n\nDid you expect this? Drop your thoughts below 👇\n\n" + " ".join(all_hashtags[:8] + PLATFORM_SPECIFIC_TAGS["tiktok"])

    # YouTube Shorts Copy: High CTR title, short description
    yt_title = f"{clip_title} #shorts"
    yt_description = (
        f"{clip_title}\n\n"
        f"\"{hook}\"\n\n"
        f"Clip from: {project_title or 'Stream/Podcast'}\n"
        f"Subscribe for more daily highlights!\n\n"
        + " ".join(all_hashtags[:6] + PLATFORM_SPECIFIC_TAGS["youtube"])
    )

    # Instagram Reels Copy: Aesthetic formatting, call to action
    ig_caption = (
        f"{clip_title} 🔥\n\n"
        f"\"{hook}\"\n\n"
        f"Save this for later 📌 and share with someone who needs to see this!\n\n"
        + " ".join(all_hashtags[:10] + PLATFORM_SPECIFIC_TAGS["instagram"])
    )

    return {
        "clip_id": clip.get('id'),
        "recommended_title": clip_title,
        "hook": hook,
        "tiktok": {
            "title": tiktok_title,
            "caption": tiktok_caption,
            "hashtags": " ".join(all_hashtags[:8])
        },
        "youtube": {
            "title": yt_title,
            "description": yt_description,
            "hashtags": " ".join(all_hashtags[:6])
        },
        "instagram": {
            "caption": ig_caption,
            "hashtags": " ".join(all_hashtags[:10])
        },
        "tags": tags,
        "file": clip.get('file'),
        "srt_file": clip.get('srt_file')
    }
