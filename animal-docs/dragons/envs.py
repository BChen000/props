import os, bpy, sys, math, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bl
from bl import N
from scipy.ndimage import gaussian_filter, zoom
from mathutils import Vector


# ---------- noise helpers ----------
def fbm2(n, octaves, seed=0, base=4, persist=0.5):
    rng = np.random.default_rng(seed)
    out = np.zeros((n, n))
    amp = 1.0; tot = 0
    for o in range(octaves):
        g = base * 2 ** o
        r = rng.standard_normal((g + 3, g + 3))
        z = zoom(r, (n + 3 * n / g) / (g + 3), order=3)[:n, :n]
        out += amp * z; tot += amp; amp *= persist
    out /= tot
    return (out - out.mean()) / (out.std() + 1e-9)


def grid_mesh(name, hf, size_x, size_y, cx=0, cy=0, z0=0.0, coll=None):
    ny, nx = hf.shape
    xs = np.linspace(-size_x / 2, size_x / 2, nx) + cx
    ys = np.linspace(-size_y / 2, size_y / 2, ny) + cy
    X, Y = np.meshgrid(xs, ys)
    V = np.stack([X.ravel(), Y.ravel(), hf.ravel() + z0], 1)
    idx = np.arange(nx * ny).reshape(ny, nx)
    a = idx[:-1, :-1].ravel(); b = idx[:-1, 1:].ravel(); c = idx[1:, 1:].ravel(); d = idx[1:, :-1].ravel()
    F = np.stack([a, b, c, d], 1)
    return bl.mesh_obj(name, V, F, coll=coll)


# ---------- haze ----------
def add_haze(mat, color, dist, max_amt=1.0, height_falloff=None):
    """mix the material output toward an emissive haze color by camera distance."""
    nt = mat.node_tree; n = nt.nodes; l = nt.links
    out = [x for x in n if x.bl_idname == "ShaderNodeOutputMaterial"][0]
    src = out.inputs["Surface"].links[0].from_socket
    cam = n.new("ShaderNodeCameraData")
    d = n.new("ShaderNodeMath"); d.operation = 'DIVIDE'; d.inputs[1].default_value = -dist
    l.new(cam.outputs["View Distance"], d.inputs[0])
    e = n.new("ShaderNodeMath"); e.operation = 'EXPONENT'; l.new(d.outputs[0], e.inputs[0])
    inv = n.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    l.new(e.outputs[0], inv.inputs[1])
    mx = n.new("ShaderNodeMath"); mx.operation = 'MULTIPLY'; mx.inputs[1].default_value = max_amt
    l.new(inv.outputs[0], mx.inputs[0])
    em = n.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*color[:3], 1); em.inputs["Strength"].default_value = 1.0
    ms = n.new("ShaderNodeMixShader")
    l.new(mx.outputs[0], ms.inputs[0]); l.new(src, ms.inputs[1]); l.new(em.outputs[0], ms.inputs[2])
    l.new(ms.outputs[0], out.inputs["Surface"])
    return em


def world_sky(s, elev, azim, strength=1.0, turb_air=1.0, dust=1.0, sun_disc=True, sun_int=1.0, kind='MULTIPLE_SCATTERING',
              tint=None, horizon_haze=None):
    w = bpy.data.worlds.new("world"); s.world = w; w.use_nodes = True
    nt = w.node_tree; n = nt.nodes; l = nt.links
    bg = n["Background"]
    sky = n.new("ShaderNodeTexSky")
    try:
        sky.sky_type = kind
    except Exception:
        sky.sky_type = 'SINGLE_SCATTERING'
    sky.sun_elevation = math.radians(elev); sky.sun_rotation = math.radians(azim - 90)
    sky.sun_disc = sun_disc; sky.sun_intensity = sun_int
    sky.air_density = turb_air; sky.aerosol_density = dust
    src = sky.outputs[0]
    if tint is not None:
        mx = n.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'
        mx.inputs["Factor"].default_value = 1.0; mx.inputs["B"].default_value = (*tint, 1)
        l.new(src, mx.inputs["A"]); src = mx.outputs["Result"]
    l.new(src, bg.inputs[0]); bg.inputs[1].default_value = strength
    return w


def world_color(s, top, horizon, strength=1.0):
    w = bpy.data.worlds.new("world"); s.world = w; w.use_nodes = True
    nt = w.node_tree; n = nt.nodes; l = nt.links
    bg = n["Background"]
    tc = n.new("ShaderNodeTexCoord")
    sep = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Generated"], sep.inputs[0])
    mr = n.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 0.0; mr.inputs["From Max"].default_value = 0.6
    l.new(sep.outputs["Z"], mr.inputs["Value"])
    mx = n.new("ShaderNodeMix"); mx.data_type = 'RGBA'
    mx.inputs["A"].default_value = (*horizon, 1); mx.inputs["B"].default_value = (*top, 1)
    l.new(mr.outputs["Result"], mx.inputs["Factor"])
    l.new(mx.outputs["Result"], bg.inputs[0]); bg.inputs[1].default_value = strength
    return w


# ---------- materials ----------
def rock_mat(name, c1, c2, scale=0.3, rough=0.85, bump=0.6, lava=None, moss=None):
    m, n, l, out = bl.new_mat(name)
    tc = N(n, "ShaderNodeTexCoord")
    noise = N(n, "ShaderNodeTexNoise", Scale=scale, Detail=10.0, Roughness=0.62)
    l.new(tc.outputs["Object"], noise.inputs["Vector"])
    vor = N(n, "ShaderNodeTexVoronoi", Scale=scale * 6, Randomness=1.0); vor.feature = 'DISTANCE_TO_EDGE'
    l.new(tc.outputs["Object"], vor.inputs["Vector"])
    fine = N(n, "ShaderNodeTexNoise", Scale=scale * 40, Detail=4.0)
    l.new(tc.outputs["Object"], fine.inputs["Vector"])
    col = N(n, "ShaderNodeMix", _data_type='RGBA', A=(*c1, 1), B=(*c2, 1))
    l.new(noise.outputs["Fac"], col.inputs["Factor"])
    cr = N(n, "ShaderNodeMapRange", **{"From Min": 0.0, "From Max": 0.06, "To Min": 0.45, "To Max": 1.0})
    l.new(vor.outputs["Distance"], cr.inputs["Value"])
    dk = N(n, "ShaderNodeMix", _data_type='RGBA', _blend_type='MULTIPLY', Factor=1.0)
    l.new(col.outputs["Result"], dk.inputs["A"])
    cc = N(n, "ShaderNodeCombineColor")
    for ch in ("Red", "Green", "Blue"):
        l.new(cr.outputs["Result"], cc.inputs[ch])
    l.new(cc.outputs["Color"], dk.inputs["B"])
    base = dk.outputs["Result"]
    if moss is not None:
        geo = N(n, "ShaderNodeNewGeometry")
        sep = N(n, "ShaderNodeSeparateXYZ"); l.new(geo.outputs["Normal"], sep.inputs[0])
        mn = N(n, "ShaderNodeTexNoise", Scale=scale * 3, Detail=6.0); l.new(tc.outputs["Object"], mn.inputs["Vector"])
        ad = N(n, "ShaderNodeMath", _operation='MULTIPLY_ADD'); ad.inputs[1].default_value = 0.6
        l.new(mn.outputs["Fac"], ad.inputs[0]); l.new(sep.outputs["Z"], ad.inputs[2])
        mm = N(n, "ShaderNodeMapRange", **{"From Min": moss[1], "From Max": moss[1] + 0.25, "To Min": 0.0, "To Max": 1.0})
        l.new(ad.outputs[0], mm.inputs["Value"])
        mc = N(n, "ShaderNodeMix", _data_type='RGBA', B=(*moss[0], 1))
        l.new(base, mc.inputs["A"]); l.new(mm.outputs["Result"], mc.inputs["Factor"])
        base = mc.outputs["Result"]
    bsdf = N(n, "ShaderNodeBsdfPrincipled", Roughness=rough)
    l.new(base, bsdf.inputs["Base Color"])
    hb = N(n, "ShaderNodeMath", _operation='MULTIPLY_ADD'); hb.inputs[1].default_value = 0.3
    l.new(fine.outputs["Fac"], hb.inputs[0]); l.new(vor.outputs["Distance"], hb.inputs[2])
    bp = N(n, "ShaderNodeBump", Strength=bump, Distance=0.05)
    l.new(hb.outputs[0], bp.inputs["Height"]); l.new(bp.outputs["Normal"], bsdf.inputs["Normal"])
    if lava is not None:
        ln = N(n, "ShaderNodeTexNoise", Scale=scale * 2.0, Detail=8.0, Distortion=1.5)
        l.new(tc.outputs["Object"], ln.inputs["Vector"])
        lm = N(n, "ShaderNodeMapRange", **{"From Min": lava[1], "From Max": lava[1] + 0.06, "To Min": 0.0, "To Max": 1.0})
        l.new(ln.outputs["Fac"], lm.inputs["Value"])
        crk = N(n, "ShaderNodeMapRange", **{"From Min": 0.0, "From Max": 0.025, "To Min": 1.0, "To Max": 0.0})
        l.new(vor.outputs["Distance"], crk.inputs["Value"])
        mul = N(n, "ShaderNodeMath", _operation='MULTIPLY'); l.new(lm.outputs["Result"], mul.inputs[0]); l.new(crk.outputs["Result"], mul.inputs[1])
        st = N(n, "ShaderNodeMath", _operation='MULTIPLY'); st.inputs[1].default_value = lava[2]
        l.new(mul.outputs[0], st.inputs[0])
        bsdf.inputs["Emission Color"].default_value = (*lava[0], 1)
        l.new(st.outputs[0], bsdf.inputs["Emission Strength"])
    l.new(bsdf.outputs[0], out.inputs[0])
    return m


def cloud_mat(name, col=(1, 1, 1), shadow=(0.55, 0.6, 0.75), scale=0.004):
    m, n, l, out = bl.new_mat(name)
    tc = N(n, "ShaderNodeTexCoord")
    noise = N(n, "ShaderNodeTexNoise", Scale=scale * 60, Detail=8.0, Roughness=0.55)
    l.new(tc.outputs["Object"], noise.inputs["Vector"])
    bsdf = N(n, "ShaderNodeBsdfDiffuse", Color=(*col, 1), Roughness=1.0)
    tr = N(n, "ShaderNodeBsdfTranslucent", Color=(*col, 1))
    mix = N(n, "ShaderNodeMixShader", Fac=0.35)
    l.new(bsdf.outputs[0], mix.inputs[1]); l.new(tr.outputs[0], mix.inputs[2])
    bp = N(n, "ShaderNodeBump", Strength=0.35, Distance=1.0)
    l.new(noise.outputs["Fac"], bp.inputs["Height"]); l.new(bp.outputs["Normal"], bsdf.inputs["Normal"])
    l.new(mix.outputs[0], out.inputs[0])
    return m


def water_mat(name, deep=(0.02, 0.06, 0.06), rough=0.04, ripple_scale=2.0, ripple_str=0.15):
    m, n, l, out = bl.new_mat(name)
    tc = N(n, "ShaderNodeTexCoord")
    mp = N(n, "ShaderNodeMapping")
    l.new(tc.outputs["Object"], mp.inputs["Vector"])
    noise = N(n, "ShaderNodeTexNoise", Scale=ripple_scale, Detail=6.0, Roughness=0.6)
    noise.noise_dimensions = '4D'
    l.new(mp.outputs["Vector"], noise.inputs["Vector"])
    bp = N(n, "ShaderNodeBump", Strength=ripple_str, Distance=0.1)
    l.new(noise.outputs["Fac"], bp.inputs["Height"])
    bsdf = N(n, "ShaderNodeBsdfPrincipled", **{"Base Color": (*deep, 1), "Roughness": rough, "Specular IOR Level": 0.7})
    l.new(bp.outputs["Normal"], bsdf.inputs["Normal"])
    l.new(bsdf.outputs[0], out.inputs[0])
    return m, noise


def card_cloud_mat(name, col=(1, 1, 1), density=1.0, seed=0.0, emit=0.0):
    """soft cloud billboard: alpha from noise * radial falloff."""
    m, n, l, out = bl.new_mat(name)
    tc = N(n, "ShaderNodeTexCoord")
    sep = N(n, "ShaderNodeSeparateXYZ"); l.new(tc.outputs["Generated"], sep.inputs[0])
    cx = N(n, "ShaderNodeMath", _operation='SUBTRACT'); cx.inputs[1].default_value = 0.5; l.new(sep.outputs["X"], cx.inputs[0])
    cy = N(n, "ShaderNodeMath", _operation='SUBTRACT'); cy.inputs[1].default_value = 0.5; l.new(sep.outputs["Y"], cy.inputs[0])
    cv = N(n, "ShaderNodeCombineXYZ"); l.new(cx.outputs[0], cv.inputs["X"]); l.new(cy.outputs[0], cv.inputs["Y"])
    ln = N(n, "ShaderNodeVectorMath", _operation='LENGTH'); l.new(cv.outputs[0], ln.inputs[0])
    fall = N(n, "ShaderNodeMapRange", **{"From Min": 0.12, "From Max": 0.5, "To Min": 1.0, "To Max": 0.0})
    fall.interpolation_type = 'SMOOTHSTEP'
    l.new(ln.outputs["Value"], fall.inputs["Value"])
    noise = N(n, "ShaderNodeTexNoise", Scale=3.0, Detail=10.0, Roughness=0.62, W=seed)
    noise.noise_dimensions = '4D'
    l.new(tc.outputs["Generated"], noise.inputs["Vector"])
    nm = N(n, "ShaderNodeMapRange", **{"From Min": 0.42, "From Max": 0.72, "To Min": 0.0, "To Max": 1.0})
    l.new(noise.outputs["Fac"], nm.inputs["Value"])
    a = N(n, "ShaderNodeMath", _operation='MULTIPLY'); l.new(nm.outputs["Result"], a.inputs[0]); l.new(fall.outputs["Result"], a.inputs[1])
    a2 = N(n, "ShaderNodeMath", _operation='MULTIPLY'); a2.inputs[1].default_value = density; l.new(a.outputs[0], a2.inputs[0])
    a3 = N(n, "ShaderNodeMath", _operation='MINIMUM'); a3.inputs[1].default_value = 1.0; l.new(a2.outputs[0], a3.inputs[0])
    tr = N(n, "ShaderNodeBsdfTransparent")
    dif = N(n, "ShaderNodeBsdfDiffuse", Color=(*col, 1))
    tl = N(n, "ShaderNodeBsdfTranslucent", Color=(*col, 1))
    m1 = N(n, "ShaderNodeMixShader", Fac=0.5); l.new(dif.outputs[0], m1.inputs[1]); l.new(tl.outputs[0], m1.inputs[2])
    if emit > 0:
        em = N(n, "ShaderNodeEmission", Color=(*col, 1), Strength=emit)
        m2 = N(n, "ShaderNodeAddShader"); l.new(m1.outputs[0], m2.inputs[0]); l.new(em.outputs[0], m2.inputs[1]); src = m2.outputs[0]
    else:
        src = m1.outputs[0]
    mx = N(n, "ShaderNodeMixShader"); l.new(a3.outputs[0], mx.inputs[0]); l.new(tr.outputs[0], mx.inputs[1]); l.new(src, mx.inputs[2])
    l.new(mx.outputs[0], out.inputs[0])
    try:
        m.surface_render_method = 'BLENDED'
    except Exception:
        pass
    return m


def cloud_card(name, loc, size, mat, rot=(math.radians(90), 0, 0), track=None):
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=loc)
    ob = bpy.context.active_object; ob.name = name
    ob.scale = (size[0], size[1], 1)
    ob.rotation_euler = rot
    ob.data.materials.append(mat)
    ob.visible_shadow = False
    if track is not None:
        c = ob.constraints.new('TRACK_TO'); c.target = track; c.track_axis = 'TRACK_Z'; c.up_axis = 'UP_Y'
    return ob


# ---------- environments ----------
def cloud_sea(z=-40.0, size=6000.0, n=420, amp=14.0, seed=1, col=(1, 1, 1), haze=None):
    hf = fbm2(n, 6, seed, base=6, persist=0.55)
    puff = np.clip(fbm2(n, 4, seed + 9, base=24, persist=0.5), -1, 3)
    h = amp * (0.6 * hf + 0.55 * np.maximum(puff, 0) ** 1.2)
    ob = grid_mesh("cloudsea", h, size, size, z0=z)
    m = cloud_mat("cloudmat", col)
    if haze is not None:
        add_haze(m, haze[0], haze[1], haze[2] if len(haze) > 2 else 1.0)
    ob.data.materials.append(m)
    return ob


def peaks(specs, mat, seed=3):
    """specs: list of (x, y, base_radius, height). jagged mountain cones."""
    obs = []
    for i, (x, y, r, hgt) in enumerate(specs):
        n = 140
        hf = fbm2(n, 6, seed + i, base=3, persist=0.55)
        xs = np.linspace(-1, 1, n); X, Y = np.meshgrid(xs, xs)
        R = np.sqrt(X ** 2 + Y ** 2)
        ridge = 1 - np.abs(fbm2(n, 5, seed + 50 + i, base=4, persist=0.5)) * 0.5
        prof = np.clip(1 - R, 0, 1) ** 1.6
        h = hgt * prof * (0.75 + 0.25 * ridge) + hgt * 0.06 * hf * prof
        ob = grid_mesh("peak%d" % i, h, 2 * r, 2 * r, cx=x, cy=y, z0=-hgt * 0.05)
        ob.data.materials.append(mat)
        obs.append(ob)
    return obs
