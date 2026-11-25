"""Marble Funnel Drain renderer: a CPU ray-caster for chrome and metallic marbles on a lacquered hardwood funnel board.

Per frame: soft shadows and contact occlusion (world-space maps), the board ray-cast through any camera (cached
while the camera holds still), a glossy floor that reflects the marbles, marbles drawn as ray-traced sprites with
reflections of their neighbours, the floor and a studio environment (softbox, fill strip, blue and magenta accent
strips), motion blur by sprite stamping, depth of field (half-res gather), bloom, ACES tone map, vignette and grain.
numba; single-threaded per worker by default (NUMBA_NUM_THREADS).
"""
import hashlib
import json
import math
import os

import cv2
import numba as nb
import numpy as np

import settings as S

_cfg = S.LOOK
W = int(S.W); H = int(S.H)
S0 = float(_cfg['S0']); S1 = float(_cfg['S1']); DEP = float(_cfg['DEP']); SIG = float(_cfg['SIG']); RH = float(_cfg['RH'])
R = 1.0


def _nrm(v):
    v = np.array(v, float)
    return v / np.linalg.norm(v)


def _basis(l):
    u = np.cross(l, [0.0, 0.0, 1.0])
    if np.linalg.norm(u) < 1e-6:
        u = np.array([1.0, 0, 0])
    u = u / np.linalg.norm(u)
    v = np.cross(u, l)
    return u, v / np.linalg.norm(v)


_L = _nrm(_cfg['L']); LX, LY, LZ = [float(a) for a in _L]
_KU, _KV = _basis(_L)
KUX, KUY, KUZ = [float(a) for a in _KU]; KVX, KVY, KVZ = [float(a) for a in _KV]
_L2 = _nrm(_cfg['L2']); L2X, L2Y, L2Z = [float(a) for a in _L2]
_U2, _V2 = _basis(_L2)
U2X, U2Y, U2Z = [float(a) for a in _U2]; V2X, V2Y, V2Z = [float(a) for a in _V2]
_L3 = _nrm(_cfg['L3']); L3X, L3Y, L3Z = [float(a) for a in _L3]
_U3, _V3 = _basis(_L3)
U3X, U3Y, U3Z = [float(a) for a in _U3]; V3X, V3Y, V3Z = [float(a) for a in _V3]
C3R, C3G, C3B = [float(a) for a in _cfg['C3']]
_L4 = _nrm(_cfg['L4']); L4X, L4Y, L4Z = [float(a) for a in _L4]
_U4, _V4 = _basis(_L4)
U4X, U4Y, U4Z = [float(a) for a in _U4]; V4X, V4Y, V4Z = [float(a) for a in _V4]
C4R, C4G, C4B = [float(a) for a in _cfg['C4']]
KI = float(_cfg['KI']); KA = float(_cfg['KA']); ALPHA = float(_cfg['ALPHA'])
SB = float(_cfg['SB']); SB2 = float(_cfg['SB2'])
BEND = float(_cfg['BEND']); EXPO = float(_cfg['EXPO']); F0F = float(_cfg['F0F'])
BLOOM = float(_cfg['BLOOM'])
ER_, EG_, EB_ = _cfg['EARLY']; LR_, LG_, LB_ = _cfg['LATE']
MR = 0.1
MX0 = -40.0; MY0 = -60.0
NMX = 800; NMY = 1300
NBR = float(S.NBR)
GCS = 2.6; GX0 = -40.0; GY0 = -60.0; GNX = 33; GNY = 51


@nb.njit(cache=False, inline='always')
def surf_h(r):
    e = math.exp(-(r / SIG) ** 2)
    return S0 * r + 0.5 * S1 * r * r - DEP * e


@nb.njit(cache=False, inline='always')
def surf_s(r):
    e = math.exp(-(r / SIG) ** 2)
    return S0 + S1 * r + 2.0 * DEP * r / (SIG * SIG) * e


ZRIM = S0 * RH + 0.5 * S1 * RH * RH - DEP * math.exp(-(RH / SIG) ** 2)
ZBOT = ZRIM - 14.0


@nb.njit(cache=False, inline='always')
def smoothstep(a, b, x):
    t = (x - a) / (b - a)
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    return t * t * (3.0 - 2.0 * t)


@nb.njit(cache=False, inline='always')
def pixel_ray(cam, px, py):
    sx = (px - W * 0.5) / cam[12]
    sy = (H * 0.5 - py) / cam[12]
    dx = cam[3] + sx * cam[6] + sy * cam[9]
    dy = cam[4] + sx * cam[7] + sy * cam[10]
    dz = cam[5] + sx * cam[8] + sy * cam[11]
    n = math.sqrt(dx * dx + dy * dy + dz * dz)
    return dx / n, dy / n, dz / n


@nb.njit(cache=False, inline='always')
def project(cam, x, y, z):
    vx = x - cam[0]; vy = y - cam[1]; vz = z - cam[2]
    zc = vx * cam[3] + vy * cam[4] + vz * cam[5]
    xc = vx * cam[6] + vy * cam[7] + vz * cam[8]
    yc = vx * cam[9] + vy * cam[10] + vz * cam[11]
    return W * 0.5 + xc / zc * cam[12], H * 0.5 - yc / zc * cam[12], zc


@nb.njit(cache=False)
def floor_trace(ox, oy, oz, dx, dy, dz):
    if dz > -1e-4:
        return 1e9, 3
    trim = (ZRIM - oz) / dz
    qx = ox + trim * dx; qy = oy + trim * dy
    if trim > 0.0 and qx * qx + qy * qy < RH * RH:
        A = dx * dx + dy * dy
        B = 2.0 * (ox * dx + oy * dy)
        C = ox * ox + oy * oy - RH * RH
        disc = B * B - 4.0 * A * C
        if A < 1e-12 or disc < 0.0:
            tw = 1e9
        else:
            tw = (-B + math.sqrt(disc)) / (2.0 * A)
        zw = oz + tw * dz
        if zw > ZBOT:
            return tw, 1
        return (ZBOT - oz) / dz, 2
    t = (0.0 - oz) / dz
    for k in range(16):
        px = ox + t * dx; py = oy + t * dy; pz = oz + t * dz
        r = math.sqrt(px * px + py * py) + 1e-9
        rr = r if r > RH else RH
        f = pz - surf_h(rr)
        s = surf_s(rr)
        fp = dz - s * (px * dx + py * dy) / r
        if fp > -0.04:
            fp = -0.04
        dt = f / fp
        t = t - dt
        if abs(dt) < 1e-5:
            break
    return t, 0


@nb.njit(cache=False, inline='always')
def fade(t):
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


@nb.njit(cache=False, inline='always')
def grad(h, x, y):
    h = h & 7
    if h == 0:
        return x + y
    elif h == 1:
        return x - y
    elif h == 2:
        return -x + y
    elif h == 3:
        return -x - y
    elif h == 4:
        return 1.4142 * x
    elif h == 5:
        return -1.4142 * x
    elif h == 6:
        return 1.4142 * y
    return -1.4142 * y


@nb.njit(cache=False)
def perlin(x, y, perm):
    fx = math.floor(x); fy = math.floor(y)
    xi = int(fx) & 255; yi = int(fy) & 255
    xf = x - fx; yf = y - fy
    u = fade(xf); v = fade(yf)
    aa = perm[perm[xi] + yi]; ab = perm[perm[xi] + yi + 1]
    ba = perm[perm[xi + 1] + yi]; bb = perm[perm[xi + 1] + yi + 1]
    x1 = grad(aa, xf, yf) + u * (grad(ba, xf - 1.0, yf) - grad(aa, xf, yf))
    x2 = grad(ab, xf, yf - 1.0) + u * (grad(bb, xf - 1.0, yf - 1.0) - grad(ab, xf, yf - 1.0))
    return 0.7 * (x1 + v * (x2 - x1))


@nb.njit(cache=False, inline='always')
def aa_line(n, w, g, fp):
    ww = 1.2 * fp * g
    if ww < w:
        ww = w
    return (1.0 - smoothstep(0.0, ww, abs(n))) * (w / ww)


@nb.njit(cache=False)
def wood(u, v, fp, perm):
    PW = 17.0
    s = (u + 1003.0) / PW
    kf_ = math.floor(s)
    lu = (s - kf_ - 0.5) * PW
    ki = int(kf_)
    if (ki & 1) == 1:
        lu = -lu
    o = (ki % 7) * 13.7 + 2.3
    w1 = perlin(u * 0.05 + 3.3, v * 0.012 + 1.7, perm)
    w2 = perlin(u * 0.21 + 9.1, v * 0.05 + 4.4, perm)
    uu = lu + 1.1 * w1 + 0.3 * w2
    dp = 5.0 + 3.8 * (0.5 + 0.5 * math.sin(v * 0.052 + o)) + 1.4 * perlin(v * 0.02 + o, 0.37, perm)
    r = math.sqrt(uu * uu + dp * dp)
    ring = r * 1.3 + 0.22 * perlin(uu * 0.5 + o, v * 0.07, perm) + 0.07 * perlin(uu * 2.1, v * 0.3 + o, perm)
    rt = ring - math.floor(ring)
    lw = smoothstep(0.50, 0.80, rt) * (1.0 - smoothstep(0.88, 1.0, rt))
    gr = 1.3 * abs(uu) / r + 0.06
    aa = smoothstep(0.38, 0.14, fp * gr)
    lw = lw * aa + 0.32 * (1.0 - aa)
    kf = smoothstep(0.10, 0.04, fp)
    fib = 0.0
    if kf > 0.0:
        fib = perlin(u * 7.0 + o, v * 0.25, perm) * kf
    kp = smoothstep(0.03, 0.012, fp)
    pore = 0.0
    if kp > 0.0:
        pn = perlin(u * 22.0 + 3.1, v * 1.6 + 7.3, perm)
        pore = smoothstep(0.30, 0.45, pn) * kp
    tone = 0.5 + 0.5 * perlin(u * 0.08 + o, v * 0.015 + 2.0, perm)
    m = 0.72 * lw
    k = (0.86 + 0.26 * tone) * (1.0 + 0.07 * fib) * (1.0 - 0.35 * pore)
    return (ER_ + (LR_ - ER_) * m) * k, (EG_ + (LG_ - EG_) * m) * k, (EB_ + (LB_ - EB_) * m) * k


@nb.njit(cache=False, inline='always')
def tex_coords(x, y, z, kind):
    r = math.sqrt(x * x + y * y) + 1e-9
    if kind == 0:
        m = 1.0 + BEND * math.exp(-(r / SIG) ** 2)
        return x * m, y * m
    mr = 1.0 + BEND * math.exp(-(RH / SIG) ** 2)
    rr = RH * mr + (ZRIM - z)
    return x / r * rr, y / r * rr


@nb.njit(cache=False, inline='always')
def ao_static(r):
    q = (r - RH) / 2.2
    if q < 0.0:
        q = 0.0
    return 1.0 - 0.88 * math.exp(-q ** 1.6)


@nb.njit(cache=False)
def static_light(x, y, z, kind):
    r = math.sqrt(x * x + y * y) + 1e-9
    if kind == 0:
        s = surf_s(max(r, RH))
        nx = -s * x / r; ny = -s * y / r; nz = 1.0
        nn = math.sqrt(nx * nx + ny * ny + 1.0)
        nx /= nn; ny /= nn; nz /= nn
        ao = ao_static(r)
        ndl = nx * LX + ny * LY + nz * LZ
        if ndl < 0.0:
            ndl = 0.0
        rim = smoothstep(RH, RH + 1.3, r)
        return KA * ao, KI * ndl * (0.12 + 0.88 * rim * rim) * (0.35 + 0.65 * ao), ao
    if kind == 1:
        dd = ZRIM - z
        ao = 0.12 * math.exp(-dd / 1.4)
        nx = -x / r; ny = -y / r
        lit = 0.0
        ndl = nx * LX + ny * LY
        if ndl > 0.0:
            A = LX * LX + LY * LY
            B = 2.0 * (x * LX + y * LY)
            C = x * x + y * y - RH * RH
            disc = B * B - 4.0 * A * C
            if disc > 0.0 and A > 1e-9:
                sx = (-B + math.sqrt(disc)) / (2.0 * A)
                ze = z + sx * LZ
                lit = smoothstep(ZRIM - 0.3, ZRIM + 0.3, ze)
        return KA * ao, KI * ndl * lit * 0.8, ao
    return KA * 0.006, 0.0, 0.0


@nb.njit(cache=False, parallel=True)
def precompute_world(perm):
    A = np.zeros((NMY, NMX, 3), np.float32)
    D = np.zeros((NMY, NMX, 3), np.float32)
    for j in nb.prange(NMY):
        for i in range(NMX):
            sa0 = 0.0; sa1 = 0.0; sa2 = 0.0; sd0 = 0.0; sd1 = 0.0; sd2 = 0.0
            for sj in range(2):
                for si in range(2):
                    x = MX0 + (i + 0.25 + 0.5 * si) * MR
                    y = MY0 + (j + 0.25 + 0.5 * sj) * MR
                    r = math.sqrt(x * x + y * y)
                    if r < RH:
                        sa0 += 0.0015; sa1 += 0.001; sa2 += 0.0008
                        continue
                    z = surf_h(r)
                    u, v = tex_coords(x, y, z, 0)
                    ar, ag, ab = wood(u, v, 0.05, perm)
                    a, d, ao = static_light(x, y, z, 0)
                    sa0 += ar * a; sa1 += ag * a; sa2 += ab * a
                    sd0 += ar * d; sd1 += ag * d; sd2 += ab * d
            A[j, i, 0] = sa0 * 0.25; A[j, i, 1] = sa1 * 0.25; A[j, i, 2] = sa2 * 0.25
            D[j, i, 0] = sd0 * 0.25; D[j, i, 1] = sd1 * 0.25; D[j, i, 2] = sd2 * 0.25
    return A, D


@nb.njit(cache=False, inline='always')
def map_lookup(M, x, y):
    fx = (x - MX0) / MR - 0.5
    fy = (y - MY0) / MR - 0.5
    if fx < 0.0 or fy < 0.0 or fx > NMX - 1.001 or fy > NMY - 1.001:
        return 1.0
    i = int(fx); j = int(fy)
    ax = fx - i; ay = fy - j
    return (M[j, i] * (1 - ax) * (1 - ay) + M[j, i + 1] * ax * (1 - ay) +
            M[j + 1, i] * (1 - ax) * ay + M[j + 1, i + 1] * ax * ay)


@nb.njit(cache=False, inline='always')
def map_lookup3(M, x, y, c):
    fx = (x - MX0) / MR - 0.5
    fy = (y - MY0) / MR - 0.5
    if fx < 0.0:
        fx = 0.0
    if fy < 0.0:
        fy = 0.0
    if fx > NMX - 1.001:
        fx = NMX - 1.001
    if fy > NMY - 1.001:
        fy = NMY - 1.001
    i = int(fx); j = int(fy)
    ax = fx - i; ay = fy - j
    return (M[j, i, c] * (1 - ax) * (1 - ay) + M[j, i + 1, c] * ax * (1 - ay) +
            M[j + 1, i, c] * (1 - ax) * ay + M[j + 1, i + 1, c] * ax * ay)


@nb.njit(cache=False)
def dyn_maps(bx, by, bz, act, aod, shd):
    aod[:, :] = 1.0
    shd[:, :] = 1.0
    for b in range(bx.shape[0]):
        if not act[b]:
            continue
        cx = bx[b]; cy = by[b]; cz = bz[b]
        rb = math.sqrt(cx * cx + cy * cy)
        hb = surf_h(max(rb, RH))
        hgt = cz - hb
        if hgt > 6.0:
            continue
        ox = -hgt * LX / LZ; oy = -hgt * LY / LZ
        rad = 2.9
        x0 = min(cx, cx + ox) - rad; x1 = max(cx, cx + ox) + rad
        y0 = min(cy, cy + oy) - rad; y1 = max(cy, cy + oy) + rad
        i0 = max(int((x0 - MX0) / MR), 0); i1 = min(int((x1 - MX0) / MR) + 1, NMX)
        j0 = max(int((y0 - MY0) / MR), 0); j1 = min(int((y1 - MY0) / MR) + 1, NMY)
        for j in range(j0, j1):
            y = MY0 + (j + 0.5) * MR
            for i in range(i0, i1):
                x = MX0 + (i + 0.5) * MR
                r = math.sqrt(x * x + y * y) + 1e-9
                if r < RH:
                    continue
                z = surf_h(r)
                vx = cx - x; vy = cy - y; vz = cz - z
                d2 = vx * vx + vy * vy + vz * vz
                if d2 > 8.4:
                    continue
                d = math.sqrt(d2)
                s = surf_s(r)
                nx = -s * x / r; ny = -s * y / r; nz = 1.0
                nn = math.sqrt(nx * nx + ny * ny + 1.0)
                cosn = (nx * vx + ny * vy + nz * vz) / (nn * d)
                if cosn > 0.0:
                    occ = (R * R / d2) * cosn
                    if occ > 1.0:
                        occ = 1.0
                    aod[j, i] *= 1.0 - 0.9 * occ
                sr = R / d
                if sr > 0.999:
                    sr = 0.999
                beta = math.asin(sr)
                cg = (vx * LX + vy * LY + vz * LZ) / d
                if cg > 1.0:
                    cg = 1.0
                if cg < -1.0:
                    cg = -1.0
                gam = math.acos(cg)
                if gam < beta + ALPHA:
                    so = (beta + ALPHA - gam) / (2.0 * ALPHA)
                    if so > 1.0:
                        so = 1.0
                    q = beta / ALPHA
                    if q < 1.0:
                        so *= q * q
                    shd[j, i] *= 1.0 - so * 0.92


@nb.njit(cache=False, inline='always')
def strip(dx, dy, dz, lx, ly, lz, ux, uy, uz, vx, vy, vz, wu, wv, rough):
    c = dx * lx + dy * ly + dz * lz
    if c < 0.2:
        return 0.0
    u = (dx * ux + dy * uy + dz * uz) / c
    v = (dx * vx + dy * vy + dz * vz) / c
    if rough > 0.5:
        return 0.3 * math.exp(-(u * u) / (wu * wu * 1.5) - (v * v) / (wv * wv * 9.0 + 0.02))
    return smoothstep(wu, wu * 0.8, abs(u)) * smoothstep(wv, wv * 0.6, abs(v))


@nb.njit(cache=False)
def env_sky(dx, dy, dz, rough):
    if dz < 0.0:
        dz = 0.0
    t = smoothstep(0.0, 0.7, dz)
    if rough > 0.5:
        r = 0.10 + 0.30 * t; g = 0.10 + 0.31 * t; b = 0.11 + 0.34 * t
    else:
        r = 0.28 + (1.25 - 0.28) * t
        g = 0.28 + (1.31 - 0.28) * t
        b = 0.30 + (1.42 - 0.30) * t
    band = 1.0 - smoothstep(0.0, 0.16 + 0.25 * rough, dz)
    r = r + (0.06 - r) * band * 0.9
    g = g + (0.056 - g) * band * 0.9
    b = b + (0.06 - b) * band * 0.9
    if rough < 0.5:
        st = smoothstep(0.30, 0.22, abs(dz - 0.42)) * smoothstep(0.1, 0.5, -dx * 0.8 + dy * 0.6)
        r -= 0.45 * st; g -= 0.45 * st; b -= 0.44 * st
    c = dx * LX + dy * LY + dz * LZ
    if c > 0.2:
        u = (dx * KUX + dy * KUY + dz * KUZ) / c
        v = (dx * KVX + dy * KVY + dz * KVZ) / c
        if rough < 0.5:
            box = smoothstep(0.62, 0.50, abs(u)) * smoothstep(0.42, 0.31, abs(v))
            k = SB * box + 1.2 * math.exp(-(u * u + v * v) / 0.5)
        else:
            k = SB * 0.18 * math.exp(-(u * u) / 0.45 - (v * v) / 0.3) + 0.35 * math.exp(-(u * u + v * v) / 1.2)
        r += k; g += k * 0.99; b += k * 0.97
    k2 = SB2 * strip(dx, dy, dz, L2X, L2Y, L2Z, U2X, U2Y, U2Z, V2X, V2Y, V2Z, 0.35, 0.7, rough)
    r += k2; g += k2; b += k2 * 1.02
    k3 = strip(dx, dy, dz, L3X, L3Y, L3Z, U3X, U3Y, U3Z, V3X, V3Y, V3Z, 1.1, 0.10, rough)
    r += C3R * k3; g += C3G * k3; b += C3B * k3
    k4 = strip(dx, dy, dz, L4X, L4Y, L4Z, U4X, U4Y, U4Z, V4X, V4Y, V4Z, 1.0, 0.09, rough)
    r += C4R * k4; g += C4G * k4; b += C4B * k4
    return r, g, b


@nb.njit(cache=False)
def floor_hit(px, py, pz, rx, ry, rz):
    r0 = math.sqrt(px * px + py * py)
    h0 = surf_h(max(r0, RH))
    t = (h0 - pz) / rz
    if t < 0.0:
        t = 0.0
    for k in range(4):
        qx = px + t * rx; qy = py + t * ry; qz = pz + t * rz
        rq = math.sqrt(qx * qx + qy * qy) + 1e-9
        rr = max(rq, RH)
        f = qz - surf_h(rr)
        s = surf_s(rr)
        fp = rz - s * (qx * rx + qy * ry) / rq
        if fp > -0.05:
            fp = -0.05
        t = t - f / fp
        if t < 0.0:
            t = 0.0
    return t


@nb.njit(cache=False)
def floor_color(qx, qy, MA, MD, aod, shd):
    rq = math.sqrt(qx * qx + qy * qy)
    if rq < RH:
        return 0.003, 0.002, 0.0015
    a = map_lookup(aod, qx, qy)
    s = map_lookup(shd, qx, qy)
    return (map_lookup3(MA, qx, qy, 0) * a + map_lookup3(MD, qx, qy, 0) * s,
            map_lookup3(MA, qx, qy, 1) * a + map_lookup3(MD, qx, qy, 1) * s,
            map_lookup3(MA, qx, qy, 2) * a + map_lookup3(MD, qx, qy, 2) * s)


@nb.njit(cache=False)
def env_or_floor(px, py, pz, rx, ry, rz, MA, MD, aod, shd):
    if rz < -0.004:
        t = floor_hit(px, py, pz, rx, ry, rz)
        qx = px + t * rx; qy = py + t * ry
        fr, fg, fb = floor_color(qx, qy, MA, MD, aod, shd)
        fogk = smoothstep(30.0, 90.0, t)
        if fogk > 0.0:
            hr, hg, hb = env_sky(rx, ry, 0.0, 0.0)
            return fr + (hr - fr) * fogk, fg + (hg - fg) * fogk, fb + (hb - fb) * fogk
        return fr, fg, fb
    return env_sky(rx, ry, rz, 0.0)


@nb.njit(cache=False)
def ball_diffuse_light(px, py, pz, nx, ny, nz, self_b, bx, by, bz, nbs, nbi):
    ndl = nx * LX + ny * LY + nz * LZ
    sh = 1.0
    ao = 1.0
    for k in range(nbs[self_b], nbs[self_b + 1]):
        j = nbi[k]
        vx = bx[j] - px; vy = by[j] - py; vz = bz[j] - pz
        d2 = vx * vx + vy * vy + vz * vz
        d = math.sqrt(d2) + 1e-9
        cosn = (nx * vx + ny * vy + nz * vz) / d
        if cosn > 0.0:
            occ = (R * R / d2) * cosn
            if occ > 1.0:
                occ = 1.0
            ao *= 1.0 - 0.8 * occ
        if ndl > 0.0:
            sr = R / d
            if sr > 0.999:
                sr = 0.999
            beta = math.asin(sr)
            cg = (vx * LX + vy * LY + vz * LZ) / d
            if cg > 1.0:
                cg = 1.0
            if cg < -1.0:
                cg = -1.0
            gam = math.acos(cg)
            if gam < beta + ALPHA:
                so = (beta + ALPHA - gam) / (2.0 * ALPHA)
                if so > 1.0:
                    so = 1.0
                sh *= 1.0 - so
    if ndl < 0.0:
        ndl = 0.0
    fl = 0.5 - 0.5 * nz
    amb = KA * (0.62 + 0.38 * nz) * ao
    bounce = (KA + KI * 0.8) * 0.16 * fl * ao
    return amb + KI * ndl * sh, bounce


@nb.njit(cache=False)
def trace_reflection(self_b, px, py, pz, rx, ry, rz, bx, by, bz, btype, bcol, nbs, nbi, MA, MD, aod, shd):
    best = 1e9; bj = -1
    for k in range(nbs[self_b], nbs[self_b + 1]):
        j = nbi[k]
        ox = px - bx[j]; oy = py - by[j]; oz = pz - bz[j]
        b = ox * rx + oy * ry + oz * rz
        if b > 0.0:
            continue
        c = ox * ox + oy * oy + oz * oz - R * R
        disc = b * b - c
        if disc <= 0.0:
            continue
        t = -b - math.sqrt(disc)
        if t > 1e-4 and t < best:
            best = t; bj = j
    if bj >= 0:
        qx = px + best * rx; qy = py + best * ry; qz = pz + best * rz
        nx = (qx - bx[bj]); ny = (qy - by[bj]); nz = (qz - bz[bj])
        cs = -(rx * nx + ry * ny + rz * nz)
        r2x = rx + 2 * cs * nx; r2y = ry + 2 * cs * ny; r2z = rz + 2 * cs * nz
        er, eg, eb = env_or_floor(qx, qy, qz, r2x, r2y, r2z, MA, MD, aod, shd)
        if btype[bj] == 0:
            f = 0.6
            return er * f, eg * f, eb * f
        ndl = nx * LX + ny * LY + nz * LZ
        if ndl < 0.0:
            ndl = 0.0
        lt = (KA * (0.62 + 0.38 * nz) * 0.8 + KI * ndl) * 0.35
        fr = 0.05 + 0.95 * (1 - abs(cs)) ** 5
        return (bcol[bj, 0] * (lt + 0.45 * er) * (1 - fr) + er * fr,
                bcol[bj, 1] * (lt + 0.45 * eg) * (1 - fr) + eg * fr,
                bcol[bj, 2] * (lt + 0.45 * eb) * (1 - fr) + eb * fr)
    return env_or_floor(px, py, pz, rx, ry, rz, MA, MD, aod, shd)


@nb.njit(cache=False)
def shade_ball(b, hx, hy, hz, dx, dy, dz, bx, by, bz, btype, bcol, nbs, nbi, MA, MD, aod, shd, falling, lowq):
    nx = hx - bx[b]; ny = hy - by[b]; nz = hz - bz[b]
    nn = math.sqrt(nx * nx + ny * ny + nz * nz) + 1e-12
    nx /= nn; ny /= nn; nz /= nn
    cs = -(dx * nx + dy * ny + dz * nz)
    if cs < 0.0:
        cs = 0.0
    rx = dx + 2 * cs * nx; ry = dy + 2 * cs * ny; rz = dz + 2 * cs * nz
    if falling:
        up = smoothstep(0.55, 0.95, rz)
        er = 0.03 + 2.0 * up; eg = 0.025 + 2.0 * up; eb = 0.02 + 2.0 * up
        if btype[b] == 0:
            return er * 0.66, eg * 0.645, eb * 0.63
        lt = 0.05 + 1.5 * up
        fr = 0.045 + 0.955 * (1 - cs) ** 5
        return (bcol[b, 0] * lt * (1 - fr) + er * fr, bcol[b, 1] * lt * (1 - fr) + eg * fr, bcol[b, 2] * lt * (1 - fr) + eb * fr)
    if lowq:
        er, eg, eb = env_or_floor(hx, hy, hz, rx, ry, rz, MA, MD, aod, shd)
        if rz > -0.004 and rz < 0.35:
            er *= 0.55; eg *= 0.55; eb *= 0.55
    else:
        er, eg, eb = trace_reflection(b, hx + nx * 1e-3, hy + ny * 1e-3, hz + nz * 1e-3, rx, ry, rz,
                                      bx, by, bz, btype, bcol, nbs, nbi, MA, MD, aod, shd)
    fk = (1 - cs) ** 5
    if btype[b] == 0:
        f0r = 0.68; f0g = 0.665; f0b = 0.66
        return er * (f0r + (1 - f0r) * fk), eg * (f0g + (1 - f0g) * fk), eb * (f0b + (1 - f0b) * fk)
    lt, bounce = ball_diffuse_light(hx, hy, hz, nx, ny, nz, b, bx, by, bz, nbs, nbi)
    fr = 0.05 + 0.95 * fk
    cr = bcol[b, 0]; cg = bcol[b, 1]; cb = bcol[b, 2]
    return ((cr * (lt * 0.62 + bounce * 0.6) + cr * er * 0.55) * (1 - fr) + er * fr,
            (cg * (lt * 0.62 + bounce * 0.4) + cg * eg * 0.55) * (1 - fr) + eg * fr,
            (cb * (lt * 0.62 + bounce * 0.3) + cb * eb * 0.55) * (1 - fr) + eb * fr)


@nb.njit(cache=False)
def build_grid(bx, by, act):
    n = bx.shape[0]
    head = np.full(GNX * GNY, -1, np.int64)
    nxt = np.full(n, -1, np.int64)
    for i in range(n):
        if act[i]:
            cx = int((bx[i] - GX0) / GCS); cy = int((by[i] - GY0) / GCS)
            if cx < 0 or cy < 0 or cx >= GNX or cy >= GNY:
                continue
            c = cy * GNX + cx
            nxt[i] = head[c]; head[c] = i
    return head, nxt


@nb.njit(cache=False)
def neighbor_lists(bx, by, bz, act, head, nxt, rad):
    n = bx.shape[0]
    nbs = np.zeros(n + 1, np.int64)
    tmp = np.empty(n * 80, np.int64)
    cnt = 0
    reach = int(math.ceil(rad / GCS))
    r2 = rad * rad
    for i in range(n):
        nbs[i] = cnt
        if not act[i]:
            continue
        cx = int((bx[i] - GX0) / GCS); cy = int((by[i] - GY0) / GCS)
        for dy in range(-reach, reach + 1):
            for dx in range(-reach, reach + 1):
                ccx = cx + dx; ccy = cy + dy
                if ccx < 0 or ccy < 0 or ccx >= GNX or ccy >= GNY:
                    continue
                j = head[ccy * GNX + ccx]
                while j != -1:
                    if j != i:
                        ddx = bx[j] - bx[i]; ddy = by[j] - by[i]; ddz = bz[j] - bz[i]
                        if ddx * ddx + ddy * ddy + ddz * ddz < r2 and cnt < tmp.shape[0]:
                            tmp[cnt] = j
                            cnt += 1
                    j = nxt[j]
    nbs[n] = cnt
    return nbs, tmp[:cnt].copy()


@nb.njit(cache=False)
def floor_refl(x, y, z, rx, ry, rz, head, nxt, bx, by, bz, btype, bcol, MA, MD, aod, shd):
    rzz = rz if rz > 0.06 else 0.06
    tmax = 2.4 / rzz
    if tmax > 25.0:
        tmax = 25.0
    ex = x + rx * tmax; ey = y + ry * tmax
    x0 = min(x, ex) - 1.1; x1 = max(x, ex) + 1.1
    y0 = min(y, ey) - 1.1; y1 = max(y, ey) + 1.1
    i0 = int((x0 - GX0) / GCS); i1 = int((x1 - GX0) / GCS)
    j0 = int((y0 - GY0) / GCS); j1 = int((y1 - GY0) / GCS)
    if i0 < 0:
        i0 = 0
    if j0 < 0:
        j0 = 0
    if i1 >= GNX:
        i1 = GNX - 1
    if j1 >= GNY:
        j1 = GNY - 1
    best = 1e9; bj = -1
    for cj in range(j0, j1 + 1):
        for ci in range(i0, i1 + 1):
            b = head[cj * GNX + ci]
            while b != -1:
                ox = x - bx[b]; oy = y - by[b]; oz = z - bz[b]
                bb = ox * rx + oy * ry + oz * rz
                if bb < 0.0:
                    c = ox * ox + oy * oy + oz * oz - R * R
                    disc = bb * bb - c
                    if disc > 0.0:
                        t = -bb - math.sqrt(disc)
                        if t > 1e-4 and t < best:
                            best = t; bj = b
                b = nxt[b]
    if bj < 0:
        return env_sky(rx, ry, rz, 1.0)
    qx = x + best * rx; qy = y + best * ry; qz = z + best * rz
    nx = qx - bx[bj]; ny = qy - by[bj]; nz = qz - bz[bj]
    cs = -(rx * nx + ry * ny + rz * nz)
    r2x = rx + 2 * cs * nx; r2y = ry + 2 * cs * ny; r2z = rz + 2 * cs * nz
    if r2z < -0.004:
        t2 = floor_hit(qx, qy, qz, r2x, r2y, r2z)
        er, eg, eb = floor_color(qx + t2 * r2x, qy + t2 * r2y, MA, MD, aod, shd)
    else:
        er, eg, eb = env_sky(r2x, r2y, r2z, 1.0)
    if btype[bj] == 0:
        return er * 0.66, eg * 0.65, eb * 0.64
    ndl = nx * LX + ny * LY + nz * LZ
    if ndl < 0.0:
        ndl = 0.0
    lt = KA * (0.6 + 0.4 * nz) + KI * ndl
    return (bcol[bj, 0] * (lt * 0.5 + er * 0.4) + 0.05 * er,
            bcol[bj, 1] * (lt * 0.5 + eg * 0.4) + 0.05 * eg,
            bcol[bj, 2] * (lt * 0.5 + eb * 0.4) + 0.05 * eb)


@nb.njit(cache=False, parallel=True)
def floor_static(cam, perm, C_pos, C_dir, C_A, C_D, C_F, C_env, C_kind, zcam0, tray):
    pixang = 1.0 / cam[12]
    for py in nb.prange(H):
        for px in range(W):
            dx, dy, dz = pixel_ray(cam, px + 0.5, py + 0.5)
            t, k = floor_trace(cam[0], cam[1], cam[2], dx, dy, dz)
            tray[py, px] = t
            zcam0[py, px] = t * (dx * cam[3] + dy * cam[4] + dz * cam[5])
            C_kind[py, px] = k
            if k == 3:
                hr, hg, hb = env_sky(dx, dy, 0.0, 1.0)
                C_A[py, px, 0] = hr; C_A[py, px, 1] = hg; C_A[py, px, 2] = hb
                C_D[py, px, 0] = 0.0; C_D[py, px, 1] = 0.0; C_D[py, px, 2] = 0.0
                C_F[py, px, 0] = 0.0; C_F[py, px, 1] = 1.0
                continue
            x = cam[0] + t * dx; y = cam[1] + t * dy; z = cam[2] + t * dz
            C_pos[py, px, 0] = x; C_pos[py, px, 1] = y; C_pos[py, px, 2] = z
            r = math.sqrt(x * x + y * y) + 1e-9
            if k == 0:
                s = surf_s(max(r, RH))
                nx = -s * x / r; ny = -s * y / r; nz = 1.0
                nn = math.sqrt(nx * nx + ny * ny + 1.0)
                nx /= nn; ny /= nn; nz /= nn
                cosv = -(dx * nx + dy * ny + dz * nz)
                if cosv < 0.05:
                    cosv = 0.05
                fp = t * pixang / cosv
                u, v = tex_coords(x, y, z, 0)
                ar, ag, ab = wood(u, v, fp, perm)
                a, d, ao = static_light(x, y, z, 0)
                C_A[py, px, 0] = ar * a; C_A[py, px, 1] = ag * a; C_A[py, px, 2] = ab * a
                C_D[py, px, 0] = ar * d; C_D[py, px, 1] = ag * d; C_D[py, px, 2] = ab * d
                rx = dx + 2 * cosv * nx; ry = dy + 2 * cosv * ny; rz = dz + 2 * cosv * nz
                C_dir[py, px, 0] = rx; C_dir[py, px, 1] = ry; C_dir[py, px, 2] = rz
                C_F[py, px, 0] = F0F + (1 - F0F) * (1 - cosv) ** 5
                C_F[py, px, 1] = ao
                er, eg, eb = env_sky(rx, ry, rz, 1.0)
                C_env[py, px, 0] = er; C_env[py, px, 1] = eg; C_env[py, px, 2] = eb
            else:
                u, v = tex_coords(x, y, z, k)
                ar, ag, ab = wood(u, v, 0.05, perm)
                a, d, ao = static_light(x, y, z, k)
                C_A[py, px, 0] = ar * (a + d); C_A[py, px, 1] = ag * (a + d); C_A[py, px, 2] = ab * (a + d)
                C_D[py, px, 0] = 0.0; C_D[py, px, 1] = 0.0; C_D[py, px, 2] = 0.0
                C_F[py, px, 0] = 0.0; C_F[py, px, 1] = 1.0


@nb.njit(cache=False, parallel=True)
def floor_dynamic(C_pos, C_dir, C_A, C_D, C_F, C_env, C_kind, aod, shd, MA, MD, head, nxt, bx, by, bz, btype, bcol, img):
    for py in nb.prange(H):
        for px in range(W):
            k = C_kind[py, px]
            if k != 0:
                for c in range(3):
                    img[py, px, c] = C_A[py, px, c]
                continue
            x = C_pos[py, px, 0]; y = C_pos[py, px, 1]; z = C_pos[py, px, 2]
            aa = map_lookup(aod, x, y); ss = map_lookup(shd, x, y)
            F = C_F[py, px, 0]
            so = math.sqrt(C_F[py, px, 1] * aa)
            rx = C_dir[py, px, 0]; ry = C_dir[py, px, 1]; rz = C_dir[py, px, 2]
            rzz = rz if rz > 0.06 else 0.06
            tmax = 2.4 / rzz
            if tmax > 25.0:
                tmax = 25.0
            ex = x + rx * tmax; ey = y + ry * tmax
            i0 = int((min(x, ex) - 1.1 - GX0) / GCS); i1 = int((max(x, ex) + 1.1 - GX0) / GCS)
            j0 = int((min(y, ey) - 1.1 - GY0) / GCS); j1 = int((max(y, ey) + 1.1 - GY0) / GCS)
            if i0 < 0:
                i0 = 0
            if j0 < 0:
                j0 = 0
            if i1 >= GNX:
                i1 = GNX - 1
            if j1 >= GNY:
                j1 = GNY - 1
            anyb = False
            for cj in range(j0, j1 + 1):
                for ci in range(i0, i1 + 1):
                    if head[cj * GNX + ci] != -1:
                        anyb = True
            if anyb:
                er, eg, eb = floor_refl(x, y, z, rx, ry, rz, head, nxt, bx, by, bz, btype, bcol, MA, MD, aod, shd)
            else:
                er = C_env[py, px, 0]; eg = C_env[py, px, 1]; eb = C_env[py, px, 2]
            for c in range(3):
                base = C_A[py, px, c] * aa + C_D[py, px, c] * ss
                e = er if c == 0 else (eg if c == 1 else eb)
                img[py, px, c] = base * (1 - F) + e * F * so


@nb.njit(cache=False)
def draw_ball(cam, b, cx, cy, cz, offs, bx, by, bz, btype, bcol, nbs, nbi, MA, MD, aod, shd,
              img, tray, zcam, ztest, dark, spr, lowq):
    pxc, pyc, dep = project(cam, cx, cy, cz)
    if dep < 1.0:
        return
    rp = R * cam[12] / dep
    pad = 2
    x0 = int(math.floor(pxc - rp)) - pad; x1 = int(math.ceil(pxc + rp)) + pad
    y0 = int(math.floor(pyc - rp)) - pad; y1 = int(math.ceil(pyc + rp)) + pad
    mo = 0.0
    for k in range(offs.shape[0]):
        mo = max(mo, abs(offs[k, 0]), abs(offs[k, 1]))
    if x1 + mo < 0 or y1 + mo < 0 or x0 - mo >= W or y0 - mo >= H:
        return
    if x0 < -int(mo) - 4:
        x0 = -int(mo) - 4
    if y0 < -int(mo) - 4:
        y0 = -int(mo) - 4
    if x1 > W + int(mo) + 4:
        x1 = W + int(mo) + 4
    if y1 > H + int(mo) + 4:
        y1 = H + int(mo) + 4
    sw = x1 - x0; sh = y1 - y0
    if sw > spr.shape[1] or sh > spr.shape[0]:
        return
    spr[:sh, :sw, :] = 0.0
    any_vis = False
    for yy in range(sh):
        py = y0 + yy
        for xx in range(sw):
            px = x0 + xx
            dx, dy, dz = pixel_ray(cam, px + 0.5, py + 0.5)
            ox = cam[0] - cx; oy = cam[1] - cy; oz = cam[2] - cz
            bb = ox * dx + oy * dy + oz * dz
            oo = ox * ox + oy * oy + oz * oz
            perp2 = oo - bb * bb
            if perp2 < 0.0:
                perp2 = 0.0
            perp = math.sqrt(perp2)
            tcl = -bb
            foot = tcl / cam[12]
            cov = (R - perp) / foot + 0.5
            if cov <= 0.0:
                continue
            if cov > 1.0:
                cov = 1.0
            if perp < R * 0.9995:
                t = tcl - math.sqrt(R * R - perp2)
            else:
                t = tcl
            if ztest:
                if px < 0 or py < 0 or px >= W or py >= H:
                    continue
                if t > tray[py, px]:
                    continue
            hx = cam[0] + t * dx; hy = cam[1] + t * dy; hz = cam[2] + t * dz
            if perp >= R * 0.9995:
                qx = hx - cx; qy = hy - cy; qz = hz - cz
                qn = math.sqrt(qx * qx + qy * qy + qz * qz) + 1e-12
                hx = cx + qx / qn * R * 0.9995; hy = cy + qy / qn * R * 0.9995; hz = cz + qz / qn * R * 0.9995
            r_, g_, b_ = shade_ball(b, hx, hy, hz, dx, dy, dz, bx, by, bz, btype, bcol, nbs, nbi, MA, MD, aod, shd, ztest, lowq)
            spr[yy, xx, 0] = r_ * dark * cov
            spr[yy, xx, 1] = g_ * dark * cov
            spr[yy, xx, 2] = b_ * dark * cov
            spr[yy, xx, 3] = cov
            any_vis = True
    if not any_vis:
        return
    zb = dep
    nk = offs.shape[0]
    if nk <= 1:
        for yy in range(sh):
            py = y0 + yy
            if py < 0 or py >= H:
                continue
            for xx in range(sw):
                px = x0 + xx
                if px < 0 or px >= W:
                    continue
                a = spr[yy, xx, 3]
                if a <= 0.0:
                    continue
                for c in range(3):
                    img[py, px, c] = img[py, px, c] * (1 - a) + spr[yy, xx, c]
                if a > 0.5 and zb < zcam[py, px]:
                    zcam[py, px] = zb
        return
    mxo = 0.0; mno = 0.0; myo = 0.0; mny = 0.0
    for k in range(nk):
        mxo = max(mxo, offs[k, 0]); mno = min(mno, offs[k, 0])
        myo = max(myo, offs[k, 1]); mny = min(mny, offs[k, 1])
    ax0 = x0 + int(math.floor(mno)) - 1; ay0 = y0 + int(math.floor(mny)) - 1
    aw = sw + int(math.ceil(mxo) - math.floor(mno)) + 3
    ah = sh + int(math.ceil(myo) - math.floor(mny)) + 3
    acc = np.zeros((ah, aw, 4), np.float32)
    wk = 1.0 / nk
    for k in range(nk):
        ofx = offs[k, 0]; ofy = offs[k, 1]
        fx0 = math.floor(ofx); fy0 = math.floor(ofy)
        ax = ofx - fx0; ay = ofy - fy0
        w00 = (1 - ax) * (1 - ay) * wk; w10 = ax * (1 - ay) * wk
        w01 = (1 - ax) * ay * wk; w11 = ax * ay * wk
        bxo = x0 + int(fx0) - ax0; byo = y0 + int(fy0) - ay0
        for yy in range(sh):
            for xx in range(sw):
                a = spr[yy, xx, 3]
                if a <= 0.0:
                    continue
                tx = bxo + xx; ty = byo + yy
                for c in range(4):
                    v = spr[yy, xx, c]
                    acc[ty, tx, c] += v * w00
                    acc[ty, tx + 1, c] += v * w10
                    acc[ty + 1, tx, c] += v * w01
                    acc[ty + 1, tx + 1, c] += v * w11
    for yy in range(ah):
        py = ay0 + yy
        if py < 0 or py >= H:
            continue
        for xx in range(aw):
            px = ax0 + xx
            if px < 0 or px >= W:
                continue
            a = acc[yy, xx, 3]
            if a <= 0.0:
                continue
            if a > 1.0:
                s = 1.0 / a
                for c in range(4):
                    acc[yy, xx, c] *= s
                a = 1.0
            for c in range(3):
                img[py, px, c] = img[py, px, c] * (1 - a) + acc[yy, xx, c]
            if a > 0.5 and zb < zcam[py, px]:
                zcam[py, px] = zb


def _spiral(n):
    k = np.arange(n) + 0.5
    r = np.sqrt(k / n)
    th = k * 2.399963
    return (r * np.cos(th)).astype(np.float64), (r * np.sin(th)).astype(np.float64)


SPX, SPY = _spiral(56)


@nb.njit(cache=False, parallel=True)
def dof(img, zc, zf, kd, spx, spy, out):
    h2 = H // 2; w2 = W // 2
    col = np.empty((h2, w2, 3), np.float32)
    coc = np.empty((h2, w2), np.float32)
    zz = np.empty((h2, w2), np.float32)
    for j in nb.prange(h2):
        for i in range(w2):
            zmin = 1e9
            for a in range(2):
                for b in range(2):
                    q = zc[2 * j + a, 2 * i + b]
                    if q < zmin:
                        zmin = q
            for c in range(3):
                col[j, i, c] = 0.25 * (img[2 * j, 2 * i, c] + img[2 * j + 1, 2 * i, c] + img[2 * j, 2 * i + 1, c] + img[2 * j + 1, 2 * i + 1, c])
            zz[j, i] = zmin
            coc[j, i] = 0.5 * kd * (zmin - zf) / zmin
    TS = 8
    th = (h2 + TS - 1) // TS; tw = (w2 + TS - 1) // TS
    tm = np.zeros((th, tw), np.float32)
    for j in range(h2):
        for i in range(w2):
            a = abs(coc[j, i])
            if a > tm[j // TS, i // TS]:
                tm[j // TS, i // TS] = a
    tm2 = np.zeros((th, tw), np.float32)
    for j in range(th):
        for i in range(tw):
            m = 0.0
            for a in range(-1, 2):
                for b in range(-1, 2):
                    jj = j + a; ii = i + b
                    if jj >= 0 and ii >= 0 and jj < th and ii < tw:
                        if tm[jj, ii] > m:
                            m = tm[jj, ii]
            tm2[j, i] = m
    blur = np.empty((h2, w2, 3), np.float32)
    alp = np.zeros((h2, w2), np.float32)
    ns = spx.shape[0]
    for j in nb.prange(h2):
        for i in range(w2):
            cp = coc[j, i]; acp = abs(cp)
            rs = max(acp, tm2[j // TS, i // TS])
            if rs < 0.6:
                for c in range(3):
                    blur[j, i, c] = col[j, i, c]
                continue
            w0 = 1.0 / max(acp * acp, 1.0)
            sr = col[j, i, 0] * w0; sg = col[j, i, 1] * w0; sb = col[j, i, 2] * w0; sw = w0
            fg = 0.0
            zp = zz[j, i]
            for k in range(ns):
                ox = spx[k] * rs; oy = spy[k] * rs
                qx = int(i + ox + 0.5); qy = int(j + oy + 0.5)
                if qx < 0:
                    qx = 0
                if qy < 0:
                    qy = 0
                if qx >= w2:
                    qx = w2 - 1
                if qy >= h2:
                    qy = h2 - 1
                dist = math.sqrt(ox * ox + oy * oy)
                cq = coc[qy, qx]; acq = abs(cq)
                w = acq - dist + 1.0
                if w <= 0.0:
                    continue
                if w > 1.0:
                    w = 1.0
                if zz[qy, qx] > zp:
                    wb = acp - dist + 1.0
                    if wb <= 0.0:
                        continue
                    if wb < 1.0:
                        w *= wb
                w /= max(acq * acq, 1.0)
                sr += col[qy, qx, 0] * w; sg += col[qy, qx, 1] * w; sb += col[qy, qx, 2] * w; sw += w
                if zz[qy, qx] < zp and acq > acp + 0.5:
                    fg += w
            blur[j, i, 0] = sr / sw; blur[j, i, 1] = sg / sw; blur[j, i, 2] = sb / sw
            alp[j, i] = min(1.0, 2.0 * fg / sw)
    for py in nb.prange(H):
        for px in range(W):
            z = zc[py, px]
            own = abs(kd * (z - zf) / z)
            fx = (px + 0.5) * 0.5 - 0.5; fy = (py + 0.5) * 0.5 - 0.5
            if fx < 0.0:
                fx = 0.0
            if fy < 0.0:
                fy = 0.0
            if fx > w2 - 1.001:
                fx = w2 - 1.001
            if fy > h2 - 1.001:
                fy = h2 - 1.001
            i0 = int(fx); j0 = int(fy); ax = fx - i0; ay = fy - j0
            a = (alp[j0, i0] * (1 - ax) * (1 - ay) + alp[j0, i0 + 1] * ax * (1 - ay) + alp[j0 + 1, i0] * (1 - ax) * ay + alp[j0 + 1, i0 + 1] * ax * ay)
            m = smoothstep(0.7, 2.2, own)
            if a > m:
                m = a
            for c in range(3):
                bv = (blur[j0, i0, c] * (1 - ax) * (1 - ay) + blur[j0, i0 + 1, c] * ax * (1 - ay) +
                      blur[j0 + 1, i0, c] * (1 - ax) * ay + blur[j0 + 1, i0 + 1, c] * ax * ay)
                out[py, px, c] = img[py, px, c] * (1 - m) + bv * m


@nb.njit(cache=False, parallel=True)
def tonemap(img, out, expo, vig, grain_seed):
    for py in nb.prange(H):
        for px in range(W):
            dxn = (px + 0.5) / W - 0.5
            dyn = (py + 0.5) / H - 0.5
            v = 1.0 - vig * (dxn * dxn * 1.6 + dyn * dyn * 0.9)
            hsh = (px * 73856093) ^ (py * 19349663) ^ (grain_seed * 83492791)
            hsh = (hsh ^ (hsh >> 13)) * 1274126177
            hsh = hsh ^ (hsh >> 16)
            gn = ((hsh & 1023) / 1023.0 - 0.5) * 0.012
            for c in range(3):
                x = img[py, px, c] * expo * v
                y = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)
                if y < 0.0:
                    y = 0.0
                if y > 1.0:
                    y = 1.0
                if y <= 0.0031308:
                    s = 12.92 * y
                else:
                    s = 1.055 * y ** (1 / 2.4) - 0.055
                s += gn
                if s < 0.0:
                    s = 0.0
                if s > 1.0:
                    s = 1.0
                out[py, px, c] = np.uint8(s * 255.0 + 0.5)


def make_cam(T, D, yaw, elev, hf):
    yaw = math.radians(yaw); e = math.radians(elev)
    f = np.array([math.sin(yaw) * math.cos(e), math.cos(yaw) * math.cos(e), -math.sin(e)])
    C = np.array(T, float) - D * f
    r = np.array([math.cos(yaw), -math.sin(yaw), 0.0])
    u = np.cross(r, f)
    return np.array([C[0], C[1], C[2], f[0], f[1], f[2], r[0], r[1], r[2], u[0], u[1], u[2], (W / 2) / hf], np.float64)


class Renderer:
    def __init__(self, cache_dir=None):
        cache_dir = cache_dir or os.path.join(S.BUILD, 'cache')
        os.makedirs(cache_dir, exist_ok=True)
        tag = hashlib.md5(json.dumps(_cfg, sort_keys=True).encode()).hexdigest()[:10]
        key = os.path.join(cache_dir, 'world_maps_%s.npz' % tag)
        perm = np.random.default_rng(int(_cfg['WOOD_SEED'])).permutation(256).astype(np.int64)
        self.perm = np.concatenate([perm, perm, perm[:2]])
        if os.path.exists(key):
            d = np.load(key)
            self.MA, self.MD = d['MA'], d['MD']
        else:
            self.MA, self.MD = precompute_world(self.perm)
            np.savez(key, MA=self.MA, MD=self.MD)
        self.aod = np.ones((NMY, NMX), np.float32)
        self.shd = np.ones((NMY, NMX), np.float32)
        self.img = np.zeros((H, W, 3), np.float32)
        self.img2 = np.zeros((H, W, 3), np.float32)
        self.zcam = np.zeros((H, W), np.float32)
        self.tray = np.zeros((H, W), np.float32)
        self.out = np.zeros((H, W, 3), np.uint8)
        self.spr = np.zeros((1000, 1000, 4), np.float32)
        self.C_pos = np.zeros((H, W, 3), np.float32); self.C_dir = np.zeros((H, W, 3), np.float32)
        self.C_A = np.zeros((H, W, 3), np.float32); self.C_D = np.zeros((H, W, 3), np.float32)
        self.C_F = np.zeros((H, W, 2), np.float32); self.C_env = np.zeros((H, W, 3), np.float32)
        self.C_kind = np.zeros((H, W), np.int8); self.zcam0 = np.zeros((H, W), np.float32)
        self.last_cam = None

    def frame(self, cam, bx, by, bz, state, btype, bcol, subs, kd=0.0, zf=100.0, grain_seed=0):
        act = (state == 1) | ((state == 2) & (bz > ZRIM - 3.0))
        dyn_maps(bx, by, bz, act, self.aod, self.shd)
        act1 = state == 1
        head, nxt = build_grid(bx, by, act1)
        if self.last_cam is None or not np.array_equal(self.last_cam, cam):
            floor_static(cam, self.perm, self.C_pos, self.C_dir, self.C_A, self.C_D, self.C_F, self.C_env, self.C_kind,
                         self.zcam0, self.tray)
            self.last_cam = cam.copy()
        floor_dynamic(self.C_pos, self.C_dir, self.C_A, self.C_D, self.C_F, self.C_env, self.C_kind, self.aod, self.shd,
                      self.MA, self.MD, head, nxt, bx, by, bz, btype, bcol, self.img)
        self.zcam[:] = self.zcam0
        nbs, nbi = neighbor_lists(bx, by, bz, act, *build_grid(bx, by, act), NBR)
        z0 = np.zeros((1, 2))
        for b in np.where(state == 2)[0]:
            dd = (ZRIM + 0.2) - bz[b]
            dark = float(np.exp(-max(dd, 0.0) / 1.1))
            if dark < 0.01:
                continue
            draw_ball(cam, b, bx[b], by[b], bz[b], z0, bx, by, bz, btype, bcol, nbs, nbi,
                      self.MA, self.MD, self.aod, self.shd, self.img, self.tray, self.zcam, True, dark, self.spr, False)
        idx = np.where(act1)[0]
        if len(idx):
            vx = bx[idx] - cam[0]; vy = by[idx] - cam[1]; vz = bz[idx] - cam[2]
            dep = vx * cam[3] + vy * cam[4] + vz * cam[5]
            idx = idx[np.argsort(-dep)]
        for b in idx:
            offs = subs[b] if (subs is not None and subs[b] is not None) else z0
            lowq = False
            if kd > 0.4:
                zb = (bx[b] - cam[0]) * cam[3] + (by[b] - cam[1]) * cam[4] + (bz[b] - cam[2]) * cam[5]
                coc = kd * abs(zb - zf) / max(zb, 1e-3)
                if coc > 7.0 and btype[b] == 0:
                    lowq = True
                    offs = z0
            draw_ball(cam, b, bx[b], by[b], bz[b], offs, bx, by, bz, btype, bcol, nbs, nbi,
                      self.MA, self.MD, self.aod, self.shd, self.img, self.tray, self.zcam, False, 1.0, self.spr, lowq)
        src = self.img
        if kd > 0.4:
            dof(self.img, self.zcam, zf, kd, SPX, SPY, self.img2)
            src = self.img2
        if BLOOM > 0:
            hi = np.maximum(src * EXPO - 0.9, 0.0).astype(np.float32)
            small = cv2.resize(hi, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
            b1 = cv2.GaussianBlur(small, (0, 0), 2.0)
            b2 = cv2.GaussianBlur(small, (0, 0), 8.0)
            bl = cv2.resize(b1 * 0.55 + b2 * 0.45, (W, H), interpolation=cv2.INTER_LINEAR)
            src = src + bl * (BLOOM / EXPO)
            src = np.ascontiguousarray(src, dtype=np.float32)
        tonemap(src, self.out, EXPO, float(_cfg['VIG']), grain_seed)
        return self.out
