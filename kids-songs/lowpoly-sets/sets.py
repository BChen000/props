"""Reusable low-poly set pieces for the 3D Story Time with Kenji episodes (rendered with ../../shared/lowpoly-gl).

Every function returns meshkit meshes (M) in local coordinates (Z up, the front faces -Y) or adds parts with meshkit.add.
  person(seed)                 a low-poly protester (legs, torso, head, arms), colours from the seed
  sign(w, h)                   a placard on a pole (board UVs 0..1, for a texture)
  pigeon()                     dict of parts: body, beak, legs, eyes, led (the robot eye), wing_L, wing_R (pivots in WING_PIVOT)
  car(), truck()               a hatchback and a guard pickup, with headlight parts
  sky_dome(colours)            an inverted sphere with a vertical colour gradient (render with mode 5)
  terrain(size, n, amp)        a faceted desert floor with height colours (flat discs: flat_r, flats)
  mountains(radius, n, h)      a ring (or arc) of ridges: one continuous jagged skyline
  hangar(), runway()           an arched hangar shell with a door wall, a runway strip
  u2(), jet(), saucer()        the U-2 spy plane, a small unmarked jet, a flying saucer (+ light ring)
  pole(), billboard(w, h)      a wooden utility pole with a crossarm, a billboard on two posts
  fence(length)                a chain-link-style fence line (posts + rails + a mesh panel)
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'shared', 'lowpoly-gl'))
import numpy as np
from meshkit import M, join, rotx, roty, rotz, box, plane, loft, ring, cyl, uvsphere, tube, jitter

SKIN = [(0.55, 0.38, 0.28), (0.36, 0.24, 0.17), (0.66, 0.50, 0.40), (0.25, 0.16, 0.11), (0.60, 0.44, 0.33)]
SHIRT = [(0.55, 0.08, 0.08), (0.08, 0.20, 0.45), (0.85, 0.75, 0.15), (0.10, 0.40, 0.18), (0.30, 0.30, 0.32),
         (0.80, 0.80, 0.78), (0.45, 0.15, 0.50), (0.85, 0.45, 0.10)]
PANTS = [(0.08, 0.09, 0.14), (0.20, 0.22, 0.30), (0.25, 0.20, 0.14), (0.05, 0.05, 0.05)]


def person(seed=0, arms_up=False):
    """About 1.7 m. Returns (mesh, per-face colours). Arms up holds a sign overhead (hands at about z=2.0)."""
    r = np.random.default_rng(seed)
    h = r.uniform(0.92, 1.06)
    skin, shirt, pants = SKIN[r.integers(len(SKIN))], SHIRT[r.integers(len(SHIRT))], PANTS[r.integers(len(PANTS))]
    parts, cols = [], []

    def put(m, c):
        parts.append(m); cols.extend([c] * sum(len(f) - 2 for f in m.f))
    for sx in (-1, 1):
        put(loft([ring(6, 0.065, 0.07, 0.0, 2) + [sx * 0.09, 0, 0], ring(6, 0.075, 0.08, 0.85 * h, 2) + [sx * 0.09, 0, 0]], True, True), pants)
    put(jitter(loft([ring(8, 0.19, 0.12, 0.82 * h, 2.4), ring(8, 0.21, 0.13, 1.22 * h, 2.6), ring(8, 0.16, 0.10, 1.42 * h, 2.2)], True, True), 0.006, seed), shirt)
    put(jitter(uvsphere(8, 6, 0.11).scaled((0.95, 1.05, 1.15)).moved((0, 0, 1.56 * h)), 0.006, seed + 1), skin)
    for sx in (-1, 1):
        sh = np.array([sx * 0.22, 0, 1.38 * h])
        if arms_up:
            el = sh + [sx * 0.05, -0.08, 0.28]; wr = np.array([sx * 0.10, -0.12, 1.98 * h])
        else:
            el = sh + [sx * 0.04, 0.0, -0.28]; wr = el + [0.0, -0.05, -0.26]
        put(tube([sh, el], 0.05, 6), shirt)
        put(tube([el, wr], 0.042, 6), skin if not arms_up else shirt)
    return join(*parts), np.array(cols)


def sign(w=0.62, h=0.42, pole=1.1):
    """Placard: board centred at z=pole + h/2 facing -Y (UVs 0..1), plus a pole from z=0. Returns (board, pole)."""
    board = plane(w, h, (0, -0.012, pole + h / 2 - 0.05))
    stick = box(0.03, 0.03, pole + 0.1, (0, 0, (pole + 0.1) / 2))
    return board, stick


def pigeon():
    """A pigeon about 0.32 m long facing -Y, standing at z=0. Wing pivots at (±0.045, -0.02, 0.135)."""
    body = uvsphere(12, 8, 1.0).scaled((0.075, 0.13, 0.08)).moved((0, 0.0, 0.12))
    body.v[:, 1] += 0.03 * np.clip((body.v[:, 2] - 0.12) / 0.08, 0, 1)
    head = uvsphere(10, 7, 0.042).moved((0, -0.115, 0.205))
    neck = loft([ring(8, 0.05, 0.05, 0.14) + [0, -0.075, 0], ring(8, 0.038, 0.038, 0.19) + [0, -0.105, 0]], False, False)
    beak = cyl(0.009, 0.002, 0.03, 5, 0).rotated(rotx(math.pi / 2 + 0.25)).moved((0, -0.15, 0.198))
    tail = loft([ring(6, 0.045, 0.012, 0.0) , ring(6, 0.06, 0.008, 0.0) + [0, 0.12, 0]], True, True)
    tail = tail.rotated(rotx(0.35)).moved((0, 0.09, 0.115))
    legs = join(*[tube([(sx * 0.025, 0.0, 0.06), (sx * 0.028, -0.005, 0.0)], 0.006, 4) for sx in (-1, 1)])
    eyes = join(*[uvsphere(6, 4, 0.009).moved((sx * 0.034, -0.128, 0.215)) for sx in (-1, 1)])
    wings = {}
    for sx, nm in ((1, 'wing_L'), (-1, 'wing_R')):
        v = np.array([(0, 0.02, 0), (sx * 0.02, -0.05, 0.01), (sx * 0.16, 0.0, 0.0), (sx * 0.20, 0.10, -0.01), (sx * 0.05, 0.13, -0.01)])
        f = [(0, 1, 2), (0, 2, 3), (0, 3, 4)]
        top = M(v, f if sx > 0 else [ff[::-1] for ff in f])
        bot = M(v - [0, 0, 0.006], [ff[::-1] for ff in f] if sx > 0 else f)
        wings[nm] = join(top, bot)
    led = uvsphere(6, 4, 0.0065).moved((-0.036, -0.13, 0.216))
    return dict(body=join(jitter(body, 0.002, 1), head, neck, tail), beak=beak, legs=legs, eyes=eyes, led=led, **wings)


WING_PIVOT = {'wing_L': (0.045, -0.02, 0.135), 'wing_R': (-0.045, -0.02, 0.135)}


def car():
    """Hatchback about 4 m long, front at -Y. Returns dict(body, glass, wheels, lights)."""
    body = loft([ring(10, 0.88, 2.0, 0.28, 4, 0), ring(10, 0.90, 2.05, 0.75, 4, 0), ring(10, 0.86, 2.0, 0.92, 4, 0)], True, True)
    cab = loft([ring(8, 0.80, 1.3, 0.92, 3.2, 0.25), ring(8, 0.70, 0.95, 1.42, 3.0, 0.35)], False, True)
    glass = loft([ring(8, 0.805, 1.27, 0.97, 3.2, 0.25), ring(8, 0.705, 0.93, 1.37, 3.0, 0.35)], False, False)
    wheels = join(*[cyl(0.32, 0.32, 0.22, 12, -0.11).rotated(roty(math.pi / 2)).moved((sx * 0.80, sy * 1.30, 0.32)) for sx in (-1, 1) for sy in (-1, 1)])
    lights = join(*[box(0.25, 0.04, 0.1, (sx * 0.6, -2.03, 0.70)) for sx in (-1, 1)])
    return dict(body=body, glass=glass, wheels=wheels, lights=lights)


def truck():
    """Pickup about 5.4 m long, front at -Y (white guard truck)."""
    bed = box(1.9, 2.2, 0.55, (0, 1.4, 0.85))
    cabin = loft([ring(8, 0.95, 0.9, 0.6, 4, -0.6), ring(8, 0.92, 0.85, 1.55, 3.4, -0.55), ring(8, 0.85, 0.6, 1.95, 3.0, -0.45)], True, True)
    hood = box(1.9, 1.1, 0.5, (0, -1.85, 0.85))
    wheels = join(*[cyl(0.4, 0.4, 0.28, 12, -0.14).rotated(roty(math.pi / 2)).moved((sx * 0.85, sy, 0.4)) for sx in (-1, 1) for sy in (-1.6, 1.6)])
    lights = join(*[box(0.3, 0.04, 0.16, (sx * 0.65, -2.41, 0.92)) for sx in (-1, 1)])
    glass = loft([ring(8, 0.93, 0.87, 1.56, 3.4, -0.55), ring(8, 0.86, 0.62, 1.93, 3.0, -0.45)], False, False).scaled((1.01, 1.01, 1.0))
    return dict(body=join(bed, cabin, hood), wheels=wheels, lights=lights, glass=glass)


def sky_dome(cols=((0.0, (0.9, 0.45, 0.2)), (0.08, (0.55, 0.25, 0.3)), (0.3, (0.08, 0.10, 0.25)), (1.0, (0.01, 0.015, 0.05))), r=900.0):
    """Inverted UV sphere; cols = (height 0..1 above the horizon, rgb) stops; returns (mesh, per-face colours)."""
    s = uvsphere(32, 16, r)
    s = M(s.v, [ff[::-1] for ff in s.f])
    tri, _ = s.tris()
    zc = s.v[tri].mean(1)[:, 2] / r
    hs = np.array([c[0] for c in cols]); cs = np.array([c[1] for c in cols])
    z = np.clip(zc, 0, 1)
    colf = np.stack([np.interp(z, hs, cs[:, k]) for k in range(3)], 1)
    colf[zc < 0] = cs[0] * 0.25
    return M(s.v, [tuple(t) for t in tri]), colf


def terrain(size=300.0, n=60, amp=1.2, seed=3, flat_r=0.0, cols=((0.0, (0.30, 0.20, 0.12)), (1.0, (0.45, 0.32, 0.20))), flats=()):
    """A faceted ground grid (size m square) with smooth noise heights; flat_r flattens a disc around the origin,
    and flats=[(x, y, r), ...] flattens more discs."""
    r = np.random.default_rng(seed)
    xs = np.linspace(-size / 2, size / 2, n + 1)
    X, Y = np.meshgrid(xs, xs)
    Z = np.zeros_like(X)
    for k in range(5):
        fx, fy, ph = r.uniform(0.01, 0.06) * (k + 1), r.uniform(0.01, 0.06) * (k + 1), r.uniform(0, 6.28)
        Z += amp / (k + 1) * np.sin(X * fx + ph) * np.cos(Y * fy + ph * 0.7)
    Z += r.normal(0, amp * 0.08, Z.shape)
    if flat_r:
        d = np.sqrt(X ** 2 + Y ** 2)
        Z *= np.clip((d - flat_r) / (flat_r * 0.6), 0, 1)
    for cx, cy, fr in flats:
        Z *= np.clip((np.sqrt((X - cx) ** 2 + (Y - cy) ** 2) - fr) / (fr * 0.6), 0, 1)
    v = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    f = []
    for j in range(n):
        for i in range(n):
            a = j * (n + 1) + i
            if (i + j) % 2:
                f += [(a, a + 1, a + n + 2), (a, a + n + 2, a + n + 1)]
            else:
                f += [(a, a + 1, a + n + 1), (a + 1, a + n + 2, a + n + 1)]
    m = M(v, f)
    tri, _ = m.tris()
    zc = v[tri].mean(1)[:, 2]
    t = np.clip((zc - Z.min()) / max(Z.max() - Z.min(), 1e-6), 0, 1)
    c0, c1 = np.array(cols[0][1]), np.array(cols[1][1])
    colf = c0 + (c1 - c0) * t[:, None] + r.normal(0, 0.012, (len(tri), 3))
    return M(v, [tuple(x) for x in tri]), np.clip(colf, 0, 1)


def mountains(radius=420.0, n=48, h=(40, 120), seed=4, arc=(0, 2 * math.pi), depth=None):
    """A ring of low-poly ridges at `radius` around the origin: one continuous skyline of n points (broad
    swells plus sharper peaks), a faceted front slope facing the centre and a back slope; returns
    (mesh, per-face colours)."""
    r = np.random.default_rng(seed)
    full = abs((arc[1] - arc[0]) - 2 * math.pi) < 1e-6
    m = n if full else n + 1
    u = np.arange(m) / n
    a = arc[0] + (arc[1] - arc[0]) * u
    s = np.zeros(m)
    for k, amp in ((3, 0.5), (7, 0.35), (13, 0.25), (29, 0.14), (57, 0.07)):
        s += amp * np.sin(2 * math.pi * k * u + r.uniform(0, 2 * math.pi))
    s += r.uniform(-0.05, 0.05, m)
    s = ((s - s.min()) / (s.max() - s.min())) ** 1.3
    ht = h[0] + (h[1] - h[0]) * s
    rr = radius * (1 + r.uniform(-0.02, 0.02, m))
    depth = depth or max(2.0 * ht.max(), 60.0)
    ca, sa = np.cos(a), np.sin(a)
    rows = [(rr, np.full(m, -2.0)),
            (rr + 0.8 * ht * r.uniform(0.7, 1.1, m), ht * r.uniform(0.4, 0.6, m)),
            (rr + 1.5 * ht, ht),
            (rr + 1.5 * ht + depth, np.full(m, -2.0))]
    v = np.concatenate([np.stack([R_ * ca, R_ * sa, z], 1) for R_, z in rows])
    f, cols = [], []
    base = np.array((0.22, 0.14, 0.12))
    for j in range(len(rows) - 1):
        for i in range(m if full else m - 1):
            i1 = (i + 1) % m
            a0, a1, b0, b1 = j * m + i, j * m + i1, (j + 1) * m + i, (j + 1) * m + i1
            f += [(a0, a1, b1), (a0, b1, b0)]
            c = base * r.uniform(0.85, 1.15) * (1.0 if j < 2 else 0.8)
            cols += [c, c * r.uniform(0.82, 1.0)]
    return M(v, f), np.array(cols)


def hangar(w=40.0, d=50.0, n=14):
    """Arched hangar shell (half cylinder along Y) with a back wall and a front wall with a door gap."""
    rings = []
    for j in range(2):
        y = -d / 2 + d * j
        a = np.linspace(0, math.pi, n + 1)
        rings.append(np.stack([w / 2 * np.cos(a), np.full(n + 1, y), w / 2 * 0.62 * np.sin(a)], 1))
    v = np.concatenate(rings); f = [(i, i + 1, n + 2 + i, n + 1 + i) for i in range(n)]
    shell = M(v, f)
    back = M(rings[1][::-1].copy(), [tuple(range(n + 1))])
    front = rings[0]
    door = 0.32 * w
    left = M(np.array([p for p in front if p[0] <= -door] + [(-door, -d / 2, 0)]), [])
    pts = [p for p in front]
    fw = []
    for i in range(n):
        p0, p1 = pts[i], pts[i + 1]
        if abs(p0[0]) > door and abs(p1[0]) > door:
            fw.append(M(np.array([p0, p1, (p1[0], p1[1], 0), (p0[0], p0[1], 0)]), [(0, 1, 2, 3)]))
    top = M(np.array([(-door, -d / 2, w * 0.24), (door, -d / 2, w * 0.24), (door, -d / 2, w * 0.31), (-door, -d / 2, w * 0.31)]), [(0, 1, 2, 3)])
    return join(shell, back, top, *fw)


def runway(length=1200.0, width=45.0):
    return box(width, length, 0.05, (0, 0, 0.03)), join(*[box(1.2, 18, 0.06, (0, -length / 2 + 40 + k * 60, 0.04)) for k in range(int(length / 60) - 1)])


def u2():
    """The U-2: slim fuselage about 19 m, straight wings about 31 m; nose at -Y. Origin at the wing root."""
    secs = [(-9.0, 0.10, 0.10), (-8.2, 0.45, 0.50), (-6.0, 0.70, 0.78), (-2.0, 0.75, 0.85), (2.0, 0.70, 0.80), (6.0, 0.45, 0.55), (9.5, 0.18, 0.30)]
    rings = [ring(10, rx, rz, 0, 2.2) for _, rx, rz in secs]
    rings = [np.stack([r_[:, 0], np.full(len(r_), y), r_[:, 1]], 1) for r_, (y, _, _) in zip(rings, secs)]
    fus = loft(rings, True, True)
    wing = M(np.array([(0.6, -1.4, 0.05), (15.5, -0.4, 0.45), (15.5, 0.55, 0.45), (0.6, 1.4, 0.05),
                       (0.6, -1.4, -0.10), (15.5, -0.4, 0.38), (15.5, 0.55, 0.38), (0.6, 1.4, -0.10)]),
             [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3)])
    wings = join(wing, wing.scaled((-1, 1, 1)).copy())
    wings = M(wings.v, [ff if i < len(wing.f) else ff[::-1] for i, ff in enumerate(wings.f)])
    tailv = M(np.array([(0, 6.5, 0.6), (0, 9.6, 0.4), (0, 10.0, 3.6), (0, 8.8, 3.6)]), [(0, 1, 2, 3)])
    tailv = join(tailv, M(tailv.v.copy(), [(3, 2, 1, 0)]))
    tailh = M(np.array([(0.2, 8.0, 0.5), (3.6, 8.9, 0.5), (3.6, 9.7, 0.5), (0.2, 9.8, 0.5)]), [(0, 1, 2, 3)])
    tailh = join(tailh, tailh.scaled((-1, 1, 1)), M(tailh.v.copy(), [(3, 2, 1, 0)]), M(tailh.scaled((-1, 1, 1)).v.copy(), [(0, 1, 2, 3)]))
    canopy = uvsphere(8, 5, 1.0).scaled((0.42, 0.9, 0.35)).moved((0, -5.6, 0.72))
    return dict(body=join(fus, wings, tailv, tailh), canopy=canopy)


def jet():
    """A small white twin-jet airliner about 30 m long, nose at -Y."""
    secs = [(-15, 0.2, 0.2), (-13.5, 1.3, 1.4), (-10, 1.8, 1.9), (8, 1.8, 1.9), (13, 1.0, 1.3), (15.5, 0.3, 0.6)]
    rings = [np.stack([ring(12, rx, rz, 0, 2)[:, 0], np.full(12, y), ring(12, rx, rz, 0, 2)[:, 1]], 1) for y, rx, rz in secs]
    fus = loft(rings, True, True)
    w = M(np.array([(1.5, -3.0, -0.6), (14.0, 3.0, 0.4), (14.0, 4.5, 0.4), (1.5, 3.0, -0.6)]), [(0, 1, 2, 3)])
    wings = join(w, M(w.v.copy(), [(3, 2, 1, 0)]), w.scaled((-1, 1, 1)), M(w.scaled((-1, 1, 1)).v.copy(), [(0, 1, 2, 3)]))
    fin = M(np.array([(0, 10.0, 1.6), (0, 15.5, 1.4), (0, 16.5, 7.0), (0, 14.3, 7.0)]), [(0, 1, 2, 3)])
    fin = join(fin, M(fin.v.copy(), [(3, 2, 1, 0)]))
    stab = M(np.array([(0.3, 12.5, 1.5), (5.5, 14.8, 1.8), (5.5, 16.0, 1.8), (0.3, 15.8, 1.5)]), [(0, 1, 2, 3)])
    stab = join(stab, M(stab.v.copy(), [(3, 2, 1, 0)]), stab.scaled((-1, 1, 1)), M(stab.scaled((-1, 1, 1)).v.copy(), [(0, 1, 2, 3)]))
    engines = join(*[cyl(0.8, 0.7, 4.0, 10, 0).rotated(rotx(math.pi / 2)).moved((sx * 5.5, -1.5, -1.3)) for sx in (-1, 1)])
    stripe = loft([np.stack([ring(12, 1.82, 1.92, 0, 2)[:, 0], np.full(12, y), ring(12, 1.82, 1.92, 0, 2)[:, 1]], 1) for y in (-13.0, 10.0)], False, False)
    stripe.v[:, 2] = np.clip(stripe.v[:, 2], -0.25, 0.05)
    return dict(body=join(fus, wings, fin, stab, engines), stripe=stripe)


def saucer(r=4.0):
    """A classic flying saucer about 2r wide: lathe body, glass dome, and a ring of light pods (separate part)."""
    prof = [(0.0, -0.55), (0.35, -0.5), (0.8, -0.25), (1.0, 0.0), (0.78, 0.18), (0.45, 0.28), (0.3, 0.3)]
    n = 24
    rings_ = [ring(n, a * r, a * r, b * r) for a, b in prof]
    body = loft(rings_, True, True)
    dome = uvsphere(14, 8, 1.0).scaled((0.33 * r, 0.33 * r, 0.25 * r)).moved((0, 0, 0.3 * r))
    pods = join(*[uvsphere(6, 4, 0.07 * r).moved((0.82 * r * math.cos(2 * math.pi * k / 12), 0.82 * r * math.sin(2 * math.pi * k / 12), -0.2 * r)) for k in range(12)])
    return dict(body=body, dome=dome, lights=pods)


def pole(h=9.0):
    p = cyl(0.14, 0.11, h, 8, 0)
    arm = box(2.6, 0.12, 0.14, (0, 0, h - 0.6))
    ins = join(*[cyl(0.05, 0.05, 0.18, 6, h - 0.53).moved((x, 0, 0)) for x in (-1.1, 0.0, 1.1)])
    return join(p, arm), ins


def billboard(w=12.0, h=4.0, z=6.0):
    """Board centred at (0, 0, z + h/2) facing -Y (UVs 0..1) on two posts, plus a frame and a catwalk."""
    board = plane(w, h, (0, -0.05, z + h / 2))
    frame = join(box(w + 0.3, 0.2, 0.2, (0, 0.05, z + h + 0.05)), box(w + 0.3, 0.2, 0.2, (0, 0.05, z - 0.05)),
                 box(0.2, 0.2, h, (-w / 2 - 0.1, 0.05, z + h / 2)), box(0.2, 0.2, h, (w / 2 + 0.1, 0.05, z + h / 2)))
    posts = join(*[box(0.35, 0.35, z, (sx * w / 4, 0.3, z / 2)) for sx in (-1, 1)], box(w, 0.8, 0.08, (0, -0.4, z - 0.1)))
    return board, join(frame, posts)


def fence(length=40.0, h=2.2, spacing=3.0):
    """Fence along X from -length/2 to length/2: posts, top and bottom rails, and one see-through panel plane."""
    posts = join(*[cyl(0.04, 0.04, h, 6, 0).moved((x, 0, 0)) for x in np.arange(-length / 2, length / 2 + 0.01, spacing)])
    rails = join(box(length, 0.05, 0.05, (0, 0, h)), box(length, 0.05, 0.05, (0, 0, 0.1)))
    panel = plane(length, h, (0, 0, h / 2), 1, 1)
    panel.uv = [[(0, 0), (length / 0.6, 0), (length / 0.6, h / 0.6), (0, h / 0.6)]]
    return join(posts, rails), panel
