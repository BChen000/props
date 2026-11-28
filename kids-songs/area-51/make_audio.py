"""Soundtrack: narration (with the tail for the beam-up), the storytime-music organ in D minor, effects, -14 LUFS.

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
PRESET = 'd-minor'
MUSIC_DB = -4.0
# (scene, line in that scene, offset s from the line's start, effect, gain[, length s or 'scene'])
EVENTS = [('desert', 0, -0.10, 'jet', 0.55),
          ('tv', 0, -0.30, 'tvon', 0.5),
          ('saucer', 1, 0.25, 'clunk', 0.65), ('saucer', 1, 0.67, 'clunk', 0.72), ('saucer', 1, 1.09, 'clunk', 0.8),
          ('cia', 2, -0.05, 'boom', 0.7),
          ('u2', 0, -0.25, 'whoosh', 0.4),
          ('itwasus', 1, -0.05, 'gavel', 0.55),
          ('storm', 1, -0.05, 'click', 0.4),
          ('gate', 0, 0.0, 'crowd', 0.35, 'scene'),
          ('end', 2, 1.35, 'beam', 0.75),      # shots.s_end: beam at the end of "Nothing to see here." + 0.25 s
          ('end', 2, 3.35, 'thud', 0.5),       # the hat lands
          ('end', 2, 3.90, 'click', 0.45)]     # the room light flickers back on

_orig_sfx = music.sfx
SR = music.SR


def _env(n, a, r):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.clip((t[-1] - t) / r, 0, 1)


def jet(dur=4.6, seed=11):
    """A distant airliner passing: low filtered roar that swells and fades, with a faint whine."""
    r = np.random.default_rng(seed)
    n = int(dur * SR); t = np.arange(n) / SR
    roar = music.lp(r.standard_normal(n), 700) + 0.4 * music.bp(r.standard_normal(n), 900, 2500)
    swell = np.exp(-((t - dur * 0.45) / (dur * 0.28)) ** 2)
    whine = 0.08 * np.sin(2 * np.pi * np.cumsum(2400 - 300 * t / dur) / SR)
    x = (roar * 0.8 + whine) * swell * _env(n, 0.3, 0.6)
    return x / max(np.abs(x).max(), 1e-6) * 0.8


def tvon(seed=12):
    """An old CRT switching on: a click, a thin high whine and a burst of static."""
    r = np.random.default_rng(seed)
    n = int(1.0 * SR); t = np.arange(n) / SR
    click = r.standard_normal(n) * np.exp(-t / 0.004)
    whine = 0.12 * np.sin(2 * np.pi * 15700 * t) * np.minimum(1, t / 0.05) * np.exp(-t / 0.8)
    static = music.bp(r.standard_normal(n), 1500, 8000) * 0.5 * np.exp(-t / 0.25)
    x = click * 0.8 + whine + static
    return x / max(np.abs(x).max(), 1e-6) * 0.8


def clunk(seed=13):
    """A heavy breaker switch: a low knock and a short metallic ring."""
    r = np.random.default_rng(seed)
    n = int(0.9 * SR); t = np.arange(n) / SR
    knock = np.sin(2 * np.pi * (70 + 60 * np.exp(-t / 0.03)) * t) * np.exp(-t / 0.09)
    ring = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t / d) for f, a, d in ((410, 0.25, 0.12), (1130, 0.12, 0.06)))
    hit = music.bp(r.standard_normal(n), 200, 3000) * np.exp(-t / 0.012) * 0.6
    x = knock + ring + hit
    return x / max(np.abs(x).max(), 1e-6) * 0.9


def crowd(dur, seed=14):
    """A small crowd murmuring at night: band-passed babble with slow swells."""
    r = np.random.default_rng(seed)
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.zeros(n)
    for k in range(7):
        f0 = r.uniform(110, 230)
        syl = (np.sin(2 * np.pi * r.uniform(2.5, 4.5) * t + r.uniform(0, 6.3)) > r.uniform(-0.2, 0.4)).astype(float)
        syl = music.lp(syl, 12)
        x += music.bp(r.standard_normal(n), f0 * 2, f0 * 8) * syl * r.uniform(0.5, 1.0)
    x += 0.15 * music.lp(r.standard_normal(n), 300)
    x *= _env(n, 0.5, 0.5) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.3 * t))
    return x / max(np.abs(x).max(), 1e-6) * 0.7


def beam(dur=2.75, seed=15):
    """A tractor beam: a rising swoop into a shimmering chord with vibrato, then a quick power-down."""
    r = np.random.default_rng(seed)
    n = int(dur * SR); t = np.arange(n) / SR
    off = 2.15
    rise = 1 - np.exp(-t / 0.35)
    drop = np.where(t > off, np.exp(-(t - off) / 0.12), 1.0)
    f = (90 + 130 * rise) * (1 + 0.012 * np.sin(2 * np.pi * 6 * t)) * np.where(t > off, np.exp(-(t - off) / 0.2), 1.0)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = sum(np.sin(ph * h) / h ** 1.2 for h in (1, 1.5, 2, 3, 4))
    shimmer = music.bp(r.standard_normal(n), 3000, 9000) * 0.12 * (0.6 + 0.4 * np.sin(2 * np.pi * 11 * t))
    x = (x * 0.5 + shimmer) * np.minimum(1, t / 0.15) * drop * np.clip((dur - t) / 0.05, 0, 1)
    return x / max(np.abs(x).max(), 1e-6) * 0.9


def thud(seed=16):
    """A hat landing on a wooden floor."""
    r = np.random.default_rng(seed)
    n = int(0.5 * SR); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * 95 * t) * np.exp(-t / 0.05) + music.lp(r.standard_normal(n), 900) * np.exp(-t / 0.02) * 0.5
    return x / max(np.abs(x).max(), 1e-6) * 0.8


def sfx(kind, dur=None):
    mine = dict(jet=jet, tvon=tvon, clunk=clunk, beam=beam, thud=thud)
    if kind in mine:
        return mine[kind]()
    if kind == 'crowd':
        return crowd(dur or 4.0)
    return _orig_sfx(kind, dur)


music.sfx = sfx

if __name__ == '__main__':
    os.makedirs(mv.BUILD, exist_ok=True)
    nar, _, _ = mv.narration_with_pause()
    tl = mv.timeline()
    tlp = os.path.join(mv.BUILD, 'timeline.json')
    json.dump(tl, open(tlp, 'w'), indent=1)
    music.mix(nar, tl, os.path.join(mv.BUILD, 'mix.wav'), PRESET, MUSIC_DB, EVENTS)
