"""Ring Escape physics: 8 marbles bounce inside spinning rings; the first one through a ring's gap
breaks that ring for everyone, and the first one out of the last ring wins.

Deterministic (numba, fixed step). Billiard-style motion without gravity: marbles keep a constant
speed, bounce elastically off each other and off ring walls (with a small random bounce angle),
and can clip the rounded ends of a gap. After the win the last gap closes so nobody else gets out.

  python sim.py            -> summary of settings.SEED (break times, winner, near misses)
  python sim.py record     -> save the race to assets/race_<SEED>.npz (timeline.py replays it)

Output of run(): positions P[step, marble, xy] and ring angles PHI[step, ring] every DT, plus an
event list ev[n, 8] = (type, step, i, j_or_ring, value, 0, x, y) with types EV_*.
"""
import os
import sys

import numpy as np
from numba import njit

import settings as S

EV_MM, EV_WALL, EV_END, EV_BREAK, EV_WIN, EV_OUT = 0, 1, 2, 3, 4, 5


@njit(cache=True)
def smooth(x):
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    return x * x * (3.0 - 2.0 * x)


@njit(cache=True)
def wrap(a):
    return (a + np.pi) % (2.0 * np.pi) - np.pi


@njit(cache=True)
def simulate(pos0, vel0, phi0, gaps, omega_base, radii, v0, sp_t, sp_om, sp_v,
             t_max, post_win, noise, seed, NM, M_R, HW, DT):
    np.random.seed(seed)
    NR = radii.shape[0]
    nsteps = int(t_max / DT) + 2
    P = np.zeros((nsteps, NM, 2))
    PHI = np.zeros((nsteps, NR))
    ev = np.zeros((80000, 8))
    ne = 0
    p = pos0.copy()
    v = vel0.copy()
    phi = phi0.copy()
    cur = 0
    winner = -1
    win_step = -1
    out_step = -1
    last = nsteps - 1
    rr = M_R + HW
    sp_start = -1.0
    for s in range(nsteps):
        t = s * DT
        P[s] = p
        PHI[s] = phi
        if win_step >= 0 and s >= win_step + int(post_win / DT):
            last = s
            break
        if sp_start < 0.0 and cur == NR - 1:
            sp_start = t + sp_t
        k_sp = 0.0
        if sp_start >= 0.0:
            k_sp = smooth((t - sp_start) / 0.8)
        om_scale = (1.0 + 0.015 * t) * (1.0 + (sp_om - 1.0) * k_sp)
        v_t = v0 * (1.0 + (sp_v - 1.0) * k_sp)
        for k in range(NR):
            phi[k] += omega_base[k] * om_scale * DT
        for i in range(NM):
            p[i, 0] += v[i, 0] * DT
            p[i, 1] += v[i, 1] * DT
        for i in range(NM):
            for j in range(i + 1, NM):
                if i == winner or j == winner:
                    continue
                dx = p[j, 0] - p[i, 0]
                dy = p[j, 1] - p[i, 1]
                d2 = dx * dx + dy * dy
                if d2 < (2 * M_R) ** 2 and d2 > 1e-9:
                    d = np.sqrt(d2)
                    nx = dx / d
                    ny = dy / d
                    ov = 2 * M_R - d
                    p[i, 0] -= nx * ov * 0.5
                    p[i, 1] -= ny * ov * 0.5
                    p[j, 0] += nx * ov * 0.5
                    p[j, 1] += ny * ov * 0.5
                    rv = (v[j, 0] - v[i, 0]) * nx + (v[j, 1] - v[i, 1]) * ny
                    if rv < 0:
                        v[i, 0] += rv * nx
                        v[i, 1] += rv * ny
                        v[j, 0] -= rv * nx
                        v[j, 1] -= rv * ny
                        if ne < 80000:
                            ev[ne, 0] = EV_MM
                            ev[ne, 1] = s
                            ev[ne, 2] = i
                            ev[ne, 3] = j
                            ev[ne, 4] = -rv
                            ev[ne, 6] = p[i, 0] + nx * M_R
                            ev[ne, 7] = p[i, 1] + ny * M_R
                            ne += 1
        for i in range(NM):
            if i == winner:
                continue
            for k in range(cur, NR):
                R = radii[k]
                d = np.sqrt(p[i, 0] ** 2 + p[i, 1] ** 2)
                if abs(d - R) >= rr or d < 1e-6:
                    continue
                ang = np.arctan2(p[i, 1], p[i, 0])
                th = wrap(ang - phi[k])
                gk = gaps[k]
                if winner >= 0 and k == NR - 1:
                    gk = gaps[k] * (1.0 - smooth((s - win_step) * DT / 0.3))
                if abs(th) > gk * 0.5:
                    nx = p[i, 0] / d
                    ny = p[i, 1] / d
                    vn = v[i, 0] * nx + v[i, 1] * ny
                    if d < R:
                        tgt = R - rr
                        hit = vn > 0
                    else:
                        tgt = R + rr
                        hit = vn < 0
                    p[i, 0] = nx * tgt
                    p[i, 1] = ny * tgt
                    if hit:
                        v[i, 0] -= 2 * vn * nx
                        v[i, 1] -= 2 * vn * ny
                        a = (np.random.random() * 2 - 1) * noise
                        ca = np.cos(a)
                        sa = np.sin(a)
                        vx = v[i, 0] * ca - v[i, 1] * sa
                        vy = v[i, 0] * sa + v[i, 1] * ca
                        vn2 = vx * nx + vy * ny
                        if (d < R and vn2 < 0) or (d >= R and vn2 > 0):
                            v[i, 0] = vx
                            v[i, 1] = vy
                        if ne < 80000:
                            ev[ne, 0] = EV_WALL
                            ev[ne, 1] = s
                            ev[ne, 2] = i
                            ev[ne, 3] = k
                            ev[ne, 4] = abs(vn)
                            ev[ne, 6] = nx * R
                            ev[ne, 7] = ny * R
                            ne += 1
                else:
                    om = omega_base[k] * om_scale
                    for sgn in (-1.0, 1.0):
                        ea = phi[k] + sgn * gk * 0.5
                        ex = R * np.cos(ea)
                        ey = R * np.sin(ea)
                        qx = p[i, 0] - ex
                        qy = p[i, 1] - ey
                        q2 = qx * qx + qy * qy
                        if q2 < rr * rr and q2 > 1e-9:
                            q = np.sqrt(q2)
                            qx /= q
                            qy /= q
                            p[i, 0] = ex + qx * rr
                            p[i, 1] = ey + qy * rr
                            ux = -om * ey
                            uy = om * ex
                            rvx = v[i, 0] - ux
                            rvy = v[i, 1] - uy
                            vn = rvx * qx + rvy * qy
                            if vn < 0:
                                rvx -= 2 * vn * qx
                                rvy -= 2 * vn * qy
                                v[i, 0] = rvx + ux
                                v[i, 1] = rvy + uy
                                if ne < 80000:
                                    ev[ne, 0] = EV_END
                                    ev[ne, 1] = s
                                    ev[ne, 2] = i
                                    ev[ne, 3] = k
                                    ev[ne, 4] = -vn
                                    ev[ne, 6] = ex
                                    ev[ne, 7] = ey
                                    ne += 1
                break
        if cur < NR and winner < 0:
            R = radii[cur]
            for i in range(NM):
                if i == winner:
                    continue
                d = np.sqrt(p[i, 0] ** 2 + p[i, 1] ** 2)
                if d > R + 2.0:
                    if ne < 80000:
                        ev[ne, 0] = EV_BREAK
                        ev[ne, 1] = s
                        ev[ne, 2] = i
                        ev[ne, 3] = cur
                        ev[ne, 6] = p[i, 0]
                        ev[ne, 7] = p[i, 1]
                        ne += 1
                    if cur == NR - 1:
                        winner = i
                        win_step = s
                        if ne < 80000:
                            ev[ne, 0] = EV_WIN
                            ev[ne, 1] = s
                            ev[ne, 2] = i
                            ne += 1
                    else:
                        cur += 1
                    break
        if winner >= 0 and out_step < 0:
            d = np.sqrt(p[winner, 0] ** 2 + p[winner, 1] ** 2)
            if d > radii[NR - 1] + rr:
                out_step = s
                if ne < 80000:
                    ev[ne, 0] = EV_OUT
                    ev[ne, 1] = s
                    ev[ne, 2] = winner
                    ne += 1
        for i in range(NM):
            if i == winner:
                if out_step >= 0:
                    f = np.exp(-11.0 * DT)
                    v[i, 0] *= f
                    v[i, 1] *= f
                continue
            sp = np.sqrt(v[i, 0] ** 2 + v[i, 1] ** 2)
            if sp > 1e-6:
                g = 1.0 + 0.08 * (v_t / sp - 1.0)
                v[i, 0] *= g
                v[i, 1] *= g
    return P[:last + 1], PHI[:last + 1], ev[:ne], winner, win_step, out_step


def ring_radii(n):
    return np.linspace(S.R_INNER, S.R_OUTER, n)


def make_initial(seed, prm):
    rng = np.random.default_rng(seed)
    nm = S.N_MARBLES
    nr = len(prm["gaps"])
    th0 = rng.uniform(0, 2 * np.pi)
    order = rng.permutation(nm)
    pos = np.zeros((nm, 2))
    vel = np.zeros((nm, 2))
    for slot in range(nm):
        i = order[slot]
        a = th0 + 2 * np.pi * slot / nm
        pos[i] = S.START_RADIUS * np.array([np.cos(a), np.sin(a)])
        b = a + rng.uniform(-0.8, 0.8)
        vel[i] = prm["v0"] * np.array([np.cos(b), np.sin(b)])
    phi0 = rng.uniform(0, 2 * np.pi, nr)
    sgn = 1.0 if rng.random() < 0.5 else -1.0
    omega = np.array([sgn * ((-1) ** k) * (prm["om0"] + prm["om_k"] * k) for k in range(nr)])
    return pos, vel, phi0, omega


def run(seed=None, prm=None, t_max=40.0, post_win=None):
    seed = S.SEED if seed is None else seed
    prm = S.PHYS if prm is None else prm
    post_win = S.POST_WIN if post_win is None else post_win
    pos, vel, phi0, omega = make_initial(seed, prm)
    gaps = np.radians(np.array(prm["gaps"], dtype=float))
    radii = ring_radii(len(gaps))
    P, PHI, ev, winner, ws, os_ = simulate(pos, vel, phi0, gaps, omega, radii, prm["v0"],
                                           prm["sp_t"], prm["sp_om"], prm["sp_v"], t_max,
                                           post_win, prm["noise"], seed,
                                           S.N_MARBLES, S.MARBLE_R, S.RING_HALF_WIDTH, S.DT)
    return dict(P=P, PHI=PHI, ev=ev, winner=winner, win_step=ws, out_step=os_, gaps=gaps,
                omega=omega, radii=radii, seed=seed, phi0=phi0)


def breaks(res):
    """[(sim_time, marble, ring)] in order; the last one is the win."""
    out = []
    for e in res["ev"]:
        if int(e[0]) == EV_BREAK:
            out.append((e[1] * S.DT, int(e[2]), int(e[3])))
    return out


def record(res, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    np.savez_compressed(path, P=res["P"], PHI=res["PHI"], ev=res["ev"], winner=res["winner"],
                        win_step=res["win_step"], out_step=res["out_step"], gaps=res["gaps"],
                        omega=res["omega"], radii=res["radii"], seed=res["seed"], phi0=res["phi0"],
                        phys=repr(sorted(S.PHYS.items())))


def load(path):
    z = np.load(path, allow_pickle=False)
    res = {k: z[k] for k in ("P", "PHI", "ev", "gaps", "omega", "radii", "phi0")}
    for k in ("winner", "win_step", "out_step", "seed"):
        res[k] = int(z[k])
    res["phys"] = str(z["phys"])
    return res


if __name__ == "__main__":
    res = run()
    if len(sys.argv) > 1 and sys.argv[1] == "record":
        record(res, S.RACE_FILE)
        print("saved", os.path.relpath(S.RACE_FILE, os.path.dirname(os.path.abspath(__file__))))
    b = breaks(res)
    print("seed", res["seed"], "winner", S.NAMES[res["winner"]], "at", round(res["win_step"] * S.DT, 3), "s")
    for t, i, k in b:
        print(f"  ring {k + 1:2d} broken by {S.NAMES[i]:6s} at {t:6.3f} s")
