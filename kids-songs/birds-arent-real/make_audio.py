"""Soundtrack: narration (with the tail for the pigeon), the storytime-music organ in G minor, effects, -14 LUFS.

  python3 make_audio.py        -> build/mix.wav (and build/timeline.json, build/narration_paused.wav)
"""
import paths  # noqa: F401  (sibling props on sys.path)
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_video as mv
import music                                  # props/kids-songs/storytime-music (path set up by make_video)

# ------------------------------------------------------------------ settings
PRESET = 'g-minor'
MUSIC_DB = -4.0
# (scene, line in that scene, offset s from the line's start, effect, gain[, length s or 'scene'])
# The offsets follow the timings in shots.py (s_car, s_lore, s_wires, s_end).
EVENTS = [('chant', 0, 0.0, 'chant', 0.32, 'scene'),
          ('lore', 2, -0.10, 'boom', 0.6),                          # the number lights up
          ('lore', 4, -0.05, 'scan', 0.5), ('lore', 4, 0.55, 'beep', 0.45),
          ('wires', 0, 0.30, 'coo', 0.5), ('wires', 1, 0.0, 'charge', 0.55),
          ('car', 0, 0.35, 'flap', 0.5), ('car', 0, 1.16, 'splat', 0.7),
          ('car', 1, 0.05, 'beep', 0.4), ('car', 1, 0.85, 'beep', 0.4), ('car', 1, 1.65, 'beep', 0.4),
          ('slogan', 0, 0.0, 'chant', 0.22, 'scene'),
          ('protest', 0, 0.0, 'chant', 0.36, 'scene'),
          ('reveal', 2, 0.0, 'scratch', 0.55),                     # "he made the whole thing up."
          ('xdrop', 0, 0.0, 'gavel', 0.55), ('xdrop', 2, 0.0, 'boom', 0.45),
          ('end', 1, 0.25, 'flap', 0.55), ('end', 1, 1.40, 'coo', 0.45),
          ('end', 1, 1.85, 'whir', 0.5), ('end', 1, 2.45, 'beep', 0.5), ('end', 1, 3.02, 'beep', 0.5)]

_orig_sfx = music.sfx
SR = music.SR


def _env(n, a, r):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.clip((t[-1] - t) / r, 0, 1)


def _norm(x, peak=0.9):
    return x / max(np.abs(x).max(), 1e-6) * peak


def chant(dur, seed=21, rate=1.1):
    """A crowd chanting in rhythm: four shouted syllables per beat over a murmur."""
    r = np.random.default_rng(seed)
    n = int(dur * SR); t = np.arange(n) / SR
    x = 0.25 * music.bp(r.standard_normal(n), 200, 1800)
    beat = 1.0 / rate
    b0 = 0.0
    while b0 < dur:
        for s, ln in zip((0.0, 0.17, 0.30, 0.46), (0.14, 0.11, 0.13, 0.22)):
            s0 = int((b0 + s) * SR); m = int(ln * SR)
            if s0 + m >= n:
                break
            tt = np.arange(m) / SR
            v = np.zeros(m)
            for _ in range(9):
                f0 = r.uniform(110, 260)
                v += ((tt * f0) % 1.0 - 0.5) * r.uniform(0.5, 1.0)
            v = music.bp(v, 350, 2600) * np.minimum(1, tt / 0.02) * np.exp(-tt / (ln * 0.7))
            x[s0:s0 + m] += v * 1.4
        b0 += beat
    return _norm(x * _env(n, 0.3, 0.4), 0.7)


def coo(seed=22):
    """A pigeon's coo: a soft two-part hoot."""
    n = int(0.9 * SR); t = np.arange(n) / SR
    f = np.where(t < 0.35, 330 + 120 * t / 0.35, 450 - 170 * (t - 0.35) / 0.55) * (1 + 0.02 * np.sin(2 * np.pi * 22 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    a = np.exp(-((t - 0.18) / 0.12) ** 2) * 0.6 + np.exp(-((t - 0.55) / 0.2) ** 2)
    x = (np.sin(ph) + 0.3 * np.sin(2 * ph)) * a
    return _norm(music.lp(x, 1500), 0.8)


def flap(dur=1.2, rate=7.0, seed=23):
    """Wing beats: soft filtered-noise whooshes."""
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    x = np.zeros(n)
    k = 0.0
    while k < dur - 0.05:
        s0 = int(k * SR); m = min(int(0.07 * SR), n - s0)
        tt = np.arange(m) / SR
        x[s0:s0 + m] += music.lp(r.standard_normal(m), 1400) * np.sin(np.pi * tt / 0.07) ** 2
        k += 1.0 / rate * r.uniform(0.9, 1.1)
    return _norm(x * _env(n, 0.05, 0.2), 0.8)


def splat(seed=24):
    r = np.random.default_rng(seed)
    n = int(0.6 * SR); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * 90 * t) * np.exp(-t / 0.05) + music.bp(r.standard_normal(n), 700, 3500) * np.exp(-t / 0.04) * 0.9
    for k in range(5):
        s0 = int(r.uniform(0.05, 0.3) * SR); m = int(0.02 * SR)
        x[s0:s0 + m] += music.hp(r.standard_normal(m), 2500) * np.exp(-np.arange(m) / SR / 0.004) * 0.3
    return _norm(x, 0.9)


def beep(f=2200.0):
    n = int(0.13 * SR); t = np.arange(n) / SR
    return _norm(np.sin(2 * np.pi * f * t) * np.minimum(1, t / 0.005) * np.clip((t[-1] - t) / 0.02, 0, 1), 0.7)


def scan():
    n = int(0.95 * SR); t = np.arange(n) / SR
    f = 300 * (8 ** (t / 0.95))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = (np.sin(ph) + 0.25 * np.sin(3 * ph)) * (0.7 + 0.3 * np.sin(2 * np.pi * 30 * t))
    return _norm(x * _env(n, 0.05, 0.15), 0.7)


def charge(dur=2.4, seed=25):
    """Power-line charging: mains buzz, a rising tone and crackles."""
    r = np.random.default_rng(seed)
    n = int(dur * SR); t = np.arange(n) / SR
    buzz = sum(np.sign(np.sin(2 * np.pi * 60 * h * t)) / h for h in (1, 2, 3)) * 0.25
    f = 420 + 380 * t / dur
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.35
    cr = np.zeros(n)
    for _ in range(int(dur * 14)):
        s0 = int(r.uniform(0, dur - 0.02) * SR); m = int(0.008 * SR)
        cr[s0:s0 + m] += r.standard_normal(m) * r.uniform(0.3, 1.0)
    x = music.lp(buzz, 900) + tone + music.hp(cr, 1500) * 0.5
    return _norm(x * _env(n, 0.15, 0.3), 0.8)


def whir():
    """A small servo turning."""
    n = int(0.4 * SR); t = np.arange(n) / SR
    f = 520 + 160 * np.sin(np.pi * t / 0.4)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = sum(np.sin(ph * h) / h for h in range(1, 6))
    return _norm(music.bp(x, 300, 4000) * _env(n, 0.03, 0.06), 0.7)


def scratch(seed=26):
    """A record scratch."""
    r = np.random.default_rng(seed)
    n = int(0.45 * SR); t = np.arange(n) / SR
    sp = np.interp(t, [0, 0.12, 0.2, 0.32, 0.45], [1.0, -0.6, 0.8, -0.9, 0.0])
    ph = np.cumsum(sp) / SR * 900
    x = np.sin(2 * np.pi * ph) * 0.5 + music.bp(r.standard_normal(n), 1200, 5000) * np.abs(sp) * 0.8
    return _norm(x * _env(n, 0.005, 0.05), 0.85)


def sfx(kind, dur=None):
    mine = dict(coo=coo, splat=splat, beep=beep, scan=scan, whir=whir, scratch=scratch)
    if kind in mine:
        return mine[kind]()
    if kind == 'chant':
        return chant(dur or 4.0)
    if kind == 'flap':
        return flap(dur or 1.2)
    if kind == 'charge':
        return charge(dur or 2.4)
    return _orig_sfx(kind, dur)


music.sfx = sfx

if __name__ == '__main__':
    os.makedirs(mv.BUILD, exist_ok=True)
    nar, _, _ = mv.narration_with_pause()
    tl = mv.timeline()
    tlp = os.path.join(mv.BUILD, 'timeline.json')
    json.dump(tl, open(tlp, 'w'), indent=1)
    music.mix(nar, tl, os.path.join(mv.BUILD, 'mix.wav'), PRESET, MUSIC_DB, EVENTS)
