"""robin / bird.py: a procedural European robin for Blender 4.0 (EEVEE Legacy), ~8 cm tall at s=1.

The body is an implicit blend of an ellipsoid and a breast sphere; plumage colour (olive-brown crown and back,
blue-grey border, orange face and breast, white belly) comes from object-space masks in mat_feather(), with soft
borders, an overlapping-feather relief and fine barbs. Each folded wing and the tail are built from individual
feather meshes laid on the body surface (found by bisecting the body function), bottom layer first, with custom
split normals copied from the smooth body so the layers shade as one surface.

build_robin(name, s) -> dict(root, hip, body, neck, head, beak, beak_tip, tail, wings)
  root      empty at the feet (perch contact); +Y forward, +Z up. Rotate/translate this to place the bird.
  hip       body pivot (local (0, -0.004, 0.040)); rotation_euler.x pitches the body (negative = lean forward)
  neck      head pivot on the hip (local (0, 0.021, 0.014)); rotation x = nod (+ up), y = roll, z = turn (+ = bird's left)
  beak_tip  Vector in neck space; world tip = neck.matrix_world @ beak_tip. The head centre is (0, 0.010, 0.009) in neck space.
Needs bblib from ../wildlore-blender-kit on sys.path.
"""
import bpy, math, numpy as np
from mathutils import Vector, Matrix, Euler, noise as mnoise
import bblib as B


def _ray_sphere(d, c, r):
    b = np.einsum('ij,j->i', d, c)
    disc = b * b - np.dot(c, c) + r * r
    t = b + np.sqrt(np.clip(disc, 0, None))
    t[disc < 0] = 0
    return t


def _ray_ellipsoid(d, ax):
    return 1.0 / np.sqrt((d[:, 0] / ax[0]) ** 2 + (d[:, 1] / ax[1]) ** 2 + (d[:, 2] / ax[2]) ** 2)


def _body_r(d, s):
    rb = _ray_ellipsoid(d, (0.029 * s, 0.041 * s, 0.031 * s))
    rc = _ray_sphere(d, np.array([0, 0.016, -0.004]) * s, 0.027 * s)
    return (rb ** 8 + rc ** 8) ** (1 / 8)


def _inside(P, s):
    n = np.linalg.norm(P, axis=1)
    d = P / np.maximum(n, 1e-9)[:, None]
    return n - _body_r(d, s)


def _surf_x(Y, Z, s):
    lo = np.zeros_like(Y)
    hi = np.full_like(Y, 0.06 * s)
    in0 = _inside(np.stack([lo, Y, Z], 1), s) < 0
    for _ in range(30):
        mid = (lo + hi) / 2
        f = _inside(np.stack([mid, Y, Z], 1), s)
        lo = np.where(f < 0, mid, lo)
        hi = np.where(f < 0, hi, mid)
    return np.where(in0, (lo + hi) / 2, 0.0)


def _surf_normal(P, sx, s):
    """outward normal of the smooth body under each point; behind the body it turns toward the flank"""
    h = 0.0004 * s
    g = np.zeros_like(P)
    for i in range(3):
        e = np.zeros(3); e[i] = h
        g[:, i] = _inside(P + e, s) - _inside(P - e, s)
    g /= np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-12)
    w = np.clip((-0.035 * s - P[:, 1]) / (0.015 * s), 0, 1)[:, None]
    side = np.array([sx * 0.88, -0.05, 0.47]); side /= np.linalg.norm(side)
    n = g * (1 - w) + side * w
    return n / np.linalg.norm(n, axis=1, keepdims=True)


def _ss(nt, x, e0, e1):
    mr = nt.new("ShaderNodeMapRange", interpolation_type='SMOOTHSTEP')
    mr.inputs["From Min"].default_value = e0
    mr.inputs["From Max"].default_value = e1
    nt.link(x, mr.inputs["Value"])
    return mr.outputs["Result"]


def mat_feather(name="RobinBody", head=False):
    """body / head plumage: soft feathered colour borders, overlapping-feather relief, fine barbs"""
    if name in B._MATS:
        return B._MATS[name]
    m, nt = B.new_mat(name)
    tc = nt.texcoord()
    oc = tc.outputs["Object"]
    sep = nt.new("ShaderNodeSeparateXYZ"); nt.link(oc, sep.inputs[0])
    y, z = sep.outputs["Y"], sep.outputs["Z"]
    # overlapping feathers: voronoi cells stretched along the body axis, dark where tucked under the feather in front
    sc_v = 430.0 if head else 250.0
    mp = nt.mapping(oc, scale=(1.0, 0.62, 1.0))
    vor = nt.voronoi(mp, scale=sc_v)
    dv = nt.new("ShaderNodeVectorMath", operation='SUBTRACT')
    nt.link(mp, dv.inputs[0]); nt.link(vor.outputs["Position"], dv.inputs[1])
    dsep = nt.new("ShaderNodeSeparateXYZ"); nt.link(dv.outputs[0], dsep.inputs[0])
    g = nt.math('MULTIPLY', nt.math('ADD', dsep.outputs["Y"], nt.math('MULTIPLY', dsep.outputs["Z"], 0.35)), sc_v)
    sh = nt.math('SUBTRACT', 0.55, g, clamp=True)
    cr = nt.new("ShaderNodeSeparateColor"); nt.link(vor.outputs["Color"], cr.inputs[0])
    cell = cr.outputs[0]
    # feathery jitter of the colour borders, partly per feather so borders follow feather edges
    nzb = nt.noise(oc, scale=180.0, detail=2.0, rough=0.6)
    nzc = nt.noise(oc, scale=520.0, detail=1.0, rough=0.5)
    jit = nt.math('ADD', nt.math('MULTIPLY', nt.math('SUBTRACT', nzb.outputs["Fac"], 0.5), 0.0055),
                  nt.math('MULTIPLY', nt.math('SUBTRACT', nzc.outputs["Fac"], 0.5), 0.0022))
    K = 230.0
    if head:
        f1 = nt.math('ADD', nt.math('SUBTRACT', y, 0.0105), jit)
        f2 = nt.math('SUBTRACT', 0.0135, nt.math('ADD', z, jit))
    else:
        f1 = nt.math('ADD', nt.math('ADD', nt.math('SUBTRACT', y, 0.004), nt.math('MULTIPLY', z, 0.25)), jit)
        f2 = nt.math('SUBTRACT', 0.026, nt.math('ADD', z, jit))
    o1 = nt.math('MULTIPLY', f1, K, clamp=True)
    o2 = nt.math('MULTIPLY', f2, K, clamp=True)
    orange = nt.math('MULTIPLY', o1, o2)
    if not head:
        o3 = nt.math('MULTIPLY', nt.math('ADD', nt.math('ADD', z, 0.019), jit), K, clamp=True)
        orange = nt.math('MULTIPLY', orange, o3)
        belly = nt.math('MULTIPLY', nt.math('SUBTRACT', -0.012, nt.math('ADD', z, nt.math('MULTIPLY', jit, 1.6))), 160.0, clamp=True)
    gw = 0.0042 if head else 0.0052
    g1 = nt.math('MULTIPLY', nt.math('ADD', f1, gw), K, clamp=True)
    g2 = nt.math('MULTIPLY', nt.math('ADD', f2, gw), K, clamp=True)
    grey = nt.math('SUBTRACT', nt.math('MULTIPLY', g1, g2), orange, clamp=True)
    if not head:
        grey = nt.math('MULTIPLY', grey, _ss(nt, nt.math('ADD', z, jit), -0.010, 0.006))
    brown = (0.090, 0.067, 0.037, 1)
    org = (0.585, 0.198, 0.045, 1)
    c = nt.mix(orange, brown, org)
    c = nt.mix(nt.math('MULTIPLY', grey, 0.85), c, (0.15, 0.162, 0.185, 1))
    if not head:
        c = nt.mix(belly, c, (0.54, 0.51, 0.46, 1))
    # barbs / fluff
    nf = nt.noise(nt.mapping(oc, scale=(1.0, 0.45, 1.0)), scale=1300.0, detail=2.0, rough=0.5)
    mot = nt.noise(nt.mapping(oc, scale=(1.0, 0.6, 1.0)), scale=330.0 if head else 210.0, detail=1.0, rough=0.5).outputs["Fac"]
    shade = nt.math('ADD', 0.86, nt.math('ADD', nt.math('MULTIPLY', mot, 0.12), nt.math('MULTIPLY', nf.outputs["Fac"], 0.08)))
    sc_n = nt.new("ShaderNodeCombineColor")
    for i in range(3):
        nt.link(shade, sc_n.inputs[i])
    c = nt.mix(1.0, c, sc_n.outputs[0], blend='MULTIPLY')
    p = B.principled(nt, Base_Color=c, Roughness=0.74, Sheen_Weight=0.6, Sheen_Roughness=0.4, Specular_IOR_Level=0.22)
    h = nt.math('ADD', nt.math('MULTIPLY', mot, 0.3), nt.math('MULTIPLY', nf.outputs["Fac"], 0.4))
    nt.link(nt.bump(h, 0.14, 0.0005), p.inputs["Normal"])
    B._MATS[name] = m
    return m


def mat_flight(name="RobinFlight"):
    """individual wing / tail feathers: colour from attributes, pale fringe on the exposed edge, shaft, barbs"""
    if name in B._MATS:
        return B._MATS[name]
    m, nt = B.new_mat(name)
    uvn = nt.new("ShaderNodeUVMap")
    sep = nt.new("ShaderNodeSeparateXYZ"); nt.link(uvn.outputs[0], sep.inputs[0])
    S, U = sep.outputs["X"], sep.outputs["Y"]
    fcol = nt.attr("fcol").outputs["Color"]
    fedge = nt.attr("fedge").outputs["Color"]
    ftip = nt.attr("ftip").outputs["Color"]
    tipamt = nt.attr("ftipamt").outputs["Fac"]
    frnd = nt.attr("frnd").outputs["Fac"]
    edge = _ss(nt, U, 0.80, 0.985)
    tipf = nt.math('MULTIPLY', _ss(nt, S, 0.80, 0.97), tipamt)
    rd = nt.math('ABSOLUTE', nt.math('SUBTRACT', U, 0.40))
    rach = nt.math('SUBTRACT', 1.0, _ss(nt, rd, 0.0, 0.035))
    rach = nt.math('MULTIPLY', rach, nt.math('MULTIPLY', _ss(nt, S, 0.04, 0.2), nt.math('SUBTRACT', 1.0, _ss(nt, S, 0.84, 0.97))))
    rach = nt.math('MULTIPLY', rach, nt.attr("frach").outputs["Fac"])
    cv = nt.new("ShaderNodeCombineXYZ")
    nt.link(nt.math('MULTIPLY', S, 30.0), cv.inputs[0])
    nt.link(nt.math('ADD', nt.math('MULTIPLY', rd, 7.0), nt.math('MULTIPLY', S, 9.0)), cv.inputs[1])
    nt.link(nt.math('MULTIPLY', frnd, 13.0), cv.inputs[2])
    bar = nt.noise(cv.outputs[0], scale=1.0, detail=2.0, rough=0.5).outputs["Fac"]
    col = nt.mix(nt.math('MULTIPLY', edge, 0.7), fcol, fedge)
    col = nt.mix(tipf, col, ftip)
    shade = nt.math('ADD', nt.math('ADD', 0.86, nt.math('MULTIPLY', _ss(nt, S, 0.0, 0.30), 0.07)), nt.math('MULTIPLY', bar, 0.10))
    shade = nt.math('SUBTRACT', shade, nt.math('MULTIPLY', rach, 0.18))
    sc_n = nt.new("ShaderNodeCombineColor")
    for i in range(3):
        nt.link(shade, sc_n.inputs[i])
    col = nt.mix(1.0, col, sc_n.outputs[0], blend='MULTIPLY')
    p = B.principled(nt, Base_Color=col, Roughness=0.62, Sheen_Weight=0.35, Sheen_Roughness=0.35, Specular_IOR_Level=0.28)
    h = nt.math('ADD', nt.math('MULTIPLY', bar, 0.4), nt.math('MULTIPLY', rach, 0.4))
    nt.link(nt.bump(h, 0.15, 0.0003), p.inputs["Normal"])
    m.use_backface_culling = False
    B._MATS[name] = m
    return m


class _FeatherSet:
    def __init__(self):
        self.V = []; self.F = []; self.UV = []
        self.col = []; self.edge = []; self.tip = []; self.tipamt = []; self.rnd = []; self.rach = []; self.nrm = []

    def add(self, P3, uv, rows, cols, col, edge, tip=(0, 0, 0), tipamt=0.0, rnd=0.0, rach=1.0, nrm=None):
        b = len(self.V)
        self.V.extend(P3.tolist()); self.UV.extend(uv)
        for i in range(rows):
            for j in range(cols):
                a = b + i * (cols + 1) + j
                self.F.append([a, a + 1, a + cols + 2, a + cols + 1])
        n = len(P3)
        self.col += [col] * n; self.edge += [edge] * n; self.tip += [tip] * n
        self.tipamt += [tipamt] * n; self.rnd += [rnd] * n; self.rach += [rach] * n
        self.nrm.extend((np.zeros((n, 3)) if nrm is None else np.asarray(nrm)).tolist())

    def mesh(self, name):
        me = B.make_mesh(name, self.V, self.F, uv=self.UV, pattrs=dict(ftipamt=self.tipamt, frnd=self.rnd, frach=self.rach),
                         cattrs=dict(fcol=self.col, fedge=self.edge, ftip=self.tip))
        me.materials.append(mat_flight())
        # shade the feathers like the smooth surface they lie on (feather structure then reads through AO,
        # edges and colour rather than each feather looking like a rounded tube)
        N = np.asarray(self.nrm)
        if np.any(N):
            va = np.zeros(len(me.vertices) * 3, np.float32)
            me.vertices.foreach_get("normal", va)
            va = va.reshape(-1, 3)
            has = np.linalg.norm(N, axis=1) > 0
            flip = np.sign(np.einsum('ij,ij->i', va, N)); flip[flip == 0] = 1
            out = va.copy()
            mixn = N * 0.82 + va * flip[:, None] * 0.18
            mixn = mixn / np.linalg.norm(mixn, axis=1, keepdims=True) * flip[:, None]  # keep the winding's side
            out[has] = mixn[has]
            me.use_auto_smooth = True
            me.auto_smooth_angle = math.pi
            me.normals_split_custom_set_from_vertices(out.tolist())
        return me


def _feather2d(base, tip, W, cap=0.72, bow=0.0, rows=12, cols=5):
    base = np.asarray(base, float); tip = np.asarray(tip, float)
    axis = tip - base
    L = np.linalg.norm(axis)
    ax = axis / L
    perp = np.array([-ax[1], ax[0]])
    if perp[1] > 0:
        perp = -perp  # u = 1 on the lower (exposed) edge
    pts = []; uv = []
    for i in range(rows + 1):
        t = i / rows
        c = base + axis * t + perp * bow * 4 * t * (1 - t) * L
        if t < 0.12:
            w = W * (0.3 + 0.7 * t / 0.12)
        elif t < cap:
            w = W
        else:
            w = W * max(0.10, math.sqrt(max(0.0, 1 - ((t - cap) / (1 - cap)) ** 2)))
        for j in range(cols + 1):
            u = j / cols
            pts.append(c + perp * (u - 0.5) * w); uv.append((t, u))
    return np.array(pts), uv


def _wing_feathers(fs, sx, s, rng):
    """folded wing laid over the body side (hip space), built from overlapping feathers, bottom layer first"""
    def put(base, tip, W, off, col, edge, tip_c=(0, 0, 0), tipamt=0.0, cap=0.72, bow=0.0, lift=1.0, rach=1.0, utuck=0.0):
        jb = rng.normal(0, 0.00035, 2); jt = rng.normal(0, 0.0005, 2)
        P2, uv = _feather2d((np.array(base) + jb) * s, (np.array(tip) + jt) * s, W * s * rng.uniform(0.94, 1.06), cap=cap, bow=bow)
        Y, Z = P2[:, 0], P2[:, 1]
        xs = _surf_x(Y, Z, s)
        xf = 0.0042 * s
        xb = (xs ** 6 + xf ** 6) ** (1 / 6)
        t = np.array([q[0] for q in uv]); u = np.array([q[1] for q in uv])
        tuck = -0.0032 * s * (1 - np.clip(t / 0.35, 0, 1)) ** 2
        lf = lift * s * (0.00022 * t ** 1.5 + 0.00004 * (1 - (2 * u - 1) ** 2) + 0.00012 * u * t)
        ut = -utuck * s * (1 - u) ** 3
        X = sx * (xb + off * s + tuck + lf + ut)
        k = rng.uniform(0.95, 1.05)
        P3 = np.stack([X, Y, Z], 1)
        fs.add(P3, uv, 12, 5, tuple(np.array(col) * k), tuple(np.array(edge) * k), tip_c, tipamt, rng.uniform(), rach,
               nrm=_surf_normal(P3, sx, s))

    PRI = ((0.040, 0.030, 0.019), (0.115, 0.084, 0.047))
    SEC = ((0.050, 0.037, 0.023), (0.125, 0.091, 0.050))
    TER = ((0.060, 0.045, 0.027), (0.150, 0.108, 0.058))
    GCV = ((0.073, 0.054, 0.032), (0.112, 0.083, 0.047))
    MCV = ((0.088, 0.066, 0.037), (0.096, 0.072, 0.041))
    BODY = ((0.098, 0.073, 0.041), (0.102, 0.076, 0.043))
    BUFF = (0.24, 0.16, 0.075)
    # within a row each feather sits a hair above the previous one, so overlaps never share a depth
    for k in range(7):
        put((0.006, 0.0035 - 0.0011 * k), (-0.0615 + 0.0042 * k, 0.0008 - 0.0012 * k), 0.0060, 0.0008 - 0.00006 * k, *PRI, cap=0.66, bow=-0.02)
    for k in range(6):
        put((0.008 - 0.0010 * k, 0.0065 + 0.0008 * k), (-0.036 + 0.0045 * k, -0.0035 + 0.0003 * k), 0.0066, 0.0012 + 0.00006 * k, *SEC, cap=0.74)
    for k in range(3):
        put((-0.002 + 0.002 * k, 0.0150 + 0.0010 * k), (-0.040 + 0.006 * k, 0.0035 + 0.0028 * k), 0.0085 - 0.0005 * k, 0.0017 + 0.00008 * k, *TER, cap=0.70, bow=-0.03)
    for k in range(8):
        tp = np.array((-0.002 - 0.0034 * k, -0.0018 + 0.0016 * k))
        put(tp + (0.010, 0.0035), tp, 0.0072, 0.0020 + 0.00004 * k, GCV[0], tuple(np.array(GCV[0]) * 1.12), tip_c=BUFF, tipamt=0.35, cap=0.58, lift=0.15, rach=0.25)
    for k in range(6):
        tp = np.array((0.004 - 0.0031 * k, 0.0046 + 0.0015 * k))
        put(tp + (0.007, 0.003), tp, 0.0066, 0.0026 + 0.00004 * k, MCV[0], tuple(np.array(MCV[0]) * 1.05), tip_c=(0.13, 0.098, 0.056), tipamt=0.12, cap=0.55, lift=0.1, rach=0.0)
    for k in range(7):
        tp = np.array((0.002 - 0.0045 * k, 0.0185 - 0.0002 * k))
        put(tp + (0.010, 0.004), tp, 0.0080, 0.0031 + 0.00004 * k, BODY[0], BODY[0], cap=0.55, lift=0.1, rach=0.0, utuck=0.0026)


def _tail_feathers(fs, s, rng):
    col = (0.070, 0.046, 0.026); edge = (0.105, 0.070, 0.038)
    base_c = np.array([0.0, -0.030, 0.0062]) * s
    rows, cols = 14, 5
    for sx in (-1, 1):
        for k in range(5, -1, -1):  # outer pairs first (underneath)
            b = base_c + np.array([sx * 0.0007 * (k + 0.5), 0.0, -0.0007 * k]) * s
            tip = np.array([sx * (0.0010 + 0.0013 * k), -0.0810 + 0.0010 * k, -0.0160 - 0.0007 * k]) * s
            tip = tip + rng.normal(0, 0.0004, 3) * s
            axis = tip - b; L = np.linalg.norm(axis); ax = axis / L
            roll = math.radians(16 + 9 * k) * sx
            wdir = np.array([math.cos(roll), 0.0, -math.sin(roll) * 1.0])
            wdir = wdir - ax * np.dot(wdir, ax); wdir /= np.linalg.norm(wdir)
            nrm = np.cross(wdir, ax); nrm *= np.sign(nrm[2]) if nrm[2] != 0 else 1
            W = 0.0095 * s * rng.uniform(0.95, 1.05)
            P = []; uv = []
            for i in range(rows + 1):
                t = i / rows
                c = b + axis * t + nrm * 0.0006 * s * 4 * t * (1 - t)
                if t < 0.10:
                    w = W * (0.35 + 0.65 * t / 0.10)
                elif t < 0.86:
                    w = W
                else:
                    w = W * max(0.25, math.sqrt(max(0.0, 1 - ((t - 0.86) / 0.14) ** 2)))
                for j in range(cols + 1):
                    u = j / cols
                    v = (u - 0.5) * w
                    curl = 0.0004 * s * (2 * u - 1) ** 2
                    P.append(c + wdir * v * sx - nrm * curl); uv.append((t, u))
            kk = rng.uniform(0.94, 1.06)
            fs.add(np.array(P), uv, rows, cols, tuple(np.array(col) * kk), tuple(np.array(edge) * kk), (0, 0, 0), 0.0, rng.uniform())


def _displace(V, amp, s, seed=0.0):
    out = V.copy()
    for i, p in enumerate(V):
        q = Vector((p[0] / s + seed, p[1] / s, p[2] / s))
        d = mnoise.noise(q * 260.0) * 0.7 + mnoise.noise(q * 640.0) * 0.3
        n = np.linalg.norm(p)
        if n > 1e-9:
            out[i] = p * (1 + amp * s * d / n)
    return out


def build_robin(name="Robin", s=1.0):
    """bird local: +Y forward, +Z up, origin at feet (perch contact). returns dict of objects"""
    rng = np.random.default_rng(17)
    root = B.empty(name)
    hip = B.empty(name + "_hip", (0, -0.004 * s, 0.040 * s), parent=root)
    # body (centered at hip): ellipsoid blended with a breast sphere, feather-scale relief on the silhouette
    us, uf = B.unit_sphere(72, 50)
    d = us / np.linalg.norm(us, axis=1, keepdims=True)
    V = d * _body_r(d, s)[:, None]
    V = _displace(V, 0.00055, s)
    me = B.make_mesh(name + "_body", V, uf)
    me.materials.append(mat_feather())
    body = B.obj_from_mesh(name + "_body", me, parent=hip)
    # neck pivot + head (head centre and radii unchanged: shot D's pluck solve depends on them)
    neck = B.empty(name + "_neck", (0, 0.021 * s, 0.014 * s), parent=hip)
    us2, uf2 = B.unit_sphere(48, 34)
    d2 = us2 / np.linalg.norm(us2, axis=1, keepdims=True)
    rh = _ray_ellipsoid(d2, (0.0185 * s, 0.0195 * s, 0.018 * s))
    HV = _displace(d2 * rh[:, None], 0.0003, s, seed=7.3) + np.array([0, 0.010, 0.009]) * s
    hme = B.make_mesh(name + "_head", HV, uf2)
    hme.materials.append(mat_feather("RobinHead", head=True))
    head = B.obj_from_mesh(name + "_head", hme, parent=neck)
    # beak: cone along +y
    hc = np.array([0, 0.010, 0.009]) * s
    bl = 0.014 * s
    bv = [hc + np.array([0, 0.0145 * s, -0.002 * s]) + np.array([0, bl * 0.85, 0])]
    for k in range(8):
        a = 2 * math.pi * k / 8
        bv.append(hc + np.array([0.0036 * s * math.cos(a), 0.0135 * s, -0.002 * s + 0.003 * s * math.sin(a)]))
    bf = [[0, 1 + (k + 1) % 8, 1 + k] for k in range(8)] + [[1 + k for k in range(8)][::-1]]
    bme = B.make_mesh(name + "_beak", bv, bf, smooth=True)
    bme.materials.append(B.mat_simple("Beak", (0.03, 0.025, 0.02), rough=0.35, spec=0.6))
    beak = B.obj_from_mesh(name + "_beak", bme, parent=neck)
    beak_tip = Vector(bv[0])
    # eyes
    for sx in (-1, 1):
        eme = B.make_mesh(name + f"_eye{sx}", *B.unit_sphere(20, 14))
        eme.materials.append(B.mat_simple("Eye", (0.005, 0.004, 0.004), rough=0.05, spec=1.0))
        e = B.obj_from_mesh(name + f"_eye{sx}", eme, parent=neck)
        e.location = Vector(hc) + Vector((sx * 0.0142 * s, 0.0068 * s, 0.0042 * s))
        e.scale = (0.0036 * s,) * 3
    # wings: overlapping feathers folded against the body sides
    wingobjs = []
    for sx in (-1, 1):
        fs = _FeatherSet()
        _wing_feathers(fs, sx, s, rng)
        wingobjs.append(B.obj_from_mesh(name + f"_wing{sx}", fs.mesh(name + f"_wing{sx}"), parent=hip))
    # tail: twelve overlapping rectrices
    fs = _FeatherSet()
    _tail_feathers(fs, s, rng)
    tail = B.obj_from_mesh(name + "_tail", fs.mesh(name + "_tail"), parent=hip)
    # legs + toes (root space, static)
    legmat = B.mat_simple("Leg", (0.12, 0.08, 0.06), rough=0.5)
    for sx in (-1, 1):
        pts = np.array([[sx * 0.008, 0.0, 0.022], [sx * 0.0085, 0.002, 0.010], [sx * 0.009, 0.003, 0.0015]]) * s
        lv, lf, luv = B.tube_mesh(pts, np.array([0.0016, 0.0011, 0.0010]) * s, sides=6)
        V = lv.tolist(); F = list(lf)
        foot = pts[-1]
        for k, (dx, dy) in enumerate([(0.004, 0.011), (0.0, 0.012), (-0.004, 0.011), (0.0, -0.009)]):
            tp = foot + np.array([dx * s * sx, dy * s, -0.003 * s])
            tv, tf, _ = B.tube_mesh(np.array([foot, (foot + tp) / 2 + np.array([0, 0, 0.0008 * s]), tp]), np.array([0.0008, 0.0007, 0.0004]) * s, sides=5)
            base = len(V); V.extend(tv.tolist()); F.extend([[base + q for q in f] for f in tf])
        lme = B.make_mesh(name + f"_leg{sx}", V, F)
        lme.materials.append(legmat)
        B.obj_from_mesh(name + f"_leg{sx}", lme, parent=root)
    return dict(root=root, hip=hip, body=body, neck=neck, head=head, beak=beak, beak_tip=beak_tip, tail=tail, wings=wingobjs)
