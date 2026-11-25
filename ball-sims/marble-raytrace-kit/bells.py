"""The mallet-bell sound of the 3D marble music Shorts, synthesized with numpy/scipy (no samples).

bell(freq, kind)  one struck note. kinds: "lead" (melody, bright 4th partial), "inner" (soft chord tones),
                  "spark" (high, glassy), "bass" (round, long). Each ends with a 50 ms fade.
knock(...)        short marble clacks: on the tray floor, walls, and marble-on-marble.
add(...)          mixes a sound into a stereo buffer at a time, with constant-power pan.
master(buf, s)    shared finish: 2.4 s stereo reverb (34% wet), 35 Hz high-pass, peak normalize, soft tanh limit,
                  0.6 s fade-out, trimmed to s seconds. Returns int16 samples for write_wav().

`rng` is seeded (7) and shared by bell/knock/reverb_ir, so the same calls in the same order give the same audio;
reset_rng() starts it over.
"""
import numpy as np
import scipy.io.wavfile as wavf
import scipy.signal as sig

SR = 48000
SEED = 7
rng = np.random.default_rng(SEED)


def reset_rng(seed=SEED):
    """Restarts the shared generator, so a soundtrack built twice in one process comes out the same."""
    global rng
    rng = np.random.default_rng(seed)
    return rng


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def bell(f, dur=None, kind="lead"):
    if kind == "lead":
        t1 = 1.05 * (523.25 / f) ** 0.35
        parts = [(1.0, 1.0, t1), (2.0, 0.10, t1 * 0.5), (4.0, 0.34, 0.30), (9.85, 0.07, 0.045)]
        click = 0.10
    elif kind == "inner":
        t1 = 0.85 * (261.6 / f) ** 0.3
        parts = [(1.0, 1.0, t1), (2.0, 0.08, t1 * 0.5), (4.0, 0.20, 0.18), (9.85, 0.03, 0.03)]
        click = 0.03
    elif kind == "spark":
        t1 = 1.3 * (1046.5 / f) ** 0.3
        parts = [(1.0, 1.0, t1), (2.76, 0.12, 0.2), (5.4, 0.05, 0.05)]
        click = 0.05
    else:
        t1 = 0.95 * (130.8 / f) ** 0.25
        parts = [(1.0, 1.0, t1), (2.0, 0.18, t1 * 0.45), (4.0, 0.22, 0.12), (9.9, 0.04, 0.02)]
        click = 0.05
    if dur is None:
        dur = min(4.5, max(p[2] for p in parts) * 6.0)
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for ratio, amp, tau in parts:
        fr = f * ratio
        if fr > SR * 0.45:
            continue
        ph = rng.uniform(0, 2 * np.pi)
        y += amp * np.sin(2 * np.pi * fr * t + ph * (ratio != 1.0)) * np.exp(-t / tau)
    att = int(0.0025 * SR)
    y[:att] *= 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, att))
    cn = int(0.012 * SR)
    nz = rng.standard_normal(cn) * np.exp(-np.arange(cn) / (0.0025 * SR))
    b, a = sig.butter(2, [2500 / (SR / 2), 7000 / (SR / 2)], btype="band")
    y[:cn] += click * sig.lfilter(b, a, nz)
    fade = int(0.05 * SR)
    y[-fade:] *= np.linspace(1, 0, fade)
    return y


def knock(freq, tau, noise_amt, dur=0.12):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.sin(2 * np.pi * freq * t) * np.exp(-t / tau)
    y += 0.6 * np.sin(2 * np.pi * freq * 2.31 * t) * np.exp(-t / (tau * 0.5))
    nz = rng.standard_normal(n) * np.exp(-t / 0.004)
    b, a = sig.butter(2, [min(freq * 1.5, 9000) / (SR / 2), min(freq * 4, 20000) / (SR / 2)], btype="band")
    y += noise_amt * sig.lfilter(b, a, nz)
    att = int(0.0008 * SR)
    y[:att] *= np.linspace(0, 1, att)
    return y


def impact_sound(kind, speed, r):
    """Clack for a tray/dish impact from the physics sim. r is the caller's RNG (used for the pitch)."""
    if kind == "ball":
        return knock(r.uniform(2600, 3600), 0.006, 0.5, 0.06), min(1.0, speed / 9.0) ** 1.2 * 0.10
    if kind == "floor":
        return knock(r.uniform(620, 820), 0.020, 0.35, 0.12), min(1.0, speed / 26.0) ** 1.1 * 0.16
    return knock(r.uniform(1000, 1300), 0.012, 0.4, 0.08), min(1.0, speed / 8.0) ** 1.2 * 0.07


def pan_gains(p):
    p = np.clip(p, -1, 1)
    a = (p + 1) * np.pi / 4
    return np.cos(a), np.sin(a)


def add(buf, y, t, gain, pan):
    i = int(round(t * SR))
    if i >= buf.shape[1]:
        return
    n = min(len(y), buf.shape[1] - i)
    gl, gr = pan_gains(pan)
    buf[0, i:i + n] += y[:n] * gain * gl
    buf[1, i:i + n] += y[:n] * gain * gr


def reverb_ir(seconds=2.4, rt60=2.1):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    out = []
    for ch in range(2):
        nz = rng.standard_normal(n)
        env = 10 ** (-3 * t / rt60)
        lo = sig.lfilter(*sig.butter(1, 1800 / (SR / 2)), nz)
        hi = nz - lo
        y = lo * env + hi * 10 ** (-3 * t / (rt60 * 0.45))
        pre = int(0.016 * SR)
        y = np.concatenate([np.zeros(pre), y])[:n]
        for d, g in [(0.011, 0.5), (0.019, 0.35), (0.027, 0.28), (0.041, 0.22)]:
            k = int((d + 0.004 * ch) * SR)
            y[k] += g * 3.0
        out.append(y / np.sqrt((y ** 2).sum()))
    return np.array(out)


def master(buf, total_s):
    ir = reverb_ir()
    wet = np.stack([sig.fftconvolve(buf[0], ir[0])[:buf.shape[1]], sig.fftconvolve(buf[1], ir[1])[:buf.shape[1]]])
    mix = buf * 0.82 + wet * 0.34
    hp = sig.butter(2, 35 / (SR / 2), btype="high")
    mix = sig.lfilter(*hp, mix, axis=1)
    peak = np.abs(mix).max()
    mix = mix / peak * 0.89
    mix = np.tanh(mix * 1.15) / np.tanh(1.15)
    n = int(total_s * SR)
    mix = mix[:, :n]
    fo = int(0.6 * SR)
    mix[:, -fo:] *= np.linspace(1, 0, fo) ** 1.5
    return (mix.T * 32767 * 0.97).astype(np.int16)


def write_wav(path, samples):
    wavf.write(path, SR, samples)
