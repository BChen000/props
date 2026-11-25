"""The spiral soundtrack: each segment a marble rolls onto plays its own note, so marbles two bars apart sing a round.

Notes are bright "lead" bells, panned by where the marble is on screen, +-5% random level. The finale is a C chord
(bass + chord tones) with a sparkle run when the last marble lands in the dish; dish impacts add clacks. Sound
design is in ../marble-raytrace-kit/bells.py (seeded, so the same timeline always renders to the same samples).
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "marble-raytrace-kit"))
import bells as B

# ===================================================================== SETTINGS (shipped values)
SEED = 11               # this soundtrack's own generator (levels, pans, clack pitches); bells.py keeps seed 7
NOTE_LEVEL = 0.34
FINALE = [(48, 0.50), (55, 0.36), (60, 0.40), (64, 0.34), (67, 0.32), (72, 0.36), (76, 0.28), (79, 0.24)]
FINALE_ARP = [72, 76, 79, 84, 88, 91, 96]
PAD_S = 3.0
# ================================================================= END SETTINGS


def build(tl, pos, out_wav, fps):
    B.reset_rng()
    rng = np.random.default_rng(SEED)
    n_frames = tl["n_frames"]
    total = n_frames / tl["fps"]
    buf = np.zeros((2, int((total + PAD_S) * B.SR)))
    cache = {}

    def note(m, kind):
        if (m, kind) not in cache:
            cache[(m, kind)] = B.bell(B.mtof(m), kind=kind)
        return cache[(m, kind)]

    for n in tl["notes"]:
        f = min(n_frames - 1, int(round(n["t"] * fps)))
        x = float(pos[f, n["marble"]][0])
        pan = float(np.clip(x / 11.0, -0.8, 0.8)) * 0.85
        g = NOTE_LEVEL * (1 + rng.uniform(-0.05, 0.05))
        B.add(buf, note(n["pitch"], "lead"), n["t"], g, pan)

    ft = tl["finale_t"]
    for m, g in FINALE:
        B.add(buf, note(m, "bass" if m < 55 else "inner"), ft, g * 0.30, rng.uniform(-0.3, 0.3))
    for i, m in enumerate(FINALE_ARP):
        B.add(buf, note(m, "spark"), ft + 0.04 + i * 0.07, 0.15 * 0.30, -0.5 + i * 0.16)

    for im in tl["impacts"]:
        pan = float(np.clip(im["x"] / 12.0, -0.7, 0.7))
        y, g = B.impact_sound(im["kind"], im["speed"], rng)
        B.add(buf, y, im["t"], g, pan)

    B.write_wav(out_wav, B.master(buf, total))


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "row-row-row"
    d = os.path.join(HERE, "build", name)
    tl = json.load(open(os.path.join(d, "timeline.json")))
    build(tl, np.load(os.path.join(d, "marbles.npz"))["pos"], os.path.join(d, "music.wav"), tl["fps"])
