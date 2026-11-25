"""storytime-narrator: the Story Time with Kenji voice, a calm American male narrator made offline with Kokoro v1.0.

Kokoro's am_michael voice in en-us at speed 1.0, from the int8 ONNX model. Each caption line is spoken on its own,
trimmed to 15 ms around its sound, and laid end to end with pauses that follow the punctuation, so one caption is
on screen per spoken line. The result is one narration WAV and a timeline JSON that the storytime-kit renderer
and the storytime-music mixer both read.

  python narrate.py ../the-locksmith/story.py          -> out/<name>/narration.wav, timeline.json, lines/*.wav
  python narrate.py ../the-hero/story.py --out build   -> build/narration.wav ...
  python narrate.py --say "He never stole a thing."    -> out/say.wav, to audition one line
  python narrate.py ../the-locksmith/story.py --preview  -> also redraws preview.png

A story is a dict: name, hook (two strings) and lines, each (scene, caption) or (scene, caption, text_to_speak).
Get the model once with `python get_models.py`.
"""
import argparse
import hashlib
import importlib.util
import json
import os

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------- settings
VOICE, SPEED, LANG = 'am_michael', 1.0, 'en-us'
MODEL, VOICES_BIN = 'kokoro-v1.0.int8.onnx', 'voices-v1.0.bin'
LEAD_IN = 0.15                   # silence before the first line, seconds
GAP_LAST = 1.8                   # after the last line (the end fade lives here)
GAP_ELLIPSIS = 0.6               # after a caption ending in "..."
GAP_SHORT_SENTENCE = 0.56        # after a sentence of 1-2 words ("Labeled.", "Filed.")
GAP_SENTENCE = 0.42              # after any other . ? !
GAP_CLAUSE = 0.13                # after a caption that runs on into the next one
TRIM_REL, TRIM_MARGIN = 0.02, 0.015   # trim below 2 % of the line's peak, keep 15 ms either side


def model_dir():
    for d in (os.environ.get('KOKORO_DIR', ''), os.path.join(HERE, 'models'), '/home/claude/models/kokoro'):
        if d and os.path.exists(os.path.join(d, MODEL)) and os.path.exists(os.path.join(d, VOICES_BIN)):
            return d
    raise SystemExit(f'{MODEL} not found: run python get_models.py (or set KOKORO_DIR)')


def load():
    from kokoro_onnx import Kokoro
    d = model_dir()
    return Kokoro(os.path.join(d, MODEL), os.path.join(d, VOICES_BIN))


def trim(a, sr):
    env = np.abs(a)
    thr = max(env.max() * TRIM_REL, 1e-4)
    idx = np.nonzero(env > thr)[0]
    if len(idx) == 0:
        return a
    m = int(TRIM_MARGIN * sr)
    return a[max(idx[0] - m, 0):min(idx[-1] + m, len(a))]


def gap_after(cap, last):
    if last:
        return GAP_LAST
    s = cap.rstrip('”"').rstrip()
    if s.endswith('...'):
        return GAP_ELLIPSIS
    if s.endswith('.') or s.endswith('?') or s.endswith('!'):
        return GAP_SHORT_SENTENCE if len(s.split()) <= 2 else GAP_SENTENCE
    return GAP_CLAUSE


def spoken(line):
    """What Kokoro reads for a line: the third field if given ("five a.m." for "5 a.m."), curly quotes removed, and a
    comma added after a bare last word so Kokoro ends the clause on a falling, unfinished note instead of a full stop."""
    txt = line[2] if len(line) > 2 else line[1]
    txt = txt.replace('“', '').replace('”', '')
    if txt[-1].isalnum():
        txt += ','
    return txt


def speak(k, text):
    a, sr = k.create(text, voice=VOICE, speed=SPEED, lang=LANG)
    return trim(np.asarray(a, dtype=np.float32), sr), sr


def narrate(story, out_dir, k=None, log=print):
    """Speaks every line (reusing out_dir/lines/ when the text and voice settings match) and writes
    out_dir/narration.wav (24 kHz mono, 16-bit) and out_dir/timeline.json. Returns the timeline dict."""
    os.makedirs(os.path.join(out_dir, 'lines'), exist_ok=True)
    lines = story['lines']
    sr = 24000
    parts, timeline, t = [np.zeros(int(LEAD_IN * sr))], [], LEAD_IN
    for i, ln in enumerate(lines):
        scene, cap = ln[0], ln[1]
        txt = spoken(ln)
        tag = hashlib.sha1(f'{txt}|{VOICE}|{SPEED}|{LANG}|{MODEL}'.encode()).hexdigest()[:8]
        cache = os.path.join(out_dir, 'lines', f'{i:02d}_{tag}.wav')
        if os.path.exists(cache):
            a, sr = sf.read(cache)
        else:
            if k is None:
                k = load()
            a, sr = speak(k, txt)
            sf.write(cache, a, sr)
        d = len(a) / sr
        g = gap_after(cap, i == len(lines) - 1)
        timeline.append({'i': i, 'scene': scene, 'text': cap, 'start': round(t, 3), 'end': round(t + d, 3)})
        parts += [a, np.zeros(int(g * sr))]
        t += d + g
        log(f'{i:2d} {d:5.2f}s  {cap}')
    full = np.concatenate(parts).astype(np.float32)
    sf.write(os.path.join(out_dir, 'narration.wav'), full, sr)
    tl = {'duration': round(len(full) / sr, 3), 'lines': timeline, 'hook': story['hook'], 'name': story['name']}
    json.dump(tl, open(os.path.join(out_dir, 'timeline.json'), 'w'), indent=1)
    log(f'TOTAL {len(full) / sr:.2f} s')
    return tl


def preview(out_dir, path, secs=20.0, rows=5):
    """The first `secs` seconds of a narration as waveform rows, each line labelled with its caption."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    tl = json.load(open(os.path.join(out_dir, 'timeline.json')))
    x, sr = sf.read(os.path.join(out_dir, 'narration.wav'))
    per = secs / rows
    fig, axs = plt.subplots(rows, 1, figsize=(7.2, 12.8), dpi=100)
    fig.patch.set_facecolor('#14161C')
    for r, ax in enumerate(axs):
        a, b = r * per, (r + 1) * per
        seg = x[int(a * sr):int(b * sr)]
        ax.set_facecolor('#1E2027')
        ax.plot(np.arange(len(seg)) / sr + a, seg, color='#8FA3B8', lw=0.4)
        for ln in tl['lines']:
            if ln['end'] > a and ln['start'] < b:
                s0, s1 = max(ln['start'], a), min(ln['end'], b)
                ax.axvspan(s0, s1, color='#F4C542', alpha=0.10)
                if ln['start'] >= a:
                    ax.text(ln['start'] + 0.03, 0.93, ln['text'], color='#F4C542', fontsize=8.5, va='top', rotation=0, clip_on=True)
        ax.set_xlim(a, b)
        ax.set_ylim(-1, 1)
        ax.set_yticks([])
        ax.tick_params(colors='#C9CED6', labelsize=8)
        for sp in ax.spines.values():
            sp.set_color('#3A3F4B')
    axs[0].set_title(f'{tl["name"]}: first {secs:.0f} s, one caption per spoken line', color='white', fontsize=12, loc='left')
    axs[-1].set_xlabel('seconds', color='#C9CED6')
    fig.tight_layout()
    fig.savefig(path, facecolor=fig.get_facecolor())
    return path


def load_story(path):
    spec = importlib.util.spec_from_file_location('story', path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.STORY


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('story', nargs='?', help='a story.py with a STORY dict')
    ap.add_argument('--out', default=None, help='output folder (default out/<story name>)')
    ap.add_argument('--say', default=None, help='speak one line to out/say.wav')
    ap.add_argument('--preview', action='store_true', help='also redraw preview.png from this narration')
    a = ap.parse_args()
    if a.say:
        os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
        s, sr = speak(load(), spoken(('', a.say)))
        sf.write(os.path.join(HERE, 'out', 'say.wav'), s, sr)
        print(round(len(s) / sr, 2), 's ->', os.path.join(HERE, 'out', 'say.wav'))
        return
    if not a.story:
        ap.error('give a story.py or --say')
    st = load_story(a.story)
    out = a.out or os.path.join(HERE, 'out', st['name'])
    narrate(st, out)
    if a.preview:
        print('wrote', preview(out, os.path.join(HERE, 'preview.png')))


if __name__ == '__main__':
    main()
