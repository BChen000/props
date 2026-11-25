"""blue-raspberry / board_scene: blue raspberries on an edge-glued wooden cutting board, a bowl of them behind.

Food-photography close-up from the Wildlore "Blue Raspberry" thumbnail options: six picked berries (calyx-free,
some upright on their open base, some on their sides) with soft contact shadows on a honey-toned strip board,
window light from the back left, a bounce card front right, a warm rim behind, f/3.2 on a 70 mm lens so the
bowl of ~70 berries further back melts into blue bokeh. Dark slate table and dark room.

  xvfb-run -a blender -b -noaudio --python board_scene.py              -> out/board_scene.png (~5 min, 64 samples)
  RES=540x960 TB_SAMP=8 xvfb-run -a blender -b -noaudio --python board_scene.py   -> quick look (~15 s)
  MODE=dry ...                                                          -> prints pixel positions, no render

Every knob below can be overridden as TB_<KEY>. The board grain comes from build/board_strips.jpg, which
make_board_texture.py builds on first run. Blender 4.0.2, EEVEE (Legacy). Needs ../wildlore-blender-kit.
"""
import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "wildlore-blender-kit"))
sys.path.insert(0, HERE)
import bblib as B
import bpy, math, numpy as np
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view

# --------------------------------------------------------------------------- settings
SETTINGS = dict(
    # render and room
    SAMP=64, GTAO=0.015, EXPO=0.0, BOKMAX=200, WR=0.003, WG=0.003, WB=0.003,
    # board: thickness, grain gamma, wood tone multiplier, oil coat, width/depth, centre, yaw (deg), edge bevel
    THICK=0.024, WGAM=1.25, WOODK=0.8, BCOAT=0.15, BW=0.38, BD=0.30, BX=0.0, BY=0.07, BYAW=-22, BEV=0.005,
    # two leaves that can lie flat on the board under the berries (scale 0 = off, as shipped)
    LX0=-0.075, LY0=0.085, LR0=2.5, LS0=0, LX1=0.075, LY1=0.095, LR1=0.4, LS1=0,
    # berries: layout seed, offset of the whole group, how many layout entries to use, drupelets on near berries
    SEED=7, OX=0.0, OY=0.0, NLAY=99, NHERO=58,
    # bowl of berries behind: on/off, scale of shot Q's bowl, centre, berry count
    BOWL=1, BOWLS=0.6, BOWLX=0.050, BOWLY=0.105, BOWLN=70,
    # berry materials: blue inner core (instead of dark), its glow, drupelet coat roughness/weight, specular
    COREBLUE=1, COREEM=0.25, COATR=0.45, COATW=0.15, DSPEC=0.35,
    # lights (positions in metres): window key back left, bounce fill, warm rim behind
    KX=-0.45, KY=0.20, KZ=0.35, KSIZE=0.4, KEY=18, FILL=3, RX=0.15, RY=0.55, RZ=0.18, RSIZE=0.4, RIM=8,
    # camera: target, yaw/pitch (deg), distance, lens, f-stop, focus point (FX, FY) on the board
    TX=0.0, TY=0.020, TZ=0.016, CYAW=-8, CPIT=30, DIST=0.24, LENS=70, FSTOP=3.2, FX=0.0, FY=-0.006,
)


def E(k):
    """a setting from SETTINGS, overridable with the environment variable TB_<KEY>"""
    return float(os.environ.get("TB_" + k, SETTINGS[k]))


OUT = os.environ.get("OUT", os.path.join(HERE, "out", "board_scene.png"))
BOARD_TEX = os.path.join(HERE, "build", "board_strips.jpg")
if not os.path.exists(BOARD_TEX):
    import make_board_texture
    make_board_texture.build(out=BOARD_TEX)
MODE = os.environ.get("MODE", "render")
sc = B.reset()
B.setup_render(sc, 1, "", samples=int(E("SAMP")), gtao_dist=E("GTAO"), exposure=E("EXPO"), bloom=True, still=True,
               shadow_cube='1024', cascade='2048', sss_samples=9)
sc.eevee.bloom_threshold = 1.2; sc.eevee.bloom_intensity = 0.02; sc.eevee.bloom_radius = 5.0
sc.eevee.bokeh_max_size = E("BOKMAX") * B.RES[0] / 1080
sc.eevee.bokeh_threshold = 1.0
sc.eevee.use_soft_shadows = True
B.world_color(sc, (E("WR"), E("WG"), E("WB")), 1.0)
TOP = E("THICK")


# ---------------------------------------------------------------- materials
def mat_board(BW, BD):
    """edge-glued strip board: photo grain (stills/board_strips.jpg) spanning the top, oiled tint, fine pore bump"""
    m, nt = B.new_mat("BoardWood")
    tc = nt.texcoord()
    oc = tc.outputs["Object"]
    mp = nt.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.0 / BW, 1.0 / BD, 1.0)
    mp.inputs["Location"].default_value = (0.5, 0.5, 0.0)
    nt.link(oc, mp.inputs["Vector"])
    im = nt.new("ShaderNodeTexImage")
    im.image = bpy.data.images.load(BOARD_TEX, check_existing=True)
    im.extension = 'EXTEND'; im.interpolation = 'Cubic'
    nt.link(mp.outputs[0], im.inputs["Vector"])
    gm = nt.new("ShaderNodeGamma"); gm.inputs["Gamma"].default_value = E("WGAM")
    nt.link(im.outputs["Color"], gm.inputs["Color"])
    k = E("WOODK")
    c = nt.mix(1.0, gm.outputs[0], (0.46 * k, 0.33 * k, 0.22 * k, 1), 'MULTIPLY')
    pores = nt.noise(nt.mapping(oc, scale=(40.0, 900.0, 900.0)), scale=6.0, detail=2.0)
    c = nt.mix(nt.math('MULTIPLY', nt.math('SUBTRACT', pores.outputs["Fac"], 0.35), 0.35, clamp=True), c, (0.05, 0.025, 0.01, 1))
    sep = nt.new("ShaderNodeRGBToBW"); nt.link(im.outputs["Color"], sep.inputs[0])
    rough = nt.math('ADD', 0.38, nt.math('MULTIPLY', nt.math('SUBTRACT', 1.0, sep.outputs[0]), 0.25))
    p = B.principled(nt, Base_Color=c, Roughness=rough, Specular_IOR_Level=0.45, Coat_Weight=E("BCOAT"), Coat_Roughness=0.3)
    h = nt.math('ADD', nt.math('MULTIPLY', sep.outputs[0], 0.6), nt.math('MULTIPLY', pores.outputs["Fac"], 0.4))
    nt.link(nt.bump(h, 0.10, 0.0004), p.inputs["Normal"])
    return m


def mat_slate():
    m, nt = B.new_mat("Slate")
    tc = nt.texcoord()
    nz = nt.noise(tc.outputs["Object"], scale=18.0, detail=6.0, rough=0.6)
    c = nt.mix(nz.outputs["Fac"], (0.008, 0.008, 0.009, 1), (0.018, 0.017, 0.018, 1))
    p = B.principled(nt, Base_Color=c, Roughness=0.9, Specular_IOR_Level=0.15)
    nt.link(nt.bump(nz.outputs["Fac"], 0.25, 0.0008), p.inputs["Normal"])
    return m


# ---------------------------------------------------------------- table + board
V = [(-3, -3, 0), (3, -3, 0), (3, 3, 0), (-3, 3, 0)]
me = B.make_mesh("table", V, [[0, 1, 2, 3]], smooth=False); me.materials.append(mat_slate()); B.obj_from_mesh("table", me)
bpy.ops.mesh.primitive_cube_add(size=1.0)
bd = bpy.context.active_object; bd.name = "board"
BW, BDp = E("BW"), E("BD")
bd.scale = (BW, BDp, TOP); bd.location = (E("BX"), E("BY"), TOP / 2)
bd.rotation_euler = (0, 0, math.radians(E("BYAW")))
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bv = bd.modifiers.new("bevel", 'BEVEL'); bv.width = E("BEV"); bv.segments = 6; bv.limit_method = 'NONE'
bd.data.materials.append(mat_board(BW, BDp))
for poly in bd.data.polygons:
    poly.use_smooth = True
bd.data.use_auto_smooth = True; bd.data.auto_smooth_angle = math.radians(40)
# ---------------------------------------------------------------- leaves lying on the board (berries rest on top of them)
def flatten_onto_board(lo):
    me = lo.data.copy(); lo.data = me
    mw = lo.matrix_world.copy(); inv = mw.inverted()
    for v in me.vertices:
        w = mw @ v.co
        if w.z < TOP + 0.0006:
            w.z = TOP + 0.0006
        v.co = inv @ w


bpy.context.view_layer.update()
for k, (pos, rot, s_) in enumerate([((E("LX0"), E("LY0"), TOP + 0.003), (0.0, 0.0, E("LR0")), E("LS0")),
                                    ((E("LX1"), E("LY1"), TOP + 0.003), (0.0, 0.0, E("LR1")), E("LS1"))]):
    if s_ <= 0:
        continue
    lo = bpy.data.objects.new(f"lf{k}", B.compound_leaf_mesh(variant=k + 1, n_leaflets=3)); B.link(lo)
    lo.location = pos; lo.rotation_euler = rot; lo.scale = (s_, s_, s_); lo.color = (1, 0, 0, 1)
    bpy.context.view_layer.update()
    flatten_onto_board(lo)
bpy.context.view_layer.update()
_dg = bpy.context.evaluated_depsgraph_get()


def surface_z(x, y, r):
    """highest surface (board or leaf) under a berry footprint of radius r"""
    best = TOP
    for dx, dy in [(0, 0), (r, 0), (-r, 0), (0, r), (0, -r), (0.7 * r, 0.7 * r), (-0.7 * r, 0.7 * r), (0.7 * r, -0.7 * r), (-0.7 * r, -0.7 * r)]:
        hit, loc, nrm, idx, obj, mat = sc.ray_cast(_dg, Vector((x + dx, y + dy, TOP + 0.05)), Vector((0, 0, -1)))
        if hit and obj.name.startswith("lf"):
            best = max(best, loc.z)
    return best


# ---------------------------------------------------------------- berries
B.CORE_FACTOR = 0.76
rng = np.random.default_rng(int(E("SEED")))
# (x, y, kind, scale, extra)  kind: 'up' sits on its open base, tip up; 'side' lies on its side, hollow facing yaw
layout = [
    (0.000, 0.000, 'up', 1.14, 0), (0.031, 0.010, 'side', 1.05, 115), (-0.032, 0.008, 'side', 1.05, 65),
    (0.012, 0.036, 'up', 1.0, 0), (-0.014, 0.048, 'up', 0.98, 0), (0.046, 0.044, 'side', 0.98, 140),
    (-0.050, 0.046, 'up', 0.96, 0), (0.026, 0.074, 'up', 0.96, 0), (-0.028, 0.084, 'side', 0.95, 30),
    (0.064, 0.006, 'up', 1.0, 0), (0.004, 0.104, 'up', 0.95, 0), (0.060, 0.090, 'up', 0.95, 0),
]
if int(E("BOWL")):
    layout = [(0.000, 0.000, 'up', 1.14, 0), (0.030, 0.008, 'side', 1.05, 115), (-0.031, 0.010, 'side', 1.05, 205),
              (-0.016, 0.045, 'up', 0.98, 0), (-0.058, 0.032, 'up', 0.96, 0), (-0.045, 0.075, 'side', 0.95, 20)]
OX, OY = E("OX"), E("OY")
centres = []
for i, (x, y, kind, s, ex) in enumerate(layout[:int(E("NLAY"))]):
    x += OX; y += OY
    hero = y < 0.06
    bo, fr = B.make_berry(f"b{i}", ripeness=float(rng.uniform(0.96, 1.0)), scale=s, hero=hero, seed=i + 3, calyx=False, stem_len=0.0005,
                          N=int(E("NHERO")) if hero else 70)
    z0 = surface_z(x, y, 0.0075 * s)
    if kind == 'up':
        ang = float(rng.uniform(0, 6.28))
        tilt = float(rng.normal(0, 0.06))
        bo.matrix_world = Matrix.Translation((x, y, z0 + 0.0002 * s)) @ Matrix.Rotation(ang, 4, 'Z') @ Matrix.Rotation(tilt, 4, 'X') @ Matrix.Scale(s, 4)
        c = Vector((x, y, z0 + 0.0095 * s))
    else:
        yaw = math.radians(ex)
        ax = Vector((math.cos(yaw), math.sin(yaw), -0.08)).normalized()
        q = ax.to_track_quat('Z', 'X')
        c = Vector((x, y, z0 + 0.0086 * s))
        bo.matrix_world = Matrix.Translation(c - ax * 0.0095 * s) @ q.to_matrix().to_4x4() @ Matrix.Scale(s, 4)
    centres.append((c, s, i))
if int(E("BOWL")):
    # a small wooden bowl of berries further back on the board (the bowl from shot Q, scaled down)
    BSC = E("BOWLS")
    bx, by = E("BOWLX"), E("BOWLY")
    prof_out = [(0.045, 0.0), (0.075, 0.012), (0.10, 0.035), (0.115, 0.06), (0.118, 0.075)]
    prof_in = [(0.111, 0.075), (0.106, 0.058), (0.092, 0.036), (0.066, 0.018), (0.0, 0.012)]
    prof = [(r * BSC, z * BSC) for r, z in prof_out + prof_in]
    segs = 64
    Vb = []; UVb = []
    for i_, (r, z) in enumerate(prof):
        for s_ in range(segs):
            a = 2 * math.pi * s_ / segs
            Vb.append((bx + r * math.cos(a), by + r * math.sin(a), TOP + z)); UVb.append((s_ / segs * 3, z / BSC * 8 + i_ * 0.05))
    Fb = [[i_ * segs + s_, i_ * segs + (s_ + 1) % segs, (i_ + 1) * segs + (s_ + 1) % segs, (i_ + 1) * segs + s_] for i_ in range(len(prof) - 1) for s_ in range(segs)]
    Vb.append((bx, by, TOP)); UVb.append((0, 0)); cidx = len(Vb) - 1
    Fb += [[cidx, (s_ + 1) % segs, s_] for s_ in range(segs)]
    bme = B.make_mesh("bowl", Vb, Fb, uv=UVb)
    bme.materials.append(B.mat_image("BowlWood", os.path.join(B.ASSETS, "tex", "hardwood2_diffuse.jpg"), None, scale=1.0, rough=0.35, tint=(0.42, 0.28, 0.18)))
    B.obj_from_mesh("bowl", bme)
    pin = [(r * BSC, z * BSC) for r, z in prof_in][::-1]

    def inner_z(r):
        return float(np.interp(r, [p_[0] for p_ in pin], [p_[1] for p_ in pin]))
    brng = np.random.default_rng(4)
    placed = []
    Rb = 0.0091
    for k_ in range(20000):
        if len(placed) >= int(E("BOWLN")):
            break
        r = math.sqrt(brng.uniform(0, 1)) * 0.098 * BSC; a = brng.uniform(0, 2 * math.pi)
        x_, y_ = r * math.cos(a), r * math.sin(a)
        z_ = inner_z(r) + Rb
        for (px_, py_, pz_) in placed:
            d2 = (x_ - px_) ** 2 + (y_ - py_) ** 2
            if d2 < (2 * Rb) ** 2:
                z_ = max(z_, pz_ + math.sqrt((2 * Rb) ** 2 - d2))
        dome = (0.088 + 0.03 * (1 - (r / (0.1 * BSC)) ** 2)) * BSC
        if z_ > dome:
            continue
        placed.append((x_, y_, z_))
    for i_, (x_, y_, z_) in enumerate(placed):
        bo, fr = B.make_berry(f"bowlb{i_}", ripeness=1.0, scale=float(brng.uniform(0.95, 1.05)), hero=False, seed=i_, stem_len=0.0005, calyx=False)
        ax = Vector(brng.normal(0, 1, 3)).normalized()
        bo.matrix_world = Matrix.Translation(Vector((bx + x_, by + y_, TOP + z_)) - ax * 0.0095) @ ax.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    print("BOWL berries", len(placed))
for a in range(len(centres)):
    for b in range(a + 1, len(centres)):
        d = (centres[a][0] - centres[b][0]).length
        if d < 0.0185 * (centres[a][1] + centres[b][1]) / 2:
            print("OVERLAP", centres[a][2], centres[b][2], round(d, 4))
_core = bpy.data.materials.get("BerryCore")
if _core and int(E("COREBLUE")):
    # the hollow of a picked berry reads as a deep blue cup rather than a black hole
    for _n in _core.node_tree.nodes:
        if _n.type == 'MIX_RGB':
            _n.inputs["Color1"].default_value = (0.020, 0.060, 0.34, 1)
            _n.inputs["Color2"].default_value = (0.035, 0.085, 0.45, 1)
    _pc = _core.node_tree.nodes["Principled BSDF"]
    _pc.inputs["Emission Color"].default_value = (0.02, 0.08, 0.55, 1); _pc.inputs["Emission Strength"].default_value = E("COREEM")
hm = bpy.data.materials.get("BerryHair")
if hm:
    hm.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.0
    hm.blend_method = 'CLIP'
    hm.shadow_method = 'NONE'
_dm = bpy.data.materials.get("Drupelet")
if _dm:
    _pd = _dm.node_tree.nodes["Principled BSDF"]
    _pd.inputs["Coat Roughness"].default_value = E("COATR")
    _pd.inputs["Coat Weight"].default_value = E("COATW")
    _pd.inputs["Specular IOR Level"].default_value = E("DSPEC")
# ---------------------------------------------------------------- lights: soft window from back-left, bounce card front-right, warm rim
key = B.area_light((E("KX"), E("KY"), E("KZ")), (0.0, 0.03, TOP), size=E("KSIZE"), energy=E("KEY"), color=(1.0, 0.94, 0.85), name="Window")
fill = B.area_light((0.45, -0.55, 0.25), (0.0, 0.02, TOP), size=0.6, energy=E("FILL"), color=(0.85, 0.9, 1.0), name="Bounce")
rim = B.area_light((E("RX"), E("RY"), E("RZ")), (0.0, 0.03, TOP), size=E("RSIZE"), energy=E("RIM"), color=(1.0, 0.82, 0.6), name="Rim")
for _l in (key, fill, rim):
    _l.data.shape = 'DISK' if _l is not key else 'RECTANGLE'
    _l.data.use_contact_shadow = True
    _l.data.contact_shadow_distance = 0.012
    _l.data.contact_shadow_thickness = 0.004
    _l.data.shadow_buffer_bias = 0.05
# ---------------------------------------------------------------- camera
T = Vector((E("TX"), E("TY"), TOP + E("TZ")))
yaw = math.radians(E("CYAW")); pit = math.radians(E("CPIT"))
dist = E("DIST")
cpos = T + Vector((math.sin(yaw) * math.cos(pit), -math.cos(yaw) * math.cos(pit), math.sin(pit))) * dist
cam = B.camera(tuple(cpos), tuple(T), lens=E("LENS"), fstop=E("FSTOP"), clip=(0.01, 20))
F0 = Vector((E("FX"), E("FY"), TOP + 0.010))
cam.data.dof.focus_distance = (F0 - cpos).length
B.compositor(sc)
bpy.context.view_layer.update()


def px(p):
    v = world_to_camera_view(sc, cam, p)
    return (round(v.x * 1080), round((1 - v.y) * 1920))


print("PX front", px(centres[0][0]), "last", px(centres[-1][0]), "bowl", px(Vector((E("BOWLX"), E("BOWLY"), TOP + 0.05))), "boardback", px(Vector((0, 0.07 + BDp / 2, TOP))), "boardfront", px(Vector((0, 0.07 - BDp / 2, TOP))))
if MODE == "render":
    t = time.time()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    B.render_still(sc, 1, OUT)
    print("STILL_TIME", round(time.time() - t, 1))
