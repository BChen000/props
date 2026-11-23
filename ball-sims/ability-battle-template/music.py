#!/usr/bin/env python3
"""music: the POWER BALLS music bed (synthesized 128 BPM EDM in A minor) + tape stop + victory fanfare.

Am-F-C-G, one chord per bar. Layers come in over the first bars (kick/clap/hats, offbeat bass, pad from
bar 1, 16th arp from bar 2, 16th hats + lead motif from bar 4) and everything brightens and doubles up
from the FINAL DUEL bar. tape_stop() winds it down for the slow-mo final blow; fanfare() plays the
winner jingle (A major) with crash and party poppers. Uses the DSP helpers and drums in sfx.py.

    python music.py --export assets          # loop_main.wav, loop_duel.wav, victory_fanfare.wav
    python music.py --preview preview.png    # spectrogram + section map (needs matplotlib)
"""
import math
import sys
from pathlib import Path

import numpy as np

import sfx
from sfx import SR, tt, lp, hp, noise, saw_add, square_add, env_exp, norm, add

# ---------------------------------------------------------------- settings
BPM = 128
BEAT = 60 / BPM
BAR = 4 * BEAT
CHORDS = [  # (bass Hz, chord tones Hz for pad/arp)
    (55.0, [220.0, 261.63, 329.63]),      # Am
    (43.65, [174.61, 220.0, 261.63]),     # F
    (65.41, [196.0, 261.63, 329.63]),     # C
    (49.0, [196.0, 246.94, 293.66]),      # G
]
LEAD = [  # per chord bar: (start in 8ths, semitones from A4, length in 8ths)
    [(0, 0, 2), (2, 3, 1), (3, 7, 1), (4, 10, 2), (6, 7, 1), (7, 3, 1)],     # Am
    [(0, -4, 2), (2, 0, 1), (3, 3, 1), (4, 8, 3), (7, 7, 1)],                # F
    [(0, 3, 2), (2, 7, 1), (3, 10, 1), (4, 12, 2), (6, 10, 1), (7, 7, 1)],   # C
    [(0, 2, 2), (2, 7, 1), (3, 5, 1), (4, 2, 2), (6, -2, 2)],                # G
]
LAYERS = dict(pad_from_bar=1, arp_from_bar=2, hats16_from_bar=4, lead_from_bar=4)
GAINS = dict(kick=0.9, clap=0.7, clap_bar0=0.45, open_hat=0.55, open_hat_bar0=0.3, closed_hat=0.35,
             closed_hat_duel=0.5, bass=0.55, pad=0.2, arp=0.14, arp_duel=0.16, lead=0.13, lead_duel=0.16,
             echo=0.35, lead_echo=0.3)
CUTOFFS = dict(bass=1300, bass_duel=1900, pad=2600, pad_duel=4000, arp=3500, arp_duel=5500, lead=4200)
SIDECHAIN = dict(depth=0.65, release=0.09)
FANFARE_NOTES = [(0.0, 659.25), (0.13, 880.0), (0.26, 1108.73), (0.39, 1318.5)]   # E5 A5 C#6 E6
FANFARE_CHORD = (220.0, 277.18, 329.63, 440.0)                                     # A major


def configure(**kw):
    g = globals()
    for k, v in kw.items():
        if k not in g:
            raise KeyError(k)
        g[k] = v


def build_bed(n, t0, t1, tau_duel, bar_offset=0):
    """Stereo bed (2 x n samples) playing from t0 to t1 s; bars after the one holding tau_duel are intense.
    bar_offset shifts which arrangement bar plays first (0 = the video's build-up from bar 0)."""
    G, CU = GAINS, CUTOFFS
    buf = np.zeros((2, n))
    pad_bus = np.zeros((2, n))
    k = sfx.kick()
    cl = sfx.clap()
    hc = sfx.hat()
    ho = sfx.hat(True)
    nbars = int(math.ceil((t1 - t0) / BAR)) + 1
    kick_times = []
    duel_bar = int((tau_duel - t0) // BAR) + 1
    for bi in range(nbars):
        bt = t0 + bi * BAR
        if bt > t1:
            break
        lb = bi + bar_offset
        bass_f, tones = CHORDS[lb % 4]
        intense = bi >= duel_bar
        for beat in range(4):
            x = bt + beat * BEAT
            if x >= t1:
                break
            add(buf, k, x, G['kick'])
            kick_times.append(x)
            if beat in (1, 3):
                add(buf, cl, x, G['clap'] if lb >= 1 else G['clap_bar0'])
            add(buf, ho, x + BEAT / 2, G['open_hat'] if lb >= 1 else G['open_hat_bar0'], pan=0.25)
            if lb >= LAYERS['hats16_from_bar']:
                for sx in (0.25, 0.75):
                    add(buf, hc, x + BEAT * sx, G['closed_hat_duel'] if intense else G['closed_hat'], pan=-0.25)
            bd = BEAT * 0.45
            bass = saw_add(bass_f * 2, bd, nh=30) * 1.0 + np.sin(2 * np.pi * bass_f * 2 * tt(bd)) * 0.35
            be = np.minimum(1, tt(bd) / 0.004) * np.exp(-tt(bd) / 0.16)
            bass = lp(bass * be, CU['bass'] if not intense else CU['bass_duel'])
            add(buf, bass, x + BEAT / 2, G['bass'])
        if lb >= LAYERS['pad_from_bar']:
            pd = BAR
            pad = np.zeros(int(pd * SR))
            for f in tones:
                for dt_ in (-0.006, 0.0, 0.006):
                    pad += saw_add(f, pd, nh=18, detune=dt_)
            pe = np.minimum(1, tt(pd) / 0.08) * np.minimum(1, (pd - tt(pd)) / 0.1)
            pad = lp(pad * pe, CU['pad'] if not intense else CU['pad_duel'])
            add(pad_bus, norm(pad) * G['pad'], bt, pan=-0.3)
            add(pad_bus, norm(pad) * G['pad'], bt + 0.012, pan=0.3)
        if lb >= LAYERS['arp_from_bar']:
            arp_notes = [tones[0] * 2, tones[1] * 2, tones[2] * 2, tones[0] * 4]
            for s16 in range(16):
                x = bt + s16 * BEAT / 4
                if x >= t1:
                    break
                f = arp_notes[s16 % 4] * (2 if (intense and s16 % 8 >= 4) else 1)
                d = BEAT / 4 * 0.95
                n_ = square_add(f, d) * np.exp(-tt(d) / 0.05)
                n_ = lp(n_, CU['arp'] if not intense else CU['arp_duel'])
                g = G['arp'] if not intense else G['arp_duel']
                add(buf, n_, x, g, pan=0.35 if s16 % 2 else -0.35)
                add(buf, n_, x + BEAT * 0.75, g * G['echo'], pan=-0.35 if s16 % 2 else 0.35)
        if lb >= LAYERS['lead_from_bar']:
            motif = LEAD[lb % 4]
            for st8, semis, ln in motif:
                x = bt + st8 * BEAT / 2
                if x >= t1:
                    break
                f = 440.0 * 2 ** (semis / 12)
                d = ln * BEAT / 2 * 0.9
                v = (square_add(f, d) * 0.5 + saw_add(f, d, nh=12) * 0.6)
                e = np.minimum(1, tt(d) / 0.006) * np.exp(-tt(d) / (0.18 if ln > 1 else 0.1))
                v = lp(v * e, CU['lead'])
                gl = G['lead'] if not intense else G['lead_duel']
                add(buf, v, x, gl, pan=0.1)
                add(buf, v, x + BEAT * 0.75, gl * G['lead_echo'], pan=-0.4)
    gain = np.ones(n)
    for kt in kick_times:
        i = int(kt * SR)
        L = int(0.3 * SR)
        if i < n:
            seg = 1 - SIDECHAIN['depth'] * np.exp(-np.arange(min(L, n - i)) / SR / SIDECHAIN['release'])
            gain[i:i + len(seg)] = np.minimum(gain[i:i + len(seg)], seg)
    buf += pad_bus * gain
    return buf


def tape_stop(buf, at, d=0.75):
    """Replace buf from `at` with a decelerating playback of what followed, then silence."""
    i0 = int(at * SR)
    n = int(d * SR)
    t = np.arange(n) / SR
    rate = (1 - t / d) ** 1.3
    pos = i0 + np.cumsum(rate)
    out = np.zeros((2, n))
    for ch in range(2):
        out[ch] = np.interp(pos, np.arange(buf.shape[1]), buf[ch])
    fade = np.minimum(1, (1 - t / d) * 3)
    buf[:, i0:i0 + n] = out * fade
    buf[:, i0 + n:] = 0


def fanfare(at, buf):
    """Winner jingle mixed into buf at `at` s: E-A-C#-E arpeggio, A major pad, kick, crash, 3 party poppers."""
    for st, f in FANFARE_NOTES:
        d = 0.16 if st < 0.39 else 2.6
        v = saw_add(f, d, nh=14) + saw_add(f, d, nh=14, detune=0.004)
        e = np.minimum(1, tt(d) / 0.01) * (np.exp(-tt(d) / 0.9) if d > 1 else np.exp(-tt(d) / 0.12))
        add(buf, lp(v * e, 5000), at + st, 0.2, pan=0.0)
    d = 3.8
    ch = np.zeros(int(d * SR))
    for f in FANFARE_CHORD:
        ch += saw_add(f, d, nh=16) + saw_add(f, d, nh=16, detune=0.005)
    e = np.minimum(1, tt(d) / 0.05) * np.exp(-tt(d) / 1.6)
    add(buf, lp(norm(ch * e), 2600) * 0.33, at + 0.39)
    add(buf, sfx.kick(0.5), at + 0.39, 1.0)
    add(buf, sfx.sfx_crash(2.5), at + 0.39, 0.8)
    for j in range(3):
        pp = hp(noise(0.08), 1500) * env_exp(0.08, 0.02)
        add(buf, norm(pp) * 0.45, at + 0.02 + j * 0.07, pan=(-0.6, 0.6, 0.0)[j])


def render_loop(intense=False, bars=4, first_bar=4):
    """A seamless `bars`-bar loop with the full arrangement (bar index first_bar on, so every layer plays).
    Spill-over (echoes, releases) past the loop end is wrapped back onto its start."""
    tail = 1.0
    n_loop = int(round(bars * BAR * SR))
    n = n_loop + int(tail * SR)
    buf = build_bed(n, 0.0, bars * BAR - 1e-9, -1e9 if intense else 1e9, bar_offset=first_bar)
    out = buf[:, :n_loop].copy()
    out[:, :n - n_loop] += buf[:, n_loop:]
    return out


def write_wav(path, x):
    x = np.clip(np.asarray(x, dtype=float), -1, 1)
    data = (x * 32767).astype(np.int16)
    import wave
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.T.tobytes())


def export(dest):
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    sfx.reseed()
    main = render_loop(False)
    duel = render_loop(True)
    fan = np.zeros((2, int(4.4 * SR)))
    fanfare(0.0, fan)
    peak = max(np.abs(main).max(), np.abs(duel).max())
    write_wav(dest / 'loop_main.wav', main / peak * 0.89)
    write_wav(dest / 'loop_duel.wav', duel / peak * 0.89)
    write_wav(dest / 'victory_fanfare.wav', fan / np.abs(fan).max() * 0.89)
    return ['loop_main.wav', 'loop_duel.wav', 'victory_fanfare.wav']


def preview(path):
    """Spectrogram of a 12-bar bed with the duel switch at bar 8, then tape stop and fanfare."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from scipy import signal as sg
    sfx.reseed()
    t_stop = 12 * BAR
    n = int((t_stop + 5.2) * SR)
    bed = build_bed(n, 0.0, t_stop + 0.8, 7.5 * BAR)
    tape_stop(bed, t_stop, 0.7)
    fanfare(t_stop + 0.9, bed)
    x = bed.mean(axis=0)
    f, t, Sxx = sg.spectrogram(x, SR, nperseg=2048, noverlap=1536)
    fig, ax = plt.subplots(figsize=(13, 4.6), facecolor='#130D22')
    ax.pcolormesh(t, f, 10 * np.log10(Sxx + 1e-12), shading='auto', vmin=-110, vmax=-30, cmap='magma')
    ax.set_yscale('symlog', linthresh=200)
    ax.set_ylim(30, 12000)
    ax.set_facecolor('#0D0D17')
    marks = [(0, 'drums + bass'), (BAR, '+pad'), (2 * BAR, '+arp'), (4 * BAR, '+lead, 16th hats'),
             (8 * BAR, 'FINAL DUEL: brighter, arp up an octave'), (t_stop, 'tape stop'), (t_stop + 0.9, 'fanfare')]
    for m, (xm, lab) in enumerate(marks):
        ax.axvline(xm, color='#FED64D', lw=1)
        ax.text(xm + 0.1, (9000, 4200, 2000)[m % 3], lab, color='white', fontsize=8, va='top',
                bbox=dict(facecolor='#130D22', edgecolor='none', alpha=0.7, pad=1.5))
    ax.set_xlim(0, t[-1])
    ax.set_title(f'POWER BALLS music bed: {BPM} BPM, Am-F-C-G', color='white', loc='left')
    ax.tick_params(colors='#8a86a0')
    ax.set_xlabel('seconds', color='#8a86a0')
    ax.set_ylabel('Hz', color='#8a86a0')
    fig.tight_layout()
    fig.savefig(path, dpi=90, facecolor=fig.get_facecolor())


def style():
    return {
        'tempo_bpm': BPM, 'key': 'A minor', 'progression': 'Am - F - C - G (one bar each)', 'sample_rate': SR,
        'chords_hz': CHORDS, 'lead_motif': LEAD, 'layers': LAYERS, 'gains': GAINS, 'lowpass_hz': CUTOFFS,
        'sidechain': SIDECHAIN, 'fanfare_notes_hz': FANFARE_NOTES, 'fanfare_chord_hz': FANFARE_CHORD,
        'tape_stop': 'rate (1 - t/d)^1.3 over 0.7 s in the video, then silence',
        'mix_in_video': 'bed x0.2 under effects x0.9, high-passed at 35 Hz, limited, then -14 LUFS',
    }


if __name__ == '__main__':
    if '--export' in sys.argv:
        out = sys.argv[sys.argv.index('--export') + 1]
        print('wrote', export(out), 'to', out)
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
