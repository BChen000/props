"""Builds the blob-style demo: alarm at 5:00, a shadow whispers excuses, the blob says no, DAY 1 montage.

  python build.py                 -> build/blob_demo.mp4 (1080x1920, 30 fps, AAC 192k)
  python build.py --stills        -> build/stills.png, one frame per scene, no encoding
  python build.py --frames 3,9.5  -> build/frame_3.00.png ... at full size
Uses ../../kids-songs/storytime-kit (renderer, drawing), storytime-narrator (voice) and storytime-music (sfx, reverb).
"""
import argparse
import math
import os
import subprocess
import sys
import time

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
KIDS = os.path.join(HERE, '..', '..', 'kids-songs')
for p in ('storytime-kit', 'storytime-narrator', 'storytime-music'):
    sys.path.insert(0, os.path.join(KIDS, p))
sys.path.insert(0, HERE)
import storytime_kit as kit  # noqa: E402
import narrate  # noqa: E402
import music  # noqa: E402
from settings import (FPS, VIGNETTE, SCENE_FADE_IN, ALARM_LEAD, WAKE_GAP, WAKE_LEN, MONTAGE, WHISPERS,  # noqa: E402
                      VOICE_PITCH, VOICE_REVERB, VOICE_LP, MUSIC, COLORS as K)
from blob import (blob, shadow, bedroom, bed, pillow, bed_front, dawn, hills, desk_lamp, book, calendar,  # noqa: E402
                  whisper, title_text, grain)
from storytime_kit import W, H, rect, line, glow, circ, oval, grect, ease, eout, ramp, clamp, text  # noqa: E402

OUT = os.environ.get('BLOB_OUT', os.path.join(HERE, 'build'))
SR = music.SR

# the kit draws captions and a hook card; this look draws its own text, adds grain and cuts faster
kit.hook_card = lambda *a, **k: None
kit.caption = lambda *a, **k: None
kit.SCENE_FADE_IN = SCENE_FADE_IN
_vig = kit.vignette


def _post(c, s=0.6, cy=0.46):
    _vig(c, VIGNETTE, cy)
    grain(c)


kit.vignette = _post


# ---------------------------------------------------------------- timeline
def timeline():
    story = dict(name='blob_demo', hook=('', ''), lines=[('bed', w) for w in WHISPERS])
    tl0 = narrate.narrate(story, os.path.join(OUT, 'voice'))
    lines = [dict(ln, start=round(ln['start'] + ALARM_LEAD, 3), end=round(ln['end'] + ALARM_LEAD, 3)) for ln in tl0['lines']]
    t = lines[-1]['end'] + WAKE_GAP
    lines.append(dict(i=len(lines), scene='wake', text='no.', start=round(t, 3), end=round(t + WAKE_LEN, 3)))
    t += WAKE_LEN
    for scene, d, txt in MONTAGE:
        lines.append(dict(i=len(lines), scene=scene, text=txt, start=round(t, 3), end=round(t + d, 3)))
        t += d
    return dict(duration=round(t, 3), lines=lines, hook=('', ''), name='blob_demo')


# ---------------------------------------------------------------- scenes
def sc_bed(c, t, x):
    alarm = 1.0 if t < x.T[0] - 0.25 else 0.0
    bedroom(c, t, alarm=alarm)
    rise = ease((t - (x.T[0] - 1.0)) / 1.1)
    grow = 1.0 + 0.10 * ramp(t, x.T[1], 0.5) + 0.10 * ramp(t, x.T[2], 0.5)
    c.save()
    c.clipRect(kit.R(-500, -500, W + 1000, 1800))
    shadow(c, 520, 1330 + 300 * (1 - rise), 1.12, t, grow=grow, lean=-14 * rise - 5 * ramp(t, x.T[2], 0.6), alpha=rise)
    c.restore()
    bed(c)
    pillow(c)
    blob(c, 618, 1262, 1.0, expr='closed', rot=-90, ground_shadow=False, squash=1 + 0.02 * math.sin(2.2 * t))
    bed_front(c, t, breathe=1.0)
    for i, s in enumerate(WHISPERS):
        out = 1 - ramp(t, x.T[i + 1] - 0.15, 0.2) if i + 1 < len(x.T) else 1 - ramp(t, x.dur - 0.25, 0.2)
        whisper(c, s, 400, 600, t - x.T[i] + 0.05, out)


def sc_wake(c, t, x):
    rect(c, -500, -500, W + 1000, H + 1000, K['wall'])
    glow(c, 980, 520, 700, K['moon'], 0.16)
    t_open, t_no = x.T[0] + 0.12, x.T[0] + 0.75
    shadow(c, 600, 1500, 2.0, t + 3, lean=-6, dissolve=ramp(t, t_no, 0.9), seed=2.0)
    blink = 1 - ramp(t, t_open, 0.07)
    blob(c, 520, 1760, 2.3, expr='open' if blink < 0.95 else 'closed', blink=blink, look=(0.15, -0.3),
         brows=ramp(t, t_no - 0.1, 0.15), ground_shadow=False)
    p = kit.skia.Path()
    p.moveTo(-500, 1600)
    p.cubicTo(120, 1520, 330, 1590, 560, 1555)
    p.cubicTo(760, 1525, 900, 1600, W + 500, 1560)
    p.lineTo(W + 500, H + 600)
    p.lineTo(-500, H + 600)
    p.close()
    c.drawPath(p, kit.P('#ffffff', shader=kit.lgrad(0, 1520, 0, 1900, [K['blanket_hi'], K['blanket']])))
    c.drawPath(p, kit.P('#5A6475', sw=4))
    a = ramp(t, t_no, 0.08)
    if a > 0:
        k = 1.12 - 0.12 * eout((t - t_no) / 0.25)
        c.save()
        c.translate(540, 1075)
        c.scale(k, k)
        text(c, 'no.', 0, 0, 92, K['text'], a, tf='serif')
        c.restore()


def sc_day1(c, t, x):
    rect(c, -500, -500, W + 1000, H + 1000, K['bg'])
    glow(c, 540, 2050, 900, K['sun'], 0.22 * ramp(t, 0.1, 0.8))
    title_text(c, 'DAY 1.', 540, 1010, 150, t - 0.05)
    u = eout((t - 0.2) / 0.5)
    if u > 0:
        line(c, 540 - 230 * u, 1070, 540 + 230 * u, 1070, K['text'], w=5, a=0.8)


def sc_run(c, t, x):
    dawn(c, t, horizon=1180, sun_y=1188, sun_r=120, sun_x=760)
    hills(c, t * 140)
    rect(c, -500, 1436, W + 1000, 12, K['path'])
    for i in range(12):
        xx = (i * 170 - t * 1100) % 2040 - 480
        line(c, xx, 1470, xx + 70, 1470, '#1C1C22', w=6)
    w_ = 2 * math.pi * 2.6
    hop = abs(math.sin(w_ * t))
    sq = 1 - 0.14 * (1 - hop) ** 6
    for k, (yy, ln) in enumerate(((1240, 160), (1300, 230), (1360, 130))):
        xx = 300 - ((t * 900 + k * 120) % 260)
        line(c, xx - ln, yy, xx, yy, K['text'], w=5, a=0.25)
    blob(c, 470, 1436 - 60 * hop, 1.05, squash=sq + 0.06 * hop, legs=w_ * t * 1.0, look=(0.7, 0.0), brows=0.8,
         ground_shadow=False)
    oval(c, 470, 1442, 90 * (0.7 + 0.3 * (1 - hop)), 10, '#000000', 0.6, blur=6)


def sc_study(c, t, x):
    rect(c, -500, -500, W + 1000, H + 1000, K['wall'])
    blob(c, 460, 1420, 1.35, look=(0.25, 0.95), blink=0.0, brows=0.5, ground_shadow=False,
         squash=1 + 0.015 * math.sin(3 * t))
    desk_lamp(c, on=1.0)
    book(c, 450, 1340, t)


CAL_N, CAL_D = 30, 1.45


def cal_times():
    return [0.12 + CAL_D * (k / CAL_N) ** 0.62 for k in range(1, CAL_N + 1)]


def sc_calendar(c, t, x):
    rect(c, -500, -500, W + 1000, H + 1000, K['bg'])
    ts = cal_times()
    n = sum(1 for tk in ts if tk <= t)
    dt = clamp((t - ts[n - 1]) / 0.12) if n else 0.0
    calendar(c, 140, 620, 800, 720, n, t, dt)
    text(c, f'DAY {max(n, 1)}', 540, 500, 104, K['text'], 1.0, tf='bold')


def sc_end(c, t, x):
    dawn(c, t, horizon=1250, sun_y=1262 - 70 * ease(t / x.dur), sun_r=150, sun_x=540)
    oval(c, 540, 1420, 560, 190, K['ground'])
    blob(c, 540, 1240, 0.62, look=(0.0, -0.6), brows=0.3, ground_shadow=False, shade=False)
    whisper(c, 'discipline.', 540, 760, t - 0.45, 1.0, size=72, cl=K['text'])


SCENES = {
    'bed': dict(draw=sc_bed, cam=(1.08, 1.15, 430, 1200), vig=VIGNETTE),
    'wake': dict(draw=sc_wake, cam=(1.0, 1.05, 540, 1150)),
    'day1': dict(draw=sc_day1, cam=(1.0, 1.0, 540, 960)),
    'run': dict(draw=sc_run, cam=(1.0, 1.0, 540, 960)),
    'study': dict(draw=sc_study, cam=(1.0, 1.05, 520, 1250)),
    'calendar': dict(draw=sc_calendar, cam=(1.0, 1.03, 540, 960)),
    'end': dict(draw=sc_end, cam=(1.06, 1.0, 540, 1150)),
}


# ---------------------------------------------------------------- sound
def env(n, att, dec):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(att, 1e-4)) * np.exp(-t / dec)


def piano(midi, dur=2.5, vel=1.0):
    f = 440 * 2 ** ((midi - 69) / 12)
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for h, (a, d) in enumerate(((1.0, 1.7), (0.42, 1.0), (0.2, 0.7), (0.1, 0.45), (0.05, 0.3)), 1):
        x += a * np.sin(2 * np.pi * f * h * (1 + 0.0004 * h * h) * t) * np.exp(-t / (d * (330 / max(f, 110)) ** 0.3))
    x *= np.minimum(1, t / 0.004) * np.minimum(1, (t[-1] - t) / 0.25 + 1e-9)
    return x * vel * 0.25


def kick():
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    ph = 2 * np.pi * np.cumsum(45 + 95 * np.exp(-t / 0.035)) / SR
    return np.sin(ph) * np.exp(-t / 0.2) + music.hp(np.random.default_rng(1).standard_normal(n), 2000) * np.exp(-t / 0.003) * 0.3


def hat(rng):
    n = int(0.08 * SR)
    return music.hp(rng.standard_normal(n), 7000) * env(n, 0.001, 0.018)


def beep():
    n = int(0.075 * SR)
    t = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * 2050 * k * t) / k for k in (1, 3, 5))
    return x * np.minimum(1, t / 0.003) * np.minimum(1, (t[-1] - t) / 0.004) * 0.35


def thump(f=55, dec=0.16):
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.6 * t)) * env(n, 0.004, dec)


def drone(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * f * t + p) for f, a, p in ((55, 0.9, 0), (110.3, 0.5, 1), (164.8, 0.25, 2), (220.6, 0.12, 3)))
    x *= 0.75 + 0.25 * np.sin(2 * np.pi * 0.2 * t)
    x += music.lp(np.random.default_rng(4).standard_normal(n), 400) * 0.25
    return x


def scratch(rng):
    n = int(0.09 * SR)
    return music.bp(rng.standard_normal(n), 2500, 7000) * env(n, 0.005, 0.03)


def put(buf, x, t0, gain=1.0):
    s0 = int(round(t0 * SR))
    if s0 >= len(buf):
        return
    x = x[:len(buf) - s0]
    buf[s0:s0 + len(x)] += x * gain


def soundtrack(tl, out_wav):
    dur = tl['duration']
    n = int(math.ceil(dur * SR)) + SR // 10
    spans = {sp['scene']: sp for sp in kit.scene_spans(tl)}
    L = tl['lines']
    rng = np.random.default_rng(9)
    # inner voice: pitched down with its length kept, low-passed, then reverb
    raw = os.path.join(OUT, 'voice', 'narration.wav')
    low = os.path.join(OUT, 'voice', 'voice_low.wav')
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', raw, '-af',
                    f'asetrate=24000*{VOICE_PITCH},aresample={SR},atempo={1 / VOICE_PITCH:.5f}', low], check=True)
    v, _ = sf.read(low)
    v = music.lp(v, VOICE_LP)
    voice = np.zeros(n)
    put(voice, v, ALARM_LEAD)
    voice_st = music.reverb(voice, VOICE_REVERB)
    # music + effects (mono, then reverb)
    mus, fx = np.zeros(n), np.zeros(n)
    t_wh = L[0]['start']
    tt = 0.2
    while tt < t_wh - 0.35:
        for k in range(3):
            put(fx, beep(), tt + k * 0.13)
        tt += 0.62
    bed_end = spans['wake']['start']
    d = drone(bed_end + 0.4)
    d *= np.minimum(1, np.arange(len(d)) / SR / 1.5) * np.minimum(1, (len(d) / SR - np.arange(len(d)) / SR) / 0.35)
    ramp_up = 0.6 + 0.4 * np.clip((np.arange(len(d)) / SR - t_wh) / 3.0, 0, 1)
    put(mus, d * ramp_up, 0.0, MUSIC['drone'])
    for t0, m in ((0.9, 57), (2.6, 64), (4.2, 60), (5.8, 57)):
        if t0 < bed_end:
            put(mus, piano(m, 2.6, 0.7), t0, MUSIC['piano'])
    wk = spans['wake']
    t_open = wk['start'] + (wk['lines'][0]['start'] - wk['start']) + 0.12
    put(fx, thump(52, 0.14), t_open, 0.9)
    put(fx, thump(52, 0.12), t_open + 0.26, 0.6)
    t_no = t_open + 0.63
    put(fx, music.sfx('boom'), t_no, 0.8)
    t_d1 = spans['day1']['start']
    put(fx, music.sfx('boom'), t_d1, 1.0)
    for sc in ('run', 'study', 'calendar', 'end'):
        put(fx, music.sfx('whoosh'), spans[sc]['start'] - 0.35, 0.45)
    beat = 60 / MUSIC['bpm']
    t_end = spans['end']['start']
    k = 0
    while t_d1 + k * beat < t_end + 0.01:
        tb = t_d1 + k * beat
        put(mus, kick(), tb, MUSIC['kick'])
        put(mus, hat(rng), tb + beat / 2, MUSIC['hat'])
        k += 1
    chords = [(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)]          # Am F C G
    step = beat / 2
    k = 0
    while t_d1 + k * step < t_end:
        ch = chords[int(k * step / (4 * beat)) % 4]
        put(mus, piano(ch[k % 3] + 12, 1.2, 0.55), t_d1 + k * step, MUSIC['piano'])
        if k % 8 == 0:
            put(mus, piano(ch[0] - 12, 2.2, 0.8), t_d1 + k * step, MUSIC['piano'])
        k += 1
    for m in (45, 57, 60, 64, 69):
        put(mus, piano(m, 3.2, 0.8), t_end, MUSIC['piano'])
    sp = spans['calendar']
    for i, tk in enumerate(cal_times()):
        put(fx, scratch(rng), sp['start'] + tk, 0.5 * (1 - i / 40))
    mix_ = voice_st * 1.0 + music.reverb(mus, 0.28) + music.reverb(fx, 0.18) * MUSIC['fx']
    mix_ = mix_[:int(round(dur * SR))]
    fade = int(0.6 * SR)
    mix_[-fade:] *= np.linspace(1, 0, fade)[:, None]
    mix_ = mix_ / max(np.abs(mix_).max(), 1e-6) * 0.89
    raw_wav = os.path.splitext(out_wav)[0] + '_raw.wav'
    sf.write(raw_wav, mix_.astype(np.float32), SR)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', raw_wav, '-af', music.LOUDNORM, '-ar', str(SR), out_wav], check=True)
    return out_wav


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--stills', action='store_true')
    ap.add_argument('--frames', default=None)
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    tl = timeline()
    if a.stills or a.frames:
        if a.stills:
            print('wrote', kit.contact_sheet(tl, SCENES, os.path.join(OUT, 'stills.png'), cols=4, thumb=(270, 480), when='late'))
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
    mp4 = kit.concat_and_mux(os.path.join(OUT, 'scenes'), wav, os.path.join(OUT, 'blob_demo.mp4'))
    print('DONE', mp4, f'{tl["duration"]:.2f} s video in {time.time() - t0:.0f} s')


if __name__ == '__main__':
    main()
