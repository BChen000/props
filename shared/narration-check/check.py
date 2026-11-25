"""narration-check / check.py: does the narration say exactly the script, and where does each phrase fall?

  python check.py words  script.txt narration.wav --timeline timeline.json   one long file + line times
  python check.py words  script.txt lines/                                   a folder of line_00.wav, line_01.wav, ...
  python check.py phrases narration.wav --timeline timeline.json [--fps 24]  split lines at pauses -> out/phrases.json
  python check.py say    clip.wav [t0 t1]                                    just transcribe

script.txt has one narration line per row (blank rows are skipped). timeline.json is {"lines": [{"start": s, "end": s},
...]} in seconds, one entry per script line, like ../../animal-docs/two-dragons-episode/narrate.py writes; extra keys are
ignored. `words` prints each line's word errors next to what was heard and exits 1 if any line is wrong.

Settings: PAD = 0.05 s around each line; pauses for `phrases` are runs of 10 ms windows below SIL_DB = -45 dBFS lasting
at least MIN_PAUSE = 0.12 s. Overridable with --pad, --sil-db, --min-pause.
"""
import argparse
import glob
import json
import os
import re
import sys

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from asr import transcribe  # noqa: E402

PAD, SIL_DB, MIN_PAUSE = 0.05, -45.0, 0.12
NUM = {str(i): w for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                        "fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}


def norm(s):
    """Words for comparison. Applied to script and transcript alike, so British and American spellings meet
    (colour/color, specialised/specialized, armoured/armored) and Whisper's digits match spelled-out numbers."""
    s = s.lower().replace("-", " ").replace("’", "'")
    s = re.sub(r"(\d+)", lambda m: " " + NUM.get(m.group(1), m.group(1)) + " ", s)
    s = re.sub(r"[^a-z' ]", " ", s)
    out = []
    for w in s.split():
        w = w.strip("'")
        w = re.sub(r"is(e|ed|es|ing|ation|ations)$", r"iz\1", w)
        w = re.sub(r"(?<=[a-z])our(?=[a-z]|$)", "or", w)
        if w:
            out.append(w)
    return out


def wer(r, h):
    d = [[0] * (len(h) + 1) for _ in range(len(r) + 1)]
    for i in range(len(r) + 1):
        d[i][0] = i
    for j in range(len(h) + 1):
        d[0][j] = j
    for i in range(1, len(r) + 1):
        for j in range(1, len(h) + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (r[i - 1] != h[j - 1]))
    return d[-1][-1]


def read_script(p):
    return [l.strip() for l in open(p, encoding="utf-8") if l.strip()]


def read_timeline(p, n):
    tl = json.load(open(p))
    lines = tl["lines"] if isinstance(tl, dict) else tl
    if len(lines) != n:
        raise SystemExit("timeline has %d lines, script has %d" % (len(lines), n))
    return [(float(m["start"]), float(m["end"])) for m in lines]


def cmd_words(a):
    script = read_script(a.script)
    if os.path.isdir(a.audio):
        files = sorted(glob.glob(os.path.join(a.audio, "line_*.wav")))
        if len(files) != len(script):
            raise SystemExit("%d line files for %d script lines" % (len(files), len(script)))
        jobs = [(f, None, None) for f in files]
    else:
        if not a.timeline:
            raise SystemExit("a single file needs --timeline")
        jobs = [(a.audio, max(0.0, s - a.pad), e + a.pad) for s, e in read_timeline(a.timeline, len(script))]
    errs = tot = 0
    bad = []
    for i, (text, (path, t0, t1)) in enumerate(zip(script, jobs)):
        hyp = transcribe(path, t0, t1)
        r, h = norm(text), norm(hyp)
        e = wer(r, h)
        errs += e; tot += len(r)
        dur = (t1 - t0 - 2 * a.pad) if t0 is not None else sf.info(path).duration
        wpm = 60.0 * len(r) / max(dur, 1e-6)
        print("%02d %5.2f s %4.0f wpm  errs=%d%s" % (i, dur, wpm, e, ("   heard: " + hyp) if e else ""), flush=True)
        if e:
            bad.append(i)
    print("WER %.3f over %d words; lines with errors: %s" % (errs / max(tot, 1), tot, bad or "none"))
    return 1 if bad else 0


def pauses(seg, sr, t_start, sil_db, min_pause):
    hop = int(0.01 * sr)
    n = len(seg) // hop
    db = np.array([20 * np.log10(np.sqrt(np.mean(seg[k * hop:(k + 1) * hop] ** 2)) + 1e-9) for k in range(n)])
    q = db < sil_db
    out = []
    k = 0
    while k < n:
        if q[k]:
            j = k
            while j < n and q[j]:
                j += 1
            if j - k >= int(round(min_pause / 0.01)) and k > 3 and j < n - 3:
                out.append((t_start + k * 0.01, t_start + j * 0.01))
            k = j
        else:
            k += 1
    return out


def cmd_phrases(a):
    y, sr = sf.read(a.audio, dtype="float32", always_2d=True)
    y = y.mean(axis=1)
    tl = json.load(open(a.timeline))
    lines = tl["lines"] if isinstance(tl, dict) else tl
    res = []
    for i, m in enumerate(lines):
        s, e = float(m["start"]), float(m["end"])
        cuts = pauses(y[int(s * sr):int(e * sr)], sr, s, a.sil_db, a.min_pause)
        bounds = [s] + [c for g in cuts for c in g] + [e]
        for k in range(0, len(bounds), 2):
            p0, p1 = bounds[k], bounds[k + 1]
            txt = transcribe(a.audio, p0 - 0.02, p1 + 0.02)
            res.append({"line": i, "s": round(p0, 2), "e": round(p1, 2),
                        "f0": int(round(p0 * a.fps)), "f1": int(round(p1 * a.fps)), "txt": txt})
            print("%02d %7.2f-%7.2f  f%5d-%5d  %s" % (i, p0, p1, res[-1]["f0"], res[-1]["f1"], txt), flush=True)
    out = a.out or os.path.join(HERE, "out", "phrases.json")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump(res, open(out, "w"), indent=1)
    print("wrote", out)
    return 0


def cmd_say(a):
    t0, t1 = (float(a.t0), float(a.t1)) if a.t0 is not None else (None, None)
    print(transcribe(a.audio, t0, t1))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("words"); w.add_argument("script"); w.add_argument("audio"); w.add_argument("--timeline")
    w.add_argument("--pad", type=float, default=PAD)
    p = sub.add_parser("phrases"); p.add_argument("audio"); p.add_argument("--timeline", required=True)
    p.add_argument("--fps", type=float, default=24.0); p.add_argument("--out")
    p.add_argument("--sil-db", type=float, default=SIL_DB); p.add_argument("--min-pause", type=float, default=MIN_PAUSE)
    s = sub.add_parser("say"); s.add_argument("audio"); s.add_argument("t0", nargs="?"); s.add_argument("t1", nargs="?")
    a = ap.parse_args()
    return {"words": cmd_words, "phrases": cmd_phrases, "say": cmd_say}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
