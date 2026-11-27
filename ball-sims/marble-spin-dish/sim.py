"""Physics of the spinning dish: marbles launched around the rim of a wooden dish roll on its surface (a gentle cone
with a funnel dip around the centre hole), bounce off the rim, the pegs and each other, slow down and spiral in, and
drop through the hole one by one. The last one still spinning wins. Adapted from ../marble-funnel-drain/sim.py
(same soft-sphere contacts, rolling resistance and drag), with a round rim, pegs and a launch around the rim.

    python3 sim.py [seed]       -> build/sim_seed<seed>.npz and a one-line summary
    python3 sim.py --search 1-300   ranks seeds for a good race (spread-out drops, a long final duel, near misses)
"""
import math
import os
import sys

import numba as nb
import numpy as np

import settings as C

G = 1200.0
HZ = 4000
REC = 16                       # record every 16 steps: 250 Hz


@nb.njit(cache=True)
def surf(r, P):
    S0, S1, DEP, SIG, HR = P[0], P[1], P[2], P[3], P[4]
    e = math.exp(-(r / SIG) ** 2)
    h = S0 * r + 0.5 * S1 * r * r - DEP * e - HR
    s = S0 + S1 * r + 2.0 * DEP * r / (SIG * SIG) * e
    return h, s


def floor_y(r):
    """Dish floor height above the table at radius r (numpy)."""
    P = params()
    r = np.asarray(r, float)
    e = np.exp(-(r / C.SIG) ** 2)
    return C.FLOOR_Y + C.S0 * r + 0.5 * C.S1 * r * r - C.DEP * e - P[4]


def params():
    h_rd = C.S0 * C.RD + 0.5 * C.S1 * C.RD ** 2 - C.DEP * math.exp(-(C.RD / C.SIG) ** 2)
    return np.array([C.S0, C.S1, C.DEP, C.SIG, h_rd, C.FLOOR_Y, C.RD, C.RH], np.float64)


@nb.njit(cache=True)
def simulate(x0, z0, vx0, vz0, P, pegs, R, T, crr, gam, wall_e, peg_e):
    N = len(x0)
    dt = 1.0 / 4000.0
    nsteps = int(T / dt)
    nrec = nsteps // 16 + 1
    x = x0.copy(); z = z0.copy(); vx = vx0.copy(); vz = vz0.copy()
    y = np.zeros(N); vy = np.zeros(N)
    state = np.ones(N, np.int64)
    drain_t = np.full(N, -1.0)
    RX = np.zeros((nrec, N), np.float32); RY = np.zeros((nrec, N), np.float32); RZ = np.zeros((nrec, N), np.float32)
    RS = np.zeros((nrec, N), np.int8)
    ev = np.zeros((200000, 5), np.float32)
    nev = 0
    FY, RD, RH = P[5], P[6], P[7]
    kb = 6.0e5
    cb = 2.0 * 0.45 * math.sqrt(kb * 0.5)
    hrh, srh = surf(RH, P)
    rfall = RH - R * srh / math.sqrt(1 + srh * srh)
    ax = np.zeros(N); az = np.zeros(N)
    fi = 0
    for it in range(nsteps):
        t = it * dt
        for i in range(N):
            if state[i] == 1:
                r = math.sqrt(x[i] * x[i] + z[i] * z[i]) + 1e-9
                h, s = surf(r, P)
                y[i] = FY + h + R * math.sqrt(1.0 + s * s)
            ax[i] = 0.0; az[i] = 0.0
        for i in range(N):
            if state[i] != 1:
                continue
            for j in range(i + 1, N):
                if state[j] != 1:
                    continue
                dx = x[j] - x[i]; dz = z[j] - z[i]; dy = y[j] - y[i]
                d2 = dx * dx + dy * dy + dz * dz
                if d2 < 4.0 * R * R:
                    d = math.sqrt(d2) + 1e-12
                    nx = dx / d; nz = dz / d
                    dvx = vx[j] - vx[i]; dvz = vz[j] - vz[i]
                    vn = dvx * nx + dvz * nz
                    f = kb * (2.0 * R - d) - cb * vn
                    if f < 0.0:
                        f = 0.0
                    ax[i] -= f * nx; az[i] -= f * nz
                    ax[j] += f * nx; az[j] += f * nz
                    if vn < -3.0 and (2.0 * R - d) <= -vn * dt * 1.01 and nev < 200000:
                        ev[nev, 0] = t; ev[nev, 1] = -vn; ev[nev, 2] = 0.5 * (x[i] + x[j]); ev[nev, 3] = 0.0
                        ev[nev, 4] = 0.5 * (z[i] + z[j]); nev += 1
        for i in range(N):
            if state[i] == 1:
                r = math.sqrt(x[i] * x[i] + z[i] * z[i]) + 1e-9
                h, s = surf(r, P)
                gacc = (5.0 / 7.0) * G * s / (1.0 + s * s)
                fx = ax[i] - gacc * x[i] / r
                fz = az[i] - gacc * z[i] / r
                # rim
                pen = r + R - RD
                if pen > 0.0:
                    nx = x[i] / r; nz = z[i] / r
                    v = vx[i] * nx + vz[i] * nz
                    if v > 0.0:
                        if v > 4.0 and nev < 200000:
                            ev[nev, 0] = t; ev[nev, 1] = v; ev[nev, 2] = x[i]; ev[nev, 3] = 1.0; ev[nev, 4] = z[i]
                            nev += 1
                        vx[i] -= (1.0 + wall_e) * v * nx; vz[i] -= (1.0 + wall_e) * v * nz
                    x[i] -= pen * nx; z[i] -= pen * nz
                # pegs
                for k in range(pegs.shape[0]):
                    dx = x[i] - pegs[k, 0]; dz = z[i] - pegs[k, 1]
                    d = math.sqrt(dx * dx + dz * dz) + 1e-12
                    pen = pegs[k, 2] + R - d
                    if pen > 0.0:
                        nx = dx / d; nz = dz / d
                        v = vx[i] * nx + vz[i] * nz
                        if v < 0.0:
                            if v < -4.0 and nev < 200000:
                                ev[nev, 0] = t; ev[nev, 1] = -v; ev[nev, 2] = x[i]; ev[nev, 3] = 4.0
                                ev[nev, 4] = z[i]; nev += 1
                            vx[i] -= (1.0 + peg_e) * v * nx; vz[i] -= (1.0 + peg_e) * v * nz
                        x[i] += pen * nx; z[i] += pen * nz
                sp2 = math.sqrt(vx[i] * vx[i] + vz[i] * vz[i])
                if sp2 > 1e-6:
                    dec = crr
                    if dec * dt > sp2:
                        dec = sp2 / dt
                    fx -= dec * vx[i] / sp2
                    fz -= dec * vz[i] / sp2
                fx -= gam * vx[i]; fz -= gam * vz[i]
                vx[i] += fx * dt; vz[i] += fz * dt
                x[i] += vx[i] * dt; z[i] += vz[i] * dt
                r2 = math.sqrt(x[i] * x[i] + z[i] * z[i])
                if r2 < rfall:
                    state[i] = 2
                    drain_t[i] = t
                    vy[i] = 0.0
                    if nev < 200000:
                        ev[nev, 0] = t; ev[nev, 1] = sp2; ev[nev, 2] = x[i]; ev[nev, 3] = 2.0; ev[nev, 4] = z[i]
                        nev += 1
            elif state[i] == 2:
                damp = math.exp(-dt / 0.05)
                vx[i] *= damp; vz[i] *= damp
                vy[i] -= G * dt
                x[i] += vx[i] * dt; z[i] += vz[i] * dt; y[i] += vy[i] * dt
                r2 = math.sqrt(x[i] * x[i] + z[i] * z[i]) + 1e-9
                lim = RH - R
                if r2 > lim:
                    x[i] *= lim / r2; z[i] *= lim / r2
                if y[i] < -6.0:
                    state[i] = 3
        if it % 16 == 0 and fi < nrec:
            for i in range(N):
                RX[fi, i] = x[i]; RY[fi, i] = y[i]; RZ[fi, i] = z[i]; RS[fi, i] = state[i]
            fi += 1
    return RX, RY, RZ, RS, ev[:nev], drain_t


def launch(seed):
    rng = np.random.default_rng(seed)
    n = len(C.MARBLES)
    a0 = rng.uniform(0, 2 * np.pi)
    ang = a0 + np.arange(n) * 2 * np.pi / n + rng.uniform(-0.12, 0.12, n)
    r0 = C.RD - C.R - 0.4 - rng.uniform(0, 1.2, n)
    x0, z0 = r0 * np.cos(ang), r0 * np.sin(ang)
    v = rng.permutation(np.linspace(*C.V_SPIN, n)) + rng.uniform(-0.5, 0.5, n)
    vr = rng.uniform(-3, 3, n)
    vx0 = -np.sin(ang) * v + np.cos(ang) * vr
    vz0 = np.cos(ang) * v + np.sin(ang) * vr
    return x0, z0, vx0, vz0


def run(seed, T=None):
    x0, z0, vx0, vz0 = launch(seed)
    pegs = np.array([(px, pz, C.PEG_R) for px, pz in C.PEGS], np.float64).reshape(-1, 3)
    RX, RY, RZ, RS, ev, drain = simulate(x0, z0, vx0, vz0, params(), pegs, C.R, T or C.SIM_T, C.CRR, C.GAM,
                                         C.WALL_E, C.PEG_E)
    return dict(RX=RX, RY=RY, RZ=RZ, RS=RS, ev=ev, drain=drain, hz=HZ / REC, seed=seed)


def near_misses(sim):
    """(time, marble) of each pass within NEAR_MISS of the hole's edge that didn't fall in."""
    rr = np.hypot(sim["RX"], sim["RZ"])
    out = []
    edge = C.RH + C.NEAR_MISS
    for i in range(rr.shape[1]):
        alive = sim["RS"][:, i] == 1
        close = alive & (rr[:, i] < edge)
        k = 0
        while k < len(close):
            if close[k]:
                j = k
                while j < len(close) and close[j]:
                    j += 1
                fell = j < len(close) and sim["RS"][j, i] != 1
                if not fell:
                    m = k + int(np.argmin(rr[k:j, i]))
                    out.append((m / sim["hz"], i))
                k = j
            else:
                k += 1
    return sorted(out)


def score(sim):
    """Higher is better: drops a few seconds apart (one double knock-out is fine), a final duel of 5-9 s, and near
    misses, especially during the duel. The video starts a few seconds before the first drop."""
    d = np.sort(sim["drain"][sim["drain"] >= 0])
    n = len(C.MARBLES)
    if len(d) < n - 1:
        return -1e9, "not enough drops"
    d = d[:n - 1]
    gaps = np.diff(d)
    nm = [t for t, _ in near_misses(sim)]
    duel = d[-1] - d[-2]
    s = 0.0
    small = np.sort(np.clip(1.4 - gaps[:-1], 0, None))
    s -= 10.0 * small[:-1].sum()                 # the smallest gap may be a double knock-out
    s -= 3.0 * np.clip(gaps[:-1] - 5.5, 0, None).sum()
    s -= 4.0 * max(0.0, 5.0 - duel) + 3.0 * max(0.0, duel - 9.0)
    s += 2.0 * min(5, sum(1 for t in nm if d[0] - 3 < t < d[-1]))
    s += 5.0 * min(2, sum(1 for t in nm if d[-2] + 0.5 < t < d[-1] - 0.8))
    allv = np.sort(np.where(sim["drain"] < 0, 1e9, sim["drain"]))
    alone = allv[n - 1] - d[-1]                  # how long the winner spins alone
    s -= 6.0 * max(0.0, 3.5 - alone)
    return s, (f"drops {np.round(d, 1)} gaps {np.round(gaps, 1)} duel {duel:.1f}s alone {min(alone, 99):.1f}s "
               f"near-misses {len(nm)}")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--search":
        a, b = map(int, sys.argv[2].split("-"))
        res = []
        for sd in range(a, b + 1):
            sim = run(sd, T=45.0)
            sc, info = score(sim)
            res.append((sc, sd, info))
        for sc, sd, info in sorted(res, reverse=True)[:12]:
            print(f"seed {sd:4d}  score {sc:7.1f}  {info}")
    else:
        sd = int(sys.argv[1]) if len(sys.argv) > 1 else (C.SEED or C.SHIPPED_SEED)
        sim = run(sd)
        os.makedirs(C.BUILD, exist_ok=True)
        np.savez_compressed(os.path.join(C.BUILD, f"sim_seed{sd}.npz"), **sim)
        print(score(sim))
