"""Small numpy mesh kit: shapes as (verts, faces), bpy decimation, and triangle-soup export for the GL renderer."""
import math
import numpy as np

PARTS = {}


class M:
    def __init__(self, v, f, uv=None):
        self.v = np.asarray(v, np.float64).reshape(-1, 3)
        self.f = [tuple(int(i) for i in ff) for ff in f]
        self.uv = uv

    def copy(self):
        return M(self.v.copy(), list(self.f), None if self.uv is None else [list(u) for u in self.uv])

    def moved(self, t):
        m = self.copy(); m.v += np.asarray(t, float); return m

    def scaled(self, s):
        m = self.copy(); m.v *= np.asarray(s, float); return m

    def rotated(self, R, about=(0, 0, 0)):
        m = self.copy(); a = np.asarray(about, float); m.v = (m.v - a) @ np.asarray(R).T + a; return m

    def tris(self):
        tri, tuv = [], []
        for k, ff in enumerate(self.f):
            for j in range(1, len(ff) - 1):
                tri.append((ff[0], ff[j], ff[j + 1]))
                if self.uv is not None:
                    u = self.uv[k]
                    tuv.append((u[0], u[j], u[j + 1]))
        return np.array(tri, np.int64), (np.array(tuv, np.float64) if self.uv is not None else None)


def join(*ms):
    v, f, uvs, off, has_uv = [], [], [], 0, all(m.uv is not None for m in ms)
    for m in ms:
        v.append(m.v)
        f += [tuple(i + off for i in ff) for ff in m.f]
        if has_uv:
            uvs += m.uv
        off += len(m.v)
    return M(np.concatenate(v), f, uvs if has_uv else None)


def rotx(a):
    c, s = math.cos(a), math.sin(a); return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def roty(a):
    c, s = math.cos(a), math.sin(a); return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rotz(a):
    c, s = math.cos(a), math.sin(a); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def box(sx, sy, sz, c=(0, 0, 0)):
    x, y, z = sx / 2, sy / 2, sz / 2
    v = [(-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z), (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    uv = [[(0, 0), (1, 0), (1, 1), (0, 1)]] * 6
    return M(np.array(v) + c, f, [list(u) for u in uv])


def plane(sx, sz, c=(0, 0, 0), nx=1, nz=1):
    """Vertical plane in XZ facing -Y, with UVs (u along +X, v along +Z)."""
    v, f, uv = [], [], []
    for j in range(nz + 1):
        for i in range(nx + 1):
            v.append((-sx / 2 + sx * i / nx, 0, -sz / 2 + sz * j / nz))
    for j in range(nz):
        for i in range(nx):
            a = j * (nx + 1) + i
            f.append((a, a + 1, a + nx + 2, a + nx + 1))
            uv.append([(i / nx, j / nz), ((i + 1) / nx, j / nz), ((i + 1) / nx, (j + 1) / nz), (i / nx, (j + 1) / nz)])
    return M(np.array(v, float) + c, f, uv)


def loft(rings, cap0=True, cap1=True):
    """rings: list of (n,3) arrays with the same n, bottom to top; quads between, fan caps."""
    n = len(rings[0]); v = np.concatenate(rings); f = []
    for r in range(len(rings) - 1):
        for i in range(n):
            a, b = r * n + i, r * n + (i + 1) % n
            f.append((a, b, b + n, a + n))
    if cap0:
        c = len(v); v = np.vstack([v, rings[0].mean(0)])
        f += [(c, (i + 1) % n, i) for i in range(n)]
    if cap1:
        c = len(v); v = np.vstack([v, rings[-1].mean(0)]); base = (len(rings) - 1) * n
        f += [(c, base + i, base + (i + 1) % n) for i in range(n)]
    return M(v, f)


def ring(n, rx, ry, z=0.0, p=2.0, yo=0.0, phase=0.0):
    t = np.linspace(0, 2 * math.pi, n, endpoint=False) + phase
    c, s = np.cos(t), np.sin(t)
    x = rx * np.sign(c) * np.abs(c) ** (2 / p)
    y = ry * np.sign(s) * np.abs(s) ** (2 / p) + yo
    return np.stack([x, y, np.full(n, z)], 1)


def cyl(r0, r1, h, n=8, z0=0.0, caps=True):
    return loft([ring(n, r0, r0, z0), ring(n, r1, r1, z0 + h)], caps, caps)


def uvsphere(nu, nv, r=1.0):
    v = [(0, 0, -r)]
    for j in range(1, nv):
        th = math.pi * j / nv - math.pi / 2
        for i in range(nu):
            ph = 2 * math.pi * i / nu
            v.append((r * math.cos(th) * math.cos(ph), r * math.cos(th) * math.sin(ph), r * math.sin(th)))
    v.append((0, 0, r)); top = len(v) - 1; f = []
    for i in range(nu):
        f.append((0, 1 + (i + 1) % nu, 1 + i))
    for j in range(nv - 2):
        for i in range(nu):
            a = 1 + j * nu + i; b = 1 + j * nu + (i + 1) % nu
            f.append((a, b, b + nu, a + nu))
    base = 1 + (nv - 2) * nu
    for i in range(nu):
        f.append((top, base + i, base + (i + 1) % nu))
    return M(np.array(v, float), f)


def tube(path, radius, sides=6, caps=True):
    path = np.asarray(path, float); rings = []
    rad = np.broadcast_to(np.asarray(radius, float), (len(path),))
    for k in range(len(path)):
        t = path[min(k + 1, len(path) - 1)] - path[max(k - 1, 0)]; t /= np.linalg.norm(t)
        a = np.array([0, 0, 1.0]) if abs(t[2]) < 0.9 else np.array([1.0, 0, 0])
        u = np.cross(t, a); u /= np.linalg.norm(u); w = np.cross(t, u)
        ang = np.linspace(0, 2 * math.pi, sides, endpoint=False)
        rings.append(path[k] + rad[k] * (np.outer(np.cos(ang), u) + np.outer(np.sin(ang), w)))
    return loft(rings, caps, caps)


def jitter(m, amt, seed=0):
    r = np.random.default_rng(seed); m = m.copy(); m.v += r.normal(0, amt, m.v.shape); return m


# ------------------------------------------------------------------ bpy bits (decimate, text)
def _bpy_obj(m, name):
    import bpy
    me = bpy.data.meshes.new(name)
    me.from_pydata(m.v.tolist(), [], [list(ff) for ff in m.f])
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def _from_bpy(ob):
    import bpy
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    v = np.zeros(len(me.vertices) * 3); me.vertices.foreach_get('co', v); v = v.reshape(-1, 3)
    mw = np.array(ob.matrix_world)
    v = v @ mw[:3, :3].T + mw[:3, 3]
    f = [tuple(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    return M(v, f)


def decimate(m, ratio, sym_x=True, name='dec'):
    import bpy
    ob = _bpy_obj(m, name)
    mod = ob.modifiers.new('d', 'DECIMATE'); mod.ratio = ratio
    if sym_x:
        mod.use_symmetry = True; mod.symmetry_axis = 'X'
    out = _from_bpy(ob)
    bpy.data.objects.remove(ob)
    return out


def text_mesh(s, font_path, size=1.0, extrude=0.05, bevel=0.004, align='CENTER', res=2):
    """3D text as a mesh, lying in the XZ plane facing -Y (readable from a camera at -Y)."""
    import bpy
    cu = bpy.data.curves.new('t', 'FONT'); cu.body = s
    cu.font = bpy.data.fonts.load(font_path, check_existing=True)
    cu.size = size; cu.extrude = extrude; cu.bevel_depth = bevel; cu.bevel_resolution = 0
    cu.resolution_u = res; cu.align_x = align; cu.align_y = 'CENTER'
    ob = bpy.data.objects.new('t', cu); bpy.context.scene.collection.objects.link(ob)
    ob.rotation_euler = (math.pi / 2, 0, 0)
    bpy.context.view_layer.update()
    out = _from_bpy(ob)
    bpy.data.objects.remove(ob)
    return out


# ------------------------------------------------------------------ export
def add(name, m, color, pivot=(0, 0, 0), flip=False):
    tri, tuv = m.tris()
    P = (m.v - np.asarray(pivot, float))[tri]
    if flip:
        P = P[:, ::-1]; tuv = None if tuv is None else tuv[:, ::-1]
    n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    ln = np.linalg.norm(n, axis=1, keepdims=True); keep = ln[:, 0] > 1e-12
    P, n = P[keep], n[keep] / ln[keep]
    if tuv is not None:
        tuv = tuv[keep]
    N = np.repeat(n[:, None, :], 3, 1)
    color = np.asarray(color, float)
    col = np.broadcast_to(color, (len(P), 3)) if color.ndim == 1 else color[keep]
    C = np.repeat(np.asarray(col)[:, None, :], 3, 1)
    UV = tuv if tuv is not None else np.zeros((len(P), 3, 2))
    if name in PARTS:
        o = PARTS[name]
        PARTS[name] = {k: np.concatenate([o[k], a.reshape(-1, a.shape[-1]).astype(np.float32)])
                       for k, a in (('pos', P), ('nrm', N), ('uv', UV), ('col', C))}
    else:
        PARTS[name] = dict(pos=P.reshape(-1, 3).astype(np.float32), nrm=N.reshape(-1, 3).astype(np.float32),
                           uv=UV.reshape(-1, 2).astype(np.float32), col=C.reshape(-1, 3).astype(np.float32))


def save(path):
    flat = {}
    for k, d in PARTS.items():
        for a, arr in d.items():
            flat[f'{k}|{a}'] = arr
    np.savez_compressed(path, **flat)
    return {k: len(d['pos']) // 3 for k, d in PARTS.items()}


def load(path):
    z = np.load(path); out = {}
    for key in z.files:
        k, a = key.split('|'); out.setdefault(k, {})[a] = z[key]
    return out
