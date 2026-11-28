"""Physics of the marble hourglass (numba, in the board's plane). Before the clock starts, the colours drop into the
top half in small one-colour batches with the neck shut by a gate, so they settle in rainbow patches. At FILL_S the gate
opens and they pour through the neck. Soft contacts (spring and damper, per unit mass) at SIM_HZ against the
oriented rails and each other; positions are recorded at REC_HZ from FILL_S - LEAD_S, plus every marble passing
the neck and every hard knock (for the sound).

    python3 sim.py               -> build/sim_seed<SEED>.npz, the order the colours run out and the winner
    python3 sim.py --search 1-60  ranks seeds by finish_score: outs spread out, then a close duel for the win
"""
import math
import os
import sys

import numba as nb
import numpy as np

import settings as C
import scene as S

EV_MAX = 200000


@nb.njit(cache=True)
def _run(spawn_t, spawn_xy, v0, walls, gate, t_gate, neck_y, g, k, zw, zb, drag, hz, rec_hz, t_rec0, t_max):
    n = len(spawn_t)
    nw = len(walls)
    dt = 1.0 / hz
    rec_every = int(hz / rec_hz)
    nsteps = int(t_max * hz)
    nrec = int((t_max - t_rec0) * rec_hz) + 2
    x = np.zeros((n, 2)); v = np.zeros((n, 2)); a = np.zeros((n, 2))
    act = np.zeros(n, np.int64)
    passed = np.full(n, -1.0)
    rec = np.zeros((nrec, n, 2), np.float32)
    ev = np.zeros((EV_MAX, 5), np.float64)                 # t, kind (0 neck, 1 knock wall, 2 knock marble), marble, speed, x
    nev = 0
    cw = 2.0 * zw * math.sqrt(k); cb = 2.0 * zb * math.sqrt(k)
    touch_w = np.zeros((n, nw + 1), np.int64)
    ri = 0
    calm = 0.0
    t_end = t_max
    cs = np.cos(walls[:, 4]); sn = np.sin(walls[:, 4])
    for it in range(nsteps):
        t = it * dt
        for i in range(n):
            if act[i] == 0 and t >= spawn_t[i]:
                act[i] = 1
                x[i, 0] = spawn_xy[i, 0]; x[i, 1] = spawn_xy[i, 1]
                v[i, 0] = 0.0; v[i, 1] = -v0
        for i in range(n):
            a[i, 0] = -drag * v[i, 0]; a[i, 1] = -g - drag * v[i, 1]
        for i in range(n):
            if act[i] == 0:
                continue
            for w in range(nw + 1):
                if w == nw:
                    if t >= t_gate:
                        continue
                    wx, wy, hx, hy, c, s = gate[0], gate[1], gate[2], gate[3], 1.0, 0.0
                else:
                    wx, wy, hx, hy, c, s = walls[w, 0], walls[w, 1], walls[w, 2], walls[w, 3], cs[w], sn[w]
                dx = x[i, 0] - wx; dy = x[i, 1] - wy
                lx = c * dx + s * dy; ly = -s * dx + c * dy
                if abs(lx) > hx + 1.5 or abs(ly) > hy + 1.5:
                    touch_w[i, w] = 0
                    continue
                qx = min(max(lx, -hx), hx); qy = min(max(ly, -hy), hy)
                ex = lx - qx; ey = ly - qy
                d = math.sqrt(ex * ex + ey * ey)
                if d < 1.0 and d > 1e-9:
                    nlx = ex / d; nly = ey / d
                    nx = c * nlx - s * nly; ny = s * nlx + c * nly
                    vn = v[i, 0] * nx + v[i, 1] * ny
                    f = k * (1.0 - d) - cw * vn
                    if f > 0:
                        a[i, 0] += f * nx; a[i, 1] += f * ny
                    vt = -v[i, 0] * ny + v[i, 1] * nx
                    a[i, 0] -= 3.0 * vt * (-ny); a[i, 1] -= 3.0 * vt * nx
                    if touch_w[i, w] == 0 and -vn > 5.0 and t >= t_rec0 and nev < EV_MAX:
                        ev[nev, 0] = t; ev[nev, 1] = 1; ev[nev, 2] = i; ev[nev, 3] = -vn; ev[nev, 4] = x[i, 0]
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
                    continue
                d = math.sqrt(d2)
                nx = dx / d; ny = dy / d
                vn = (v[j, 0] - v[i, 0]) * nx + (v[j, 1] - v[i, 1]) * ny
                f = k * (2.0 - d) - cb * vn
                if f > 0:
                    a[i, 0] -= f * nx; a[i, 1] -= f * ny
                    a[j, 0] += f * nx; a[j, 1] += f * ny
                vtx = (v[j, 0] - v[i, 0]) - vn * nx; vty = (v[j, 1] - v[i, 1]) - vn * ny
                a[i, 0] += 1.5 * vtx; a[i, 1] += 1.5 * vty
                a[j, 0] -= 1.5 * vtx; a[j, 1] -= 1.5 * vty
                if -vn > 7.0 and t >= t_rec0 and nev < EV_MAX:
                    ev[nev, 0] = t; ev[nev, 1] = 2; ev[nev, 2] = i; ev[nev, 3] = -vn; ev[nev, 4] = x[i, 0]
                    nev += 1
        vmax = 0.0
        for i in range(n):
            if act[i] == 0:
                continue
            v[i, 0] += a[i, 0] * dt; v[i, 1] += a[i, 1] * dt
            x[i, 0] += v[i, 0] * dt; x[i, 1] += v[i, 1] * dt
            sp = abs(v[i, 0]) + abs(v[i, 1])
            if sp > vmax:
                vmax = sp
            if passed[i] < 0 and x[i, 1] < neck_y - 1.2:
                passed[i] = t
                if nev < EV_MAX:
                    ev[nev, 0] = t; ev[nev, 1] = 0; ev[nev, 2] = i; ev[nev, 3] = -v[i, 1]; ev[nev, 4] = x[i, 0]
                    nev += 1
        if t >= t_rec0 and it % rec_every == 0 and ri < nrec:
            for i in range(n):
                rec[ri, i, 0] = x[i, 0]; rec[ri, i, 1] = x[i, 1]
            ri += 1
        done = True
        for i in range(n):
            if passed[i] < 0:
                done = False
                break
        if done and vmax < 1.5:
            calm += dt
            if calm > 1.0:
                t_end = t
                break
        else:
            calm = 0.0
    return rec[:ri], ev[:nev], passed, t_end


def spawns(seed):
    """Before the clock starts (off camera) the marbles pour in one at a time, in batches of BATCH of one colour.
    Each batch drops around its own random spot along the top and the batches come in a random order, so the top
    half fills with rainbow patches like a sand-art bottle and every colour is spread through it: whichever colour
    falls last is a real race, not just the top layer. The seed picks the order and the spots."""
    rng = np.random.default_rng(seed)
    nc = len(C.COLOURS)
    batch_col = rng.permutation(np.repeat(np.arange(nc), C.PER_COLOUR // C.BATCH))
    col = np.repeat(batch_col, C.BATCH)
    n = len(col)
    t = np.arange(n) * C.FILL_STREAM_S
    x = np.repeat(rng.uniform(-C.HALF_W + 3.5, C.HALF_W - 3.5, len(batch_col)), C.BATCH) + rng.uniform(-2.5, 2.5, n)
    xy = np.stack([np.clip(x, -C.HALF_W + 1.2, C.HALF_W - 1.2), np.full(n, C.TOP_Y - 1.6)], 1)
    return t, xy, col


def sim_path(seed=None):
    return os.path.join(C.BUILD, "sim_seed%d.npz" % (C.SEED if seed is None else seed))


def run(seed=None, save=True):
    seed = C.SEED if seed is None else seed
    st, sxy, col = spawns(seed)
    gate = np.array([0.0, C.NECK_Y + 0.3, C.NECK_HALF + 1.2, 0.3])
    t_rec0 = C.FILL_S - C.LEAD_S
    rec, ev, passed, t_end = _run(st, sxy, C.POUR_V, S.walls(), gate, C.FILL_S, C.NECK_Y, C.G, C.K_CONTACT, C.ZETA_WALL,
                                  C.ZETA_BALL, C.DRAG, C.SIM_HZ, C.REC_HZ, t_rec0, C.T_SIM)
    if save:
        os.makedirs(C.BUILD, exist_ok=True)
        np.savez_compressed(sim_path(seed), rec=rec, ev=ev, passed=passed, t_end=t_end, colours=col,
                            t_rec0=t_rec0, rec_hz=C.REC_HZ)
    return rec, ev, passed, t_end, col


def outs(passed, col):
    """(time, colour index) when each colour's last marble passes the neck, in order; the last one is the winner."""
    res = []
    for k in range(len(C.COLOURS)):
        p = passed[col == k]
        res.append((float(p.max()) if (p >= 0).all() else float("inf"), k))
    return sorted(res)


def finish_score(o):
    """Ranks a race: the first colour out early, outs spread at least 0.6 s apart so each gets its moment, a duel
    of the last two colours that lasts 0.8-2.5 s, and the winner's last marble 0.25-1.2 s after the runner-up's."""
    t = [x for x, _ in o]
    if not all(math.isfinite(x) for x in t):
        return -99.0
    g = np.diff(t)
    s = -0.15 * (t[0] - C.FILL_S)
    s -= 2.0 * np.clip(0.6 - g[:-2], 0, None).sum()
    s -= 2.0 * max(0.0, 0.8 - g[-2]) + 0.5 * max(0.0, g[-2] - 2.5)
    s -= 2.0 * max(0.0, 0.25 - g[-1]) + 0.5 * max(0.0, g[-1] - 1.2)
    return float(s)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--search":
        a, _, b = sys.argv[2].partition("-")
        rows = []
        for seed in range(int(a), int(b or a) + 1):
            rec, ev, passed, t_end, col = run(seed, save=False)
            o = outs(passed, col)
            ok = all(math.isfinite(t) for t, _ in o)
            rows.append((-finish_score(o), seed, ok, "".join(C.COLOURS[k][0][0] for _, k in o),
                         [round(t - C.FILL_S, 2) for t, _ in o][:1] + ([round(float(x), 2) for x in np.diff([t for t, _ in o])]
                                                                       if ok else [])))
        print("  seed  ok  order (first out .. winner)  first out, then the gaps between outs (s)   score")
        for r in sorted(rows):
            print("  %4d  %s   %-8s  %-52s %6.2f" % (r[1], "y" if r[2] else "n", r[3], r[4], -r[0]))
    else:
        rec, ev, passed, t_end, col = run()
        o = outs(passed, col)
        print("seed", C.SEED, "out order", [C.COLOURS[k][0] for _, k in o], "times after gate",
              [round(t - C.FILL_S, 2) for t, _ in o], "ends", round(t_end - C.FILL_S, 2), "s after gate",
              "frames recorded", len(rec), "events", len(ev))
