#!/usr/bin/env python3
"""The stream soundtrack: the public-domain tunes of the marble music Shorts (stream_songs.py) played on the same
synthesized mallet bells (../marble-raytrace-kit/bells.py), arranged calmer for a 24/7 background. No samples, no
recordings, so nothing to clear.

Each song goes through its `passes`: "soft" (melody, round bass, soft rolled chords), "flow" (adds a broken-chord
arpeggio) and "sparkle" (adds glassy octave sparkles on longer melody notes); a `canon` pass plays the melody as a
round over a tonic pedal. Every song ends on its tonic chord with a sparkle run, is mastered with the kit's reverb,
leveled to LOUDNESS LUFS, and the songs are joined with GAP_S of silence (also after the last, so the mix loops).

Usage:
  python3 music.py                      # -> build/marble_bells_mix.m4a (+ build/music/*.wav), prints the running order
  python3 music.py --only "Jingle Bells"
"""
import argparse
import os
import subprocess
import sys

import numpy as np
import scipy.io.wavfile as wavf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "marble-raytrace-kit"))
import bells as B
import pipeline as P
import stream_songs as SS

# ===================================================================== SETTINGS (shipped values)
BUILD = os.environ.get("BUILD_DIR", os.path.join(HERE, "build"))
OUT_NAME = "marble_bells_mix.m4a"
SEED = 23
LOUDNESS = -16.0        # LUFS integrated, per song
PEAK_LIMIT = 0.891      # -1 dBFS limiter in the final encode
GAP_S = 1.8             # silence between songs (after each song's ring-out)
TAIL_S = 3.4            # ring-out after the final chord
MEL_GAIN = 0.32         # lead bell (melody)
BASS_GAIN = 0.19
INNER_GAIN = 0.072      # per chord tone
SPARK_GAIN = 0.05
JITTER_S = 0.006        # timing humanization, +-
AUDIO_BITRATE = "192k"
# ================================================================= END SETTINGS


def fit(midi, lo, hi):
    while midi < lo:
        midi += 12
    while midi > hi:
        midi -= 12
    return midi


def arrange(song, rng):
    """-> list of (beat, midi, kind, gain, pan) and the song's length in beats (final chord included)."""
    ev = []
    mel_lo = min(n[1] for n in song["notes"])
    hi = mel_lo - 1
    lo = hi - 15
    step = {6: 3.0, 8: 2.0}.get(song["meter"], 1.0)
    tonic_tones, tonic_bass = song["chords"][-1][2], song["chords"][-1][3]
    t0 = 0.0
    for ps in song["passes"]:
        style = ps["style"]
        canon = ps.get("canon", [0])
        length = song["end"] + max(canon)
        pans = [0.0] if len(canon) == 1 else [-0.28, 0.28, -0.6, 0.6][:len(canon)]
        for vi, off in enumerate(canon):
            for b, midi, d in song["notes"]:
                tb = t0 + off + b
                ev.append((tb, midi, "lead", MEL_GAIN * (1.0 if vi == 0 else 0.78) * rng.uniform(0.94, 1.04),
                           pans[vi] + rng.uniform(-0.07, 0.07)))
                if style == "sparkle" and vi == 0 and d >= 1.0:
                    ev.append((tb, midi + 12, "spark", SPARK_GAIN * rng.uniform(0.85, 1.1), rng.choice([-0.45, 0.45])))
        if len(canon) > 1:
            for bb in np.arange(0, length, song["meter"]):
                ev.append((t0 + bb, fit(tonic_bass, 36, 48), "bass", BASS_GAIN * 0.85, 0.0))
                if style == "sparkle":
                    for i, x in enumerate(sorted({fit(x, lo, hi) for x in tonic_tones})):
                        ev.append((t0 + bb + 0.03 * i, x, "inner", INNER_GAIN * 0.55, -0.3 + 0.3 * i))
        else:
            for b, d, tones, bass in song["chords"]:
                tb = t0 + b
                ev.append((tb, fit(bass, 36, 48), "bass", BASS_GAIN * (0.8 if style == "soft" else 1.0),
                           rng.uniform(-0.08, 0.08)))
                tv = sorted({fit(x, lo, hi) for x in tones})
                if style == "soft":
                    for i, x in enumerate(tv):
                        ev.append((tb + 0.04 * i, x, "inner", INNER_GAIN * 0.85, -0.3 + 0.6 * i / max(1, len(tv) - 1)))
                else:
                    pattern = tv + tv[-2:0:-1]
                    n = max(1, int(round(d / step)))
                    for i in range(n):
                        ev.append((tb + i * step, pattern[i % len(pattern)], "inner",
                                   INNER_GAIN * (1.0 if i == 0 else 0.82) * rng.uniform(0.9, 1.05), (-0.3, 0.3)[i % 2]))
        t0 += length
    ev.append((t0, fit(tonic_bass, 36, 48), "bass", BASS_GAIN * 1.1, 0.0))
    tv = sorted({fit(x, lo, hi) for x in tonic_tones})
    for i, x in enumerate(tv):
        ev.append((t0 + 0.035 * i, x, "inner", INNER_GAIN * 1.15, -0.3 + 0.6 * i / max(1, len(tv) - 1)))
    run = sorted({fit(x, 84, 95) for x in tonic_tones}) + sorted({fit(x, 96, 107) for x in tonic_tones})
    for i, x in enumerate(run[:6]):
        ev.append((t0 + 0.12 + 0.07 * i * song["bpm"] / 60.0, x, "spark", SPARK_GAIN * 0.9, -0.5 + 0.2 * i))
    return ev, t0


def render_song(song, rng, cache):
    ev, beats = arrange(song, rng)
    spb = 60.0 / song["bpm"]
    total = beats * spb + TAIL_S
    buf = np.zeros((2, int((total + 1.0) * B.SR)))
    for b, midi, kind, g, pan in ev:
        key = (midi, kind)
        if key not in cache:
            cache[key] = B.bell(B.mtof(midi), kind=kind)
        t = max(0.0, b * spb + rng.uniform(-JITTER_S, JITTER_S))
        B.add(buf, cache[key], t, g, float(np.clip(pan, -0.9, 0.9)))
    return B.master(buf, total), total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    out_dir = os.path.join(BUILD, "music")
    os.makedirs(out_dir, exist_ok=True)
    B.reset_rng()
    rng = np.random.default_rng(SEED)
    cache = {}
    pieces = []
    t = 0.0
    for i, fn in enumerate(SS.PLAYLIST):
        song = fn()
        if args.only and song["name"] != args.only:
            continue
        samples, dur = render_song(song, rng, cache)
        wav = os.path.join(out_dir, f"{i + 1:02d}.wav")
        B.write_wav(wav, samples)
        integ, peak = P.loudness(wav)
        gain = 10 ** ((LOUDNESS - integ) / 20)
        pieces.append(samples.astype(np.float32) / 32768.0 * gain)
        pieces.append(np.zeros((int(GAP_S * B.SR), 2), np.float32))
        P.log(f"{t / 60:5.2f} min  {song['name']:<31s} {dur:6.1f} s  {integ:6.1f} LUFS -> {LOUDNESS:.0f}")
        t += dur + GAP_S
    mix = np.concatenate(pieces)
    wav = os.path.join(BUILD, OUT_NAME[:-4] + ".wav")
    wavf.write(wav, B.SR, mix)
    out = os.path.join(BUILD, OUT_NAME)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-af", f"alimiter=limit={PEAK_LIMIT}:level=false",
                    "-c:a", "aac", "-b:a", AUDIO_BITRATE, "-ar", "48000", "-movflags", "+faststart", out], check=True)
    integ, peak = P.loudness(out)
    P.log(f"mix -> {out}: {len(mix) / B.SR / 60:.2f} min, {integ:.1f} LUFS, peak {peak:.1f} dBFS")


if __name__ == "__main__":
    main()
