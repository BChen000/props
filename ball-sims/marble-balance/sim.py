"""Physics of the balance: marbles roll down their tracks (glass along the shelf on the left, steel down the zigzag
on the right), drop into the baskets and pile up; the beam turns about its pivot under the weight in the baskets and
rests on a stop post at either end of its swing.

Soft-sphere contacts (springs and dampers) between marbles and against every box of the set, integrated at SIM_HZ.
The baskets work like the pans of a scale: the weight and landing knocks they take turn the beam at the fixed arm
ARM, whatever spot in the basket a marble lands on, so the side with more mass goes down (and the totals on the
counters always predict the result). Each marble starts at its track's spawn point so that it lands at its time in
settings.LAND_LEFT / LAND_RIGHT; run() adjusts the start times until the landings match.

    python3 sim.py          -> build/sim.npz and the flips, e.g. "flips at 0.62 R, 2.21 L, ..."
"""
import math
import os
import sys

import numba as nb
import numpy as np

import settings as C
import scene as S

K_WALL, K_BALL = 2.5e5, 2.5e5          # contact stiffness (per unit mass of a glass marble)
ZETA_WALL, ZETA_BALL = 0.55, 0.5       # contact damping (fraction of critical): low bounce
MU, CT = 0.15, 8.0                     # marble-on-marble friction: limit and viscous part (piles settle)
CRR = 3.0                              # rolling resistance on wood (units/s^2); marbles roll, so no sliding friction
EV_MAX = 200000


def box_arrays():
    """Physics boxes: the whole set except the wall; moving=1 for the beam and baskets (beam frame)."""
    st = [b for b in S.static_boxes() if b["oid"] != S.OID_WALL]
    mv = S.beam_local_boxes(physics=True)
    allb = st + mv
    n = len(allb)
    mn = np.array([b["mn"] for b in allb], np.float64)
    mx = np.array([b["mx"] for b in allb], np.float64)
    rot = np.array([b["rot"] for b in allb], np.float64)
    piv = np.array([b["piv"] for b in allb], np.float64)
    moving = np.array([0] * len(st) + [1] * len(mv), np.int64)
    side = np.zeros(n, np.int64)
    kind = np.zeros(n, np.int64)          # 0 wood track, 1 basket, 2 beam/stand
    for k, b in enumerate(allb):
        if b["oid"] == S.OID_LEFT_BASKET:
            side[k], kind[k] = -1, 1
        elif b["oid"] == S.OID_RIGHT_BASKET:
            side[k], kind[k] = 1, 1
        elif b["oid"] in (S.OID_BEAM, S.OID_STAND, S.OID_PIN):
            kind[k] = 2
    return mn, mx, rot, piv, moving, side, kind


@nb.njit(cache=True)
def _step_all(T, dt, rec_every, spawn_t, spawn_p, spawn_v, mass, team, R, G, mn, mx, rot, piv, moving, side, kind,
              P, arm, I_beam, c_piv, th_max, k_stop, c_stop, kw, kb, zw, zb, mu, ct, crr, bhx, rim_y):
    N = len(mass)
    nb_ = len(mn)
    nsteps = int(T / dt)
    nrec = nsteps // rec_every + 1
    x = np.zeros((N, 3)); v = np.zeros((N, 3))
    active = np.zeros(N, np.int64)
    for i in range(N):
        x[i, 0] = 1000.0 + 10.0 * i; x[i, 1] = 1000.0
    land = np.full(N, -1.0)
    th = 0.0; om = 0.0
    RX = np.zeros((nrec, N, 3), np.float32)
    RA = np.zeros((nrec, N), np.int8)
    RT = np.zeros((nrec, 2), np.float64)
    ev = np.zeros((EV_MAX, 6), np.float32)     # t, kind, speed, x, y, marble/side
    nev = 0
    a = np.zeros((N, 3))
    cbs = np.zeros(nb_); sbs = np.zeros(nb_)
    for k in range(nb_):
        cbs[k] = math.cos(rot[k]); sbs[k] = math.sin(rot[k])
    in_stop = 0
    fi = 0
    for it in range(nsteps):
        t = it * dt
        for i in range(N):
            if active[i] == 0 and t >= spawn_t[i]:
                active[i] = 1
                for q in range(3):
                    x[i, q] = spawn_p[i, q]; v[i, q] = spawn_v[i, q]
        cth = math.cos(th); sth = math.sin(th)
        tau = 0.0
        for i in range(N):
            a[i, 0] = 0.0; a[i, 1] = -G; a[i, 2] = 0.0
        # marble - marble
        for i in range(N):
            if active[i] == 0:
                continue
            for j in range(i + 1, N):
                if active[j] == 0:
                    continue
                dx = x[j, 0] - x[i, 0]; dy = x[j, 1] - x[i, 1]; dz = x[j, 2] - x[i, 2]
                d2 = dx * dx + dy * dy + dz * dz
                if d2 >= 4.0 * R * R:
                    continue
                d = math.sqrt(d2) + 1e-12
                nx = dx / d; ny = dy / d; nz = dz / d
                rvx = v[j, 0] - v[i, 0]; rvy = v[j, 1] - v[i, 1]; rvz = v[j, 2] - v[i, 2]
                vn = rvx * nx + rvy * ny + rvz * nz
                meff = mass[i] * mass[j] / (mass[i] + mass[j])
                kk = kb * meff
                cc = 2.0 * zb * math.sqrt(kk * meff)
                f = kk * (2.0 * R - d) - cc * vn
                if f < 0.0:
                    f = 0.0
                tx = rvx - vn * nx; ty = rvy - vn * ny; tz = rvz - vn * nz
                tl = math.sqrt(tx * tx + ty * ty + tz * tz)
                ft = 0.0
                if tl > 1e-9:
                    ft = ct * meff * tl
                    if ft > mu * f:
                        ft = mu * f
                    ft /= tl
                fx = f * nx + ft * tx; fy = f * ny + ft * ty; fz = f * nz + ft * tz
                a[i, 0] -= fx / mass[i]; a[i, 1] -= fy / mass[i]; a[i, 2] -= fz / mass[i]
                a[j, 0] += fx / mass[j]; a[j, 1] += fy / mass[j]; a[j, 2] += fz / mass[j]
                if vn < -12.0 and (2.0 * R - d) <= -vn * dt * 1.01 and nev < EV_MAX:
                    ev[nev, 0] = t; ev[nev, 1] = 0; ev[nev, 2] = -vn; ev[nev, 3] = x[i, 0]; ev[nev, 4] = x[i, 1]
                    ev[nev, 5] = i; nev += 1
        # marble - box
        for i in range(N):
            if active[i] == 0:
                continue
            for k in range(nb_):
                # into the box frame
                if moving[k] == 1:
                    ox = x[i, 0] - P[0]; oy = x[i, 1] - P[1]
                    lx = cth * ox + sth * oy; ly = -sth * ox + cth * oy; lz = x[i, 2] - P[2]
                    c_ = cth; s_ = sth
                elif rot[k] != 0.0:
                    ox = x[i, 0] - piv[k, 0]; oy = x[i, 1] - piv[k, 1]
                    lx = cbs[k] * ox + sbs[k] * oy; ly = -sbs[k] * ox + cbs[k] * oy; lz = x[i, 2] - piv[k, 2]
                    c_ = cbs[k]; s_ = sbs[k]
                else:
                    lx = x[i, 0]; ly = x[i, 1]; lz = x[i, 2]
                    c_ = 1.0; s_ = 0.0
                if (lx < mn[k, 0] - R or lx > mx[k, 0] + R or ly < mn[k, 1] - R or ly > mx[k, 1] + R or
                        lz < mn[k, 2] - R or lz > mx[k, 2] + R):
                    continue
                qx = min(max(lx, mn[k, 0]), mx[k, 0]); qy = min(max(ly, mn[k, 1]), mx[k, 1])
                qz = min(max(lz, mn[k, 2]), mx[k, 2])
                ddx = lx - qx; ddy = ly - qy; ddz = lz - qz
                dist = math.sqrt(ddx * ddx + ddy * ddy + ddz * ddz)
                if dist >= R:
                    continue
                if dist > 1e-9:
                    nlx = ddx / dist; nly = ddy / dist; nlz = ddz / dist
                    pen = R - dist
                else:
                    best = 1e30; nlx = 0.0; nly = 1.0; nlz = 0.0
                    for q in range(3):
                        lq = lx if q == 0 else (ly if q == 1 else lz)
                        dlo = lq - mn[k, q]; dhi = mx[k, q] - lq
                        if dlo < best:
                            best = dlo; nlx = -1.0 if q == 0 else 0.0; nly = -1.0 if q == 1 else 0.0
                            nlz = -1.0 if q == 2 else 0.0
                        if dhi < best:
                            best = dhi; nlx = 1.0 if q == 0 else 0.0; nly = 1.0 if q == 1 else 0.0
                            nlz = 1.0 if q == 2 else 0.0
                    pen = R + best
                nx = c_ * nlx - s_ * nly; ny = s_ * nlx + c_ * nly; nz = nlz
                cpx = x[i, 0] - nx * R; cpy = x[i, 1] - ny * R
                vsx = 0.0; vsy = 0.0
                if moving[k] == 1:
                    vsx = -om * (cpy - P[1]); vsy = om * (cpx - P[0])
                rvx = v[i, 0] - vsx; rvy = v[i, 1] - vsy; rvz = v[i, 2]
                vn = rvx * nx + rvy * ny + rvz * nz
                m = mass[i]
                kk = kw * m
                cc = 2.0 * zw * math.sqrt(kk * m)
                f = kk * pen - cc * vn
                if f < 0.0:
                    f = 0.0
                tx = rvx - vn * nx; ty = rvy - vn * ny; tz = rvz - vn * nz
                tl = math.sqrt(tx * tx + ty * ty + tz * tz)
                ftx = 0.0; fty = 0.0; ftz = 0.0
                if tl > 1e-9 and f > 0.0:
                    ft = crr * m
                    if ft * dt > tl:
                        ft = tl / dt
                    ftx = -ft * tx / tl; fty = -ft * ty / tl; ftz = -ft * tz / tl
                fx = f * nx + ftx; fy = f * ny + fty; fz = f * nz + ftz
                a[i, 0] += fx / m; a[i, 1] += fy / m; a[i, 2] += fz / m
                if moving[k] == 1:
                    if side[k] != 0:
                        tau += side[k] * arm * cth * (-fy)       # a scale pan: fixed arm
                    else:
                        tau += (cpx - P[0]) * (-fy) - (cpy - P[1]) * (-fx)
                if vn < -10.0 and pen <= -vn * dt * 1.01 and nev < EV_MAX:
                    ev[nev, 0] = t; ev[nev, 1] = 1 + kind[k]; ev[nev, 2] = -vn; ev[nev, 3] = x[i, 0]
                    ev[nev, 4] = x[i, 1]; ev[nev, 5] = i; nev += 1
        # landed: inside its basket, below the rim (on the floor or on the pile)
        for i in range(N):
            if active[i] == 0 or land[i] >= 0.0:
                continue
            ox = x[i, 0] - P[0]; oy = x[i, 1] - P[1]
            lx = cth * ox + sth * oy; ly = -sth * ox + cth * oy
            if abs(lx - team[i] * arm) < bhx and ly < rim_y:
                land[i] = t
        # the beam
        ts = 0.0
        if th > th_max:
            ts = -k_stop * (th - th_max) - c_stop * om
            if ts > 0.0:
                ts = 0.0
        elif th < -th_max:
            ts = -k_stop * (th + th_max) - c_stop * om
            if ts < 0.0:
                ts = 0.0
        if ts != 0.0 and in_stop == 0:
            if nev < EV_MAX:
                ev[nev, 0] = t; ev[nev, 1] = 9; ev[nev, 2] = abs(om); ev[nev, 3] = 0.0; ev[nev, 4] = 0.0
                ev[nev, 5] = 1.0 if th > 0 else -1.0
                nev += 1
            in_stop = 1
        elif ts == 0.0 and abs(th) < th_max - 0.002:
            in_stop = 0
        alpha = (tau + ts - c_piv * om) / I_beam
        om += alpha * dt
        th += om * dt
        for i in range(N):
            if active[i] == 0:
                continue
            for q in range(3):
                v[i, q] += a[i, q] * dt
                x[i, q] += v[i, q] * dt
        if it % rec_every == 0 and fi < nrec:
            for i in range(N):
                for q in range(3):
                    RX[fi, i, q] = x[i, q]
                RA[fi, i] = active[i]
            RT[fi, 0] = th; RT[fi, 1] = om
            fi += 1
    return RX, RA, RT, ev[:nev], land


def teams():
    """Per marble: team side (-1 glass/left, +1 steel/right), mass, landing target time."""
    nl, nr = C.LEFT["n"], C.RIGHT["n"]
    assert len(C.LAND_LEFT) == nl and len(C.LAND_RIGHT) == nr
    team = np.array([-1] * nl + [1] * nr, np.int64)
    mass = np.array([C.LEFT["mass"]] * nl + [C.RIGHT["mass"]] * nr, np.float64)
    target = np.array(list(C.LAND_LEFT) + list(C.LAND_RIGHT), np.float64) + C.T_LEAD
    return team, mass, target


def spawn_points(team, seed=11):
    """Start positions and pushes; a small random offset across the track (z) lets the marbles spread out in the
    baskets instead of stacking in one plane."""
    rng = np.random.default_rng(seed)
    p = np.zeros((len(team), 3)); v = np.zeros((len(team), 3))
    gx, gv = C.GLASS_SPAWN
    sx, sv = C.STEEL_SPAWN
    for i, s in enumerate(team):
        if s < 0:
            seg = C.GLASS_RAMP
            x0, v0 = gx, gv
        else:
            seg = C.STEEL_ZIG[0]
            x0, v0 = sx, sv
        (ax, ay), (bx, by) = seg
        ang = math.atan2(by - ay, bx - ax)
        y = S.track_y(seg, x0)
        p[i] = (x0 - math.sin(ang) * C.R, y + math.cos(ang) * C.R, rng.uniform(-0.2, 0.2))
        v[i] = (v0 * math.cos(ang), v0 * math.sin(ang), rng.uniform(-2.0, 2.0))
    return p, v


def simulate(spawn_t, T):
    team, mass, _ = teams()
    sp, sv = spawn_points(team)
    mn, mx, rot, piv, moving, side, kind = box_arrays()
    I_beam = C.BEAM_MASS * C.ARM ** 2
    G = C.G
    c_piv = C.PIVOT_DAMP * 2.0 * math.sqrt(C.LEFT["mass"] * G * C.ARM * I_beam)
    k_stop = C.STOP_K
    c_stop = 2.0 * C.STOP_ZETA * math.sqrt(k_stop * (I_beam + 40 * C.ARM ** 2))
    dt = 1.0 / C.SIM_HZ
    rec = C.SIM_HZ // C.REC_HZ
    return _step_all(T, dt, rec, np.asarray(spawn_t, np.float64), sp, sv, mass, team, C.R, G, mn, mx, rot, piv,
                     moving, side, kind, np.array(C.PIVOT, np.float64), C.ARM, I_beam, c_piv, C.THETA_MAX, k_stop,
                     c_stop, K_WALL, K_BALL, ZETA_WALL, ZETA_BALL, MU, CT, CRR, C.BASKET_HX,
                     S.basket_floor_y() + C.BASKET_H - 0.5)


def run(log=print, iters=5):
    """Finds start times that land every marble at its scheduled time, then returns the recording."""
    team, mass, target = teams()
    T = float(max(target)) + C.HOLD_S + 1.5
    # first guess from a lone marble down each track
    lone = np.full(len(team), 1e3)
    lone[0] = lone[len(team) - 1] = 0.0
    land0 = simulate(lone, 5.0)[4]
    spawn = target - np.where(team < 0, land0[0], land0[-1])
    best = None
    for it in range(iters):
        RX, RA, RT, ev, land = simulate(spawn, T)
        err = np.where(land < 0, 9.0, target - land)
        score = np.abs(err).max()
        log(f"sim pass {it + 1}: landing error max {score:.3f} s, {int((land < 0).sum())} never landed")
        if best is not None and score >= best[0]:
            break                                   # nudging made it worse: keep the best pass
        best = (score, dict(RX=RX, RA=RA, RT=RT, ev=ev, land=land, spawn=spawn.copy()))
        if score < 0.02:
            break
        # nudge only the marbles that are a little off; a big miss means a knock on the way, not a timing error
        spawn = spawn + np.where(np.abs(err) < 0.4, 0.8 * err, 0.0)
    out = best[1]
    out.update(team=team, mass=mass, target=target, hz=C.REC_HZ)
    return out


def check(simd, log=print):
    """Where every marble ended up: in its own basket, or not (a marble that bounced out would spoil the count)."""
    team = simd["team"]
    th = float(simd["RT"][-2, 0])
    p = simd["RX"][-2].astype(float) - np.array(C.PIVOT)
    lx = math.cos(th) * p[:, 0] + math.sin(th) * p[:, 1]
    ok = np.abs(lx - team * C.ARM) < C.BASKET_HX + 0.2
    if not ok.all():
        log(f"WARNING: marbles outside their basket at the end: {np.nonzero(~ok)[0].tolist()}")
    return bool(ok.all())


def flips(simd):
    """(video time, side that went down) each time the beam crosses level."""
    th = simd["RT"][:, 0]
    s = np.sign(th)
    k = np.nonzero((s[1:] != s[:-1]) & (s[1:] != 0))[0]
    return [((i + 1) / simd["hz"] - C.T_LEAD, "R" if th[i + 1] < 0 else "L") for i in k]


if __name__ == "__main__":
    simd = run()
    os.makedirs(C.BUILD, exist_ok=True)
    np.savez_compressed(os.path.join(C.BUILD, "sim.npz"), **simd)
    print("flips at " + ", ".join(f"{t:.2f} {s}" for t, s in flips(simd)))
    check(simd)
    th = np.degrees(simd["RT"][:, 0])
    print(f"theta range {th.min():.2f}..{th.max():.2f} deg")
