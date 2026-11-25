import sys, json, math
import numpy as np
from scipy import signal
from scipy.io import wavfile
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import synth as A
import settings as C

SR = A.SR
FPS = 30
rng = np.random.default_rng(21)


def partial(f, tau, dur=None, phase=None):
    dur = dur or min(2.0, tau * 7)
    n = int(SR * dur)
    t = np.arange(n) / SR
    ph = rng.uniform(0, 2 * np.pi) if phase is None else phase
    return np.sin(2 * np.pi * f * t + ph) * np.exp(-t / tau)


def mixp(*xs):
    n = max(len(x) for x in xs)
    out = np.zeros(n)
    for x in xs:
        out[:len(x)] += x
    return out


def place(buf, x, i0, g=1.0):
    if i0 >= len(buf):
        return
    n = min(len(x), len(buf) - i0)
    buf[i0:i0 + n] += x[:n] * g


def glass_crash(strength=1.0, dur=1.4, npart=80, low=1700, high=9800):
    n = int(SR * dur)
    y = np.zeros(n)
    y += A.bandnoise(n, 1200, 13000) * A.env_exp(n, 0.007, 0.0003) * 1.1
    for i in range(npart):
        on = min(rng.exponential(0.04), 0.35)
        f = 10 ** rng.uniform(np.log10(low), np.log10(high))
        tau = rng.uniform(0.014, 0.085) * (1.6 if f < 3000 else 1.0)
        amp = rng.uniform(0.25, 1.0) * math.exp(-on / 0.18)
        x = mixp(partial(f, tau), 0.35 * partial(f * rng.uniform(2.3, 2.9), tau * 0.6))
        place(y, x * amp * 0.16, int(on * SR))
    y += A.bandnoise(n, 2600, 11500) * A.env_exp(n, 0.16, 0.003) * 0.22
    return y * strength


def clink(strength=1.0, base=2300):
    n = int(SR * 0.9)
    y = np.zeros(n)
    for r_, a_, d_ in ((1.0, 1.0, 0.28), (1.73, 0.55, 0.18), (2.61, 0.35, 0.11), (3.9, 0.2, 0.07)):
        place(y, partial(base * r_, d_), 0, a_)
    y += A.bandnoise(n, 3000, 12000) * A.env_exp(n, 0.002, 0.0002) * 0.6
    return y * 0.35 * strength


def tinkle(strength=1.0):
    f = 10 ** rng.uniform(np.log10(2600), np.log10(9500))
    tau = rng.uniform(0.012, 0.05)
    x = mixp(partial(f, tau), 0.4 * partial(f * rng.uniform(2.2, 2.8), tau * 0.6))
    x[:int(SR * 0.0015)] += A.bandnoise(int(SR * 0.0015), 3000, 12000) * 0.4
    return x * 0.12 * strength


def heavy_thump(kg, strength=1.0):
    f0 = 120 * kg ** -0.13
    n = int(SR * 0.8)
    y = A.thump(f0, 0.8, 0.07 + 0.05 * math.log10(kg + 1)) * 0.9
    y += A.lowpass(rng.standard_normal(n), 400) * A.env_exp(n, 0.06, 0.002) * 0.7
    return y * strength


def crunch(strength=1.0):
    n = int(SR * 0.6)
    y = A.bandnoise(n, 700, 7000) * A.env_exp(n, 0.09, 0.002)
    for i in range(30):
        on = min(rng.exponential(0.05), 0.3)
        place(y, tinkle(rng.uniform(0.5, 1.2)), int(on * SR), 1.0)
    return y * strength


def out_time(tl, s, k, stage_start):
    mp = tl['maps'][s]
    for f, v in enumerate(mp):
        if v >= k - 1e-6:
            return (stage_start[s] + f) / FPS
    return (stage_start[s] + len(mp)) / FPS


def build(tl_path, out_wav, music_gain=0.17):
    tl = json.load(open(tl_path))
    D = tl['total'] / FPS
    n = int(SR * D)
    L = np.zeros(n)
    Rr = np.zeros(n)
    def add(x, t, g=1.0, pan=0.0):
        i = int(round(t * SR))
        l = math.cos((pan + 1) * math.pi / 4) * 1.414
        r = math.sin((pan + 1) * math.pi / 4) * 1.414
        place(L, x * l, i, g)
        place(Rr, x * r, i, g)
    stage_start = np.cumsum([0] + tl['stage_len'])
    scale = [0, 2, 4, 7, 9, 12, 16]
    for s in range(len(tl['stage_len'])):
        t_s = stage_start[s] / FPS
        add(A.pop(523.25 * 2 ** (scale[s] / 12)), t_s, 0.5)
        d = np.load(tl['sims'][s])
        ev = json.loads(str(d['events']))
        kg = tl['kgs'][s]
        bp = d['ball_pos']
        Lsim = min(len(bp), int(math.ceil(max(tl['maps'][s]))) + 1)
        breaks = [e for e in ev if e['type'] == 'break']
        hits = [e for e in ev if e['type'] == 'ball_hit']
        rel = out_time(tl, s, 0.01, stage_start)
        fall = A.shaped_noise(int(SR * 0.5), np.linspace(0, 1, 16) ** 2 * 1.2, np.linspace(500, 1500, 16), np.full(16, 1.0))
        first = breaks[0]['frame'] if breaks else (hits[0]['frame'] if hits else 15)
        add(fall, out_time(tl, s, max(0, first - 15), stage_start), 0.18 + 0.05 * math.log10(kg + 1))
        for i, e in enumerate(breaks):
            t = out_time(tl, s, e['frame'], stage_start)
            pan = float(np.clip(bp[min(e['frame'], len(bp) - 1)][0] - bp[min(e['frame'], len(bp) - 1)][1], -0.5, 0.5))
            st = 0.75 + 0.25 * min(1.0, e['speed'] / 5.0)
            add(glass_crash(st, npart=70 + 8 * i, low=1600 - 60 * i, high=9800 - 300 * i), t, 0.9, pan)
            if i == 0:
                add(heavy_thump(kg, 0.8), t, 0.8)
        for e in hits:
            if any(abs(e['frame'] - b['frame']) <= 2 for b in breaks):
                continue
            t = out_time(tl, s, e['frame'], stage_start)
            st = min(1.2, e['dv'] / 4.0)
            if e['z'] - float(d['r']) < 0.06:
                add(heavy_thump(kg, st), t, 0.9)
                add(crunch(0.7 * st), t, 0.6)
            else:
                add(clink(st, base=2300 * (kg ** -0.08)), t, 0.8)
                add(heavy_thump(kg, 0.35 * st), t, 0.5)
        P = d['sh_pos'][:Lsim]
        if P.shape[1] > 0:
            v = np.zeros(P.shape[:2])
            dP = np.linalg.norm(np.nan_to_num(P[1:] - P[:-1], nan=0.0), axis=2) * FPS
            v[1:] = dP
            imp = (v[:-1] > 0.7) & (v[1:] < 0.45 * v[:-1])
            env_r = np.zeros(Lsim)
            for k in range(1, Lsim):
                cnt = int(imp[k - 1].sum())
                env_r[k] = float(np.clip(v[k][v[k] > 0.05].sum() / 40.0, 0, 1.5)) if (v[k] > 0.05).any() else 0.0
                if cnt:
                    mags = v[k - 1][imp[k - 1]]
                    nt = min(cnt, 9)
                    g = 1.0 / math.sqrt(max(1, cnt / 3))
                    t = out_time(tl, s, k, stage_start)
                    for j in range(nt):
                        add(tinkle(min(1.3, 0.35 + mags[j % len(mags)] / 3.0)), t + rng.uniform(0, 1.0 / FPS), 0.8 * g, rng.uniform(-0.6, 0.6))
            nfr = tl['stage_len'][s]
            env_out = np.zeros(nfr)
            for f in range(nfr):
                kf = tl['maps'][s][f]
                env_out[f] = env_r[min(int(kf), Lsim - 1)]
            rat = A.shaped_noise(int(SR * nfr / FPS), env_out, np.full(nfr, 5200.0), np.full(nfr, 0.7))
            add(rat, t_s, 0.06)
    n2 = len(L)
    sfx = np.stack([L, Rr], 1)
    ir_n = int(SR * 0.8)
    ir = rng.standard_normal((ir_n, 2)) * np.exp(-np.arange(ir_n) / SR / 0.2)[:, None]
    ir = np.stack([A.lowpass(ir[:, c], 6000) for c in range(2)], 1)
    wet = np.stack([signal.fftconvolve(sfx[:, c], ir[:, c])[:n2] for c in range(2)], 1) * 0.01
    sfx = sfx + wet
    mus = A.music(D)[:n2]
    mix = sfx + mus * music_gain
    mix = A.highpass(mix.T, 30).T
    mix = mix / np.max(np.abs(mix)) * 0.89
    rms = np.sqrt(np.mean(mix ** 2))
    target = 10 ** (-16.0 / 20)
    if rms < target:
        g = target / rms
        mix = np.tanh(mix * g * 1.05) / np.tanh(1.05)
        mix *= 0.92 / np.max(np.abs(mix))
    fade = int(SR * 0.01)
    mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
    wavfile.write(out_wav, SR, (mix * 32767).astype(np.int16))
    print('audio', out_wav, D, 'rms dB', round(20 * np.log10(np.sqrt(np.mean(mix ** 2))), 1))


if __name__ == '__main__':
    tl = sys.argv[1] if len(sys.argv) > 1 else C.TIMELINE
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(C.OUT, 'audio.wav')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    build(tl, out)
