"""two-dragons-episode / narrate.py: the episode's narration track, read by Kokoro's bm_george at normal speed.

Reads script.txt (24 lines), writes $WORK/vo/vo_raw.wav (48 kHz mono, 173.06 s) and $WORK/vo/timeline.json
({"total": s, "lines": [{"i", "start", "end", "text"}]}), which the edit, the score and the mix are cut to.

Settings below are the shipped ones. Model files: KOKORO_DIR, else ../wildlore-narrator/models, else
/home/claude/models/kokoro (python ../wildlore-narrator/get_models.py or ./setup.sh animal-docs fetches them).
"""
import os, sys, json
import numpy as np, soundfile as sf
import scipy.signal as ss

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.environ.get("TWO_DRAGONS_WORK") or os.path.join(HERE, "build")
VOICE, LANG, SPEED = "bm_george", "en-gb", 1.0
PREFIX = "... "            # without it Kokoro sometimes swallows a line's first word
TEXT_FIX = {16: ("mist-covered", "mist covered")}   # the hyphenated form was read as one smeared word
TRIM_THR, TRIM_PAD = 0.0015, 0.08
SILENCE_CAP = 0.32         # pauses inside a line longer than this are shortened to it
PAUSE_AFTER = [0.35, 0.7, 0.35, 0.8, 0.4, 0.3, 0.9, 0.4, 0.4, 0.3, 0.4, 0.45, 0.3, 0.8, 0.35, 0.4, 0.7, 0.35, 0.7, 0.4, 0.35, 0.5, 0.4, 0.0]
INTRO, OUTRO = 1.0, 3.2
SR = 48000


def kokoro_dir():
    for d in (os.environ.get("KOKORO_DIR"), os.path.join(HERE, "..", "wildlore-narrator", "models"), "/home/claude/models/kokoro"):
        if d and os.path.exists(os.path.join(d, "kokoro-v1.0.onnx")):
            return d
    raise SystemExit("Kokoro model not found: python ../wildlore-narrator/get_models.py, or set KOKORO_DIR")


def trim(a, sr, thr=TRIM_THR):
    idx = np.where(np.abs(a) > thr)[0]
    s = max(0, idx[0] - int(TRIM_PAD * sr)); e = min(len(a), idx[-1] + int(TRIM_PAD * sr))
    out = a[s:e].copy(); f = int(0.01 * sr)
    out[:f] *= np.linspace(0, 1, f); out[-f:] *= np.linspace(1, 0, f)
    return out


def compress_silence(a, sr, cap, thr_db=-42.0, win=0.01):
    hop = int(sr * win); n = len(a) // hop
    env = np.array([np.sqrt(np.mean(a[i * hop:(i + 1) * hop] ** 2) + 1e-12) for i in range(n)])
    quiet = 20 * np.log10(env + 1e-9) < thr_db
    keep = np.ones(len(a), bool); i = 0
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]:
                j += 1
            dur = (j - i) * win
            if dur > cap and i > 0 and j < n:
                excess = int((dur - cap) * sr); mid = (i * hop + j * hop) // 2
                keep[mid - excess // 2: mid - excess // 2 + excess] = False
            i = j
        else:
            i += 1
    return a[keep]


def main():
    from kokoro_onnx import Kokoro
    lines = [l.strip() for l in open(os.path.join(HERE, "script.txt"), encoding="utf-8") if l.strip()]
    assert len(lines) == len(PAUSE_AFTER), "one PAUSE_AFTER entry per script line"
    d = kokoro_dir()
    k = Kokoro(os.path.join(d, "kokoro-v1.0.onnx"), os.path.join(d, "voices-v1.0.bin"))
    segs = []
    for i, t in enumerate(lines):
        if i in TEXT_FIX:
            t = t.replace(*TEXT_FIX[i])
        a, sr = k.create(PREFIX + t, voice=VOICE, speed=SPEED, lang=LANG)
        a = compress_silence(trim(a, sr), sr, SILENCE_CAP)
        segs.append(ss.resample_poly(a, 2, 1).astype(np.float32))      # 24 kHz -> 48 kHz
        print("line %02d %.2f s" % (i, len(segs[-1]) / SR), flush=True)
    total = INTRO + sum(len(a) / SR for a in segs) + sum(PAUSE_AFTER) + OUTRO
    vo = np.zeros(int(total * SR) + SR, np.float32)
    t = INTRO; timeline = []
    for i, a in enumerate(segs):
        s0 = int(round(t * SR)); vo[s0:s0 + len(a)] += a
        timeline.append({"i": i, "start": round(t, 3), "end": round(t + len(a) / SR, 3), "text": lines[i]})
        t += len(a) / SR + PAUSE_AFTER[i]
    out = os.path.join(WORK, "vo"); os.makedirs(out, exist_ok=True)
    sf.write(os.path.join(out, "vo_raw.wav"), vo[:int(total * SR)], SR)
    json.dump({"total": round(total, 3), "lines": timeline}, open(os.path.join(out, "timeline.json"), "w"), indent=1)
    print("total runtime %.2f s -> %s" % (total, out))


if __name__ == "__main__":
    main()
