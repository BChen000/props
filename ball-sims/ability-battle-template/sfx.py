#!/usr/bin/env python3
"""sfx: synthesized sound effects for POWER BALLS (numpy + scipy, no samples).

Every sound is built from oscillators, filtered noise and envelopes, so nothing here is licensed audio.
Also holds the DSP helpers and drum hits that music.py builds on, and add() for mixing into a buffer.
All randomness comes from one generator (reseed(SEED)), so a given call order always gives the same audio.

    python sfx.py --export assets           # writes every sound as a 44.1 kHz mono WAV
    python sfx.py --preview preview.png     # waveform sheet (needs matplotlib)
"""
import math
import sys
import wave
from pathlib import Path

import numpy as np
from scipy import signal

# ---------------------------------------------------------------- settings
SR = 44100
SEED = 1774
HIT_PITCH = {0: 1.0, 1: 1.12, 2: 0.9, 3: 1.22}   # per victim index, so each color sounds a little different

rng = np.random.default_rng(SEED)


def reseed(seed=SEED):
    global rng
    rng = np.random.default_rng(seed)


# ---------------------------------------------------------------- dsp helpers
def tt(d):
    return np.arange(int(d * SR)) / SR


def lp(x, f, order=2):
    sos = signal.butter(order, min(f, SR * 0.45), 'low', fs=SR, output='sos')
    return signal.sosfilt(sos, x)


def hp(x, f, order=2):
    sos = signal.butter(order, f, 'high', fs=SR, output='sos')
    return signal.sosfilt(sos, x)


def bp(x, f1, f2, order=2):
    sos = signal.butter(order, [f1, min(f2, SR * 0.45)], 'band', fs=SR, output='sos')
    return signal.sosfilt(sos, x)


def noise(d):
    return rng.standard_normal(int(d * SR))


def sweep(f0, f1, d, curve='exp'):
    t = tt(d)
    if curve == 'exp':
        f = f0 * (f1 / f0) ** (t / d)
    else:
        f = f0 + (f1 - f0) * t / d
    return 2 * np.pi * np.cumsum(f) / SR


def saw_add(freq, d, nh=None, detune=0.0):
    t = tt(d)
    nh = nh or max(1, int(9000 / freq))
    out = np.zeros_like(t)
    ph0 = rng.uniform(0, 2 * np.pi)
    f = freq * (1 + detune)
    for k in range(1, nh + 1):
        if k * f > 16000:
            break
        out += np.sin(2 * np.pi * k * f * t + ph0 * k) / k
    return out * 0.6


def square_add(freq, d):
    t = tt(d)
    out = np.zeros_like(t)
    for k in range(1, 40, 2):
        if k * freq > 12000:
            break
        out += np.sin(2 * np.pi * k * freq * t) / k
    return out * 0.8


def env_exp(d, tau, attack=0.002):
    t = tt(d)
    e = np.exp(-t / tau)
    a = int(attack * SR)
    if a > 0:
        e[:a] *= np.linspace(0, 1, a)
    return e


def norm(x, peak=1.0):
    m = np.max(np.abs(x)) + 1e-9
    return x * (peak / m)


def resample_rate(x, rate):
    """Play x at `rate` (0.5 = half speed, an octave lower; used for slow-motion events)."""
    n_out = int(len(x) / rate)
    idx = np.arange(n_out) * rate
    return np.interp(idx, np.arange(len(x)), x)


def add(buf, x, at, gain=1.0, pan=0.0):
    """Mix mono x into stereo buf (2 x N) at `at` seconds, with click-free edges and constant-power pan."""
    x = np.array(x, dtype=float)
    fi = min(len(x) // 4, int(0.0007 * SR))
    fo = min(len(x) // 4, int(0.006 * SR))
    if fi > 0:
        x[:fi] *= np.linspace(0, 1, fi)
    if fo > 0:
        x[-fo:] *= np.linspace(1, 0, fo)
    i = int(round(at * SR))
    if i >= buf.shape[1] or i + len(x) <= 0:
        return
    j0 = max(0, -i)
    x = x[j0:]
    i = max(0, i)
    n = min(len(x), buf.shape[1] - i)
    l = math.cos((pan + 1) * math.pi / 4) * math.sqrt(2)
    r = math.sin((pan + 1) * math.pi / 4) * math.sqrt(2)
    buf[0, i:i + n] += x[:n] * gain * l
    buf[1, i:i + n] += x[:n] * gain * r


# ---------------------------------------------------------------- ability sounds
def sfx_pew(n):
    """360 blaster volley; slightly louder with more bullets (n)."""
    d = 0.22
    out = np.zeros(int(d * SR) + int(0.03 * SR))
    for j in range(3):
        off = int(j * 0.008 * SR)
        ph = sweep(1900 + 150 * j, 260, 0.16)
        s = np.sign(np.sin(ph)) * 0.5 + np.sin(ph) * 0.5
        s = lp(s, 5000) * env_exp(0.16, 0.05)
        out[off:off + len(s)] += s * (1 - 0.25 * j)
    nz = hp(noise(0.05), 2500) * env_exp(0.05, 0.012)
    out[:len(nz)] += nz * 0.5
    return norm(out) * (0.55 + 0.02 * min(n, 14))


def sfx_laser_charge(d=0.75):
    t = tt(d)
    f = 280 * (1600 / 280) ** (t / d)
    ph = 2 * np.pi * np.cumsum(f * (1 + 0.02 * np.sin(2 * np.pi * 28 * t))) / SR
    s = np.sin(ph) + 0.3 * np.sin(2 * ph)
    amp = (t / d) ** 1.6
    tail = np.ones_like(t)
    s = s * amp * tail
    s += 0.15 * hp(noise(d), 3000) * amp
    return norm(s) * 0.38


def sfx_laser_fire(d=0.42):
    t = tt(d)
    fm = 110 * (1 + 0.15 * np.sin(2 * np.pi * 60 * t))
    ph = 2 * np.pi * np.cumsum(fm) / SR
    buzz = sum(np.sin(k * ph) / k for k in range(1, 30))
    hi = np.sin(sweep(2400, 900, d)) * 0.5
    s = lp(buzz, 4500) * 0.8 + hi + 0.35 * bp(noise(d), 800, 6000)
    env = np.minimum(1, t / 0.006) * np.where(t < 0.26, 1.0, np.exp(-(t - 0.26) / 0.05))
    thump = np.sin(sweep(160, 45, 0.25)) * env_exp(0.25, 0.08)
    s = s * env
    s[:len(thump)] += thump * 1.2
    return np.tanh(norm(s) * 1.6) * 0.8


def sfx_whoosh(d=0.4, f0=700, f1=3000):
    nz = noise(d)
    out = np.zeros_like(nz)
    seg = int(0.02 * SR)
    for i in range(0, len(nz), seg):
        u = i / len(nz)
        fc = f0 * (f1 / f0) ** u
        out[i:i + seg] = bp(nz[max(0, i - 2048):i + seg], fc * 0.7, fc * 1.4)[-len(nz[i:i + seg]):]
    env = np.sin(np.pi * np.clip(tt(d) / d, 0, 1)) ** 1.5
    return norm(out * env)


def sfx_missile_launch():
    w = sfx_whoosh(0.38, 600, 2600)
    th = np.sin(sweep(140, 60, 0.12)) * env_exp(0.12, 0.04)
    w[:len(th)] += th * 0.7
    return norm(w) * 0.5


def sfx_explosion(big=1.0, d=0.9):
    nz = noise(d)
    body = lp(nz, 900 if big > 0.7 else 1400) * env_exp(d, 0.18 * big + 0.05)
    crack = hp(noise(0.08), 2000) * env_exp(0.08, 0.02)
    sub = np.sin(sweep(90, 32, 0.5)) * env_exp(0.5, 0.16 * big + 0.05)
    crunch = bp(noise(0.35), 400, 3200) * env_exp(0.35, 0.07)
    out = body * 1.2
    out[:len(sub)] += sub * 1.2 * big
    out[:len(crack)] += crack * 0.6
    out[:len(crunch)] += crunch * 0.9
    return np.tanh(norm(out) * 1.5) * (0.55 + 0.35 * big)


def sfx_lightning():
    d = 0.42
    t = tt(d)
    out = np.zeros_like(t)
    n_gr = 70
    for _ in range(n_gr):
        st = int(abs(rng.normal(0, 0.09)) * SR)
        ln = int(rng.uniform(0.002, 0.012) * SR)
        if st + ln < len(out):
            out[st:st + ln] += rng.standard_normal(ln) * rng.uniform(0.3, 1.0)
    out = hp(out, 1200)
    snap = hp(noise(0.012), 1500) * env_exp(0.012, 0.004) * 2.5
    out[:len(snap)] += snap
    ph = 2 * np.pi * 75 * t
    buzz = np.sign(np.sin(ph)) * env_exp(d, 0.08) * 0.25
    rumble = lp(noise(d), 200) * env_exp(d, 0.15) * 1.5
    out = out + lp(buzz, 2500) + rumble
    return np.tanh(norm(out) * 1.4) * 0.62


# ---------------------------------------------------------------- combat sounds
def sfx_hit(pitch=1.0):
    d = 0.22
    body = np.sin(sweep(260 * pitch, 70 * pitch, 0.12)) * env_exp(0.12, 0.05)
    out = np.zeros(int(d * SR))
    out[:len(body)] += body * 1.2
    nz = bp(noise(d), 900, 5000) * env_exp(d, 0.035)
    out += nz * 0.8
    click = hp(noise(0.004), 3000)
    out[:len(click)] += click * 0.8
    return np.tanh(norm(out) * 1.8) * 0.72


def sfx_ko():
    boom = sfx_explosion(1.0, 1.4)
    t = tt(0.75)
    tone = square_add(1.0, 0.75)  # same call as the video (shape is replaced below)
    ph = sweep(900, 90, 0.75)
    tone = lp(np.sign(np.sin(ph)) * 0.6 + np.sin(ph) * 0.4, 3000) * np.exp(-t / 0.35)
    shatter = hp(noise(0.5), 3500) * env_exp(0.5, 0.12)
    out = boom.copy()
    out[:len(tone)] += tone * 0.35
    out[:len(shatter)] += shatter * 0.25
    return np.tanh(norm(out) * 1.3) * 0.95


def sfx_bump():
    d = 0.08
    s = np.sin(2 * np.pi * 520 * tt(d)) * env_exp(d, 0.018) + 0.3 * hp(noise(d), 2000) * env_exp(d, 0.006)
    return norm(s) * 0.22


def sfx_tick():
    d = 0.05
    s = hp(noise(d), 3000) * env_exp(d, 0.006) + np.sin(2 * np.pi * 1800 * tt(d)) * env_exp(d, 0.01) * 0.5
    return norm(s) * 0.08


def sfx_absorb():
    d = 0.25
    s = np.sin(2 * np.pi * 2100 * tt(d)) * env_exp(d, 0.05) + 0.5 * np.sin(2 * np.pi * 3150 * tt(d)) * env_exp(d, 0.03)
    return norm(s) * 0.25


def sfx_upgrade():
    out = np.zeros(int(0.18 * SR))
    for j, f in enumerate([988, 1319, 1976]):
        st = int(j * 0.045 * SR)
        d = 0.09
        s = (np.sin(2 * np.pi * f * tt(d)) + 0.25 * np.sign(np.sin(2 * np.pi * f * tt(d)))) * env_exp(d, 0.03)
        out[st:st + len(s)] += s
    return norm(lp(out, 7000)) * 0.2


# ---------------------------------------------------------------- intro / drama
def sfx_pop():
    d = 0.12
    s = np.sin(sweep(300, 900, d)) * env_exp(d, 0.04)
    return norm(s) * 0.35


def sfx_riser(d):
    t = tt(d)
    w = sfx_whoosh(d, 300, 6000)
    w *= (t / d) ** 2
    tone = np.sin(sweep(110, 880, d)) * (t / d) ** 2 * 0.3
    return norm(w + tone) * 0.45


def sfx_crash(d=2.0):
    nz = hp(noise(d), 4000)
    s = nz * env_exp(d, 0.5)
    return norm(s) * 0.45


def sfx_stab(d=0.5):
    """A-minor brass-ish chord stab on FIGHT!"""
    stab = np.zeros(int(d * SR))
    for f in (220.0, 261.63, 329.63, 440.0):
        stab += saw_add(f, d, nh=14) + saw_add(f, d, nh=14, detune=0.006)
    stab = lp(stab * env_exp(d, 0.14, 0.004), 4000)
    return norm(stab) * 0.45


def heartbeat():
    out = np.zeros(int(0.5 * SR))
    for st, g in [(0.0, 1.0), (0.17, 0.75)]:
        ph = sweep(110, 50, 0.16)
        s = (np.sin(ph) + 0.6 * np.sin(2 * ph) + 0.3 * np.sin(3 * ph)) * env_exp(0.16, 0.045)
        s += bp(noise(0.16), 150, 900) * env_exp(0.16, 0.02) * 0.6
        i = int(st * SR)
        out[i:i + len(s)] += s * g
    return np.tanh(norm(lp(out, 1200)) * 1.6) * 0.9


def tension_drone(d):
    """Slow-motion bed: low hum + tremolo saws + airy noise (normalized, 0.3 peak)."""
    dt_ = tt(d)
    trem = 0.6 + 0.4 * np.sin(2 * np.pi * 7 * dt_)
    drone = (np.sin(2 * np.pi * 55 * dt_) * 0.6
             + saw_add(220.0, d, nh=10) * 0.25 * trem
             + saw_add(311.13, d, nh=8) * 0.18 * trem)
    drone *= np.minimum(1, dt_ / 0.8)
    drone += bp(noise(d), 300, 1500) * 0.12 * np.minimum(1, dt_ / 1.5)
    return lp(norm(drone), 3000) * 0.3


def sub_drop(d=2.0):
    sub = np.sin(sweep(70, 28, d)) * env_exp(d, 0.6)
    return np.tanh(sub * 1.5) * 0.9


# ---------------------------------------------------------------- drums (used by music.py)
def kick(d=0.36, gain=1.0):
    t = tt(d)
    f = 55 + 150 * np.exp(-t / 0.03)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-t / 0.17) + 0.35 * np.sin(2 * ph) * np.exp(-t / 0.06)
    click = bp(noise(0.012), 1500, 6000) * env_exp(0.012, 0.003) * 0.9
    s[:len(click)] += click
    return np.tanh(s * 1.8) * gain


def clap():
    d = 0.28
    out = np.zeros(int(d * SR))
    for j in range(3):
        st = int(j * 0.011 * SR)
        b = noise(0.012) * env_exp(0.012, 0.004)
        out[st:st + len(b)] += b
    tail = noise(d) * env_exp(d, 0.07)
    tail[:int(0.03 * SR)] *= np.linspace(0, 1, int(0.03 * SR))
    out += tail * 0.7
    return norm(bp(out, 900, 3800)) * 0.55


def hat(open_=False):
    d = 0.2 if open_ else 0.06
    s = hp(noise(d), 7000) * env_exp(d, 0.07 if open_ else 0.015)
    return norm(s) * (0.22 if open_ else 0.14)


# ---------------------------------------------------------------- export / preview
CATALOG = [  # (file name, builder, what it is used for in the video)
    ('blaster_volley', lambda: sfx_pew(8), '360 blaster ring of bullets'),
    ('laser_charge', sfx_laser_charge, 'laser charging (0.75 s, plays with the aim line)'),
    ('laser_fire', sfx_laser_fire, 'laser beam firing'),
    ('missile_launch', sfx_missile_launch, 'missile volley launch'),
    ('missile_hit', lambda: sfx_explosion(0.55, 0.6), 'missile explodes on a fighter'),
    ('missile_miss', lambda: sfx_explosion(0.35, 0.6), 'missile hits a wall or runs out'),
    ('lightning_zap', sfx_lightning, 'lightning strike'),
    ('hit', sfx_hit, 'a fighter loses a heart (pitch x1.0/1.12/0.9/1.22 for red/blue/green/yellow)'),
    ('ko', sfx_ko, 'knockout explosion + power-down'),
    ('bump', sfx_bump, 'two balls bounce off each other'),
    ('wall_tick', sfx_tick, 'bullet hits the wall'),
    ('shield_tink', sfx_absorb, 'bullet blocked by i-frames'),
    ('upgrade', sfx_upgrade, 'power-up chime after landing a hit'),
    ('intro_pop', sfx_pop, 'fighter pops into PICK YOUR FIGHTER'),
    ('riser', lambda: sfx_riser(2.45), 'build-up into FIGHT!'),
    ('fight_stab', sfx_stab, 'chord stab on FIGHT!'),
    ('crash', lambda: sfx_crash(2.0), 'cymbal crash (FIGHT!, final blow, winner)'),
    ('slowmo_whoosh', lambda: sfx_whoosh(0.9, 3000, 200) * 0.5, 'slow-motion starts'),
    ('tension_drone', lambda: tension_drone(2.5), 'under the slow-motion final blow'),
    ('heartbeat', heartbeat, 'repeats every 0.85 s during slow motion'),
    ('sub_drop', sub_drop, 'final blow low-end drop'),
]


def write_wav(path, x, sr=SR):
    x = np.clip(np.asarray(x, dtype=float), -1, 1)
    data = (x * 32767).astype(np.int16)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1 if data.ndim == 1 else data.shape[0])
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.T.tobytes() if data.ndim > 1 else data.tobytes())


def export(dest):
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    reseed()
    for name, fn, _ in CATALOG:
        write_wav(dest / f'{name}.wav', fn())
    return [dest / f'{n}.wav' for n, _, _ in CATALOG]


def preview(path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    reseed()
    cols = 3
    rows = math.ceil(len(CATALOG) / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(13, rows * 1.25), facecolor='#130D22')
    for ax, (name, fn, _) in zip(axes.flat, CATALOG):
        x = fn()
        t = np.arange(len(x)) / SR
        ax.set_facecolor('#0D0D17')
        ax.plot(t, x, color='#FED64D', lw=0.6)
        ax.set_ylim(-1, 1)
        ax.set_title(f'{name}  ({len(x) / SR:.2f} s)', color='white', fontsize=9, loc='left')
        ax.tick_params(colors='#8a86a0', labelsize=6)
        for sp in ax.spines.values():
            sp.set_color('#504A61')
    for ax in list(axes.flat)[len(CATALOG):]:
        ax.axis('off')
    fig.suptitle('POWER BALLS sound set (synthesized)', color='white', fontsize=13, y=0.995)
    fig.tight_layout()
    fig.savefig(path, dpi=90, facecolor=fig.get_facecolor())


def style():
    return {
        'sample_rate': SR, 'format': '16-bit PCM WAV, mono', 'noise_seed': SEED, 'hit_pitch_by_victim': HIT_PITCH,
        'sounds': [{'file': f'{n}.wav', 'use': u} for n, _, u in CATALOG],
        'slow_motion': 'events inside the slow-mo window play at rate 0.5 (an octave down) with gain x1.1',
        'edges': 'add() fades the first 0.7 ms and last 6 ms of every sound to avoid clicks',
    }


if __name__ == '__main__':
    if '--export' in sys.argv:
        out = sys.argv[sys.argv.index('--export') + 1]
        files = export(out)
        print('wrote', len(files), 'sounds to', out)
    elif '--preview' in sys.argv:
        out = sys.argv[sys.argv.index('--preview') + 1]
        preview(out)
        print('wrote', out)
    elif '--style' in sys.argv:
        import json
        out = sys.argv[sys.argv.index('--style') + 1]
        Path(out).write_text(json.dumps(style(), indent=2))
        print('wrote', out)
    else:
        print(__doc__)
