"""The low-poly hooded man: faceless faceted head, fedora, black hoodie with drawstrings, sleeves, mannequin hands.

Every part is exported in the local frame of the node it hangs from (see rig.py):
  head node (pivot HEAD): head, neck, hat_crown, hat_band, hat_brim
  torso node (pivot HIPS): torso, hood, hood_bag, strings, aglets, pocket, hem
  arm nodes: upper_R/L (pivot shoulder, hanging along -Z), fore_R/L (pivot elbow), hand_<pose>_R/L (pivot wrist)
  legs (world, pivot 0)
"""
import math
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', 'shared', 'lowpoly-gl'))
import numpy as np
from meshkit import M, join, rotx, roty, rotz, box, loft, ring, cyl, uvsphere, tube, jitter, decimate, add
from rig import HIPS, HEAD, SHOULDER, UPPER, FORE, COLORS, HAND_POSES

# ------------------------------------------------------------------ settings
HEAD_RES = (52, 30)          # UV-sphere resolution before decimation
HEAD_RATIO = 0.17            # decimate ratio (about 520 faces)
SKULL_C = np.array([0.0, 0.004, 0.104])     # skull centre in head-local coords
SKULL_R = np.array([0.088, 0.104, 0.126])   # half sizes x (width), y (depth), z (height)
HAT_TILT = math.radians(-4)  # forward tilt of the hat (about X)
HAT_BASE = np.array([0.0, -0.002, 0.172])
TORSO_RATIO = 0.55


def head_mesh():
    """A calm mannequin head: egg-shaped skull, flat broad face, soft nose ridge, small chin. No brow ridge or eye
    sockets (they rendered as dark slanted facets that read as an angry frown)."""
    s = uvsphere(*HEAD_RES)
    d = s.v / np.linalg.norm(s.v, axis=1, keepdims=True)
    x, y, z = d.T
    X, Y, Z = x * SKULL_R[0], y * SKULL_R[1], z * SKULL_R[2]
    lo = np.clip(-z, 0, 1)
    X = X * (1 - 0.17 * lo ** 1.8)
    Y = np.where(y > 0, Y * (1 - 0.32 * lo ** 1.4), Y * (1 - 0.06 * lo))
    Y = np.where(y < 0, Y * 0.90, Y)
    front = np.clip(-y, 0, 1)
    chin = np.exp(-(x / 0.35) ** 2 - ((z + 0.80) / 0.18) ** 2) * front
    Y = Y - 0.006 * chin
    t = np.clip((0.06 - z) / 0.34, 0, 1)
    below = np.clip((-0.28 - z) / 0.08, 0, 1)
    prof = t ** 1.5 * (1 - below) ** 2
    nose = prof * np.exp(-(x / 0.16) ** 2) * front ** 4
    Y = Y - 0.012 * nose
    m = M(np.stack([X, Y, Z], 1) + SKULL_C, s.f)
    return decimate(m, HEAD_RATIO, True, 'head')


def hat_meshes():
    n = 16
    th = np.linspace(0, 2 * math.pi, n, endpoint=False) - math.pi / 2   # vertex 0 at the front (-Y)
    rx, ry = 0.087, 0.104

    def crown_ring(scale, h, pinch=0.0):
        x, y = rx * scale * np.cos(th), ry * scale * np.sin(th)
        if pinch:
            ang = (th + math.pi / 2 + math.pi) % (2 * math.pi) - math.pi     # 0 at the front
            pin = np.exp(-((np.abs(ang) - 0.55) / 0.28) ** 2)
            x, y = x * (1 - pinch * pin), y * (1 - 0.5 * pinch * pin)
        return np.stack([x, y, np.full(n, h)], 1)

    rings = [crown_ring(1.0, 0.0), crown_ring(0.975, 0.045, 0.06), crown_ring(0.90, 0.082, 0.16),
             crown_ring(0.76, 0.098, 0.24)]
    crown = loft(rings, cap0=False, cap1=False)
    c = len(crown.v)
    crown.v = np.vstack([crown.v, [0, 0.010, 0.080]])
    base = 3 * n
    crown.f = list(crown.f) + [(base + i, base + (i + 1) % n, c) for i in range(n)]
    band = loft([crown_ring(1.012, 0.003), crown_ring(1.008, 0.030)], False, False)
    ri = np.stack([rx * 0.98 * np.cos(th), ry * 0.98 * np.sin(th)], 1)
    cos2 = np.cos(th) ** 2
    ro1 = np.stack([0.118 * np.cos(th), 0.136 * np.sin(th)], 1)
    ro2 = np.stack([0.148 * np.cos(th), 0.170 * np.sin(th)], 1)
    front = np.clip(-np.sin(th), 0, 1)
    back = np.clip(np.sin(th), 0, 1)
    z1 = 0.006 * cos2 - 0.006 * front + 0.004 * back
    z2 = 0.022 * cos2 - 0.022 * front ** 2 + 0.014 * back ** 2 - 0.002
    top_rings = [np.column_stack([ri, np.zeros(n)]), np.column_stack([ro1, z1]), np.column_stack([ro2, z2])]
    th_b = 0.006
    bot_rings = [r - [0, 0, th_b] for r in top_rings]
    v = np.vstack(top_rings + bot_rings)
    f = []
    for r in range(2):
        for i in range(n):
            a, b = r * n + i, r * n + (i + 1) % n
            f.append((a, b, b + n, a + n))
            A, B = 3 * n + a, 3 * n + b
            f.append((A, A + n, B + n, B))
    for i in range(n):
        a, b = 2 * n + i, 2 * n + (i + 1) % n
        f.append((a, b, 3 * n + b, 3 * n + a))
        a, b = i, (i + 1) % n
        f.append((a, 3 * n + a, 3 * n + b, b))
    brim = M(v, f)
    R = rotx(HAT_TILT)
    return [m.rotated(R).moved(HAT_BASE) for m in (crown, band, brim)]


def torso_meshes():
    spec = [(0.905, 0.174, 0.118, 0.0, 2.6), (0.97, 0.177, 0.121, 0.0, 2.6), (1.10, 0.182, 0.125, 0.0, 2.6),
            (1.24, 0.194, 0.130, 0.004, 2.6), (1.33, 0.204, 0.128, 0.008, 2.8), (1.395, 0.212, 0.116, 0.012, 3.0),
            (1.445, 0.180, 0.104, 0.016, 2.6), (1.485, 0.135, 0.092, 0.018, 2.3), (1.515, 0.088, 0.076, 0.02, 2.0)]
    rings = [ring(22, hw, hd, z, p, yo, phase=-math.pi / 2) for z, hw, hd, yo, p in spec]
    torso = jitter(loft(rings, True, False), 0.0015, 3)
    torso = decimate(torso, TORSO_RATIO, True, 'torso')
    hem = loft([ring(22, 0.177, 0.121, 0.895, 2.6, 0, -math.pi / 2), ring(22, 0.179, 0.123, 0.955, 2.6, 0, -math.pi / 2)],
               False, False)
    # hood collar: a fat open torus around the neck, open at the front
    path, rad = [], []
    for k in range(24):
        phi = math.radians(-90 + 360 * k / 24)     # closed ring around the neck; -90 deg is the front (-Y)
        back = (math.sin(phi) + 1) / 2
        fr = 1 - back
        path.append((0.116 * math.cos(phi), 0.104 * math.sin(phi) + 0.016, 1.536 + 0.010 * back - 0.022 * fr ** 4))
        rad.append(0.033 + 0.027 * back ** 0.8)
    path.append(path[0])
    rad.append(rad[0])
    hood = tube(path, rad, 9, False)
    hood.v[:, 2] = 1.53 + (hood.v[:, 2] - 1.53) * 0.85
    hood = jitter(hood, 0.0012, 5)
    bag = uvsphere(12, 8, 1.0).scaled((0.155, 0.056, 0.115)).moved((0, 0.122, 1.445))
    bag.v[:, 1] += 0.02 * np.clip((bag.v[:, 2] - 1.445) / 0.11, 0, 1)
    bag = jitter(bag, 0.002, 7)
    strings, aglets = [], []
    for sx in (-1, 1):
        p = np.array([(0.030, -0.092, 1.500), (0.034, -0.114, 1.450), (0.037, -0.127, 1.388),
                      (0.039, -0.132, 1.325), (0.040, -0.133, 1.285)]) * [sx, 1, 1]
        strings.append(tube(p, 0.0055, 6))
        aglets.append(cyl(0.0068, 0.0062, 0.032, 6, 0).moved((sx * 0.040, -0.133, 1.253)))
    pocket = loft([ring(14, 0.13, 0.008, 0, 4, 0, -math.pi / 2) + [0, -0.128, 1.0],
                   ring(14, 0.12, 0.008, 0, 4, 0, -math.pi / 2) + [0, -0.130, 1.12]], True, True)
    return torso, hem, hood, bag, join(*strings), join(*aglets), pocket


def sleeve_meshes():
    up = cyl(0.057, 0.050, UPPER, 10, -UPPER, True)
    up.v[:, 2] = -up.v[:, 2] - UPPER    # flip so it hangs from z=0 down to -UPPER, wide end at the top
    up = M(up.v, [ff[::-1] for ff in up.f])
    cap = uvsphere(10, 6, 0.053).moved((0, 0, -0.018))
    upper = join(up, cap)
    fore = cyl(0.044, 0.049, FORE - 0.04, 10, -(FORE - 0.04), True)
    cuff = cyl(0.040, 0.042, 0.045, 10, -FORE, True)
    elbow = uvsphere(10, 6, 0.050)
    return jitter(upper, 0.001, 11), jitter(join(fore, elbow), 0.001, 12), cuff


def hand_mesh(pose, side):
    """Right hand at side 'R': wrist at the origin, fingers along -Z, palm facing +X, thumb toward -Y."""
    P = HAND_POSES[pose]
    parts = [box(0.026, 0.080, 0.088, (0.0, 0.0, -0.049))]
    parts[0].v[:, 0] *= np.where(parts[0].v[:, 2] < -0.06, 0.95, 1.0)
    fy = [-0.029, -0.0095, 0.0095, 0.028]
    lens = [(0.042, 0.040), (0.045, 0.044), (0.042, 0.040), (0.034, 0.032)]
    for k, (y, (l1, l2)) in enumerate(zip(fy, lens)):
        prox, dist = P['prox'], P['dist']
        if k == 0 and P['index'] is not None:
            prox, dist = P['index']
        spread = math.radians(P['spread'] * (k - 1.5) / 1.5)
        a1 = math.radians(prox); a2 = a1 + math.radians(dist)
        j0 = np.array([0.0, y, -0.093])
        d1 = np.array([math.sin(a1), math.sin(spread), -math.cos(a1)]); d1 /= np.linalg.norm(d1)
        j1 = j0 + d1 * l1
        d2 = np.array([math.sin(a2), math.sin(spread), -math.cos(a2)]); d2 /= np.linalg.norm(d2)
        j2 = j1 + d2 * l2
        w = 0.0085 if k < 3 else 0.0075
        parts.append(tube([j0, j1], w, 5, True))
        parts.append(tube([j1, j2], w * 0.92, 5, True))
    t1, t2 = map(math.radians, P['thumb'])
    j0 = np.array([0.004, -0.036, -0.022])
    d1 = np.array([math.sin(t1) * 0.8, -math.cos(t1) * 0.55, -0.75]); d1 /= np.linalg.norm(d1)
    j1 = j0 + d1 * 0.038
    d2 = np.array([math.sin(t1 + t2) * 0.9, -math.cos(t1 + t2) * 0.4, -0.7]); d2 /= np.linalg.norm(d2)
    j2 = j1 + d2 * 0.032
    parts += [tube([j0, j1], 0.0105, 5), tube([j1, j2], 0.0092, 5)]
    m = join(*parts)
    if side == 'L':
        m.v[:, 0] *= -1
        m = M(m.v, [ff[::-1] for ff in m.f])
    return m


def legs_meshes():
    legs, shoes = [], []
    for sx in (-1, 1):
        x = sx * 0.095
        legs.append(loft([ring(10, 0.055, 0.058, 0.07, 2.2) + [x, 0, 0], ring(10, 0.062, 0.066, 0.50, 2.2) + [x, 0.005, 0],
                          ring(10, 0.080, 0.085, 0.92, 2.2) + [x * 0.95, 0, 0]], True, True))
        sh = loft([ring(10, 0.050, 0.13, 0.0, 2.6, -0.035) + [x, 0, 0], ring(10, 0.048, 0.12, 0.05, 2.6, -0.03) + [x, 0, 0],
                   ring(10, 0.040, 0.075, 0.095, 2.4, -0.005) + [x, 0, 0]], True, True)
        shoes.append(sh)
    return join(*legs), join(*shoes)


def build():
    h = head_mesh()
    add('head', h, COLORS['skin'])
    neck = cyl(0.057, 0.054, 0.15, 8, -0.10)
    add('neck', neck.moved((0, 0.012, 0)), COLORS['skin'])
    crown, band, brim = hat_meshes()
    add('hat_crown', crown, COLORS['hat']); add('hat_band', band, COLORS['band']); add('hat_brim', brim, COLORS['hat'])
    torso, hem, hood, bag, strings, aglets, pocket = torso_meshes()
    for nm, m, c in (('torso', torso, 'hoodie'), ('hem', hem, 'hoodie_rib'), ('hood', hood, 'hoodie'),
                     ('hood_bag', bag, 'hoodie'), ('strings', strings, 'string'), ('aglets', aglets, 'aglet'),
                     ('pocket', pocket, 'hoodie')):
        add(nm, m, COLORS[c], pivot=HIPS)
    upper, fore, cuff = sleeve_meshes()
    for s in ('R', 'L'):
        add(f'upper_{s}', upper, COLORS['hoodie'])
        add(f'fore_{s}', fore, COLORS['hoodie'])
        add(f'fore_{s}', cuff, COLORS['hoodie_rib'])
        for pose in HAND_POSES:
            add(f'hand_{pose}_{s}', hand_mesh(pose, s), COLORS['skin'])
    legs, shoes = legs_meshes()
    add('legs', legs, COLORS['pants']); add('shoes', shoes, COLORS['shoe'])


if __name__ == '__main__':
    import os, sys
    import bpy
    from meshkit import save
    bpy.ops.wm.read_factory_settings(use_empty=True)
    build()
    out = os.environ.get('HM_OUT', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out'))
    os.makedirs(out, exist_ok=True)
    print(save(os.path.join(out, 'man.npz')))
