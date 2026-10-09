"""Local editorial proxies, not predictions of a platform's private algorithm."""
import math
import re

PROFILES = {
    'streamer': ('Funny streamer moments', r'\b(?:chat|streamer|twitch|stream snip\w*|clip that|clip this|ishowspeed|kai cenat|faze|no shot)\b'),
    'gaming': ('Gaming & reactions', r'\b(?:game|gaming|round|clutch|respawn|teammate|kill|boss|lobby|match|no scope)\b'),
    'education': ('Education & how-to', r'\b(?:research|learn|science|explain|technique|step|tutorial|evidence|study|solution)\b'),
    'podcast': ('Podcast & opinion', r'\b(?:interview|opinion|believe|agree|disagree|experience|conversation|perspective)\b'),
    'story': ('Stories & comedy', r'\b(?:joke|laugh|hilarious|suddenly|finally|realized|ended up|one time|story)\b'),
}


def choose_profile(text, requested='auto'):
    if requested in PROFILES:
        return requested
    counts = {key: len(re.findall(pattern, text, re.I)) for key, (_, pattern) in PROFILES.items()}
    winner = max(counts, key=counts.get)
    return winner if counts[winner] >= 2 else 'balanced'


def replay_evidence(heatmap, start, end):
    """Only reward above-baseline public replay interest, weighted by covered time."""
    rows = []
    for row in heatmap or []:
        try:
            a, b, v = (float(row[key]) for key in ('start_time', 'end_time', 'value'))
            if all(math.isfinite(x) for x in (a, b, v)) and b > a and 0 <= v <= 1:
                rows.append((a, b, v))
        except (KeyError, TypeError, ValueError):
            continue
    total = sum(b-a for a, b, _ in rows)
    covered = sum(max(0, min(end, b)-max(start, a)) for a, b, _ in rows)
    if not total or covered < (end-start)*.5:
        return None
    baseline = sum((b-a)*v for a, b, v in rows)/total
    interest = sum(max(0, min(end, b)-max(start, a))*v for a, b, v in rows)/covered
    return dict(relative_interest=round(interest, 3), baseline=round(baseline, 3),
                bonus=min(8, max(0, round((interest-baseline)*16))))


def refine_score(units, breakdown, cautions, profile, heatmap):
    text = ' '.join(u['text'] for u in units)
    first = units[0]
    # The first three seconds matter; a hook at the end of a long sentence is late.
    opening = ' '.join(first['text'].split()[:max(3, round(len(first['text'].split())*min(1, 3/max(.1, first['end']-first['start']))))])
    slow = bool(re.match(r'^(?:um|uh|okay so|all right so|before (?:we|i)|let me (?:just|start)|as (?:i|we) (?:said|mentioned))\b', re.sub(r'[,;:]', '', opening), re.I))
    hook_pattern = r'\b(?:why|how|secret|mistake|imagine|never|wait|no way|what if|watch this|turns out|here.s)\b'
    hook = bool(re.search(hook_pattern, opening, re.I))
    breakdown['Immediate hook'] = 5 if hook else 0
    if slow:
        breakdown['Slow opening'] = -8
        cautions.append('Trim the setup: opening spends time before the point')
    elif breakdown.get('Opening hook', 0) and not hook:
        breakdown['Delayed hook'] = -4
    # Capped profile fit: avoids stacking slang/volume until everything scores 100.
    relevant = {
        'streamer': ['Humor or entertainment', 'Surprise or tension', 'Story payoff'],
        'gaming': ['Humor or entertainment', 'Surprise or tension', 'Story payoff'],
        'education': ['Useful information', 'Direct viewer engagement', 'Story payoff'],
        'podcast': ['Emotion or opinion', 'Useful information', 'Story payoff'],
        'story': ['Humor or entertainment', 'Story payoff', 'Surprise or tension'],
    }.get(profile, [])
    breakdown['Content fit'] = min(9, sum(3 for key in relevant if breakdown.get(key, 0) > 0))
    audio_keys = ['High vocal energy', 'Climactic reaction / punchline', 'High-energy opening hook']
    cap = 6 if profile == 'streamer' else 10 if profile in ('gaming', 'story') else 4
    audio_total = sum(max(0, breakdown.get(key, 0)) for key in audio_keys)
    if audio_total > cap:
        breakdown['Audio evidence cap'] = cap-audio_total
    payoff = breakdown.get('Story payoff', 0) > 0
    if profile in ('gaming', 'story') and not payoff:
        cautions.append('Check that the reaction has its setup and payoff')
    replay = replay_evidence(heatmap, first['start'], units[-1]['end'])
    if replay:
        breakdown['Public replay interest'] = replay['bonus']
    label = PROFILES.get(profile, ('Balanced', ''))[0]
    return dict(profile=profile, label=label,
                opening='Immediate hook' if hook and not slow else 'Review opening',
                payoff='Payoff language found' if payoff else 'Review ending',
                evidence='Public YouTube replay data + local analysis' if replay else 'Local transcript and audio analysis',
                replay=replay)
