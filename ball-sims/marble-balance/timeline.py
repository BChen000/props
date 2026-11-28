"""From the physics recording to video frames: marble positions, the beam angle per frame (rounded to the poses
whose sets get rendered), the counters, and the cues for text and sound.

The video starts T_LEAD seconds into the physics, with the first steel ball already on the zigzag, and ends HOLD_S
after the decisive tip. Beam angles are rounded finely while the beam is still or slow (0.15 degree, about a pixel
at the baskets) and coarsely while it swings fast (0.6 degree), so a few dozen poses cover the whole video; marbles
in a basket are turned by the same rounding, so they sit exactly in the basket that is drawn.

    build(sim) -> dict(pos, vis, theta, theta_q, n_frames, events, colors, metal, names, ...)
"""
import math

import numpy as np

import settings as C
import sim as SIM


def quantize(th_deg):
    """Per-frame beam angle (degrees) -> rounded pose angle (degrees)."""
    sp = np.abs(np.gradient(th_deg))
    step = np.where(sp < 0.25, 0.15, np.where(sp < 0.7, 0.3, 0.6))
    q = np.round(th_deg / step) * step
    tm = math.degrees(C.THETA_MAX)
    q = np.where(th_deg >= tm - 0.03, tm, np.where(th_deg <= -tm + 0.03, -tm, q))
    return np.round(q, 3) + 0.0                 # no -0.0


def build(simd, log=print):
    hz = simd["hz"]
    team, mass = simd["team"], simd["mass"]
    n = len(team)
    land = simd["land"] - C.T_LEAD
    t_last = float(np.max(land))
    fl = SIM.flips(simd)
    t_tip = next((t for t, s in fl if t >= t_last - 0.05), t_last + 0.5)
    t_end = t_tip + C.HOLD_S
    n_frames = int(round(t_end * C.FPS))
    ft = np.arange(n_frames) / C.FPS
    k = np.clip(np.round((ft + C.T_LEAD) * hz).astype(int), 0, len(simd["RX"]) - 1)
    pos = simd["RX"][k].astype(np.float64)
    vis = simd["RA"][k].astype(bool)
    th = simd["RT"][k, 0]
    th_deg = np.degrees(th)
    th_q = quantize(th_deg)
    # marbles in a basket turn with the drawn (rounded) basket
    P = np.array(C.PIVOT)
    dq = np.radians(th_q) - th
    for f in range(n_frames):
        inb = vis[f] & (land <= ft[f])
        if not inb.any() or abs(dq[f]) < 1e-9:
            continue
        c, s = math.cos(dq[f]), math.sin(dq[f])
        d = pos[f, inb, :2] - P[:2]
        pos[f, inb, 0] = P[0] + c * d[:, 0] - s * d[:, 1]
        pos[f, inb, 1] = P[1] + s * d[:, 0] + c * d[:, 1]
    # cues
    ev = []
    nl = nr = 0
    order = np.argsort(land)
    for i in order:
        if team[i] < 0:
            nl += 1
            ev.append((float(land[i]), "land", ("L", int(i), nl)))
        else:
            nr += 1
            ev.append((float(land[i]), "land", ("R", int(i), nr)))
    for j, (t, s) in enumerate(fl):
        ev.append((float(t), "flip", s))
    # near tips: a steel ball knocks the beam a good way up without tipping it
    tm = math.degrees(C.THETA_MAX)
    for i in order:
        if team[i] < 0 or land[i] >= t_last - 0.01:
            continue
        a, b = int((land[i]) * C.FPS), int((land[i] + 1.0) * C.FPS)
        seg = th_deg[a:min(b, n_frames)]
        if len(seg) and seg[0] > tm - 0.5 and seg.min() > 0 and tm - seg.min() > 1.2:
            ev.append((float(land[i]) + 0.15, "close", float(tm - seg.min())))
    t_all = float(max(land[team < 0]))
    ev.append((t_all + 0.3, "all_left", None))
    steel = np.sort(land[team > 0])
    t_one = min(float(steel[-2]) + 1.25, float(steel[-1]) - 0.6)     # after the second-last ball's SO CLOSE
    ev.append((t_one, "last_one", None))
    ev.append((float(t_tip), "winner", "R" if th[-1] < 0 else "L"))
    # stop knocks and impacts for the sound
    for row in simd["ev"]:
        t, kind, sp, x, y, who = (float(v) for v in row)
        t -= C.T_LEAD
        if 0 <= t <= t_end:
            ev.append((t, {0: "clack", 1: "wood", 2: "basket", 3: "stand", 9: "stop"}.get(int(kind), "wood"),
                       (sp, x, y, int(who))))
    ev.sort(key=lambda e: e[0])
    names = [C.LEFT["name"]] * int((team < 0).sum()) + [C.RIGHT["name"]] * int((team > 0).sum())
    colors = [C.LEFT["srgb"] if s < 0 else C.RIGHT["srgb"] for s in team]
    metal = [bool(C.LEFT["metal"] if s < 0 else C.RIGHT["metal"]) for s in team]
    poses = sorted(set(th_q.tolist()))
    log(f"timeline: {n_frames} frames ({n_frames / C.FPS:.2f} s); flips at "
        f"{', '.join(f'{t:.2f}{s}' for t, s in fl)}; {len(poses)} beam poses")
    return dict(pos=pos, vis=vis, theta=th_deg, theta_q=th_q, poses=poses, n_frames=n_frames, events=ev,
                land=land, team=team, mass=mass, colors=colors, metal=metal, names=names, t_tip=float(t_tip),
                winner="R" if th[-1] < 0 else "L")
