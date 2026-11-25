import os, bpy, sys, math, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bl, envs
from bl import N
from sdf import Prim, build_field, mesh_from_field, bezier


def skeleton_prims():
    P = []
    # spine curve (S-shape lying in slab plane XY), z ~ 0
    spine = bezier((-2.4, -2.6, 0), (-1.0, -1.2, 0), (1.4, -0.6, 0), (1.2, 1.6, 0), 40)
    tail = bezier((-2.4, -2.6, 0), (-3.0, -3.4, 0), (-1.8, -4.6, 0), (-0.6, -4.9, 0), 30)
    neck = bezier((1.2, 1.6, 0), (1.05, 2.3, 0), (0.6, 2.7, 0), (0.15, 3.05, 0), 16)
    chain = np.vstack([tail[::-1], spine[1:], neck[1:]])
    n = len(chain)
    for i in range(1, n - 1, 1):
        p = chain[i]; d = chain[i + 1] - chain[i - 1]; d /= np.linalg.norm(d)
        t = i / n
        r = 0.05 + 0.08 * math.sin(math.pi * min(max((t - 0.05) / 0.9, 0), 1)) ** 0.7
        P.append(Prim("ell", "b", k=0.0, c=p, r=(r * 0.55, r * 0.8, r * 0.5), rot=(0, 0, math.atan2(d[1], d[0]))))
        # neural spine
        nrm = np.array([-d[1], d[0], 0])
        if 0.25 < t < 0.85 and i % 1 == 0:
            P.append(Prim("cone", "b", k=0.0, a=p, b=p - nrm * r * 1.9, r1=r * 0.22, r2=r * 0.12, squash=(1, 1, 0.5)))
    # ribs
    rib_start = 32; rib_end = 60
    for i in range(rib_start, rib_end, 2):
        p = chain[i]; d = chain[i + 1] - chain[i - 1]; d /= np.linalg.norm(d)
        nrm = np.array([-d[1], d[0], 0])
        L = 0.75 * math.sin(math.pi * (i - rib_start) / (rib_end - rib_start)) + 0.35
        for sgn in (1,):
            a = p + nrm * 0.08 * sgn
            b1 = p + nrm * L * 0.5 * sgn - d * L * 0.25
            b2 = p + nrm * L * sgn - d * L * 0.6
            pts = bezier(a, b1, b1 + (b2 - b1) * 0.5, b2, 8)
            for k in range(len(pts) - 1):
                P.append(Prim("cone", "b", k=0.0, a=pts[k], b=pts[k + 1], r1=0.035 - 0.002 * k, r2=0.033 - 0.002 * k, squash=(1, 1, 0.6)))
    # skull
    hp = neck[-1]; hd = neck[-1] - neck[-3]; hd /= np.linalg.norm(hd)
    ang = math.atan2(hd[1], hd[0])
    P.append(Prim("ell", "b", k=0.06, c=hp + hd * 0.28, r=(0.32, 0.2, 0.12), rot=(0, 0, ang)))
    P.append(Prim("cone", "b", k=0.06, a=hp + hd * 0.45, b=hp + hd * 0.95, r1=0.15, r2=0.07, squash=(1, 1, 0.6)))
    P.append(Prim("sph", "b", k=0.03, neg=True, c=hp + hd * 0.38 + np.array([0, 0, 0.1]), r=0.085))
    P.append(Prim("sph", "b", k=0.03, neg=True, c=hp + hd * 0.66 + np.array([0, 0, 0.08]), r=0.05))
    jaw_d = np.array([math.cos(ang - 0.35), math.sin(ang - 0.35), 0])
    P.append(Prim("cone", "b", k=0.03, a=hp + hd * 0.2, b=hp + hd * 0.2 + jaw_d * 0.75, r1=0.05, r2=0.03, squash=(1, 1, 0.5)))
    for s_ in (1, -1):
        hn = np.array([-hd[1], hd[0], 0]) * s_
        P.append(Prim("cone", "b", k=0.02, a=hp + hd * 0.1 + hn * 0.1, b=hp - hd * 0.25 + hn * 0.22, r1=0.04, r2=0.012))
    # limbs (front pair near shoulder i=56, hind near i=34)
    for (i0, L1, L2, ang1, ang2) in ((56, 0.6, 0.5, -0.6, 0.9), (34, 0.75, 0.6, -0.9, 0.7), (56, 0.6, 0.5, 2.4, -0.8), (34, 0.7, 0.55, 2.6, -0.7)):
        p = chain[i0]; d = chain[i0 + 1] - chain[i0 - 1]; base = math.atan2(d[1], d[0])
        a1 = base + ang1 + math.pi / 2
        e = p + np.array([math.cos(a1), math.sin(a1), 0]) * L1
        a2 = a1 + ang2
        w = e + np.array([math.cos(a2), math.sin(a2), 0]) * L2
        P.append(Prim("cone", "b", k=0.02, a=p, b=e, r1=0.06, r2=0.045, squash=(1, 1, 0.6)))
        P.append(Prim("cone", "b", k=0.02, a=e, b=w, r1=0.045, r2=0.035, squash=(1, 1, 0.6)))
        for t_ in (-0.5, 0.0, 0.5):
            a3 = a2 + t_
            P.append(Prim("cone", "b", k=0.01, a=w, b=w + np.array([math.cos(a3), math.sin(a3), 0]) * 0.22, r1=0.022, r2=0.01))
    return P


def build():
    P = skeleton_prims()
    F, lo, h = build_field(P, 0.012, pad=0.1)
    v, f = mesh_from_field(F, lo, h, target_faces=220000)
    bones = bl.mesh_obj("fossil_bones", v, f)
    bones.location.z = 0.0
    bones.scale = (1.0, 1.0, 1.4)
    bm, n, l, out = bl.new_mat("bone")
    tc = N(n, "ShaderNodeTexCoord")
    noise = N(n, "ShaderNodeTexNoise", Scale=9.0, Detail=8.0)
    l.new(tc.outputs["Object"], noise.inputs["Vector"])
    c = N(n, "ShaderNodeMix", _data_type='RGBA', A=(0.55, 0.45, 0.33, 1), B=(0.82, 0.74, 0.6, 1))
    l.new(noise.outputs["Fac"], c.inputs["Factor"])
    b = N(n, "ShaderNodeBsdfPrincipled", Roughness=0.75)
    l.new(c.outputs["Result"], b.inputs["Base Color"])
    bp = N(n, "ShaderNodeBump", Strength=0.4, Distance=0.01); l.new(noise.outputs["Fac"], bp.inputs["Height"]); l.new(bp.outputs["Normal"], b.inputs["Normal"])
    l.new(b.outputs[0], out.inputs[0])
    bones.data.materials.append(bm)
    # slab: layered sandstone heightfield with matrix
    n_ = 420
    hf = envs.fbm2(n_, 7, 11, base=6, persist=0.55)
    xs = np.linspace(-6, 6, n_)
    X, Y = np.meshgrid(xs, xs)
    sk = np.zeros_like(X)
    hgt = 0.025 * hf + 0.004 * envs.fbm2(n_, 4, 12, base=60)
    slab = envs.grid_mesh("slab", hgt, 12, 12, z0=0.0)
    sm = envs.rock_mat("sandstone", (0.3, 0.19, 0.11), (0.5, 0.35, 0.22), scale=2.2, rough=0.9, bump=0.35)
    slab.data.materials.append(sm)
    return bones, slab
