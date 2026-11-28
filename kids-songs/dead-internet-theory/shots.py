"""The shots of the Dead Internet Short. Each scene function gets (t, x, R) and returns a frame description:
dict(items, cam, lights, env, adds, post). t: seconds into the scene; x.T / x.E: line starts / ends in the scene."""
import paths  # noqa: F401  (sibling props on sys.path)
import math
import numpy as np
from glr import T, R3, S, euler
import man
from man import track, add_life, merge, REST
from poses import G
import layout as L

GLOBAL = {}          # filled by make_video: speech envelope, texture sizes, renderer


def ease(x):
    x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)


def eio(x):
    x = min(max(x, 0.0), 1.0); return 0.5 - 0.5 * math.cos(math.pi * x)


def lerp(a, b, t):
    return np.asarray(a, float) + (np.asarray(b, float) - np.asarray(a, float)) * t


def ramp(t, t0, d):
    return ease((t - t0) / d) if d > 0 else float(t >= t0)


def shake(t, amt=0.004, seed=0.0):
    return np.array([amt * (math.sin(1.3 * t + seed) + 0.5 * math.sin(2.9 * t + 1.7 + seed)),
                     0.0, amt * (math.sin(1.1 * t + 0.4 + seed) + 0.5 * math.sin(3.3 * t + seed))])


def env_at(gt):
    e = GLOBAL.get('env')
    if e is None:
        return 0.0
    i = int(gt * 30)
    return float(e[min(max(i, 0), len(e) - 1)])


def billboard(p, cam_eye, size):
    p = np.asarray(p, float); f = p - np.asarray(cam_eye, float); f /= np.linalg.norm(f)
    up = np.array([0, 0, 1.0])
    x = np.cross(f, up); x /= max(np.linalg.norm(x), 1e-6); z = np.cross(x, f)
    Rm = np.stack([x, f, z], 1)
    return T(p) @ R3(Rm) @ S(size)


# ------------------------------------------------------------------ the room
DESK_R, DESK_O = L.desk_frame()


def desk_pt(local):
    return DESK_R @ np.asarray(local, float) + DESK_O


CRT_C = desk_pt((0, -0.142, L.DESK['top'] + 0.21))
CRT_N = DESK_R @ np.array([0, -1.0, 0])
PHONE_C = desk_pt((L.PHONE_LOCAL[0], L.PHONE_LOCAL[1], L.DESK['top'] + 0.0095))
DESK_UP = DESK_R @ np.array([0, 1.0, 0])

ROOM_PARTS = [('floor', dict(spec=0.25, shin=30)), ('wall', {}), ('ceiling', {}), ('board_frame', dict(spec=0.2)),
              ('cork', dict(mode=2)), ('pins', dict(spec=0.8, shin=40)), ('lamp', {}), ('shade', dict(spec=0.6, shin=30)),
              ('desk', dict(spec=0.2)), ('crt', dict(spec=0.2)), ('keyboard', {}), ('mug', dict(spec=0.5)),
              ('desk_papers', {}), ('phone_body', dict(spec=0.8, shin=60))]


def room_items(t, post_scroll=0.0, bulb=1.0, crt=1.0):
    out = [(nm, np.eye(4), dict(m)) for nm, m in ROOM_PARTS]
    for name in L.ITEMS:
        out.append(('item_' + name, np.eye(4), dict(tex=name, spec=0.05)))
    out.append(('bulb', np.eye(4), dict(emit=(9.0 * bulb, 6.5 * bulb, 3.6 * bulb), cast=False)))
    out.append(('crt_screen', np.eye(4), dict(tex='crt', tmode=2, temit=0.55 * crt, cast=False)))
    win = 0.413
    out.append(('phone_screen', np.eye(4), dict(tex='post', tmode=2, temit=1.1, cast=False,
                                                uvx=(0, 1 - win - post_scroll, 1, win))))
    return out


def spot(pos, target, **k):
    return dict(type='spot', pos=tuple(pos), dir=tuple(np.subtract(target, pos)), **k)


FACE_KEY = 1.4                  # soft front light on his face, under the hat brim


def room_lights(t, bulb=1.0, swing=0.0, crt=1.0):
    lx, ly, lz = L.LAMP
    sw = swing * math.sin(2 * math.pi * 0.35 * t)
    key = spot((lx, ly, lz - 0.03), (lx + 0.35 * sw, ly + 0.45, 0.0), col=(1.0, 0.76, 0.48), energy=1.55 * bulb, outer=50,
               inner=26, shadow=True, range=9, soft=3.0, sh_fov=106, sh_near=0.05, sh_far=6)
    return [key,
            dict(type='point', pos=(lx, ly, lz - 0.1), col=(1.0, 0.7, 0.45), energy=0.16 * bulb, range=4.5, spec=0.0),
            spot((0.2, -1.2, 3.3), (0.0, L.WALL_Y, 1.55), col=(1.0, 0.82, 0.6), energy=1.5, outer=34, inner=18, range=9, spec=0.2),
            spot((-0.85, 0.95, 2.15), (0, 0, 1.55), col=(0.30, 0.52, 1.0), energy=1.5, outer=28, inner=14, range=5, spec=2.0),
            spot((0.85, 0.9, 2.05), (0, 0, 1.5), col=(0.30, 0.52, 1.0), energy=1.2, outer=28, inner=14, range=5, spec=2.0),
            dict(type='point', pos=tuple(CRT_C + CRT_N * 0.35), col=(0.45, 0.85, 0.8), energy=0.07 * crt, range=2.2, spec=0.3),
            dict(type='point', pos=(0.0, -2.2, 1.6), col=(0.75, 0.82, 1.0), energy=0.12, range=6, spec=0.0),
            spot((0.30, -2.0, 1.95), (0, 0, 1.68), col=(1.0, 0.9, 0.8), energy=FACE_KEY, outer=13, inner=6, range=6, spec=0.2)]


ROOM_ENV = dict(amb_top=(0.012, 0.014, 0.02), amb_bot=(0.003, 0.003, 0.004), fog_col=(0.006, 0.007, 0.011), fog_d=0.05, bg=(0, 0, 0))

_DUST = None


def room_adds(t, cam_eye, bulb=1.0):
    global _DUST
    rng = np.random.default_rng(4)
    n = 140
    if _DUST is None:
        _DUST = dict(h=rng.uniform(0.15, 2.3, n), a=rng.uniform(0, 2 * math.pi, n), r=np.sqrt(rng.random(n)),
                     ph=rng.uniform(0, 6.28, n), s=rng.uniform(0.003, 0.007, n), b=rng.uniform(0.3, 1.0, n))
    d = _DUST
    lx, ly, lz = L.LAMP
    h = (d['h'] + 0.03 * t) % 2.3 + 0.15
    rad = h * math.tan(math.radians(24)) * d['r']
    x = lx + rad * np.cos(d['a'] + 0.05 * t) + 0.02 * np.sin(0.4 * t + d['ph'])
    y = ly + 0.22 * h / 2.3 * 2 + rad * np.sin(d['a'] + 0.05 * t) + 0.02 * np.cos(0.33 * t + d['ph'])
    z = lz - h
    P = np.stack([x, y, z], 1)
    dcam = np.linalg.norm(P - np.asarray(cam_eye, float), axis=1)
    near = np.clip((dcam - 0.55) / 0.5, 0, 1)
    f = P - np.asarray(cam_eye, float); f /= np.linalg.norm(f, axis=1, keepdims=True)
    up = np.array([0, 0, 1.0])
    xs = np.cross(f, up); xs /= np.maximum(np.linalg.norm(xs, axis=1, keepdims=True), 1e-6); zs = np.cross(xs, f)
    s = d['s'][:, None]
    c0 = P - xs * s - zs * s; c1 = P + xs * s - zs * s; c2 = P + xs * s + zs * s; c3 = P - xs * s + zs * s
    tri = np.stack([c0, c1, c2, c0, c2, c3], 1).reshape(-1, 3)
    uv = np.tile(np.array([[0, 0], [1, 0], [1, 1], [0, 0], [1, 1], [0, 1]], np.float32), (n, 1))
    br = (d['b'] * (1 - h / 2.6) * near)[:, None] * np.ones((1, 3))
    col = np.repeat(br, 6, 0)
    GLOBAL['R'].set_dynamic('dust', dict(pos=tri.astype(np.float32), nrm=np.zeros_like(tri, np.float32), uv=uv,
                                         col=col.astype(np.float32)))
    beamM = T((lx, ly, lz - 0.02)) @ R3(euler(-0.11, 0, 0)) @ S((1.07, 1.07, 2.4))
    return [('beam', beamM, dict(amode=0, col=(1.0, 0.78, 0.5), int=0.05 * bulb)),
            ('quad', billboard(L.LAMP, cam_eye, 0.55), dict(amode=1, col=(1.0, 0.75, 0.45), int=1.4 * bulb)),
            ('dust', np.eye(4), dict(amode=2, col=(1.0, 0.85, 0.6), int=1.2 * bulb))]


def strings_items(progress=1.0, sag=0.025, fall=0.0):
    wh = GLOBAL['texwh']
    pins = {k: L.pin_pos(k, wh[k]) for k in L.ITEMS if k.startswith('p_')}
    rng = np.random.default_rng(21)
    tris = []
    for k, (a, b) in enumerate(L.STRINGS):
        pr = progress if np.isscalar(progress) else progress[k]
        if pr <= 0:
            continue
        A, B = pins[a] + [0, -0.004, 0], pins[b] + [0, -0.004, 0]
        n = 14
        ts = np.linspace(0, pr, n)
        P = A[None] + (B - A)[None] * ts[:, None]
        s = sag * (1 + 2.0 * rng.random())
        P[:, 2] -= s * 4 * ts * (1 - ts) * (np.linalg.norm(B - A) / 1.0)
        if fall > 0 and k % 3 != 1:
            fr = min(1.0, fall * (1.2 + 0.3 * (k % 4)))
            drop = fr * (0.6 + 0.4 * (k % 2))
            P[:, 2] -= drop * ts ** 1.5 * 1.2
            P[:, 1] -= 0.04 * fr * ts
        tris.append(_tube_soup(P, 0.0022))
    if not tris:
        tris = [np.zeros((3, 3), np.float32)]
    pos = np.concatenate(tris).astype(np.float32)
    e1 = pos[1::3] - pos[0::3]; e2 = pos[2::3] - pos[0::3]
    nn = np.cross(e1, e2); nn /= np.maximum(np.linalg.norm(nn, axis=1, keepdims=True), 1e-9)
    nrm = np.repeat(nn, 3, 0).astype(np.float32)
    GLOBAL['R'].set_dynamic('strings_dyn', dict(pos=pos, nrm=nrm, uv=np.zeros((len(pos), 2), np.float32),
                                                col=np.tile(np.array([[0.55, 0.02, 0.02]], np.float32), (len(pos), 1))))
    return [('strings_dyn', np.eye(4), dict(spec=0.3, cast=False))]


def _tube_soup(P, r, sides=4):
    out = []
    for i in range(len(P) - 1):
        t = P[i + 1] - P[i]; ln = np.linalg.norm(t)
        if ln < 1e-6:
            continue
        t /= ln
        a = np.array([0, 0, 1.0]) if abs(t[2]) < 0.9 else np.array([1.0, 0, 0])
        u = np.cross(t, a); u /= np.linalg.norm(u); w = np.cross(t, u)
        ring = [r * (math.cos(2 * math.pi * k / sides) * u + math.sin(2 * math.pi * k / sides) * w) for k in range(sides)]
        for k in range(sides):
            p0, p1 = P[i] + ring[k], P[i] + ring[(k + 1) % sides]
            q0, q1 = P[i + 1] + ring[k], P[i + 1] + ring[(k + 1) % sides]
            out += [p0, p1, q1, p0, q1, q0]
    return np.array(out, np.float32).reshape(-1, 3)


def man_items(t, gt, keys, life=1.0, glitch=0.0, mats=None):
    pose = track(keys, t)
    pose = add_life(pose, gt, env_at(gt) * life, 0.3, life)
    gh = None
    if glitch > 0:
        gh = {}
        for nm in man.HEAD_PARTS:
            d = man.explode(GLOBAL['parts'][nm], glitch, seed=hash(nm) % 1000)
            GLOBAL['R'].set_dynamic(nm + '_x', d)
            gh[nm] = nm + '_x'
    return man.items(pose, mats=mats, glitch_head=gh)


def cam(eye, target, fov, t=0.0, sh=0.004, seed=0.0):
    e = np.asarray(eye, float) + shake(t, sh, seed)
    return dict(eye=tuple(e), target=tuple(np.asarray(target, float) + shake(t + 3, sh * 0.6, seed)), fov=fov)


def dist(c, p):
    return float(np.linalg.norm(np.asarray(c['eye']) - np.asarray(p)))


def room_frame(t, gt, c, keys, post=None, bulb=1.0, swing=0.0, strings=1.0, sag=0.025, fall=0.0, glitch=0.0,
               scroll=0.0, man_on=True):
    items = room_items(t, scroll, bulb) + strings_items(strings, sag, fall)
    if man_on:
        items += man_items(t, gt, keys, glitch=glitch)
    p = dict(exposure=1.0, vignette=0.55, grain=0.022, bloom=0.4)
    p.update(post or {})
    return dict(items=items, cam=c, lights=room_lights(gt, bulb, swing), env=ROOM_ENV, adds=room_adds(gt, c['eye'], bulb), post=p)


HEADC = np.array([0, 0.0, 1.66])


# ------------------------------------------------------------------ scenes
def s_hook(t, x, gt):
    k = ease(t / x.dur)
    c = cam(lerp((0.05, -1.55, 1.60), (0.03, -1.12, 1.64), k), (0, 0, 1.60), 30, t)
    fl = [0, 0.15, 0, 0, 0.6, 0.1, 1, 0.3, 1, 1]
    bulb = fl[min(int(t / 0.06), len(fl) - 1)] if t < 0.6 else 1.0
    keys = [(0, dict(head=(20, -6, 0))), (x.T[1] - 0.25, dict(head=(-1, 0, 0), dur=0.7))]
    return room_frame(t, gt, c, keys, dict(dof=7, focus=dist(c, HEADC)), bulb=bulb)


def s_name(t, x, gt):
    k = eio(t / x.dur)
    c = cam(lerp((0.75, -3.05, 1.50), (0.55, -2.65, 1.56), k), lerp((0.05, 0.6, 1.55), (0.05, 0.6, 1.58), k), 44, t, 0.006)
    keys = [(0, dict(head=(-1, 0, 0))), (0.15, dict(G['present_R'], head=(0, -10, 0), dur=0.55))]
    return room_frame(t, gt, c, keys, dict(dof=3, focus=dist(c, (0, 0.3, 1.5)), exposure=1.15))


def s_forum(t, x, gt):
    k = eio(t / x.dur)
    d = lerp(1.55, 1.08, k)
    side = DESK_R @ np.array([1.0, 0, 0])
    eye = CRT_C + CRT_N * d + side * 0.04 * (1 - k) + np.array([0, 0, -0.03])
    c = cam(eye, CRT_C + np.array([0, 0, -0.07]), 40, t, 0.003)
    keys = [(0, {})]
    return room_frame(t, gt, c, keys, dict(dof=4, focus=dist(c, CRT_C), exposure=1.2, bloom=0.5))


FARM_ENV = dict(amb_top=(0.014, 0.018, 0.03), amb_bot=(0.002, 0.002, 0.003), fog_col=(0.006, 0.010, 0.018), fog_d=0.07, bg=(0, 0, 0))


def farm_frame(t, gt, c, cellf=-1.0, rate=2.5, post=None, screen=2.6):
    o = L.FARM
    items = [('farm_floor', np.eye(4), dict(spec=0.4, shin=30)), ('farm_racks', np.eye(4), dict(spec=0.6, shin=40)),
             ('farm_phones', np.eye(4), dict(spec=0.8, shin=60)),
             ('farm_screens', np.eye(4), dict(tex='cells', mode=3, cellf=cellf, tt=gt, rate=rate, temit=screen, cast=False)),
             ('farm_tubes', np.eye(4), dict(emit=(0.9, 1.0, 1.15), cast=False))]
    lights = [dict(type='point', pos=tuple(o + [0, -0.5 + k * 2.6, 2.45]), col=(0.7, 0.85, 1.0), energy=0.9, range=4.5, spec=0.6)
              for k in range(6)]
    lights += [dict(type='point', pos=tuple(o + [s * 0.45, 0.5 + 2.6 * k, 1.0]), col=(0.25, 0.6, 1.0), energy=0.18, range=2.2)
               for s in (-1, 1) for k in range(3)]
    p = dict(exposure=1.1, vignette=0.6, grain=0.022, bloom=0.55, bloom_t=0.8)
    p.update(post or {})
    return dict(items=items, cam=c, lights=lights, env=FARM_ENV, adds=[], post=p)


def s_bots(t, x, gt):
    o = L.FARM
    sx = -0.95 + 0.02 + 0.0055 + 0.001
    shelf_z = 0.30 + 2 * 0.38 + 0.0125 + 0.077
    py = -1.0 + 2 * 2.0 - 0.80 + 6 * 0.145
    screen = o + np.array([sx, py, shelf_z])
    a = ease((t - x.T[1] + 0.3) / (x.T[4] - x.T[1]))
    b = eio((t - (x.T[4] - 0.3)) / (x.dur - x.T[4] + 0.3))
    e0 = screen + np.array([0.40, -0.05, 0.02])
    e1 = screen + np.array([0.85, -0.60, 0.12])
    e2 = o + np.array([0.0, -0.75, 1.30])
    eye = lerp(e0, e1, a) if b <= 0 else lerp(e1, e2, b)
    tg0 = screen + np.array([0.0, 0.0, 0.0])
    tg1 = screen + np.array([0.0, 0.35, -0.05])
    tg2 = o + np.array([0.0, 7.0, 1.0])
    tgt = lerp(tg0, tg1, a) if b <= 0 else lerp(tg1, tg2, b)
    fov = 30 + 22 * b
    c = cam(eye, tgt, fov, t, 0.002)
    cellf = 0.0
    if t >= x.T[2] - 0.05:
        cellf = 1.0
    if t >= x.T[3] - 0.05:
        cellf = 2.0
    if t >= x.T[4] - 0.05:
        cellf = -1.0
    if t >= x.T[5] - 0.05:
        cellf = 3.0 if int(gt * 4) % 2 == 0 else 6.0
    focus = dist(c, screen) if b <= 0.3 else dist(c, o + [0, 3.0, 1.1])
    return farm_frame(t, gt, c, cellf, 3.0, dict(dof=6 * (1 - b) + 2, focus=focus))


def s_purpose(t, x, gt):
    k = eio(t / x.dur)
    c = cam(lerp((0.08, -1.25, 1.60), (0.04, -1.00, 1.62), k), (0, 0, 1.58), 30, t, 0.003)
    keys = [(0, dict(head=(2, 6, -3))), (0.2, dict(lean=(5, 0), head=(4, 0, 0), dur=1.2)),
            (x.T[1], dict(lean=(7, 0), head=(6, -3, 4), dur=0.8))]
    return room_frame(t, gt, c, keys, dict(dof=7, focus=dist(c, HEADC) - 0.05), swing=1.0)


def s_crazy(t, x, gt):
    k = eio(t / x.dur)
    c = cam(lerp((0.12, -2.15, 1.48), (0.08, -1.95, 1.50), k), (0, 0, 1.42), 38, t)
    keys = [(0, {}), (max(x.T[0] - 0.15, 0), dict(G['shrug'], dur=0.35)),
            (x.T[1] - 0.25, dict(G['finger_up_R'], L=REST['L'], head=(0, 3, -3), dur=0.4))]
    return room_frame(t, gt, c, keys, dict(dof=6, focus=dist(c, HEADC)))


CHART_ENV = dict(amb_top=(0.02, 0.022, 0.03), amb_bot=(0.004, 0.004, 0.006), fog_col=(0.004, 0.005, 0.01), fog_d=0.05, bg=(0.0, 0.0, 0.0))


def s_chart(t, x, gt):
    o = L.CHART
    k = eio(t / x.dur)
    eye = o + lerp((0.35, -6.9, 1.45), (0.15, -5.9, 1.55), k)
    tgt = o + np.array([0.0, 0.0, 1.85])
    c = cam(eye, tgt, 40, t, 0.004)
    grow = ease((t - x.T[0] - 0.3) / 2.2)
    shift = ease((t - x.T[3] + 0.1) / 0.6)
    vh = lerp(49, 47, shift) * grow; vb = lerp(51, 53, shift) * grow
    sc = 0.045
    items = [('chart_floor', np.eye(4), dict(mode=4, seed=1.0, spec=0.3))]
    xh, xb = -0.55, 0.55
    items.append(('bar', T(o + [xh, 0, 0]) @ S((0.72, 0.72, max(vh * sc, 0.001))), dict(tint=(0.30, 0.34, 0.42), spec=0.4)))
    glow = 0.6 + 2.2 * shift
    items.append(('bar', T(o + [xb, 0, 0]) @ S((0.72, 0.72, max(vb * sc, 0.001))),
                  dict(tint=(0.55, 0.03, 0.03), emit=(0.22 * glow, 0.01, 0.01), spec=0.5)))
    items.append(('txt_humans', T(o + [xh, -0.45, 0.16]), dict(tint=(0.75, 0.78, 0.85), emit=(0.10, 0.11, 0.13), spec=0.3)))
    items.append(('txt_bots', T(o + [xb, -0.45, 0.16]), dict(tint=(0.95, 0.2, 0.2), emit=(0.45, 0.02, 0.02), spec=0.3)))
    pop1 = ease((t - x.T[1] - 0.6) / 0.25)
    if pop1 > 0:
        nh = 'txt_47' if shift > 0.5 else 'txt_49'
        nb = 'txt_53' if shift > 0.5 else 'txt_51'
        s53 = 1 + 0.5 * ease((t - x.T[3]) / 0.25) * (1 - 0.35 * ease((t - x.T[3] - 0.3) / 0.4))
        items.append((nh, T(o + [xh, -0.1, vh * sc + 0.30]) @ S(pop1 * 0.9), dict(tint=(0.85, 0.88, 0.95))))
        items.append((nb, T(o + [xb, -0.1, vb * sc + 0.30 + 0.08 * (s53 - 1)]) @ S(pop1 * s53),
                      dict(tint=(1.0, 0.25, 0.25), emit=(0.3 + 0.9 * shift, 0.02, 0.02))))
    yr = ease((t - x.T[0] + 0.1) / 0.3)
    flip = ease((t - x.T[2]) / 0.25)
    yname = 'txt_2025' if flip > 0.5 else 'txt_2024'
    ys = yr * (abs(1 - 2 * flip) if 0 < flip < 1 else 1)
    items.append((yname, T(o + [0, 0.6, 3.78]) @ S((max(ys, 1e-3), 1, 1)), dict(tint=(0.9, 0.9, 0.92), emit=(0.05, 0.05, 0.05))))
    items.append(('txt_sub', T(o + [0, 0.6, 3.36]) @ S(yr), dict(tint=(0.8, 0.85, 0.95), emit=(0.25, 0.27, 0.32))))
    lights = [spot(o + [xh, -1.2, 4.0], o + [xh, 0, 1.0], col=(0.85, 0.9, 1.0), energy=6, outer=28, inner=12, range=12, shadow=True, sh_fov=70),
              spot(o + [xb, -1.2, 4.0], o + [xb, 0, 1.0], col=(1.0, 0.8, 0.75), energy=6, outer=28, inner=12, range=12),
              spot(o + [0, 3, 3.5], o + [0, 0, 1.2], col=(0.3, 0.5, 1.0), energy=4, outer=40, inner=20, range=12, spec=2),
              dict(type='point', pos=tuple(o + [xb, -0.8, 0.8]), col=(1.0, 0.1, 0.1), energy=0.4 + 1.2 * shift, range=3),
              dict(type='point', pos=tuple(o + [0, -3.5, 2.0]), col=(0.8, 0.85, 1.0), energy=1.2, range=10)]
    p = dict(exposure=1.1, vignette=0.6, grain=0.022, bloom=0.5, dof=1.5, focus=dist(c, o + [0, 0, 1.5]))
    return dict(items=items, cam=c, lights=lights, env=CHART_ENV, adds=[], post=p)


def s_shrimp(t, x, gt):
    k = eio(t / x.dur)
    h = lerp(0.34, 0.24, k)
    off = DESK_UP * lerp(-0.01, 0.012, k)
    eye = PHONE_C + np.array([0, 0, h]) + off - DESK_UP * 0.02
    c = dict(eye=tuple(eye + shake(t, 0.0015)), target=tuple(PHONE_C + off), fov=34, up=tuple(DESK_UP))
    s1 = ease((t - x.T[2] + 0.2) / 2.4)
    scroll = 0.07 * ease((t - x.T[1]) / 1.2) + 0.40 * s1 * (1 + 0.0 * s1)
    p = dict(dof=2.5, focus=dist(c, PHONE_C), exposure=1.05, bloom=0.35)
    fr = room_frame(t, gt, c, [(0, {})], p, scroll=scroll, man_on=False)
    fr['lights'].append(dict(type='point', pos=tuple(PHONE_C + [0, 0, 0.5]), col=(0.9, 0.85, 0.8), energy=0.03, range=2))
    return fr


def s_who(t, x, gt):
    o = L.FARM
    k = eio(t / x.dur)
    eye = o + lerp((-0.30, 1.55, 1.30), (-0.30, 2.25, 1.27), k)
    tgt = o + lerp((-0.95, 2.05, 1.12), (-0.95, 2.75, 1.08), k)
    c = cam(eye, tgt, 30, t, 0.002)
    cellf = 4.0 if int(gt * 3) % 2 == 0 else 7.0
    return farm_frame(t, gt, c, cellf, 3.0, dict(dof=4, focus=dist(c, tgt)))


def s_ceo(t, x, gt):
    wh = GLOBAL['texwh']['p_quote']
    qx, qz = L.ITEMS['p_quote'][0], L.ITEMS['p_quote'][1]
    card = np.array([qx, L.CORK_Y, qz])
    k = eio(t / x.dur)
    eye = card + lerp((-0.35, -2.25, 0.10), (-0.05, -1.32, 0.03), k)
    c = cam(eye, card + lerp((-0.12, 0, -0.02), (0, 0, 0), k), 32, t, 0.0025)
    keys = [(0, dict(head=(0, 14, 0))), (0.3, dict(G['explain_R'], head=(2, 18, 0), dur=0.6))]
    return room_frame(t, gt, c, keys, dict(dof=6, focus=dist(c, card), exposure=1.15))


def s_debunk(t, x, gt):
    k = eio(t / x.dur)
    c = cam(lerp((-0.35, -2.55, 1.62), (-0.25, -2.25, 1.62), k), (0.0, 0.8, 1.62), 42, t, 0.005)
    fall = ease((t - 0.5) / 1.6)
    keys = [(0, dict(head=(0, 0, 0))), (0.3, dict(G['think'], head=(6, -12, 6), dur=0.6))]
    return room_frame(t, gt, c, keys, dict(dof=2.5, focus=dist(c, (0, 0.6, 1.6)), exposure=1.15), sag=0.025 + 0.06 * fall, fall=fall)


CITY_ENV = dict(amb_top=(0.05, 0.065, 0.11), amb_bot=(0.004, 0.004, 0.008), fog_col=(0.015, 0.022, 0.045), fog_d=0.0042,
                bg=(0.012, 0.018, 0.04))


def s_city(t, x, gt):
    o = L.CITY
    k = eio(t / x.dur)
    eye = o + lerp((-10, -170, 62), (-4, -128, 52), k)
    tgt = o + lerp((0, 220, 22), (0, 220, 20), k)
    c = dict(eye=tuple(eye), target=tuple(tgt), fov=46, far=1500)
    items = [('city_ground', np.eye(4), {}), ('city_bldg', np.eye(4), dict(mode=1, seed=3.0, spec=0.2, tint=(1.6, 1.6, 1.8))),
             ('moon', np.eye(4), dict(emit=(2.2, 2.3, 2.6), cast=False))]
    lights = [dict(type='dir', dir=(0.4, -0.6, -0.5), col=(0.35, 0.45, 0.8), energy=0.25, spec=0.2)]
    p = dict(exposure=1.25, vignette=0.6, grain=0.025, bloom=0.6, bloom_t=0.7)
    return dict(items=items, cam=c, lights=lights, env=CITY_ENV, adds=[], post=p)


def s_twist(t, x, gt):
    k = eio(t / x.dur)
    c = cam(lerp((0.02, -1.50, 1.62), (0.0, -1.22, 1.62), k), (0, 0, 1.55), 30, t, 0.003)
    keys = [(0, dict(head=(3, 5, -4))), (x.T[0] + 0.3, dict(head=(6, 0, 0), lean=(4, 0), dur=0.9)),
            (x.T[1] - 0.2, dict(G['temple_R'], head=(4, 6, 4), lean=(5, 0), dur=0.4))]
    return room_frame(t, gt, c, keys, dict(dof=3, focus=dist(c, HEADC) - 0.1))


def s_reveal(t, x, gt):
    k = eio(t / x.dur)
    c = cam(lerp((0.05, -1.3, 1.60), (0.03, -1.05, 1.62), k), (0, 0, 1.58), 31, t, 0.003)
    g0 = x.E[1] + 0.12
    g1 = x.T[2] - 0.25
    glitch = 0.0
    if g0 <= t <= g1:
        u = (t - g0) / (g1 - g0)
        glitch = math.sin(math.pi * min(u * 1.25, 1.0)) ** 0.7 * (0.75 + 0.25 * math.sin(40 * t))
    bulb = 1.0
    if g0 <= t <= g1:
        bulb = 0.25 + 0.75 * (int(t * 17) % 3 != 0)
    keys = [(0, {}), (x.T[0] + 0.15, dict(G['hand_chest_R'], head=(2, 0, 0), dur=0.5)),
            (x.E[0] + 0.3, dict(R=REST['R'], head=(0, 0, 0), dur=0.6)),
            (x.T[2] - 0.15, dict(G['small_shrug'], head=(3, 6, -9), dur=0.4)),
            (x.T[2] + 0.95, dict(R=REST['R'], L=REST['L'], head=(2, 3, -4), dur=0.8))]
    p = dict(dof=7, focus=dist(c, HEADC), glitch=glitch * 0.42)
    return room_frame(t, gt, c, keys, p, bulb=bulb, glitch=glitch)


SCENES = {
    'hook': dict(fn=s_hook, cap_y=1380), 'name': dict(fn=s_name, cap_y=1440), 'forum': dict(fn=s_forum, cap_y=1450),
    'claim': dict(fn=s_bots, cap_y=1420), 'bots': dict(fn=s_bots, cap_y=1420), 'purpose': dict(fn=s_purpose, cap_y=1450),
    'crazy': dict(fn=s_crazy, cap_y=1420), 'chart': dict(fn=s_chart, cap_y=1230), 'shrimp': dict(fn=s_shrimp, cap_y=1500),
    'who': dict(fn=s_who, cap_y=1420), 'ceo': dict(fn=s_ceo, cap_y=1480), 'debunk': dict(fn=s_debunk, cap_y=1440),
    'city': dict(fn=s_city, cap_y=1420), 'twist': dict(fn=s_twist, cap_y=1450), 'reveal': dict(fn=s_reveal, cap_y=1420),
}
