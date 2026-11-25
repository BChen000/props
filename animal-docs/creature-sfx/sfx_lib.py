"""creature-sfx / sfx_lib.py: synthesized creature, fire and weather sounds (numpy + scipy, no samples).

Every generator returns float32 stereo (n, 2) at SR unless noted. Noise comes from the Generator you pass, so a
fixed seed and a fixed call order give a sample-identical soundtrack. Track keeps that state for a whole film:

    T = Track(dur=60.0, seed=11)
    wind = wind_bed(T.rng, T.N)                       # full-length beds first ...
    T.bed(wind, 0.0, 6.9, gain=1.0, fade=0.6)
    T.add(roar(2.1, f0=92, seed=3, gain=0.34), 31.2)   # ... then one-shot events
    T.write("out/sfx.wav")                             # peak-limited to 0.9 if it went over

Settings: SR = 48000.
"""
import numpy as np
import scipy.signal as ss
import soundfile as sf

SR = 48000


# ---------------- filters and noise ----------------
def bp(x, lo, hi, order=2):
    sos = ss.butter(order, [lo, hi], btype='band', fs=SR, output='sos')
    return ss.sosfilt(sos, x, axis=0)


def lp(x, f, order=2):
    sos = ss.butter(order, f, btype='low', fs=SR, output='sos')
    return ss.sosfilt(sos, x, axis=0)


def hp(x, f, order=2):
    sos = ss.butter(order, f, btype='high', fs=SR, output='sos')
    return ss.sosfilt(sos, x, axis=0)


def pink(rng, n, ch=2):
    w = rng.standard_normal((n, ch))
    b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
    a = [1, -2.494956002, 2.017265875, -0.522189400]
    return ss.lfilter(b, a, w, axis=0) * 8


def brown(rng, n, ch=2):
    w = rng.standard_normal((n, ch))
    y = np.cumsum(w, axis=0)
    y = hp(y, 15)
    return y / (np.abs(y).max() + 1e-9)


def slow_mod(n, rate=0.2, depth=0.5, seed=0):
    """Smooth random gain between 1-depth and 1, changing about 4*rate times a second."""
    r = np.random.default_rng(seed)
    k = int(n / SR * rate * 4) + 4
    pts = r.uniform(1 - depth, 1, k)
    return np.interp(np.linspace(0, k - 1, n), np.arange(k), pts).astype(np.float32)


# ---------------- beds (full-length, envelope them with Track.bed) ----------------
def wind_bed(rng, n):
    w = bp(pink(rng, n), 120, 1400) * 0.05
    return w * slow_mod(n, 0.25, 0.6, 1)[:, None]


def volcano_bed(rng, n, cracks=None):
    """Low rumble plus random rock cracks and crackle (about 9 cracks a second unless cracks= is given)."""
    rumble = lp(brown(rng, n), 140) * 0.55
    crack = np.zeros((n, 2), np.float32)
    for k in range(cracks if cracks is not None else int(round(9.25 * n / SR))):
        p = int(rng.uniform(0, n - 400))
        crack[p:p + 300, rng.integers(0, 2)] += rng.uniform(0.2, 1.0) * np.exp(-np.arange(300) / 40.0) * rng.standard_normal(300)
    return rumble + bp(crack, 900, 6000) * 0.06


def river_bed(rng, n, bubbles=None):
    """Running water: band-limited noise plus small rising bubble chirps (about 29 a second unless bubbles= is given)."""
    river = bp(pink(rng, n), 300, 4500) * 0.045
    bub = np.zeros((n, 2), np.float32)
    for k in range(bubbles if bubbles is not None else int(round(28.9 * n / SR))):
        p = int(rng.uniform(0, n - 2000)); f = rng.uniform(500, 2200); L = int(rng.uniform(300, 1500))
        tt = np.arange(L) / SR
        bub[p:p + L, rng.integers(0, 2)] += np.sin(2 * np.pi * f * tt * (1 + 2 * tt)) * np.exp(-tt * 60) * rng.uniform(0.1, 0.5)
    return river + bub * 0.02


def rain_bed(rng, n, ticks=None):
    """Hiss plus individual drop ticks (about 116 a second unless ticks= is given)."""
    rain = hp(pink(rng, n), 1800) * 0.06
    drops = np.zeros((n, 2), np.float32)
    for k in range(ticks if ticks is not None else int(round(115.6 * n / SR))):
        p = int(rng.uniform(0, n - 200))
        drops[p:p + 120, rng.integers(0, 2)] += rng.standard_normal(120) * np.exp(-np.arange(120) / 18.0) * rng.uniform(0.05, 0.4)
    return rain + hp(drops, 2500) * 0.08


def gust_bed(rng, n):
    return bp(pink(rng, n), 80, 900) * 0.06 * slow_mod(n, 0.5, 0.9, 5)[:, None]


# ---------------- events ----------------
def thunder(rng, dur=4.5, crack=True, seed=0):
    """Rolling thunder; with crack=True a sharp 0.4 s crack on top (place it ~0.12 s after the flash)."""
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    x = lp(brown(rng, n) * 1.0, 260)
    e = np.exp(-np.arange(n) / (SR * 1.3)) * (1 - np.exp(-np.arange(n) / (SR * 0.06)))
    mod = slow_mod(n, 3.0, 0.8, seed + 2)
    y = x * (e * mod)[:, None] * 0.9
    if crack:
        c = r.standard_normal((int(0.4 * SR), 2)) * np.exp(-np.arange(int(0.4 * SR)) / (SR * 0.06))[:, None]
        c = bp(c, 700, 7000) * 0.5
        y[:len(c)] += c
    return y


def whoosh(rng, dur, lo=100, hi=900, peak=0.5):
    """Pass-by air: band-limited noise under a Gaussian swell peaking at peak*dur."""
    n = int(dur * SR)
    x = bp(pink(rng, n), lo, hi)
    tt = np.linspace(0, 1, n)
    e = np.exp(-((tt - peak) / 0.22) ** 2)
    return x * e[:, None] * 0.5


def flap(rng, gain=1.0):
    """One big wingbeat (0.55 s). Start it ~0.1 s before the downstroke frame."""
    n = int(0.55 * SR)
    x = bp(pink(rng, n), 60, 520)
    tt = np.arange(n) / SR
    e = (1 - np.exp(-tt / 0.06)) * np.exp(-tt / 0.16)
    return x * e[:, None] * gain


def growl(dur, f0=48, seed=0, gain=1.0):
    """Low throat growl: a jittered sawtooth through band-passes and soft clipping."""
    n = int(dur * SR)
    tt = np.arange(n) / SR
    r = np.random.default_rng(seed)
    jit = np.cumsum(r.standard_normal(n)) / SR * 30
    f = f0 * (1 + 0.06 * np.sin(2 * np.pi * 7 * tt)) + jit
    ph = 2 * np.pi * np.cumsum(f) / SR
    saw = 2 * ((ph / (2 * np.pi)) % 1) - 1
    nz = r.standard_normal(n) * 0.5
    x = saw * (0.6 + 0.4 * np.sin(2 * np.pi * 13 * tt)) + nz * 0.4
    y = bp(x, 40, 500) + 0.5 * bp(x, 500, 1100) * 0.4
    y = np.tanh(y * 2.5)
    e = np.minimum(1, tt / 0.6) * np.minimum(1, (dur - tt) / 0.5)
    return np.stack([y * e, y * e], 1) * gain * 0.35


def roar(dur=2.0, f0=95, seed=3, gain=1.0):
    """A big creature roar: pitch swell at 0.5 s, vocal formants (380-900, 1000-1500, 2200-3000 Hz), soft clipping."""
    n = int(dur * SR)
    tt = np.arange(n) / SR
    r = np.random.default_rng(seed)
    f = f0 * (1 + 0.25 * np.exp(-((tt - 0.5) / 0.4) ** 2)) * (1 + 0.04 * np.sin(2 * np.pi * 9 * tt)) + np.cumsum(r.standard_normal(n)) / SR * 40
    ph = 2 * np.pi * np.cumsum(f) / SR
    saw = 2 * ((ph / (2 * np.pi)) % 1) - 1
    sub = np.sin(ph / 2)
    nz = r.standard_normal(n)
    x = saw * 0.8 + sub * 0.5 + nz * 0.5
    form = bp(x, 380, 900, 2) * 1.2 + bp(x, 1000, 1500, 2) * 0.7 + bp(x, 2200, 3000, 2) * 0.25 + lp(x, 300) * 0.8
    y = np.tanh(form * 2.2)
    e = np.minimum(1, tt / 0.25) * np.clip((dur - tt) / 0.7, 0, 1)
    y = y * e
    return np.stack([y, y], 1) * gain * 0.45


def fire_roar(rng, dur, seed=0, gain=1.0, attack=0.12):
    """Fire breath: rushing low noise with fast flutter and crackle; 0.5 s release at the end."""
    n = int(dur * SR)
    tt = np.arange(n) / SR
    r = np.random.default_rng(seed)
    x = pink(rng, n)
    body = lp(x, 2500) * 0.5 + lp(brown(rng, n), 200) * 0.8
    flutter = 0.7 + 0.3 * slow_mod(n, 25.0, 1.0, seed + 1)
    e = np.minimum(1, tt / attack) * np.clip((dur - tt) / 0.5, 0, 1)
    y = body * (flutter * e)[:, None]
    cr = np.zeros((n, 2), np.float32)
    for k in range(int(dur * 120)):
        p = int(r.uniform(0, n - 300))
        cr[p:p + 250, r.integers(0, 2)] += r.standard_normal(250) * np.exp(-np.arange(250) / 25.0) * r.uniform(0.2, 1.0)
    y += hp(cr, 1500) * 0.15 * e[:, None]
    return y * gain


# ---------------- a whole soundtrack ----------------
class Track:
    def __init__(self, dur, seed=11):
        self.N = int(SR * dur)
        self.rng = np.random.default_rng(seed)
        self.out = np.zeros((self.N, 2), np.float32)

    def env(self, t0, t1, fade=0.5):
        """0..1 envelope over the whole track: on from t0 to t1 with linear fades inside the interval."""
        e = np.zeros(self.N, np.float32)
        a, b = max(0, int(t0 * SR)), min(self.N, int(t1 * SR))
        L = b - a
        if L <= 0:
            return e
        k = min(int(fade * SR), L // 2)
        seg = np.ones(L, np.float32)
        seg[:k] = np.linspace(0, 1, k); seg[L - k:] = np.linspace(1, 0, k)
        e[a:b] = seg
        return e

    def bed(self, sig, t0, t1, gain=1.0, fade=0.5):
        self.out += sig * self.env(t0, t1, fade)[:, None] * gain

    def add(self, sig, t0, gain=1.0):
        a = int(t0 * SR)
        if sig.ndim == 1:
            sig = np.stack([sig, sig], 1)
        b = min(self.N, a + len(sig))
        if a < 0:
            sig = sig[-a:]; a = 0
        self.out[a:b] += sig[:b - a] * gain

    def flaps(self, s_frame, n_frames, gain, phase_frame=7, period=28, fps=24.0):
        """One flap per wingbeat of a looping sprite: frames where (i % period) == phase_frame, 0.1 s early."""
        for i in range(n_frames):
            if i % period == phase_frame:
                self.add(flap(self.rng, gain), (s_frame + i) / fps - 0.1)

    def write(self, path, peak=0.9):
        pk = float(np.abs(self.out).max())
        if pk > peak:
            self.out *= peak / pk
        sf.write(path, self.out, SR)
        return pk
