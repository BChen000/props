"""The twin-staircase soundtrack: the front lane plays the melody and the back lane the harmony, one note per beat.

Per beat and lane, hits are sorted from the highest tile down. Melody lane: first hit = melody note (bright lead
bell), second = the same note an octave up as a sparkle, more = chord sparkles. Harmony lane: first hit = harmony
note (softer lead bell), second = chord bass, more = chord tones. Lanes are panned apart; +-5% random level per
voice. The finale is a C chord with a sparkle run when the last marble lands. Sound design is in
../marble-raytrace-kit/bells.py (seeded, so the same timeline always renders to the same samples).
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "marble-raytrace-kit"))
import bells as B
from songs import VOICING

# ===================================================================== SETTINGS (shipped values)
SEED = 5                # this soundtrack's own generator (levels, pans, clack pitches); bells.py keeps seed 7
LANE_PAN = {1: -0.35, 0: 0.35}
VOICE_LEVEL = 0.30
FINALE = [(36, 0.50), (48, 0.55), (55, 0.36), (60, 0.40), (64, 0.34), (67, 0.32), (72, 0.38), (76, 0.30),
          (79, 0.26), (84, 0.20)]
FINALE_ARP = [72, 76, 79, 84, 88, 91, 96, 100]
PAD_S = 3.0
# ================================================================= END SETTINGS


def build(tl, song, out_wav):
    B.reset_rng()
    rng = np.random.default_rng(SEED)
    mel_line, har_line, chords = song["melody"], song["harmony"], song["chords"]
    n_frames = tl["n_frames"]
    total = n_frames / tl["fps"]
    buf = np.zeros((2, int((total + PAD_S) * B.SR)))
    cache = {}

    def note(m, kind):
        if (m, kind) not in cache:
            cache[(m, kind)] = B.bell(B.mtof(m), kind=kind)
        return cache[(m, kind)]

    by_beat = {}
    for h in tl["hits"]:
        by_beat.setdefault(h["beat"], []).append(h)
    for b in sorted(by_beat):
        hs = by_beat[b]
        t = hs[0]["t"]
        mel = mel_line[b] if b < len(mel_line) else 84
        har = har_line[b] if b < len(har_line) else 76
        v = VOICING[chords[b] if b < len(chords) else "C"]
        for lane in (1, 0):
            lh = sorted([h for h in hs if h["lane"] == lane], key=lambda h: -h["step"])
            for vi, h in enumerate(lh):
                pan = LANE_PAN[lane] + 0.04 * (h["step"] - 7.5) / 7.5
                if lane == 1:
                    if vi == 0:
                        if mel < 0:
                            m, kind, g = -mel + 12, "spark", 0.30
                        else:
                            m, kind, g = mel, "lead", 1.0
                    elif vi == 1:
                        m, kind, g = abs(mel) + 12, "spark", 0.22
                    else:
                        m, kind, g = v["sp"][(vi - 2) % 2], "spark", 0.16
                else:
                    if vi == 0:
                        if har < 0:
                            m, kind, g = -har, "inner", 0.32
                        else:
                            m, kind, g = har, "lead", 0.62
                    elif vi == 1:
                        m, kind, g = v["bass"], "bass", 0.55
                    else:
                        m, kind, g = v["mid"][(vi - 2) % 2], "inner", 0.26
                g *= 1.0 + rng.uniform(-0.05, 0.05)
                B.add(buf, note(m, kind), t, g * VOICE_LEVEL, pan)

    ft = tl["finale_t"]
    for m, g in FINALE:
        B.add(buf, note(m, "bass" if m < 55 else "inner"), ft, g * VOICE_LEVEL, rng.uniform(-0.3, 0.3))
    for i, m in enumerate(FINALE_ARP):
        B.add(buf, note(m, "spark"), ft + 0.04 + i * 0.05, 0.15 * VOICE_LEVEL, -0.4 + i * 0.11)

    for im in tl["impacts"]:
        pan = float(np.clip(-im["z"] / 10.0, -0.6, 0.6))
        y, g = B.impact_sound(im["kind"], im["speed"], rng)
        B.add(buf, y, im["t"], g, pan)

    B.write_wav(out_wav, B.master(buf, total))


if __name__ == "__main__":
    from songs import SONGS
    name = sys.argv[1] if len(sys.argv) > 1 else "ode-to-joy"
    d = os.path.join(HERE, "build", name)
    build(json.load(open(os.path.join(d, "timeline.json"))), SONGS[name], os.path.join(d, "music.wav"))
