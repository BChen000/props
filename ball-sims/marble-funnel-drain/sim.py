"""Marble Funnel Drain physics: 480 marbles poured onto a bowl-shaped board with a funnel and a hole.

Marbles roll on the board's height field (2D positions, heights from the surface), collide in 3D as soft spheres,
bounce off invisible rounded walls, and drop into the hole one by one. Deterministic for a given seed on one machine.
  python sim.py            -> build/sim_seed<SEED>.npz (about 10 s)
  python sim.py --compare  -> also checks it against assets/drain_seed<SEED>.npz
"""
import math
import os
import sys

import numba as nb
import numpy as np

import settings as S

R = 1.0
G = 981.0
CELL = 2.2
GX0, GY0 = -27.0, -45.0
NCX = int(54 / CELL) + 2
NCY = int(108 / CELL) + 2


@nb.njit(cache=True)
def surf(r, P):
    S0 = P[0]; S1 = P[1]; DEP = P[2]; SIG = P[3]
    e = math.exp(-(r / SIG) ** 2)
    h = S0 * r + 0.5 * S1 * r * r - DEP * e
    s = S0 + S1 * r + 2.0 * DEP * r / (SIG * SIG) * e
    return h, s


@nb.njit(cache=True)
def zcenter(r, P):
    h, s = surf(r, P)
    return h + R * math.sqrt(1.0 + s * s), s


@nb.njit(cache=True)
def simulate(N, sx, sy, svx, svy, st, T, dt, rec_every,
             kb, cb, kw, cw, crr, gam, mu_t, rfall, nrec, P):
    x = np.zeros(N); y = np.zeros(N); z = np.zeros(N)
    vx = np.zeros(N); vy = np.zeros(N); vz = np.zeros(N)
    ax = np.zeros(N); ay = np.zeros(N); az = np.zeros(N)
    state = np.zeros(N, np.int64)
    drain_t = np.full(N, -1.0)
    gone_t = np.full(N, -1.0)
    spawn_t = st.copy()
    order = np.argsort(st)
    nsteps = int(T / dt)
    nframes = nsteps // rec_every + 1
    RX = np.zeros((nframes, N), np.float32)
    RY = np.zeros((nframes, N), np.float32)
    RZ = np.zeros((nframes, N), np.float32)
    RS = np.zeros((nframes, N), np.int8)
    RV = np.zeros(nframes, np.float32)
    RN = np.zeros(nframes, np.float32)
    maxev = 4000000
    ev = np.zeros((maxev, 5), np.float32)
    nev = 0
    head = np.full(NCX * NCY, -1, np.int64)
    nxt = np.full(N, -1, np.int64)
    sp = 0
    RH = P[4]
    zrim, srim = surf(RH, P)
    fi = 0
    for it in range(nsteps):
        t = it * dt
        while sp < N:
            i = order[sp]
            if spawn_t[i] > t:
                break
            ok = True
            for j in range(N):
                if state[j] == 1:
                    dx = x[j] - sx[i]; dy = y[j] - sy[i]
                    if dx * dx + dy * dy < (2.05 * R) ** 2:
                        ok = False
                        break
            if ok:
                x[i] = sx[i]; y[i] = sy[i]; vx[i] = svx[i]; vy[i] = svy[i]
                state[i] = 1
                sp += 1
            else:
                spawn_t[i] = t + 0.004
                order = np.argsort(spawn_t)
                break
        for c in range(NCX * NCY):
            head[c] = -1
        for i in range(N):
            if state[i] == 1 or state[i] == 2:
                cx = int((x[i] - GX0) / CELL); cy = int((y[i] - GY0) / CELL)
                if cx < 0: cx = 0
                if cx >= NCX: cx = NCX - 1
                if cy < 0: cy = 0
                if cy >= NCY: cy = NCY - 1
                c = cy * NCX + cx
                nxt[i] = head[c]; head[c] = i
        for i in range(N):
            if state[i] == 1:
                r = math.sqrt(x[i] * x[i] + y[i] * y[i]) + 1e-9
                zc, s = zcenter(r, P)
                z[i] = zc
                vr = (x[i] * vx[i] + y[i] * vy[i]) / r
                vz[i] = s * vr
        for i in range(N):
            ax[i] = 0.0; ay[i] = 0.0; az[i] = 0.0
        for i in range(N):
            if state[i] != 1:
                continue
            cx = int((x[i] - GX0) / CELL); cy = int((y[i] - GY0) / CELL)
            for ddy in range(-1, 2):
                for ddx in range(-1, 2):
                    ccx = cx + ddx; ccy = cy + ddy
                    if ccx < 0 or ccy < 0 or ccx >= NCX or ccy >= NCY:
                        continue
                    j = head[ccy * NCX + ccx]
                    while j != -1:
                        if j > i and state[j] == 1:
                            dx = x[j] - x[i]; dy = y[j] - y[i]; dz = z[j] - z[i]
                            d2 = dx * dx + dy * dy + dz * dz
                            if d2 < 4.0 * R * R:
                                d = math.sqrt(d2) + 1e-12
                                nx = dx / d; ny = dy / d; nz = dz / d
                                dvx = vx[j] - vx[i]; dvy = vy[j] - vy[i]; dvz = vz[j] - vz[i]
                                vn = dvx * nx + dvy * ny + dvz * nz
                                dlt = 2.0 * R - d
                                f = kb * dlt - cb * vn
                                if f < 0.0:
                                    f = 0.0
                                tvx = dvx - vn * nx; tvy = dvy - vn * ny; tvz = dvz - vn * nz
                                tv = math.sqrt(tvx * tvx + tvy * tvy + tvz * tvz)
                                ft = 0.0
                                if tv > 1e-6:
                                    ft = min(mu_t * f, 40.0 * tv) / tv
                                fx = -f * nx + ft * tvx; fy = -f * ny + ft * tvy; fz = -f * nz + ft * tvz
                                ax[i] += fx; ay[i] += fy; az[i] += fz
                                ax[j] -= fx; ay[j] -= fy; az[j] -= fz
                                if vn < -2.0 and dlt <= -vn * dt * 1.01 and nev < maxev:
                                    ev[nev, 0] = t; ev[nev, 1] = -vn; ev[nev, 2] = 0.5 * (x[i] + x[j])
                                    ev[nev, 3] = 0.0; ev[nev, 4] = 0.5 * (y[i] + y[j])
                                    nev += 1
                        j = nxt[j]
        tot_v = 0.0; nmov = 0.0
        for i in range(N):
            if state[i] == 1:
                r = math.sqrt(x[i] * x[i] + y[i] * y[i]) + 1e-9
                h, s = surf(r, P)
                gacc = (5.0 / 7.0) * G * s / (1.0 + s * s)
                fx = ax[i] - gacc * x[i] / r
                fy = ay[i] - gacc * y[i] / r
                BA = P[5]; BB = P[6]; BYC = P[7]; BRC = P[8]
                px = x[i]; py = y[i] - BYC
                qx = abs(px) - (BA - BRC); qy = abs(py) - (BB - BRC)
                mx = max(qx, 0.0); my = max(qy, 0.0)
                sd = math.sqrt(mx * mx + my * my) + min(max(qx, qy), 0.0) - BRC
                pen = sd + R
                if pen > 0.0:
                    if qx > 0.0 and qy > 0.0:
                        ql = math.sqrt(qx * qx + qy * qy) + 1e-12
                        wnx = qx / ql; wny = qy / ql
                    elif qx > qy:
                        wnx = 1.0; wny = 0.0
                    else:
                        wnx = 0.0; wny = 1.0
                    if px < 0.0:
                        wnx = -wnx
                    if py < 0.0:
                        wny = -wny
                    v = vx[i] * wnx + vy[i] * wny
                    if pen <= v * dt * 1.01 and v > 3.0 and nev < maxev:
                        ev[nev, 0] = t; ev[nev, 1] = v; ev[nev, 2] = x[i]; ev[nev, 3] = 1.0; ev[nev, 4] = y[i]
                        nev += 1
                    f = kw * pen + cw * v
                    if f < 0.0:
                        f = 0.0
                    fx -= f * wnx; fy -= f * wny
                sp2 = math.sqrt(vx[i] * vx[i] + vy[i] * vy[i])
                if sp2 > 1e-6:
                    dec = crr
                    if dec * dt > sp2:
                        dec = sp2 / dt
                    fx -= dec * vx[i] / sp2
                    fy -= dec * vy[i] / sp2
                fx -= gam * vx[i]; fy -= gam * vy[i]
                vx[i] += fx * dt; vy[i] += fy * dt
                x[i] += vx[i] * dt; y[i] += vy[i] * dt
                tot_v += sp2
                if sp2 > 1.0:
                    nmov += 1.0
                r2 = math.sqrt(x[i] * x[i] + y[i] * y[i])
                if r2 < rfall:
                    state[i] = 2
                    drain_t[i] = t
                    if nev < maxev:
                        ev[nev, 0] = t; ev[nev, 1] = sp2; ev[nev, 2] = x[i]; ev[nev, 3] = 2.0; ev[nev, 4] = y[i]
                        nev += 1
            elif state[i] == 2:
                damp = math.exp(-dt / 0.06)
                vx[i] *= damp; vy[i] *= damp
                vz[i] -= G * dt
                x[i] += vx[i] * dt; y[i] += vy[i] * dt; z[i] += vz[i] * dt
                r2 = math.sqrt(x[i] * x[i] + y[i] * y[i]) + 1e-9
                lim = RH - R
                if r2 > lim:
                    x[i] *= lim / r2; y[i] *= lim / r2
                    vr = (x[i] * vx[i] + y[i] * vy[i]) / lim
                    if vr > 0.0:
                        vx[i] -= 1.3 * vr * x[i] / lim; vy[i] -= 1.3 * vr * y[i] / lim
                if z[i] < zrim - 8.0:
                    state[i] = 3
                    gone_t[i] = t
                    if nev < maxev:
                        ev[nev, 0] = t; ev[nev, 1] = -vz[i]; ev[nev, 2] = x[i]; ev[nev, 3] = 3.0; ev[nev, 4] = y[i]
                        nev += 1
        if it % rec_every == 0 and fi < nframes:
            for i in range(N):
                RX[fi, i] = x[i]; RY[fi, i] = y[i]; RZ[fi, i] = z[i]; RS[fi, i] = state[i]
            RV[fi] = tot_v; RN[fi] = nmov
            fi += 1
    return RX, RY, RZ, RS, RV, RN, ev[:nev], drain_t, gone_t


def run(out, quiet=False):
    p = S.SIM
    rng = np.random.default_rng(p["seed"])
    N = p["N"]
    st = np.sort(rng.uniform(0.0, p["pour"], N))
    sx = rng.uniform(p["sx0"], p["sx1"], N)
    sy = rng.uniform(p["sy0"], p["sy1"], N)
    svx = p["vx0"] + rng.normal(0, 4.0, N)
    svy = p["vy0"] + rng.normal(0, 4.0, N)
    P = np.array([p["S0"], p["S1"], p["DEP"], p["SIG"], p["RH"], p["BA"], p["BB"], p["BYC"], p["BRC"]], np.float64)
    zrim, srim = surf(p["RH"], P)
    rfall = p["RH"] - R * srim / math.sqrt(1 + srim * srim)
    dt = 1.0 / 6000.0
    rec_every = 50
    kb = 8.0e5
    cb = 2.0 * p["zeta"] * math.sqrt(kb * 0.5)
    kw = 6.0e5
    cw = 2.0 * 0.2 * math.sqrt(kw)
    RX, RY, RZ, RS, RV, RN, ev, drain_t, gone_t = simulate(
        N, sx, sy, svx, svy, st, p["T"], dt, rec_every, kb, cb, kw, cw, p["crr"], p["gam"], p["mu_t"], rfall, 0, P)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    np.savez_compressed(out, RX=RX, RY=RY, RZ=RZ, RS=RS, RV=RV, RN=RN, ev=ev,
                        drain_t=drain_t, gone_t=gone_t, rec_hz=1.0 / (dt * rec_every), P=P)
    if not quiet:
        d = np.sort(drain_t[drain_t >= 0])
        print("seed", p["seed"], "drained", len(d), "of", N)
        if len(d):
            print("first %.2f  50%% %.2f  90%% %.2f  last %.2f   last 6 gaps %s" % (
                d[0], d[len(d) // 2], d[int(len(d) * 0.9)], d[-1], np.round(np.diff(d[-6:]), 2)))
    return out


def sim_path():
    """The race to show: the recorded one if present (identical on every machine), else simulate and cache it."""
    if S.USE_RECORDED_SIM and os.path.exists(S.RECORDED_SIM):
        return S.RECORDED_SIM
    out = os.path.join(S.BUILD, "sim_seed%d.npz" % S.SEED)
    if not os.path.exists(out):
        run(out)
    return out


if __name__ == "__main__":
    out = run(os.path.join(S.BUILD, "sim_seed%d.npz" % S.SEED))
    if "--compare" in sys.argv:
        a, b = np.load(out), np.load(S.RECORDED_SIM)
        same = all(np.array_equal(a[k], b[k]) for k in ("RX", "RY", "RZ", "RS", "ev", "drain_t", "gone_t"))
        print("identical to the recorded race:", same)
