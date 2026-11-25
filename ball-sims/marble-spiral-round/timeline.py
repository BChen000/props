"""Choreography of the spiral round: marbles wait in a queue on the feeder rail, a gate releases each one, it
rolls down the helix at constant speed (one note per segment), and drops into the dish, where a small rigid-body
sim (dt 1/1200 s; floor, rim, pole, marble-marble) takes over and logs impacts for the clack sounds.

Round r has rounds[r] marbles (songs.py) entering CANON_BARS apart, so they sing the song as a round. Rounds are
separated by REST_BARS of silence. build(song, outdir) writes outdir/timeline.json (notes, impacts, titles, finale) and
outdir/marbles.npz (pos, vis).
"""
import json
import math
import os

import numpy as np

import scene as S

# ===================================================================== SETTINGS (shipped values)
BAR = S.BAR_EIGHTHS * S.EIGHTH
CANON_BARS = 2
CANON = CANON_BARS * BAR
SONG_BARS = S.EIGHTHS // S.BAR_EIGHTHS
S1 = 1.8                # first song note at 1.8 s
REST_BARS = 1
T_ACC = 2 * abs(S.GATE_X) / S.VEL
SLOT = 2.08             # queue spacing on the rail
TAIL = 2.6              # seconds after the finale
E_FLOOR, E_WALL, E_BALL = 0.32, 0.45, 0.62

MARBLE_SRGB = [(246, 246, 246), (88, 196, 250), (255, 122, 98), (255, 112, 190), (92, 228, 168), (255, 206, 64),
               (172, 128, 255)]
# ================================================================= END SETTINGS


def song_starts(rounds):
    out = []
    s = S1
    for r, n in enumerate(rounds):
        out.append(s)
        s += (SONG_BARS + (n - 1) * 2 + REST_BARS) * BAR
    return out


def plan(rounds):
    ss = song_starts(rounds)
    marbles = []
    for r, n in enumerate(rounds):
        for k in range(n):
            song0 = ss[r] + k * CANON
            t_in = song0 - S.LEAD_IN / S.VEL
            marbles.append(dict(round=r, k=k, n=n, song0=song0, t_in=t_in, t_rel=t_in - T_ACC,
                                t_arrive=ss[r] - S.LEAD_IN / S.VEL - T_ACC - 0.35,
                                t_rollin=ss[r] - S.LEAD_IN / S.VEL - T_ACC - 0.35 - 1.7))
    return ss, marbles


def rail_center(x):
    tb = math.tan(S.RAIL_BETA)
    y = S.Y_S + (0.0 - x) * tb
    n = np.array([tb, 1.0, 0.0])
    n /= np.linalg.norm(n)
    return np.array([x, y, -S.RC]) + S.R * n


def ease_out(u):
    u = min(max(u, 0.0), 1.0)
    return 1 - (1 - u) ** 3


def ease_io(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def kin(m, all_m, t):
    if t >= m["t_in"]:
        s = (t - m["t_in"]) * S.VEL
        return S.center_on_track(min(s, S.TOTAL)), "track" if s <= S.TOTAL else "off"
    if t >= m["t_rel"]:
        u = (t - m["t_rel"]) / T_ACC
        x = S.GATE_X + (0.0 - S.GATE_X) * u * u
        return rail_center(x), "rail"
    same = [o for o in all_m if o["round"] == m["round"]]
    released_before = sum(1 for o in same if o["k"] < m["k"] and t >= o["t_rel"])
    slot = m["k"] - released_before
    x = S.GATE_X - SLOT * slot
    for o in same:
        if o["k"] < m["k"] and t >= o["t_rel"]:
            pass
    adv = 0.0
    for o in same:
        if o["k"] < m["k"] and o["t_rel"] <= t < o["t_rel"] + 0.55:
            adv = 1 - ease_io((t - o["t_rel"] - 0.08) / 0.42)
    x -= SLOT * adv
    if t < m["t_arrive"]:
        u = (t - m["t_rollin"]) / (m["t_arrive"] - m["t_rollin"])
        x0 = -48.0 - SLOT * m["k"]
        x = x0 + (S.GATE_X - SLOT * m["k"] - x0) * ease_out(u)
        if m["round"] == 0:
            x = S.GATE_X - SLOT * m["k"]
    return rail_center(x), "queue"


def track_vel(s):
    th = S.theta_of_s(s)
    tg = np.array([-math.sin(th) * S.RC, -S.HH, math.cos(th) * S.RC])
    return tg / np.linalg.norm(tg) * S.VEL


def simulate(n_frames, marbles):
    nm = len(marbles)
    t_off = [m["t_in"] + S.TOTAL / S.VEL for m in marbles]
    pos = np.zeros((nm, 3))
    vel = np.zeros((nm, 3))
    active = np.zeros(nm, bool)
    frames = np.zeros((n_frames, nm, 3), np.float32)
    vis = np.zeros((n_frames, nm), bool)
    impacts = []
    last = {}
    dt = 1.0 / 1200
    fy = S.DISH_FLOOR + S.R
    r_out = S.DISH_R - S.DISH_RIM - S.R
    r_in = S.POLE_R + S.R
    e_f, e_w, e_b = E_FLOOR, E_WALL, E_BALL

    def imp(t, kind, spd, p, key):
        if spd < 1.2:
            return
        if key in last and t - last[key] < 0.06:
            return
        last[key] = t
        impacts.append(dict(t=round(t, 5), kind=kind, speed=round(float(spd), 3), x=round(float(p[0]), 3),
                            z=round(float(p[2]), 3)))

    t = 0.0
    for f in range(n_frames):
        tf = f / S.FPS
        while t < tf - 1e-9:
            t += dt
            for i in range(nm):
                if not active[i] and t >= t_off[i]:
                    pos[i] = S.center_on_track(S.TOTAL)
                    vel[i] = track_vel(S.TOTAL)
                    pos[i] += vel[i] * (t - t_off[i])
                    active[i] = True
            idx = np.where(active)[0]
            if len(idx) == 0:
                continue
            vel[idx, 1] -= S.G * dt
            pos[idx] += vel[idx] * dt
            for i in idx:
                p, v = pos[i], vel[i]
                if p[1] < fy:
                    p[1] = fy
                    if v[1] < 0:
                        sp = -v[1]
                        imp(t, "floor", sp, p, ("f", i))
                        v[1] = e_f * sp if sp > 1.0 else 0.0
                on_floor = p[1] <= fy + 1e-3 and abs(v[1]) < 0.5
                rr = math.hypot(p[0], p[2])
                if p[1] < S.DISH_TOP + S.R:
                    if rr > r_out:
                        nx, nz = p[0] / rr, p[2] / rr
                        p[0], p[2] = nx * r_out, nz * r_out
                        vn = v[0] * nx + v[2] * nz
                        if vn > 0:
                            imp(t, "wall", vn, p, ("w", i))
                            v[0] -= (1 + e_w) * vn * nx
                            v[2] -= (1 + e_w) * vn * nz
                        v[0] *= 1 - 0.35 * dt
                        v[2] *= 1 - 0.35 * dt
                    if rr < r_in:
                        nx, nz = p[0] / max(rr, 1e-6), p[2] / max(rr, 1e-6)
                        p[0], p[2] = nx * r_in, nz * r_in
                        vn = v[0] * nx + v[2] * nz
                        if vn < 0:
                            imp(t, "wall", -vn, p, ("p", i))
                            v[0] -= (1 + e_w) * vn * nx
                            v[2] -= (1 + e_w) * vn * nz
                if on_floor:
                    vh = math.hypot(v[0], v[2])
                    if vh > 1e-9:
                        nv = max(0.0, vh - 1.7 * dt) * (1 - 0.12 * dt)
                        v[0] *= nv / vh
                        v[2] *= nv / vh
                    if vh < 0.04:
                        v[0] = v[2] = 0.0
            if len(idx) > 1:
                for _ in range(3):
                    Pp = pos[idx]
                    d = Pp[:, None, :] - Pp[None, :, :]
                    dist = np.sqrt((d ** 2).sum(-1))
                    ii, jj = np.where(np.triu(dist < 2 * S.R - 1e-6, 1))
                    if len(ii) == 0:
                        break
                    for a, b in zip(ii, jj):
                        ma_, mb_ = idx[a], idx[b]
                        dv = pos[ma_] - pos[mb_]
                        dd = max(np.linalg.norm(dv), 1e-6)
                        n = dv / dd
                        pen = 2 * S.R - dd
                        pos[ma_] += n * pen * 0.5
                        pos[mb_] -= n * pen * 0.5
                        rv = np.dot(vel[ma_] - vel[mb_], n)
                        if rv < 0:
                            imp(t, "ball", -rv, 0.5 * (pos[ma_] + pos[mb_]), ("b", min(ma_, mb_), max(ma_, mb_)))
                            j = -(1 + e_b) * rv * 0.5
                            vel[ma_] += j * n
                            vel[mb_] -= j * n
                    for i in idx:
                        if pos[i][1] < fy:
                            pos[i][1] = fy
                            vel[i][1] = max(vel[i][1], 0.0)
        for i, m in enumerate(marbles):
            if active[i]:
                frames[f, i] = pos[i]
                vis[f, i] = True
            else:
                p, ph = kin(m, marbles, tf)
                frames[f, i] = p
                vis[f, i] = (ph != "queue") or tf >= m["t_rollin"] or m["round"] == 0
    return frames, vis, impacts


def build(song, outdir):
    rounds = list(song["rounds"])
    ss, marbles = plan(rounds)
    last = marbles[-1]
    t_end_music = last["song0"] + SONG_BARS * BAR
    finale_t = last["t_in"] + S.TOTAL / S.VEL + 0.30
    t_end = finale_t + TAIL
    n_frames = int(math.ceil(t_end * S.FPS))
    frames, vis, impacts = simulate(n_frames, marbles)
    for imp_ in impacts:
        if imp_["kind"] == "floor" and abs(imp_["t"] - (last["t_in"] + S.TOTAL / S.VEL)) < 0.6:
            finale_t = imp_["t"]
    notes = []
    for i, m in enumerate(marbles):
        for k, (p, d) in enumerate(S.SONG):
            t = m["t_in"] + (S.LEAD_IN + S.STARTS[k] * S.LE) / S.VEL
            dur = d * S.EIGHTH
            notes.append(dict(t=t, dur=dur, pitch=p, seg=k, marble=i, round=m["round"]))
    notes.sort(key=lambda n: n["t"])
    titles = []
    for r, n in enumerate(rounds):
        first = [m for m in marbles if m["round"] == r][0]
        titles.append(dict(t=0.0 if r == 0 else first["t_rel"], text=f"{n} MARBLE" + ("" if n == 1 else "S")))
    colors = [MARBLE_SRGB[i % len(MARBLE_SRGB)] for i in range(len(marbles))]
    data = dict(fps=S.FPS, n_frames=n_frames, notes=notes, impacts=impacts, titles=titles, finale_t=finale_t,
                colors=colors, marbles=marbles, song_starts=ss, t_end_music=t_end_music)
    os.makedirs(outdir, exist_ok=True)
    np.savez_compressed(os.path.join(outdir, "marbles.npz"), pos=frames, vis=vis)
    with open(os.path.join(outdir, "timeline.json"), "w") as f:
        json.dump(data, f)
    return data, frames, vis


