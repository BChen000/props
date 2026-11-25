import numpy as np, soundfile as sf, json, subprocess, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ep_paths
A = ep_paths.AUDIO
from scipy.signal import butter, sosfilt, resample_poly, fftconvolve

SR = 48000
FPS = 24.0
SHOTS = [('s01', 209), ('s02', 51), ('s03', 110), ('s04', 140), ('s05', 102), ('s06', 154), ('s07a', 50), ('s08', 92), ('s07b', 127), ('s09', 85), ('s10', 140), ('s11', 147), ('s12', 106), ('s13', 85), ('s14', 149), ('s15', 121), ('s16', 139), ('s17', 87), ('s18', 266), ('s19', 165), ('s20', 199), ('s21', 79), ('s22', 123), ('s23', 71), ('s24', 111), ('s25', 154), ('s26', 95), ('s27', 56), ('s28', 114)]
START = {}
acc = 0
for n, c in SHOTS:
    START[n] = acc / FPS
    acc += c
TOTAL = acc / FPS
N = int(round(TOTAL * SR))
rng = np.random.default_rng(11)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], 'bandpass', fs=SR, output='sos'), x)


def lp(x, f, order=2):
    return sosfilt(butter(order, f, 'lowpass', fs=SR, output='sos'), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, 'highpass', fs=SR, output='sos'), x)


def env_curve(points, n):
    t = np.arange(n) / SR
    ts = [p[0] for p in points]; vs = [p[1] for p in points]
    return np.interp(t, ts, vs)


def reverb_ir(sec=2.8, decay=3.2, seed=3):
    r = np.random.default_rng(seed)
    n = int(sec * SR)
    t = np.arange(n) / SR
    ir = r.normal(0, 1, (n, 2)) * np.exp(-decay * t)[:, None]
    ir[:, 0] = lp(ir[:, 0], 6000); ir[:, 1] = lp(ir[:, 1], 6000)
    ir[: int(0.01 * SR)] *= np.linspace(0, 1, int(0.01 * SR))[:, None]
    return ir / np.sqrt((ir ** 2).sum(0))


# ------------------------------------------------------------ narration
nar, nsr = sf.read(A + 'narration_raw.wav', dtype='float64')
nar = resample_poly(nar, SR, nsr)
nar = hp(nar, 75)
# gentle warmth: low-shelf-ish boost via parallel low band, de-harsh highs
nar = nar + 0.18 * bp(nar, 120, 400) - 0.10 * bp(nar, 5500, 11000)
# simple compressor
env = np.sqrt(np.maximum(lp(nar ** 2, 12), 0.0))
thr = 0.10
gain = np.where(env > thr, (thr / np.maximum(env, 1e-9)) ** 0.35, 1.0)
nar = nar * gain
nar = nar / np.max(np.abs(nar)) * 0.70
narr = np.zeros(N)
narr[:min(N, len(nar))] = nar[:N]
tim = json.load(open(A + 'timings.json'))
speech = np.zeros(N)
for tt in tim:
    a = int(max(0, tt['start'] - 0.15) * SR); b = int(min(TOTAL, tt['end'] + 0.25) * SR)
    speech[a:b] = 1.0
speech = lp(speech, 3.0)
speech = np.clip(speech / max(1e-6, speech.max()), 0, 1)

# ------------------------------------------------------------ music
def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def pad_voice(freq, n, detune=0.0025, harmonics=14, bright=1.0):
    t = np.arange(n) / SR
    out = np.zeros(n)
    for d in (-detune, 0.0, detune):
        f = freq * (1 + d)
        ph = rng.random() * 2 * np.pi
        for h in range(1, harmonics + 1):
            if f * h > 9000:
                break
            amp = (1.0 / h) * (bright ** (h - 1))
            out += amp * np.sin(2 * np.pi * f * h * t + ph * h)
    vib = 1 + 0.002 * np.sin(2 * np.pi * 5.1 * t + rng.random() * 6)
    return out * vib / 3.0


CH = {
    'Dm': [38, 50, 57, 62, 65], 'Bb': [34, 46, 53, 58, 62], 'F': [41, 48, 53, 57, 60], 'C': [36, 48, 55, 60, 64],
    'Gm': [31, 43, 50, 55, 58], 'A': [33, 45, 52, 57, 61], 'D': [38, 50, 57, 62, 66], 'G': [31, 43, 50, 55, 59],
    'Am': [33, 45, 52, 57, 60], 'Fsus': [41, 48, 53, 58, 60], 'Bbmaj7': [34, 46, 53, 57, 62],
}
_to = json.load(open(os.path.join(ep_paths.EP, 'first_cut_timings.json')))  # the cut the chords were written for
_tn = json.load(open(A + 'timings.json'))
_xo = [0.0] + [x['start'] for x in _to] + [_to[-1]['end'], 119.54]
_xn = [0.0] + [x['start'] for x in _tn] + [_tn[-1]['end'], TOTAL]
def RM(t):
    return float(np.interp(t, _xo, _xn))
prog = [  # (start, chord, level)
    (0.0, 'Dm', 0.9), (5.5, 'Bb', 0.9), (9.5, 'F', 1.0), (13.5, 'C', 1.0), (17.0, 'Dm', 0.7),
    (20.5, 'F', 0.55), (26.0, 'Bbmaj7', 0.55), (31.0, 'F', 0.55), (35.3, 'C', 0.55), (38.2, 'Bb', 0.75), (42.8, 'F', 0.6),
    (47.4, 'C', 0.6), (51.5, 'Dm', 0.7), (54.4, 'Gm', 0.6), (59.4, 'Bb', 0.6), (63.5, 'A', 0.8), (68.2, 'Dm', 0.65),
    (71.2, 'Bb', 0.7), (75.8, 'F', 0.75), (80.4, 'Gm', 0.75), (86.0, 'C', 0.8), (92.7, 'A', 0.85), (95.5, 'Bb', 0.9),
    (99.6, 'A', 1.0), (101.8, 'F', 1.15), (105.4, 'C', 1.2), (110.6, 'Bb', 1.0), (113.7, 'Gm', 0.85), (115.6, 'D', 1.0), (TOTAL, 'D', 0.0)]
music = np.zeros((N, 2))
prog = [(RM(a) if a < TOTAL - 0.01 else TOTAL, b, c) for a, b, c in prog]
for (t0, ch, lv), (t1, _, _) in zip(prog[:-1], prog[1:]):
    a = int(t0 * SR); b = min(N, int((t1 + 1.6) * SR))
    n = b - a
    if n <= 0:
        continue
    t = np.arange(n) / SR
    dur = t1 - t0
    e = np.clip(t / 1.2, 0, 1) * np.clip((dur + 1.6 - t) / 1.6, 0, 1)
    for i, m in enumerate(CH[ch]):
        v = pad_voice(mtof(m), n, bright=0.78 if i > 0 else 0.6) * e * lv * (0.9 if i == 0 else 0.55)
        pan = 0.5 + 0.35 * np.sin(i * 1.7)
        music[a:b, 0] += v * (1 - pan); music[a:b, 1] += v * pan
music[:, 0] = lp(music[:, 0], 2600); music[:, 1] = lp(music[:, 1], 2600)
# soft plucked motif in the chick section and the soaring section
motif = [62, 66, 69, 71, 69, 66, 64, 62]
for (s, e_, gap) in ((RM(21.0), RM(50.0), 1.6), (RM(102.5), RM(112.0), 0.8)):
    k = 0
    t = s
    while t < e_:
        m = motif[k % len(motif)] + 12
        n = int(1.6 * SR)
        tt = np.arange(n) / SR
        note = (np.sin(2 * np.pi * mtof(m) * tt) + 0.3 * np.sin(2 * np.pi * mtof(m) * 2 * tt)) * np.exp(-tt * 3.2) * np.clip(tt / 0.004, 0, 1)
        a = int(t * SR)
        if a + n < N:
            music[a:a + n, 0] += 0.10 * note; music[a:a + n, 1] += 0.08 * note
        k += 1
        t += gap
# low drum swells at key beats
for tb, amp in ((0.05, 0.7), (RM(7.0), 0.8), (RM(63.5), 0.6), (RM(95.5), 0.6), (RM(101.8), 1.0), (RM(115.6), 0.8)):
    n = int(2.5 * SR); tt = np.arange(n) / SR
    f = 55 * np.exp(-tt * 1.2) + 38
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 2.2) * np.clip(tt / 0.01, 0, 1)
    a = int(tb * SR)
    if a + n < N:
        music[a:a + n, 0] += amp * 0.35 * boom; music[a:a + n, 1] += amp * 0.35 * boom
ir = reverb_ir()
wet = np.stack([fftconvolve(music[:, 0], ir[:, 0])[:N], fftconvolve(music[:, 1], ir[:, 1])[:N]], 1)
music = 0.55 * music + 0.75 * wet
music = music / np.max(np.abs(music)) * 0.9
mus_level = env_curve([(0, 0.22), (TOTAL - 3.0, 0.22), (TOTAL, 0.05)], N)
duck = 1.0 - 0.45 * speech
music = music * (mus_level * duck)[:, None]

# ------------------------------------------------------------ wind ambience
wn = rng.normal(0, 1, (N, 2))
wind = np.stack([bp(wn[:, 0], 150, 1400), bp(wn[:, 1], 150, 1400)], 1)
gust = 0.55 + 0.45 * np.sin(2 * np.pi * np.arange(N) / SR * 0.11) * np.sin(2 * np.pi * np.arange(N) / SR * 0.047 + 1.0)
whistle = np.stack([bp(wn[:, 1], 1800, 2600, 3), bp(wn[:, 0], 1900, 2700, 3)], 1) * 0.06
wind = (wind + whistle) * gust[:, None]
wind = wind / np.sqrt(np.mean(wind ** 2))
wl = []
for n_, c in SHOTS:
    lv = {'s01': 0.05, 's02': 0.05, 's03': 0.045, 's04': 0.06, 's05': 0.05, 's13': 0.06, 's16': 0.055, 's21': 0.06,
          's22': 0.06, 's23': 0.09, 's24': 0.07, 's25': 0.05, 's26': 0.045, 's28': 0.035}.get(n_, 0.025)
    wl.append((START[n_] + 0.01, lv))
pts = []
for (t0, lv), nxt in zip(wl, wl[1:] + [(TOTAL, wl[-1][1])]):
    pts += [(t0, lv), (nxt[0] - 0.02, lv)]
wind = wind * (lp(env_curve(pts, N), 2.0) * 0.75 * (1.0 - 0.62 * speech))[:, None]
wind = np.stack([lp(wind[:, 0], 1500), lp(wind[:, 1], 1500)], 1)

# ------------------------------------------------------------ sfx
sfx = np.zeros((N, 2))
pp = np.zeros((N, 2))


def whoosh(t, amp=0.25, dur=0.38, lo=180, hi=900, pan=0.5):
    n = int(dur * SR); a = int(t * SR)
    if a < 0 or a + n >= N:
        return
    x = rng.normal(0, 1, n)
    x = bp(x, lo, hi)
    tt = np.arange(n) / dur / SR
    e = np.sin(np.pi * np.clip(tt, 0, 1)) ** 2
    y = x * e
    y = y / (np.max(np.abs(y)) + 1e-9) * amp
    sfx[a:a + n, 0] += y * (1 - pan); sfx[a:a + n, 1] += y * pan


def peep(t, amp=0.16, f0=3100, dur=0.13, pan=0.5):
    n = int(dur * SR); a = int(t * SR)
    if a + n >= N:
        return
    tt = np.arange(n) / SR
    u = tt / dur
    f = f0 * (1 + 0.32 * np.sin(np.pi * u) - 0.05 * u)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = (np.sin(ph) + 0.25 * np.sin(2 * ph)) * (np.clip(tt / 0.008, 0, 1) * np.exp(-((u - 0.4) ** 2) / 0.12))
    pp[a:a + n, 0] += y * amp * (1 - pan); pp[a:a + n, 1] += y * amp * pan


def flaps(shot, t0, t1, period, amp=0.22, lo=160, hi=700):
    s = START[shot]
    k = 0
    while True:
        tl = period * (0.5 + k)
        if tl > t1:
            break
        if tl >= t0:
            whoosh(s + tl - 0.12, amp=amp, lo=lo, hi=hi)
        k += 1


flaps('s01', 3.0, 4.3, 1.15, amp=0.14)
flaps('s10', 1.4, 4.9, 1.0, amp=0.18)
flaps('s18', 0.0, 3.9, 0.55, amp=0.16, lo=250, hi=1100)
flaps('s18', 5.45, 8.9, 0.55, amp=0.20, lo=250, hi=1100)
flaps('s22', 2.6, 5.1, 0.56, amp=0.18, lo=250, hi=1100)
whoosh(START['s22'] + 2.4, amp=0.22, dur=0.5, lo=150, hi=900, pan=0.35)
flaps('s23', 0.0, 2.9, 0.42, amp=0.20, lo=250, hi=1200)
whoosh(START['s04'] + 4.6, amp=0.40, dur=0.85, lo=120, hi=1600, pan=0.75)
whoosh(START['s24'] + 1.25, amp=0.35, dur=1.1, lo=120, hi=1300, pan=0.4)
whoosh(START['s17'] + 0.7, amp=0.30, dur=0.7, lo=150, hi=900, pan=0.3)
peep(START['s07b'] + (2.17 - 50 / 24.0), amp=0.10, f0=3300)
for c0, ff, dd, aa in ((0.4, 2950, 0.12, 0.12), (0.75, 3250, 0.10, 0.10), (1.1, 3050, 0.15, 0.13), (1.9, 3400, 0.11, 0.11), (2.2, 3150, 0.14, 0.12)):
    peep(START['s09'] + c0 + 0.03, amp=aa, f0=ff, dur=dd)
peep(START['s06'] + 2.0, amp=0.07, f0=3200)
# pebble clicks falling away (s16)
for i, dt in enumerate((1.62, 1.95, 2.35)):
    n = int(0.03 * SR); a = int((START['s16'] + dt) * SR)
    y = hp(rng.normal(0, 1, n), 2000) * np.exp(-np.arange(n) / SR * 120) * (0.12 / (1 + i))
    sfx[a:a + n, 0] += y; sfx[a:a + n, 1] += y * 0.8

# ------------------------------------------------------------ mix
sfx = sfx * (1.0 - 0.6 * speech)[:, None] + pp * (1.0 - 0.2 * speech)[:, None]
mix = music + wind + sfx
mix[:, 0] += narr; mix[:, 1] += narr
fade_out = env_curve([(0, 1.0), (TOTAL - 1.0, 1.0), (TOTAL, 0.0)], N)
mix = mix * fade_out[:, None]
mix = mix / np.max(np.abs(mix)) * 0.89
sf.write(A + 'mix_pre.wav', mix.astype(np.float32), SR, subtype='FLOAT')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', A + 'mix_pre.wav', '-af',
                'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', '48000', '-c:a', 'pcm_s16le', A + 'final_mix.wav'], check=True)
print('total', round(TOTAL, 3), 's', N, 'samples')
