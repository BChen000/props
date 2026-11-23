"""Glockenspiel sound set: turns hit events into a finished stereo WAV.

Sounds (all synthesized, no samples): metal-bar notes, glass marble clicks, wicker basket thuds,
rolling noise on the bars and in the basket, a small-room reverb, then slow leveling + a limiter.

Run:  python3 synth.py EVENTS.npz OUT.wav --duration 12.2 [--spectrogram preview.png]
EVENTS.npz comes from marble-drop-sim/events.py (notes carry their MIDI pitch, so any tuning works).
"""
import os, sys, argparse
import numpy as np
import scipy.signal as ss
import scipy.io.wavfile as wf

# ======================================================================= SETTINGS
SR = 48000
SEED = 7
NOTE_GAIN = 0.22
CLICK_GAIN = 0.16
THUD_GAIN = 0.5
ROLL_BAR_GAIN = 0.035
ROLL_BASKET_GAIN = 0.05
PARTIAL_RATIOS = [1.0, 2.756, 5.404, 8.933]      # free metal bar modes
PARTIAL_AMPS = [1.0, 0.32, 0.11, 0.045]
DECAY_C5 = 1.5                                   # seconds; higher notes ring shorter
REVERB_RT60 = 0.65
REVERB_WET = 0.28
LEVEL_WINDOW = (7.5, 11.0)   # the loudness of this stretch (the finale) becomes the target for the whole track
PEAK = 0.89
FADE_OUT = 0.25
PAN_WIDTH = 0.55             # how far left/right a marble at the bar ends is panned
# ===================================================================== END SETTINGS

rng = np.random.default_rng(SEED)


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def pan_gains(x):
    p = np.clip(x / 0.14, -1, 1) * PAN_WIDTH
    a = (p + 1) * np.pi / 4
    return np.cos(a), np.sin(a)


def add(buf, start, sig, x):
    i0 = int(round(start * SR))
    if i0 >= buf.shape[1]:
        return
    if i0 < 0:
        sig = sig[-i0:]
        i0 = 0
    n = min(len(sig), buf.shape[1] - i0)
    gl, gr = pan_gains(x)
    buf[0, i0:i0 + n] += sig[:n] * gl
    buf[1, i0:i0 + n] += sig[:n] * gr


_hp = ss.butter(2, 2500, 'hp', fs=SR, output='sos')


def glock(f, vel):
    tau1 = DECAY_C5 * (523.0 / f) ** 0.42
    dur = min(5 * tau1, 4.5)
    n = int(dur * SR)
    t = np.arange(n) / SR
    bright = 0.35 + 0.65 * vel
    sig = np.zeros(n)
    for k, (rt, a) in enumerate(zip(PARTIAL_RATIOS, PARTIAL_AMPS)):
        fk = f * rt
        if fk > SR * 0.45:
            continue
        tk = tau1 / (1 + 3.2 * k)
        amp = a * bright ** k
        sig += amp * np.sin(2 * np.pi * fk * t + rng.uniform(0, 6.28)) * np.exp(-t / tk)
    sig += 0.12 * np.sin(2 * np.pi * (f + 0.7) * t) * np.exp(-t / (tau1 * 0.9))
    att = int(0.0006 * SR)
    sig[:att] *= np.linspace(0, 1, att)
    nn = int(0.002 * SR)
    click = ss.sosfilt(_hp, rng.standard_normal(nn)) * np.exp(-np.arange(nn) / (0.0005 * SR))
    sig[:nn] += 0.25 * vel * click
    loud = (523.0 / f) ** 0.18
    return sig * vel * loud


def glass_click(vel):
    n = int(0.03 * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for fr, dc, a in ((3300, 0.006, 1.0), (5600, 0.004, 0.7), (8400, 0.003, 0.45), (11800, 0.002, 0.3)):
        fr *= rng.uniform(0.88, 1.12)
        sig += a * np.sin(2 * np.pi * fr * t + rng.uniform(0, 6.28)) * np.exp(-t / dc)
    nn = int(0.0012 * SR)
    sig[:nn] += 0.6 * rng.standard_normal(nn) * np.exp(-np.arange(nn) / (0.0003 * SR))
    return sig * vel


_bp = ss.butter(2, [350, 2600], 'bp', fs=SR, output='sos')


def wicker_thud(vel):
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    noise = ss.sosfilt(_bp, rng.standard_normal(n)) * np.exp(-t / 0.018)
    low = np.sin(2 * np.pi * rng.uniform(95, 140) * t) * np.exp(-t / 0.012)
    sig = 0.9 * noise + 0.5 * low
    for _ in range(rng.integers(2, 5)):
        i = rng.integers(0, int(0.012 * SR))
        m = int(0.0015 * SR)
        sig[i:i + m] += 0.35 * rng.standard_normal(min(m, n - i)) * np.exp(-np.arange(min(m, n - i)) / (0.0004 * SR))
    glassy = np.sin(2 * np.pi * rng.uniform(2800, 3600) * t) * np.exp(-t / 0.004)
    sig += 0.25 * glassy
    return sig * vel


def reverb_ir(rt60=REVERB_RT60, n_ch=2):
    n = int(rt60 * 1.2 * SR)
    t = np.arange(n) / SR
    out = []
    lp = ss.butter(1, 5000, 'lp', fs=SR, output='sos')
    for c in range(n_ch):
        ir = rng.standard_normal(n) * np.exp(-6.9 * t / rt60)
        ir = ss.sosfilt(lp, ir)
        pre = int(0.012 * SR)
        ir = np.concatenate([np.zeros(pre), ir])
        out.append(ir / np.sqrt((ir ** 2).sum()))
    return out


def build(ev, dur, out_wav):
    n = int(dur * SR)
    dry = np.zeros((2, n))
    cache = {}
    for (t, bar, midi, amp, x, marble, first) in ev['notes']:
        key = (int(midi), round(amp, 2))
        if key not in cache:
            cache[key] = glock(midi_hz(midi), amp)
        add(dry, t, cache[key] * NOTE_GAIN, x)
    for (t, vel, x) in ev['clicks']:
        add(dry, t, glass_click(vel ** 0.8) * CLICK_GAIN, x)
    for (t, vel, x) in ev['thuds']:
        add(dry, t, wicker_thud(vel ** 0.8) * THUD_GAIN, x)
    tt = ev['t']
    tgrid = np.arange(n) / SR
    lp = ss.butter(2, 1400, 'lp', fs=SR, output='sos')
    rolln = ss.sosfilt(lp, rng.standard_normal(n))
    bpk = ss.butter(2, [600, 4000], 'bp', fs=SR, output='sos')
    rustle = ss.sosfilt(bpk, rng.standard_normal(n))
    for e, x_w, src, gain in ((ev['roll_bar_env'], ev['roll_bar_x'], rolln, ROLL_BAR_GAIN),
                              (ev['roll_bask_env'], ev['roll_bask_x'], rustle, ROLL_BASKET_GAIN)):
        env = np.interp(tgrid, tt, e)
        xe = np.interp(tgrid, tt, x_w)
        gl, gr = pan_gains(xe)
        sig = src * np.clip(env, 0, 2.5) * gain
        dry[0] += sig * gl
        dry[1] += sig * gr
    irs = reverb_ir()
    wet = np.stack([ss.fftconvolve(dry[c], irs[c])[:n] for c in range(2)])
    mix = dry + REVERB_WET * wet
    hp = ss.butter(2, 40, 'hp', fs=SR, output='sos')
    mix = ss.sosfilt(hp, mix, axis=1)
    slow = np.sqrt(ss.sosfiltfilt(ss.butter(1, 1.2, 'lp', fs=SR, output='sos'), (mix ** 2).mean(0)).clip(1e-12))
    target = np.percentile(slow[int(LEVEL_WINDOW[0] * SR):int(LEVEL_WINDOW[1] * SR)], 50)
    agc = np.clip((target / slow) ** 0.75, 0.6, 4.0)
    mix = mix * agc
    env = np.sqrt(ss.sosfiltfilt(ss.butter(1, 40, 'lp', fs=SR, output='sos'), (mix ** 2).mean(0)).clip(1e-12))
    thr = np.percentile(env, 97) * 0.8
    gain = np.where(env > thr, (thr / env) ** 0.6, 1.0)
    mix = mix * gain
    mix = mix / np.abs(mix).max() * PEAK
    fade = int(FADE_OUT * SR)
    mix[:, -fade:] *= np.linspace(1, 0, fade) ** 2
    rms = np.sqrt((mix ** 2).mean())
    os.makedirs(os.path.dirname(os.path.abspath(out_wav)), exist_ok=True)
    wf.write(out_wav, SR, (mix.T * 32767).astype(np.int16))
    print('saved', out_wav, 'rms %.1f dBFS' % (20 * np.log10(rms)), 'peak %.2f' % np.abs(mix).max())
    return mix


def spectrogram_png(mix, path, notes=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    x = mix.mean(0)
    f, t, S = ss.spectrogram(x, SR, nperseg=4096, noverlap=4096 - 480)
    S = 10 * np.log10(S + 1e-12)
    fig, ax = plt.subplots(figsize=(9, 5), dpi=130)
    m = (f > 150) & (f < 6000)
    ax.pcolormesh(t, f[m], S[m], vmin=S.max() - 70, vmax=S.max(), cmap='magma', shading='auto')
    ax.set_yscale('log')
    from matplotlib.ticker import NullFormatter
    ax.set_yticks([250, 500, 1000, 2000, 4000]); ax.set_yticklabels(['250', '500', '1k', '2k', '4k'])
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.set_xlabel('time (s)'); ax.set_ylabel('Hz')
    ax.set_title('glockenspiel-sounds: spectrogram of the synthesized track')
    plt.tight_layout()
    plt.savefig(path)
    print('saved', path)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('events'); ap.add_argument('out')
    ap.add_argument('--duration', type=float, required=True)
    ap.add_argument('--spectrogram', default=None)
    a = ap.parse_args()
    ev = np.load(a.events)
    mix = build(ev, a.duration, a.out)
    if a.spectrogram:
        spectrogram_png(mix, a.spectrogram)
