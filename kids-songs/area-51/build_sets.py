"""The sets: the conspiracy room (evidence board, hanging lamp, desk with a CRT and a phone), the desert airbase
(dusk and night skies, terrain, ridges, runway, hangars, planes, the gate) and the saucer hangar. Run build_all.py to build
these and the man into build/assets.npz."""
import paths  # noqa: F401  (sibling props on sys.path)
import math
import os
import sys
import numpy as np
from PIL import Image
from meshkit import M, join, rotx, roty, rotz, box, plane, loft, ring, cyl, uvsphere, tube, jitter, add, text_mesh
import layout as L

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, 'build', 'tex')
ANTON = os.path.join(HERE, 'fonts', 'Anton-Regular.ttf')


def tex_wh(name):
    with Image.open(os.path.join(TEX, name + '.png')) as im:
        return im.size


def room():
    r = np.random.default_rng(1)
    for i, x in enumerate(np.arange(-3.0, 3.0, 0.16)):
        c = np.array([0.050, 0.030, 0.018]) * (0.75 + 0.5 * r.random())
        add('floor', box(0.155, 6.4, 0.03, (x + 0.08, -1.8, -0.015)), c)
    add('wall', plane(6.4, 3.6, (0, L.WALL_Y, 1.8), 4, 3), (0.030, 0.036, 0.034))
    add('wall', box(6.4, 0.03, 0.12, (0, L.WALL_Y - 0.015, 0.06)), (0.02, 0.02, 0.02))
    for sx in (-1, 1):
        w = plane(5.0, 3.6, (0, 0, 1.8), 2, 2).rotated(rotz(sx * math.pi / 2)).moved((sx * 2.6, -1.1, 0))
        add('wall', w, (0.026, 0.030, 0.030))
    add('ceiling', box(6.4, 6.4, 0.05, (0, -1.6, 3.45)), (0.02, 0.02, 0.02))
    B = L.BOARD
    fw = 0.06
    frame = join(box(B['w'] + 2 * fw, 0.05, fw, (B['cx'], B['y'], B['cz'] + B['h'] / 2 + fw / 2)),
                 box(B['w'] + 2 * fw, 0.05, fw, (B['cx'], B['y'], B['cz'] - B['h'] / 2 - fw / 2)),
                 box(fw, 0.05, B['h'], (B['cx'] - B['w'] / 2 - fw / 2, B['y'], B['cz'])),
                 box(fw, 0.05, B['h'], (B['cx'] + B['w'] / 2 + fw / 2, B['y'], B['cz'])))
    add('board_frame', frame, (0.09, 0.05, 0.025))
    add('cork', plane(B['w'], B['h'], (B['cx'], L.CORK_Y, B['cz'])), (0.30, 0.17, 0.08))
    for k, (name, (x, z, rot, h)) in enumerate(L.ITEMS.items()):
        wh = tex_wh(name)
        w, h = L.item_size(name, wh)
        p = plane(w, h, (0, 0, 0), 2, 2)
        rr = np.random.default_rng(k + 10)
        corner = (np.abs(p.v[:, 0]) > w * 0.4) & (np.abs(p.v[:, 2]) > h * 0.4)
        p.v[corner, 1] -= rr.uniform(0.002, 0.012, corner.sum())
        p = p.rotated(roty(-math.radians(rot))).moved((x, L.CORK_Y - 0.003 - 0.0012 * (k % 5), z))
        add('item_' + name, p, (1, 1, 1))
        if name.startswith('p_'):
            pp = L.pin_pos(name, wh)
            col = np.array(L.PIN_COL.get(name, (0.75, 0.05, 0.05)))
            add('pins', uvsphere(8, 5, 0.011).scaled((1, 0.8, 1)).moved(pp), col)
            add('pins', cyl(0.0035, 0.0035, 0.018, 5, 0).rotated(rotx(-math.pi / 2)).moved(pp + [0, 0.002, 0]), col * 0.6)
        else:
            pp = np.array([x, L.CORK_Y - 0.016, z + h / 2 - 0.02])
            add('pins', uvsphere(8, 5, 0.009).moved(pp), (0.8, 0.8, 0.8))
    # hanging lamp
    lx, ly, lz = L.LAMP
    add('lamp', cyl(0.004, 0.004, 3.45 - (lz + 0.12), 5, lz + 0.12).moved((lx, ly, 0)), (0.01, 0.01, 0.01))
    shade = loft([ring(14, 0.17, 0.17, lz - 0.035), ring(14, 0.10, 0.10, lz + 0.03), ring(14, 0.035, 0.035, lz + 0.11)],
                 False, True).moved((lx, ly, 0))
    add('shade', shade, (0.03, 0.06, 0.045))
    add('bulb', uvsphere(10, 7, 0.034).moved(L.LAMP), (1, 1, 1))
    # desk, CRT, keyboard, mug, papers, phone (desk frame)
    R, o = L.desk_frame()

    def put(name, m, col):
        add(name, m.rotated(R).moved(o), col)

    t = L.DESK['top']
    desk = join(box(1.3, 0.65, 0.04, (0, 0, t - 0.02)), *[box(0.05, 0.05, t - 0.04, (sx * 0.6, sy * 0.28, (t - 0.04) / 2))
                                                         for sx in (-1, 1) for sy in (-1, 1)],
                box(0.45, 0.6, 0.12, (0.38, 0, t - 0.10)))
    put('desk', desk, (0.07, 0.04, 0.022))
    crt = join(box(0.40, 0.36, 0.34, (0, 0.04, t + 0.03 + 0.17)), box(0.30, 0.20, 0.26, (0, 0.24, t + 0.03 + 0.17)),
               box(0.22, 0.2, 0.03, (0, 0.06, t + 0.015)))
    put('crt', crt, (0.32, 0.30, 0.26))
    put('crt_screen', plane(0.31, 0.24, (0, -0.142, t + 0.03 + 0.18)), (1, 1, 1))
    put('keyboard', box(0.42, 0.15, 0.025, (0.02, -0.21, t + 0.0125)), (0.28, 0.27, 0.24))
    put('mug', cyl(0.04, 0.04, 0.1, 10, t), (0.45, 0.08, 0.06))
    for k in range(3):
        pp = plane(0.21, 0.29, (0, 0, 0)).rotated(rotx(-math.pi / 2)).rotated(rotz(0.3 * k - 0.2)).moved((-0.30 + 0.05 * k, 0.10 - 0.03 * k, t + 0.002 + 0.001 * k))
        put('desk_papers', pp, (0.7, 0.68, 0.62))
    px, py = L.PHONE_LOCAL
    put('phone_body', box(0.078, 0.160, 0.009, (px, py, t + 0.0045)), (0.02, 0.02, 0.025))
    scr = plane(0.070, 0.150, (0, 0, 0)).rotated(rotx(-math.pi / 2))
    put('phone_screen', scr.moved((px, py, t + 0.0095)), (1, 1, 1))


sys.path.insert(0, os.path.join(HERE, '..', 'lowpoly-sets'))
import sets as S

DUSK = ((0.0, (1.0, 0.48, 0.20)), (0.05, (0.70, 0.30, 0.28)), (0.18, (0.20, 0.14, 0.32)), (0.45, (0.05, 0.06, 0.18)), (1.0, (0.01, 0.015, 0.05)))
NIGHT = ((0.0, (0.06, 0.07, 0.14)), (0.1, (0.03, 0.035, 0.08)), (1.0, (0.004, 0.006, 0.02)))


def add_smooth_sky(name, cols, o, r):
    """Inverted sphere with a per-vertex colour gradient (smooth, unlike per-face colours)."""
    import meshkit
    s_ = uvsphere(64, 32, r)
    s_ = M(s_.v, [ff[::-1] for ff in s_.f])
    tri, _ = s_.tris()
    P = s_.v[tri]
    z = np.clip(P[..., 2] / r, 0, 1)
    hs = np.array([c[0] for c in cols]); cs = np.array([c[1] for c in cols])
    col = np.stack([np.interp(z, hs, cs[:, k]) for k in range(3)], -1)
    col[P[..., 2] < 0] = cs[0] * 0.3
    n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]); n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    meshkit.PARTS[name] = dict(pos=(P + o).reshape(-1, 3).astype(np.float32), nrm=np.repeat(n[:, None], 3, 1).reshape(-1, 3).astype(np.float32),
                               uv=np.zeros((len(tri) * 3, 2), np.float32), col=col.reshape(-1, 3).astype(np.float32))


def desert():
    o = L.DESERT
    t, tc = S.terrain(2400, 90, 2.2, 3, flat_r=420, cols=((0.0, (0.26, 0.17, 0.11)), (1.0, (0.40, 0.29, 0.19))),
                       flats=((L.GATE[0], L.GATE[1], 90),))
    add('d_ground', t.moved(o), tc)
    m, mc = S.mountains(900, 220, (18, 75), 4)
    add('d_mount', m.moved(o), mc * np.array([0.55, 0.5, 0.75]))
    for nm, cols in (('sky_dusk', DUSK), ('sky_night', NIGHT)):
        add_smooth_sky(nm, cols, o, 1500)
    rw, marks = S.runway(1400, 45)
    add('d_runway', rw.moved(o + [0, 250, 0]), (0.06, 0.06, 0.065))
    add('d_marks', marks.moved(o + [0, 250, 0]), (0.75, 0.75, 0.7))
    for k in range(4):
        add('d_hangar', S.hangar(36, 44).moved(o + [-120, 40 + k * 70, 0]), (0.42, 0.42, 0.40))
    add('d_tower', join(box(5, 5, 22, (0, 0, 11)), box(9, 9, 4, (0, 0, 24))).moved(o + [-80, -60, 0]), (0.5, 0.48, 0.44))
    j = S.jet()
    add('jet_body', j['body'], (0.85, 0.86, 0.88)); add('jet_stripe', j['stripe'], (0.75, 0.10, 0.10))
    u = S.u2()
    add('u2_body', u['body'], (0.62, 0.64, 0.68)); add('u2_canopy', u['canopy'], (0.05, 0.07, 0.1))
    gx = o + L.GATE
    rails, panel = S.fence(60, 2.4)
    for sx in (-1, 1):
        add('g_fence', rails.moved((sx * 32.9, 0.4, 0)).moved(gx), (0.45, 0.46, 0.48))
        add('g_fence_panel', panel.moved((sx * 32.9, 0.4, 0)).moved(gx), (1, 1, 1))
    posts = [box(0.4, 0.4, 1.15, (-2.75, 0, 0.575)), box(0.16, 0.16, 0.95, (2.75, 0, 0.475))]
    add('g_gate', join(*posts), (0.85, 0.78, 0.15))
    segs = np.linspace(-2.6, 2.75, 10)
    add('g_arm_r', join(*[box(segs[i + 1] - segs[i], 0.1, 0.12, ((segs[i] + segs[i + 1]) / 2, 0, 1.0)) for i in range(0, 9, 2)]).moved(gx), (0.75, 0.06, 0.05))
    add('g_arm_w', join(*[box(segs[i + 1] - segs[i], 0.1, 0.12, ((segs[i] + segs[i + 1]) / 2, 0, 1.0)) for i in range(1, 9, 2)]).moved(gx), (0.9, 0.9, 0.88))
    add('g_signpost', join(*[box(0.09, 0.09, 2.6, (sx * px, -0.3, 1.3)) for sx in (-1, 1) for px in (3.25, 4.35)]).moved(gx), (0.3, 0.3, 0.3))
    add('g_sign', join(*[plane(1.4, 0.98, (sx * 3.8, -0.36, 2.0)) for sx in (-1, 1)]).moved(gx), (1, 1, 1))
    tr = S.truck()
    add('truck_body', tr['body'], (0.80, 0.80, 0.78)); add('truck_wheels', tr['wheels'], (0.03, 0.03, 0.03))
    add('truck_lights', tr['lights'], (1, 1, 1)); add('truck_glass', tr['glass'], (0.05, 0.06, 0.08))
    for k in range(24):
        p, pc = S.person(100 + k)
        if k % 6 == 2:
            nf = len(pc); pc = pc.copy(); pc[-int(nf * 0.32):] = pc[-int(nf * 0.32):]
        add(f'crowd_{k}', p, pc)
    add('alien_head', uvsphere(8, 6, 0.13).scaled((1.0, 1.0, 1.25)), (0.25, 0.65, 0.25))


def hangar_set():
    o = L.HANGAR
    add('h_floor', box(80, 120, 0.1, (0, 20, -0.05)).moved(o), (0.10, 0.10, 0.11))
    add('h_shell', S.hangar(46, 110).moved(o + [0, 20, 0]), (0.16, 0.17, 0.18))
    sc = S.saucer(2.7)
    add('saucer_body', sc['body'], (0.55, 0.57, 0.60)); add('saucer_dome', sc['dome'], (0.20, 0.30, 0.34))
    add('saucer_lights', sc['lights'], (1, 1, 1))
    add('h_lamp', join(cyl(0.6, 0.25, 0.4, 10, 0), cyl(0.02, 0.02, 6, 4, 0.4)), (0.1, 0.1, 0.1))
    add('h_lampglow', cyl(0.55, 0.55, 0.02, 10, -0.01), (1, 1, 1))


def fx():
    # light beam cone: apex at origin, opening down -Z to radius 1 at z=-1; uv.y 0 at apex -> 1 at the base
    n = 28
    v, f, uv = [], [], []
    for k in range(n + 1):
        a = 2 * math.pi * k / n
        v += [(0, 0, 0), (math.cos(a), math.sin(a), -1.0)]
    for k in range(n):
        a, b = 2 * k, 2 * (k + 1)
        f.append((a, a + 1, b + 1, b)); uv.append([(0, 0), (0, 1), (1, 1), (1, 0)])
    add('beam', M(np.array(v), f, uv), (1, 1, 1))
    add('quad', plane(1, 1, (0, 0, 0)), (1, 1, 1))


def build():
    room(); desert(); hangar_set(); fx()
