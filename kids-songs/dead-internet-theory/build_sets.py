"""The sets: the conspiracy room (evidence board, hanging lamp, desk with a CRT and a phone), the bot phone farm,
the bar-chart stage and the night city. Run build_all.py to build these and the man into build/assets.npz."""
import paths  # noqa: F401  (sibling props on sys.path)
import math
import os
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


def farm():
    o = L.FARM
    add('farm_floor', box(8, 30, 0.02, (0, 8, -0.01)).moved(o), (0.03, 0.03, 0.035))
    rng = np.random.default_rng(3)
    bodies, screens, scol, racks = [], [], [], []
    for side in (-1, 1):
        x = side * 0.95
        for k in range(7):
            y0 = -1.0 + k * 2.0
            for py in (y0 - 0.88, y0 + 0.88):
                for px in (x - side * 0.15, x + side * 0.15):
                    racks.append(box(0.04, 0.04, 2.05, (px, py, 1.025)))
            for s in range(5):
                z = 0.30 + s * 0.38
                racks.append(box(0.36, 1.80, 0.025, (x, y0, z)))
                for j in range(12):
                    py = y0 - 0.80 + j * 0.145
                    ph = box(0.010, 0.074, 0.152, (x - side * 0.02, py, z + 0.0125 + 0.077))
                    ph = ph.rotated(rotz(rng.normal(0, 0.03)), (x, py, z))
                    bodies.append(ph)
                    sc = plane(0.066, 0.142, (0, 0, 0))
                    sc = sc.rotated(rotz(-side * math.pi / 2)).moved((x - side * 0.02 - side * 0.0055, py, z + 0.0125 + 0.077))
                    screens.append(sc)
                    cell = int(rng.integers(0, 8)); ph_ = rng.random()
                    scol += [(cell / 8 + 0.01, ph_, 0.0)] * 2
    add('farm_racks', join(*racks).moved(o), (0.10, 0.10, 0.11))
    add('farm_phones', join(*bodies).moved(o), (0.015, 0.015, 0.018))
    add('farm_screens', join(*screens).moved(o), np.array(scol))
    lights = [box(0.08, 1.6, 0.04, (0, -0.5 + k * 2.6, 2.6)) for k in range(6)]
    add('farm_tubes', join(*lights).moved(o), (1, 1, 1))


def chart():
    o = L.CHART
    add('chart_floor', box(30, 30, 0.02, (0, 5, -0.01)).moved(o), (0.02, 0.022, 0.03))
    add('bar', box(1, 1, 1, (0, 0, 0.5)), (1, 1, 1))
    for name, s, size in (('txt_humans', 'HUMANS', 0.28), ('txt_bots', 'BOTS', 0.28), ('txt_49', '49%', 0.42),
                          ('txt_51', '51%', 0.42), ('txt_47', '47%', 0.42), ('txt_53', '53%', 0.42),
                          ('txt_2024', '2024', 0.55), ('txt_2025', '2025', 0.55), ('txt_sub', 'SHARE OF ALL WEB TRAFFIC', 0.17)):
        add(name, text_mesh(s, ANTON, size, extrude=0.03 if size > 0.2 else 0.01, bevel=0.003), (1, 1, 1))


def city():
    o = L.CITY
    rng = np.random.default_rng(5)
    add('city_ground', box(800, 800, 0.1, (0, 0, -0.05)).moved(o), (0.01, 0.012, 0.02))
    bl = []
    for i in range(-14, 15):
        for j in range(-6, 26):
            if rng.random() < 0.18:
                continue
            w, d = rng.uniform(8, 16), rng.uniform(8, 16)
            h = rng.uniform(8, 30) * (1 + 2.5 * math.exp(-((i * 0.5) ** 2 + ((j - 10) * 0.25) ** 2) / 4) * rng.random())
            bl.append(box(w, d, h, (i * 20 + rng.uniform(-2, 2), j * 20 + rng.uniform(-2, 2), h / 2)))
    add('city_bldg', join(*bl).moved(o), (0.025, 0.028, 0.04))
    add('moon', uvsphere(14, 9, 16).moved(o + [-75, 520, 165]), (1, 1, 1))


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
    room(); farm(); chart(); city(); fx()
