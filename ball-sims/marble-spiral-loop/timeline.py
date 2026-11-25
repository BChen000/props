"""Motion of the spiral loop: every marble rolls at one constant speed along the feeder rail, down the helix and out
along the exit rail. Marbles leave an off-screen start point on a fixed pattern that repeats every LOOP_S seconds,
so the last frame leads straight back into the first.

Marble instance (slot j, cycle c) starts at c * LOOP_S + OFFSETS[j]. Instance (j, c) at time t + LOOP_S is where
(j, c - 1) is at time t and has the same color, so the frames at t and t + LOOP_S match exactly.
build(outdir) writes outdir/marbles.npz (pos, vis) and outdir/timeline.json (colors, segment glow events and holds).
"""
import json
import math
import os

import numpy as np

import scene as S

# ===================================================================== SETTINGS (shipped values)
LOOP_S = 24.0           # loop length (a multiple of 2 s keeps 2-second keyframes aligned when the loop repeats)
SPEED = 11.0            # roll speed, units per second (marble radius = 1)
GAPS = [1.2, 2.1, 1.5, 1.0, 2.2, 1.6, 1.9, 1.1, 2.0, 1.7, 1.4, 2.2, 1.0, 3.1]   # seconds between marbles, sum = LOOP_S
MARBLE_SRGB = [(246, 246, 246), (88, 196, 250), (255, 122, 98), (255, 112, 190), (92, 228, 168), (255, 206, 64),
               (172, 128, 255)]
X_SPAWN = -80.0         # start point on the feeder rail (off-screen left)
X_DESPAWN = 80.0        # end point on the exit rail (off-screen right)
BLEND = 2.0             # track units over which the marble's offset from the surface turns at the rail joints
SCREEN_MARGIN = 90      # px: marbles further off-screen than this are not drawn
CYCLES = (-3, -2, -1, 0)
# ================================================================= END SETTINGS

OFFSETS = np.concatenate([[0.0], np.cumsum(GAPS)[:-1]])
S_START = X_SPAWN / math.cos(S.FEED_BETA)
S_END = S.L_HELIX + X_DESPAWN / math.cos(S.EXIT_BETA)


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


N_FEED = _unit([math.tan(S.FEED_BETA), 1.0, 0.0])
N_EXIT = _unit([math.tan(S.EXIT_BETA), 1.0, 0.0])


def _smooth(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def surface_point(s):
    if s < 0:
        x = s * math.cos(S.FEED_BETA)
        return np.array([x, S.Y_S - x * math.tan(S.FEED_BETA), -S.RC])
    if s <= S.L_HELIX:
        th = S.theta_of_s(s)
        return np.array([S.RC * math.cos(th), S.y_top(th), S.RC * math.sin(th)])
    x = (s - S.L_HELIX) * math.cos(S.EXIT_BETA)
    return np.array([x, S.Y_END - x * math.tan(S.EXIT_BETA), -S.RC])


def center(s):
    """Marble center at track position s (s < 0 feeder, 0..L_HELIX helix, beyond that the exit rail)."""
    nh = S.surf_normal(S.theta_of_s(min(max(s, 0.0), S.L_HELIX)))
    w_in = _smooth((s + BLEND) / (2 * BLEND))
    w_out = _smooth((s - S.L_HELIX + BLEND) / (2 * BLEND))
    n = N_FEED * (1 - w_in) + nh * w_in
    n = n * (1 - w_out) + N_EXIT * w_out
    return surface_point(s) + S.R * _unit(n)


def instances():
    out = []
    for c in CYCLES:
        for j, o in enumerate(OFFSETS):
            out.append(dict(slot=j, cycle=c, t0=c * LOOP_S + float(o), color=MARBLE_SRGB[j % len(MARBLE_SRGB)]))
    return out


def on_screen(p):
    x, y, z = S.project(p)
    m = SCREEN_MARGIN
    return z > 0 and -m <= x <= S.W + m and -m <= y <= S.H + m


def build(outdir):
    n_frames = int(round(LOOP_S * S.FPS))
    inst = instances()
    nm = len(inst)
    pos = np.zeros((n_frames, nm, 3), np.float32)
    vis = np.zeros((n_frames, nm), bool)
    for f in range(n_frames):
        t = f / S.FPS
        for i, m in enumerate(inst):
            s = S_START + SPEED * (t - m["t0"])
            if not (S_START <= s <= S_END):
                continue
            p = center(s)
            pos[f, i] = p
            vis[f, i] = on_screen(p)
    glows = []
    for k in range(S.N_SEG):
        ev, hold = [], []
        for m in inst:
            te = m["t0"] + (k * S.L_SEG - S_START) / SPEED
            tx = te + S.L_SEG / SPEED
            if tx < -4.0 or te > LOOP_S + 1.0:
                continue
            ev.append(round(te, 5))
            hold.append((round(te, 5), round(tx, 5)))
        glows.append(dict(seg=k, events=sorted(ev), hold=sorted(hold)))
    data = dict(fps=S.FPS, n_frames=n_frames, loop_s=LOOP_S, speed=SPEED, colors=[m["color"] for m in inst],
                instances=inst, glows=glows)
    os.makedirs(outdir, exist_ok=True)
    np.savez_compressed(os.path.join(outdir, "marbles.npz"), pos=pos, vis=vis)
    with open(os.path.join(outdir, "timeline.json"), "w") as fh:
        json.dump(data, fh)
    return data, pos, vis


def loop_check(pos, vis):
    """Max distance between the set of visible marbles at frame 0 and the frame after the last (one loop later)."""
    t = LOOP_S
    inst = instances()
    after = []
    for m in inst:
        s = S_START + SPEED * (t - m["t0"])
        if S_START <= s <= S_END:
            p = center(s)
            if on_screen(p):
                after.append((tuple(m["color"]), p))
    first = [(tuple(inst[i]["color"]), pos[0, i]) for i in np.nonzero(vis[0])[0]]
    if len(first) != len(after):
        return float("inf")
    worst = 0.0
    for col, p in first:
        d = min((np.linalg.norm(p - q) for c2, q in after if c2 == col), default=float("inf"))
        worst = max(worst, d)
    return worst
