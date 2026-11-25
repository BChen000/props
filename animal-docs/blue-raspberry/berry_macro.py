"""blue-raspberry / berry_macro: the single-berry macro still used for the Wildlore "Blue Raspberry" thumbnail.

A hero blue raspberry (Rubus cyanocarpus) hangs from a curved stalk with its five green sepals, side-lit from
the upper left with a warm rim from behind-right, against dark, sun-flecked forest bokeh. The frame is
1080x1920 and leaves the top ~30 % dark for a title (see ../wildlore-title).

  xvfb-run -a blender -b -noaudio --python berry_macro.py              -> out/berry_macro.png (~3 min, 64 samples, 2 cores)
  RES=540x960 TM_SAMP=8 xvfb-run -a blender -b -noaudio --python berry_macro.py   -> quick look (~15 s)
  MODE=dry ...                                                          -> prints where the berry lands in pixels, no render

Every knob below can be overridden from the environment as TM_<KEY> (e.g. TM_FSTOP=4).
Blender 4.0.2, EEVEE (Legacy). Needs ../wildlore-blender-kit and the forest HDRI it names (see that README).
"""
import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "wildlore-blender-kit"))
import bblib as B
import bpy, math, numpy as np
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view

# --------------------------------------------------------------------------- settings
SETTINGS = dict(
    # render
    SAMP=64, EXPO=0.0, BLOOMI=0.03, BOKMAX=220, BOKTH=1.0,
    # backdrop: the camera sees its own patch of babylon_forest.hdr (u = longitude 0..1, a = tilt up in degrees),
    # warmed by (BGR, BGG, BGB), mid-tones crushed by gamma BGGAM so only sun flecks survive as bokeh
    BGU=0.42, BGA=8, BGR=1.0, BGG=0.86, BGB=0.55, BGSAT=1.2, WCAM=0.5, BGGAM=1.55,
    WSTR=0.25,                      # forest light on the subject (the HDRI as seen by shading, rotated 3.4 rad)
    # stalk (Catmull-Rom from the upper right into the calyx) and its look
    SX0=0.060, SZ0=0.070, SX1=0.030, SZ1=0.040, SR0=0.0010, SR1=0.0011, PSHEEN=0.25,
    # the berry: seed, drupelet count, tilt/spin in degrees, drupelet coat, core glow, hairs
    SEED=3, NDRUP=110, TILTX=6, TILTY=-8, SPIN=0, COATR=0.24, COATW=0.3, COREEM=0.25,
    HAIRR=0.12, HAIRG=0.15, HAIRB=0.30, NOHAIR=1,  # at this magnification the fine hairs read as scratches, so they're hidden
    # leaves behind the berry (scale 0 = off) and a second, out-of-focus berry further back
    L0X=-0.05, L0Y=0.09, L0Z=0.512, L0S=0.85, L1S=0,
    BG_BERRY=1, B2X=-0.045, B2Y=0.11, B2Z=0.522,
    # optional extras, off in the shipped still: emissive bokeh orbs behind the berry, dew drops on the drupelets
    ORBS=0, OSEED=21, OZLO=-0.55, OZHI=0.12, OEM=3.0,
    DROPS=0, CX=-0.02, CY=-0.12, CZ=0.0, DSEED=4, DSCALE=1.0,
    # lights (offsets from the berry centre, metres): soft key upper left, small warm rim behind right, faint cool fill
    KX=-0.10, KY=-0.01, KZ=0.10, KSIZE=0.22, KEY=0.55,
    RX=0.07, RY=0.10, RZ=0.06, RSIZE=0.05, RIM=2.0,
    FILL=0.03,
    # camera: yaw/pitch in degrees, distance in metres, 100 mm-equivalent framing on an 8 mm lens with a scaled sensor,
    # target offset (TX, TZ) from the berry centre, focus FOFF metres in front of the centre
    CYAW=-12, CPIT=6, DIST=0.147, TX=0.0, TZ=0.0052, LENS=100, FSTOP=2.2, FOFF=0.0075,
)


def E(k):
    """a setting from SETTINGS, overridable with the environment variable TM_<KEY>"""
    return float(os.environ.get("TM_" + k, SETTINGS[k]))


OUT = os.environ.get("OUT", os.path.join(HERE, "out", "berry_macro.png"))
MODE = os.environ.get("MODE", "render")
sc = B.reset()
B.setup_render(sc, 1, "", samples=int(E("SAMP")), gtao_dist=0.004, exposure=E("EXPO"), bloom=True, still=True,
               shadow_cube='1024', cascade='2048', sss_samples=9)
sc.eevee.bloom_threshold = 1.2; sc.eevee.bloom_intensity = E("BLOOMI"); sc.eevee.bloom_radius = 6.0
sc.eevee.bokeh_max_size = E("BOKMAX") * B.RES[0] / 1080
sc.eevee.bokeh_threshold = E("BOKTH")
sc.eevee.use_ssr = True; sc.eevee.use_ssr_refraction = True; sc.eevee.ssr_quality = 0.5


def world_split():
    """dim forest light on the subject; the camera sees a darker, sun-flecked part of the canopy, which the lens blurs to bokeh"""
    w = bpy.data.worlds.new("World"); sc.world = w; w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    img = bpy.data.images.load(os.path.join(B.ASSETS, "hdri", "babylon_forest.hdr"), check_existing=True)
    tc = nt.nodes.new("ShaderNodeTexCoord")

    def branch(rot, tint, sat):
        mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Rotation"].default_value = rot
        env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = img
        hs = nt.nodes.new("ShaderNodeHueSaturation"); hs.inputs["Saturation"].default_value = sat
        mul = nt.nodes.new("ShaderNodeMixRGB"); mul.blend_type = 'MULTIPLY'; mul.inputs["Fac"].default_value = 1.0
        mul.inputs["Color2"].default_value = (*tint, 1)
        nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
        nt.links.new(mp.outputs["Vector"], env.inputs["Vector"])
        nt.links.new(env.outputs["Color"], hs.inputs["Color"])
        nt.links.new(hs.outputs["Color"], mul.inputs["Color1"])
        return mul.outputs["Color"]
    cl = branch((0, 0, 3.4), (1.0, 0.92, 0.8), 1.0)
    u = E("BGU"); a = math.radians(E("BGA"))
    g = (0.5 - u) * 2 * math.pi - math.pi / 2
    cc = branch((a, 0, g), (E("BGR"), E("BGG"), E("BGB")), E("BGSAT"))
    bg = nt.nodes.new("ShaderNodeBackground"); bg.inputs["Strength"].default_value = E("WSTR")
    nt.links.new(cl, bg.inputs["Color"])
    # crush the backdrop's mid-tones so only the sun flecks survive as bokeh
    pw = nt.nodes.new("ShaderNodeGamma"); pw.inputs["Gamma"].default_value = E("BGGAM")
    nt.links.new(cc, pw.inputs["Color"])
    bg2 = nt.nodes.new("ShaderNodeBackground"); bg2.inputs["Strength"].default_value = E("WCAM")
    nt.links.new(pw.outputs[0], bg2.inputs["Color"])
    lp = nt.nodes.new("ShaderNodeLightPath"); mix = nt.nodes.new("ShaderNodeMixShader")
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(bg.outputs[0], mix.inputs[1]); nt.links.new(bg2.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])


world_split()
root = B.empty("root", (0, 0, 0.5))
# stalk arching in from above
sp = np.array([[E("SX0"), 0.020, E("SZ0")], [E("SX1"), 0.010, E("SZ1")], [0.008, 0.002, 0.016], [0.0, 0.0, 0.0]])
P = B.catmull(sp, 10)
V, F, UV = B.tube_mesh(P, np.linspace(E("SR0"), E("SR1"), len(P)), sides=12)
me = B.make_mesh("stalk", V, F, uv=UV); me.materials.append(B.mat_pedicel())
B.obj_from_mesh("stalk", me, parent=root)
B.CORE_FACTOR = 0.93
bo, fr = B.make_berry("hero", ripeness=1.0, scale=1.0, hero=True, seed=int(E("SEED")), parent=root, stem_len=0.0015,
                      N=int(E("NDRUP")), seg=30, rings=20)
bo.rotation_euler = (math.pi + math.radians(E("TILTX")), math.radians(E("TILTY")), math.radians(E("SPIN")))
_pm = bpy.data.materials.get("Pedicel")
if _pm:
    _pp = _pm.node_tree.nodes["Principled BSDF"]
    _pp.inputs["Sheen Weight"].default_value = E("PSHEEN"); _pp.inputs["Roughness"].default_value = 0.7
    _pp.inputs["Specular IOR Level"].default_value = 0.2
_dm = bpy.data.materials.get("Drupelet")
if _dm:
    _pd = _dm.node_tree.nodes["Principled BSDF"]
    _pd.inputs["Coat Roughness"].default_value = E("COATR")
    _pd.inputs["Coat Weight"].default_value = E("COATW")
_core = bpy.data.materials.get("BerryCore")
if _core:
    for _n in _core.node_tree.nodes:
        if _n.type == 'MIX_RGB':
            _n.inputs["Color1"].default_value = (0.020, 0.070, 0.42, 1)
            _n.inputs["Color2"].default_value = (0.030, 0.090, 0.50, 1)
    _pc = _core.node_tree.nodes["Principled BSDF"]
    _pc.inputs["Emission Color"].default_value = (0.02, 0.08, 0.55, 1); _pc.inputs["Emission Strength"].default_value = E("COREEM")
hm = bpy.data.materials.get("BerryHair")
if hm:
    hm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (E("HAIRR"), E("HAIRG"), E("HAIRB"), 1)
    if int(E("NOHAIR")):  # at this magnification the fine hairs read as scratches
        hm.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.0
        hm.blend_method = 'CLIP'
        hm.shadow_method = 'NONE'
bpy.context.view_layer.update()
cen = fr.matrix_world @ Vector((0, 0, 0.0095))
# ---- leaves: one behind-left catching the rim light, one behind-right
lr = np.random.default_rng(9)
for k, (pos, rot, s_) in enumerate([((E("L0X"), E("L0Y"), E("L0Z")), (1.15, 0.25, 2.7), E("L0S")),
                                    ((0.034, 0.055, 0.505), (1.05, -0.35, -0.55), E("L1S"))]):
    if s_ <= 0:
        continue
    lo = bpy.data.objects.new(f"tl{k}", B.compound_leaf_mesh(variant=k, n_leaflets=3)); B.link(lo)
    lo.location = pos; lo.rotation_euler = rot; lo.scale = (s_, s_, s_); lo.color = (1, 0, 0, 1)
# a second, unripe-to-ripe berry far behind, out of focus
if int(E("BG_BERRY")):
    b2, f2 = B.make_berry("back", ripeness=0.97, scale=0.95, hero=False, seed=5, stem_len=0.01, N=80)
    b2.location = (E("B2X"), E("B2Y"), E("B2Z")); b2.rotation_euler = (math.pi - 0.15, 0.1, 0.4)
# ---- out-of-focus sun flecks behind the berry (they blur into bokeh discs), kept out of the title band
NB = int(E("ORBS"))
if NB:
    rngb = np.random.default_rng(int(E("OSEED")))
    us, uf = B.unit_sphere(16, 10)
    for i in range(NB):
        d = float(rngb.uniform(0.25, 0.55))
        ang_x = float(rngb.uniform(-1, 1)) * 0.36
        ang_z = float(rngb.uniform(E("OZLO"), E("OZHI")))
        p = Vector((d * ang_x, d, d * ang_z)) + Vector((0, 0, 0.5))
        r = float(rngb.uniform(0.0015, 0.004)) * d / 0.4
        col = [(1.0, 0.78, 0.42), (1.0, 0.9, 0.62), (0.85, 0.95, 0.55), (1.0, 0.68, 0.35)][i % 4]
        om = B.mat_simple(f"Orb{i}", (0, 0, 0), rough=1.0, spec=0.0, emission=col, emit_strength=float(rngb.uniform(0.6, 1.6)) * E("OEM"))
        ome = B.make_mesh(f"orb{i}", us, uf); ome.materials.append(om)
        oo = B.obj_from_mesh(f"orb{i}", ome); oo.location = p; oo.scale = (r, r, r)
        oo.visible_shadow = False; oo.visible_diffuse = False; oo.visible_glossy = False
# ---- dew
drops = []
ND = int(E("DROPS"))
if ND:
    dm = bpy.data.materials.new("Dew"); dm.use_nodes = True
    pb = dm.node_tree.nodes["Principled BSDF"]
    pb.inputs["Base Color"].default_value = (1, 1, 1, 1); pb.inputs["Roughness"].default_value = 0.03
    pb.inputs["IOR"].default_value = 1.33; pb.inputs["Transmission Weight"].default_value = 1.0
    dm.blend_method = 'BLEND'; dm.use_screen_refraction = True; dm.refraction_depth = 0.001
    dm.shadow_method = 'NONE'; dm.show_transparent_back = False
    mw = fr.matrix_world; nm = mw.to_3x3().inverted().transposed()
    cam_dir_guess = Vector((E("CX"), E("CY"), E("CZ"))).normalized()
    cand = []
    for v in fr.data.vertices:
        p = mw @ v.co; n = (nm @ v.normal).normalized()
        if n.dot(cam_dir_guess) > 0.55 and n.z > -0.2 and (p - cen).length > 0.0085:
            cand.append((p, n))
    rngd = np.random.default_rng(int(E("DSEED")))
    rngd.shuffle(cand)
    for p, n in cand:
        if len(drops) >= ND:
            break
        if any((p - q).length < 0.0035 for q, _ in drops):
            continue
        drops.append((p, n))
    us, uf = B.unit_sphere(24, 16)
    for i, (p, n) in enumerate(drops):
        r = float(rngd.uniform(0.45, 0.85)) * 0.001 * E("DSCALE")
        dme = B.make_mesh(f"drop{i}", us, uf); dme.materials.append(dm)
        do = B.obj_from_mesh(f"drop{i}", dme)
        q = n.to_track_quat('Z', 'Y')
        do.matrix_world = Matrix.Translation(p + n * r * 0.45) @ q.to_matrix().to_4x4() @ Matrix.Diagonal((r, r, r * 0.72, 1))
    print("DROPS placed", len(drops))
# ---- lights
key = B.area_light(tuple(cen + Vector((E("KX"), E("KY"), E("KZ")))), tuple(cen), size=E("KSIZE"), energy=E("KEY"),
                   color=(1.0, 0.95, 0.88), name="Key")
rim = B.area_light(tuple(cen + Vector((E("RX"), E("RY"), E("RZ")))), tuple(cen), size=E("RSIZE"), energy=E("RIM"),
                   color=(1.0, 0.78, 0.48), name="Rim")
fill = B.area_light(tuple(cen + Vector((0.08, -0.09, -0.05))), tuple(cen), size=0.12, energy=E("FILL"), color=(0.75, 0.85, 1.0), name="Fill")
for _l in (key, rim, fill):
    _l.data.shape = 'DISK'
# ---- camera: short lens with a proportionally small sensor, so focus distance stays far above the focal length
yaw = math.radians(E("CYAW")); pit = math.radians(E("CPIT"))
dist = E("DIST")
T = cen + Vector((E("TX"), 0, E("TZ")))
cpos = T + Vector((math.sin(yaw) * math.cos(pit), -math.cos(yaw) * math.cos(pit), -math.sin(pit))) * dist
LENS_EQ = E("LENS")
cam = B.camera(tuple(cpos), tuple(T), lens=8.0, fstop=E("FSTOP"), clip=(0.002, 20))
cam.data.sensor_width = 36.0 * 8.0 / LENS_EQ
fpt = cen + (cpos - cen).normalized() * E("FOFF")
cam.data.dof.focus_distance = (fpt - cpos).length
B.compositor(sc)
bpy.context.view_layer.update()


def px(p):
    v = world_to_camera_view(sc, cam, p)
    return (round(v.x * 1080), round((1 - v.y) * 1920))


print("PX centre", px(cen), "top", px(cen + Vector((0, 0, 0.0105))), "bottom", px(cen - Vector((0, 0, 0.0105))),
      "left", px(cen - Vector((0.0098, 0, 0))), "right", px(cen + Vector((0.0098, 0, 0))))
if MODE == "render":
    t = time.time()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    B.render_still(sc, 1, OUT)
    print("STILL_TIME", round(time.time() - t, 1))
