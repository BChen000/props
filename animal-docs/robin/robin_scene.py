"""robin / robin_scene: a European robin perched on a bramble cane, holding a blue raspberry in its beak.

This is the close-up still behind the robin version of the Wildlore "Blue Raspberry" thumbnail: the bird's
body turned 30 degrees toward the camera, head back toward profile so its eye meets the lens, beak tipped down
into the top of a 1.25x hero berry. Warm golden canopy bokeh, strong backlit rim, round catchlights.

  xvfb-run -a blender -b -noaudio --python robin_scene.py              -> out/robin_with_berry.png (~5 min, 64 samples)
  RES=540x960 TH_SAMP=6 xvfb-run -a blender -b -noaudio --python robin_scene.py   -> quick look (~15 s)
  MODE=dry ...                                                          -> prints eye/berry/head pixel positions only

Every knob below can be overridden from the environment as TH_<KEY>.
Blender 4.0.2, EEVEE (Legacy). Needs bird.py (here), ../wildlore-blender-kit and its forest HDRI.
"""
import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "wildlore-blender-kit"))
sys.path.insert(0, HERE)
import bblib as B, bird
import bpy, math, numpy as np
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view

# --------------------------------------------------------------------------- settings
SETTINGS = dict(
    # render
    SAMP=64, GTAO=0.008, EXPO=0.3, BLOOM=1, BTH=1.0, BINT=0.04, BOKMAX=140, BOKTH=2.0,
    # backdrop patch of babylon_forest.hdr seen by the camera (u = longitude 0..1, a = tilt up in degrees), warm tint
    BGU=0.30, BGA=12, BGG=0.86, BGB=0.6, BGSAT=1.15, WCAM=0.55,
    WSTR=0.45,                       # forest light on the bird (same HDRI, rotated as in shot D)
    # pose in degrees: body yaw toward camera, hip pitch, neck pitch/roll/yaw (yaw back toward profile)
    BYAW=30, HIP=-3, NP=-26, NR=0, NY=-14,
    MASKTOP=0.0165,                  # orange face mask reaches up around the eye (the video's robin uses 0.0135)
    # held berry: scale, forward/down offset from the beak tip (m), tilt toward the beak, seed, spin
    BS=1.25, BF=0.0, BD=0.0117, BTILT=0.0, BSEED=3, BSPIN=0,
    BGCANES=0,                       # 1 adds two far canes with berry clusters behind the bird
    # lights: soft key (offset from head centre), warm rim sun (rotation in degrees), cool fill, warm kick, eye catchlight
    KX=-0.24, KY=-0.12, KZ=0.17, KSIZE=0.16, KEY=0.6,
    RIMX=-62, RIMZ=-20, RIM=30, FILL=0.25, KICK=0.4, CATCH=0.08,
    COREEM=0.15,                     # glow of the berry's inner core showing between drupelets
    # camera: focus point FMIX of the way from eye to berry, target offset (TX, TZ), yaw/pitch (deg), distance (m), lens (mm)
    FMIX=0.5, TX=0.004, TZ=0.0098, CYAW=0, CPIT=8, DIST=0.31, LENS=85, FSTOP=16,
)


def E(k):
    """a setting from SETTINGS, overridable with the environment variable TH_<KEY>"""
    return float(os.environ.get("TH_" + k, SETTINGS[k]))


OUT = os.environ.get("OUT", os.path.join(HERE, "out", "robin_with_berry.png"))
MODE = os.environ.get("MODE", "render")
sc = B.reset()
B.setup_render(sc, 1, "", samples=int(E("SAMP")), gtao_dist=E("GTAO"), exposure=E("EXPO"), bloom=bool(int(E("BLOOM"))),
               still=True, shadow_cube='1024', cascade='2048')
sc.eevee.bloom_threshold = E("BTH"); sc.eevee.bloom_intensity = E("BINT"); sc.eevee.bloom_radius = 6.5
sc.eevee.bokeh_max_size = E("BOKMAX") * B.RES[0] / 1080
sc.eevee.bokeh_threshold = E("BOKTH")


def world_split():
    """the robin is lit by the same forest as shot D; the camera sees a separate, sunlit part of the canopy as backdrop"""
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
    cl = branch((0, 0, 3.4), (1.0, 0.9, 0.72), 1.0)
    u = E("BGU"); a = math.radians(E("BGA"))
    g = (0.5 - u) * 2 * math.pi - math.pi / 2
    cc = branch((a, 0, g), (1.0, E("BGG"), E("BGB")), E("BGSAT"))
    bg = nt.nodes.new("ShaderNodeBackground"); bg.inputs["Strength"].default_value = E("WSTR")
    nt.links.new(cl, bg.inputs["Color"])
    vm = nt.nodes.new("ShaderNodeVectorMath"); vm.operation = 'MINIMUM'; vm.inputs[1].default_value = (8.0, 8.0, 8.0)
    nt.links.new(cc, vm.inputs[0])
    bg2 = nt.nodes.new("ShaderNodeBackground"); bg2.inputs["Strength"].default_value = E("WCAM")
    nt.links.new(vm.outputs[0], bg2.inputs["Color"])
    lp = nt.nodes.new("ShaderNodeLightPath"); mix = nt.nodes.new("ShaderNodeMixShader")
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(bg.outputs[0], mix.inputs[1]); nt.links.new(bg2.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])


world_split()
# ---- perch
rng = np.random.default_rng(41)
ctrl = np.array([[-0.32, 0.04, -0.030], [-0.14, 0.012, -0.010], [0.0, 0.0, -0.006], [0.13, -0.01, -0.010], [0.30, -0.02, -0.032]])
co, P, radii = B.make_cane("cane", ctrl, r0=0.0068, r1=0.0052, rng=rng)
co.color = (0.55, 0, 0, 1)
n = len(P)
ip = int(np.argmin(np.abs(P[:, 0] - 0.012)))
perch = Vector(P[ip]) + Vector((0, 0, radii[ip] * 0.9))
lr = np.random.default_rng(5)
for k, (fi, d, sc_, tl) in enumerate([(0.12, (-0.4, 0.8, 0.25), 1.3, -30), (0.80, (0.3, 0.9, 0.3), 1.3, -35), (0.93, (0.5, -0.7, 0.15), 1.1, -25)]):
    B.attach_leaf(f"lf{k}", co, P, radii, int(n * fi), d, scale=sc_, variant=k % 4, n_leaflets=3 if k % 2 else 5, tilt=tl, rng=lr, wind=0.0)
# ---- robin
R = bird.build_robin("robin", s=1.0)
br = R["root"]; br.location = perch
br.rotation_euler = (0, 0, math.pi / 2 + math.radians(E("BYAW")))
hip, neck = R["hip"], R["neck"]
hip.rotation_euler = (math.radians(E("HIP")), 0, 0)
neck.rotation_euler = (math.radians(E("NP")), math.radians(E("NR")), math.radians(E("NY")))
# thumbnail only: the orange mask reaches up around the eye, as on a real robin
_hm = bpy.data.materials.get("RobinHead")
if _hm:
    for _n in _hm.node_tree.nodes:
        if _n.type == 'MATH' and _n.operation == 'SUBTRACT' and not _n.inputs[0].is_linked and abs(_n.inputs[0].default_value - 0.0135) < 1e-6:
            _n.inputs[0].default_value = E("MASKTOP")
            print("MASKTOP set", _n.inputs[0].default_value)
bpy.context.view_layer.update()
nw = neck.matrix_world.copy()
tip_w = nw @ R["beak_tip"]
base_w = nw @ (Vector(R["beak_tip"]) - Vector((0, 0.0129, 0)))
bdir = (tip_w - base_w).normalized()
hc_w = nw @ Vector((0, 0.010, 0.009))
eye_w = nw @ (Vector((0, 0.010, 0.009)) + Vector((-0.0142, 0.0068, 0.0042)))
down = Vector((0, 0, -1))
# ---- the berry, held by the beak tip at its shoulder
B.CORE_FACTOR = 0.93
BS = E("BS")
c = tip_w + bdir * E("BF") + down * E("BD")
for _ in range(40):
    if (c - hc_w).length >= 0.0195 + 0.0098 * BS:
        break
    c += bdir * 0.0004
axis = ((c - tip_w).normalized() * E("BTILT") + down * (1 - E("BTILT"))).normalized()
bo, fr = B.make_berry("hero", ripeness=1.0, scale=BS, hero=True, seed=int(E("BSEED")), calyx=False, N=110, seg=30, rings=20)
top = c - axis * 0.0095 * BS
q = axis.to_track_quat('Z', 'Y')
bo.matrix_world = Matrix.Translation(top) @ q.to_matrix().to_4x4() @ Matrix.Rotation(math.radians(E("BSPIN")), 4, 'Z') @ Matrix.Scale(BS, 4)
_core = bpy.data.materials.get("BerryCore")
if _core:
    for _n in _core.node_tree.nodes:
        if _n.type == 'MIX_RGB':
            _n.inputs["Color1"].default_value = (0.020, 0.070, 0.42, 1)
            _n.inputs["Color2"].default_value = (0.030, 0.090, 0.50, 1)
    _pc = _core.node_tree.nodes["Principled BSDF"]
    _pc.inputs["Emission Color"].default_value = (0.02, 0.08, 0.55, 1); _pc.inputs["Emission Strength"].default_value = 0.35
hm = bpy.data.materials.get("BerryHair")
if hm:
    hm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.10, 0.13, 0.26, 1)
print("BERRY head-clear", round((c - hc_w).length, 4), "tip-to-centre", round((c - tip_w).length, 4))
# ---- background canes with berries, far behind (soft blue shapes that echo the hero)
bg_berries = []
for k, (ctl, seed) in enumerate([] if not int(E("BGCANES")) else [
        (np.array([[0.02, 0.30, 0.20], [0.10, 0.30, 0.16], [0.20, 0.32, 0.10], [0.34, 0.34, 0.08]]), 7),
        (np.array([[-0.30, 0.42, 0.26], [-0.18, 0.40, 0.21], [-0.08, 0.38, 0.19], [0.04, 0.40, 0.21]]), 11)]):
    ox = E(f"BG{k}X", 0.0); oz = E(f"BG{k}Z", 0.0)
    ctl = ctl + np.array([ox, 0, oz])
    cb, Pb, rb = B.make_cane(f"bgcane{k}", ctl, r0=0.0065, r1=0.004, rng=np.random.default_rng(seed))
    nb = len(Pb)
    for j, (fi, od) in enumerate([(0.35, (0.2, -0.6, -0.3)), (0.7, (-0.3, -0.5, -0.3))]):
        B.make_cluster(f"bgcl{k}{j}", cb, Pb[int(nb * fi)], od, n=3, ripeness=1.0, rng=np.random.default_rng(seed + j), length=0.035, berry_list=bg_berries, wind=0.0)
    for j, (fi, od) in enumerate([(0.15, (0.3, -0.8, 0.3)), (0.55, (-0.4, 0.8, 0.3)), (0.9, (0.2, -0.9, 0.2))]):
        B.attach_leaf(f"bglf{k}{j}", cb, Pb, rb, int(nb * fi), od, scale=1.3, variant=j % 4, n_leaflets=3, tilt=-30, rng=lr, wind=0.0)
# ---- lights
key = B.area_light(tuple(Vector((E("KX"), E("KY"), E("KZ"))) + hc_w), tuple(hc_w), size=E("KSIZE"), energy=E("KEY"), color=(1.0, 0.94, 0.84), name="Key")
rim = B.sun((math.radians(E("RIMX")), 0, math.radians(E("RIMZ"))), energy=E("RIM"), angle=4, cascade_max=0.6, color=(1.0, 0.80, 0.52), name="Rim")
fill = B.area_light(tuple(Vector((0.10, -0.20, -0.08)) + c), tuple(c), size=0.2, energy=E("FILL"), color=(0.82, 0.88, 1.0), name="Fill")
kick = B.area_light(tuple(Vector((-0.10, 0.16, 0.10)) + c), tuple(c), size=0.08, energy=E("KICK"), color=(1.0, 0.85, 0.62), name="Kick")
catch = B.area_light(tuple(Vector((-0.03, -0.25, 0.06)) + eye_w), tuple(eye_w), size=0.03, energy=E("CATCH"), color=(1.0, 0.97, 0.92), name="Catch")
for _l in (key, fill, kick, catch):
    _l.data.shape = 'DISK'  # round highlights on the drupelets and a round catchlight in the eye
if _core:
    _core.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = E("COREEM")
# ---- camera
fm = E("FMIX")
fpt = eye_w.lerp(c, fm)
T = eye_w.lerp(c, 0.5) + Vector((E("TX"), 0, E("TZ")))
yaw = math.radians(E("CYAW")); pit = math.radians(E("CPIT"))
dist = E("DIST")
cpos = T + Vector((math.sin(yaw) * math.cos(pit), -math.cos(yaw) * math.cos(pit), -math.sin(pit))) * dist
cam = B.camera(tuple(cpos), tuple(T), lens=E("LENS"), fstop=E("FSTOP"), clip=(0.005, 50))
cam.data.dof.focus_distance = (fpt - cpos).length
B.compositor(sc)
bpy.context.view_layer.update()


def px(p):
    v = world_to_camera_view(sc, cam, p)
    return (round(v.x * 1080), round((1 - v.y) * 1920))


head_top = hc_w + Vector((0, 0, 0.0185))
print("PX eye", px(eye_w), "berry", px(c), "tip", px(tip_w), "headtop", px(head_top), "headc", px(hc_w),
      "berry_bottom", px(c + axis * 0.0095 * BS), "berry_r_px", px(c + Vector((0.0098 * BS, 0, 0)))[0] - px(c)[0], "perch", px(perch))
if MODE == "render":
    t = time.time()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    B.render_still(sc, 1, OUT)
    print("STILL_TIME", round(time.time() - t, 1))
