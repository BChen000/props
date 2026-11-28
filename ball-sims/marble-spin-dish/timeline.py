"""From the physics recording to video frames: which stretch of the race is shown, at what speed, from which camera,
and the cues for text and sound.

The video starts a few seconds before the first marble drops (everyone already spinning), fast-forwards long quiet
stretches, slows down for the last knock-out, cuts to the close-up camera for it, and cuts back to the whole dish to hold on the
winner still circling the hole.

    build(sim) -> dict(pos (frames, n, 3), vis (frames, n), roll (frames, n), cam (frames,) 'main'/'close', sim_t (frames,),
                       events [(video t, kind, data)], n_frames, order (drop order), winner)
"""
import math
import os
import sys

import numpy as np

import settings as C
import sim as SIM

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "marble-raytrace-kit"))
import look


def close_window(st, pos, vis, last):
    """Frames [a, b) for the close-up of the last knock-out: from at most CLOSE_FROM sim seconds before the drop to at
    most CLOSE_TO after it, but only while every marble still in play stays well inside the close camera's frame
    (marbles can swing wide just before they drop). Empty if the drop itself isn't in frame."""
    cc = C.CAMS["close"]
    cam = look.camera_from(np.array(cc["target"], float), C.CAM_AZ, math.radians(cc["el"]), cc["dist"])
    fov = math.radians(cc["fovy"])

    def inside(f):
        for i in np.nonzero(vis[f])[0]:
            x, y, _ = look.project_with(cam, fov, C.CAM_SHIFT, pos[f, i], C.W, C.H)
            if not (0.09 * C.W < x < 0.91 * C.W and 0.27 * C.H < y < 0.72 * C.H):
                return False
        return True

    fd = int(np.searchsorted(st, last))
    if fd >= len(st) or not inside(fd):
        return fd, fd
    a = fd
    while a > 0 and st[a - 1] >= last - C.CLOSE_FROM and inside(a - 1):
        a -= 1
    b = fd
    while b < len(st) and st[b] <= last + C.CLOSE_TO and inside(b):
        b += 1
    return a, b


def speed_keys(drops):
    """Playback speed (sim seconds per video second) as (sim time, speed) keys."""
    d = drops
    keys = [(d[0] - 4.0, 1.0)]
    for a, b in zip(d[:-2], d[1:-1]):
        if b - a > 4.5:
            keys += [(a + 0.9, 1.0), (a + 1.4, 1.7), (b - 1.6, 1.7), (b - 1.1, 1.0)]
    last = d[-1]
    keys += [(last - 1.15, 1.0), (last - 0.75, C.SLOWMO), (last + 0.45, C.SLOWMO), (last + 0.9, 1.0),
             (last + C.HOLD_S + 2.0, 1.0)]
    return keys


def build(simd, log=print):
    names = [m[0] for m in C.MARBLES]
    n = len(names)
    drain = simd["drain"]
    order = list(np.argsort(np.where(drain < 0, 1e9, drain)))
    drops = np.sort(drain[drain >= 0])[:n - 1]
    winner = order[n - 1]
    keys = speed_keys(drops)
    ks = np.array([k[0] for k in keys])
    kv = np.array([k[1] for k in keys])
    s0 = ks[0]
    s_end = drops[-1] + C.HOLD_S * 1.0 + 0.6
    hz = simd["hz"]
    ss = np.arange(s0, s_end, 1.0 / 600.0)
    sp = np.interp(ss, ks, kv)
    vt = np.concatenate([[0.0], np.cumsum(np.diff(ss) / (0.5 * (sp[1:] + sp[:-1])))])
    n_frames = int(vt[-1] * C.FPS)
    ft = np.arange(n_frames) / C.FPS
    st = np.interp(ft, vt, ss)

    def v_of(s):
        return float(np.interp(s, ss, vt))

    RX, RY, RZ, RS = simd["RX"], simd["RY"], simd["RZ"], simd["RS"]
    tr = np.arange(len(RX)) / hz
    pos = np.zeros((n_frames, n, 3))
    vis = np.zeros((n_frames, n), bool)
    roll = np.zeros((n_frames, n), bool)
    for i in range(n):
        pos[:, i, 0] = np.interp(st, tr, RX[:, i])
        pos[:, i, 1] = np.interp(st, tr, RY[:, i])
        pos[:, i, 2] = np.interp(st, tr, RZ[:, i])
        k = np.clip((st * hz).astype(int), 0, len(RS) - 1)
        vis[:, i] = (RS[k, i] == 1) | (RS[k, i] == 2)
        roll[:, i] = RS[k, i] == 1
    fa, fb = close_window(st, pos, vis, drops[-1])
    cam = np.full(n_frames, "main", dtype="<U8")
    if fb - fa >= 12:
        cam[fa:fb] = "close"
    ev = []
    for rank, i in enumerate(order[:n - 1]):
        ev.append((v_of(drain[i]), "out", names[i]))
    ev.append((v_of(drops[-2]) + 0.9, "final2", None))
    ev.append((v_of(drops[-1]), "winner", names[winner]))
    if fb - fa >= 12:
        ev.append((fa / C.FPS, "cut", "close"))
        ev.append((fb / C.FPS, "back", "main"))
    # a few clear near misses: very close, not just before that marble drops, spaced out, none after the win
    picks = []
    for t, i in SIM.near_misses(simd):
        k = int(t * hz)
        r = math.hypot(RX[k, i], RZ[k, i])
        if r > C.RH + 0.45 or t < s0 + 1.0 or t > drops[-1] - 0.9:
            continue
        if drain[i] >= 0 and drain[i] - t < 1.4:
            continue
        if picks and t - picks[-1][0] < 1.6:
            continue
        picks.append((t, i))
    for t, i in picks[:4]:
        ev.append((v_of(t), "close", (names[i], i)))
    pegs = np.array(C.PEGS)
    for row in simd["ev"]:
        t, sp_, x, kind, z = (float(v) for v in row)
        if s0 <= t <= s_end and kind in (0.0, 1.0):
            ev.append((v_of(t), {0.0: "clack", 1.0: "rim"}[kind], (sp_, x, z)))
        elif s0 <= t <= s_end and kind == 4.0:
            k = int(np.argmin(np.hypot(pegs[:, 0] - x, pegs[:, 1] - z)))
            j = min(len(RX) - 1, int(round(t * hz)))
            i = int(np.argmin(np.where(RS[j] == 1, np.hypot(RX[j] - x, RZ[j] - z), 1e9)))
            ev.append((v_of(t), "peg", (sp_, x, z, k, i)))
    ev.sort(key=lambda e: e[0])
    log(f"timeline: sim {s0:.1f}-{s_end:.1f} s -> {n_frames} frames ({n_frames / C.FPS:.2f} s); out order "
        f"{[names[i] for i in order[:n - 1]]}; winner {names[winner]}; near misses shown {len(picks[:4])}; "
        f"close-up frames {fa}-{fb}")
    return dict(pos=pos, vis=vis, roll=roll, cam=cam, sim_t=st, events=ev, n_frames=n_frames, order=[names[i] for i in order],
                winner=names[winner], colors=[m[1] for m in C.MARBLES], names=names)
