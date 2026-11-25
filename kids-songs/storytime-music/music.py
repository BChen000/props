"""storytime-music: the Story Time with Kenji soundtrack, synthesized with numpy and scipy (no samples).

The music is one slow legato organ melody, root-3rd-5th-3rd on each chord at 0.75 s a note, over a long bass note
and a quiet inner organ note, 3 s per chord, in an 8-chord minor loop. The organ is three sine partials (1 : 0.30 : 0.10,
so the 2nd harmonic sits about 10 dB and the 3rd 20 dB under the fundamental, as in the channel's earlier uploads).
It runs from the first frame, set a few dB under the narration. On top go a few synthesized effects (boom, splash,
click, drill, grind, gavel, clink, whoosh) cued to caption lines, a stereo noise reverb, and a -14 LUFS loudness pass.

  python music.py --preset d-minor --dur 24          -> out/music_d-minor.wav (music alone, to audition)
  python music.py --sfx splash                       -> out/sfx_splash.wav
  python music.py --preview                          -> preview.png (piano roll of both presets)
  from music import mix; mix(narration_wav, timeline_json, out_wav, preset='d-minor', music_db=-3.5, events=[...])

Effects and the reverb draw noise from one generator (SEED) that every mix() restarts, so a mix is the same
every time it is built.
"""
import argparse
import json
import os
import subprocess

import numpy as np
import soundfile as sf
from scipy.signal import butter, fftconvolve, resample_poly, sosfilt

HERE = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------- settings
SR = 48000
SEED = 7
# each chord: (bass MIDI note, inner MIDI note, four melody MIDI notes; None = the note before rings on)
PRESETS = {
    'd-minor': dict(chord=3.0, step=0.75, prog=[        # The Locksmith: Dm A Bb Gm | Dm C Bb A
        (38, 50, [62, 65, 69, 65]), (33, 45, [57, 61, 64, 61]), (34, 46, [58, 62, 65, 62]), (31, 43, [67, 70, 67, None]),
        (38, 50, [62, 65, 69, 65]), (36, 48, [60, 64, 67, 64]), (34, 46, [58, 62, 65, 62]), (33, 45, [57, 61, 57, None])]),
    'g-minor': dict(chord=3.0, step=0.75, prog=[        # The Hero: Gm Eb Cm D | Gm Eb Cm D
        (31, 43, [67, 70, 74, 70]), (39, 51, [63, 67, 70, 67]), (36, 48, [60, 63, 67, 63]), (38, 50, [62, 66, 62, None]),
        (31, 43, [67, 70, 74, 70]), (39, 51, [63, 67, 70, 67]), (36, 48, [60, 63, 67, 63]), (38, 50, [62, 66, 69, None])]),
}
ORGAN_2ND, ORGAN_3RD = 0.30, 0.10         # partial levels relative to the fundamental
BASS_LEN, BASS_DETUNE = 2.4, 1.76         # seconds per bass note; a 1.76 Hz detuned copy gives it a slow beat
LAYERS = dict(melody=1.0, bass=0.9, inner=0.22)   # RMS-normalised layer levels
MUSIC_REVERB = 0.12
VOICE_GAIN = 0.9
OPEN_HIT = 0.7                            # a boom on the first frame, under the hook card
FX_REVERB, FX_GAIN = 0.25, 0.5
PEAK = 0.89
LOUDNORM = 'loudnorm=I=-14:TP=-1.5:LRA=11'


def env_ad(n, att, dec):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(att, 1e-4)) * np.exp(-np.maximum(0, t - att) / dec)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], 'bandpass', fs=SR, output='sos'), x)


def lp(x, f, order=2):
    return sosfilt(butter(order, f, 'lowpass', fs=SR, output='sos'), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, 'highpass', fs=SR, output='sos'), x)


rng = IRL = IRR = None


def ir(sec=2.4):
    n = int(sec * SR)
    t = np.arange(n) / SR
    L = rng.standard_normal(n) * np.exp(-t / 0.55)
    R = rng.standard_normal(n) * np.exp(-t / 0.55)
    return lp(L, 5000) * 0.02, lp(R, 5000) * 0.02


def reseed(seed=SEED):
    """Restart the noise generator and redraw the reverb impulse response from it. mix() calls this first, so the
    effects in a mix are the same draw every time, whatever was mixed before in the same process."""
    global rng, IRL, IRR
    rng = np.random.default_rng(seed)
    IRL, IRR = ir()


reseed()


def reverb(x, wet=0.3):
    l = fftconvolve(x, IRL)[:len(x)]
    r = fftconvolve(x, IRR)[:len(x)]
    return np.stack([x * (1 - wet) + l * wet, x * (1 - wet) + r * wet], 1)


def note(f):
    return 440.0 * 2 ** ((f - 69) / 12)


def organ(f, ln, att=0.02, rel=0.05):
    tt = np.arange(ln) / SR
    v = np.sin(2 * np.pi * f * tt) + ORGAN_2ND * np.sin(4 * np.pi * f * tt) + ORGAN_3RD * np.sin(6 * np.pi * f * tt)
    e = np.minimum(1, tt / att) * np.minimum(1, np.maximum(0, ln / SR - tt) / rel)
    return v * e


def music(dur, preset):
    """dur seconds of music, stereo at SR. preset: a PRESETS key or a dict like them."""
    cfg = PRESETS[preset] if isinstance(preset, str) else preset
    n = int(dur * SR)
    mel = np.zeros(n + SR * 8); bas = np.zeros(n + SR * 8); inn = np.zeros(n + SR * 8)
    t, k = 0.0, 0
    while t < dur:
        b, inner, notes = cfg['prog'][k % len(cfg['prog'])]
        s0 = int(t * SR)
        bl = int(BASS_LEN * SR)
        tt = np.arange(bl) / SR
        bv = (np.sin(2 * np.pi * note(b) * tt) + 0.2 * np.sin(2 * np.pi * (note(b) + BASS_DETUNE) * tt) + 0.3 * np.sin(4 * np.pi * note(b) * tt) + 0.1 * np.sin(6 * np.pi * note(b) * tt))
        be = np.minimum(1, tt / 0.03) * np.minimum(1, (BASS_LEN - tt) / 0.3) * (0.6 + 0.4 * np.exp(-tt / 1.2))
        bas[s0:s0 + bl] += bv * be
        il = int(cfg['chord'] * SR)
        inn[s0:s0 + il] += organ(note(inner), il, att=0.1, rel=0.2)
        for i, m in enumerate(notes):
            if m is None:
                continue
            j = i + 1
            while j < len(notes) and notes[j] is None:
                j += 1
            hold = (j - i) * cfg['step'] if j < len(notes) else cfg['chord'] - i * cfg['step']
            if j >= len(notes) and any(q is None for q in notes[i + 1:]):
                hold = cfg['step'] * 1.3
            a0 = int((t + i * cfg['step']) * SR)
            ln = int((hold + 0.03) * SR)
            mel[a0:a0 + ln] += organ(note(m), ln)
        t += cfg['chord']
        k += 1
    nm_ = lambda v: v[:n] / (np.sqrt(np.mean(v[:n] ** 2)) + 1e-9)
    out = nm_(mel) * LAYERS['melody'] + nm_(bas) * LAYERS['bass'] + nm_(inn) * LAYERS['inner']
    return reverb(out, MUSIC_REVERB)


def sfx(kind, dur=None):
    if kind == 'boom':
        n = int(2.8 * SR)
        t = np.arange(n) / SR
        f = 38 + 60 * np.exp(-t / 0.25)
        ph = 2 * np.pi * np.cumsum(f) / SR
        x = np.sin(ph) * np.exp(-t / 0.7) * 0.9 + lp(rng.standard_normal(n), 300) * np.exp(-t / 0.08) * 0.6
        return x
    if kind == 'splash':
        n = int(1.4 * SR)
        t = np.arange(n) / SR
        x = bp(rng.standard_normal(n), 400, 5000) * env_ad(n, 0.01, 0.35) * 0.8
        for k in range(10):
            s0 = int(rng.random() * 0.8 * SR)
            ln = int(0.05 * SR)
            tt = np.arange(ln) / SR
            fq = 600 + rng.random() * 900
            if s0 + ln < n:
                x[s0:s0 + ln] += np.sin(2 * np.pi * (fq + 4000 * tt) * tt) * np.exp(-tt / 0.015) * 0.25
        return x
    if kind == 'click':
        n = int(0.5 * SR)
        x = np.zeros(n)
        for s0 in (0, int(0.12 * SR)):
            ln = int(0.03 * SR)
            tt = np.arange(ln) / SR
            x[s0:s0 + ln] += (rng.standard_normal(ln) * 0.6 + np.sin(2 * np.pi * 2300 * tt)) * np.exp(-tt / 0.006)
        return hp(x, 800) * 0.8
    if kind == 'drill':
        n = int((dur or 1.5) * SR)
        t = np.arange(n) / SR
        f = 170 + 20 * np.sin(2 * np.pi * 3 * t)
        ph = 2 * np.pi * np.cumsum(f) / SR
        x = sum(np.sin(ph * h) / h for h in range(1, 9)) * 0.35 + bp(rng.standard_normal(n), 1500, 6000) * 0.12
        e = np.minimum(1, t / 0.08) * np.minimum(1, (t[-1] - t) / 0.15)
        return x * e * (0.75 + 0.25 * np.sin(2 * np.pi * 7 * t))
    if kind == 'grind':
        n = int((dur or 3) * SR)
        t = np.arange(n) / SR
        x = bp(rng.standard_normal(n), 2500, 7500) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.35 * t * 2 * np.pi) ** 2)
        x += np.sin(2 * np.pi * 120 * t) * 0.15
        e = np.minimum(1, t / 0.2) * np.minimum(1, (t[-1] - t) / 0.3)
        return x * e * 0.35
    if kind == 'gavel':
        n = int(0.8 * SR)
        t = np.arange(n) / SR
        return (bp(rng.standard_normal(n), 300, 3000) * np.exp(-t / 0.02) * 0.9 + np.sin(2 * np.pi * 140 * t) * np.exp(-t / 0.12) * 0.7)
    if kind == 'clink':
        n = int(1.2 * SR)
        t = np.arange(n) / SR
        return sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t / d) for f, a, d in ((1850, 0.5, 0.35), (3120, 0.3, 0.25), (5200, 0.15, 0.15)))
    if kind == 'whoosh':
        n = int(1.2 * SR)
        t = np.arange(n) / SR
        x = rng.standard_normal(n)
        out = np.zeros(n)
        for k in range(12):
            s0, s1 = k * n // 12, (k + 1) * n // 12
            fc = 400 + 3000 * (k / 12)
            out[s0:s1] = bp(x[s0:s1], fc * 0.6, fc * 1.4)
        return out * np.sin(np.pi * t / t[-1]) ** 2 * 0.5
    raise ValueError(kind)


SFX = ['boom', 'splash', 'click', 'drill', 'grind', 'gavel', 'clink', 'whoosh']


def scene_spans(tl):
    """Same as storytime_kit.scene_spans: a scene starts halfway through the pause before its first line."""
    lines = tl['lines']
    spans = []
    for i, ln in enumerate(lines):
        if not spans or spans[-1]['scene'] != ln['scene']:
            st = 0.0 if i == 0 else (lines[i - 1]['end'] + ln['start']) / 2
            spans.append({'scene': ln['scene'], 'start': st, 'lines': []})
        spans[-1]['lines'].append(ln)
    for k, sp in enumerate(spans):
        sp['end'] = spans[k + 1]['start'] if k + 1 < len(spans) else tl['duration']
    return spans


def mix(narration_wav, timeline, out_wav, preset, music_db, events=(), log=print):
    """Narration + music + effects -> out_wav (48 kHz stereo, 16-bit, -14 LUFS).
    music_db: music RMS relative to the narration's RMS while it speaks (The Locksmith -3.5, The Hero -4.1).
    events: (scene, line index in that scene, offset s from the line's start, sfx kind, gain[, length s or 'scene']).
    'scene' makes the effect fill its scene, from 0.1 s after the cut to 0.1 s before the next."""
    reseed()
    tl = json.load(open(timeline)) if isinstance(timeline, str) else timeline
    nar, sr = sf.read(narration_wav)
    nar = resample_poly(nar, SR // 6000, sr // 6000) if sr != SR else nar
    dur = len(nar) / SR
    n = len(nar)
    spans = scene_spans(tl)
    mus = music(dur, preset)[:n]
    if len(mus) < n:
        mus = np.pad(mus, ((0, n - len(mus)), (0, 0)))
    sp_idx = np.concatenate([np.arange(int(l['start'] * SR), int(l['end'] * SR)) for l in tl['lines']])
    sp_idx = sp_idx[sp_idx < n]
    speech_rms = np.sqrt(np.mean((nar[sp_idx] * VOICE_GAIN) ** 2))
    mus_rms = np.sqrt(np.mean(mus.mean(axis=1) ** 2))
    mus = mus * (speech_rms * 10 ** (music_db / 20) / mus_rms)
    fx = np.zeros(n)
    hit = sfx('boom') * OPEN_HIT
    fx[:len(hit)] += hit[:n]
    for ev in events:
        scene, li, off, kind, gain = ev[:5]
        sp = [s for s in spans if s['scene'] == scene][0]
        t0 = sp['lines'][li]['start'] + off
        d = None
        if len(ev) > 5:
            d = (sp['end'] - sp['start'] - 0.2) if ev[5] == 'scene' else ev[5]
            if ev[5] == 'scene':
                t0 = sp['start'] + 0.1
        x = sfx(kind, d) * gain
        s0 = int(t0 * SR)
        e = min(n, s0 + len(x))
        if s0 < n:
            fx[s0:e] += x[:e - s0]
    fxs = reverb(fx, FX_REVERB)
    mixd = np.stack([nar, nar], 1) * VOICE_GAIN + mus + fxs * FX_GAIN
    peak = np.abs(mixd).max()
    mixd = mixd / max(peak, 1e-6) * PEAK
    raw = os.path.splitext(out_wav)[0] + '_raw.wav'
    sf.write(raw, mixd.astype(np.float32), SR)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', raw, '-af', LOUDNORM, '-ar', str(SR), out_wav], check=True)
    log(f'mixed {dur:.2f} s -> {out_wav}')
    return out_wav


def _preview(path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(3, 1, figsize=(7.2, 12.8), dpi=100, gridspec_kw=dict(height_ratios=[1, 1, 0.8]))
    fig.patch.set_facecolor('#14161C')
    names = {'d-minor': 'd-minor  (The Locksmith)', 'g-minor': 'g-minor  (The Hero)'}
    for ax, (key, cfg) in zip(axs[:2], PRESETS.items()):
        ax.set_facecolor('#1E2027')
        for k, (b, inner, notes) in enumerate(cfg['prog']):
            t = k * cfg['chord']
            ax.add_patch(plt.Rectangle((t, b - 0.4), BASS_LEN, 0.8, color='#8FA3B8'))
            ax.add_patch(plt.Rectangle((t, inner - 0.4), cfg['chord'], 0.8, color='#5C6B7A'))
            for i, m in enumerate(notes):
                if m is None:
                    continue
                j = i + 1
                while j < len(notes) and notes[j] is None:
                    j += 1
                hold = (j - i) * cfg['step'] if j < len(notes) else cfg['chord'] - i * cfg['step']
                if j >= len(notes) and any(q is None for q in notes[i + 1:]):
                    hold = cfg['step'] * 1.3
                ax.add_patch(plt.Rectangle((t + i * cfg['step'], m - 0.4), hold - 0.04, 0.8, color='#F4C542'))
        ax.set_xlim(0, len(cfg['prog']) * cfg['chord'])
        ax.set_ylim(28, 77)
        ax.set_title(names[key], color='white', fontsize=13, loc='left')
        ax.set_xlabel('seconds', color='#C9CED6')
        ax.set_ylabel('MIDI note (yellow melody, grey inner + bass)', color='#C9CED6', fontsize=9)
        ax.tick_params(colors='#C9CED6')
        for s in ax.spines.values():
            s.set_color('#3A3F4B')
    ax = axs[2]
    ax.set_facecolor('#1E2027')
    for i, kind in enumerate(SFX):
        x = sfx(kind, 1.5 if kind in ('drill', 'grind') else None)
        x = x / (np.abs(x).max() + 1e-9) * 0.42
        tt = np.arange(len(x)) / SR
        ax.plot(tt, x + i, color='#E8EEF0', lw=0.3)
        ax.text(2.85, i, kind, color='#F4C542', fontsize=10, va='center', ha='right')
    ax.set_xlim(0, 2.9)
    ax.set_yticks([])
    ax.set_title('effects', color='white', fontsize=13, loc='left')
    ax.set_xlabel('seconds', color='#C9CED6')
    ax.tick_params(colors='#C9CED6')
    for s in ax.spines.values():
        s.set_color('#3A3F4B')
    fig.tight_layout()
    fig.savefig(path, facecolor=fig.get_facecolor())
    print('wrote', path)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--preset', default='d-minor', choices=sorted(PRESETS))
    ap.add_argument('--dur', type=float, default=24.0)
    ap.add_argument('--sfx', default=None, choices=SFX)
    ap.add_argument('--preview', action='store_true')
    a = ap.parse_args()
    out = os.path.join(HERE, 'out')
    os.makedirs(out, exist_ok=True)
    if a.preview:
        _preview(os.path.join(HERE, 'preview.png'))
    elif a.sfx:
        x = sfx(a.sfx, 1.5)
        x = reverb(x, FX_REVERB)
        p = os.path.join(out, f'sfx_{a.sfx}.wav')
        sf.write(p, (x / np.abs(x).max() * PEAK).astype(np.float32), SR)
        print('wrote', p)
    else:
        m = music(a.dur, a.preset)
        p = os.path.join(out, f'music_{a.preset}.wav')
        sf.write(p, (m / np.abs(m).max() * PEAK).astype(np.float32), SR)
        print('wrote', p)


if __name__ == '__main__':
    main()
