"""Choreography of the twin staircase: marbles drop in from above the top tile of their lane, hop down one tile per
beat (exact parabolas, so every landing is on the beat), then a small rigid-body sim of the tray (dt 1/1200 s;
floor, walls, marble-marble) takes over and logs impacts for the clack sounds.

build(song, outdir) writes outdir/timeline.json (hits, impacts, titles, finale) and outdir/marbles.npz (pos, vis).
"""
import json
import math
import os

import numpy as np

import scene as S

# ===================================================================== SETTINGS (shipped values)
T0 = 1.5                # first marble lands on its top tile at 1.5 s
DROP_T = 0.85           # marbles appear this long before landing on the top tile
DROP_V = 65.0
TAIL_BEATS = 5
HANDOFF = 0.80          # beats after the last tile hit
E_FLOOR, E_WALL, E_BALL = 0.30, 0.45, 0.62
A_ROLL = 2.4

MARBLE_SRGB = [
    (246, 246, 246),
    (88, 196, 250), (255, 122, 98),
    (255, 112, 190), (92, 228, 168), (255, 206, 64), (172, 128, 255),
    (255, 150, 52), (64, 222, 232), (240, 84, 124), (172, 230, 76), (74, 132, 255), (255, 176, 136),
    (204, 96, 232), (242, 194, 44),
]
VZ = [0.0, 0.25, -0.25, -0.3, 0.3, 0.12, -0.12, 0.35, -0.35, -0.2, 0.2, 0.05, -0.05, 0.28, -0.28]
# ================================================================= END SETTINGS


def entries(rounds):
    out = []
    b = 0
    for r, ents in enumerate(rounds):
        for lane, off in ents:
            out.append((r, lane, b + off))
        b = b + max(o for _, o in ents) + S.T
    return out


def beat_time(b):
    return T0 + b * S.TAU


def kinematic(lane, m_beat, vz, t):
    zl = S.LANE_Z[lane]
    t0 = beat_time(m_beat)
    if t < t0:
        tp = t0 - t
        if tp > DROP_T:
            return None, None, "hidden"
        y = S.Y0 + S.R + DROP_V * tp - 0.5 * S.G * tp * tp
        x = -S.VX * tp
        return np.array([x, y, zl]), np.array([S.VX, -(DROP_V - S.G * tp), 0.0]), "drop"
    k = min(int(math.floor((t - t0) / S.TAU)), S.T - 1)
    tk = t0 + k * S.TAU
    dt = t - tk
    x = k * S.DX + S.VX * dt
    y = (S.Y0 - k * S.DY) + S.R + S.V_UP * dt - 0.5 * S.G * dt * dt
    z = zl + vz * (t - t0)
    return np.array([x, y, z]), np.array([S.VX, S.V_UP - S.G * dt, vz]), f"hop{k}"


def simulate(ent, vz, n_frames):
    nm = len(ent)
    x_in0, x_in1 = S.TRAY_IN_X
    z_in0, z_in1 = S.TRAY_IN_Z
    fy = S.TRAY_FLOOR + S.R
    handoff = [beat_time(b + S.T - 1) + HANDOFF * S.TAU for (_, _, b) in ent]
    pos = np.zeros((nm, 3))
    vel = np.zeros((nm, 3))
    active = np.zeros(nm, bool)
    frames = np.zeros((n_frames, nm, 3), np.float32)
    vis = np.zeros((n_frames, nm), bool)
    impacts = []
    dt = 1.0 / 1200.0
    e_floor, e_wall, e_ball = E_FLOOR, E_WALL, E_BALL
    last_imp = {}

    def imp(t, kind, spd, p, key):
        if spd < 1.2:
            return
        if key in last_imp and t - last_imp[key] < 0.06:
            return
        last_imp[key] = t
        impacts.append(dict(t=round(t, 5), kind=kind, speed=round(float(spd), 3), x=round(float(p[0]), 3),
                            z=round(float(p[2]), 3)))

    t = 0.0
    for f in range(n_frames):
        tf = f / S.FPS
        while t < tf - 1e-9:
            t += dt
            for m in range(nm):
                if not active[m] and t >= handoff[m]:
                    p, v, _ = kinematic(ent[m][1], ent[m][2], vz[m], t)
                    pos[m] = p
                    vel[m] = v
                    active[m] = True
            idx = np.where(active)[0]
            if len(idx) == 0:
                continue
            vel[idx, 1] -= S.G * dt
            pos[idx] += vel[idx] * dt
            for m in idx:
                p, v = pos[m], vel[m]
                if p[1] < fy:
                    p[1] = fy
                    if v[1] < 0:
                        s = -v[1]
                        imp(t, "floor", s, p, ("f", m))
                        v[1] = e_floor * s if s > 1.0 else 0.0
                on_floor = p[1] <= fy + 1e-3 and abs(v[1]) < 0.5
                if on_floor:
                    vh = math.hypot(v[0], v[2])
                    if vh > 1e-9:
                        nv = max(0.0, vh - A_ROLL * dt) * (1 - 0.15 * dt)
                        v[0] *= nv / vh
                        v[2] *= nv / vh
                    if vh < 0.04:
                        v[0] = v[2] = 0.0
                if p[1] < S.TRAY_TOP + S.R * 0.9:
                    for ax, lo, hi in ((0, x_in0, x_in1), (2, z_in0, z_in1)):
                        if p[ax] < lo + S.R:
                            p[ax] = lo + S.R
                            if v[ax] < 0:
                                imp(t, "wall", -v[ax], p, ("w", m))
                                v[ax] = -e_wall * v[ax]
                        if p[ax] > hi - S.R:
                            p[ax] = hi - S.R
                            if v[ax] > 0:
                                imp(t, "wall", v[ax], p, ("w", m))
                                v[ax] = -e_wall * v[ax]
            if len(idx) > 1:
                for _ in range(3):
                    P = pos[idx]
                    d = P[:, None, :] - P[None, :, :]
                    dist = np.sqrt((d ** 2).sum(-1))
                    ii, jj = np.where(np.triu(dist < 2 * S.R - 1e-6, 1))
                    if len(ii) == 0:
                        break
                    for a, b in zip(ii, jj):
                        ma, mb = idx[a], idx[b]
                        dv = pos[ma] - pos[mb]
                        dd = max(np.linalg.norm(dv), 1e-6)
                        n = dv / dd
                        pen = 2 * S.R - dd
                        pos[ma] += n * pen * 0.5
                        pos[mb] -= n * pen * 0.5
                        rv = np.dot(vel[ma] - vel[mb], n)
                        if rv < 0:
                            imp(t, "ball", -rv, 0.5 * (pos[ma] + pos[mb]), ("b", min(ma, mb), max(ma, mb)))
                            j = -(1 + e_ball) * rv * 0.5
                            vel[ma] += j * n
                            vel[mb] -= j * n
                    for m in idx:
                        if pos[m][1] < fy:
                            pos[m][1] = fy
                            vel[m][1] = max(vel[m][1], 0.0)
        for m in range(nm):
            if active[m]:
                frames[f, m] = pos[m]
                vis[f, m] = True
            else:
                p, v, ph = kinematic(ent[m][1], ent[m][2], vz[m], tf)
                if p is not None:
                    frames[f, m] = p
                    vis[f, m] = True
    return frames, vis, impacts


def build(song, outdir):
    rounds = song["rounds"]
    ent = entries(rounds)
    vz = [VZ[i % len(VZ)] for i in range(len(ent))]
    last_beat = max(b for (_, _, b) in ent) + S.T
    t_end = beat_time(last_beat) + TAIL_BEATS * S.TAU
    n_frames = int(math.ceil(t_end * S.FPS))
    frames, vis, impacts = simulate(ent, vz, n_frames)
    hits = []
    for m, (r, lane, b) in enumerate(ent):
        for i in range(S.T):
            hits.append(dict(t=beat_time(b + i), beat=b + i, tile=lane * S.T + i, step=i, lane=lane, marble=m,
                             round=r))
    hits.sort(key=lambda h: (h["t"], -h["step"]))
    titles = []
    for r, ents in enumerate(rounds):
        first = min(b for (rr, _, b) in ent if rr == r)
        n = len(ents)
        txt = f"{n} MARBLE" + ("" if n == 1 else "S")
        titles.append(dict(t=0.0 if r == 0 else beat_time(first) - DROP_T, text=txt, beat=first))
    finale_t = beat_time(last_beat) + 0.07 * S.TAU
    for im in impacts:
        if im["kind"] == "floor" and abs(im["t"] - beat_time(last_beat)) < 0.3:
            finale_t = im["t"]
            break
    colors = [MARBLE_SRGB[i % len(MARBLE_SRGB)] for i in range(len(ent))]
    data = dict(fps=S.FPS, n_frames=n_frames, tau=S.TAU, t0=T0, entries=ent, hits=hits, impacts=impacts,
                titles=titles, finale_t=finale_t, last_beat=last_beat, colors=colors)
    os.makedirs(outdir, exist_ok=True)
    np.savez_compressed(os.path.join(outdir, "marbles.npz"), pos=frames, vis=vis)
    with open(os.path.join(outdir, "timeline.json"), "w") as f:
        json.dump(data, f)
    return data, frames, vis


