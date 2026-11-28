"""The shots of the Area 51 Short. Each scene function gets (t, x, R) and returns a frame description:
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
    tw, th = GLOBAL['texwh'].get('post', (720, 3600))
    win = min(1.0, tw * 0.150 / 0.070 / th)
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
            ('dust', np.eye(4), dict(amode=2, col=(1.0, 0.85, 0.6), int=0.8 * bulb))]


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
    keys = [(0, dict(head=(20, -6, 0))), (x.T[2] - 0.3, dict(head=(-1, 0, 0), dur=0.7))]
    return room_frame(t, gt, c, keys, dict(dof=7, focus=dist(c, HEADC)), bulb=bulb)


SKY = dict(cast=False, mode=5, temit=1.0)
DUSK_ENV = dict(amb_top=(0.10, 0.08, 0.16), amb_bot=(0.03, 0.02, 0.02), fog_col=(0.20, 0.11, 0.13), fog_d=0.0009, fog_h=60.0)
NIGHT_ENV = dict(amb_top=(0.015, 0.02, 0.04), amb_bot=(0.004, 0.004, 0.006), fog_col=(0.01, 0.012, 0.025), fog_d=0.004, fog_h=40.0)


def desert_items(sky='sky_dusk', ground_tint=(1, 1, 1)):
    return [(sky, np.eye(4), dict(SKY)), ('d_ground', np.eye(4), dict(spec=0.05, tint=ground_tint)),
            ('d_mount', np.eye(4), dict(tint=ground_tint)), ('d_runway', np.eye(4), dict(spec=0.2)), ('d_marks', np.eye(4), {}),
            ('d_hangar', np.eye(4), dict(spec=0.3)), ('d_tower', np.eye(4), {})]


def yaw_to(d):
    """Rotation turning a model that faces -Y so its nose points along the horizontal direction d."""
    a = math.atan2(d[0], -d[1])
    return euler(0, 0, a)


def s_desert(t, x, gt):
    o = L.DESERT
    p0, p1 = o + np.array([-6.0, -420.0, 60.0]), o + np.array([0.0, 300.0, 20.0])
    u = (t + 1.2) / 5.5
    jp = p0 + (p1 - p0) * u
    jm = T(jp) @ R3(yaw_to(p1 - p0) @ euler(math.radians(2.5), 0, 0))
    up = ease((t - x.T[2] + 0.5) / 1.8)
    eye = o + np.array([16.0, -330.0, 1.6])
    tgt = lerp(o + np.array([0.0, 150.0, 25.0]), o + np.array([140.0, 600.0, 520.0]), up)
    c = cam(eye, tgt, 40, t, 0.01)
    c['far'] = 4000
    glint = o + np.array([150.0 + 8 * t, 640.0, 560.0])
    gi = 0.0 if up < 0.3 else (up - 0.3) / 0.7 * (0.75 + 0.25 * math.sin(gt * 9))
    items = desert_items() + [('jet_body', jm, dict(spec=0.6, shin=40)), ('jet_stripe', jm, dict(spec=0.4))]
    lights = [dict(type='dir', dir=(0.92, 0.25, -0.20), col=(1.0, 0.56, 0.30), energy=1.1, spec=0.6),
              dict(type='point', pos=tuple(jp + [0, 0, -3]), col=(1.0, 0.2, 0.2), energy=60.0 * (int(gt * 2) % 2), range=40)]
    adds = [('quad', billboard(glint, c['eye'], 14.0), dict(amode=1, col=(1.0, 0.85, 0.6), int=2.5 * gi))]
    for wing in (-14.0, 14.0):
        pos = jp + yaw_to(p1 - p0) @ np.array([wing, 1.0, 0.0])
        adds.append(('quad', billboard(pos, c['eye'], 3.0), dict(amode=1, col=(1.0, 1.0, 1.0), int=3.0 * (int(gt * 1.5) % 2))))
    return dict(items=items, cam=c, lights=lights, env=DUSK_ENV, adds=adds,
                post=dict(exposure=1.15, vignette=0.55, grain=0.022, bloom=0.5, bloom_t=0.9))


def s_tv(t, x, gt):
    k = eio(t / x.dur)
    d = lerp(1.55, 0.95, k)
    side = DESK_R @ np.array([1.0, 0, 0])
    eye = CRT_C + CRT_N * d + side * 0.05 * (1 - k) + np.array([0, 0, -0.03])
    c = cam(eye, CRT_C + np.array([0, 0, -0.06]), 40, t, 0.003)
    fr = room_frame(t, gt, c, [(0, {})], dict(dof=4, focus=dist(c, CRT_C), exposure=1.2, bloom=0.5))
    for it in fr['items']:
        if it[0] == 'crt_screen':
            it[2]['temit'] = 0.6 * (0.93 + 0.07 * math.sin(gt * 50) * math.sin(gt * 7.3))
    return fr


HANG_ENV = dict(amb_top=(0.006, 0.007, 0.01), amb_bot=(0.002, 0.002, 0.003), fog_col=(0.004, 0.005, 0.008), fog_d=0.012)
SAUCERS = [(-12.0, 12.0), (0.0, 12.0), (12.0, 12.0), (-12.0, 30.0), (0.0, 30.0), (12.0, 30.0), (-12.0, 48.0), (0.0, 48.0), (12.0, 48.0)]


def s_saucer(t, x, gt):
    o = L.HANGAR
    k = eio(t / x.dur)
    eye = o + lerp((2.5, -6.0, 2.4), (2.0, 1.5, 2.2), k)
    c = cam(eye, o + lerp((0.0, 40.0, 1.8), (-1.0, 40.0, 1.6), k), 42, t, 0.004)
    c['far'] = 300
    offs = [x.T[1] + 0.25 + 0.42 * j for j in range(3)]        # rows switch off far to near on "No proof ever turned up."
    rows_on = [1.0 if t < offs[2 - r] else 0.0 for r in range(3)]
    items = [('h_floor', np.eye(4), dict(spec=0.35, shin=30)), ('h_shell', np.eye(4), dict(spec=0.1))]
    lights, adds = [], []
    for i, (sx, sy) in enumerate(SAUCERS):
        r = i // 3
        on = rows_on[r]
        M_ = T(o + np.array([sx, sy, 1.55 + 0.05 * math.sin(gt * 1.3 + i)])) @ R3(euler(0, 0, gt * 0.05 + i))
        items += [('saucer_body', M_, dict(spec=1.2, shin=60)), ('saucer_dome', M_, dict(spec=1.5, shin=80)),
                  ('saucer_lights', M_, dict(emit=(0.4 * on, 0.9 * on, 1.2 * on), cast=False))]
        lamp = o + np.array([sx, sy, 9.0])
        items += [('h_lamp', T(lamp), {}), ('h_lampglow', T(lamp), dict(emit=(4.0 * on, 3.6 * on, 3.0 * on), cast=False))]
    for r in range(3):
        if rows_on[r] > 0:
            y = 12.0 + 18.0 * r
            lights.append(dict(type='spot', pos=tuple(o + [0.0, y - 4, 10.0]), dir=(0, 0.25, -1), col=(1.0, 0.92, 0.8), energy=60.0,
                               outer=58, inner=35, range=40, spec=1.0, shadow=(r == 0)))
    lights.append(dict(type='point', pos=tuple(o + [0, -10, 6]), col=(0.4, 0.5, 0.7), energy=4.0, range=60))
    return dict(items=items, cam=c, lights=lights, env=HANG_ENV, adds=adds,
                post=dict(exposure=1.0, vignette=0.6, grain=0.025, bloom=0.5, dof=2.5, focus=dist(c, o + [0, 30, 1.5])))


def s_board_card(t, x, gt, name, k0=(-0.35, -2.25, 0.10), k1=(-0.05, -1.32, 0.03), keys=None):
    qx, qz = L.ITEMS[name][0], L.ITEMS[name][1]
    card = np.array([qx, L.CORK_Y, qz])
    k = eio(t / x.dur)
    eye = card + lerp(k0, k1, k)
    c = cam(eye, card + lerp((-0.12, 0, -0.02), (0, 0, 0), k), 32, t, 0.0025)
    keys = keys or [(0, dict(head=(0, 14, 0)))]
    return room_frame(t, gt, c, keys, dict(dof=6, focus=dist(c, card), exposure=1.15))


def s_cia(t, x, gt):
    return s_board_card(t, x, gt, 'p_clip', (-0.70, -2.3, 0.12), (-0.40, -1.30, 0.03))


def s_u2(t, x, gt):
    o = L.DESERT
    cut = x.T[4] - 0.12
    R_ = yaw_to(np.array([-1.0, 0.0, 0.0])) @ euler(0, math.radians(4 * math.sin(gt * 0.4)), 0)
    if t < cut:
        P = o + np.array([220.0 - 32.0 * t, 260.0, 650.0])
        eye = P + lerp(np.array([-18.0, -34.0, -6.0]), np.array([10.0, -40.0, -9.0]), eio(t / cut))
        c = cam(eye, P + np.array([-4.0, 0, 0]), 36, t, 0.02)
        sun = P + np.array([-420.0, 40.0, 30.0])
        exposure, adds = 1.15, []
    else:
        tg = t - cut
        P = o + np.array([60.0 - 22.0 * tg, 120.0, 220.0])
        eye = o + np.array([4.0, -300.0, 1.7])
        c = cam(eye, o + np.array([8.0, 200.0, 128.0 + 3.0 * tg]), 44, t, 0.004)
        sun = P + np.array([-420.0, 40.0, -60.0])
        exposure = 0.72
        adds = [('quad', billboard(P, c['eye'], 22.0), dict(amode=1, col=(1.0, 0.72, 0.42), int=0.9 + 0.15 * math.sin(gt * 7)))]
    M_ = T(P) @ R3(R_)
    c['far'] = 4000
    items = desert_items(ground_tint=(0.35, 0.33, 0.4)) + [('u2_body', M_, dict(spec=1.4, shin=50)), ('u2_canopy', M_, dict(spec=2.0, shin=90))]
    lsz, lem = (7.0, (6.0, 4.0, 1.8)) if t < cut else (1.1, (4.0, 2.7, 1.2))
    for k in range(40):
        for sx in (-24.0, 24.0):
            items.append(('quad', billboard(o + np.array([sx, -440.0 + k * 35.0, 0.5]), c['eye'], lsz), dict(mode=5, temit=0.0, cast=False, emit=lem)))
    lights = [dict(type='spot', pos=tuple(sun), dir=tuple(P - sun), col=(1.0, 0.58, 0.30), energy=1.8 * 420 ** 2, outer=7, inner=4,
                   range=3000, spec=2.5),
              dict(type='dir', dir=(0.9, 0.2, -0.4), col=(0.35, 0.3, 0.5), energy=0.18, spec=0.0)]
    env = dict(DUSK_ENV); env['amb_top'] = (0.05, 0.04, 0.09); env['fog_d'] = 0.00025; env['fog_col'] = (0.03, 0.025, 0.05)
    return dict(items=items, cam=c, lights=lights, env=env, adds=adds,
                post=dict(exposure=exposure, vignette=0.55, grain=0.022, bloom=0.6, bloom_t=0.8))


def s_quote(t, x, gt):
    k = eio(t / x.dur)
    c = cam(lerp((0.10, -1.85, 1.50), (0.06, -1.60, 1.52), k), (0, 0, 1.45), 36, t)
    keys = [(0, {}), (x.T[0] + 0.2, dict(G['explain_R'], head=(2, -4, 0), dur=0.5)),
            (x.T[2] - 0.1, dict(G['finger_up_R'], head=(0, 3, -3), dur=0.4))]
    return room_frame(t, gt, c, keys, dict(dof=6, focus=dist(c, HEADC)))


def s_itwasus(t, x, gt):
    return s_board_card(t, x, gt, 'p_quote')


def s_storm(t, x, gt):
    k = eio(t / x.dur)
    h = lerp(0.36, 0.25, k)
    off = DESK_UP * lerp(-0.01, 0.01, k)
    eye = PHONE_C + np.array([0, 0, h]) + off - DESK_UP * 0.02
    c = dict(eye=tuple(eye + shake(t, 0.0015)), target=tuple(PHONE_C + off), fov=34, up=tuple(DESK_UP))
    scroll = 0.16 * ease((t - x.T[1] + 0.2) / 1.0)
    fr = room_frame(t, gt, c, [(0, {})], dict(dof=2.5, focus=dist(c, PHONE_C), exposure=1.05, bloom=0.35), scroll=scroll, man_on=False)
    return fr


CROWD = None


def crowd_layout():
    global CROWD
    if CROWD is None:
        r = np.random.default_rng(8)
        CROWD = []
        for k in range(24):
            CROWD.append((r.uniform(-9, 9), r.uniform(-13, -4.5), r.uniform(-25, 25), r.uniform(0, 6.28), k))
    return CROWD


def s_gate(t, x, gt):
    o = L.DESERT + L.GATE
    k = eio(t / x.dur)
    eye = o + lerp((2.0, -31.0, 3.4), (0.6, -21.0, 2.25), k)
    tgt = o + lerp((0.0, 0.0, 1.5), (-0.3, 0.0, 1.55), k)
    c = cam(eye, tgt, 42, t, 0.008)
    c['far'] = 4000
    items = desert_items('sky_night', ground_tint=(0.6, 0.6, 0.7))
    items += [('g_fence', np.eye(4), dict(spec=0.6)), ('g_fence_panel', np.eye(4), dict(tex='fence', tmode=3, cast=True)),
              ('g_gate', np.eye(4), dict(spec=0.5)), ('g_arm_r', np.eye(4), dict(spec=0.6)), ('g_arm_w', np.eye(4), dict(spec=0.6)),
              ('g_signpost', np.eye(4), {}), ('g_sign', np.eye(4), dict(tex='warn', spec=0.1))]
    trM = T(o + np.array([2.5, 9.0, 0.0])) @ R3(euler(0, 0, math.radians(8)))
    items += [('truck_body', trM, dict(spec=0.7, shin=40)), ('truck_wheels', trM, {}), ('truck_glass', trM, dict(spec=1.5, shin=80)),
              ('truck_lights', trM, dict(emit=(6.0, 6.0, 5.5), cast=False))]
    for (px, py, yaw, ph, kk) in crowd_layout():
        bob = 0.015 * math.sin(gt * 2.0 + ph)
        PM = T(o + np.array([px, py, bob])) @ R3(euler(0, 0, math.radians(yaw + 180)))
        items.append((f'crowd_{kk}', PM, dict(spec=0.1)))
        if kk % 6 == 2:
            items.append(('alien_head', PM @ T((0, 0, 1.56)), dict(spec=0.4, emit=(0.02, 0.06, 0.02))))
    hl = [trM @ np.array([sx * 0.65, -2.45, 0.92, 1.0]) for sx in (-1, 1)]
    lights = [dict(type='spot', pos=tuple(hl[0][:3]), dir=(0.05, -1.0, -0.12), col=(1.0, 0.95, 0.85), energy=55, outer=26, inner=12,
                   range=60, shadow=True, sh_fov=60, sh_near=0.2, sh_far=60, spec=1.0),
              dict(type='spot', pos=tuple(hl[1][:3]), dir=(-0.05, -1.0, -0.12), col=(1.0, 0.95, 0.85), energy=55, outer=26, inner=12, range=60, spec=1.0),
              dict(type='dir', dir=(-0.3, 0.6, -0.6), col=(0.45, 0.55, 0.9), energy=0.15, spec=0.2),
              dict(type='point', pos=tuple(o + [-3.0, -7.0, 1.4]), col=(0.9, 0.95, 1.0), energy=1.2, range=8),
              dict(type='point', pos=tuple(o + [4.0, -9.0, 1.4]), col=(0.9, 0.95, 1.0), energy=1.0, range=8)]
    adds = [('quad', billboard(h_[:3], c['eye'], 1.6), dict(amode=1, col=(1.0, 0.95, 0.85), int=2.2)) for h_ in hl]
    return dict(items=items, cam=c, lights=lights, env=NIGHT_ENV, adds=adds,
                post=dict(exposure=1.2, vignette=0.6, grain=0.025, bloom=0.6, bloom_t=0.8, dof=1.5, focus=dist(c, o + [0, -2, 1.5])))


HAT_PARTS = ('hat_crown', 'hat_band', 'hat_brim')


def rot_slerp(Ra, Rb, s):
    """The rotation s of the way from Ra to Rb."""
    Rr = Ra.T @ Rb
    ang = math.acos(max(-1.0, min(1.0, (np.trace(Rr) - 1) / 2)))
    if ang < 1e-6:
        return Ra
    ax = np.array([Rr[2, 1] - Rr[1, 2], Rr[0, 2] - Rr[2, 0], Rr[1, 0] - Rr[0, 1]]) / (2 * math.sin(ang))
    K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
    a = ang * s
    return Ra @ (np.eye(3) + math.sin(a) * K + (1 - math.cos(a)) * K @ K)


def hat_local():
    """Centre and lowest z of the hat in head-local coordinates."""
    P = []
    for nm in HAT_PARTS:
        d = GLOBAL['parts'][nm]
        P.append(np.asarray(d['pos'] if isinstance(d, dict) else d, float).reshape(-1, 3))
    P = np.concatenate(P)
    return P.mean(0), P[:, 2].min()


def s_end(t, x, gt):
    tb = x.E[2] + 0.25                       # the beam comes on after "Nothing to see here."
    t_up, up_dur, up_h = tb + 0.4, 1.6, 3.9  # he is pulled up through the ceiling
    t_d = t_up + 0.55                        # the hat slips off and floats down
    drift = 1.05
    t_off = t_d + drift + 0.15               # beam off once the hat has landed
    t_on = t_off + 0.4                       # the room light flickers back on
    b = ease((t - tb) / 0.5) * (1.0 - ease((t - t_off) / 0.3))
    keys = [(0, {}), (x.T[0] + 0.1, dict(G['small_shrug'], head=(0, 0, 6), dur=0.4)),
            (x.T[1] + 0.2, dict(R=REST['R'], L=REST['L'], head=(4, 0, 0), dur=0.5)),
            (x.T[2] + 0.1, dict(G['present_R'], head=(-2, -5, 0), dur=0.5)),
            (tb, dict(R=REST['R'], L=REST['L'], head=(-25, 0, 0), dur=0.5))]
    if t < tb:
        k = eio(t / x.dur)
        c = cam(lerp((0.05, -1.35, 1.58), (0.03, -1.15, 1.60), k), np.array([0, 0, 1.58]), 31, t, 0.003)
        return room_frame(t, gt, c, keys, dict(dof=7, focus=dist(c, HEADC)))
    if t < t_on:
        bulb = 1.0 - ease((t - tb) / 0.5)
    else:
        u = t - t_on
        bulb = 0.0 if 0.07 < u < 0.19 else min(1.0, 0.6 + u * 3)
    k2 = eio((t - t_off) / 1.8)
    c = cam(lerp((0.30, -3.6, 1.0), (0.15, -2.2, 0.85), k2), lerp((0.0, 0.0, 1.55), (0.0, -0.25, 0.2), k2), 58, t, 0.002 + 0.004 * b)

    def rise_at(tt):
        return ease((tt - t_up) / up_dur) ** 1.6

    def pose_at(tt, gtt):
        p = track(keys, tt)
        r_ = rise_at(tt)
        p['root'] = (0.0, 0.0, up_h * r_, 90.0 * r_)
        return add_life(p, gtt, 0.0, 0.3, 1.0)

    fr = room_frame(t, gt, c, keys, dict(dof=3, focus=dist(c, np.array([0, 0, 1.0]))), bulb=bulb)
    fr['items'] = [it for it in fr['items'] if it[0] not in man.MAN_PARTS and not it[0].startswith(('upper_', 'fore_', 'hand_'))]
    man_its = man.items(pose_at(t, gt)) if rise_at(t) < 0.999 else []
    if t >= t_d:
        man_its = [it for it in man_its if it[0] not in HAT_PARTS]
        Wd = [it[1] for it in man.items(pose_at(t_d, gt - (t - t_d))) if it[0] == 'hat_crown'][0]
        c_loc, zb = hat_local()
        c_d = Wd[:3, :3] @ c_loc + Wd[:3, 3]
        tau = min(1.0, (t - t_d) / drift)
        c_land = np.array([c_d[0], c_d[1] - 0.25, c_loc[2] - zb])
        cen = np.array([c_d[0] + 0.10 * math.sin(tau * 2 * math.pi * 1.5) * (1 - tau), c_d[1] - 0.25 * tau,
                        c_d[2] + (c_land[2] - c_d[2]) * eio(tau)])
        Rh = rot_slerp(Wd[:3, :3], np.eye(3), eio(min(1.0, tau * 1.4)))
        sway = math.radians(14) * math.sin(tau * 2 * math.pi * 1.5) * (1 - tau)
        land = t - (t_d + drift)
        rock = math.radians(5) * math.exp(-5 * land) * math.sin(14 * land) if land > 0 else 0.0
        Rh = Rh @ euler(rock, sway, 0)
        Mh = np.eye(4); Mh[:3, :3] = Rh; Mh[:3, 3] = cen - Rh @ c_loc
        mats = {nm: dict(man.MAT.get(nm, {})) for nm in HAT_PARTS}
        man_its += [(nm, Mh, mats[nm]) for nm in HAT_PARTS]
    fr['items'] += man_its
    if b > 0:
        fr['lights'] = [l for l in fr['lights'] if not l.get('shadow')] + [
            dict(type='spot', pos=(0.0, 0.0, 3.35), dir=(0, 0.02, -1), col=(0.55, 0.95, 1.0), energy=7.0 * b, outer=24, inner=14,
                 range=8, shadow=True, soft=2.0, sh_fov=60, spec=1.5)]
        fr['adds'] = [a_ for a_ in fr['adds'] if a_[0] != 'beam'] + [
            ('beam', T((0.0, 0.0, 3.4)) @ S((0.75, 0.75, 3.4)), dict(amode=0, col=(0.55, 0.95, 1.0), int=0.35 * b)),
            ('quad', billboard(np.array([0.0, 0.0, 3.25]), c['eye'], 0.9), dict(amode=1, col=(0.6, 0.95, 1.0), int=0.8 * b))]
        fr['items'].append(('h_lampglow', T((0.0, 0.0, 3.415)) @ S((0.8, 0.8, 0.5)), dict(emit=(0.9 * b, 1.6 * b, 1.8 * b), cast=False, spec=0.0)))
    fr['post']['bloom'] = 0.45 + 0.5 * b
    return fr


SCENES = {
    'hook': dict(fn=s_hook, cap_y=1380), 'desert': dict(fn=s_desert, cap_y=1420), 'tv': dict(fn=s_tv, cap_y=1450),
    'saucer': dict(fn=s_saucer, cap_y=1420), 'cia': dict(fn=s_cia, cap_y=1480), 'u2': dict(fn=s_u2, cap_y=1420),
    'quote': dict(fn=s_quote, cap_y=1420), 'itwasus': dict(fn=s_itwasus, cap_y=1480), 'storm': dict(fn=s_storm, cap_y=1500),
    'gate': dict(fn=s_gate, cap_y=1420), 'end': dict(fn=s_end, cap_y=1420),
}
