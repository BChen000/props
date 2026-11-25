import os, sys, math, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sdf import Prim, build_field, mesh_from_field, tube, bezier

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(os.environ.get("DRAGON_CACHE", os.path.join(HERE, "cache")), "cdragon.npz")
PROF_X = [0.0, 0.6, 1.5, 3.0, 5.0, 7.5, 10.0, 12.0, 13.5, 14.6, 15.4, 16.0, 16.3]
PROF_R = [0.035, 0.08, 0.15, 0.24, 0.34, 0.42, 0.46, 0.45, 0.41, 0.35, 0.3, 0.28, 0.27]


def rad(x):
    return float(np.interp(x, PROF_X, PROF_R))


def zoff(x):
    return 0.0


def prims_body():
    P = []
    xs = np.arange(0.0, 16.31, 0.5)
    for a, b in zip(xs[:-1], xs[1:]):
        P.append(Prim("cone", "body", k=0.05, a=(a, 0, zoff(a)), b=(b, 0, zoff(b)), r1=rad(a), r2=rad(b), squash=(1, 1.0, 0.9)))
    # legs (short) front at 14.0, hind at 8.2
    for x0, sc in ((14.0, 1.0), (8.2, 1.05)):
        for s in (1, -1):
            sh = np.array([x0, 0.22 * s, -0.12]); kn = np.array([x0 - 0.3, 0.46 * s, -0.42]); an = np.array([x0 - 0.05, 0.52 * s, -0.72])
            P.append(Prim("ell", "leg", k=0.12, c=(x0 - 0.08, 0.24 * s, -0.16), r=(0.3 * sc, 0.16 * sc, 0.2 * sc)))
            P.append(Prim("cone", "leg", k=0.07, a=sh, b=kn, r1=0.15 * sc, r2=0.11 * sc))
            P.append(Prim("cone", "leg", k=0.05, a=kn, b=an, r1=0.11 * sc, r2=0.075 * sc))
            P.append(Prim("ell", "leg", k=0.04, c=an + np.array([0.08, 0.0, -0.03]), r=(0.13 * sc, 0.1 * sc, 0.06 * sc)))
            for dy, dz in ((-0.09, 0.0), (-0.03, 0.0), (0.03, 0.0), (0.09, 0.0)):
                b0 = an + np.array([0.12, dy * s * sc, -0.03]); b1 = b0 + np.array([0.16, dy * s * 0.9, -0.05])
                P.append(Prim("cone", "leg", k=0.02, a=b0, b=b1, r1=0.035 * sc, r2=0.025 * sc))
    # head
    P.append(Prim("ell", "head", k=0.14, c=(16.45, 0, 0.06), r=(0.5, 0.31, 0.29), rot=(0, 0.05, 0)))
    P.append(Prim("cone", "head", k=0.14, a=(16.7, 0, 0.04), b=(17.42, 0, -0.02), r1=0.25, r2=0.17, squash=(1, 1.1, 0.82)))
    P.append(Prim("ell", "head", k=0.1, c=(17.5, 0, 0.02), r=(0.17, 0.2, 0.15)))
    P.append(Prim("ell", "head", k=0.06, c=(17.06, 0, 0.17), r=(0.36, 0.1, 0.07), rot=(0, 0.08, 0)))
    for s in (1, -1):
        P.append(Prim("sph", "head", k=0.05, c=(17.5, 0.11 * s, 0.1), r=0.075))
        P.append(Prim("sph", "head", k=0.02, neg=True, c=(17.58, 0.115 * s, 0.11), r=0.03))
        P.append(Prim("ell", "head", k=0.07, c=(16.66, 0.205 * s, 0.29), r=(0.27, 0.11, 0.1), rot=(0, 0.1, -0.2 * s)))
        P.append(Prim("ell", "head", k=0.1, c=(16.38, 0.24 * s, -0.06), r=(0.3, 0.14, 0.19)))
        P.append(Prim("sph", "head", k=0.035, neg=True, c=(16.75, 0.262 * s, 0.17), r=0.088))
    return P


def prims_jaw():
    P = [Prim("cone", "jaw", k=0.1, a=(16.35, 0, -0.15), b=(17.2, 0, -0.18), r1=0.2, r2=0.1, squash=(1, 1.05, 0.68)),
         Prim("ell", "jaw", k=0.06, c=(17.16, 0, -0.18), r=(0.12, 0.11, 0.07))]
    for s in (1, -1):
        P.append(Prim("ell", "jaw", k=0.08, c=(16.42, 0.14 * s, -0.2), r=(0.22, 0.09, 0.12)))
    return P


def build_cache():
    pb = prims_body()
    F, lo, h = build_field(pb, 0.02)
    vb, fb = mesh_from_field(F, lo, h, target_faces=200000)
    pj = prims_jaw()
    F, lo, h = build_field(pj, 0.012)
    vj, fj = mesh_from_field(F, lo, h, target_faces=30000)
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    np.savez_compressed(CACHE, vb=vb, fb=fb, vj=vj, fj=fj)
    print("C body", len(vb), len(fb), "jaw", len(vj))


def ensure_cache():
    if not os.path.exists(CACHE):
        build_cache()


if __name__ == "__main__":
    build_cache()
