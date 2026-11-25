"""Episode timeline: shot order and lengths (frames at 24 fps), crossfades, and where each narration line starts.

score.py, mix.py and assemble.py all read this. For a new episode, replace SEGS and VO; run it to list line
starts/ends and flag overlaps: python timeline.py
"""
import json
import os
HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.environ.get("WILDLORE_WORK", os.path.join(HERE, "build"))   # episode folder: out/ (shot renders), vo/, audio/, final/
FPS = 24
# (name, file, frames, xfade_in_frames)
# v2 pacing: B, D, E, IJ, K, N, Q, R hold longer at the end so the narration breathes at each change of subject
SEGS = [
    ("A", "A.mp4", 62, 0), ("B", "B.mp4", 182, 0), ("C", "C.mp4", 151, 0), ("D", "D.mp4", 163, 0), ("E", "E.mp4", 209, 0),
    ("F", "F.mp4", 166, 0), ("H1", "H1.mp4", 104, 12), ("H2", "H2.mp4", 164, 8), ("H3", "H3.mp4", 94, 8), ("IJ", "IJ.mp4", 355, 10),
    ("K", "K.mp4", 242, 0), ("L1", "L1.mp4", 124, 0), ("L2", "L2.mp4", 134, 0), ("M1", "M1.mp4", 100, 0), ("M2", "M2.mp4", 130, 0),
    ("N", "N.mp4", 352, 0), ("O", "O.mp4", 88, 0), ("P", "P.mp4", 206, 0), ("Q", "Q.mp4", 239, 0), ("R", "R.mp4", 128, 0),
    ("S", "S.mp4", 384, 12),
]


def starts():
    out = {}
    t = 0
    for name, f, n, xf in SEGS:
        t -= xf
        out[name] = t
        t += n
    return out, t


ST, TOTAL = starts()
S = {k: v / FPS for k, v in ST.items()}
# VO line start times (seconds), anchored to shots
VO = [
    ("A", 0.75), ("B", 0.3), ("C", 0.25), ("D", 0.25), ("E", 0.25), ("F", 0.3), ("F", 3.85), ("H1", 0.65),
    ("IJ", 0.55), ("IJ", 4.95), ("K", 0.35), ("L1", 0.3), ("M1", 0.2), ("N", 0.3), ("N", 3.65), ("N", 7.0),
    ("O", 0.3), ("P", 0.25), ("Q", 0.3), ("R", 0.3), ("S", 0.6),
]
if __name__ == "__main__":
    info = json.load(open(os.path.join(WORK, "vo", "lines_info.json")))
    prev_end = 0
    for i, ((shot, off), li) in enumerate(zip(VO, info)):
        t = S[shot] + off
        flag = "  <-- OVERLAP" if t < prev_end + 0.3 else ""
        print(f"{i:2d} {shot:3s} start {t:7.2f} end {t + li['dur']:7.2f} gap {t - prev_end:5.2f}{flag}  {li['text'][:40]}")
        prev_end = t + li['dur']
    print("TOTAL", TOTAL, TOTAL / FPS)
    for k, v in S.items():
        print(k, round(v, 2))
