"""Where every marble is in every frame: the queue on the rail, the run through the grooves and holes, the roll out
of the front face, and the picture on the mat (pile.py).

All marbles follow the same position-vs-time curve along the run, just shifted by 1/RATE seconds each, so they keep
their spacing: packed in the queue (2 radii apart), spread out once they speed up in the first U-turn.

    build(outdir) -> timeline dict (also timeline.json) and marbles.npz: pos (frames, n, 3), vis (frames, n),
                     s (frames, n) arc length along the run (nan on the mat), mat (frames, n) bool
"""
import json
import math
import os

import numpy as np

import settings as C
import layout as LY
import pile

V_QUEUE = 2 * C.R * C.RATE


def speed_profile(pts, s, tags):
    """Rolling speed at every path point (drops are timed separately)."""
    v = np.full(len(s), C.V_TRACK)
    ramp = (V_QUEUE + C.V_TRACK) / 2 * C.ACCEL_S
    u = np.clip(s / ramp, 0, 1)
    v = V_QUEUE + (v - V_QUEUE) * u * u * (3 - 2 * u)
    on_wave = (pts[:, 2] > LY.zb(1)) & (pts[:, 2] < LY.zf(1)) & (pts[:, 0] > LY.xr(0)) & (pts[:, 0] < LY.xl(C.NCOL - 1))
    depth = (LY.Y1 - LY.DROP - pts[:, 1]) / (2 * C.WAVE_A)
    v = np.where(on_wave & (tags == "roll"), v * (1 + C.WAVE_DV * (2 * np.clip(depth, 0, 1) - 1)), v)
    return v


def time_along(pts, s, tags):
    """tau(s): seconds since entering the first U-turn, for every path point."""
    v = speed_profile(pts, s, tags)
    tau = np.zeros(len(s))
    i = 1
    drop_events = []
    while i < len(s):
        if tags[i] == "drop":
            j = i
            while j < len(s) and tags[j] == "drop":
                j += 1
            s0 = s[i - 1]
            seg = s[i - 1:j] - s0
            tau[i - 1:j] = tau[i - 1] + np.sqrt(2 * seg / C.G_DROP)
            drop_events.append((float(tau[j - 1]), float(seg[-1]), pts[j - 1].tolist()))
            i = j
            continue
        ds = s[i] - s[i - 1]
        tau[i] = tau[i - 1] + ds / (0.5 * (v[i] + v[i - 1]))
        i += 1
    return tau, v, drop_events


def build(outdir, log=print):
    os.makedirs(outdir, exist_ok=True)
    pts, s, tags = LY.marble_path()
    tau, v, drops = time_along(pts, s, tags)
    tau_end = tau[-1]
    _, cols, names, _ = pile.picture(pile.n_marbles())
    n = len(cols)
    t_start = C.T_FIRST + np.arange(n) / C.RATE
    t_exit = t_start + tau_end
    # roll out of the tunnel at track speed, braking over the last 1.5 radii to the heart's notch
    brake = 1.5
    run = C.CUSP_Z - brake
    t_run = run / C.V_TRACK
    t_brake = 2 * brake / C.V_TRACK
    t_arrive = t_exit + t_run + t_brake
    t_last = t_arrive[-1] + 3 * C.PUSH_S
    n_frames = int(math.ceil((t_last + C.HOLD_S) * C.FPS))
    ft = np.arange(n_frames) / C.FPS

    pile_xz, fin, slot = pile.simulate(t_arrive, t_exit, ft, (C.V_TRACK, t_run, t_brake, run), log=log)
    if C.REGION_COLOURS:   # each marble wears the colour of the spot it settles on
        cols, names = [cols[k] for k in slot], [names[k] for k in slot]
    pos = np.full((n_frames, n, 3), np.nan)
    vis = np.zeros((n_frames, n), bool)
    sarr = np.full((n_frames, n), np.nan)
    onmat = np.zeros((n_frames, n), bool)
    hid_path = LY.covered(pts)
    for f, t in enumerate(ft):
        tq = t - t_start
        q = tq < 0
        if q.any():
            sq = V_QUEUE * tq[q]
            pos[f, q] = LY.rail_point(sq)
            sarr[f, q] = sq
            vis[f, q] = pos[f, q, 0] < 24.0
        on = (tq >= 0) & (tq < tau_end)
        if on.any():
            ss = np.interp(tq[on], tau, s)
            for k in range(3):
                pos[f, on, k] = np.interp(ss, s, pts[:, k])
            sarr[f, on] = ss
            vis[f, on] = ~np.interp(ss, s, hid_path.astype(float)).round().astype(bool)
        m = tq >= tau_end
        if m.any():
            p2 = pile_xz[f, m]
            pos[f, m, 0] = p2[:, 0]
            pos[f, m, 1] = LY.MAT_Y
            pos[f, m, 2] = p2[:, 1]
            onmat[f, m] = True
            vis[f, m] = p2[:, 1] > -1.15
    # events for the soundtrack
    ev = dict(drops=[], exits=[], arrivals=[], u_entries=[])
    for i in range(n):
        for (td, h, p) in drops:
            ev["drops"].append(dict(t=float(t_start[i] + td), h=h, x=p[0]))
        ev["exits"].append(float(t_exit[i]))
        ev["arrivals"].append(float(t_arrive[i]))
    tl = dict(fps=C.FPS, n_frames=n_frames, n=n, colors=[list(c) for c in cols], names=names,
              t_start=t_start.tolist(), t_exit=t_exit.tolist(), t_arrive=t_arrive.tolist(), tau_end=float(tau_end),
              t_done=float(t_last), path_len=float(s[-1]), events=ev, v_queue=V_QUEUE)
    with open(os.path.join(outdir, "timeline.json"), "w") as fh:
        json.dump(tl, fh)
    np.savez_compressed(os.path.join(outdir, "marbles.npz"), pos=pos.astype(np.float32), vis=vis,
                        s=sarr.astype(np.float32), mat=onmat, fin=fin)
    log(f"timeline: {n_frames} frames ({n_frames / C.FPS:.2f} s), {n} marbles, run {s[-1]:.0f} radii in "
        f"{tau_end:.2f} s, last marble settles at {t_last:.2f} s")
    return tl
