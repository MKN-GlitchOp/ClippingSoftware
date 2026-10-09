"""Explainable streamer cues. These are editorial hints, not laughter recognition."""
import re
from collections import Counter

CREATORS = re.compile(r'\b(?:ishowspeed|i show speed|kai cenat|fanum|duke dennis|agent\s*00|adin ross|jynxzi|caseoh|case oh|xqc|ludwig|jerma|sodapoppin|pokimane|valkyrae|faze|stable ronaldo|lacy|plaqueboymax|jasontheween|smii7y|shroud|timthetatman|drdisrespect|ninja|streamers?|twitch)\b', re.I)
FUNNY = re.compile(r'\b(?:funny|funniest|hilarious|laugh\w*|jok\w*|prank\w*|troll\w*|roast\w*|fails?|failed|rage\w*|scared|scream\w*|jumpscare|awkward|embarrass\w*|unexpected|fell for|does not listen|can.t stop|loses it|lost it|crash(?:es|ed)? out)\b|[😂🤣💀]', re.I)
REACTION = re.compile(r'\b(?:oh (?:my god|my gosh|shit)|no (?:way|shot)|what the (?:hell|heck|fuck)|wait what|are you (?:kidding|serious)|i can.t believe|i cannot believe|you.re (?:kidding|trolling)|clip (?:that|this)|i.m (?:dead|crying)|ain.t no way)\b', re.I)
LAUGHTER = re.compile(r'\b(?:ha(?:ha)+|laugh(?:s|ing|ter)|hilarious|can.t (?:stop laughing|breathe)|i.m (?:dead|crying)|that was funny)\b', re.I)
PAYOFF = re.compile(r'\b(?:got (?:you|him|her|me)|fell for|roasted|pranked|trolled|skill issue|you (?:missed|lost|died)|i (?:missed|lost|died)|it was (?:a joke|me)|just kidding|look at (?:his|her|your) face)\b', re.I)
SETUP = re.compile(r'\b(?:watch this|bet (?:you|i)|i bet|try (?:this|to)|let.s (?:see|try)|can you|don.t (?:look|move|laugh)|if (?:you|i)|i dare|challenge|prank|pretend)\b', re.I)

MOMENTS = {
    'reactions': ('Unexpected reactions', r'\b(?:react\w*|unexpected|shocked|loses it|lost it|does not listen)\b', 'funny streamer reactions'),
    'banter': ('Roasts & banter', r'\b(?:roast\w*|banter|troll\w*|prank\w*|fell for|jok\w*)\b', 'streamer funny roast prank'),
    'fails': ('Fails & rage', r'\b(?:fails?|failed|rage\w*|crash\w*|missed|loses|lost)\b', 'streamer funny fails rage'),
    'scares': ('Scares & screams', r'\b(?:scare\w*|scream\w*|horror|jumpscare\w*)\b', 'streamer funny jumpscare'),
    'irl': ('IRL moments', r'\b(?:irl|outside|public|fan meets|meets a fan|street|store)\b', 'streamer funny IRL moments'),
    'funny': ('Funny moments', '', 'funniest streamer moments'),
}


def public_moment(title, channel=''):
    """Require streamer identity AND a humor cue; never infer relevance from query."""
    if not CREATORS.search(title+' '+channel) or not FUNNY.search(title):
        return None
    for key, (_, pattern, _) in MOMENTS.items():
        if pattern and re.search(pattern, title, re.I):
            return key
    return 'funny'


def event(unit):
    text = unit['text']
    return bool(REACTION.search(text) or LAUGHTER.search(text) or PAYOFF.search(text))


def refine_moment(units, i, j, breakdown, cautions):
    """Favor setup -> reaction, avoid isolated shouting and dragging past a payoff."""
    passage = units[i:j+1]
    first, last = passage[0], passage[-1]
    tokens = re.findall(r'\w+', ' '.join(u['text'] for u in passage).lower())
    lines = Counter(re.sub(r'\W+', ' ',u['text'].lower()).strip() for u in passage)
    repeated_words = sum((count-1)*len(line.split()) for line,count in lines.items())
    if len(tokens) >= 12 and (len(set(tokens))/len(tokens) < .35 or repeated_words/len(tokens) > .25):
        breakdown['Repetitive shouting'] = -14
        cautions.append('Repeated words dominate this range')
    anchors = [k for k in range(i,j+1) if event(units[k])]
    result = dict(kind='Review moment', anchor=None, setup=False, confidence='Transcript cues only')
    if not anchors:
        breakdown['No clear reaction or punchline'] = -24
        cautions.append('No clear reaction or punchline in the transcript; inspect the visuals')
        return result
    anchor = anchors[0]
    before = units[i:anchor]
    setup = any(len(u['text'].split()) >= 5 and not event(u) for u in before)
    # An explicit challenge and reaction may share one Whisper sentence.
    setup = setup or bool(SETUP.search(units[anchor]['text']) and len(units[anchor]['text'].split()) >= 8)
    result.update(kind='Setup + reaction' if setup else 'Reaction to review',
                  anchor=round(units[anchor]['start'],3), setup=setup)
    breakdown['Reaction or punchline evidence'] = 8
    if setup:
        breakdown['Setup before reaction'] = 12
    else:
        breakdown['Reaction missing setup'] = -15
        cautions.append('Reaction starts without a clear spoken setup; check visual context')
    delay = units[anchor]['start']-first['start']
    if delay > 12:
        breakdown['Long lead-in to reaction'] = -min(18, round((delay-12)*1.2))
    tail = last['end']-units[anchors[-1]]['end']
    if tail > 5:
        breakdown['Drifts after reaction'] = -min(18,round((tail-5)*1.5))
    if event(last):
        # "No way!" can be the natural ending of a joke, not an unfinished thought.
        breakdown.pop('Unresolved ending',None)
        if 'Final line may introduce another idea' in cautions:
            cautions.remove('Final line may introduce another idea')
    if j+1 < len(units) and units[j+1]['start']-last['end'] <= 1.5 and event(units[j+1]):
        breakdown['Cuts before follow-up reaction'] = -18
        cautions.append('A follow-up reaction starts immediately after this range')
    if anchor == i and i > 0 and units[i]['start']-units[i-1]['end'] <= 2.5:
        breakdown['Earlier setup available'] = -8
    return result
