"""Choreography of the staircase: when each marble leaves the chute, its hops (one tile per beat), and the tray.

On the stairs the motion is exact and kinematic (a parabola per beat, so every landing is on the beat). After the
last tile each marble is handed to a small rigid-body sim of the tray (dt 1/1200 s): floor, walls, marble-marble
collisions with restitution and rolling friction. The sim also logs impacts, which become clack sounds.

build(song, outdir) writes outdir/timeline.json (hits, impacts, titles, finale) and outdir/marbles.npz (pos, vis).
"""
import json
import math
import os

import numpy as np

import scene as S

# ===================================================================== SETTINGS (shipped values)
T0_BEATS = 2            # first marble lands on tile 0 after 2 beats
TAIL_BEATS = 4.5        # video keeps running 4.5 beats after the finale chord
HANDOFF = 0.80          # marble leaves the kinematic path 0.8 beat after its last tile hit
E_FLOOR, E_WALL, E_BALL = 0.30, 0.45, 0.62
A_ROLL = 2.4            # rolling deceleration on the tray floor
SIM_DT = 1.0 / 1200.0

MARBLE_SRGB = [
    (246, 246, 246),
    (88, 196, 250), (255, 122, 98),
    (255, 112, 190), (92, 228, 168), (255, 206, 64),
    (172, 128, 255), (255, 150, 52), (64, 222, 232), (240, 84, 124), (172, 230, 76),
    (74, 132, 255), (255, 176, 136), (204, 96, 232), (64, 204, 112), (242, 194, 44), (236, 70, 70),
    (120, 236, 255), (255, 120, 220),
]
VZ = [0.0,
      0.30, -0.36,
      -0.48, 0.10, 0.44,
      0.52, -0.22, 0.26, -0.54, 0.02,
      -0.40, 0.46, -0.12, 0.34, -0.52, 0.18, 0.54, -0.28]
# ================================================================= END SETTINGS


def entries(offsets):
    out = []
    b = 0
    for r, offs in enumerate(offsets):
        for o in offs:
            out.append((r, b + o))
        b = b + offs[-1] + S.T
    return out


def beat_time(b):
    return T0_BEATS * S.TAU + b * S.TAU


def kinematic(m_beat, vz, t):
    th = S.CHUTE_THETA
    t0 = beat_time(m_beat)
    t_exit = t0 - S.CH_TF
    if t < t_exit:
        s = (t_exit - t) * S.VX / math.cos(th)
        p = S.CH_EXIT - s * S.CH_U
        return np.array([p[0], p[1], 0.0]), np.array([S.VX, -S.VX * math.tan(th), 0.0]), "chute"
    if t < t0:
        dt = t - t_exit
        return (np.array([S.CH_EXIT[0] + S.VX * dt, S.CH_EXIT[1] - S.VX * math.tan(th) * dt - 0.5 * S.G * dt * dt, 0.0]),
                np.array([S.VX, -S.VX * math.tan(th) - S.G * dt, 0.0]), "fall")
    k = int(math.floor((t - t0) / S.TAU))
    k = min(k, S.T - 1)
    tk = t0 + k * S.TAU
    dt = t - tk
    x = k * S.DX + S.VX * dt
    y = (S.Y0 - k * S.DY) + S.R + S.V_UP * dt - 0.5 * S.G * dt * dt
    z = vz * (t - t0)
    return np.array([x, y, z]), np.array([S.VX, S.V_UP - S.G * dt, vz]), f"hop{k}"


def simulate(ent, vz, n_frames):
    nm = len(ent)
    x_in0, x_in1 = S.TRAY_IN_X
    z_in0, z_in1 = S.TRAY_IN_Z
    fy = S.TRAY_FLOOR + S.R
    handoff = [beat_time(b + S.T - 1) + HANDOFF * S.TAU for (_, b) in ent]
    pos = np.zeros((nm, 3))
    vel = np.zeros((nm, 3))
    active = np.zeros(nm, bool)
    frames = np.zeros((n_frames, nm, 3), np.float32)
    vis = np.zeros((n_frames, nm), bool)
    impacts = []
    dt = SIM_DT
    e_floor, e_wall, e_ball = E_FLOOR, E_WALL, E_BALL
    a_roll = A_ROLL
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
                    p, v, _ = kinematic(ent[m][1], vz[m], t)
                    pos[m] = p
                    vel[m] = v
                    active[m] = True
            idx = np.where(active)[0]
            if len(idx) == 0:
                continue
            vel[idx, 1] -= S.G * dt
            pos[idx] += vel[idx] * dt
            for m in idx:
                p = pos[m]
                v = vel[m]
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
                        nv = max(0.0, vh - a_roll * dt) * (1 - 0.15 * dt)
                        v[0] *= nv / vh
                        v[2] *= nv / vh
                    if vh < 0.04:
                        v[0] = v[2] = 0.0
                if p[1] < S.TRAY_TOP + S.R * 0.9:
                    if p[0] < x_in0 + S.R:
                        p[0] = x_in0 + S.R
                        if v[0] < 0:
                            imp(t, "wall", -v[0], p, ("w", m))
                            v[0] = -e_wall * v[0]
                    if p[0] > x_in1 - S.R:
                        p[0] = x_in1 - S.R
                        if v[0] > 0:
                            imp(t, "wall", v[0], p, ("w", m))
                            v[0] = -e_wall * v[0]
                    if p[2] < z_in0 + S.R:
                        p[2] = z_in0 + S.R
                        if v[2] < 0:
                            imp(t, "wall", -v[2], p, ("w", m))
                            v[2] = -e_wall * v[2]
                    if p[2] > z_in1 - S.R:
                        p[2] = z_in1 - S.R
                        if v[2] > 0:
                            imp(t, "wall", v[2], p, ("w", m))
                            v[2] = -e_wall * v[2]
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
                        dd = np.linalg.norm(dv)
                        if dd < 1e-9:
                            dv = np.array([1e-3, 0, 0])
                            dd = 1e-3
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
                            if vel[m][1] < 0:
                                vel[m][1] = 0.0
        for m in range(nm):
            if active[m]:
                frames[f, m] = pos[m]
                vis[f, m] = True
            else:
                p, v, ph = kinematic(ent[m][1], vz[m], tf)
                frames[f, m] = p
                vis[f, m] = p[0] > -60
    return frames, vis, impacts


def build(song, outdir):
    rounds, offsets = song["rounds"], song["offsets"]
    ent = entries(offsets)
    nm = len(ent)
    k = song.get("marble_shift", 0) % len(MARBLE_SRGB)
    pal = MARBLE_SRGB[k:] + MARBLE_SRGB[:k]
    colors = [pal[i % len(pal)] for i in range(nm)]
    vz = [VZ[i % len(VZ)] for i in range(nm)]
    last_beat = ent[-1][1] + S.T
    t_end = beat_time(last_beat) + TAIL_BEATS * S.TAU
    n_frames = int(math.ceil(t_end * S.FPS))
    frames, vis, impacts = simulate(ent, vz, n_frames)
    hits = []
    for m, (r, b) in enumerate(ent):
        for k in range(S.T):
            hits.append(dict(t=beat_time(b + k), beat=b + k, tile=k, marble=m, round=r))
    hits.sort(key=lambda h: (h["t"], -h["tile"]))
    titles = []
    for r, n in enumerate(rounds):
        first = min(b for (rr, b) in ent if rr == r)
        txt = f"{n} MARBLE" + ("" if n == 1 else "S")
        titles.append(dict(t=0.0 if r == 0 else beat_time(first) - 0.5 * S.TAU, text=txt, beat=first))
    finale_t = beat_time(last_beat)
    data = dict(fps=S.FPS, n_frames=n_frames, tau=S.TAU, t0=beat_time(0), entries=ent, hits=hits, impacts=impacts,
                titles=titles, finale_t=finale_t, finale_beat=last_beat, last_beat=last_beat, colors=colors)
    os.makedirs(outdir, exist_ok=True)
    np.savez_compressed(os.path.join(outdir, "marbles.npz"), pos=frames, vis=vis)
    with open(os.path.join(outdir, "timeline.json"), "w") as f:
        json.dump(data, f)
    return data, frames, vis
