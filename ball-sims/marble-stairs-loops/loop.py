"""The loop's choreography: which beat every marble lands on its top tile, where it is in every frame, which tile it
hits on which beat, and when it lands in the trough.

Marble j of lane l lands on its top tile on beat E[j] of the medley and hops one tile per beat. The pattern repeats
every TOTAL beats, so instance (j, cycle c) lands on beat c * TOTAL + E[j]. Instance (j, c) at time t + loop is where
(j, c - 1) is at time t, with the same color and drift, so the frame after the last is exactly the first frame.
"""
import json
import os

import numpy as np

# ===================================================================== SETTINGS (shipped values)
MARBLE_SRGB = [(246, 246, 246), (88, 196, 250), (255, 122, 98), (255, 112, 190), (92, 228, 168), (255, 206, 64),
               (172, 128, 255)]   # the 7 marble colors of the marble music Shorts ("pick your marble")
GAPS = {                # beats between marbles, per lane; cycled, then nudged so each lane sums to the loop length
    "stairs": {0: [2, 3, 2, 3, 2, 2, 3, 3]},
    "twin": {1: [7, 8, 6, 9, 8, 7], 0: [8, 6, 9, 7, 6, 9]},
}
GAP_RANGE = {"stairs": (2, 4), "twin": (5, 11)}
FIRST = {"stairs": {0: 0}, "twin": {1: 0, 0: 3}}     # beat of each lane's first marble
VZ_STEPS = [0.0, 0.6, -0.8, -0.3, 1.0, 0.25, -1.0, 0.8, -0.5, 0.45, -0.15]   # times VZ_MAX
CYCLES = (-1, 0, 1)
SCREEN_MARGIN = 90
# ================================================================= END SETTINGS


def fill(pattern, total, rng_lo, rng_hi):
    """Gaps from `pattern`, cycled, adjusted to sum exactly to `total`, each within [rng_lo, rng_hi]."""
    n = max(1, int(round(total / (sum(pattern) / len(pattern)))))
    gaps = [pattern[i % len(pattern)] for i in range(n)]
    diff = total - sum(gaps)
    i = 0
    while diff != 0:
        k = (i * 7) % n
        step = 1 if diff > 0 else -1
        if rng_lo <= gaps[k] + step <= rng_hi:
            gaps[k] += step
            diff -= step
        i += 1
        if i > 100 * n:
            raise ValueError("cannot fit the gaps")
    return gaps


def marbles(S, total):
    out = []
    for lane, pat in GAPS[S.NAME].items():
        gaps = fill(pat, total, *GAP_RANGE[S.NAME])
        b = FIRST[S.NAME][lane]
        for g in gaps:
            out.append(dict(lane=lane, beat=b % total))
            b += g
    out.sort(key=lambda m: (m["beat"], m["lane"]))
    for j, m_ in enumerate(out):
        m_["color"] = MARBLE_SRGB[j % len(MARBLE_SRGB)]
        m_["vz"] = VZ_STEPS[j % len(VZ_STEPS)] * S.VZ_MAX
    return out


def build(S, total, outdir):
    """Positions of every instance in every frame (pos, vis), hits per beat, trough landings, tile glow events."""
    tau = S.TAU
    n_frames = int(round(total * tau * S.FPS))
    ms = marbles(S, total)
    inst = [dict(m, cycle=c, t0=(c * total + m["beat"]) * tau) for c in CYCLES for m in ms]
    pos = np.zeros((n_frames, len(inst), 3), np.float32)
    vis = np.zeros((n_frames, len(inst)), bool)
    for f in range(n_frames):
        t = f / S.FPS
        for i, m in enumerate(inst):
            if S.gone(m["t0"], t):
                continue
            p = S.hop(m["t0"], t, m["vz"], m["lane"])
            x, y, z = S.project(p)
            mg = SCREEN_MARGIN
            if z > 0 and -mg <= x <= S.W + mg and -mg <= y <= S.H + mg:
                pos[f, i] = p
                vis[f, i] = True
    hits, knocks = {}, []
    for m in ms:
        for k in range(S.T):
            hits.setdefault((m["beat"] + k) % total, []).append((m["lane"], k))
        knocks.append((m["beat"] + S.T) % total)
    glows = [[] for _ in range(S.NL * S.T)]
    for m in inst:
        for k in range(S.T):
            t = m["t0"] + k * tau
            if -3.0 <= t <= total * tau + 1.0:
                glows[m["lane"] * S.T + k].append(round(t, 5))
    data = dict(fps=S.FPS, n_frames=n_frames, total_beats=total, tau=tau, colors=[m["color"] for m in inst],
                marbles=ms, glows=[sorted(g) for g in glows])
    os.makedirs(outdir, exist_ok=True)
    np.savez_compressed(os.path.join(outdir, "marbles.npz"), pos=pos, vis=vis)
    with open(os.path.join(outdir, "timeline.json"), "w") as fh:
        json.dump(data, fh)
    return data, pos, vis, hits, sorted(knocks)


def seam_check(S, data):
    """The loop is seamless if CYCLES holds every marble that can appear: instances one cycle earlier or later than
    CYCLES must be gone for the whole loop. Returns how many frames such an instance would be on screen (want 0)."""
    total, tau = data["total_beats"], data["tau"]
    bad = 0
    for c in (min(CYCLES) - 1, max(CYCLES) + 1):
        for m in data["marbles"]:
            t0 = (c * total + m["beat"]) * tau
            for f in range(data["n_frames"]):
                if not S.gone(t0, f / S.FPS):
                    bad += 1
    return bad
