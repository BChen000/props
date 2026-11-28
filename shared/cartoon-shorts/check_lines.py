"""check_lines: is every spoken line of a motivational Short heard right? Offline speech recognition (Whisper small.en
int8, from ../narration-check) transcribes each narrator, shadow, old-man and storyteller line where it falls in the mix, under the
music and sound effects, and compares it word for word with the script.

  python check_lines.py five_more_minutes        mixes only the soundtrack (no picture) into build/<name>_check/ and
                                                 checks every line; exits 1 if any line is misheard
  python check_lines.py five_more_minutes --mp4  checks the finished build/<name>/<name>.mp4 instead
                                                 (add --style stick for build/<name>_stick/)
  python check_lines.py --try "nar:Five minutes | become | hours." "sha:you'll never change." "old:Don't be scared, | kid."
                                                 speaks candidate lines on their own (no music) and transcribes them

Fix a misheard line by rewording it (plainer words, a stressed last word, one more word of context) or by clearing the
sound under it, then run this again. Settings: PAD_IN before and PAD_OUT after each line, in seconds.
"""
import argparse
import importlib
import json
import os
import re
import subprocess
import sys

import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'episodes'))
sys.path.insert(0, os.path.join(HERE, '..', 'narration-check'))
import motivation as m  # noqa: E402
from asr import transcribe  # noqa: E402
from check import norm, wer  # noqa: E402

PAD_IN, PAD_OUT = 0.15, 0.25
SPOKEN = ('nar', 'sha', 'old', 'story')
ONES = ('zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen '
        'eighteen nineteen').split()
TENS = 'twenty thirty forty fifty sixty seventy eighty ninety'.split()
SOUND_ALIKE = {'too': 'to', 'two': 'to', 'their': 'there', "they're": 'there', "it's": 'its', "you're": 'your',
               'know': 'no', 'won': 'one', 'here': 'hear', 'write': 'right'}   # a listener can't tell these apart


def spell(n):
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS[n // 10 - 2] + ('' if n % 10 == 0 else ' ' + ONES[n % 10])
    if n < 1000:
        return ONES[n // 100] + ' hundred' + ('' if n % 100 == 0 else ' ' + spell(n % 100))
    if n < 1000000:
        return spell(n // 1000) + ' thousand' + ('' if n % 1000 == 0 else ' ' + spell(n % 1000))
    return str(n)


def words(s):
    """Words as a listener hears them: numbers spelled out (50 = fifty, 1% = one percent) and sound-alikes merged."""
    s = re.sub(r'(?<=\d),(?=\d{3})', '', s).replace('%', ' percent ')
    s = re.sub(r'\d+', lambda g: ' ' + spell(int(g.group())) + ' ', s)
    return [SOUND_ALIKE.get(w, w) for w in norm(s)]


def report(tl, wav):
    bad = 0
    for ln in tl['lines']:
        if ln['v'] not in SPOKEN:
            continue
        txt = m.plain(ln['text'])
        hyp = transcribe(wav, max(0.0, ln['start'] - PAD_IN), ln['end'] + PAD_OUT)
        e = wer(words(txt), words(hyp))
        bad += e > 0
        print(f"{ln['start']:6.2f} {ln['v']:3s} {'ok   ' if not e else 'CHECK'} {txt}" + (f"   heard: {hyp}" if e else ''),
              flush=True)
    print('every line heard right' if not bad else f'{bad} line(s) misheard')
    return 1 if bad else 0


def try_lines(items):
    out = os.path.join(HERE, 'build', '_try')
    os.makedirs(out, exist_ok=True)
    script = []
    for it in items:
        v, _, s = it.partition(':')
        if v not in m.VOICES or not s.strip():
            raise SystemExit(f'"{it}": write voice:text with voice one of {", ".join(m.VOICES)}')
        script.append(dict(scene='a', v=v, text=s.strip(), pre=0.6))
    tl, segs = m.timeline(script, out)
    wav = os.path.join(out, 'voices.wav')
    sf.write(wav, sum(m.voice_tracks(tl, segs, out).values()), m.SR)
    return report(tl, wav)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('episode', nargs='?')
    ap.add_argument('--mp4', action='store_true', help='check the finished video instead of a fresh soundtrack')
    ap.add_argument('--style', default='lit', choices=['lit', 'stick'])
    ap.add_argument('--try', dest='try_', nargs='+', metavar='VOICE:TEXT')
    a = ap.parse_args()
    if a.try_:
        return try_lines(a.try_)
    if not a.episode:
        ap.error('give an episode name or --try')
    ep = importlib.import_module(a.episode)
    if a.mp4:
        name = ep.NAME + ('' if a.style == 'lit' else '_' + a.style)
        d = os.path.join(HERE, 'build', name)
        mp4 = os.path.join(d, name + '.mp4')
        if not os.path.exists(mp4):
            raise SystemExit(f'{mp4} is missing: run python make_short.py {a.episode}' +
                             ('' if a.style == 'lit' else f' --style {a.style}'))
        wav = os.path.join(d, 'check16k.wav')
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', mp4, '-vn', '-ac', '1', '-ar', '16000', wav], check=True)
        tl = json.load(open(os.path.join(d, 'timeline.json')))
    else:
        out = os.path.join(HERE, 'build', ep.NAME + '_check')
        os.makedirs(out, exist_ok=True)
        tl, segs = m.timeline(ep.SCRIPT, out)
        wav = m.soundtrack(tl, segs, ep.SCORE, getattr(ep, 'SFX', None), out)
    return report(tl, wav)


if __name__ == '__main__':
    sys.exit(main())
