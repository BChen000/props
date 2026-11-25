#!/usr/bin/env python3
"""Checks a finished long-form: stream lengths, a full decode, loudness and true peak, and audio sync per round.

Sync: each round's source audio (0.5 s from its first note, or from 1 s in for the other games) is cross-correlated
with the finished mix around where build/plan.json put it, so the offset is measured to the sample.

python3 check.py                  # build/<OUT_NAME>
python3 check.py --no-decode      # skip the full decode (about 1 min)
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import settings as S  # noqa: E402

SR = 16000
SEARCH_S = 0.3


def pcm(path, start=None, dur=None):
    cmd = ["ffmpeg", "-v", "error"]
    if start is not None:
        cmd += ["-ss", f"{start:.4f}", "-t", f"{dur:.4f}"]
    cmd += ["-i", path, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.check_output(cmd), np.float32)


def streams(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,duration,nb_frames",
                                   "-of", "json", path])
    return {s["codec_type"]: s for s in json.loads(out)["streams"]}


def loudness(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-vn", "-af", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True)
    txt = r.stderr[r.stderr.rfind("Summary:"):]
    get = lambda pat: float(re.search(pat, txt, re.S).group(1))  # noqa: E731
    return get(r"I:\s+(-?[\d.]+) LUFS"), get(r"LRA:\s+([\d.]+) LU"), get(r"True peak:.*?Peak:\s+(-?[\d.]+) dBFS")


def offset_ms(mix, it):
    """Where the round's source audio really sits in the mix, minus where the plan put it."""
    ts = it["ts_f"] / S.FPS
    anchor = it.get("f0", ts + 1.0) if it["kind"] in ("song", "bonus") else ts + 1.0
    if anchor - ts < 0.2:                                              # no lead-in to match against (speed round)
        anchor = ts + 1.0
    ref = pcm(it["path"], anchor - 0.02, 0.5)
    planned = it["start"] / S.FPS + (anchor - ts) - 0.02          # start is in frames; no speed-up before the anchor
    a = int((planned - SEARCH_S) * SR)
    seg = mix[a:a + len(ref) + int(2 * SEARCH_S * SR)]
    c = np.correlate(seg, ref, "valid")
    norm = np.sqrt(np.convolve(seg ** 2, np.ones(len(ref)), "valid")) * np.linalg.norm(ref) + 1e-9
    k = int(np.argmax(c / norm))
    return (k - SEARCH_S * SR) / SR * 1000, float((c / norm)[k])


def main():
    out = os.path.join(S.BUILD, S.OUT_NAME)
    st = streams(out)
    v, a = float(st["video"]["duration"]), float(st["audio"]["duration"])
    print(f"{out}\n  video {v:.3f} s ({st['video'].get('nb_frames')} frames), audio {a:.3f} s")
    if "--no-decode" not in sys.argv:
        err = subprocess.run(["ffmpeg", "-v", "error", "-i", out, "-f", "null", "-"], capture_output=True, text=True)
        print(f"  full decode: {'no errors' if not err.stderr.strip() else err.stderr.strip()[:400]}")
    i, lra, tp = loudness(out)
    print(f"  loudness {i:.1f} LUFS, range {lra:.1f} LU, true peak {tp:.1f} dBFS")
    plan = json.load(open(os.path.join(S.BUILD, "plan.json")))
    mix = pcm(out)
    worst = 0.0
    for it in plan:
        ms, score = offset_ms(mix, it)
        worst = max(worst, abs(ms))
        print(f"  {it['idx']:2d} {it['key']:<14} sync {ms:+6.1f} ms  (match {score:.2f})")
    print(f"  worst sync offset {worst:.1f} ms")


if __name__ == "__main__":
    main()
