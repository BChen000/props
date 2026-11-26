"""The loop soundtrack: every tile hit plays a note, so the music is exactly in time with the picture.

Each beat (one hop, an eighth note) has some number of hits. The beat's notes are taken from a ranked list until
every hit has one: the tune's note if one starts on this beat (and the canon voice's), the bass on the bar's main
beats, a soft broken chord below the tune, a second chord tone, then glassy sparkles. A held tune note therefore
never re-strikes; the other marbles keep a gentle music-box arpeggio going. A marble landing in the trough adds a
soft knock.

The audio is periodic: notes that ring past the end of the loop wrap round to its start, and the reverb and high-pass
are applied circularly, so the last sample leads straight into the first. Bells come from
../marble-raytrace-kit/bells.py (no samples, nothing to clear).
"""
import os
import subprocess
import sys

import numpy as np
import scipy.io.wavfile as wavf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "marble-raytrace-kit"))
import bells as B
import pipeline as P
import medleys as MD

# ===================================================================== SETTINGS (shipped values)
SEED = 31
LOUDNESS = -16.0        # LUFS integrated (the spiral stream's mix is at -16 too)
PEAK_MAX = -1.0         # dBFS; louder peaks are soft-clipped (memoryless, so the loop stays seamless)
MEL_GAIN = 0.32         # tune (lead bell)
CANON_GAIN = 0.25       # canon voice
BASS_GAIN = 0.19
ARP_GAIN = 0.085        # broken chord, one note per beat
ARP2_GAIN = 0.055
SPARK_GAIN = 0.045
KNOCK_GAIN = 0.05       # marble landing in the trough
ARP_SPAN = 15           # the broken chord sits in the 15 semitones below the tune's lowest note
REVERB_WET = 0.34
REVERB_DRY = 0.82
HP_HZ = 35.0
# ================================================================= END SETTINGS


def fit(midi, lo, hi):
    while midi < lo:
        midi += 12
    while midi > hi:
        midi -= 12
    return midi


def chord_at(song, beat):
    for b, d, name in song["chords"]:
        if b <= beat < b + d:
            return name
    return song["chords"][-1][2]


def tones(name, lo, hi):
    pcs, bass = MD.CHORDS[name]
    return sorted({fit(12 * 5 + MD.pc(p), lo, hi) for p in pcs.split()}), MD.pc(bass)


def contexts(name):
    """Per beat of the medley: dict(song, chord, onsets [(voice, midi)], bar position, meter, tune floor)."""
    songs, starts, total = MD.medley(name)
    ctx = [None] * total
    for i, (s, st) in enumerate(zip(songs, starts)):
        nxt_s = songs[(i + 1) % len(songs)]
        end = starts[i + 1] if i + 1 < len(songs) else total
        lo = min(p for v in s["voices"] for _, p, _ in v)
        on = {}
        for vi, v in enumerate(s["voices"]):
            for b, p, d in v:
                on.setdefault(b, []).append((vi, p))
        last = s["chords"][-1][2]
        for b in range(st, end):
            rb = b - st
            if rb < s["length"]:
                ch, onsets, meter, pos, floor = chord_at(s, rb), on.get(rb, []), s["meter"], rb - s["pickup"], lo
            else:
                g = rb - s["length"]
                half = (end - st - s["length"]) / 2
                ch = last if g < half else nxt_s["chords"][0][2]
                onsets, meter, pos, floor = [], s["meter"], rb - s["pickup"], lo
            bass_at = s.get("bass_at", (0, 4) if meter == 8 else (0,))
            ctx[b] = dict(song=i, chord=ch, onsets=onsets, pos=pos % meter, meter=meter, floor=floor,
                          bass_beat=(pos % meter) in bass_at)
    return songs, starts, total, ctx


def candidates(c):
    """Ranked (kind, midi, gain) for one beat."""
    out = []
    for vi, p in sorted(c["onsets"]):
        out.append(("lead", p, MEL_GAIN if vi == 0 else CANON_GAIN))
    tv, bass = tones(c["chord"], c["floor"] - ARP_SPAN, c["floor"] - 1)
    if c["bass_beat"]:
        out.append(("bass", fit(36 + bass, 36, 47), BASS_GAIN))
    pattern = tv + tv[-2:0:-1]
    k = c["pos"] % len(pattern)
    out.append(("inner", pattern[k], ARP_GAIN))
    out.append(("inner", fit(tv[(k + 1) % len(tv)] + 12, c["floor"] - 3, c["floor"] + 9), ARP2_GAIN))
    sp, _ = tones(c["chord"], 84, 95)
    for i in range(8):
        out.append(("spark", sp[(c["pos"] + i) % len(sp)] + (12 if i >= len(sp) else 0), SPARK_GAIN * 0.9 ** i))
    return out


def notes(name, hits_by_beat, knocks, tau, n_tiles):
    """-> [(t, kind, midi, gain, pan)] for the whole loop, plus the medley info."""
    songs, starts, total, ctx = contexts(name)
    ev = []
    for b in range(total):
        hs = sorted(hits_by_beat.get(b, []), key=lambda h: h[1])      # (lane, step): top of the stairs first
        if not hs:
            continue
        cand = candidates(ctx[b])
        for (lane, step), (kind, midi, g) in zip(hs, cand):
            pan = -0.42 + 0.84 * step / max(1, n_tiles - 1) + (0.06 if lane == 1 else -0.06 if lane == 0 and
                                                                 n_tiles > 8 else 0.0)
            ev.append((b * tau, kind, midi, g, float(np.clip(pan, -0.8, 0.8))))
    for b in knocks:
        ev.append((b * tau, "knock", 0, KNOCK_GAIN, 0.35))
    return ev, songs, starts, total


def render(ev, total_s, out_wav):
    """Circular mix: wrap every note into the loop, circular reverb and high-pass, memoryless limiting."""
    B.reset_rng()
    rng = np.random.default_rng(SEED)
    n = int(round(total_s * B.SR))
    dry = np.zeros((2, n))
    cache = {}
    for t, kind, midi, g, pan in ev:
        if kind == "knock":
            y = B.knock(rng.uniform(620, 820), 0.020, 0.35, 0.12)
        else:
            key = (midi, kind)
            if key not in cache:
                cache[key] = B.bell(B.mtof(midi), kind=kind)
            y = cache[key]
        gl, gr = B.pan_gains(pan)
        i0 = int(round(t * B.SR)) % n
        k = min(len(y), n - i0)
        dry[0, i0:i0 + k] += y[:k] * g * gl
        dry[1, i0:i0 + k] += y[:k] * g * gr
        if k < len(y):                       # rings past the end of the loop: wrap to the start
            dry[0, :len(y) - k] += y[k:] * g * gl
            dry[1, :len(y) - k] += y[k:] * g * gr
    ir = B.reverb_ir()
    spec = np.fft.rfft(dry, n=n, axis=1)
    wet = np.fft.irfft(spec * np.fft.rfft(ir, n=n, axis=1), n=n, axis=1)
    mix = dry * REVERB_DRY + wet * REVERB_WET
    f = np.fft.rfftfreq(n, 1.0 / B.SR)
    hp = 1.0 / np.sqrt(1.0 + (HP_HZ / np.maximum(f, 1e-6)) ** 4)
    mix = np.fft.irfft(np.fft.rfft(mix, axis=1) * hp, n=n, axis=1)
    mix = mix / np.abs(mix).max() * 0.89
    mix = np.tanh(mix * 1.15) / np.tanh(1.15)
    tmp = out_wav[:-4] + ".pre.wav"
    wavf.write(tmp, B.SR, mix.T.astype(np.float32))
    integ, _ = P.loudness(tmp)
    os.remove(tmp)
    mix *= 10 ** ((LOUDNESS - integ) / 20)
    ceil = 10 ** (PEAK_MAX / 20)
    over = np.abs(mix) > 0.8 * ceil
    if over.any():
        a = 0.8 * ceil
        mix = np.where(over, np.sign(mix) * (a + (ceil - a) * np.tanh((np.abs(mix) - a) / (ceil - a))), mix)
    wavf.write(out_wav, B.SR, mix.T.astype(np.float32))
    integ2, peak2 = P.loudness(out_wav)
    return integ2, peak2


def seam_jump(wav):
    """Size of the step from the last sample to the first, against the typical step between neighbours."""
    _, x = wavf.read(wav)
    d = np.abs(np.diff(x, axis=0))
    return float(np.abs(x[0] - x[-1]).max()), float(np.percentile(d, 99.9))
