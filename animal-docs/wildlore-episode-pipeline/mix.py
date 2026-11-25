"""The Blue Raspberry soundtrack mix at 48 kHz: synthesized forest ambience (wind, rustle, distant bird calls),
shot-cued sound effects (bee buzz, berry thuds, whooshes, bells), the narration through the Wildlore voice chain
with a small room, the FluidSynth score ducked 55 % under speech, and a look-ahead peak limiter at -4.5 dBFS.

  python mix.py   -> $WILDLORE_WORK/audio/mix.wav (+ vo_only, music_only, fx_only stems)
Needs vo/line_XX.wav + vo/lines_info.json (../wildlore-narrator) and audio/score_raw.wav (score.py + render_score.sh).
The ambience and effect cues between the helpers and the voice section are written per shot for this episode.
"""
import sys, os, json, math
import numpy as np, soundfile as sf, librosa
from scipy import signal
from pedalboard import Pedalboard, HighpassFilter, LowShelfFilter, PeakFilter, HighShelfFilter, Compressor, Reverb, Gain, Limiter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import S, VO, TOTAL, FPS, WORK

SR = 48000
DUR = TOTAL / FPS + 1.8  # covers the 1.25 s end-card tail added at assembly
N = int(DUR * SR)
rng = np.random.default_rng(11)


def T(shot, frame):
    return S[shot] + (frame - 1) / FPS


def sos(kind, f, order=2):
    return signal.butter(order, f, btype=kind, fs=SR, output='sos')


def filt(x, kind, f, order=2):
    return signal.sosfilt(sos(kind, f, order), x)


def pink(n):
    w = rng.normal(0, 1, n)
    b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
    a = [1, -2.494956002, 2.017265875, -0.522189400]
    return signal.lfilter(b, a, w)


def env_adsr(n, a=0.01, r=0.1):
    e = np.ones(n)
    na, nr = max(1, int(a * SR)), max(1, int(r * SR))
    e[:na] = np.linspace(0, 1, na)
    e[-nr:] *= np.linspace(1, 0, nr)
    return e


def place(buf, x, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= buf.shape[0] or i + len(x) <= 0:
        return
    if i < 0:
        x = x[-i:]; i = 0
    x = x[:buf.shape[0] - i]
    l = math.cos((pan + 1) * math.pi / 4); r = math.sin((pan + 1) * math.pi / 4)
    buf[i:i + len(x), 0] += x * gain * l * 1.414
    buf[i:i + len(x), 1] += x * gain * r * 1.414


def seg_env(t0, t1, fade=0.4):
    e = np.zeros(N)
    i0, i1 = int(max(0, t0) * SR), int(min(DUR, t1) * SR)
    if i1 <= i0:
        return e
    e[i0:i1] = 1
    nf = int(fade * SR)
    e[i0:min(i0 + nf, i1)] *= np.linspace(0, 1, min(nf, i1 - i0))
    e[max(i1 - nf, i0):i1] *= np.linspace(1, 0, i1 - max(i1 - nf, i0))
    return e


# ------------------------------------------------ sound generators
def chirp(dur, f0, f1, vib=0.0, harm=0.15):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f0 + (f1 - f0) * (t / dur) ** 0.8 + vib * np.sin(2 * np.pi * 35 * t)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) + harm * np.sin(2 * ph)
    e = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5
    return x * e


def bird_phrase(kind):
    parts = []
    if kind == 0:  # robin-like warble
        for k in range(rng.integers(5, 11)):
            d = rng.uniform(0.04, 0.13)
            f0 = rng.uniform(2500, 6500); f1 = f0 * rng.uniform(0.7, 1.4)
            parts.append(chirp(d, f0, f1, vib=rng.uniform(0, 300)))
            parts.append(np.zeros(int(rng.uniform(0.01, 0.06) * SR)))
    elif kind == 1:  # two-note call
        f = rng.uniform(3000, 4500)
        for k in range(2):
            parts.append(chirp(0.14, f, f * 0.98)); parts.append(np.zeros(int(0.09 * SR))); f *= 0.8
    else:  # trill
        f = rng.uniform(4000, 6000)
        for k in range(rng.integers(8, 16)):
            parts.append(chirp(0.035, f, f * 0.85)); parts.append(np.zeros(int(0.025 * SR)))
    return np.concatenate(parts)


def birds(buf, t0, t1, density=0.5, gain=0.06, far=False):
    t = t0 + rng.uniform(0, 1.5)
    while t < t1 - 0.5:
        x = bird_phrase(int(rng.integers(0, 3)))
        if far:
            x = filt(x, 'lowpass', 3500)
        place(buf, x, t, gain * rng.uniform(0.4, 1.0) * (0.5 if far else 1.0), pan=rng.uniform(-0.8, 0.8))
        t += rng.exponential(1.0 / density) + len(x) / SR


def wind(dur, cutoff=700, gust=0.15):
    n = int(dur * SR)
    x = filt(pink(n), 'lowpass', cutoff)
    t = np.arange(n) / SR
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * gust * t + rng.uniform(0, 6)) * np.sin(2 * np.pi * gust * 0.37 * t + 1)
    return x / (np.std(x) + 1e-9) * lfo


def rustle(dur, amount=1.0):
    n = int(dur * SR)
    x = filt(rng.normal(0, 1, n), 'bandpass', [1800, 7000])
    t = np.arange(n) / SR
    e = np.clip(pink(n), 0, None); e = filt(e, 'lowpass', 6); e /= e.max() + 1e-9
    return x / (np.std(x) + 1e-9) * e * amount


def tone(dur, f, decay=1.0, kind='sine'):
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t)
    return x * np.exp(-t / decay) * env_adsr(n, 0.004, 0.02)


def bell(dur, f, ratio=1.4, idx=3.0, decay=1.2):
    n = int(dur * SR); t = np.arange(n) / SR
    m = idx * np.exp(-t / (decay * 0.5)) * np.sin(2 * np.pi * f * ratio * t)
    return np.sin(2 * np.pi * f * t + m) * np.exp(-t / decay) * env_adsr(n, 0.002, 0.05)


def thud(f=110, dur=0.25):
    n = int(dur * SR); t = np.arange(n) / SR
    body = np.sin(2 * np.pi * f * t * (1 - 0.3 * t / dur)) * np.exp(-t / 0.05)
    click = filt(rng.normal(0, 1, n), 'bandpass', [800, 4000]) * np.exp(-t / 0.006) * 0.3
    return body + click


def whoosh(dur, f0=200, f1=4000, up=True):
    n = int(dur * SR)
    x = rng.normal(0, 1, n + 4096)
    f, t, Z = signal.stft(x, fs=SR, nperseg=2048, noverlap=1536)
    u = np.clip(t / dur, 0, 1)
    fc = f0 * (f1 / f0) ** (u if up else 1 - u)
    mask = np.exp(-0.5 * (np.log((f[:, None] + 1) / fc[None, :]) / 0.45) ** 2)
    _, y = signal.istft(Z * mask, fs=SR, nperseg=2048, noverlap=1536)
    y = y[:n]
    e = np.sin(np.pi * np.linspace(0, 1, n)) ** 2
    return y / (np.std(y) + 1e-9) * e


def buzz(dur, f=225):
    n = int(dur * SR); t = np.arange(n) / SR
    fm = f * (1 + 0.012 * np.sin(2 * np.pi * 5.5 * t) + 0.006 * rng.normal(0, 1, n).cumsum() / np.sqrt(np.arange(1, n + 1)))
    ph = 2 * np.pi * np.cumsum(fm) / SR
    saw = signal.sawtooth(ph)
    x = filt(saw, 'lowpass', 2600) + 0.15 * filt(saw, 'bandpass', [3000, 6000])
    return x * (1 + 0.15 * np.sin(2 * np.pi * 11 * t))


# ------------------------------------------------ build stems
amb = np.zeros((N, 2)); sfx = np.zeros((N, 2))
forest_shots = [("A", 0), ("B", 0), ("C", 0), ("D", 0), ("E", 0), ("O", 0), ("R", 0)]
seglen = {}
from timeline import SEGS
for name, f, n, xf in SEGS:
    seglen[name] = n / FPS
def span(shot):
    return S[shot], S[shot] + seglen[shot]
# forest ambience across forest shots
w = wind(DUR, 650)
lv = np.zeros(N)
for sh in ("A", "B", "C", "D", "E", "F", "O", "P", "R"):
    a, b = span(sh)
    lv += seg_env(a - 0.2, b + 0.2, 0.5) * (0.5 if sh in ("F", "P") else 1.0)
lv = np.clip(lv, 0, 1)
amb[:, 0] += w * lv * 0.012; amb[:, 1] += np.roll(w, 2400) * lv * 0.012
rs = rustle(DUR)
amb[:, 0] += rs * lv * 0.004; amb[:, 1] += np.roll(rs, 5000) * lv * 0.004
for sh in ("A", "B", "C", "E", "O", "R"):
    a, b = span(sh); birds(amb, a, b, density=0.45, gain=0.035, far=sh in ("B", "R"))
a, b = span("D"); birds(amb, a, b, density=0.3, gain=0.025, far=True)
# farm ambience
for sh in ("L2", "M2"):
    a, b = span(sh)
    e = seg_env(a - 0.2, b + 0.2, 0.4)
    ww = wind(DUR, 900, 0.25)
    amb[:, 0] += ww * e * 0.014; amb[:, 1] += np.roll(ww, 3000) * e * 0.014
    birds(amb, a, b, density=0.7, gain=0.02, far=True)
    n_ = int((b - a) * SR); tt = np.arange(n_) / SR
    crick = np.sin(2 * np.pi * 4600 * tt) * (np.sin(2 * np.pi * 28 * tt) > 0.6) * (np.sin(2 * np.pi * 0.7 * tt) > -0.2)
    place(sfx, filt(crick, 'bandpass', [4000, 5200]), a, 0.006, pan=0.4)
# bee (shot C)
a, b = span("C")
bz = buzz(b - a)
fr = np.arange(len(bz)) / SR * FPS + 1
e = np.interp(fr, [1, 25, 70, 110, 126, 131, 151], [0.0, 0.25, 1.0, 1.0, 0.6, 0.05, 0.03])
place(sfx, bz * e, a, 0.034, pan=0.25)
a2 = a
bz2 = buzz(b - a, 240) * np.interp(np.arange(int((b - a) * SR)) / SR * FPS + 1, [1, 60, 120, 151], [0.0, 0.25, 0.15, 0.0])
place(sfx, filt(bz2, 'lowpass', 1500), a, 0.03, pan=-0.5)
# robin (shot D): pecks at 40 and 70, call at 100
for fr_ in (40, 70):
    place(sfx, filt(rng.normal(0, 1, 600), 'bandpass', [1500, 6000]) * np.exp(-np.arange(600) / 60), T("D", fr_), 0.12, pan=0.1)
place(sfx, rustle(0.6) * 0.5, T("D", 70), 0.03, pan=0.1)
place(sfx, filt(bird_phrase(1), 'lowpass', 3200), T("D", 126), 0.018, pan=-0.75)  # a distant bird, not the robin (its beak is full)
place(sfx, filt(bird_phrase(0), 'lowpass', 3000), T("D", 10), 0.016, pan=-0.8)  # distant, off to the side
# E: berries landing on litter
for land, g in ((8, 1.0), (14, 0.5), (26, 1.0)):  # first berry lands at E frame 8 and bounces once (frame 14)
    place(sfx, thud(140, 0.2), T("E", land), 0.15 * g)
    place(sfx, 0.4 * rustle(0.2), T("E", land), 0.12 * g)
place(sfx, whoosh(3.0, 300, 900), T("E", 60), 0.012)
# F -> H: whoosh into the cell world, shimmer
place(sfx, whoosh(1.6, 150, 5000), S["H1"] - 1.3, 0.028)
place(sfx, whoosh(1.0, 400, 3000), S["H2"] - 0.5, 0.025)
place(sfx, whoosh(1.0, 300, 2500, up=False), S["H3"] - 0.4, 0.025)
a, b = S["H1"], S["IJ"]
n_ = int((b - a) * SR); tt = np.arange(n_) / SR
drone = sum(np.sin(2 * np.pi * f * tt + rng.uniform(0, 6)) * g for f, g in ((55, 0.5), (82.6, 0.35), (110.3, 0.3), (164.8, 0.15)))
drone = drone * env_adsr(n_, 1.0, 1.0)
place(amb, drone, a, 0.03)
t = a
while t < b - 0.5:
    place(sfx, tone(1.5, rng.uniform(1800, 5200), 0.4), t, 0.012, pan=rng.uniform(-0.8, 0.8)); t += rng.exponential(0.35)
place(sfx, bell(3.5, 784, 1.41, 2.5, 1.4), T("H2", 185 - 97 + 1), 0.035)
place(sfx, bell(3.5, 1176, 1.41, 2.0, 1.2), T("H2", 187 - 97 + 1), 0.022, pan=0.2)
place(sfx, whoosh(2.2, 200, 1800), T("H3", 265 - 253 + 1), 0.02)
# IJ: drupelets separating - soft pops
for k in range(40):
    fr_ = 112 + int(rng.uniform(0, 60))
    place(sfx, tone(0.08, rng.uniform(500, 1400), 0.02), T("IJ", fr_), 0.03, pan=rng.uniform(-0.6, 0.6))
place(sfx, whoosh(2.0, 300, 1200), T("IJ", 108), 0.015)
# K: underground rumble + sparkles
a, b = span("K")
e = seg_env(a - 0.1, b + 0.1, 0.6)
rum = filt(pink(N), 'lowpass', 160); rum /= np.std(rum) + 1e-9
amb[:, 0] += rum * e * 0.02; amb[:, 1] += rum * e * 0.02
place(sfx, whoosh(1.4, 1500, 200, up=True), a + 1.5, 0.02)
t = a + 3.5
while t < b - 0.3:
    place(sfx, tone(0.5, rng.uniform(2500, 6000), 0.12), t, 0.01, pan=rng.uniform(-0.7, 0.7)); t += rng.exponential(0.18)
# L1: quiet room tone
a, b = span("L1")
rt = filt(pink(int((b - a) * SR)), 'lowpass', 300)
place(amb, rt / (np.std(rt) + 1e-9) * env_adsr(len(rt), 0.3, 0.3), a, 0.006)
# M1: shoot breaks the surface
place(sfx, rustle(0.5), T("M1", 50), 0.04)
place(sfx, 0.3 * thud(200, 0.15), T("M1", 50), 0.04)
a, b = span("M1")
place(amb, filt(pink(int((b - a) * SR)), 'lowpass', 200) * 0.3, a, 0.04)
# N: time-lapse whooshes at season changes, wind
for fr_ in (40, 150, 176, 262, 300):
    place(sfx, whoosh(1.4, 250, 2500), T("N", fr_), 0.02)
a, b = span("N")
ww = wind(b - a, 900, 0.3)
place(amb, ww * env_adsr(len(ww), 0.4, 0.4), a, 0.012)
# P: rustle and pluck
place(sfx, rustle(1.5), T("P", 25), 0.03, pan=0.3)
place(sfx, filt(rng.normal(0, 1, 2400), 'bandpass', [300, 1800]) * np.exp(-np.arange(2400) / 300), T("P", 92), 0.06)
place(sfx, 0.5 * tone(0.12, 520, 0.03), T("P", 92), 0.06)
place(sfx, rustle(0.8), T("P", 95), 0.025, pan=0.2)
# Q: berries landing in the bowl, room tone
for j in range(3):
    place(sfx, thud(180, 0.18) * 0.8, T("Q", 18 + j * 22 + 30), 0.07)
    place(sfx, 0.3 * filt(rng.normal(0, 1, 4000), 'bandpass', [1500, 5000]) * np.exp(-np.arange(4000) / 400), T("Q", 18 + j * 22 + 30), 0.07)
a, b = span("Q")
rt = filt(pink(int((b - a) * SR)), 'lowpass', 400)
place(amb, rt / (np.std(rt) + 1e-9) * env_adsr(len(rt), 0.3, 0.3), a, 0.005)
# S: wind and distant birds
a, b = span("S")
ww = wind(b - a + 1, 500, 0.12)
place(amb, ww * env_adsr(len(ww), 1.0, 3.0), a - 0.5, 0.02)
birds(amb, a, b - 3, density=0.35, gain=0.015, far=True)

# ------------------------------------------------ voice
info = json.load(open(os.path.join(WORK, "vo", "lines_info.json")))
vo = np.zeros(N)
board = Pedalboard([HighpassFilter(75), LowShelfFilter(cutoff_frequency_hz=170, gain_db=2.0), PeakFilter(cutoff_frequency_hz=420, gain_db=-1.5, q=1.0),
                    PeakFilter(cutoff_frequency_hz=3200, gain_db=1.5, q=0.8), HighShelfFilter(cutoff_frequency_hz=9000, gain_db=-1.0),
                    Compressor(threshold_db=-20, ratio=2.5, attack_ms=8, release_ms=120)])
for (shot, off), li in zip(VO, info):
    x, sr = sf.read(os.path.join(WORK, "vo", f"line_{li['i']:02d}.wav"), dtype='float32')
    x = librosa.resample(x, orig_sr=sr, target_sr=SR)
    x = board(x[None, :].astype(np.float32), SR)[0]
    i = int((S[shot] + off) * SR)
    vo[i:i + len(x)] += x[:N - i]
vo = vo / (np.sqrt(np.mean(vo[vo != 0] ** 2)) + 1e-9) * 0.06
room = Pedalboard([Reverb(room_size=0.18, damping=0.6, wet_level=0.07, dry_level=1.0, width=0.6)])
vo_st = room(np.stack([vo, vo]).astype(np.float32), SR).T
# ------------------------------------------------ music with ducking
mus, msr = sf.read(os.path.join(WORK, "audio", "score_raw.wav"), dtype='float32')
if msr != SR:
    mus = librosa.resample(mus.T, orig_sr=msr, target_sr=SR).T
mus = mus[:N] if len(mus) >= N else np.vstack([mus, np.zeros((N - len(mus), 2))])
mus = mus / (np.sqrt(np.mean(mus ** 2)) + 1e-9) * 0.042
from scipy.ndimage import maximum_filter1d, minimum_filter1d, uniform_filter1d
env = signal.sosfiltfilt(sos('lowpass', 6), np.abs(vo))
act = (env > 0.12 * np.percentile(env[env > 1e-4], 50)).astype(float)
act = maximum_filter1d(act, size=int(0.9 * SR), origin=int(0.15 * SR))
act = signal.sosfiltfilt(sos('lowpass', 1.2), act).clip(0, 1)
duck = 1.0 - 0.55 * act
L20 = [li for li in info][-1]
t20 = S[VO[-1][0]] + VO[-1][1]
extra = seg_env(t20 - 0.4, t20 + L20['dur'] + 0.2, 0.6)
duck *= 1.0 - 0.3 * extra
mus *= duck[:, None]
# music swells at the end, and when VO is absent
mix = vo_st + mus + 1.4 * (amb + sfx)
def limit(x, thr_db=-4.5, look=240):
    thr = 10 ** (thr_db / 20)
    pk = np.max(np.abs(x), axis=1)
    g = np.minimum(1.0, thr / (pk + 1e-9))
    g = minimum_filter1d(g, size=4 * look + 1, mode='nearest')
    g = uniform_filter1d(g, size=2 * look + 1, mode='nearest')
    return x * g[:, None]
mix = limit(mix)
print("PEAK after limiter", round(20 * np.log10(np.abs(mix).max()), 2))
sf.write(os.path.join(WORK, "audio", "mix.wav"), mix, SR, subtype='FLOAT')
sf.write(os.path.join(WORK, "audio", "vo_only.wav"), vo_st, SR, subtype='PCM_24')
sf.write(os.path.join(WORK, "audio", "music_only.wav"), mus, SR, subtype='PCM_24')
sf.write(os.path.join(WORK, "audio", "fx_only.wav"), 1.4 * (amb + sfx), SR, subtype='PCM_24')
print("mix written", mix.shape, DUR)
