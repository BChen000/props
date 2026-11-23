#!/usr/bin/env python3
"""audio: builds the POWER BALLS soundtrack from out/timeline.json (event times in video seconds).

Music bed from FIGHT! until the slow-mo final blow (tape stop), a sound for every sim event (events
inside the slow-mo window play an octave down), slow-mo drone + heartbeat, sub drop on the final blow,
victory fanfare, then a look-ahead limiter. make_video.py normalizes the result to -14 LUFS when muxing.

    python audio.py [out/timeline.json] [out/audio.wav]
"""
import json
import math
import sys
import wave
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.ndimage import minimum_filter1d, uniform_filter1d

import settings as S
import sfx
import music
from sfx import SR, tt, lp, add, resample_rate

HERE = Path(__file__).resolve().parent


def pan_of(e):
    x = e.get('x')
    if x is None:
        return 0.0
    return max(-0.6, min(0.6, (x / S.ARENA - 0.5) * 1.3))


def build(T):
    sfx.reseed(S.AUDIO_SEED)
    fps = T['fps']
    dur = T['total'] / fps
    n = int(dur * SR) + SR
    t_intro = T['T_INTRO']
    tau_s = t_intro + T['t_s']
    tau_win = T['tau_win']
    events = T['events']
    kos = [e for e in events if e['type'] == 'ko']
    tau_final = kos[-1]['tau']
    tau_duel = kos[-2]['tau'] if len(kos) >= 2 else kos[-1]['tau']

    fxbuf = np.zeros((2, n))
    bed = music.build_bed(n, t_intro, tau_s + 0.8, tau_duel)
    music.tape_stop(bed, tau_s, 0.7)
    # intro: pops, riser, FIGHT! impact
    for i in range(4):
        pp = resample_rate(sfx.sfx_pop(), 1.0 / (1 + 0.12 * i))
        add(fxbuf, pp, 0.03 + 0.08 * i, 0.6 + 0.1 * i, pan=(i - 1.5) * 0.3)
    add(fxbuf, sfx.sfx_riser(2.45), t_intro - 2.45, 0.75)
    add(fxbuf, sfx.kick(0.6), t_intro, 1.0)
    add(fxbuf, sfx.sfx_explosion(0.8, 1.0), t_intro, 0.55)
    add(fxbuf, sfx.sfx_crash(2.0), t_intro, 0.6)
    add(fxbuf, sfx.sfx_stab(0.5), t_intro)
    cache = {}

    def get(key, fn):
        if key not in cache:
            cache[key] = fn()
        return cache[key]

    for e in events:
        ty = e['type']
        at = e['tau']
        slow = T['t_s'] <= e['t'] < T['t_e']
        x = None
        g = 1.0
        if ty == 'blaster':
            x = sfx.sfx_pew(e['n'])
            g = 1.05
        elif ty == 'laser_charge':
            x = get('lzc', sfx.sfx_laser_charge)
            g = 0.85
        elif ty == 'laser_fire':
            x = get('lzf', sfx.sfx_laser_fire)
            g = 0.75
        elif ty == 'missile_launch':
            x = sfx.sfx_missile_launch()
            g = 1.0
        elif ty == 'missile_explode':
            x = sfx.sfx_explosion(0.55 if e['hit'] else 0.35, 0.6)
            g = 0.9 if e['hit'] else 0.6
        elif ty == 'lightning':
            x = sfx.sfx_lightning()
            g = 0.8
        elif ty == 'hit':
            x = sfx.sfx_hit(sfx.HIT_PITCH.get(e['victim'], 1.0))
            g = 0.9
            if e.get('upgraded') and not (e['t'] >= T['t_end'] - 1e-6):
                add(fxbuf, get('upg', sfx.sfx_upgrade), at + 0.06, 0.8, pan=0.0)
        elif ty == 'ko':
            final = abs(at - tau_final) < 1e-6
            x = sfx.sfx_ko()
            g = 1.0 if not final else 1.25
        elif ty == 'bump':
            if e['v'] > 120:
                x = get('bump', sfx.sfx_bump)
                g = 1.0
        elif ty == 'bullet_wall':
            x = get('tick', sfx.sfx_tick)
            g = 0.6
        elif ty == 'absorb':
            x = get('abs', sfx.sfx_absorb)
        if x is None:
            continue
        if slow:
            x = resample_rate(x, 0.5)
            g *= 1.1
        add(fxbuf, x, at, g, pan=pan_of(e))
    # slow-motion atmosphere
    add(fxbuf, sfx.sfx_whoosh(0.9, 3000, 200) * 0.5, tau_s, 0.7)
    add(fxbuf, sfx.tension_drone(tau_final - tau_s + 0.3), tau_s)
    hb = sfx.heartbeat()
    tb = tau_s + 0.25
    while tb < tau_final - 0.25:
        add(fxbuf, hb, tb, 0.9)
        tb += 0.85
    add(fxbuf, sfx.sub_drop(2.0), tau_final, 1.0)
    add(fxbuf, sfx.sfx_crash(2.5), tau_final, 0.7)
    music.fanfare(tau_win, fxbuf)
    # mix
    bed = sfx.hp(bed, 35)
    mix = bed * S.MUSIC_GAIN + fxbuf * S.SFX_GAIN
    fade_n = int(0.6 * SR)
    end_i = int(dur * SR)
    mix[:, end_i - fade_n:end_i] *= np.linspace(1, 0, fade_n)
    mix[:, end_i:] = 0
    mix = mix[:, :end_i]
    return master(mix)


def master(mix):
    """Level from the 99.5th percentile, low-pass at 16 kHz, then a 4x-oversampled look-ahead limiter."""
    ref = np.percentile(np.abs(mix), 99.5)
    mix = mix * (S.PREGAIN / ref)
    thr = S.LIMIT
    mix = np.vstack([lp(mix[0], 16000, 4), lp(mix[1], 16000, 4)])
    up = signal.resample_poly(mix, 4, 1, axis=1)
    pk = np.max(np.abs(up), axis=0).reshape(-1, 4).max(axis=1)[:mix.shape[1]]
    need = np.minimum(1.0, thr / np.maximum(pk, 1e-9))
    W = int(0.005 * SR)
    g = minimum_filter1d(need, size=2 * W + 1)
    g = uniform_filter1d(g, size=W)
    rel = 1 - math.exp(-1 / (0.09 * SR))
    out_g = np.empty_like(g)
    cur = 1.0
    for i in range(len(g)):
        v = g[i]
        if v < cur:
            cur = v
        else:
            cur = cur + (v - cur) * rel
        out_g[i] = cur
    mix = mix * out_g
    return np.clip(mix, -0.97, 0.97)


def write(path, mix):
    out = (mix.T * 32767).astype(np.int16)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(out.tobytes())


def main():
    tl = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / 'out' / 'timeline.json'
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / 'out' / 'audio.wav'
    T = json.loads(tl.read_text())
    mix = build(T)
    write(dst, mix)
    print('wrote', dst, f'{mix.shape[1] / SR:.2f} s')


if __name__ == '__main__':
    main()
