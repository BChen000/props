"""The shots of the Birds Aren't Real Short. Each scene function gets (t, x, R) and returns a frame description:
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
            ('dust', np.eye(4), dict(amode=2, col=(1.0, 0.85, 0.6), int=0.45 * bulb))]


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
    keys = [(0, dict(head=(14, -6, 0))), (x.T[0] + 0.1, dict(G['finger_up_R'], head=(-1, 3, -2), dur=0.4)),
            (x.T[1] + 0.1, dict(G['explain_R'], head=(0, -4, 0), dur=0.5))]
    return room_frame(t, gt, c, keys, dict(dof=7, focus=dist(c, HEADC)), bulb=bulb)


SKY = dict(cast=False, mode=5, temit=1.0)
DAY_ENV = dict(amb_top=(0.13, 0.16, 0.21), amb_bot=(0.055, 0.05, 0.045), fog_col=(0.36, 0.44, 0.56), fog_d=0.003, fog_h=45.0)
STAGE_ENV = dict(amb_top=(0.01, 0.012, 0.018), amb_bot=(0.003, 0.003, 0.004), fog_col=(0.004, 0.005, 0.008), fog_d=0.02, bg=(0, 0, 0))
STREET_PARTS = [('st_ground', {}), ('st_road', dict(spec=0.15)), ('st_marks', {}), ('st_walk', {}), ('st_curb', {}),
                ('st_bldg', dict(mode=1, temit=0.0, seed=2.0, wsc=(2.2, 3.0), wcol=(0.05, 0.065, 0.085))), ('st_roof', {}), ('st_hq', dict(mode=1, temit=0.0, spec=1.2, shin=60, wsc=(1.6, 3.6), wcol=(0.04, 0.07, 0.10))),
                ('st_hq_base', {}), ('st_hq_canopy', {}), ('st_plaza', {}), ('st_pole', {}), ('st_ins', dict(spec=0.6)),
                ('st_wire', {}), ('car_body', dict(spec=1.0, shin=50)), ('car_glass', dict(spec=2.0, shin=90)), ('car_wheels', {}),
                ('car_lights', dict(spec=0.8)), ('bb_board', dict(tex='billboard', spec=0.05)), ('bb_frame', {})]


def street_items():
    return [('sky_day', np.eye(4), dict(SKY))] + [(nm, np.eye(4), dict(m)) for nm, m in STREET_PARTS]


def sun(direction=(0.35, 0.55, -0.75), energy=1.35):
    return dict(type='dir', dir=direction, col=(1.0, 0.93, 0.82), energy=energy, spec=0.6)


def sky_fill(energy=0.22):
    return dict(type='dir', dir=(-0.2, -0.3, -1.0), col=(0.55, 0.68, 0.95), energy=energy, spec=0.0)


def yaw_to(d):
    """Rotation turning a model that faces -Y so its nose points along the horizontal direction d."""
    a = math.atan2(d[0], -d[1])
    return euler(0, 0, a)


# ------------------------------------------------------------------ the pigeon
PIGEON_PARTS = ('pg_beak', 'pg_legs', 'pg_eyes')
WING_PIVOT = {'wing_L': (0.045, -0.02, 0.135), 'wing_R': (-0.045, -0.02, 0.135)}


def pigeon_items(M_, flap=None, led=0.0, led_col=(1.0, 0.04, 0.02), robot=False, legs=True):
    """One pigeon at M_ (feet at the origin, facing -Y). flap: wing angle in radians (None = folded, wings hidden)."""
    out = [('pg_robot' if robot else 'pg_body', M_, dict(spec=1.6 if robot else 0.25, shin=60 if robot else 20))]
    out += [(nm, M_, dict(spec=0.6)) for nm in PIGEON_PARTS if legs or nm != 'pg_legs']
    if led > 0:
        out.append(('pg_led', M_, dict(emit=tuple(c * 6.0 * led for c in led_col), cast=False)))
    if flap is not None:
        for nm, sx in (('wing_L', 1), ('wing_R', -1)):
            out.append(('pg_' + nm, M_ @ T(WING_PIVOT[nm]) @ R3(euler(0, -sx * flap, 0)), dict(spec=0.2)))
    return out


def flap_angle(t, f=7.0, amp=1.0, bias=0.15):
    return bias + amp * math.sin(2 * math.pi * f * t)


# ------------------------------------------------------------------ crowds with signs
def crowd_layout(seed, rows, width):
    r = np.random.default_rng(seed)
    out, k = [], 0
    for j, (y, n) in enumerate(rows):
        for i in range(n):
            xx = -width / 2 + width * (i + 0.5) / n + r.uniform(-0.35, 0.35) + (0.5 if j % 2 else 0.0)
            out.append((xx, y + r.uniform(-0.2, 0.2), r.uniform(-14, 14), r.uniform(0, 6.28), k))
            k += 1
    return out


def crowd_items(origin, layout, gt, signs, chant=1.0, hero=None):
    """People (pp_k parts) at origin + layout, facing -Y; arms-up people hold a sign overhead, the rest at the chest.
    signs: texture names cycled over the people; hero: (k, texture) to force one sign."""
    items = []
    for (px, py, yaw, ph, k) in layout:
        up = (k % 3 != 1)
        bob = 0.025 * chant * max(0.0, math.sin(gt * 2 * math.pi * 1.1 + ph))
        PM = T(origin + np.array([px, py, bob])) @ R3(euler(0, 0, math.radians(yaw)))
        items.append((f'pp_{k % 28}', PM, dict(spec=0.15)))
        tex = signs[k % len(signs)]
        if hero is not None and k == hero[0]:
            tex = hero[1]
        if up:
            pump = 0.10 * chant * max(0.0, math.sin(gt * 2 * math.pi * 1.1 + ph + 0.4))
            SM = PM @ T((0.0, -0.13, 1.12 + pump)) @ R3(euler(0, math.radians(4 * math.sin(gt * 1.7 + ph)), 0))
            items += [('sign_board', SM, dict(tex=tex, spec=0.05)), ('sign_stick', SM, {})]
        else:
            SM = PM @ T((0.0, -0.21, -0.2)) @ S((0.85, 1.0, 0.85))
            items.append(('sign_board', SM, dict(tex=tex, spec=0.05)))
    return items


RALLY_O = L.STREET + np.array([L.RALLY[0], 0.0, 0.16])
RALLY = crowd_layout(31, [(6.6, 7), (7.6, 7), (8.7, 6)], 13.0)
HQ_O = L.STREET + np.array([L.HQ[0], 0.0, 0.18])
HQCROWD = crowd_layout(37, [(12.5, 8), (13.6, 8), (14.8, 7), (16.0, 6)], 16.0)


def sign_center(origin, entry, gt, chant=1.0):
    px, py, yaw, ph, k = entry
    bob = 0.025 * chant * max(0.0, math.sin(gt * 2 * math.pi * 1.1 + ph))
    pump = 0.10 * chant * max(0.0, math.sin(gt * 2 * math.pi * 1.1 + ph + 0.4))
    PM = T(origin + np.array([px, py, bob])) @ R3(euler(0, 0, math.radians(yaw)))
    return (PM @ np.array([0.0, -0.15, 1.12 + pump + 1.26, 1.0]))[:3]


# ------------------------------------------------------------------ scenes
def s_chant(t, x, gt):
    k = eio(t / x.dur)
    ex = RALLY_O[0] + lerp(-3.0, 2.5, k)
    eye = np.array([ex, L.STREET[1] + 1.6, 1.45])
    c = cam(eye, np.array([ex + 0.8, L.STREET[1] + 8.0, 2.0]), 50, t, 0.012)
    c['far'] = 2500
    items = street_items() + crowd_items(RALLY_O, RALLY, gt, ['sign_real', 'sign_wake', 'sign_spies', 'sign_drones', 'sign_real'])
    lights = [sun((0.75, 0.35, -0.56)), sky_fill()]
    return dict(items=items, cam=c, lights=lights, env=DAY_ENV, adds=[],
                post=dict(exposure=1.0, vignette=0.45, grain=0.018, bloom=0.25, dof=1.2, focus=dist(c, RALLY_O + [0, 7.6, 1.8])))


def s_slogan(t, x, gt):
    k = eio(t / x.dur)
    hero = RALLY[9]
    sc = sign_center(RALLY_O, hero, gt, chant=0.6)
    eye = sc + lerp((0.45, -3.0, -0.70), (0.2, -2.3, -0.55), k)
    c = cam(eye, sc + np.array([0.0, 0.0, -0.28]), 36, t, 0.01)
    c['far'] = 2500
    items = street_items() + crowd_items(RALLY_O, RALLY, gt, ['sign_real', 'sign_wake', 'sign_drones', 'sign_real'], chant=0.6,
                                         hero=(hero[4], 'sign_spies'))
    lights = [sun((0.75, 0.35, -0.56)), sky_fill()]
    return dict(items=items, cam=c, lights=lights, env=DAY_ENV, adds=[],
                post=dict(exposure=1.0, vignette=0.5, grain=0.018, bloom=0.25, dof=4.0, focus=dist(c, sc)))


def s_lore(t, x, gt):
    o = L.STAGE
    ped = o + np.array([0.0, 0.0, 1.01])
    wide = ease((t - x.T[2] + 0.35) / 0.9) * (1 - ease((t - x.T[3] + 0.2) / 0.9))
    ang = math.radians(-18 + 26 * eio(t / x.dur))
    near = ped + np.array([1.55 * math.sin(ang), -1.55 * math.cos(ang), 0.22])
    far = o + np.array([2.2, -7.5, 2.6])
    eye = lerp(near, far, wide)
    tgt = lerp(ped + np.array([0, 0, 0.16]), o + np.array([0.0, 4.0, 2.1]), wide)
    c = cam(eye, tgt, 36, t, 0.004)
    t_scan = x.T[4] - 0.05
    scan = (t - t_scan) / 0.9
    robot = scan > 0.5
    lit = ease((t - x.T[2] + 0.1) / 0.3) * (1 - ease((t - x.T[3] + 0.1) / 0.5))
    led = 0.0 if t < t_scan + 0.6 else (1.0 if int((t - t_scan) * 3) % 2 == 0 else 0.6)
    PM = T(ped) @ R3(euler(0, 0, math.radians(8 * math.sin(gt * 0.7))))
    items = [('sg_floor', np.eye(4), dict(mode=4, seed=0.9, spec=0.4)), ('sg_wall', np.eye(4), {}),
             ('sg_pedestal', np.eye(4), dict(spec=0.8, shin=40)),
             ('sg_billion', T(o + np.array([0.0, 4.0, 2.2])), dict(emit=(4.0 * lit, 0.25 * lit, 0.15 * lit), spec=0.3))]
    items += pigeon_items(PM, led=led, robot=robot)
    lights = [spot(ped + np.array([0.3, -0.6, 3.2]), ped, col=(1.0, 0.95, 0.9), energy=3.6, outer=20, inner=10, range=8,
                   shadow=True, sh_fov=46, sh_near=0.5, sh_far=8, soft=2.0, spec=1.5),
              spot(ped + np.array([-1.5, 1.6, 1.2]), ped + [0, 0, 0.15], col=(0.35, 0.6, 1.0), energy=3.0, outer=25, inner=12, range=6, spec=2.0),
              spot(ped + np.array([1.5, 1.4, 1.0]), ped + [0, 0, 0.15], col=(0.35, 0.6, 1.0), energy=2.4, outer=25, inner=12, range=6, spec=2.0),
              dict(type='point', pos=tuple(o + np.array([0.0, 3.2, 2.2])), col=(1.0, 0.1, 0.06), energy=6.0 * lit, range=7, spec=0.3)]
    adds = []
    if 0 <= scan <= 1:
        zc = 1.32 - 0.34 * scan
        adds.append(('quad', T(ped + np.array([0, 0, zc - 1.01])) @ R3(euler(-math.pi / 2, 0, 0)) @ S(0.55),
                     dict(amode=1, col=(0.3, 1.0, 0.6), int=1.6)))
    if led > 0:
        eyep = PM @ np.array([-0.036, -0.13, 0.216, 1.0])
        adds.append(('quad', billboard(eyep[:3], c['eye'], 0.06), dict(amode=1, col=(1.0, 0.1, 0.05), int=2.0 * led)))
    return dict(items=items, cam=c, lights=lights, env=STAGE_ENV, adds=adds,
                post=dict(exposure=1.1, vignette=0.6, grain=0.022, bloom=0.5, bloom_t=0.8, dof=3.0 * (1 - wide) + 0.5, focus=dist(c, ped + [0, 0, 0.15])))


WIRE_BIRDS = [10.2, 11.5, 12.7, 13.8, 15.2, 16.6]


def wire_point(xw, dy=0.0):
    u = (xw % L.POLE_DX) / L.POLE_DX
    return L.STREET + np.array([xw, L.POLE_Y + dy, L.wire_z(u) + 0.014])


def s_wires(t, x, gt):
    k = eio(t / x.dur)
    eye = L.STREET + lerp((8.6, -6.3, 8.30), (9.0, -6.5, 8.36), k)
    tgt = L.STREET + np.array([14.0, L.POLE_Y, 8.22])
    c = cam(eye, tgt, 38, t, 0.006)
    c['far'] = 2500
    charge = ease((t - x.T[1] + 0.05) / 0.25)
    items = street_items()
    adds = []
    for i, xw in enumerate(WIRE_BIRDS):
        p = wire_point(xw)
        sway = math.radians(10 * math.sin(gt * 0.9 + i * 1.7))
        PM = T(p) @ R3(euler(0, 0, math.pi + sway))
        pulse = 0.55 + 0.45 * math.sin(gt * 6 + i * 0.8)
        items += pigeon_items(PM, led=charge * pulse, led_col=(0.1, 1.0, 0.25))
        if charge > 0:
            for j in range(2):
                fl = 0.5 + 0.5 * math.sin(gt * 37 + i * 3.1 + j * 1.7)
                q = p + np.array([(j - 0.5) * 0.06, 0.0, -0.01])
                adds.append(('quad', billboard(q, c['eye'], 0.14 + 0.06 * fl), dict(amode=1, col=(0.5, 0.8, 1.0), int=1.8 * charge * fl)))
            eyep = PM @ np.array([-0.036, -0.13, 0.216, 1.0])
            adds.append(('quad', billboard(eyep[:3], c['eye'], 0.13), dict(amode=1, col=(0.2, 1.0, 0.3), int=2.2 * charge * pulse)))
    lights = [sun((0.3, -0.62, -0.72), 1.35), sky_fill(0.25)]
    return dict(items=items, cam=c, lights=lights, env=DAY_ENV, adds=adds,
                post=dict(exposure=1.0, vignette=0.45, grain=0.018, bloom=0.35, dof=2.0, focus=dist(c, wire_point(12.7))))


def car_frame():
    return T(L.STREET + L.CAR) @ R3(euler(0, 0, -math.pi / 2))


def s_car(t, x, gt):
    k = eio(t / x.dur)
    CM = car_frame()
    hood = (CM @ np.array([0.12, -1.42, 0.93, 1.0]))[:3]
    eye = L.STREET + lerp((9.4, -8.4, 3.3), (9.8, -7.9, 3.05), k)
    c = cam(eye, hood + np.array([0.15, 0.1, 0.35]), 40, t, 0.006)
    c['far'] = 2500
    items = street_items()
    t0 = x.T[0] + 0.35
    fly = (t - t0) / 1.3
    if 0 <= fly <= 1:
        p0, p1 = hood + np.array([3.6, 1.2, 1.7]), hood + np.array([-3.8, -0.6, 1.5])
        P = lerp(p0, p1, fly)
        items += pigeon_items(T(P) @ R3(yaw_to(p1 - p0)), flap=flap_angle(t), legs=False)
    t_drop = t0 + 0.55
    t_hit = t_drop + 0.26
    if t_drop <= t < t_hit:
        u = (t - t_drop) / (t_hit - t_drop)
        src = hood + np.array([0.0, 0.0, 1.6])
        P = lerp(src, hood + [0, 0, 0.03], u * u)
        items.append(('led_dot', T(P) @ S((2.2, 2.2, 3.0)), dict(spec=0.3)))
    if t >= t_hit:
        sp = ease((t - t_hit) / 0.08)
        SM = CM @ T((0.12, -1.42, 0.932)) @ R3(euler(0.02, 0.0, 0.4)) @ S((0.6 + 0.4 * sp, 0.6 + 0.4 * sp, 1.0))
        items.append(('splat', SM, dict(spec=1.2, shin=40)))
        if t >= x.T[1] + 0.05:
            bl = 1.0 if int((t - x.T[1]) * 2.5) % 2 == 0 else 0.0
            dm = CM @ T((0.13, -1.43, 0.94))
            items.append(('led_dot', dm @ S(1.0), dict(emit=(6.0 * bl, 0.2 * bl, 0.1 * bl), cast=False)))
            c_led = (dm @ np.array([0, 0, 0, 1.0]))[:3]
            adds = [('quad', billboard(c_led, c['eye'], 0.2), dict(amode=1, col=(1.0, 0.1, 0.05), int=2.4 * bl))]
        else:
            adds = []
    else:
        adds = []
    lights = [sun((0.45, 0.5, -0.74)), sky_fill()]
    return dict(items=items, cam=c, lights=lights, env=DAY_ENV, adds=adds,
                post=dict(exposure=1.0, vignette=0.5, grain=0.018, bloom=0.35, dof=2.5, focus=dist(c, hood)))


def s_billboard(t, x, gt):
    k = eio(t / x.dur)
    bb = L.STREET + L.BILLBOARD
    eye = L.STREET + lerp((-19.0, -6.5, 1.5), (-21.5, -4.5, 1.7), k)
    tgt = bb + lerp((1.0, 0.0, 7.6), (0.4, 0.0, 7.9), k)
    c = cam(eye, tgt, 52, t, 0.006)
    c['far'] = 2500
    items = street_items()
    lights = [sun((0.2, 0.7, -0.68)), sky_fill()]
    return dict(items=items, cam=c, lights=lights, env=DAY_ENV, adds=[],
                post=dict(exposure=1.0, vignette=0.45, grain=0.018, bloom=0.25))


def s_protest(t, x, gt):
    k = eio(t / x.dur)
    eye = HQ_O + lerp((3.0, 3.5, 1.6), (1.5, 5.2, 1.7), k)
    c = cam(eye, HQ_O + lerp((0.0, 16.0, 3.2), (-0.3, 16.0, 3.9), k), 54, t, 0.01)
    c['far'] = 2500
    items = street_items() + crowd_items(HQ_O, HQCROWD, gt, ['sign_drop', 'sign_real', 'sign_drop', 'sign_spies'])
    lights = [sun((-0.7, 0.4, -0.6)), sky_fill()]
    return dict(items=items, cam=c, lights=lights, env=DAY_ENV, adds=[],
                post=dict(exposure=1.0, vignette=0.45, grain=0.018, bloom=0.3, dof=0.8, focus=dist(c, HQ_O + [0, 13.5, 1.8])))


def s_board_card(t, x, gt, name, k0=(-0.35, -2.25, 0.10), k1=(-0.05, -1.32, 0.03), keys=None, t0=0.0):
    qx, qz = L.ITEMS[name][0], L.ITEMS[name][1]
    card = np.array([qx, L.CORK_Y, qz])
    k = eio((t - t0) / max(x.dur - t0, 0.1))
    eye = card + lerp(k0, k1, k)
    c = cam(eye, card + lerp((-0.12, 0, -0.02), (0, 0, 0), k), 32, t, 0.0025)
    keys = keys or [(0, dict(head=(0, 14, 0)))]
    return room_frame(t, gt, c, keys, dict(dof=6, focus=dist(c, card), exposure=1.15))


def s_reveal(t, x, gt):
    return s_board_card(t, x, gt, 'p_clip', (-0.55, -2.3, 0.12), (-0.25, -1.25, 0.03))


def s_satire(t, x, gt):
    k = eio(t / x.dur)
    c = cam(lerp((0.10, -1.85, 1.50), (0.06, -1.60, 1.52), k), (0, 0, 1.45), 36, t)
    keys = [(0, {}), (x.T[0] + 0.05, dict(G['small_shrug'], head=(0, 0, 6), dur=0.4)),
            (x.T[1] + 0.1, dict(G['explain_R'], head=(2, -4, 0), dur=0.5)),
            (x.T[2] + 0.1, dict(G['present_R'], head=(-2, -5, 0), dur=0.5))]
    return room_frame(t, gt, c, keys, dict(dof=6, focus=dist(c, HEADC)))


def s_xdrop(t, x, gt):
    cut = x.T[1] - 0.15
    if t < cut:
        k = eio(t / cut)
        c = cam(lerp((0.06, -1.45, 1.60), (0.04, -1.30, 1.61), k), (0, 0, 1.60), 31, t)
        keys = [(0, {}), (x.T[0] + 0.05, dict(G['clasp'], head=(6, 0, 0), dur=0.35)), (x.T[0] + 0.6, dict(G['clasp'], head=(-2, 0, 0), dur=0.4))]
        return room_frame(t, gt, c, keys, dict(dof=7, focus=dist(c, HEADC)))
    return s_board_card(t, x, gt, 'p_quote', (0.85, -2.2, 0.10), (0.70, -1.45, 0.02), t0=cut)


HAT_PARTS = ('hat_crown', 'hat_band', 'hat_brim')


def hat_top_local():
    d = GLOBAL['parts']['hat_crown']
    P = np.asarray(d['pos'] if isinstance(d, dict) else d, float).reshape(-1, 3)
    top = P[P[:, 2] > P[:, 2].max() - 0.01]
    return np.array([top[:, 0].mean(), top[:, 1].mean(), P[:, 2].max()])


def s_end(t, x, gt):
    t_fly = x.T[1] + 0.25                      # the pigeon flies in during "Birds are real."
    t_land = t_fly + 1.15
    t_turn = t_land + 0.45
    t_led = t_turn + 0.6
    back = ease((t - t_fly + 0.2) / 1.1)
    k = eio(t / x.dur)
    eye = lerp(lerp((0.05, -1.35, 1.58), (0.03, -1.18, 1.60), k), (0.04, -2.05, 1.80), back)
    c = cam(eye, lerp((0.0, 0.0, 1.58), (0.0, 0.0, 1.84), back), 31, t, 0.003)
    keys = [(0, {}), (x.T[0] + 0.05, dict(G['small_shrug'], head=(0, 0, 6), dur=0.4)),
            (x.T[1] + 0.1, dict(R=REST['R'], L=REST['L'], head=(4, 0, 0), dur=0.5)),
            (t_land, dict(R=REST['R'], L=REST['L'], head=(7, 0, 0), dur=0.15)),
            (t_land + 0.25, dict(R=REST['R'], L=REST['L'], head=(2, 0, 0), dur=0.4))]
    fr = room_frame(t, gt, c, keys, dict(dof=6, focus=dist(c, HEADC + [0, 0, 0.25 * back])))
    if t >= t_fly:
        Wh = [it[1] for it in fr['items'] if it[0] == 'hat_crown'][0]
        top = Wh @ np.append(hat_top_local(), 1.0)
        top = top[:3]
        if t < t_land:
            u = (t - t_fly) / (t_land - t_fly)
            p0 = top + np.array([1.7, 0.5, 0.9])
            ctrl = top + np.array([0.6, -0.1, 0.55])
            P = (1 - u) ** 2 * p0 + 2 * (1 - u) * u * ctrl + u * u * top
            d = 2 * (1 - u) * (ctrl - p0) + 2 * u * (top - ctrl)
            fl = flap_angle(t, 7.0, 1.0 if u < 0.8 else 0.4, 0.15 if u < 0.8 else 0.9)
            fr['items'] += pigeon_items(T(P) @ R3(yaw_to(d)), flap=fl)
        else:
            d_in = top - (top + np.array([0.6, -0.1, 0.55]))
            yaw0 = math.atan2(d_in[0], -d_in[1])
            yaw = yaw0 + (0.0 - yaw0) * ease((t - t_turn) / 0.35)
            led = 0.0 if t < t_led else (0.0 if 0.45 < (t - t_led) < 0.57 else 1.0)
            settle = 0.012 * math.exp(-6 * (t - t_land)) * math.sin(18 * (t - t_land))
            PM = T(top + np.array([0, 0, settle])) @ R3(euler(0, 0, yaw))
            fr['items'] += pigeon_items(PM, led=led)
            if led > 0:
                eyep = PM @ np.array([-0.036, -0.13, 0.216, 1.0])
                fr['adds'] = fr['adds'] + [('quad', billboard(eyep[:3], c['eye'], 0.05), dict(amode=1, col=(1.0, 0.1, 0.05), int=2.4 * led))]
    return fr


SCENES = {
    'hook': dict(fn=s_hook, cap_y=1380), 'chant': dict(fn=s_chant, cap_y=1450), 'lore': dict(fn=s_lore, cap_y=1450),
    'wires': dict(fn=s_wires, cap_y=1450), 'car': dict(fn=s_car, cap_y=1450), 'slogan': dict(fn=s_slogan, cap_y=1480),
    'billboard': dict(fn=s_billboard, cap_y=1450), 'protest': dict(fn=s_protest, cap_y=1450), 'reveal': dict(fn=s_reveal, cap_y=1480),
    'satire': dict(fn=s_satire, cap_y=1420), 'xdrop': dict(fn=s_xdrop, cap_y=1450), 'end': dict(fn=s_end, cap_y=1420),
}
