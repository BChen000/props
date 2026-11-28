"""The sets: the conspiracy room (evidence board, hanging lamp, desk with a CRT and a phone), a daytime city street
(power line, parked car, billboard, rally, HQ), the pigeon and the specimen stage. Run build_all.py to build these and the
man into build/assets.npz."""
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

DAY = ((0.0, (0.46, 0.53, 0.64)), (0.08, (0.30, 0.42, 0.62)), (0.35, (0.12, 0.26, 0.56)), (1.0, (0.05, 0.15, 0.44)))


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


def street():
    o = L.STREET
    add('st_ground', box(700, 500, 0.1, (0, 0, -0.06)).moved(o), (0.30, 0.29, 0.27))
    add('st_road', box(700, 12, 0.02, (0, 0, 0.005)).moved(o), (0.075, 0.075, 0.08))
    add('st_marks', join(*[box(3.0, 0.15, 0.01, (x, 0, 0.02)) for x in np.arange(-330, 330, 9.0)]).moved(o), (0.80, 0.66, 0.18))
    for sy in (-1, 1):
        add('st_walk', box(700, 4.0, 0.16, (0, sy * 8.0, 0.08)).moved(o), (0.47, 0.46, 0.44))
        add('st_curb', box(700, 0.2, 0.18, (0, sy * 6.05, 0.09)).moved(o), (0.62, 0.61, 0.58))
    r = np.random.default_rng(21)
    pal = [(0.45, 0.22, 0.16), (0.52, 0.46, 0.36), (0.30, 0.32, 0.36), (0.58, 0.50, 0.38), (0.36, 0.20, 0.15), (0.40, 0.42, 0.44)]
    for sy in (-1, 1):
        x = -330.0
        while x < 330:
            w = r.uniform(12, 26)
            if sy > 0 and (abs(x + w / 2 - L.HQ[0]) < 34 or abs(x + w / 2 - L.BILLBOARD[0]) < 12):
                x += w; continue
            h, d = r.uniform(9, 34), r.uniform(14, 26)
            col = np.array(pal[r.integers(len(pal))]) * r.uniform(0.85, 1.1)
            add('st_bldg', box(w - 0.6, d, h, (x + w / 2, sy * (10.2 + d / 2), h / 2)).moved(o), col)
            add('st_roof', box(w - 0.4, d + 0.2, 0.5, (x + w / 2, sy * (10.2 + d / 2), h + 0.25)).moved(o), col * 0.7)
            x += w
    # the HQ: a glass tower with a plaza
    hx, hy = L.HQ[0], L.HQ[1]
    add('st_hq', box(44, 26, 64, (hx, hy + 13, 32)).moved(o), (0.30, 0.42, 0.52))
    add('st_hq_base', box(46, 28, 5, (hx, hy + 13, 2.5)).moved(o), (0.22, 0.24, 0.26))
    add('st_hq_canopy', box(14, 4, 0.4, (hx, hy - 2, 4.6)).moved(o), (0.85, 0.86, 0.88))
    add('st_plaza', box(60, hy - 10.0, 0.18, (hx, 10.0 + (hy - 10.0) / 2, 0.09)).moved(o), (0.60, 0.58, 0.54))
    # power line on the near sidewalk: poles along X, cross-arms along Y, three wires per span
    pole, ins = S.pole(9.0)
    R90 = rotz(math.pi / 2)
    for k in range(-5, 7):
        px = k * L.POLE_DX
        add('st_pole', pole.rotated(R90).moved((px, L.POLE_Y, 0)).moved(o), (0.30, 0.24, 0.18))
        add('st_ins', ins.rotated(R90).moved((px, L.POLE_Y, 0)).moved(o), (0.75, 0.78, 0.72))
        if k < 6:
            for dy in (-1.1, 0.0, 1.1):
                u = np.linspace(0, 1, 24)
                pts = [np.array([px + L.POLE_DX * uu, L.POLE_Y + dy, L.wire_z(uu)]) + o for uu in u]
                add('st_wire', tube(pts, 0.014, 4), (0.05, 0.05, 0.05))
    # parked car, front at -X
    c = S.car()
    Rc = rotz(-math.pi / 2)
    for nm, col in (('body', (0.62, 0.10, 0.10)), ('glass', (0.05, 0.07, 0.10)), ('wheels', (0.03, 0.03, 0.03)), ('lights', (0.9, 0.9, 0.85))):
        add('car_' + nm, c[nm].rotated(Rc).moved(L.CAR).moved(o), col)
    # billboard facing the road (-Y)
    board, frame = S.billboard(13.5, 4.5, 6.0)
    add('bb_board', board.moved(L.BILLBOARD).moved(o), (1, 1, 1))
    add('bb_frame', frame.moved(L.BILLBOARD).moved(o), (0.25, 0.26, 0.28))
    add_smooth_sky('sky_day', DAY, o, 900)
    # placards and people (placed per frame)
    sb, stick = S.sign(0.62, 0.42, 1.1)
    add('sign_board', sb, (1, 1, 1))
    add('sign_stick', stick, (0.55, 0.42, 0.28))
    for k in range(28):
        p, pc = S.person(300 + k, arms_up=(k % 3 != 1))
        add(f'pp_{k}', p, pc)


def pigeon_parts():
    pg = S.pigeon()
    body = pg['body']
    tri, _ = body.tris()
    cen = body.v[tri].mean(1)
    base = np.array((0.46, 0.49, 0.56))
    col = np.tile(base, (len(tri), 1))
    neck = (cen[:, 1] < -0.06) & (cen[:, 2] > 0.13)
    col[neck] = (0.30, 0.38, 0.36)
    col[(cen[:, 1] < -0.09) & (cen[:, 2] > 0.17)] = (0.40, 0.42, 0.50)
    col[cen[:, 1] > 0.12] = (0.22, 0.23, 0.27)
    r = np.random.default_rng(3)
    col *= r.uniform(0.92, 1.06, (len(tri), 1))
    add('pg_body', M(body.v, [tuple(t) for t in tri]), col)
    add('pg_beak', pg['beak'], (0.25, 0.20, 0.18))
    add('pg_legs', pg['legs'], (0.70, 0.30, 0.30))
    add('pg_eyes', pg['eyes'], (0.95, 0.55, 0.15))
    add('pg_led', pg['led'], (1, 1, 1))
    for nm in ('wing_L', 'wing_R'):
        w = pg[nm]
        tri, _ = w.tris(); cen = w.v[tri].mean(1)
        wc = np.tile((0.42, 0.45, 0.52), (len(tri), 1))
        wc[np.abs(cen[:, 0]) > 0.12] = (0.24, 0.25, 0.30)
        add('pg_' + nm, M(w.v, [tuple(t) for t in tri]), wc, pivot=S.WING_PIVOT[nm])
    # the robot version of the body: metal panels
    tri, _ = pg['body'].tris()
    cen = pg['body'].v[tri].mean(1)
    band = (np.floor(cen[:, 1] / 0.035) + np.floor(cen[:, 2] / 0.035)) % 2
    rc = np.where(band[:, None] > 0, 0.62, 0.24) * np.array((1.0, 1.03, 1.1))
    add('pg_robot', M(pg['body'].v, [tuple(t) for t in tri]), rc)
    add('led_dot', uvsphere(6, 4, 0.012), (1, 1, 1))
    # a splat for the car
    rr = np.random.default_rng(8)
    blobs = []
    for k, (cx, cy, rad) in enumerate(((0, 0, 0.09), (0.11, 0.03, 0.03), (-0.08, 0.07, 0.025), (0.05, -0.1, 0.02), (-0.1, -0.06, 0.018))):
        n = 14
        a = np.linspace(0, 2 * math.pi, n, endpoint=False)
        rj = rad * (1 + 0.25 * rr.uniform(-1, 1, n))
        v = np.concatenate([[[cx, cy, 0.004]], np.stack([cx + rj * np.cos(a), cy + rj * np.sin(a), np.zeros(n)], 1)])
        blobs.append(M(v, [(0, 1 + i, 1 + (i + 1) % n) for i in range(n)]))
    add('splat', join(*blobs), (0.92, 0.92, 0.88))


def stage():
    o = L.STAGE
    add('sg_floor', plane(60, 60, (0, 0, 0)).rotated(rotx(-math.pi / 2)).moved(o), (0.02, 0.025, 0.03))
    add('sg_wall', plane(60, 20, (0, 14, 10)).moved(o), (0.015, 0.017, 0.02))
    add('sg_pedestal', join(cyl(0.34, 0.34, 0.95, 16, 0), cyl(0.40, 0.40, 0.06, 16, 0.95), cyl(0.42, 0.42, 0.06, 16, 0.0)).moved(o), (0.75, 0.76, 0.78))
    add('sg_billion', text_mesh('12,000,000,000', ANTON, 0.9, 0.12, 0.006), (1, 1, 1))
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
    room(); street(); pigeon_parts(); stage(); fx()
