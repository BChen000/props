import os
import bpy, math, sys
import numpy as np
from mathutils import Vector, Matrix, Euler, Quaternion
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blib import creature_rot

FPS = 24.0


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def wob(t, seed=0, freq=0.5, oct=3):
    rng = np.random.default_rng(seed)
    ph = rng.random(oct) * 6.283
    v = 0.0; a = 1.0; f = freq; s = 0.0
    for i in range(oct):
        v += a * math.sin(t * f * 6.283 + ph[i]); s += a
        a *= 0.5; f *= 2.13
    return v / s


def keyed(times_vals, t):
    """piecewise smooth interpolation through (time, value) keys"""
    if t <= times_vals[0][0]:
        return times_vals[0][1]
    for (t0, v0), (t1, v1) in zip(times_vals[:-1], times_vals[1:]):
        if t0 <= t <= t1:
            u = ease((t - t0) / max(1e-6, t1 - t0))
            if isinstance(v0, (tuple, list)):
                return tuple(a + (b - a) * u for a, b in zip(v0, v1))
            return v0 + (v1 - v0) * u
    return times_vals[-1][1]


def obj_matrix(loc, yaw=0.0, pitch=0.0, roll=0.0, scale=1.0):
    R = Euler((math.radians(pitch), math.radians(roll), math.radians(yaw)), 'YXZ').to_matrix().to_4x4()
    return Matrix.Translation(Vector(loc)) @ R @ Matrix.Diagonal((scale, scale, scale, 1.0))


def key_object(ob, frame, M):
    ob.rotation_mode = 'QUATERNION'
    ob.matrix_world = M
    ob.keyframe_insert('location', frame=frame)
    ob.keyframe_insert('rotation_quaternion', frame=frame)
    ob.keyframe_insert('scale', frame=frame)


def rest_pole(rig, upper, lower, push=3.0):
    h = rig.rest[upper].to_translation(); k = rig.rest[lower].to_translation()
    e = (rig.rest[lower] @ Matrix.Translation((0, rig.length[lower], 0))).to_translation()
    mid = (h + e) * 0.5
    return k + (k - mid) * push


def bone_tail_rest(rig, b):
    return (rig.rest[b] @ Matrix.Translation((0, rig.length[b], 0))).to_translation()


def pose_creature(rig, frame, arm_M, rots, root_off=Vector((0, 0, 0)), feet=None, legs=None):
    """rots: bone -> (rx, ry, rz) degrees creature space. feet: leg-key -> world target (or None to use rest).
    legs: dict leg-key -> (upper, lower, end)"""
    local = {}
    for b, (rx, ry, rz) in rots.items():
        if b in rig.rest:
            local[b] = rig.local_from_creature(b, creature_rot(rx, ry, rz))
    root = rig.order[0]
    if legs and feet:
        inv = arm_M.inverted()
        for key, (u, l, e) in legs.items():
            tgt = feet.get(key)
            if tgt is None:
                continue
            ta = inv @ Vector(tgt)
            pole = rest_pole(rig, u, l)
            pole = pole + root_off
            rig.ik2(local, u, l, ta, pole, end=e, root_loc=root_off)
    rig.key(frame, local, root_loc=root_off)
    return local


CHICK_LEGS = {'fl': ('f_up_L', 'f_low_L', 'f_foot_L'), 'fr': ('f_up_R', 'f_low_R', 'f_foot_R'),
              'hl': ('h_thigh_L', 'h_shin_L', 'h_paw_L'), 'hr': ('h_thigh_R', 'h_shin_R', 'h_paw_R')}
ADULT_LEGS = {'fl': ('f_up_L', 'f_low_L', 'f_foot_L'), 'fr': ('f_up_R', 'f_low_R', 'f_foot_R'),
              'hl': ('h_thigh_L', 'h_shin_L', 'h_meta_L'), 'hr': ('h_thigh_R', 'h_shin_R', 'h_meta_R')}


def rest_feet_world(rig, arm_M, legs, ground=None):
    out = {}
    for key, (u, l, e) in legs.items():
        p = bone_tail_rest(rig, l)
        w = arm_M @ p
        out[key] = w
    return out


# ------------------------------------------------------------ adult flight
def flight_rots(t, period=1.1, amp=42.0, glide=0.0, fold_up=0.18, legs='tuck', tail_wave=1.0, head=(0, 0, 0), seed=0, phase=0.0,
                dihedral=8.0, sweep=0.0):
    """returns rots dict and fold dict for feathers. glide: 0 flapping .. 1 gliding"""
    ph = 2 * math.pi * (t / period) + phase
    A = amp * (1 - glide)
    up = math.sin(ph)
    flap_h = A * up + dihedral + 2.0 * glide * wob(t, seed + 1, 0.3)
    flap_f = 0.55 * A * math.sin(ph - 0.7)
    flap_hd = 0.45 * A * math.sin(ph - 1.2)
    upstroke = max(0.0, math.cos(ph))  # wing moving up when cos>0
    fold = (fold_up * upstroke) * (1 - glide) + sweep
    rots = {}
    for side, s in (('L', 1), ('R', -1)):
        sw = 22.0 * fold
        rots['w_hum_' + side] = (0, -s * flap_h, s * (sw + 4))
        rots['w_fore_' + side] = (0, -s * flap_f, -s * sw * 1.6)
        rots['w_hand_' + side] = (5.0 * math.sin(ph - 1.4) * (1 - glide), -s * flap_hd, s * sw * 1.5)
    if legs == 'tuck':
        for side in ('L', 'R'):
            rots['f_up_' + side] = (62, 0, 0)
            rots['f_low_' + side] = (-105, 0, 0)
            rots['f_foot_' + side] = (-35, 0, 0)
            rots['h_thigh_' + side] = (42, 0, 0)
            rots['h_shin_' + side] = (18, 0, 0)
            rots['h_meta_' + side] = (8, 0, 0)
            rots['h_paw_' + side] = (25, 0, 0)
    elif legs == 'strike':
        for side in ('L', 'R'):
            rots['f_up_' + side] = (55, 0, 0)
            rots['f_low_' + side] = (-20, 0, 0)
            rots['f_foot_' + side] = (-30, 0, 0)
            rots['h_thigh_' + side] = (-50, 0, 0)
            rots['h_shin_' + side] = (-25, 0, 0)
            rots['h_meta_' + side] = (55, 0, 0)
    elif legs == 'carry':
        for side in ('L', 'R'):
            rots['f_up_' + side] = (15, 0, 0)
            rots['f_low_' + side] = (10, 0, 0)
            rots['f_foot_' + side] = (-10, 0, 0)
            rots['h_thigh_' + side] = (-55, 0, 0)
            rots['h_shin_' + side] = (-30, 0, 0)
            rots['h_meta_' + side] = (60, 0, 0)
    tw = tail_wave
    rots['tail1'] = (-6 + 3 * math.sin(ph * 0.5), 0, 4 * tw * wob(t, seed + 5, 0.4))
    rots['tail2'] = (8 + 4 * tw * math.sin(ph * 0.5 - 0.6), 0, 6 * tw * wob(t, seed + 6, 0.4))
    rots['tail3'] = (6 + 5 * tw * math.sin(ph * 0.5 - 1.2), 0, 7 * tw * wob(t, seed + 7, 0.45))
    rots['tail4'] = (5 + 5 * tw * math.sin(ph * 0.5 - 1.8), 0, 8 * tw * wob(t, seed + 8, 0.5))
    rots['tail5'] = (4 + 5 * tw * math.sin(ph * 0.5 - 2.4), 0, 8 * tw * wob(t, seed + 9, 0.5))
    hp, hy, hr = head
    rots['neck1'] = (-6 + hp * 0.3 - 2 * up * (1 - glide), 0, hy * 0.3)
    rots['neck2'] = (-4 + hp * 0.3, 0, hy * 0.3)
    rots['head'] = (6 + hp * 0.4 + 2.5 * up * (1 - glide), hr, hy * 0.4)
    rots['chest'] = (-2 * up * (1 - glide), 0, 0)
    bob = -0.07 * up * (1 - glide)
    return rots, {'L': fold, 'R': fold}, bob


def perch_rots(t, wing_spread=0.0, wing_raise=0.0, head=(0, 0, 0), seed=0, breathe=1.0, fold=0.75):
    rots = {}
    br = math.sin(t * 2 * math.pi / 3.2) * breathe
    rots['chest'] = (1.0 * br, 0, 0)
    rots['spine'] = (-0.6 * br, 0, 0)
    hp, hy, hr = head
    rots['neck1'] = (hp * 0.35 - 4, 0, hy * 0.3)
    rots['neck2'] = (hp * 0.3, 0, hy * 0.3)
    rots['head'] = (hp * 0.35 + 4, hr, hy * 0.4)
    for side, s in (('L', 1), ('R', -1)):
        f = fold * (1 - wing_spread)
        rots['w_hum_' + side] = (0, -s * (wing_raise - 62 * f), s * (80 * f))
        rots['w_fore_' + side] = (0, -s * (wing_raise * 0.3), -s * 165 * f)
        rots['w_hand_' + side] = (0, -s * 4 * f, s * 165 * f)
    rots['tail1'] = (-10, 0, 6 * wob(t, seed + 3, 0.15))
    rots['tail2'] = (-8, 0, 8 * wob(t, seed + 4, 0.15))
    rots['tail3'] = (-6, 0, 10 * wob(t, seed + 5, 0.18))
    rots['tail4'] = (12, 0, 12 * wob(t, seed + 6, 0.2))
    rots['tail5'] = (20, 0, 14 * wob(t, seed + 7, 0.25))
    return rots


def chick_rots(t, head=(0, 0, 0), wings=(0.0, 0.0), jaw=0.0, tail=(0.0, 0.0), seed=0, breathe=1.0, body=(0, 0, 0), wing_fold=0.0):
    rots = {}
    br = math.sin(t * 2 * math.pi / 1.1) * breathe
    hp, hy, hr = head
    bp, by, brl = body
    rots['hips'] = (bp * 0.3, brl * 0.5, by * 0.3)
    rots['spine'] = (bp * 0.3 + 0.8 * br, 0, by * 0.3)
    rots['chest'] = (bp * 0.4 - 0.8 * br, brl * 0.5, by * 0.4)
    rots['neck'] = (hp * 0.35, 0, hy * 0.4)
    rots['head'] = (hp * 0.65, hr, hy * 0.6)
    rots['jaw'] = (jaw, 0, 0)
    for side, s, w in (('L', 1, wings[0]), ('R', -1, wings[1])):
        rots['wing_' + side] = (-10 * wing_fold, -s * w, s * 6 * wing_fold)
    tp, ts = tail
    rots['tail1'] = (tp * 0.4, 0, ts * 0.3 + 6 * wob(t, seed + 3, 0.35))
    rots['tail2'] = (tp * 0.3, 0, ts * 0.3 + 9 * wob(t, seed + 4, 0.4))
    rots['tail3'] = (tp * 0.3, 0, ts * 0.4 + 12 * wob(t, seed + 5, 0.45))
    return rots


def saccade_track(t, keys):
    """bird-like head motion: quick moves between held poses. keys: [(time, (p,y,r))]"""
    out = keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys[:-1], keys[1:]):
        if t >= t1:
            out = v1
        elif t >= t0:
            dur = min(0.32, (t1 - t0))
            u = ease((t - t0) / dur) if t - t0 < dur else 1.0
            out = tuple(a + (b - a) * u for a, b in zip(v0, v1))
            break
    return out
