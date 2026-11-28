"""Builds the stickman demo: "What if you were stranded on a tiny island?" in five scenes, narrated.

  python build.py                 -> build/stickman_demo.mp4 (1080x1920, 30 fps, AAC 192k)
  python build.py --stills        -> build/stills.png, one frame per scene, no encoding
  python build.py --frames 3,9.5  -> build/frame_3.00.png ... at full size
Uses ../../kids-songs/storytime-kit (renderer, captions), storytime-narrator (voice) and storytime-music (music, sfx).
"""
import argparse
import math
import os
import subprocess
import sys
import time

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

HERE = os.path.dirname(os.path.abspath(__file__))
KIDS = os.path.join(HERE, '..', '..', 'kids-songs')
for p in ('storytime-kit', 'storytime-narrator', 'storytime-music'):
    sys.path.insert(0, os.path.join(KIDS, p))
sys.path.insert(0, HERE)
import storytime_kit as kit  # noqa: E402
import narrate  # noqa: E402
import music  # noqa: E402
from settings import STORY, GROUND, HORIZON, CAP_Y, MUSIC  # noqa: E402
from stickman import (stick, stand, walk, shrug, push, crouch, wave, salute, lerp_pose, sky, sea, island, palm,  # noqa: E402
                      campfire, ship, fin, coconut)
from storytime_kit import line, circ, ease, ramp, clamp, glow  # noqa: E402

OUT = os.environ.get('STICKMAN_OUT', os.path.join(HERE, 'build'))
SR = music.SR
kit.hook_card = lambda *a, **k: None          # no hook card: the first caption is the hook

PALM = (775, GROUND + 6, 0.95)
FIRE = (600, GROUND + 8)
SCALE = 0.8


# ---------------------------------------------------------------- scenes
def sc_island(c, t, x):
    sky(c, 'dawn', t)
    sea(c, 'dawn', t)
    island(c, 'dawn', t)
    palm(c, *PALM, t=t, tod='dawn')
    t_stop = x.T[1] - 0.1
    u = clamp(t / t_stop)
    if t < t_stop:
        stick(c, 170 + 270 * u, GROUND, SCALE, walk(2 * math.pi * 0.85 * t, amp=20))
    else:
        stick(c, 440, GROUND, SCALE, lerp_pose(stand(), shrug(), (t - t_stop) / 0.3))


COCO_DROP, G = 0.2, 3000.0


def coco_path(t_rel):
    """Coconut position t_rel seconds after it falls from the crown; returns (x, y, landed_at)."""
    x0, y0, y1 = 731, 822, GROUND
    tf = math.sqrt(2 * (y1 - y0) / G)
    if t_rel < tf:
        return x0, y0 + 0.5 * G * t_rel ** 2, tf
    u = t_rel - tf
    hop = max(0.0, 120 * u - 0.5 * G * u * u)
    return x0 - 90 * (1 - math.exp(-u / 0.25)), y1 - hop, tf


def sc_day1(c, t, x):
    sky(c, 'day', t)
    sea(c, 'day', t)
    island(c, 'day', t)
    t_arrive = x.T[1] - 0.3
    shake = ramp(t, t_arrive, 0.1) * (1 - ramp(t, x.T[1] + 0.8, 0.2))
    t_drop = x.T[1] + COCO_DROP
    palm(c, *PALM, t=t, sway=2.2 * math.sin(2 * math.pi * 6 * t) * shake, tod='day', coconuts=3 if t < t_drop else 2)
    if t < t_arrive:
        u = clamp(t / t_arrive)
        stick(c, 400 + 160 * u, GROUND, SCALE, walk(2 * math.pi * 0.9 * t, amp=20))
    else:
        joy = ramp(t, t_drop + 0.75, 0.25)
        pose = lerp_pose(push(t, shake), stand(), ramp(t, x.T[1] + 0.8, 0.2))
        pose = lerp_pose(pose, dict(stand(), la=(-150.0, -165.0), ra=(150.0, 165.0)), joy)
        stick(c, 560, GROUND, SCALE, pose, lift=28 * joy * abs(math.sin(2 * math.pi * 2.2 * t)))
    if t >= t_drop:
        cx, cy, _ = coco_path(t - t_drop)
        coconut(c, cx, cy - 18, 1.0)


def sc_day2(c, t, x):
    sky(c, 'night', t)
    sea(c, 'night', t)
    island(c, 'night', t)
    palm(c, *PALM, t=t, tod='night')
    ign = x.T[1] + 0.05
    fire = ease((t - ign) / 0.6)
    campfire(c, *FIRE, t, fire=fire)
    rub = 1 - ramp(t, ign, 0.2)

    def sticks(cc, hl, hr):
        if rub > 0.05:
            line(cc, hl[0] - 10, hl[1] + 30, hr[0] + 30, hr[1] - 10, '#6B4426', w=9)
            for k in range(3):
                ph = (t * 3 + k / 3) % 1
                circ(cc, hr[0] + 24 + 30 * ph, hr[1] - 6 - 40 * ph, 4 * (1 - ph), '#FFC861', rub * (1 - ph))

    stick(c, 470, GROUND, SCALE, crouch(t, rub), hold=sticks)


def sc_day3(c, t, x):
    sky(c, 'morning', t)
    sea(c, 'morning', t)
    ship(c, 770 + 22 * t, HORIZON + 2, 0.9, ramp(t, x.T[1] - 0.1, 0.4))
    island(c, 'morning', t)
    palm(c, *PALM, t=t, tod='morning')
    campfire(c, *FIRE, t, fire=0.0, smoke=1.0)
    wv = ramp(t, x.T[1] + 0.2, 0.2)
    stick(c, 400, GROUND, SCALE, lerp_pose(stand(), wave(t), wv), lift=26 * wv * abs(math.sin(2 * math.pi * 1.3 * t)))


def sc_swim(c, t, x):
    sky(c, 'morning', t + 5)
    sea(c, 'morning', t + 5)
    ship(c, 880 + 16 * t, HORIZON + 2, 0.9)
    island(c, 'morning', t + 5)
    palm(c, *PALM, t=t + 5, tod='morning')
    campfire(c, *FIRE, t + 5, fire=0.0, smoke=1.0)
    stick(c, 820, GROUND, SCALE, salute())
    fa = ramp(t, x.T[0] + 0.35, 0.3)
    fin(c, 60 + 290 * (t - x.T[0]), 1565, t, 1.6, fa, dirn=1)


SCENES = {
    'island': dict(draw=sc_island, cam=(1.15, 1.0, 420, 1200), cap_y=CAP_Y, vig=0.45),
    'day1': dict(draw=sc_day1, cam=(1.0, 1.06, 600, 1150), cap_y=CAP_Y, vig=0.4),
    'day2': dict(draw=sc_day2, cam=(1.04, 1.1, 540, 1250), cap_y=CAP_Y, vig=0.7),
    'day3': dict(draw=sc_day3, cam=(1.0, 1.05, 520, 1100), cap_y=CAP_Y, vig=0.4),
    'swim': dict(draw=sc_swim, cam=(1.0, 1.1, 600, 1300), cap_y=CAP_Y, vig=0.5),
}


# ---------------------------------------------------------------- sound
def horn(dur=1.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 98 * (1 + 0.004 * np.sin(2 * np.pi * 5 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = sum(np.sin(ph * h) / h for h in range(1, 9))
    return music.lp(x, 900) * np.minimum(1, t / 0.12) * np.minimum(1, (t[-1] - t) / 0.3) * 0.5


def crackle(dur, rng):
    n = int(dur * SR)
    x = np.zeros(n)
    for _ in range(int(dur * 22)):
        s0 = int(rng.random() * (n - 800))
        ln = int((0.002 + rng.random() * 0.006) * SR)
        x[s0:s0 + ln] += rng.standard_normal(ln) * np.exp(-np.arange(ln) / (ln / 4)) * (0.3 + rng.random())
    return music.bp(x, 900, 6000) + music.lp(rng.standard_normal(n), 300) * 0.15


def crickets(dur, rng):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for k in range(int(dur * 2.2)):
        t0 = rng.random() * dur
        for j in range(3):
            s0 = int((t0 + j * 0.045) * SR)
            ln = int(0.03 * SR)
            if s0 + ln < n:
                tt = np.arange(ln) / SR
                x[s0:s0 + ln] += np.sin(2 * np.pi * 4600 * tt) * np.sin(np.pi * tt / tt[-1]) * 0.2
    return x


def riser(dur, rng):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = rng.standard_normal(n)
    out = np.zeros(n)
    for k in range(16):
        s0, s1 = k * n // 16, (k + 1) * n // 16
        fc = 200 * 2 ** (k / 4)
        out[s0:s1] = music.bp(x[s0:s1], fc * 0.7, fc * 1.4)
    return out * (t / t[-1]) ** 2 * 0.6


def put(buf, x, t0, gain=1.0):
    s0 = int(round(t0 * SR))
    if 0 <= s0 < len(buf):
        x = x[:len(buf) - s0]
        buf[s0:s0 + len(x)] += x * gain


def soundtrack(tl, out_wav):
    nar, sr = sf.read(os.path.join(OUT, 'narration.wav'))
    nar = resample_poly(nar, SR // 6000, sr // 6000) if sr != SR else nar
    dur = tl['duration']
    n = len(nar)
    rng = np.random.default_rng(12)
    spans = {sp['scene']: sp for sp in kit.scene_spans(tl)}
    sp_idx = np.concatenate([np.arange(int(l['start'] * SR), int(l['end'] * SR)) for l in tl['lines']])
    speech_rms = np.sqrt(np.mean((nar[sp_idx[sp_idx < n]] * 0.9) ** 2))
    mus = music.music(dur, MUSIC['preset'])[:n]
    mus = np.pad(mus, ((0, max(0, n - len(mus))), (0, 0)))
    mus *= speech_rms * 10 ** (MUSIC['music_db'] / 20) / np.sqrt(np.mean(mus.mean(1) ** 2))
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    swell = 0.55 + 0.45 * np.sin(2 * np.pi * 0.13 * t) ** 2
    ocean_m = (music.lp(noise, 450) * 0.7 + music.bp(noise, 700, 2600) * 0.22) * swell
    night = spans['day2']
    og = np.ones(n)
    og[int(night['start'] * SR):int(night['end'] * SR)] = 0.55
    ocean = np.stack([ocean_m, np.roll(ocean_m, 811)], 1) * og[:, None]
    ocean *= speech_rms * 10 ** (-14 / 20) / np.sqrt(np.mean(ocean ** 2))
    fx = np.zeros(n)
    put(fx, music.sfx('boom'), 0.0, 0.6)
    for name in ('day1', 'day2', 'day3', 'swim'):
        put(fx, music.sfx('whoosh'), spans[name]['start'] - 0.4, 0.35)
    d1 = spans['day1']
    t_drop = d1['lines'][1]['start'] + COCO_DROP
    _, _, tf = coco_path(0)
    put(fx, music.sfx('gavel'), t_drop + tf, 0.8)
    put(fx, music.sfx('gavel'), t_drop + tf + 0.08 + 120 / G, 0.25)
    ign = night['lines'][1]['start'] + 0.05
    put(fx, music.sfx('grind', ign - night['start'] - 0.3) * 0.6, night['start'] + 0.3, 0.5)
    put(fx, music.sfx('whoosh'), ign - 0.25, 0.6)
    put(fx, crackle(night['end'] - ign, rng), ign, 0.7)
    put(fx, crickets(night['end'] - night['start'], rng), night['start'], 0.5)
    d3 = spans['day3']
    put(fx, horn(), d3['lines'][1]['start'] + 0.1, 0.7)
    sw = spans['swim']
    t_fin = sw['lines'][0]['start'] + 0.35
    put(fx, music.sfx('boom'), t_fin, 0.8)
    put(fx, riser(sw['end'] - t_fin - 1.0, rng), t_fin, 0.5)
    mix_ = np.stack([nar, nar], 1) * 0.9 + mus + ocean * (MUSIC['ocean'] / 0.22) + music.reverb(fx, 0.22) * MUSIC['fx']
    mix_ = mix_ / max(np.abs(mix_).max(), 1e-6) * 0.89
    raw = os.path.splitext(out_wav)[0] + '_raw.wav'
    sf.write(raw, mix_.astype(np.float32), SR)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', raw, '-af', music.LOUDNORM, '-ar', str(SR), out_wav], check=True)
    return out_wav


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--stills', action='store_true')
    ap.add_argument('--frames', default=None)
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    tl = narrate.narrate(STORY, OUT)
    if a.stills or a.frames:
        if a.stills:
            print('wrote', kit.contact_sheet(tl, SCENES, os.path.join(OUT, 'stills.png'), cols=3, thumb=(270, 480), when='late'))
        if a.frames:
            from PIL import Image
            ts = [float(v) for v in a.frames.split(',')]
            for tt, f in zip(ts, kit.render(tl, SCENES, None, frames_at=ts)):
                p = os.path.join(OUT, f'frame_{tt:.2f}.png')
                Image.fromarray(f).save(p)
                print('wrote', p)
        return
    wav = soundtrack(tl, os.path.join(OUT, 'mix.wav'))
    kit.render(tl, SCENES, os.path.join(OUT, 'scenes'))
    mp4 = kit.concat_and_mux(os.path.join(OUT, 'scenes'), wav, os.path.join(OUT, 'stickman_demo.mp4'))
    print('DONE', mp4, f'{tl["duration"]:.2f} s video in {time.time() - t0:.0f} s')


if __name__ == '__main__':
    main()
