import os, bpy, sys, math, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bl
from bl import N
from sdf import tube, bezier
import cdragon as C
import wd_build as WB
from mathutils import Vector, Matrix


def strands():
    """hair-like parts: mane, beard, whiskers, fins, tufts. returns dict of lists"""
    hair = dict(V=[], F=[], TP=[], FLEX=[])
    fins = dict(V=[], F=[], TP=[])
    horn = dict(V=[], F=[], TP=[], PT=[])
    rng = np.random.default_rng(7)

    def add(dst, pts, radii, ring=6, squash=None, flex=False, part=0):
        tv, tf, tp = tube(pts, radii, ring=ring)
        if squash is not None:
            c = np.repeat(np.array(pts), ring, axis=0); c = np.vstack([c, [pts[-1], pts[0]]])
            tv = c + (tv - c) * np.array(squash)
        base = len(dst["V"])
        dst["V"].extend(list(tv)); dst["F"].extend([tuple(base + x for x in f) for f in tf]); dst["TP"].extend(list(tp))
        if "FLEX" in dst:
            dst["FLEX"].extend(list(tp if flex else np.zeros(len(tp))))
        if "PT" in dst:
            dst["PT"].extend([part] * len(tp))

    # mane
    for k in range(130):
        ang = rng.uniform(-1.4, 1.4)
        x0 = rng.uniform(15.95, 16.45)
        r0 = C.rad(x0) * 0.95 + 0.06
        p0 = np.array([x0, r0 * math.sin(ang), r0 * math.cos(ang) * 0.95])
        ln = rng.uniform(0.7, 1.9)
        outward = np.array([0, math.sin(ang), math.cos(ang)])
        p3 = p0 + np.array([-ln, 0, 0]) + outward * rng.uniform(0.15, 0.45)
        p1 = p0 + outward * 0.2 + np.array([-0.2, 0, 0])
        p2 = p3 + np.array([0.35, 0, 0]) + outward * rng.uniform(-0.15, 0.15) + np.array([0, 0, rng.uniform(-0.1, 0.15)])
        add(hair, bezier(p0, p1, p2, p3, 12), np.linspace(0.017, 0.002, 12), flex=True)
    # beard
    for k in range(18):
        x0 = rng.uniform(16.55, 17.15); y0 = rng.uniform(-0.12, 0.12)
        p0 = np.array([x0, y0, -0.27])
        ln = rng.uniform(0.35, 0.7)
        p3 = p0 + np.array([-ln * 0.8, y0 * 1.5, -ln * 0.6])
        add(hair, bezier(p0, p0 + np.array([-0.05, 0, -0.15]), p3 + np.array([0.15, 0, 0.1]), p3, 10), np.linspace(0.02, 0.003, 10), flex=True)
    # elbow tufts
    for x0, sc in ((14.0, 1.0), (8.2, 1.05)):
        for s in (1, -1):
            kn = np.array([x0 - 0.3, 0.46 * s, -0.42])
            for k in range(6):
                p0 = kn + np.array([0.0, 0.03 * s, rng.uniform(-0.06, 0.06)])
                ln = rng.uniform(0.35, 0.6)
                p3 = p0 + np.array([-ln, 0.12 * s, rng.uniform(-0.15, 0.1)])
                add(hair, bezier(p0, p0 + np.array([-0.1, 0.05 * s, 0.05]), p3 + np.array([0.15, 0, 0.08]), p3, 8), np.linspace(0.022, 0.003, 8), flex=True)
    # tail tuft
    for k in range(16):
        ang = rng.uniform(-1.6, 1.6)
        p0 = np.array([rng.uniform(0.15, 0.7), 0, 0])
        ln = rng.uniform(0.6, 1.1)
        d = np.array([-math.cos(ang * 0.5) * 0.8, math.sin(ang) * 0.35, math.cos(ang) * 0.6 * np.sign(rng.uniform(-1, 1))])
        p3 = p0 + d * ln
        add(hair, bezier(p0, p0 + d * 0.2 + np.array([0, 0, 0.05]), p3 - d * 0.25, p3, 10), np.linspace(0.03, 0.003, 10), flex=True)
    # whiskers
    for s in (1, -1):
        add(hair, bezier((17.45, 0.2 * s, -0.03), (17.95, 0.55 * s, 0.08), (17.15, 1.0 * s, -0.65), (15.9, 1.1 * s, -0.95), 40), np.linspace(0.022, 0.003, 40), ring=6, flex=True)
        add(hair, bezier((17.56, 0.08 * s, 0.14), (17.35, 0.28 * s, 0.5), (16.95, 0.42 * s, 0.66), (16.45, 0.52 * s, 0.58), 24), np.linspace(0.013, 0.002, 24), ring=5, flex=True)
    # dorsal fins
    for x in np.arange(0.9, 15.7, 0.27):
        r = C.rad(x)
        base = np.array([x, 0, r * 0.88])
        hgt = 0.1 + 0.42 * r
        tip = base + np.array([-hgt * 0.75, 0, hgt])
        ctrl = base + np.array([0.05, 0, hgt * 0.6])
        add(fins, bezier(base - np.array([0, 0, 0.05]), base + (ctrl - base) * 0.5, ctrl, tip, 7), np.linspace(0.09 * (0.6 + r), 0.004, 7), ring=8, squash=(1, 0.28, 1))
    # antlers
    for s in (1, -1):
        m = lambda p: np.array([p[0], p[1] * s, p[2]])
        beam = bezier(m((16.18, 0.12, 0.3)), m((16.0, 0.22, 0.62)), m((15.75, 0.34, 0.9)), m((15.48, 0.42, 1.08)), 20)
        add(horn, beam, np.linspace(0.058, 0.012, 20), ring=10, part=0)
        for u, dl in ((0.3, 0.32), (0.55, 0.28), (0.8, 0.22)):
            k = int(u * 19); b = beam[k]
            tdir = np.array([0.45, 0.12 * s, 0.88]); tdir /= np.linalg.norm(tdir)
            add(horn, bezier(b, b + tdir * dl * 0.4, b + tdir * dl * 0.8 + np.array([0.04, 0, 0]), b + tdir * dl + np.array([0.06, 0, 0]), 8),
                np.linspace(0.032, 0.006, 8), ring=8, part=0)
        # fangs
        for x, ln in ((17.33, 0.1), (17.18, 0.06), (17.05, 0.05), (16.92, 0.045)):
            p0 = np.array([x, 0.13 * s if x > 17.2 else 0.17 * s, -0.11]); p1 = p0 + np.array([-0.01, 0, -ln])
            add(horn, np.linspace(p0, p1, 4), np.linspace(0.02, 0.003, 4), ring=6, part=1)
    # claws
    for x0, sc in ((14.0, 1.0), (8.2, 1.05)):
        for s in (1, -1):
            an = np.array([x0 - 0.05, 0.52 * s, -0.72])
            for dy in (-0.09, -0.03, 0.03, 0.09):
                b0 = an + np.array([0.12, dy * s * sc, -0.03]); b1 = b0 + np.array([0.16, dy * s * 0.9, -0.05])
                tip0 = b1
                add(horn, bezier(tip0, tip0 + np.array([0.05, 0, 0]), tip0 + np.array([0.09, 0, -0.03]), tip0 + np.array([0.1, 0, -0.08]), 6),
                    np.linspace(0.028, 0.004, 6), ring=6, part=3)
    return hair, fins, horn


def hair_material(name, col=(0.86, 0.88, 0.9), tipcol=(0.55, 0.72, 0.85)):
    m, n, l, out = bl.new_mat(name)
    tp = N(n, "ShaderNodeAttribute", _attribute_name="tp")
    c = N(n, "ShaderNodeMix", _data_type='RGBA', A=(*col, 1), B=(*tipcol, 1))
    l.new(tp.outputs["Fac"], c.inputs["Factor"])
    bsdf = N(n, "ShaderNodeBsdfPrincipled", Roughness=0.45, **{"Sheen Weight": 0.6, "Sheen Roughness": 0.4})
    l.new(c.outputs["Result"], bsdf.inputs["Base Color"])
    tr = N(n, "ShaderNodeBsdfTranslucent")
    l.new(c.outputs["Result"], tr.inputs["Color"])
    mix = N(n, "ShaderNodeMixShader", Fac=0.3)
    l.new(bsdf.outputs[0], mix.inputs[1]); l.new(tr.outputs[0], mix.inputs[2])
    l.new(mix.outputs[0], out.inputs[0])
    return m


def eye_mat_attr(name, iris=(1.0, 0.75, 0.15)):
    m = WB.eye_material(name, iris=iris, glow=1.2)
    nt = m.node_tree
    tc = [x for x in nt.nodes if x.bl_idname == "ShaderNodeTexCoord"][0]
    at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "eyeloc"
    for lk in list(nt.links):
        if lk.from_node == tc:
            nt.links.new(at.outputs["Vector"], lk.to_socket)
    return m


def eye_mesh(center, side, r=0.085):
    """sphere with attribute eyeloc (local coords, z outward, y up)"""
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=96, v_segments=48, radius=1.0)
    V = np.array([v.co[:] for v in bm.verts]); F = [tuple(v.index for v in f.verts) for f in bm.faces]
    bm.free()
    loc = V.copy()
    if side > 0:
        Rm = np.array([[-1, 0, 0], [0, 0, 1], [0, 1, 0]], float)
    else:
        Rm = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float)
    W_ = (V @ Rm.T) * r + np.array(center)
    return W_, F, loc


def build(prefix="C", palette=None):
    pal = palette or dict(back=(0.006, 0.05, 0.045, 1), flank=(0.02, 0.16, 0.13, 1), belly=(0.62, 0.46, 0.17, 1))
    C.ensure_cache()
    d = np.load(C.CACHE)
    root = bpy.data.objects.new(prefix + "_root", None); bl.link(root)
    vb = d["vb"]
    body = bl.mesh_obj(prefix + "_body", vb, d["fb"])
    me = body.data
    nrm = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("normal", nrm); nrm = nrm.reshape(-1, 3)
    x, y, z = vb[:, 0], vb[:, 1], vb[:, 2]
    legmask = (z < -0.3) | (np.abs(y) > 0.42)
    belly = np.clip((-nrm[:, 2] - 0.25) / 0.45, 0, 1) * (~legmask) * (x < 16.2)
    dorsal = np.clip((nrm[:, 2] - 0.15) / 0.6, 0, 1)
    mouth = ((x > 16.65) & (x < 17.5) & (nrm[:, 2] < -0.55) & (np.abs(y) < 0.2) & (z > -0.2)).astype(float)
    bl.store_rest(body)
    bl.add_attr(body, "belly", belly); bl.add_attr(body, "dorsal", dorsal); bl.add_attr(body, "mouth", mouth); bl.add_attr(body, "gland", np.zeros(len(vb)))
    jaw = bl.mesh_obj(prefix + "_jaw", d["vj"], d["fj"])
    vj = d["vj"]
    jn = np.zeros(len(vj) * 3, np.float32); jaw.data.vertices.foreach_get("normal", jn); jn = jn.reshape(-1, 3)
    bl.store_rest(jaw)
    bl.add_attr(jaw, "belly", np.clip((-jn[:, 2] - 0.2) / 0.5, 0, 1)); bl.add_attr(jaw, "dorsal", np.zeros(len(vj)))
    bl.add_attr(jaw, "mouth", ((jn[:, 2] > 0.5) & (np.abs(vj[:, 1]) < 0.17)).astype(float)); bl.add_attr(jaw, "gland", np.zeros(len(vj)))
    skin = WB.scale_material(prefix + "_skin", pal["back"], pal["flank"], pal["belly"], scale_size=22.0)
    bs = [nd for nd in skin.node_tree.nodes if nd.bl_idname == "ShaderNodeBsdfPrincipled"][0]
    bs.inputs["Thin Film Thickness"].default_value = 320.0
    bs.inputs["Thin Film IOR"].default_value = 1.45
    body.data.materials.append(skin); jaw.data.materials.append(skin)
    body["glow"] = 0.0; jaw["glow"] = 0.0
    hair, fins, horn = strands()
    ho = bl.mesh_obj(prefix + "_hair", hair["V"], hair["F"]); bl.store_rest(ho); bl.add_attr(ho, "tp", hair["TP"])
    vg = ho.vertex_groups.new(name="flex")
    flex = np.array(hair["FLEX"])
    for val in np.unique(np.round(flex * 20) / 20):
        idx = np.nonzero(np.abs(np.round(flex * 20) / 20 - val) < 1e-6)[0]
        if val > 0:
            vg.add(idx.tolist(), float(val) ** 1.5, 'REPLACE')
    fo = bl.mesh_obj(prefix + "_fins", fins["V"], fins["F"]); bl.store_rest(fo); bl.add_attr(fo, "tp", fins["TP"])
    hm = hair_material(prefix + "_hairmat")
    ho.data.materials.append(hm); fo.data.materials.append(hm)
    hno = bl.mesh_obj(prefix + "_horns", horn["V"], horn["F"]); bl.store_rest(hno)
    bl.add_attr(hno, "tp", horn["TP"]); bl.add_attr(hno, "part", horn["PT"])
    hno.data.materials.append(WB.horn_material(prefix + "_hornmat", base=(0.35, 0.28, 0.18), tip=(0.85, 0.8, 0.68)))
    em = eye_mat_attr(prefix + "_eye")
    eyes = []
    for s in (1, -1):
        V, F, loc = eye_mesh((16.75, 0.262 * s, 0.17), s, 0.08)
        eo = bl.mesh_obj(prefix + "_eye" + ("L" if s > 0 else "R"), V, F)
        bl.add_attr(eo, "eyeloc", loc, 'VEC')
        eo.data.materials.append(em)
        eyes.append(eo)
    parts = [body, jaw, ho, fo, hno] + eyes
    for p in parts:
        p.parent = root
    # jaw pivot: set origin at hinge by offsetting mesh
    hinge = Vector((16.35, 0, -0.08))
    jaw.data.transform(Matrix.Translation(-hinge)); jaw.location = hinge
    # whisker/hair flutter
    wv = ho.modifiers.new("wave", 'WAVE')
    wv.use_x = True; wv.use_y = False; wv.use_normal = False
    wv.height = 0.07; wv.width = 0.9; wv.narrowness = 1.2; wv.speed = -0.05
    wv.vertex_group = "flex"; wv.start_position_x = 17.5
    return dict(root=root, body=body, jaw=jaw, hair=ho, fins=fo, horns=hno, eyes=eyes, parts=parts)


def attach_path(D, curve_ob):
    for p in D["parts"]:
        m = p.modifiers.new("path", 'CURVE')
        m.object = curve_ob
        m.deform_axis = 'POS_X'


def make_path(name, pts, res=64):
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.resolution_u = res
    cu.twist_mode = 'Z_UP'
    cu.use_stretch = False
    cu.use_deform_bounds = False
    sp = cu.splines.new('BEZIER')
    sp.bezier_points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        bp = sp.bezier_points[i]
        bp.co = Vector(p)
        bp.handle_left_type = 'AUTO'; bp.handle_right_type = 'AUTO'
    ob = bpy.data.objects.new(name, cu)
    bl.link(ob)
    return ob


def path_length(curve_ob):
    import bmesh
    dg = bpy.context.evaluated_depsgraph_get()
    ev = curve_ob.evaluated_get(dg)
    me = ev.to_mesh()
    co = np.array([v.co[:] for v in me.vertices])
    ev.to_mesh_clear()
    return float(np.linalg.norm(np.diff(co, axis=0), axis=1).sum())


def head_frame(D):
    """world-space head center and forward direction after deformation."""
    dg = bpy.context.evaluated_depsgraph_get()
    ob = D["body"].evaluated_get(dg)
    me = ob.to_mesh()
    co = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    rest = np.zeros(len(me.vertices) * 3, np.float32)
    me.attributes["rest"].data.foreach_get("vector", rest); rest = rest.reshape(-1, 3)
    ob.to_mesh_clear()
    mw = np.array(D["body"].matrix_world)
    co = co @ mw[:3, :3].T + mw[:3, 3]
    def at(x0, x1):
        sel = (rest[:, 0] > x0) & (rest[:, 0] < x1)
        return co[sel].mean(0)
    h = at(16.5, 16.9); n = at(17.3, 17.6); k = at(15.0, 15.4)
    f = n - k; f /= np.linalg.norm(f)
    return h, f


def body_point(D, x0, x1):
    dg = bpy.context.evaluated_depsgraph_get()
    ob = D["body"].evaluated_get(dg)
    me = ob.to_mesh()
    co = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    rest = np.zeros(len(me.vertices) * 3, np.float32)
    me.attributes["rest"].data.foreach_get("vector", rest); rest = rest.reshape(-1, 3)
    ob.to_mesh_clear()
    mw = np.array(D["body"].matrix_world)
    co = co @ mw[:3, :3].T + mw[:3, 3]
    sel = (rest[:, 0] > x0) & (rest[:, 0] < x1)
    return co[sel].mean(0)
