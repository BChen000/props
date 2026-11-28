"""Soundtrack: narration (with the glitch pause), the storytime-music organ in a new E minor preset, effects, -14 LUFS.

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
PRESET = 'e-minor'
music.PRESETS[PRESET] = dict(chord=3.0, step=0.75, prog=[      # Em C Am B | Em C D B, root-3rd-5th-3rd
    (40, 52, [64, 67, 71, 67]), (36, 48, [60, 64, 67, 64]), (33, 45, [57, 60, 64, 60]), (35, 47, [59, 63, 66, None]),
    (40, 52, [64, 67, 71, 67]), (36, 48, [60, 64, 67, 64]), (38, 50, [62, 66, 69, 66]), (35, 47, [59, 63, 59, None])])
MUSIC_DB = -4.0
EVENTS = [('forum', 0, 0.10, 'click', 0.6),
          ('bots', 4, -0.30, 'whoosh', 0.55),
          ('chart', 3, -0.06, 'boom', 0.75),
          ('city', 0, -0.35, 'whoosh', 0.35),
          ('reveal', 1, 0.88, 'glitch', 0.9)]

_orig_sfx = music.sfx


def glitch_sfx(dur=1.15, seed=5):
    """Digital stutter: gated bit-crushed noise bursts and square blips over a falling power-down tone."""
    SR = music.SR
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    k = 0
    while k < n:
        ln = int(r.uniform(0.018, 0.075) * SR)
        if r.random() < 0.72:
            seg = r.standard_normal(min(ln, n - k))
            step = int(r.integers(6, 40))
            seg = np.repeat(seg[::step], step)[:len(seg)]
            if r.random() < 0.5:
                f = r.uniform(180, 1800)
                seg = 0.6 * seg + 0.8 * np.sign(np.sin(2 * np.pi * f * np.arange(len(seg)) / SR))
            seg *= r.uniform(0.3, 1.0)
            out[k:k + len(seg)] += seg
        k += ln + int(r.uniform(0.0, 0.03) * SR)
    f = 220 * np.exp(-t / 0.35) + 40
    tone = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * np.exp(-t / 0.6) * 0.35
    x = (out * 0.55 + tone) * np.minimum(1, t / 0.01) * np.clip((dur - t) / 0.15, 0, 1)
    return x / max(np.abs(x).max(), 1e-6) * 0.9


def sfx(kind, dur=None):
    if kind == 'glitch':
        return glitch_sfx()
    return _orig_sfx(kind, dur)


music.sfx = sfx

if __name__ == '__main__':
    os.makedirs(mv.BUILD, exist_ok=True)
    nar, _, _ = mv.narration_with_pause()
    tl = mv.timeline()
    tlp = os.path.join(mv.BUILD, 'timeline.json')
    json.dump(tl, open(tlp, 'w'), indent=1)
    music.mix(nar, tl, os.path.join(mv.BUILD, 'mix.wav'), PRESET, MUSIC_DB, EVENTS)
