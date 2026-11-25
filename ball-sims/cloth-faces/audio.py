"""Synthesizes the soundtrack from the sims and the timeline. Writes build/out/audio.wav.
Run:  HERO=duck python3 audio.py [TIMELINE.json OUT.wav]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import settings as CFG
import json, sys, math
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 48000
FPS = 30
MARBLE_C = np.array([0.0, 0.0, 0.32])
MARBLE_R = 0.5
rng = np.random.default_rng(5)


def env_exp(n, tau, attack=0.002):
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * np.exp(-t / tau)


def bandnoise(n, lo, hi, order=2):
    x = rng.standard_normal(n)
    sos = signal.butter(order, [lo, min(hi, SR / 2 - 100)], btype='band', fs=SR, output='sos')
    return signal.sosfilt(sos, x)


def lowpass(x, fc, order=2):
    sos = signal.butter(order, fc, btype='low', fs=SR, output='sos')
    return signal.sosfilt(sos, x)


def highpass(x, fc, order=2):
    sos = signal.butter(order, fc, btype='high', fs=SR, output='sos')
    return signal.sosfilt(sos, x)


def shaped_noise(n, frames_env, centers, widths):
    nper = 1024
    hop = 256
    x = rng.standard_normal(n + nper)
    f, t, Z = signal.stft(x, fs=SR, nperseg=nper, noverlap=nper - hop)
    ft = t * SR / (SR / FPS)
    fe = np.interp(ft, np.arange(len(frames_env)), frames_env)
    fc = np.interp(ft, np.arange(len(centers)), centers)
    fw = np.interp(ft, np.arange(len(widths)), widths)
    lf = np.log2(np.maximum(f, 20))[:, None]
    g = np.exp(-0.5 * ((lf - np.log2(fc)[None, :]) / fw[None, :]) ** 2)
    Z = Z * g * fe[None, :]
    _, y = signal.istft(Z, fs=SR, nperseg=nper, noverlap=nper - hop)
    y = y[:n]
    if len(y) < n:
        y = np.pad(y, (0, n - len(y)))
    return y


def pop(f0=660.0, dur=0.22):
    n = int(SR * dur)
    t = np.arange(n) / SR
    fr = f0 * (1 + 0.7 * (1 - np.exp(-t / 0.03)))
    ph = 2 * np.pi * np.cumsum(fr) / SR
    y = np.sin(ph) * env_exp(n, 0.07, 0.001) + 0.35 * np.sin(2 * ph) * env_exp(n, 0.04, 0.001)
    click = bandnoise(n, 2000, 9000) * env_exp(n, 0.004, 0.0005) * 0.5
    return (y + click) * 0.55


def glock_note(midi, dur=1.4, amp=1.0):
    f = 440 * 2 ** ((midi - 69) / 12)
    n = int(SR * dur)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for r, a, d in ((1.0, 1.0, 0.9), (2.76, 0.35, 0.25), (5.40, 0.18, 0.09), (8.93, 0.08, 0.04)):
        if f * r < SR / 2 - 500:
            y += a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / d)
    y *= np.clip(t / 0.001, 0, 1)
    y += bandnoise(n, 3000, 12000) * env_exp(n, 0.003) * 0.15
    return y * amp


def thump(f0=70, dur=0.35, tau=0.09):
    n = int(SR * dur)
    t = np.arange(n) / SR
    fr = f0 * (1 + 1.2 * np.exp(-t / 0.015))
    ph = 2 * np.pi * np.cumsum(fr) / SR
    return np.sin(ph) * env_exp(n, tau, 0.002)


def slap_plastic(strength=1.0):
    n = int(SR * 0.35)
    y = bandnoise(n, 900, 6000) * env_exp(n, 0.03, 0.0008) * 0.9
    t = np.arange(n) / SR
    y += 0.5 * np.sin(2 * np.pi * 240 * t) * env_exp(n, 0.045)
    y += 0.25 * np.sin(2 * np.pi * 610 * t) * env_exp(n, 0.03)
    y += 0.6 * thump(85, 0.35, 0.06)
    return y * strength


def flop_fabric(strength=1.0, soft=1.0):
    n = int(SR * 0.6)
    y = lowpass(rng.standard_normal(n), 700 + 1200 * (1 - soft)) * env_exp(n, 0.10 + 0.08 * soft, 0.008) * 1.6
    y += 0.7 * thump(62, 0.6, 0.1)
    y += bandnoise(n, 2500, 9000) * env_exp(n, 0.05, 0.01) * 0.12
    return y * strength


def wood_slap(strength=1.0):
    n = int(SR * 0.4)
    t = np.arange(n) / SR
    y = bandnoise(n, 400, 5000) * env_exp(n, 0.025, 0.0008)
    y += 0.6 * np.sin(2 * np.pi * 180 * t) * env_exp(n, 0.06)
    y += 0.3 * np.sin(2 * np.pi * 410 * t) * env_exp(n, 0.04)
    y += 0.5 * thump(75, 0.4, 0.07)
    return y * strength


def far_thud():
    n = int(SR * 1.6)
    y = 0.9 * thump(52, 1.6, 0.16) + lowpass(rng.standard_normal(n), 300) * env_exp(n, 0.12, 0.01) * 0.8
    ir_n = int(SR * 1.4)
    ir = rng.standard_normal(ir_n) * np.exp(-np.arange(ir_n) / SR / 0.35)
    ir = lowpass(ir, 1500)
    wet = signal.fftconvolve(y, ir)[:n] * 0.03
    return (y * 0.6 + wet) * 0.9


def drop_whoosh(dur=0.7):
    n = int(SR * dur)
    nfr = int(dur * FPS) + 2
    envf = np.linspace(0, 1, nfr) ** 0.5 * np.linspace(1, 0, nfr) ** 1.5 * 3
    c = np.linspace(1800, 300, nfr)
    w = np.full(nfr, 0.9)
    return shaped_noise(n, envf, c, w) * 0.6


def gloop(dur=0.55):
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = 210 * np.exp(-t / 0.25) + 85 + 12 * np.sin(2 * np.pi * 9 * t) * np.exp(-t / 0.2)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * env_exp(n, 0.16, 0.01)
    y += 0.4 * np.sin(2 * ph) * env_exp(n, 0.08, 0.01)
    y += lowpass(rng.standard_normal(n), 500) * env_exp(n, 0.1, 0.02) * 0.5
    return y * 0.8


def tick(midi=84):
    return glock_note(midi, 0.25, 0.5) * np.exp(-np.arange(int(SR * 0.25)) / SR / 0.06)


def chime_arp(base=84):
    notes = [base, base + 4, base + 7, base + 12, base + 16]
    out = np.zeros(int(SR * 2.4))
    for i, m in enumerate(notes):
        g = glock_note(m, 1.6, 0.55 - 0.05 * i)
        st = int(SR * 0.07 * i)
        out[st:st + len(g)] += g[:len(out) - st]
    sh = bandnoise(len(out), 6000, 14000) * env_exp(len(out), 0.5, 0.05) * 0.06
    return out + sh


def add(buf, x, t, gain=1.0, pan=0.0):
    i = int(round(t * SR))
    if i >= buf.shape[0]:
        return
    if i < 0:
        x = x[-i:]
        i = 0
    n = min(len(x), buf.shape[0] - i)
    l = math.cos((pan + 1) * math.pi / 4)
    r = math.sin((pan + 1) * math.pi / 4)
    buf[i:i + n, 0] += x[:n] * gain * l * 1.414
    buf[i:i + n, 1] += x[:n] * gain * r * 1.414


_TREE = None


def hero_dist(pts):
    global _TREE
    if _TREE is None:
        from scipy.spatial import cKDTree
        hp = np.load(os.path.join(CFG.SIMS, 'hero_pts.npy'))
        _TREE = cKDTree(hp)
    d, _ = _TREE.query(pts.reshape(-1, 3), k=1)
    return d.reshape(pts.shape[:-1])


def stage_features(pos, mp):
    k = np.asarray(mp)
    k0 = np.floor(k).astype(int)
    k1 = np.minimum(k0 + 1, len(pos) - 1)
    k0 = np.minimum(k0, len(pos) - 1)
    w = (k - k0)[:, None, None]
    P = pos[k0] * (1 - w) + pos[k1] * w
    sub = P[:, ::max(1, P.shape[1] // 4000)]
    d = hero_dist(sub)
    dmin = d.min(1)
    zmean = sub[..., 2].mean(1)
    zmin = sub[..., 2].min(1)
    v = np.zeros(len(P))
    v[1:] = np.linalg.norm(sub[1:] - sub[:-1], axis=2).mean(1) * FPS
    cx = sub[..., 0].mean(1) - sub[..., 1].mean(1)
    on = (d < 0.06).mean(1)
    outside = (np.abs(sub[..., 0]) > 1.12) | (np.abs(sub[..., 1]) > 1.12)
    ffl = ((sub[..., 2] < 0.06) & outside).mean(1)
    return dict(dmin=dmin, zmean=zmean, zmin=zmin, v=v, pan=np.clip(cx * 0.35, -0.6, 0.6), on=on, ffl=ffl)


def music(D, bars=12):
    bpm = bars * 4 * 60.0 / D
    beat = 60.0 / bpm
    n = int(SR * D)
    out = np.zeros((n, 2))
    prog = [(48, [60, 64, 67, 72]), (45, [57, 60, 64, 69]), (41, [57, 60, 65, 69]), (43, [55, 59, 62, 67])]
    for b in range(bars):
        root, ch = prog[b % 4]
        t0 = b * 4 * beat
        for q in (0, 2, 3.5):
            if q == 3.5 and b % 2 == 0:
                continue
            m = root if q != 3.5 else root + 7
            f = 440 * 2 ** ((m - 69) / 12)
            L = int(SR * beat * (1.6 if q == 0 else 1.2))
            t = np.arange(L) / SR
            tri = signal.sawtooth(2 * np.pi * f * t, 0.5)
            x = lowpass(tri, 700) * env_exp(L, beat * 0.9, 0.01) * 0.55
            add(out, x, t0 + q * beat, 0.9, 0.0)
        pat = [0, 2, 1, 3, 2, 1, 3, 2]
        for e in range(8):
            m = ch[pat[e]] + 12
            x = glock_note(m, 0.9, 0.22) * np.exp(-np.arange(int(SR * 0.9)) / SR / 0.25)
            add(out, x, t0 + e * beat * 0.5, 0.55, -0.35 if e % 2 else 0.35)
        for q in range(4):
            if q in (0, 2):
                add(out, thump(58, 0.3, 0.07), t0 + q * beat, 0.5, 0.0)
            hh = highpass(rng.standard_normal(int(SR * 0.05)), 7000) * env_exp(int(SR * 0.05), 0.012, 0.0005)
            add(out, hh, t0 + (q + 0.5) * beat, 0.12, 0.2)
    head = int(SR * 0.004)
    out[:head] *= np.linspace(0, 1, head)[:, None]
    return out


def build(tl_path, out_wav, music_gain=0.28):
    tl = json.load(open(tl_path))
    D = tl['total'] / FPS
    n = int(SR * D)
    sfx = np.zeros((n, 2))
    stage_start = np.cumsum([0] + tl['stage_len'])
    scale = [0, 2, 4, 7, 9, 12, 16]
    for s in range(len(tl['stage_len'])):
        t_s = stage_start[s] / FPS
        add(sfx, pop(523.25 * 2 ** (scale[s] / 12)), t_s, 0.55, 0.0)
        pos = np.load(tl['sims'][s])['pos']
        F = stage_features(pos, tl['maps'][s])
        L = len(F['v'])
        hold = next(i for i, k in enumerate(tl['maps'][s]) if k > 0) if any(k > 0 for k in tl['maps'][s]) else 0
        hit = int(np.argmax(F['dmin'] < 0.03)) if (F['dmin'] < 0.03).any() else None
        vz = np.diff(F['zmean'], prepend=F['zmean'][0])
        acc = np.diff(vz, prepend=vz[0])
        dec = [t for t in range(2, L) if vz[t - 1] < -0.04 and acc[t] > 0.015 and F['zmean'][t] > -0.2]
        if dec:
            hit = dec[0] if hit is None else min(hit, dec[0])
        if hit is not None:
            dur = (hit - hold) / FPS
            nfr = hit - hold + 3
            ev = np.linspace(0, 1, nfr) ** 2
            ev[-3:] = [1.0, 0.4, 0.0]
            wn = shaped_noise(int(SR * nfr / FPS), ev * 2.2, np.linspace(500, 1800, nfr), np.full(nfr, 1.0))
            add(sfx, wn, (stage_start[s] + hold) / FPS, 0.28, float(F['pan'][hit]))
            vhit = float(F['v'][max(hit - 1, 0)])
            st = min(1.2, 0.45 + vhit / 6.0)
            if s <= 2:
                add(sfx, slap_plastic(st), (stage_start[s] + hit) / FPS, 0.7, float(F['pan'][hit]))
            elif s <= 4:
                add(sfx, flop_fabric(st, 0.4), (stage_start[s] + hit) / FPS, 0.8, float(F['pan'][hit]))
            else:
                add(sfx, flop_fabric(st, 1.0), (stage_start[s] + hit) / FPS, 0.9, float(F['pan'][hit]))
                if s == len(tl['stage_len']) - 1:
                    add(sfx, gloop(), (stage_start[s] + hit) / FPS + 0.05, 0.55, 0.0)
            env = np.zeros(L)
            con = np.clip(F['on'] * 5.0, 0, 1)
            env[hit:] = (np.clip(F['v'][hit:] / 2.5, 0, 1.0) ** 0.8) * con[hit:]
            env = np.convolve(env, np.ones(3) / 3, mode='same')
            if s <= 2:
                cen, wid, g = np.full(L, 2600.0), np.full(L, 1.1), 0.22
            elif s <= 4:
                cen, wid, g = np.full(L, 2200.0), np.full(L, 1.0), 0.2
            else:
                cen, wid, g = np.full(L, 3000.0), np.full(L, 0.8), 0.16
            rus = shaped_noise(int(SR * L / FPS), env, cen, wid)
            add(sfx, rus, t_s, g, 0.0)
            if s <= 2:
                dens = env * 18
                for fi in range(hit, L):
                    for _ in range(rng.poisson(dens[fi] / 3)):
                        cl = bandnoise(int(SR * 0.01), 2000, 8000) * env_exp(int(SR * 0.01), 0.0015, 0.0003)
                        add(sfx, cl, (stage_start[s] + fi) / FPS + rng.uniform(0, 1 / FPS), 0.25 * env[fi], rng.uniform(-0.3, 0.3))
        below = np.where(F['zmean'] < -0.35)[0]
        print('stage', s, 'len', L, 'hold', hold, 'hit', hit, 'below', int(below[0]) if len(below) else None, flush=True)
        if len(below):
            b0 = int(below[0])
            add(sfx, drop_whoosh(0.8), (stage_start[s] + b0) / FPS - 0.1, 0.5, float(F['pan'][b0]))
            if b0 + 14 < L + 12:
                add(sfx, far_thud(), (stage_start[s] + b0) / FPS + 0.55, 0.55, 0.0)
        floor = np.where(F['ffl'] > 0.15)[0]
        if len(floor):
            f0 = int(floor[0])
            print('  floor', s, f0, flush=True)
            add(sfx, wood_slap(0.8), (stage_start[s] + f0) / FPS, 0.6, float(F['pan'][f0]))
        if s == len(tl['stage_len']) - 1:
            rv = np.where((F['on'] < 0.02) & (np.arange(L) > (hit or 0) + 10))[0]
            if len(rv):
                add(sfx, chime_arp(84), (stage_start[s] + int(rv[0])) / FPS, 0.5, 0.0)
    t_ref = stage_start[-1] / FPS
    for i in range(7):
        add(sfx, tick(76 + scale[i]) * 0.7, t_ref + (i * tl['refill_stagger'] + tl['refill_len'] - 6 * tl['refill_stagger'] - 1) / FPS, 0.35, 0.0)
    ref_w = shaped_noise(int(SR * 0.7), np.linspace(0, 1, 22) ** 2 * 1.5, np.linspace(600, 2400, 22), np.full(22, 1.0))
    add(sfx, ref_w, t_ref, 0.15, 0.0)
    ir_n = int(SR * 0.9)
    ir = rng.standard_normal((ir_n, 2)) * np.exp(-np.arange(ir_n) / SR / 0.22)[:, None]
    ir = np.stack([lowpass(ir[:, c], 4000) for c in range(2)], 1)
    wet = np.stack([signal.fftconvolve(sfx[:, c], ir[:, c])[:n] for c in range(2)], 1) * 0.012
    sfx = sfx + wet
    mus = music(D)
    mix = sfx + mus * music_gain
    mix = highpass(mix.T, 30).T
    pk = np.max(np.abs(mix))
    mix = mix / pk * 0.89
    rms = np.sqrt(np.mean(mix ** 2))
    target = 10 ** (-15.5 / 20)
    if rms < target:
        g = target / rms
        mix = np.tanh(mix * g * 1.1) / np.tanh(1.1)
        mix *= 0.92 / np.max(np.abs(mix))
    fade = int(SR * 0.01)
    mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
    wavfile.write(out_wav, SR, (mix * 32767).astype(np.int16))
    print('audio', out_wav, D, 'rms dB', 20 * np.log10(np.sqrt(np.mean(mix ** 2))))


if __name__ == '__main__':
    tl = sys.argv[1] if len(sys.argv) > 1 else CFG.TIMELINE
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(CFG.OUT, 'audio.wav')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    build(tl, out)
