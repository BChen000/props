import os, sys, math, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sdf import Prim, build_field, mesh_from_field, bone_weights, tube, bezier

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(os.environ.get("DRAGON_CACHE", os.path.join(HERE, "cache")), "wdragon.npz")

SP = [("tail7", -8.0, 1.55, 0.035), ("tail6", -7.1, 1.62, 0.08), ("tail5", -6.2, 1.72, 0.14),
      ("tail4", -5.3, 1.84, 0.2), ("tail3", -4.45, 1.96, 0.28), ("tail2", -3.65, 2.08, 0.37),
      ("tail1", -2.85, 2.2, 0.47), ("pelvis", -2.0, 2.32, 0.58), ("lumbar", -0.95, 2.42, 0.66),
      ("chest", 0.2, 2.5, 0.72), ("shoulder", 1.1, 2.68, 0.64), ("neck0", 1.8, 3.05, 0.52),
      ("neck1", 2.3, 3.5, 0.44), ("neck2", 2.72, 3.92, 0.38), ("neck3", 3.08, 4.25, 0.345),
      ("head", 3.45, 4.42, 0.33)]
SPD = {n: (np.array([x, 0, z]), r) for n, x, z, r in SP}

SEG_BONE = {("tail7", "tail6"): "tail7", ("tail6", "tail5"): "tail6", ("tail5", "tail4"): "tail5",
            ("tail4", "tail3"): "tail4", ("tail3", "tail2"): "tail3", ("tail2", "tail1"): "tail2",
            ("tail1", "pelvis"): "tail1", ("pelvis", "lumbar"): "hips", ("lumbar", "chest"): "spine1",
            ("chest", "shoulder"): "spine2", ("shoulder", "neck0"): "neck0", ("neck0", "neck1"): "neck1",
            ("neck1", "neck2"): "neck2", ("neck2", "neck3"): "neck3", ("neck3", "head"): "neck4"}

HX, HZ = 3.45, 4.42
WING = dict(S=(1.2, 0.5, 3.12), E=(0.9, 2.3, 3.45), W=(1.55, 4.2, 3.55),
            tips=[(2.7, 7.6, 3.3), (0.7, 8.5, 3.1), (-1.25, 7.8, 3.0), (-2.55, 5.8, 2.95)],
            body_end=(-1.85, 0.55, 2.78))

LEG = dict(fhip=(1.1, 0.68, 2.15), felb=(0.82, 0.95, 1.25), fwri=(1.1, 0.97, 0.45), ftoe=(1.45, 0.99, 0.1),
           hhip=(-1.6, 0.66, 1.95), hkne=(-0.85, 0.98, 1.0), hank=(-1.5, 1.0, 0.42), htoe=(-1.08, 1.02, 0.1))


def mir(p, s):
    return (p[0], p[1] * s, p[2])


def prims_body():
    P = []
    names = [n for n, *_ in SP]
    for a, b in zip(names[:-1], names[1:]):
        pa, ra = SPD[a]; pb, rb = SPD[b]
        P.append(Prim("cone", SEG_BONE[(a, b)], k=0.12, a=pa, b=pb, r1=ra, r2=rb, squash=(1, 0.9, 1.08)))
    P.append(Prim("ell", "spine1", k=0.3, c=(0.15, 0, 2.3), r=(1.35, 0.86, 0.98)))
    P.append(Prim("ell", "hips", k=0.3, c=(-1.05, 0, 2.18), r=(1.25, 0.78, 0.82)))
    P.append(Prim("ell", "spine2", k=0.25, c=(1.05, 0, 2.45), r=(0.78, 0.74, 0.82)))
    P.append(Prim("ell", "neck4", k=0.14, c=(3.2, 0, 4.12), r=(0.4, 0.25, 0.21), rot=(0, 0.45, 0)))
    P.append(Prim("ell", "neck2", k=0.16, c=(2.5, 0, 3.55), r=(0.5, 0.32, 0.3), rot=(0, 0.75, 0)))
    P.append(Prim("ell", "neck0", k=0.2, c=(1.75, 0, 2.85), r=(0.6, 0.48, 0.48), rot=(0, 0.6, 0)))
    # head
    P.append(Prim("ell", "head", k=0.14, c=(3.72, 0, 4.45), r=(0.56, 0.36, 0.34), rot=(0, 0.12, 0)))
    P.append(Prim("cone", "head", k=0.16, a=(3.98, 0, 4.42), b=(4.72, 0, 4.3), r1=0.3, r2=0.17, squash=(1, 1.15, 0.8)))
    P.append(Prim("ell", "head", k=0.08, c=(4.78, 0, 4.3), r=(0.16, 0.19, 0.13)))
    P.append(Prim("ell", "head", k=0.1, c=(3.36, 0, 4.7), r=(0.34, 0.15, 0.14), rot=(0, -0.35, 0)))
    for s in (1, -1):
        P.append(Prim("ell", "head", k=0.07, c=(3.9, 0.235 * s, 4.66), r=(0.28, 0.1, 0.09), rot=(0, 0.15, -0.3 * s)))
        P.append(Prim("ell", "head", k=0.1, c=(3.5, 0.27 * s, 4.3), r=(0.3, 0.16, 0.22)))
        P.append(Prim("sph", "head", k=0.035, neg=True, c=(4.0, 0.3 * s, 4.55), r=0.09))
        P.append(Prim("sph", "head", k=0.02, neg=True, c=(4.86, 0.09 * s, 4.37), r=0.032))
        sfx = ".L" if s > 0 else ".R"
        # wing shoulder bulge
        P.append(Prim("ell", "spine2", k=0.18, c=(1.15, 0.42 * s, 2.98), r=(0.42, 0.24, 0.28)))
        # front leg
        sh = mir(LEG["fhip"], s); el = mir(LEG["felb"], s); wr = mir(LEG["fwri"], s); to = mir(LEG["ftoe"], s)
        P.append(Prim("ell", "spine2", k=0.2, c=mir((1.02, 0.55, 2.25), s), r=(0.55, 0.32, 0.55), rot=(0, 0.3, 0)))
        P.append(Prim("cone", "uparm" + sfx, k=0.14, a=sh, b=el, r1=0.32, r2=0.215))
        P.append(Prim("ell", "uparm" + sfx, k=0.12, c=mir((0.98, 0.84, 1.75), s), r=(0.28, 0.2, 0.42), rot=(0, 0.25, 0)))
        P.append(Prim("cone", "forearm" + sfx, k=0.07, a=el, b=wr, r1=0.215, r2=0.15))
        P.append(Prim("ell", "forearm" + sfx, k=0.08, c=mir((0.95, 0.96, 0.95), s), r=(0.2, 0.17, 0.3), rot=(0, -0.3, 0)))
        P.append(Prim("cone", "hand" + sfx, k=0.05, a=wr, b=to, r1=0.15, r2=0.13))
        P.append(Prim("ell", "hand" + sfx, k=0.06, c=mir((1.48, 0.99, 0.1), s), r=(0.27, 0.2, 0.1)))
        for k_, dy in enumerate((-0.14, 0.0, 0.14)):
            base = np.array(mir((1.55, 0.99 + dy, 0.1), s)); tip = np.array(mir((1.86, 0.99 + dy * 1.45, 0.07), s))
            P.append(Prim("cone", "hand" + sfx, k=0.035, a=base, b=tip, r1=0.075, r2=0.05))
        # hind leg
        hp = mir(LEG["hhip"], s); kn = mir(LEG["hkne"], s); an = mir(LEG["hank"], s); ht = mir(LEG["htoe"], s)
        P.append(Prim("ell", "thigh" + sfx, k=0.26, c=mir((-1.35, 0.62, 1.72), s), r=(0.78, 0.42, 0.78), rot=(0, -0.5, 0)))
        P.append(Prim("cone", "thigh" + sfx, k=0.12, a=hp, b=kn, r1=0.42, r2=0.28))
        P.append(Prim("cone", "shin" + sfx, k=0.09, a=kn, b=an, r1=0.28, r2=0.17))
        P.append(Prim("ell", "shin" + sfx, k=0.1, c=mir((-1.05, 0.98, 0.85), s), r=(0.3, 0.2, 0.32), rot=(0, 0.8, 0)))
        P.append(Prim("cone", "foot" + sfx, k=0.06, a=an, b=ht, r1=0.17, r2=0.14))
        P.append(Prim("ell", "foot" + sfx, k=0.06, c=mir((-1.0, 1.02, 0.1), s), r=(0.3, 0.22, 0.1)))
        for k_, dy in enumerate((-0.15, 0.0, 0.15)):
            base = np.array(mir((-0.92, 1.02 + dy, 0.1), s)); tip = np.array(mir((-0.58, 1.02 + dy * 1.4, 0.07), s))
            P.append(Prim("cone", "foot" + sfx, k=0.035, a=base, b=tip, r1=0.08, r2=0.055))
    return P


def prims_jaw():
    P = [Prim("cone", "jaw", k=0.1, a=(3.55, 0, 4.18), b=(4.68, 0, 4.15), r1=0.25, r2=0.12, squash=(1, 1.06, 0.72)),
         Prim("ell", "jaw", k=0.06, c=(4.64, 0, 4.14), r=(0.14, 0.13, 0.085))]
    for s in (1, -1):
        P.append(Prim("ell", "jaw", k=0.08, c=(3.62, 0.17 * s, 4.13), r=(0.24, 0.1, 0.13)))
    return P


def build_cache(h_body=0.022, h_jaw=0.012):
    pb = prims_body()
    F, lo, h = build_field(pb, h_body)
    vb, fb = mesh_from_field(F, lo, h, target_faces=260000)
    del F
    wb = bone_weights(vb, pb, tau=0.07)
    pj = prims_jaw()
    F, lo, h = build_field(pj, h_jaw)
    vj, fj = mesh_from_field(F, lo, h, target_faces=40000)
    bones = sorted(wb.keys())
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    np.savez_compressed(CACHE, vb=vb, fb=fb, vj=vj, fj=fj, bones=np.array(bones),
                        wb=np.stack([wb[b] for b in bones], 1))
    print("body verts", len(vb), "faces", len(fb), "jaw", len(vj), len(fj))


def ensure_cache():
    if not os.path.exists(CACHE):
        build_cache()


if __name__ == "__main__":
    import time
    t = time.time()
    build_cache()
    print("took %.1f" % (time.time() - t))
