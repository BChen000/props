"""The staircase soundtrack: every tile hit plays the next note of the song, plus tray clacks and a finale chord.

At each beat the hits are sorted from the highest tile down: the first plays the melody note, the second the chord's
bass, the next three the chord tones, the rest sparkles; each voice gets +-6% random level. Tiles are panned left to
right. The finale is a big C chord with a quick sparkle run down the stairs. Sound design is in
../marble-raytrace-kit/bells.py (seeded, so a song always renders to the same samples).
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "marble-raytrace-kit"))
import bells as B
from songs import VOICING, GAINS

# ===================================================================== SETTINGS (shipped values)
VOICE_LEVEL = 0.30
TILE_PAN = [-0.42 + 0.11 * k for k in range(8)]
FINALE = [(36, 0.55), (48, 0.60), (55, 0.40), (60, 0.42), (64, 0.36), (67, 0.34), (72, 0.40), (76, 0.30),
          (79, 0.26), (84, 0.20)]
FINALE_ARP = [72, 76, 79, 84, 88, 91, 96, 100]
PAD_S = 0.5             # buffer runs this long past the video before mastering
# ================================================================= END SETTINGS


def build(tl, song, out_wav):
    rng = B.reset_rng()
    melody, chords = song["melody"], song["chords"]
    n_frames = tl["n_frames"]
    dur = n_frames / tl["fps"] + PAD_S
    buf = np.zeros((2, int(dur * B.SR)))
    by_beat = {}
    for h in tl["hits"]:
        by_beat.setdefault(h["beat"], []).append(h)
    cache = {}

    def note(m, kind):
        key = (m, kind)
        if key not in cache:
            cache[key] = B.bell(B.mtof(m), kind=kind)
        return cache[key]

    log = []
    for b in sorted(by_beat):
        hs = sorted(by_beat[b], key=lambda h: -h["tile"])
        t = hs[0]["t"]
        mel = melody[b] if b < len(melody) else 84
        ch = VOICING[chords[b] if b < len(chords) else "C"]
        voices = []
        for vi, h in enumerate(hs):
            if vi == 0:
                if mel == 0:
                    m, kind, g = ch["sp"][b % 3], "spark", 0.24
                elif mel < 0:
                    m, kind, g = -mel + 12, "spark", 0.30
                else:
                    m, kind, g = mel, "lead", 1.0
            elif vi == 1:
                m, kind, g = ch["bass"], "bass", GAINS[1]
            elif vi <= 4:
                m, kind, g = ch["inner"][vi - 2], "inner", GAINS[vi]
            else:
                m, kind, g = ch["sp"][(vi - 5) % 3], "spark", GAINS[min(vi, 7)]
            g *= 1.0 + rng.uniform(-0.06, 0.06)
            B.add(buf, note(m, kind), t, g * VOICE_LEVEL, TILE_PAN[h["tile"]])
            voices.append(m)
        log.append((b, round(t, 4), len(hs), voices))

    ft = tl["finale_t"]
    for m, g in FINALE:
        kind = "bass" if m < 55 else "lead"
        B.add(buf, note(m, kind), ft, g * VOICE_LEVEL, rng.uniform(-0.3, 0.3))
    for i, m in enumerate(FINALE_ARP):
        B.add(buf, note(m, "spark"), ft + 0.035 + i * 0.045, 0.16 * VOICE_LEVEL, TILE_PAN[7 - i])

    for im in tl["impacts"]:
        y, g = B.impact_sound(im["kind"], im["speed"], rng)
        B.add(buf, y, im["t"], g, 0.25 + 0.04 * im["z"] * -1)

    B.write_wav(out_wav, B.master(buf, n_frames / tl["fps"]))
    return log


if __name__ == "__main__":
    from songs import SONGS
    name = sys.argv[1] if len(sys.argv) > 1 else "twinkle"
    d = os.path.join(HERE, "build", name)
    tl = json.load(open(os.path.join(d, "timeline.json")))
    for row in build(tl, SONGS[name], os.path.join(d, "music.wav"))[:8]:
        print(row)
