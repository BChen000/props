"""The picture on the mat: where every marble ends up, and how the growing picture pushes outward.

The picture is a heart made of marbles on a hex lattice. Every lattice point gets a "level" rho: the smallest
scale of the heart (scaled about its notch, which sits just in front of the exit hole) that contains it. The N
points with the lowest rho form the finished heart, and they're handed out from the outside in: the first marble
off the rail ends up on the rim, the last one in the middle, so each colour batch becomes a heart-shaped band.

While the picture grows, a marble that has arrived sits at level rho * sqrt(k / K) on the line from the notch to its
final spot, where k counts the marbles that arrived after it (like dye pushed out by more dye from the same
nozzle: equal-area bands, so the bands stay heart shaped). A few rounds of pairwise relaxation then remove overlaps,
and the newest marble pushes the others rather than the other way round.
"""
import math

import numpy as np
from numba import njit

import settings as C
import layout as LY


def heart_boundary(n=20000):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    x = 16 * np.sin(t) ** 3
    y = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
    return np.stack([x, 5.0 - y], 1)          # notch at the origin, +v toward the camera (down the picture)


def present_boundary(n=20000):
    """A gift box seen from above with a bow: the box's back edge runs through the notch (box below it, toward the
    camera) and the bow's two loops sit behind it, like the heart's lobes. Sizes in marble radii (PRESENT)."""
    P = C.PRESENT
    wb, hb, rl = P["half_w"], P["depth"], P["bow_r"]
    k = n // 3
    t = np.linspace(0, 1, k, endpoint=False)
    box = np.concatenate([np.stack([wb * (2 * t - 1), np.zeros(k)], 1), np.stack([np.full(k, wb), hb * t], 1),
                          np.stack([wb * (1 - 2 * t), np.full(k, hb)], 1), np.stack([np.full(k, -wb), hb * (1 - t)], 1)])
    a = np.linspace(0, 2 * np.pi, k, endpoint=False)
    loops = [np.stack([sx * P["bow_dx"] * rl + rl * np.cos(a), -P["bow_dy"] * rl + rl * np.sin(a)], 1) for sx in (-1, 1)]
    return np.concatenate([box] + loops)


def boundary():
    return present_boundary() if C.SHAPE == "present" else heart_boundary()


def _radius_table(nb=7200):
    b = boundary()
    th = np.arctan2(b[:, 1], b[:, 0])
    r = np.hypot(b[:, 0], b[:, 1])
    idx = ((th + np.pi) / (2 * np.pi) * nb).astype(int) % nb
    tab = np.zeros(nb)
    np.maximum.at(tab, idx, r)
    # fill empty bins from neighbours (the notch directions stay ~0)
    for _ in range(3):
        z = tab == 0
        tab[z] = np.maximum(np.roll(tab, 1), np.roll(tab, -1))[z]
    return tab


_TAB = _radius_table()


def rho_of(u, v):
    """Heart level of points (u, v) relative to the notch (u right, v toward the camera)."""
    th = np.arctan2(v, u)
    nb = len(_TAB)
    idx = ((th + np.pi) / (2 * np.pi) * nb).astype(int) % nb
    return np.hypot(u, v) / np.maximum(_TAB[idx], 1e-6)


def notch():
    return np.array([LY.EXIT[0], C.CUSP_Z])


def slots(n):
    """The n lattice points of the finished heart (x, z), outermost first, and their levels.

    The heart's lobes would reach behind the front face, so the shape is the heart cut by a line just in front of
    the face; the level of a point is its gauge for that cut heart (scaled about the notch), so the picture grows
    as a scaled copy of its final shape."""
    d = 2 * C.R + C.LATTICE_GAP
    rh = d * math.sqrt(3) / 2
    nc = notch()
    z_ok = C.R + 0.15
    v_clip = (z_ok - 0.9) - nc[1]
    best = None
    for off in np.linspace(0, 1, 9, endpoint=False):
        pts = []
        for j in range(-30, 60):
            v = (j + off) * rh
            sh = (j % 2) * d / 2
            for i in range(-30, 31):
                pts.append((i * d + sh, v))
        pts = np.array(pts)
        ok = nc[1] + pts[:, 1] > z_ok
        rh_heart = rho_of(pts[:, 0], pts[:, 1])
        cut = np.where(pts[:, 1] < 0, pts[:, 1] / v_clip, 0.0)
        lo, hi = 0.1, 5.0
        for _ in range(60):
            sc = 0.5 * (lo + hi)
            g = np.maximum(rh_heart / sc, cut)
            if (ok & (g <= 1)).sum() >= n:
                hi = sc
            else:
                lo = sc
        g = np.where(ok, np.maximum(rh_heart / hi, cut), np.inf)
        order = np.argsort(g, kind="stable")[:n]
        sel = pts[order]
        xs = np.sort(sel[:, 0])
        asym = np.abs(xs + xs[::-1]).sum()
        if best is None or asym < best[0] - 1e-9:
            best = (asym, sel, g[order], off, hi)
    _, sel, rho, off, _ = best
    xz = sel + nc[None]
    out = np.argsort(-rho, kind="stable")
    global SCALE
    SCALE = best[4]
    return xz[out], rho[out]


SCALE = 1.0


def n_marbles():
    return C.N_MARBLES or sum(b[2] for b in C.BATCHES)


def region_names(rel):
    """Colour names of the final spots (u, v) relative to the notch, for pictures coloured by region: the present's
    bow (behind the notch), its ribbon (a vertical strip and the two lattice rows nearest RIBBON_AT) and its box."""
    P = C.PRESENT
    u, v = rel[:, 0], rel[:, 1]
    rows = np.unique(np.round(v[v >= 0], 3))
    mid = P["ribbon_at"] * P["depth"] * SCALE
    band = rows[np.argsort(np.abs(rows - mid))[:P.get("ribbon_rows", 2)]]
    names = np.where(np.abs(u) < P["ribbon_half"], "ribbon", "box").astype(object)
    names[np.isin(np.round(v, 3), band)] = "ribbon"
    names[v < 0] = "bow"
    return list(names)


def picture(n):
    """Final spots (outermost first, i.e. in the order the marbles arrive), their sRGB colours and names, and the
    matching group of each (marbles of one group are interchangeable). With REGION_COLOURS the colours belong to the
    spots, and simulate() gives each marble the colour of the spot it ends up on."""
    fin, _ = slots(n)
    if not C.REGION_COLOURS:
        fin = fix_strays(fin)
        cols, names = colours_for(n)
    else:
        names = region_names(fin - notch()[None])
        cols = [C.REGION_SRGB[nm] for nm in names]
    keys = sorted(set(map(tuple, cols)))
    groups = np.array([keys.index(tuple(c)) for c in cols])
    return fin, cols, names, groups


def colours_for(n_total):
    cols, names = [], []
    for name, srgb, k in C.BATCHES:
        cols += [srgb] * k
        names += [name] * k
    assert len(cols) == n_total, (len(cols), n_total)
    return cols, names


def fix_strays(fin):
    """Banding by level can leave a lone marble of one colour inside the next band (the hex rows near the heart's
    tip). Swap such a marble with the best-placed marble of the surrounding colour."""
    band = np.concatenate([[i] * b[2] for i, b in enumerate(C.BATCHES)])
    order = np.arange(len(fin))
    dd = np.linalg.norm(fin[:, None] - fin[None], axis=-1)
    nb = (dd < 2 * C.R + C.LATTICE_GAP + 0.3) & (dd > 0)
    for _ in range(40):
        col = band[np.argsort(order)]          # colour at each slot
        changed = False
        for s_ in range(len(fin)):
            a = col[s_]
            nbc = col[nb[s_]]
            if (nbc == a).sum() > 1:
                continue
            vals, cnt = np.unique(nbc[nbc != a], return_counts=True)
            if len(vals) == 0 or cnt.max() < 3:
                continue
            x = vals[cnt.argmax()]
            cands = [c for c in range(len(fin)) if col[c] == x and c != s_]
            score = [((col[nb[c]] == a).sum(), -abs(order[c] - order[s_])) for c in cands]
            c = cands[max(range(len(cands)), key=lambda k: score[k])]
            if score[cands.index(c)][0] == 0:
                continue
            order[s_], order[c] = order[c], order[s_]
            changed = True
            break
        if not changed:
            break
    out = np.empty_like(fin)
    out[order] = fin
    return out


def smoothstep(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


@njit(cache=True)
def _ss(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


@njit(cache=True)
def _steps(x, v, state, tgt, ta, te, t0, t1, ex, v_roll, t_run, t_brake, run, dmin, zmin, xmin, xmax,
           k_spring, c_damp, hz, iters):
    """Advances the picture physics from t0 to t1 (240 Hz). state: 0 not out yet, 1 rolling out of the tunnel
    (kinematic), 2 in the picture (spring toward tgt, contacts)."""
    n = len(ta)
    dt = 1.0 / hz
    nsteps = max(1, int(round((t1 - t0) * hz)))
    dt = (t1 - t0) / nsteps
    xp = np.zeros((n, 2))
    t = t0
    for _ in range(nsteps):
        t += dt
        for i in range(n):
            if t < te[i]:
                state[i] = 0
            elif t < ta[i]:
                state[i] = 1
                dtr = t - te[i]
                if dtr <= t_run:
                    z = v_roll * dtr
                    vz = v_roll
                else:
                    db = min(dtr - t_run, t_brake)
                    z = run + v_roll * db - 0.5 * (v_roll / t_brake) * db * db
                    vz = v_roll * (1 - db / t_brake)
                x[i, 0] = ex
                x[i, 1] = z
                v[i, 0] = 0.0
                v[i, 1] = vz
            else:
                state[i] = 2
        for i in range(n):
            xp[i, 0] = x[i, 0]
            xp[i, 1] = x[i, 1]
            if state[i] == 2:
                for a in range(2):
                    v[i, a] += dt * (k_spring * (tgt[i, a] - x[i, a]) - c_damp * v[i, a])
                    x[i, a] += dt * v[i, a]
        for it in range(iters):
            for i in range(n):
                if state[i] == 0:
                    continue
                for j in range(i + 1, n):
                    if state[j] == 0 or (state[i] == 1 and state[j] == 1):
                        continue
                    dx = x[j, 0] - x[i, 0]
                    dz = x[j, 1] - x[i, 1]
                    d2 = dx * dx + dz * dz
                    if d2 >= dmin * dmin:
                        continue
                    d = math.sqrt(d2) + 1e-9
                    corr = dmin - d
                    ux, uz = dx / d, dz / d
                    wi = 1.0 if state[i] == 2 else 0.0
                    wj = 1.0 if state[j] == 2 else 0.0
                    ws = wi + wj
                    x[i, 0] -= ux * corr * wi / ws
                    x[i, 1] -= uz * corr * wi / ws
                    x[j, 0] += ux * corr * wj / ws
                    x[j, 1] += uz * corr * wj / ws
            for i in range(n):
                if state[i] == 2:
                    x[i, 1] = max(x[i, 1], zmin)
                    x[i, 0] = min(max(x[i, 0], xmin), xmax)
        for i in range(n):
            if state[i] == 2:
                v[i, 0] = (x[i, 0] - xp[i, 0]) / dt
                v[i, 1] = (x[i, 1] - xp[i, 1]) / dt


def simulate(t_arrive, t_exit, frames_t, roll, log=print):
    """Positions (frames, n, 2) in x, z of every marble that has left the front face (nan before). Marble i (in
    arrival order) rolls out of the exit at t_exit[i] (roll = (v, t_run, t_brake, run)) and reaches the notch at
    t_arrive[i]. A small 2D physics sim: every marble in the picture is pulled by a damped spring toward a point of
    the growing picture, and contacts keep the marbles apart; the marble rolling in can't be pushed back. Marbles of
    one colour are interchangeable, so every frame they're matched to their colour's points by shortest moves, which
    keeps them from jamming."""
    from scipy.optimize import linear_sum_assignment
    n = len(t_arrive)
    ta, te = np.asarray(t_arrive, float), np.asarray(t_exit, float)
    fin, _, _, band = picture(n)
    if C.REGION_COLOURS:
        band = np.zeros(n, np.int64)   # one group: any marble can take any spot; colours are given at the end
    nc = notch()
    rel = fin - nc[None]
    ex = LY.EXIT[0]
    left = np.maximum(n - np.arange(n), 1).astype(float)
    w = 2 * math.pi * C.PILE_HZ
    prm = (ex, *roll, 2 * C.R + 0.02, C.R + 0.1, ex - C.MAT_HALF_W + C.R, ex + C.MAT_HALF_W - C.R, w * w,
           2 * 0.9 * w, 240.0, C.RELAX_ITERS)
    x = np.zeros((n, 2))
    v = np.zeros((n, 2))
    state = np.zeros(n, np.int64)
    nf = len(frames_t)
    out = np.full((nf, n, 2), np.nan)
    t = float(frames_t[0])
    for fi, tf in enumerate(frames_t):
        push = smoothstep((tf - (ta - 0.5 * C.PUSH_S)) / C.PUSH_S)
        settle = smoothstep((tf - ta) / C.PUSH_S)
        k_after = np.cumsum(push[::-1])[::-1] - push
        frac = np.sqrt(np.clip((k_after + settle) / left, 0, 1))
        T = nc[None] + rel * frac[:, None]
        tgt = T.copy()
        for b in range(band.max() + 1):
            idx = np.nonzero((band == b) & (state == 2))[0]
            if len(idx) > 1:
                cost = ((x[idx][:, None, :] - T[idx][None, :, :]) ** 2).sum(-1)
                r, c = linear_sum_assignment(cost)
                tgt[idx[r]] = T[idx[c]]
        if tf > t:
            _steps(x, v, state, tgt, ta, te, t, float(tf), *prm)
            t = float(tf)
        here = state > 0
        out[fi, here] = x[here]
    cost = ((x[:, None, :] - fin[None, :, :]) ** 2).sum(-1)
    r, c = linear_sum_assignment(cost)
    slot = np.empty(n, np.int64)
    slot[r] = c
    log(f"picture: every marble within {np.sqrt(cost[r, c].max()):.2f} radii of its final spot")
    return out, fin, slot


if __name__ == "__main__":
    n = n_marbles()
    fin, cols, names, _ = picture(n)
    print("marbles", n, "x range", fin[:, 0].min(), fin[:, 0].max(), "z range", fin[:, 1].min(), fin[:, 1].max(),
          "scale", round(SCALE, 3), {k: names.count(k) for k in sorted(set(names))})
    from PIL import Image, ImageDraw
    import os
    os.makedirs(C.BUILD, exist_ok=True)
    s = 20
    img = Image.new("RGB", (int(40 * s), int(40 * s)), (110, 170, 90))
    dr = ImageDraw.Draw(img)
    for (x, z), c in zip(fin, cols):
        X, Z = (x - LY.EXIT[0] + 20) * s, z * s
        dr.ellipse([X - s, Z - s, X + s, Z + s], fill=c, outline=(40, 40, 40))
    img.save(C.BUILD + "/%s_plan.png" % C.SHAPE)
    print(C.BUILD + "/%s_plan.png" % C.SHAPE)
