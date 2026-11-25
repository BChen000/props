import os, bpy, sys, math, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bl
from bl import N
from sdf import tube, bezier
import wdragon as W
from mathutils import Vector, Matrix


def bone_list():
    B = []
    S = W.SPD
    B.append(("root", (-0.5, 0, 2.4), (-0.5, 0, 3.4), None, (1, 0, 0)))
    B.append(("hips", S["lumbar"][0], S["pelvis"][0], "root", (0, 0, 1)))
    tails = ["pelvis", "tail1", "tail2", "tail3", "tail4", "tail5", "tail6", "tail7"]
    for i in range(1, 8):
        B.append(("tail%d" % i, S[tails[i - 1]][0], S[tails[i]][0], "hips" if i == 1 else "tail%d" % (i - 1), (0, 0, 1)))
    B.append(("spine1", S["lumbar"][0], S["chest"][0], "root", (0, 0, 1)))
    B.append(("spine2", S["chest"][0], S["shoulder"][0], "spine1", (0, 0, 1)))
    necks = ["shoulder", "neck0", "neck1", "neck2", "neck3", "head"]
    for i in range(5):
        B.append(("neck%d" % i, S[necks[i]][0], S[necks[i + 1]][0], "spine2" if i == 0 else "neck%d" % (i - 1), (0, 0, 1)))
    B.append(("head", S["head"][0], (4.85, 0, 4.3), "neck4", (0, 0, 1)))
    B.append(("jaw", (3.5, 0, 4.25), (4.7, 0, 4.12), "head", (0, 0, 1)))
    L = W.LEG
    for s, sfx in ((1, ".L"), (-1, ".R")):
        m = lambda p: (p[0], p[1] * s, p[2])
        B.append(("uparm" + sfx, m(L["fhip"]), m(L["felb"]), "spine2", (1, 0, 0)))
        B.append(("forearm" + sfx, m(L["felb"]), m(L["fwri"]), "uparm" + sfx, (1, 0, 0)))
        B.append(("hand" + sfx, m(L["fwri"]), m(L["ftoe"]), "forearm" + sfx, (1, 0, 0)))
        B.append(("thigh" + sfx, m(L["hhip"]), m(L["hkne"]), "hips", (1, 0, 0)))
        B.append(("shin" + sfx, m(L["hkne"]), m(L["hank"]), "thigh" + sfx, (1, 0, 0)))
        B.append(("foot" + sfx, m(L["hank"]), m(L["htoe"]), "shin" + sfx, (1, 0, 0)))
        Sx, Ex, Wx = m(W.WING["S"]), m(W.WING["E"]), m(W.WING["W"])
        B.append(("wing1" + sfx, Sx, Ex, "spine2", (0, 0, 1)))
        B.append(("wing2" + sfx, Ex, Wx, "wing1" + sfx, (0, 0, 1)))
        for i, tip in enumerate(W.WING["tips"]):
            tip = np.array(m(tip)); wv = np.array(Wx)
            mid = wv + 0.5 * (tip - wv) + np.array([-0.12, 0, -0.08])
            B.append(("f%da%s" % (i + 1, sfx), tuple(wv), tuple(mid), "wing2" + sfx, (0, 0, 1)))
            B.append(("f%db%s" % (i + 1, sfx), tuple(mid), tuple(tip), "f%da%s" % (i + 1, sfx), (0, 0, 1)))
    return B


def finger_pts(B, sfx, i, n=12):
    d = {b[0]: b for b in B}
    a = np.array(d["f%da%s" % (i, sfx)][1]); m = np.array(d["f%da%s" % (i, sfx)][2]); t = np.array(d["f%db%s" % (i, sfx)][2])
    pts = []
    for k in range(n):
        u = k / (n - 1)
        if u <= 0.5:
            p = a + (m - a) * (u / 0.5)
        else:
            p = m + (t - m) * ((u - 0.5) / 0.5)
        pts.append(p)
    return np.array(pts)


def wing_mesh(B, s, sfx):
    """Returns verts, faces, weights dict, part attr (0 membrane,1 bone)."""
    d = {b[0]: b for b in B}
    V = []; F = []; WT = []; PART = []
    def add(v, w, part):
        V.append(np.array(v, float)); WT.append(w); PART.append(part); return len(V) - 1
    Sx = np.array(d["wing1" + sfx][1]); Ex = np.array(d["wing1" + sfx][2]); Wx = np.array(d["wing2" + sfx][2])
    fingers = [finger_pts(B, sfx, i) for i in range(1, 5)]
    nU, nV = 14, 12
    def fw(i, u):
        return {"f%da%s" % (i, sfx): 1 - u, "f%db%s" % (i, sfx): u} if u > 0 else {"wing2" + sfx: 1.0}
    def arm_pt(v):
        if v < 0.5:
            return Sx + (Ex - Sx) * (v / 0.5), {"wing1" + sfx: 1.0 - 0.3 * (v / 0.5), "wing2" + sfx: 0.3 * (v / 0.5)}
        return Ex + (Wx - Ex) * ((v - 0.5) / 0.5), {"wing1" + sfx: 0.3 * (1 - (v - 0.5) / 0.5), "wing2" + sfx: 0.7 + 0.3 * (v - 0.5) / 0.5}
    def interp(pa, pb, wa, wb, t):
        w = {}
        for k, val in wa.items(): w[k] = w.get(k, 0) + val * (1 - t)
        for k, val in wb.items(): w[k] = w.get(k, 0) + val * t
        return pa + (pb - pa) * t, w
    def grid(edgeA, edgeB, scallop_dir=None, scallop=0.0):
        idx = []
        for j in range(nV):
            v = j / (nV - 1)
            pa, wa = edgeA(v); pb, wb = edgeB(v)
            row = []
            for i in range(nU):
                t = i / (nU - 1)
                p, w = interp(pa, pb, wa, wb, t)
                if scallop and scallop_dir is not None:
                    p = p + scallop_dir * scallop * math.sin(math.pi * t) * (v ** 1.5)
                row.append(add(p, w, 0))
            idx.append(row)
        for j in range(nV - 1):
            for i in range(nU - 1):
                F.append((idx[j][i], idx[j][i + 1], idx[j + 1][i + 1], idx[j + 1][i]))
    # finger panels (radial from wrist)
    for i in range(3):
        fa, fb = fingers[i], fingers[i + 1]
        tipdir = (fa[-1] + fb[-1]) / 2 - Wx
        sd = -tipdir / np.linalg.norm(tipdir)
        def eA(v, fa=fa, ii=i + 1):
            k = v * (len(fa) - 1); k0 = int(min(k, len(fa) - 2)); f = k - k0
            return fa[k0] + (fa[k0 + 1] - fa[k0]) * f, fw(ii, v)
        def eB(v, fb=fb, ii=i + 2):
            k = v * (len(fb) - 1); k0 = int(min(k, len(fb) - 2)); f = k - k0
            return fb[k0] + (fb[k0 + 1] - fb[k0]) * f, fw(ii, v)
        L = np.linalg.norm(fa[-1] - fb[-1])
        grid(eA, eB, sd, 0.28 * L)
    # plagiopatagium: arm+finger4 to body flank
    f4 = fingers[3]
    bstart = Sx + np.array([-0.05, -0.08 * s, -0.05]); bend = np.array(W.WING["body_end"]) * np.array([1, s, 1])
    def eA(v):
        if v < 0.5:
            return arm_pt(v * 2 * 0.999 if v < 0.5 else 1)
        u = (v - 0.5) / 0.5
        k = u * (len(f4) - 1); k0 = int(min(k, len(f4) - 2)); f = k - k0
        return f4[k0] + (f4[k0 + 1] - f4[k0]) * f, fw(4, u)
    def eB(v):
        p = bstart + (bend - bstart) * v
        w = {"spine2": max(0, 1 - 2 * v), "spine1": 1 - abs(2 * v - 1) if v < 1 else 0, "hips": max(0, 2 * v - 1)}
        return p, {k: val for k, val in w.items() if val > 0}
    sdv = np.array([1.0, 0.0, 0.0])
    grid(eA, eB, sdv, 0.9)
    # propatagium: S->W straight leading edge vs arm
    def eA2(v):
        return arm_pt(v)
    def eB2(v):
        p = Sx + (Wx - Sx) * v + np.array([0.18, 0, 0.02]) * math.sin(math.pi * v)
        return p, {"wing1" + sfx: 1 - v, "wing2" + sfx: v}
    grid(eA2, eB2)
    # bones as tubes
    def add_tube(pts, radii, wfun):
        tv, tf, tp = tube(pts, radii, ring=8)
        base = len(V)
        for k, p in enumerate(tv):
            add(p, wfun(tp[k]), 1)
        for f in tf:
            F.append(tuple(base + x for x in f))
    arm = np.array([arm_pt(v)[0] for v in np.linspace(0, 1, 16)])
    add_tube(arm, np.interp(np.linspace(0, 1, 16), [0, 0.5, 0.52, 1], [0.15, 0.11, 0.12, 0.085]), lambda t: arm_pt(t)[1])
    for i, f in enumerate(fingers):
        add_tube(f, np.linspace(0.06, 0.015, len(f)), lambda t, ii=i + 1: fw(ii, t))
    # thumb claw
    cl = bezier(Wx, Wx + np.array([0.25, 0.05 * s, 0.12]), Wx + np.array([0.45, 0.02 * s, 0.1]), Wx + np.array([0.55, 0.0, 0.0]), 8)
    add_tube(cl, np.linspace(0.06, 0.008, 8), lambda t: {"wing2" + sfx: 1.0})
    return np.array(V), F, WT, np.array(PART)


def detail_meshes():
    """horns, teeth, spikes, claws: verts, faces, weights(list of dict), tp (0..1 along), part id"""
    V = []; F = []; WT = []; TP = []; PT = []
    def add_tube(pts, radii, bone, part, ring=10, squash=None):
        tv, tf, tp = tube(pts, radii, ring=ring)
        if squash is not None:
            c = np.repeat(np.array(pts), ring, axis=0)
            c = np.vstack([c, [pts[-1], pts[0]]])
            tv = c + (tv - c) * np.array(squash)
        base = len(V)
        for k, p in enumerate(tv):
            V.append(p); WT.append(bone if isinstance(bone, dict) else {bone: 1.0}); TP.append(tp[k]); PT.append(part)
        for f in tf:
            F.append(tuple(base + x for x in f))
    for s in (1, -1):
        m = lambda p: np.array([p[0], p[1] * s, p[2]])
        add_tube(bezier(m((3.36, 0.2, 4.68)), m((3.0, 0.3, 4.92)), m((2.6, 0.4, 5.02)), m((2.28, 0.44, 5.32)), 18),
                 np.linspace(0.105, 0.012, 18) ** 1.0, "head", 0)
        add_tube(bezier(m((3.3, 0.3, 4.48)), m((3.06, 0.43, 4.53)), m((2.86, 0.5, 4.58)), m((2.7, 0.53, 4.7)), 12),
                 np.linspace(0.065, 0.008, 12), "head", 0)
        add_tube(bezier(m((3.5, 0.4, 4.22)), m((3.38, 0.47, 4.2)), m((3.26, 0.51, 4.18)), m((3.16, 0.53, 4.17)), 8),
                 np.linspace(0.045, 0.006, 8), "head", 0)
        add_tube(bezier(m((3.78, 0.31, 4.73)), m((3.7, 0.35, 4.77)), m((3.62, 0.37, 4.81)), m((3.55, 0.38, 4.84)), 6),
                 np.linspace(0.035, 0.005, 6), "head", 0)
        # upper teeth
        for x in np.arange(3.92, 4.74, 0.07):
            t = (x - 3.98) / 0.74; r = 0.3 + (0.17 - 0.3) * min(max(t, 0), 1)
            zc = 4.42 + (4.3 - 4.42) * t
            y = r * 1.15 * 0.88 - 0.02
            zb = zc - r * 0.8 * 0.55 - 0.015
            ln = 0.055 + 0.03 * math.sin(x * 37) ** 2
            p0 = m((x, y, zb)); p1 = m((x - 0.01, y + 0.004, zb - ln))
            add_tube(np.linspace(p0, p1, 4), np.linspace(0.02, 0.003, 4), "head", 1, ring=6)
        # lower teeth
        for x in np.arange(3.9, 4.62, 0.075):
            t = (x - 3.55) / 1.13; r = 0.25 + (0.12 - 0.25) * t
            zc = 4.18 + (4.15 - 4.18) * t
            y = r * 1.06 - 0.035
            zt = zc + r * 0.72 * 0.6
            ln = 0.045 + 0.025 * math.cos(x * 41) ** 2
            p0 = m((x, y, zt)); p1 = m((x + 0.008, y, zt + ln))
            add_tube(np.linspace(p0, p1, 4), np.linspace(0.017, 0.003, 4), "jaw", 1, ring=6)
        # claws
        for dy in (-0.14, 0.0, 0.14):
            b = m((1.84, 0.99 + dy * 1.45, 0.09))
            add_tube(bezier(b, b + np.array([0.08, 0, 0.0]), b + np.array([0.15, 0, -0.03]), b + np.array([0.19, 0, -0.08]), 8),
                     np.linspace(0.045, 0.006, 8), "hand" + (".L" if s > 0 else ".R"), 3, ring=8)
        for dy in (-0.15, 0.0, 0.15):
            b = m((-0.6, 1.02 + dy * 1.4, 0.09))
            add_tube(bezier(b, b + np.array([0.09, 0, 0.0]), b + np.array([0.17, 0, -0.03]), b + np.array([0.21, 0, -0.08]), 8),
                     np.linspace(0.05, 0.006, 8), "foot" + (".L" if s > 0 else ".R"), 3, ring=8)
    # nose horn
    add_tube(bezier((4.6, 0, 4.48), (4.62, 0, 4.55), (4.6, 0, 4.62), (4.55, 0, 4.67), 6), np.linspace(0.04, 0.005, 6), "head", 0)
    # dorsal spikes along spine polyline
    sp = [W.SPD[n] for n in ["head", "neck3", "neck2", "neck1", "neck0", "shoulder", "chest", "lumbar", "pelvis",
                              "tail1", "tail2", "tail3", "tail4", "tail5", "tail6"]]
    seg_bones = ["neck4", "neck3", "neck2", "neck1", "neck0", "spine2", "spine1", "hips", "tail1", "tail2", "tail3",
                 "tail4", "tail5", "tail6"]
    pts = np.array([p for p, r in sp]); rad = np.array([r for p, r in sp])
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    for dist in np.arange(0.25, L[-1] - 0.3, 0.3):
        k = np.searchsorted(L, dist) - 1; k = min(max(k, 0), len(pts) - 2)
        f = (dist - L[k]) / (L[k + 1] - L[k])
        p = pts[k] + (pts[k + 1] - pts[k]) * f; r = rad[k] + (rad[k + 1] - rad[k]) * f
        tang = (pts[k + 1] - pts[k]); tang /= np.linalg.norm(tang)
        up = np.array([0, 0, 1.0]) - tang * tang[2]; up /= np.linalg.norm(up)
        top = p + up * r * (1.02 if k > 4 else 0.95)
        extra = 0.08 if 4 <= k <= 8 else 0.0
        hgt = 0.1 + 0.45 * r + extra
        if k <= 4:
            hgt *= 0.8
        back = tang
        base = top - up * 0.06
        tip = top + up * hgt + back * hgt * 0.55
        ctrl = top + up * hgt * 0.6 + back * hgt * 0.1
        add_tube(bezier(base, base + (ctrl - base) * 0.5, ctrl, tip, 7), np.linspace(0.11 * (0.5 + r), 0.004, 7) * 1.0,
                 seg_bones[k], 2, ring=8, squash=(1, 0.35, 1))
    return np.array(V), F, WT, np.array(TP), np.array(PT)


def scale_material(name, col_back, col_flank, col_belly, scale_size=16.0, glow_col=(1.0, 0.35, 0.06)):
    m, n, l, out = bl.new_mat(name)
    rest = N(n, "ShaderNodeAttribute", _attribute_name="rest")
    belly = N(n, "ShaderNodeAttribute", _attribute_name="belly")
    dors = N(n, "ShaderNodeAttribute", _attribute_name="dorsal")
    mouth = N(n, "ShaderNodeAttribute", _attribute_name="mouth")
    gland = N(n, "ShaderNodeAttribute", _attribute_name="gland")
    glow = N(n, "ShaderNodeAttribute", _attribute_name="glow", _attribute_type='OBJECT')
    v1e = N(n, "ShaderNodeTexVoronoi", Scale=scale_size, Randomness=0.85)
    v1e.feature = 'DISTANCE_TO_EDGE'
    l.new(rest.outputs["Vector"], v1e.inputs["Vector"])
    v1 = N(n, "ShaderNodeTexNoise", Scale=scale_size * 0.6, Detail=1.0)
    l.new(rest.outputs["Vector"], v1.inputs["Vector"])
    noise = N(n, "ShaderNodeTexNoise", Scale=1.6, Detail=4.0)
    l.new(rest.outputs["Vector"], noise.inputs["Vector"])
    # base color mix
    mx1 = N(n, "ShaderNodeMix", _data_type='RGBA', A=col_flank, B=col_back)
    l.new(dors.outputs["Fac"], mx1.inputs["Factor"])
    mx2 = N(n, "ShaderNodeMix", _data_type='RGBA', B=col_belly)
    l.new(mx1.outputs["Result"], mx2.inputs["A"]); l.new(belly.outputs["Fac"], mx2.inputs["Factor"])
    # per-scale variation
    hue = N(n, "ShaderNodeMix", _data_type='RGBA', _blend_type='MULTIPLY')
    hue.inputs["Factor"].default_value = 0.3
    bw = N(n, "ShaderNodeRGBToBW"); l.new(v1.outputs["Color"], bw.inputs[0])
    l.new(mx2.outputs["Result"], hue.inputs["A"]); l.new(bw.outputs[0], hue.inputs["B"])
    # crevice darkening
    cre = N(n, "ShaderNodeMapRange", **{"From Min": 0.0, "From Max": 0.12, "To Min": 0.35, "To Max": 1.0})
    l.new(v1e.outputs["Distance"], cre.inputs["Value"])
    dark = N(n, "ShaderNodeMix", _data_type='RGBA', _blend_type='MULTIPLY', Factor=1.0)
    l.new(hue.outputs["Result"], dark.inputs["A"])
    cc = N(n, "ShaderNodeCombineColor");
    for ch in ("Red", "Green", "Blue"):
        l.new(cre.outputs["Result"], cc.inputs[ch])
    l.new(cc.outputs["Color"], dark.inputs["B"])
    # mottling
    mot = N(n, "ShaderNodeMix", _data_type='RGBA', _blend_type='OVERLAY', Factor=0.25)
    l.new(dark.outputs["Result"], mot.inputs["A"]); l.new(noise.outputs["Color"], mot.inputs["B"])
    # mouth
    mm = N(n, "ShaderNodeMix", _data_type='RGBA', B=(0.18, 0.025, 0.025, 1))
    l.new(mot.outputs["Result"], mm.inputs["A"]); l.new(mouth.outputs["Fac"], mm.inputs["Factor"])
    bsdf = N(n, "ShaderNodeBsdfPrincipled", Roughness=0.42, **{"Specular IOR Level": 0.55})
    l.new(mm.outputs["Result"], bsdf.inputs["Base Color"])
    rmap = N(n, "ShaderNodeMapRange", **{"From Min": 0.0, "From Max": 0.1, "To Min": 0.75, "To Max": 0.38})
    l.new(v1e.outputs["Distance"], rmap.inputs["Value"])
    l.new(rmap.outputs["Result"], bsdf.inputs["Roughness"])
    # bump
    b1 = N(n, "ShaderNodeMapRange", **{"From Min": 0.0, "From Max": 0.15, "To Min": 0.0, "To Max": 1.0})
    l.new(v1e.outputs["Distance"], b1.inputs["Value"])
    bump = N(n, "ShaderNodeBump", Strength=0.7, Distance=0.025)
    l.new(b1.outputs["Result"], bump.inputs["Height"])
    l.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    # gland glow
    gm = N(n, "ShaderNodeMath", _operation='MULTIPLY')
    l.new(gland.outputs["Fac"], gm.inputs[0]); l.new(glow.outputs["Fac"], gm.inputs[1])
    gm2 = N(n, "ShaderNodeMath", _operation='MULTIPLY'); gm2.inputs[1].default_value = 6.0
    l.new(gm.outputs["Value"], gm2.inputs[0])
    crev = N(n, "ShaderNodeMapRange", **{"From Min": 0.0, "From Max": 0.05, "To Min": 1.0, "To Max": 0.08})
    l.new(v1e.outputs["Distance"], crev.inputs["Value"])
    gm3 = N(n, "ShaderNodeMath", _operation='MULTIPLY')
    l.new(gm2.outputs["Value"], gm3.inputs[0]); l.new(crev.outputs["Result"], gm3.inputs[1])
    bsdf.inputs["Emission Color"].default_value = (*glow_col, 1)
    l.new(gm3.outputs["Value"], bsdf.inputs["Emission Strength"])
    l.new(bsdf.outputs[0], out.inputs[0])
    return m


def horn_material(name, base=(0.03, 0.025, 0.02), tip=(0.55, 0.48, 0.38)):
    m, n, l, out = bl.new_mat(name)
    tp = N(n, "ShaderNodeAttribute", _attribute_name="tp")
    part = N(n, "ShaderNodeAttribute", _attribute_name="part")
    ramp = N(n, "ShaderNodeMix", _data_type='RGBA', A=(*base, 1), B=(*tip, 1))
    pw = N(n, "ShaderNodeMath", _operation='POWER'); pw.inputs[1].default_value = 1.6
    l.new(tp.outputs["Fac"], pw.inputs[0]); l.new(pw.outputs["Value"], ramp.inputs["Factor"])
    # teeth ivory when part==1, claws dark when part==3
    is_tooth = N(n, "ShaderNodeMath", _operation='COMPARE'); is_tooth.inputs[1].default_value = 1.0; is_tooth.inputs[2].default_value = 0.5
    l.new(part.outputs["Fac"], is_tooth.inputs[0])
    t2 = N(n, "ShaderNodeMix", _data_type='RGBA', B=(0.78, 0.72, 0.6, 1))
    l.new(ramp.outputs["Result"], t2.inputs["A"]); l.new(is_tooth.outputs["Value"], t2.inputs["Factor"])
    ring = N(n, "ShaderNodeTexWave", Scale=3.0, Distortion=2.0, Detail=3.0)
    ring.wave_type = 'BANDS'; ring.bands_direction = 'Z'
    rest = N(n, "ShaderNodeAttribute", _attribute_name="rest")
    l.new(rest.outputs["Vector"], ring.inputs["Vector"])
    bump = N(n, "ShaderNodeBump", Strength=0.25, Distance=0.01)
    l.new(ring.outputs["Fac"], bump.inputs["Height"])
    bsdf = N(n, "ShaderNodeBsdfPrincipled", Roughness=0.35)
    l.new(t2.outputs["Result"], bsdf.inputs["Base Color"]); l.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    l.new(bsdf.outputs[0], out.inputs[0])
    return m


def membrane_material(name, col=(0.06, 0.016, 0.012), trans=(0.5, 0.09, 0.03)):
    m, n, l, out = bl.new_mat(name)
    part = N(n, "ShaderNodeAttribute", _attribute_name="part")
    rest = N(n, "ShaderNodeAttribute", _attribute_name="rest")
    noise = N(n, "ShaderNodeTexNoise", Scale=2.5, Detail=6.0, Roughness=0.6)
    l.new(rest.outputs["Vector"], noise.inputs["Vector"])
    vein = N(n, "ShaderNodeTexVoronoi", Scale=1.8); vein.feature = 'DISTANCE_TO_EDGE'
    l.new(rest.outputs["Vector"], vein.inputs["Vector"])
    vm = N(n, "ShaderNodeMapRange", **{"From Min": 0.0, "From Max": 0.03, "To Min": 1.0, "To Max": 0.0})
    l.new(vein.outputs["Distance"], vm.inputs["Value"])
    c1 = N(n, "ShaderNodeMix", _data_type='RGBA', A=(*col, 1), B=(col[0] * 0.45, col[1] * 0.45, col[2] * 0.45, 1))
    l.new(vm.outputs["Result"], c1.inputs["Factor"])
    c2 = N(n, "ShaderNodeMix", _data_type='RGBA', _blend_type='OVERLAY', Factor=0.3)
    l.new(c1.outputs["Result"], c2.inputs["A"]); l.new(noise.outputs["Color"], c2.inputs["B"])
    bsdf = N(n, "ShaderNodeBsdfPrincipled", Roughness=0.55, **{"Specular IOR Level": 0.4})
    l.new(c2.outputs["Result"], bsdf.inputs["Base Color"])
    tr = N(n, "ShaderNodeBsdfTranslucent", Color=(*trans, 1))
    mix = N(n, "ShaderNodeMixShader")
    fac = N(n, "ShaderNodeMath", _operation='MULTIPLY'); fac.inputs[1].default_value = 0.25
    inv = N(n, "ShaderNodeMath", _operation='SUBTRACT'); inv.inputs[0].default_value = 1.0
    l.new(part.outputs["Fac"], inv.inputs[1]); l.new(inv.outputs["Value"], fac.inputs[0])
    l.new(fac.outputs["Value"], mix.inputs[0])
    l.new(bsdf.outputs[0], mix.inputs[1]); l.new(tr.outputs[0], mix.inputs[2])
    bump = N(n, "ShaderNodeBump", Strength=0.3, Distance=0.02)
    l.new(noise.outputs["Fac"], bump.inputs["Height"]); l.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    l.new(mix.outputs[0], out.inputs[0])
    return m


def eye_material(name, iris=(1.0, 0.45, 0.05), glow=1.5):
    m, n, l, out = bl.new_mat(name)
    tc = N(n, "ShaderNodeTexCoord")
    sep = N(n, "ShaderNodeSeparateXYZ"); l.new(tc.outputs["Object"], sep.inputs[0])
    ax = N(n, "ShaderNodeMath", _operation='ABSOLUTE'); l.new(sep.outputs["X"], ax.inputs[0])
    ay = N(n, "ShaderNodeMath", _operation='ABSOLUTE'); l.new(sep.outputs["Y"], ay.inputs[0])
    ay2 = N(n, "ShaderNodeMath", _operation='POWER'); ay2.inputs[1].default_value = 2.0; l.new(ay.outputs["Value"], ay2.inputs[0])
    slitw = N(n, "ShaderNodeMath", _operation='MULTIPLY_ADD'); slitw.inputs[1].default_value = -0.13; slitw.inputs[2].default_value = 0.13
    l.new(ay2.outputs["Value"], slitw.inputs[0])
    pup0 = N(n, "ShaderNodeMath", _operation='LESS_THAN'); l.new(ax.outputs["Value"], pup0.inputs[0]); l.new(slitw.outputs["Value"], pup0.inputs[1])
    front = N(n, "ShaderNodeMapRange", **{"From Min": 0.55, "From Max": 0.7, "To Min": 0.0, "To Max": 1.0})
    l.new(sep.outputs["Z"], front.inputs["Value"])
    pup = N(n, "ShaderNodeMath", _operation='MULTIPLY'); l.new(pup0.outputs["Value"], pup.inputs[0]); l.new(front.outputs["Result"], pup.inputs[1])
    capm = N(n, "ShaderNodeMapRange", **{"From Min": 0.15, "From Max": 0.45, "To Min": 0.0, "To Max": 1.0})
    l.new(sep.outputs["Z"], capm.inputs["Value"])
    rad = N(n, "ShaderNodeVectorMath", _operation='LENGTH')
    cxy = N(n, "ShaderNodeCombineXYZ"); l.new(sep.outputs["X"], cxy.inputs["X"]); l.new(sep.outputs["Y"], cxy.inputs["Y"])
    l.new(cxy.outputs[0], rad.inputs[0])
    ring = N(n, "ShaderNodeMapRange", **{"From Min": 0.2, "From Max": 0.85, "To Min": 1.0, "To Max": 0.25})
    l.new(rad.outputs["Value"], ring.inputs["Value"])
    noise = N(n, "ShaderNodeTexNoise", Scale=14.0, Detail=3.0); l.new(tc.outputs["Object"], noise.inputs["Vector"])
    ic = N(n, "ShaderNodeMix", _data_type='RGBA', A=(iris[0] * 0.25, iris[1] * 0.15, iris[2] * 0.1, 1), B=(*iris, 1))
    rr = N(n, "ShaderNodeMath", _operation='MULTIPLY'); l.new(ring.outputs["Result"], rr.inputs[0]); l.new(noise.outputs["Fac"], rr.inputs[1])
    rr2 = N(n, "ShaderNodeMath", _operation='MULTIPLY'); rr2.inputs[1].default_value = 1.3
    l.new(rr.outputs["Value"], rr2.inputs[0])
    rr3 = N(n, "ShaderNodeMath", _operation='MULTIPLY'); l.new(rr2.outputs["Value"], rr3.inputs[0]); l.new(capm.outputs["Result"], rr3.inputs[1])
    l.new(rr3.outputs["Value"], ic.inputs["Factor"])
    blk = N(n, "ShaderNodeMix", _data_type='RGBA', B=(0.004, 0.003, 0.003, 1))
    l.new(ic.outputs["Result"], blk.inputs["A"]); l.new(pup.outputs["Value"], blk.inputs["Factor"])
    bsdf = N(n, "ShaderNodeBsdfPrincipled", Roughness=0.05, **{"Coat Weight": 1.0, "Coat Roughness": 0.02})
    l.new(blk.outputs["Result"], bsdf.inputs["Base Color"])
    em = N(n, "ShaderNodeMath", _operation='MULTIPLY'); em.inputs[1].default_value = glow
    inv = N(n, "ShaderNodeMath", _operation='SUBTRACT'); inv.inputs[0].default_value = 1.0
    l.new(pup.outputs["Value"], inv.inputs[1])
    em2 = N(n, "ShaderNodeMath", _operation='MULTIPLY'); l.new(inv.outputs["Value"], em2.inputs[0]); l.new(capm.outputs["Result"], em2.inputs[1])
    l.new(em2.outputs["Value"], em.inputs[0])
    l.new(ic.outputs["Result"], bsdf.inputs["Emission Color"]); l.new(em.outputs["Value"], bsdf.inputs["Emission Strength"])
    l.new(bsdf.outputs[0], out.inputs[0])
    return m


def make_eye(name, center, side, mat, radius=0.075, parent=None, bone="head"):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=48, radius=1.0)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = (radius, radius, radius)
    if side > 0:
        R = Matrix(((-1, 0, 0), (0, 0, 1), (0, 1, 0)))
    else:
        R = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))
    ob.rotation_euler = R.to_euler()
    ob.location = Vector(center)
    for p in ob.data.polygons:
        p.use_smooth = True
    ob.data.materials.append(mat)
    if parent is not None:
        bpy.context.view_layer.update()
        mw = ob.matrix_world.copy()
        ob.parent = parent; ob.parent_type = 'BONE'; ob.parent_bone = bone
        bpy.context.view_layer.update()
        ob.matrix_world = mw
    return ob


def build(prefix="W", coll=None, palette=None):
    pal = palette or dict(back=(0.035, 0.012, 0.01, 1), flank=(0.2, 0.03, 0.018, 1), belly=(0.5, 0.24, 0.08, 1))
    W.ensure_cache()
    d = np.load(W.CACHE)
    B = bone_list()
    rig = bl.make_armature(prefix + "_rig", B, coll)
    vb, fb = d["vb"], d["fb"]
    body = bl.mesh_obj(prefix + "_body", vb, fb, coll=coll)
    jaw = bl.mesh_obj(prefix + "_jaw", d["vj"], d["fj"], coll=coll)
    wts = {b: d["wb"][:, i] for i, b in enumerate(d["bones"])}
    bl.set_weights_fast(body, wts)
    bl.set_weights_fast(jaw, {"jaw": np.ones(len(d["vj"]))})
    # masks
    me = body.data
    nrm = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("normal", nrm); nrm = nrm.reshape(-1, 3)
    x, y, z = vb[:, 0], vb[:, 1], vb[:, 2]
    spz = np.interp(x, [s[1] for s in W.SP], [s[2] for s in W.SP])
    leg = (z < 1.75) & (np.abs(y) > 0.45) | (np.abs(y) > 0.75)
    belly = np.clip((-nrm[:, 2] - 0.15) / 0.5, 0, 1) * (~leg) * np.clip((z - 0.9) / 0.4, 0, 1)
    dorsal = np.clip((nrm[:, 2] - 0.1) / 0.6, 0, 1)
    mouth = ((x > 3.75) & (x < 4.95) & (nrm[:, 2] < -0.55) & (np.abs(y) < 0.24) & (z > 4.05)).astype(float)
    gland = np.clip((-nrm[:, 2] - 0.1) / 0.5, 0, 1) * np.clip(1 - np.abs(x - 2.9) / 0.9, 0, 1) * (np.abs(y) < 0.32)
    bl.store_rest(body)
    bl.add_attr(body, "belly", belly); bl.add_attr(body, "dorsal", dorsal); bl.add_attr(body, "mouth", mouth); bl.add_attr(body, "gland", gland)
    jme = jaw.data
    jn = np.zeros(len(jme.vertices) * 3, np.float32); jme.vertices.foreach_get("normal", jn); jn = jn.reshape(-1, 3)
    vj = d["vj"]
    bl.store_rest(jaw)
    bl.add_attr(jaw, "belly", np.clip((-jn[:, 2] - 0.2) / 0.5, 0, 1)); bl.add_attr(jaw, "dorsal", np.zeros(len(vj)))
    bl.add_attr(jaw, "mouth", ((jn[:, 2] > 0.5) & (np.abs(vj[:, 1]) < 0.2)).astype(float))
    bl.add_attr(jaw, "gland", np.zeros(len(vj)))
    skin = scale_material(prefix + "_skin", pal["back"], pal["flank"], pal["belly"])
    body.data.materials.append(skin); jaw.data.materials.append(skin)
    body["glow"] = 0.0; jaw["glow"] = 0.0
    # details
    V, F, WT, TP, PT = detail_meshes()
    det = bl.mesh_obj(prefix + "_details", V, F, coll=coll)
    allb = sorted(set(k for w in WT for k in w))
    bl.set_weights_fast(det, {b: np.array([w.get(b, 0.0) for w in WT]) for b in allb})
    bl.store_rest(det); bl.add_attr(det, "tp", TP); bl.add_attr(det, "part", PT)
    det.data.materials.append(horn_material(prefix + "_horn"))
    # wings
    wing_objs = []
    mem = membrane_material(prefix + "_membrane")
    for s, sfx in ((1, ".L"), (-1, ".R")):
        V, F, WT, PT = wing_mesh(B, s, sfx)
        wo = bl.mesh_obj(prefix + "_wing" + sfx, V, F, coll=coll)
        allb = sorted(set(k for w in WT for k in w))
        bl.set_weights_fast(wo, {b: np.array([w.get(b, 0.0) for w in WT]) for b in allb})
        bl.store_rest(wo); bl.add_attr(wo, "part", PT)
        wo.data.materials.append(mem)
        wing_objs.append(wo)
    for ob in [body, jaw, det] + wing_objs:
        bl.bind(ob, rig)
    sub = body.modifiers.new("sub", 'SUBSURF'); sub.levels = 0; sub.render_levels = 0
    eyem = eye_material(prefix + "_eye")
    eyes = [make_eye(prefix + "_eyeL", (4.0, 0.3, 4.55), 1, eyem, 0.078, rig), make_eye(prefix + "_eyeR", (4.0, -0.3, 4.55), -1, eyem, 0.078, rig)]
    # mouth emitter empty
    emp = bpy.data.objects.new(prefix + "_mouth", None); bl.link(emp, coll)
    emp.location = (4.95, 0, 4.24)
    bpy.context.view_layer.update()
    mw = emp.matrix_world.copy(); emp.parent = rig; emp.parent_type = 'BONE'; emp.parent_bone = "head"
    bpy.context.view_layer.update(); emp.matrix_world = mw
    return dict(rig=rig, body=body, jaw=jaw, details=det, wings=wing_objs, eyes=eyes, mouth=emp,
                parts=[body, jaw, det] + wing_objs + eyes)


# ---------------- posing -----------------
def R(rig, bone, pitch=0.0, yaw=0.0, roll=0.0):
    pb = rig.pose.bones[bone]
    pb.rotation_euler = (pitch, roll, yaw)


def key_all(rig, frame):
    for pb in rig.pose.bones:
        pb.keyframe_insert("rotation_euler", frame=frame)
        pb.keyframe_insert("location", frame=frame)


def pose_wings(rig, lift=0.0, sweep=0.0, fold=0.0, spread=0.0, twist=0.0):
    """lift: raise wing (rad); sweep: move whole wing back(+); fold: 0 spread..1 folded; spread: extra finger spread"""
    for s, sfx in ((1, ".L"), (-1, ".R")):
        R(rig, "wing1" + sfx, pitch=lift, yaw=s * (sweep + fold * 0.9), roll=s * twist)
        R(rig, "wing2" + sfx, pitch=-fold * 0.35, yaw=-s * fold * 2.1)
        for i in range(1, 5):
            f_yaw = s * (fold * (1.75 + 0.12 * i) - spread * (i - 2.5) * 0.12)
            R(rig, "f%da%s" % (i, sfx), pitch=-fold * 0.15, yaw=f_yaw)
            R(rig, "f%db%s" % (i, sfx), pitch=0, yaw=s * fold * 0.15)


def pose_legs_flight(rig, tuck=1.0):
    for sfx in (".L", ".R"):
        R(rig, "uparm" + sfx, pitch=-0.9 * tuck)
        R(rig, "forearm" + sfx, pitch=1.4 * tuck)
        R(rig, "hand" + sfx, pitch=0.6 * tuck)
        R(rig, "thigh" + sfx, pitch=-0.95 * tuck)
        R(rig, "shin" + sfx, pitch=-0.4 * tuck)
        R(rig, "foot" + sfx, pitch=1.0 * tuck)


def pose_tail(rig, t, amp=0.06, freq=0.35, curl=0.0, lift=0.0):
    for i in range(1, 8):
        ph = 2 * math.pi * freq * t - i * 0.55
        R(rig, "tail%d" % i, pitch=lift * (1 if i < 3 else 0.4) - curl * 0.04 * i, yaw=amp * (0.5 + i * 0.25) * math.sin(ph))


def pose_neck(rig, pitch=0.0, yaw=0.0, head_pitch=0.0, head_yaw=0.0, jaw=0.0):
    for i in range(5):
        R(rig, "neck%d" % i, pitch=pitch / 5, yaw=yaw / 5)
    R(rig, "head", pitch=head_pitch, yaw=head_yaw)
    R(rig, "jaw", pitch=-jaw)
