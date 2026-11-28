"""Physics of the peg board (numba, in the board's plane): marbles drop from the hopper, bounce off the diamond pegs,
the rails and each other, and pile up in the bins. Soft contacts (spring and damper, per unit mass) at SIM_HZ;
positions are recorded at REC_HZ, plus every peg hit (for the flashes and notes) and every landing and knock in
the bins (for the counters and the sound).

    python3 sim.py              -> build/sim_seed<SEED>.npz and the final count per bin
    python3 sim.py --search 1-60  ranks seeds for a close finish
"""
import math
import os
import sys

import numba as nb
import numpy as np

import settings as C
import scene as S

EV_MAX = 200000


def geometry():
    pegs = np.array([(x, y) for x, y, _ in S.PEGS], np.float64)
    walls = []                                            # axis-aligned rectangles: x0, y0, x1, y1
    t = C.WALL_T
    xo = S.HALF + t / 2
    walls.append((-xo, C.BIN_FLOOR_Y - 1.0, -xo + t, S.TOP_Y))
    walls.append((xo - t, C.BIN_FLOOR_Y - 1.0, xo, S.TOP_Y))
    walls.append((-xo, C.BIN_FLOOR_Y - 1.0, xo, C.BIN_FLOOR_Y))
    for x in S.WALL_X[1:-1]:
        walls.append((x - t / 2, C.BIN_FLOOR_Y, x + t / 2, S.BIN_TOP))
    return pegs, np.array(walls, np.float64)


@nb.njit(cache=True)
def _run(spawn_t, spawn_x, mouth_y, v0, pegs, peg_half, walls, wall_x, bin_top, floor_y, g, k, zp, zw, zb, drag,
         hz, rec_hz, t_max):
    n = len(spawn_t)
    npg = len(pegs)
    nw = len(walls)
    dt = 1.0 / hz
    rec_every = int(hz / rec_hz)
    nsteps = int(t_max * hz)
    nrec = nsteps // rec_every + 1
    x = np.zeros((n, 2)); v = np.zeros((n, 2))
    act = np.zeros(n, np.int64)
    in_bin = np.full(n, -1, np.int64)
    touch = np.zeros((n, npg), np.int64)
    touch_w = np.zeros((n, nw), np.int64)
    touch_b = np.zeros((n, n), np.int64)
    rec = np.zeros((nrec, n, 2), np.float32)
    rec_act = np.zeros((nrec, n), np.int8)
    ev = np.zeros((EV_MAX, 6), np.float64)                 # t, kind (0 peg, 1 land, 2 knock), a, b, speed, x
    nev = 0
    cp = 2.0 * zp * math.sqrt(k); cw = 2.0 * zw * math.sqrt(k); cb = 2.0 * zb * math.sqrt(k)
    c45 = math.sqrt(0.5)
    a = np.zeros((n, 2))
    calm = 0.0
    ri = 0
    last_step = nsteps
    for it in range(nsteps):
        t = it * dt
        for i in range(n):
            if act[i] == 0 and t >= spawn_t[i]:
                act[i] = 1
                x[i, 0] = spawn_x[i]; x[i, 1] = mouth_y - 0.25
                v[i, 0] = 0.0; v[i, 1] = -v0
        for i in range(n):
            a[i, 0] = 0.0; a[i, 1] = -g
        for i in range(n):
            if act[i] == 0:
                continue
            a[i, 0] -= drag * v[i, 0]; a[i, 1] -= drag * v[i, 1]
            for p in range(npg):                          # diamond pegs: a square turned 45 degrees
                dx = x[i, 0] - pegs[p, 0]; dy = x[i, 1] - pegs[p, 1]
                if dx * dx + dy * dy > 9.0:
                    touch[i, p] = 0
                    continue
                lx = c45 * (dx + dy); ly = c45 * (dy - dx)
                qx = min(max(lx, -peg_half), peg_half); qy = min(max(ly, -peg_half), peg_half)
                ex = lx - qx; ey = ly - qy
                d = math.sqrt(ex * ex + ey * ey)
                if d < 1.0 and d > 1e-9:
                    nx_l = ex / d; ny_l = ey / d
                    nx = c45 * (nx_l - ny_l); ny = c45 * (nx_l + ny_l)
                    vn = v[i, 0] * nx + v[i, 1] * ny
                    f = k * (1.0 - d) - cp * vn
                    if f > 0:
                        a[i, 0] += f * nx; a[i, 1] += f * ny
                    vt = -v[i, 0] * ny + v[i, 1] * nx
                    a[i, 0] -= 0.8 * vt * (-ny) * 6.0; a[i, 1] -= 0.8 * vt * nx * 6.0
                    if touch[i, p] == 0 and nev < EV_MAX:
                        ev[nev, 0] = t; ev[nev, 1] = 0; ev[nev, 2] = p; ev[nev, 3] = i; ev[nev, 4] = -vn
                        ev[nev, 5] = pegs[p, 0]
                        nev += 1
                    touch[i, p] = 1
                elif d >= 1.2:
                    touch[i, p] = 0
            for w in range(nw):
                qx = min(max(x[i, 0], walls[w, 0]), walls[w, 2]); qy = min(max(x[i, 1], walls[w, 1]), walls[w, 3])
                ex = x[i, 0] - qx; ey = x[i, 1] - qy
                d = math.sqrt(ex * ex + ey * ey)
                if d < 1.0 and d > 1e-9:
                    nx = ex / d; ny = ey / d
                    vn = v[i, 0] * nx + v[i, 1] * ny
                    f = k * (1.0 - d) - cw * vn
                    if f > 0:
                        a[i, 0] += f * nx; a[i, 1] += f * ny
                    vt = -v[i, 0] * ny + v[i, 1] * nx
                    a[i, 0] -= vt * (-ny) * 8.0; a[i, 1] -= vt * nx * 8.0
                    if touch_w[i, w] == 0 and -vn > 4.0 and x[i, 1] < bin_top and nev < EV_MAX:
                        ev[nev, 0] = t; ev[nev, 1] = 2; ev[nev, 2] = 0; ev[nev, 3] = i; ev[nev, 4] = -vn
                        ev[nev, 5] = x[i, 0]
                        nev += 1
                    touch_w[i, w] = 1
                elif d >= 1.1:
                    touch_w[i, w] = 0
            for j in range(i + 1, n):
                if act[j] == 0:
                    continue
                dx = x[j, 0] - x[i, 0]; dy = x[j, 1] - x[i, 1]
                d2 = dx * dx + dy * dy
                if d2 >= 4.0 or d2 < 1e-12:
                    if d2 >= 4.8:
                        touch_b[i, j] = 0
                    continue
                d = math.sqrt(d2)
                nx = dx / d; ny = dy / d
                vn = (v[j, 0] - v[i, 0]) * nx + (v[j, 1] - v[i, 1]) * ny
                f = k * (2.0 - d) - cb * vn
                if f > 0:
                    a[i, 0] -= f * nx; a[i, 1] -= f * ny
                    a[j, 0] += f * nx; a[j, 1] += f * ny
                vtx = (v[j, 0] - v[i, 0]) - vn * nx; vty = (v[j, 1] - v[i, 1]) - vn * ny
                a[i, 0] += 3.0 * vtx; a[i, 1] += 3.0 * vty
                a[j, 0] -= 3.0 * vtx; a[j, 1] -= 3.0 * vty
                if touch_b[i, j] == 0 and -vn > 5.0 and x[i, 1] < bin_top and nev < EV_MAX:
                    ev[nev, 0] = t; ev[nev, 1] = 2; ev[nev, 2] = 1; ev[nev, 3] = i; ev[nev, 4] = -vn
                    ev[nev, 5] = x[i, 0]
                    nev += 1
                touch_b[i, j] = 1
        vmax = 0.0
        for i in range(n):
            if act[i] == 0:
                continue
            v[i, 0] += a[i, 0] * dt; v[i, 1] += a[i, 1] * dt
            x[i, 0] += v[i, 0] * dt; x[i, 1] += v[i, 1] * dt
            sp = abs(v[i, 0]) + abs(v[i, 1])
            if sp > vmax:
                vmax = sp
            if in_bin[i] < 0 and x[i, 1] < bin_top - 1.0:
                b = 0
                while b < len(wall_x) - 2 and x[i, 0] > wall_x[b + 1]:
                    b += 1
                in_bin[i] = b
                if nev < EV_MAX:
                    ev[nev, 0] = t; ev[nev, 1] = 1; ev[nev, 2] = b; ev[nev, 3] = i; ev[nev, 4] = -v[i, 1]
                    ev[nev, 5] = x[i, 0]
                    nev += 1
        if it % rec_every == 0:
            for i in range(n):
                rec[ri, i, 0] = x[i, 0]; rec[ri, i, 1] = x[i, 1]; rec_act[ri, i] = act[i]
            ri += 1
        if t > spawn_t[n - 1] and vmax < 1.0:
            calm += dt
            if calm > 1.0:
                last_step = it
                break
        else:
            calm = 0.0
    return rec[:ri], rec_act[:ri], ev[:nev], in_bin, last_step * dt


def spawns(seed):
    rng = np.random.default_rng(seed)
    t = C.T_FIRST + np.arange(C.N) / C.RATE
    xs = rng.uniform(-C.SPAWN_JITTER, C.SPAWN_JITTER, C.N)
    return t, xs


def sim_path(seed=None):
    return os.path.join(C.BUILD, "sim_seed%d.npz" % (C.SEED if seed is None else seed))


def run(seed=None, save=True):
    seed = C.SEED if seed is None else seed
    pegs, walls = geometry()
    st, sx = spawns(seed)
    rec, ract, ev, in_bin, t_end = _run(st, sx, S.MOUTH_Y, C.SPAWN_V, pegs, C.PEG_HALF, walls,
                                        np.array(S.WALL_X, np.float64), S.BIN_TOP, C.BIN_FLOOR_Y, C.G, C.K_CONTACT,
                                        C.ZETA_PEG, C.ZETA_WALL, C.ZETA_BALL, C.DRAG, C.SIM_HZ, C.REC_HZ, C.T_SIM)
    counts = np.bincount(in_bin[in_bin >= 0], minlength=C.BINS)
    if save:
        os.makedirs(C.BUILD, exist_ok=True)
        np.savez_compressed(sim_path(seed), rec=rec, act=ract, ev=ev, in_bin=in_bin, t_end=t_end, rec_hz=C.REC_HZ,
                            spawn_t=st)
    return rec, ract, ev, in_bin, t_end, counts


def lead_story(ev):
    """Counts over time from the landing events: the final counts, the winner's margin, and the last time the
    lead changed (or was tied)."""
    land = ev[ev[:, 1] == 1]
    land = land[np.argsort(land[:, 0])]
    c = np.zeros(C.BINS, int)
    last_change, leader = 0.0, -1
    for t, _, b, *_ in land:
        c[int(b)] += 1
        top = np.flatnonzero(c == c.max())
        if len(top) > 1:
            last_change = t
            leader = -1
        elif top[0] != leader:
            leader = int(top[0])
            last_change = t
    s = np.sort(c)
    return c, int(s[-1] - s[-2]), last_change, int(np.argmax(c))


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--search":
        a, _, b = sys.argv[2].partition("-")
        rows = []
        for seed in range(int(a), int(b or a) + 1):
            rec, ract, ev, in_bin, t_end, counts = run(seed, save=False)
            c, margin, last, win = lead_story(ev)
            ok = (in_bin >= 0).all()
            rows.append((margin != 1 or not ok, -last, seed, c.tolist(), margin, last, win + 1, t_end))
        print("  seed  counts                       margin  last lead change  winner  done")
        for r in sorted(rows):
            print("  %4d  %-28s  %5d  %15.2f  %6d  %5.1f" % (r[2], r[3], r[4], r[5], r[6], r[7]))
    else:
        rec, ract, ev, in_bin, t_end, counts = run()
        c, margin, last, win = lead_story(ev)
        print("seed", C.SEED, "counts", counts.tolist(), "winner bin", win + 1, "margin", margin,
              "last lead change %.2f s" % last, "ends %.2f s" % t_end, "events", len(ev),
              "not in a bin", int((in_bin < 0).sum()))
