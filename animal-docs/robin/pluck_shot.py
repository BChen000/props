"""robin / pluck_shot: shot D of "The Blue Raspberry": the robin on a fruiting cane plucks the hero berry and turns
toward the camera holding it (163 frames, 6.8 s at 24 fps, ~12 min at 3 TAA samples on 2 cores).

How the pluck works:
- The berry (a calyx-on-cane 'tb' with its fruit 'tfruit') stays on the plant.
- The head lunges in. For each frame up to contact, a small solver picks hip/neck angles (0.5 degree steps) that keep
  the beak tip on a slide path toward the berry with the least change from the previous frame.
- On contact, 'tfruit' is hidden and a loose copy 'bb' parented to the neck is shown at the same place, with the beak
  tip sunk 2 mm into its side. The calyx stays behind on the cane, as a real raspberry's does.
- After the release the neck retracts along its own axis (rt) instead of re-solving: a free solver found absurd poses.
- CORECHK lines in the log report the 3D and on-screen clearance between beak, head and the berry's core every few frames.

  xvfb-run -a blender -b -noaudio --python pluck_shot.py -- anim     -> out/pluck.mp4
  SF=40,75,120 xvfb-run -a blender -b -noaudio --python pluck_shot.py -- still   -> out/pluck_40.png ...
  RES=540x960 FRANGE=60-100 ... -- anim                              -> part of the shot at half size
"""
import sys, time, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "wildlore-blender-kit"))
sys.path.insert(0, HERE)
import bblib as B, bird
import bpy, math, numpy as np
from mathutils import Vector, Matrix, Euler
MODE = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "still"
FR = int(os.environ.get("FR", "163"))   # frames; the episode cut uses 163
sc = B.reset()
B.setup_render(sc, FR, "", samples=3, gtao_dist=0.05, exposure=0.35)
B.world_hdri(sc, "babylon_forest.hdr", strength=0.9, cam_strength=1.05, rot=3.4, clamp_bg=2.0, tint=(1.0, 0.92, 0.75))
B.sun((math.radians(60), 0, math.radians(125)), energy=4.5, angle=2.5, cascade_max=3.0, color=(1.0, 0.82, 0.6))
B.area_light((-0.4, -0.9, 1.1), (0.0, 0.0, 0.85), size=0.8, energy=12, color=(1.0, 0.95, 0.9))
rng = np.random.default_rng(41)
root = B.empty("plantroot", (0, 0, 0))
ctrl = np.array([[-0.45, 0.06, 0.74], [-0.2, 0.02, 0.795], [0.0, 0.0, 0.805], [0.18, 0.01, 0.79], [0.42, 0.05, 0.72]])
co, P, radii = B.make_cane("cane", ctrl, r0=0.0065, r1=0.0045, rng=rng, parent=root)
co.color = (0.55, 0, 0, 1)
n = len(P)
# perch point
ip = int(n * 0.42)
perch = Vector(P[ip]) + Vector((0, 0, radii[ip] * 0.9))
R = bird.build_robin("robin", s=1.0)
br = R["root"]
br.location = perch
br.rotation_euler = (0, 0, math.radians(-90))  # bird +Y -> world +X
hip, neck = R["hip"], R["neck"]
# lunge pose -> beak tip world position; berry placed so the beak tip just enters it and the head stays clear
def set_pose(hp, nk, ny=0.0):
    hip.rotation_euler = (math.radians(hp), 0, 0)
    neck.rotation_euler = (math.radians(nk), 0, math.radians(ny))
    neck.location = Vector((0, 0.021, 0.014)) + Vector((0, 0.010 * max(0, -nk) / 30, 0))
LUNGE = (-12, -20)
set_pose(*LUNGE)
bpy.context.view_layer.update()
nw0 = neck.matrix_world.copy()
tip_w = nw0 @ R["beak_tip"]
base_w = nw0 @ (Vector(R["beak_tip"]) - Vector((0, 0.0129, 0)))
bdir = (tip_w - base_w).normalized()
head_c = nw0 @ Vector((0, 0.010, 0.009))
berry_c = tip_w + bdir * 0.0068
for _ in range(30):
    if (berry_c - head_c).length >= 0.0195 + 0.0098:
        break
    berry_c += bdir * 0.0005
calyx = berry_c + Vector((0, 0, 0.0098))
print("CLEARANCE", round((berry_c - head_c).length, 4), "TIPDEPTH", round(0.0088 - (berry_c - tip_w).length, 4))
set_pose(0, 0)
# peduncle from cane to calyx
ia = int(n * 0.55)
A = P[ia] + np.array([0, 0, -radii[ia] * 0.5])
Cc = np.array(calyx)
mid = (A + Cc) / 2 + np.array([0.004, -0.003, 0.004])
ped = B.catmull([A, mid, Cc], 6)
pv, pf, puv = B.tube_mesh(ped, np.linspace(0.0011, 0.0006, len(ped)), sides=6)
pme = B.make_mesh("ped", pv, pf, uv=puv); pme.materials.append(B.mat_pedicel())
pedo = B.obj_from_mesh("ped", pme, parent=root)
down = Vector((0, 0, -1))
hang = down.to_track_quat('Z', 'Y').to_matrix().to_4x4()
tb, tfruit = B.make_berry("target", ripeness=1.0, scale=1.0, hero=True, seed=7, parent=root, stem_len=0.0015)
tb.matrix_local = Matrix.Translation(calyx) @ hang
rme = B.receptacle_mesh()
rec = bpy.data.objects.new("rec", rme); B.link(rec); rec.parent = root
rec.matrix_local = Matrix.Translation(calyx) @ hang
# other berries in the same cluster + another cluster
berries = []
B.make_cluster("cl2", co, P[int(n * 0.66)], (0.3, -0.5, -0.3), n=3, ripeness=1.0, rng=np.random.default_rng(6), length=0.03, berry_list=berries, wind=0.4)
B.make_cluster("cl3", co, P[int(n * 0.85)], (0.4, 0.5, -0.3), n=4, ripeness=0.95, rng=np.random.default_rng(9), length=0.035, berry_list=berries, wind=0.4)
B.make_cluster("cl4", co, P[int(n * 0.12)], (-0.4, 0.4, -0.3), n=3, ripeness=0.9, rng=np.random.default_rng(13), length=0.035, berry_list=berries, wind=0.4)
lr = np.random.default_rng(5)
for k, (fi, d, sc_, tl) in enumerate([(0.05, (-0.5, 0.8, 0.3), 1.3, -35), (0.3, (-0.2, 0.9, 0.4), 1.4, -40), (0.72, (0.3, 0.9, 0.35), 1.4, -40),
                                      (0.93, (0.6, 0.6, 0.2), 1.2, -30), (0.62, (0.4, -0.9, 0.1), 1.0, -20)]):
    B.attach_leaf(f"lf{k}", co, P, radii, int(n * fi), d, scale=sc_, variant=k % 4, n_leaflets=3 if k % 2 else 5, tilt=tl, rng=lr, wind=0.6)
# ---- animation
PECK1, PLUCK, SLIDE = 40, 70, 7
L0, L1_ = LUNGE
def pose_key(f, hp, nk, ny=0.0, nr=0.0, interp='BEZIER', rt=0.0):
    hip.rotation_euler = (math.radians(hp), 0, 0); hip.keyframe_insert("rotation_euler", frame=f)
    neck.rotation_euler = (math.radians(nk), math.radians(nr), math.radians(ny)); neck.keyframe_insert("rotation_euler", frame=f)
    neck.location = Vector((0, 0.021 - rt, 0.014)) + Vector((0, 0.010 * max(0, -nk) / 30, 0)); neck.keyframe_insert("location", frame=f)
seq = [(1, 0, 0, 0, 0), (6, 0, 0, 0, 0), (8, 0, 4, 32, 0), (15, 0, 4, 32, 0), (17, 0, 0, -10, 12), (25, 0, 0, -10, 12), (27, 0, -6, 0, 0),
       (32, -4, -8, 0, 0), (PECK1 - 3, -9, -15, 0, 0), (PECK1, L0, L1_, 0, 0), (PECK1 + 4, -6, -6, 0, 0), (PECK1 + 9, 0, 2, 0, 0),
       (PECK1 + 14, 0, 2, 18, 8), (PLUCK - 8, -5, -8, 0, 0), (PLUCK - 3, -9, -15, 0, 0), (PLUCK, L0, L1_, 0, 0)]
for f, hp, nk, ny, nr in seq:
    pose_key(f, hp, nk, ny, nr)
# pull: the berry slides straight down off its receptacle while the beak follows it (solved pose per frame)
pivot = B.empty("pedpiv", tuple(A))
bpy.context.view_layer.update()
for o in (pedo, tb, rec):
    o.parent = pivot
    o.matrix_parent_inverse = pivot.matrix_world.inverted()
bpy.context.view_layer.update()
print("CHECK fruit-vs-tip at lunge:", round((tfruit.matrix_world @ Vector((0, 0, 0.0095)) - berry_c).length, 4))
DROP = 0.0175
def tip_for(hp, nk):
    set_pose(hp, nk)
    bpy.context.view_layer.update()
    return neck.matrix_world @ R["beak_tip"]
best = (L0, L1_)
for k in range(1, SLIDE + 1):
    d = DROP * B.ease(k / SLIDE)
    target = tip_w + Vector((0, 0, -d))
    bh, bn = best
    cand = None
    for hp in np.arange(bh - 8, bh + 8.01, 0.5):
        for nk in np.arange(bn - 12, bn + 12.01, 0.5):
            e = (tip_for(hp, nk) - target).length
            # prefer the smallest change from the previous frame's pose, so the body doesn't jolt between near-equal solutions
            cost = e + 0.00012 * abs(hp - bh) + 0.00005 * abs(nk - bn)
            if cand is None or cost < cand[3]:
                cand = (e, hp, nk, cost)
    best = (cand[1], cand[2])
    pose_key(PLUCK + k, cand[1], cand[2], 0, 0)
    tfruit.location = (0, 0, d); tfruit.keyframe_insert("location", frame=PLUCK + k)
    print("SLIDE", k, "err", round(cand[0], 4), "pose", cand[1], cand[2])
tfruit.location = (0, 0, 0); tfruit.keyframe_insert("location", frame=PLUCK)
END = PLUCK + SLIDE
# after release: turn the head toward the camera so the berry swings clear of the receptacle, then lift
PULL = 6
bh, bn = best
RTB = float(os.environ.get("RTB", "0.020"))
pose_key(END + PULL, bh + 2, bn + 3, 0, 0, rt=RTB)
E2 = END + PULL
pose_key(E2 + 8, -8, -8, -4, 0, rt=RTB)
for f, hp, nk, ny, nr in [(E2 + 14, -7, -6, -32, 0), (E2 + 22, -7, -6, -42, 5), (E2 + 26, -7, -6, -42, 5), (E2 + 30, -6, -5, -24, -4),
                          (E2 + 46, -6, -5, -24, -4), (E2 + 49, -7, -6, -36, 0), (FR, -7, -6, -36, 0)]:
    pose_key(f, hp, nk, ny, nr)
for o in (hip, neck):
    for fc in o.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            if PLUCK < kp.co[0] <= END + PULL:
                kp.interpolation = 'LINEAR'
            else:
                kp.interpolation = 'BEZIER'; kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'
for fc in tfruit.animation_data.action.fcurves:
    for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
# berry jiggle after peck 1
for f, a_ in [(1, 0), (PECK1, 0), (PECK1 + 3, 0.2), (PECK1 + 7, -0.12), (PECK1 + 11, 0.06), (PECK1 + 16, -0.02), (PECK1 + 21, 0)]:
    tb.delta_rotation_euler = (0, a_, 0); tb.keyframe_insert("delta_rotation_euler", index=1, frame=f)
# swap: once clear of the receptacle the berry rides with the beak
sc.frame_set(END)
bpy.context.view_layer.update()
bw = tfruit.matrix_world.copy(); nw = neck.matrix_world.copy()
bb = bpy.data.objects.new("beakberry", tfruit.data); B.link(bb)
bb.parent = neck; bb.matrix_parent_inverse = Matrix.Identity(4)
bb.matrix_local = nw.inverted() @ bw
bb.color = tfruit.color
for o, vis in ((tfruit, True), (bb, False)):  # the calyx (on tb) stays on the stalk with the core
    o.hide_render = not vis; o.keyframe_insert("hide_render", frame=END - 1)
    o.hide_render = vis; o.keyframe_insert("hide_render", frame=END)
for o in (tfruit, bb):
    for fc in o.animation_data.action.fcurves:
        if fc.data_path == "hide_render":
            for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'
for fchk in (PECK1, PLUCK, END, END + PULL, END + 20):
    sc.frame_set(fchk); bpy.context.view_layer.update()
    tipc = neck.matrix_world @ R["beak_tip"]
    fobj = bb if fchk >= END else tfruit
    print("FRAMECHK", fchk, "tip-to-berrycentre", round((tipc - (fobj.matrix_world @ Vector((0, 0, 0.0095)))).length, 4))
# the stalk springs back once released (pivot at the cane)
for f, a_ in [(END, 0), (END + 3, 0.05), (END + 8, -0.03), (END + 13, 0.015), (END + 20, 0)]:
    pivot.rotation_euler = (a_, 0, 0); pivot.keyframe_insert("rotation_euler", index=0, frame=f)
def _seg_dist(p, a, b):
    ab = b - a; t = max(0.0, min(1.0, (p - a).dot(ab) / ab.dot(ab)))
    return (p - (a + ab * t)).length
for fchk in range(END, END + 31):
    sc.frame_set(fchk); bpy.context.view_layer.update()
    fobj = bb if fchk >= END else tfruit
    bc = fobj.matrix_world @ Vector((0, 0, 0.0095))
    ca = rec.matrix_world @ Vector((0, 0, 0.0)); cb = rec.matrix_world @ Vector((0, 0, 0.012))
    flat = lambda v: Vector((v.x, 0.0, v.z))
    hc = neck.matrix_world @ Vector((0, 0.010, 0.009))
    tipc = neck.matrix_world @ R["beak_tip"]
    print("CORECHK", fchk, "3d", round(_seg_dist(bc, ca, cb), 4), "view", round(_seg_dist(flat(bc), flat(ca), flat(cb)), 4),
          "head-core", round(_seg_dist(hc, ca, cb), 4), "tip-core", round(_seg_dist(tipc, ca, cb), 4))
sc.frame_set(1)
# breathing
B.driver_expr(R["body"], "scale", 2, "1+0.015*sin(frame*0.35)")
tgt = Vector((perch.x + 0.03, 0.0, perch.z + 0.035))
def cpos(t):
    e = B.ease(t)
    return (tgt.x - 0.06 + 0.02 * e, -0.95 + 0.12 * e, tgt.z + 0.06 - 0.01 * e)
cam = B.camera(cpos(0), tgt, lens=100, fstop=6.3, clip=(0.02, 80))
B.camera_path(cam, 1, FR, cpos, lambda t: tuple(tgt), focus_fn=lambda t: (Vector(cpos(t)) - tgt).length)
B.compositor(sc)
OUTDIR = os.path.join(HERE, "out")
os.makedirs(OUTDIR, exist_ok=True)
if MODE == "still":
    for f in [int(x) for x in os.environ.get("SF", "40,75").split(",")]:
        B.render_still(sc, f, os.path.join(OUTDIR, f"pluck_{f}.png"))
else:
    t = time.time(); B.render(sc, os.path.join(OUTDIR, "pluck.mp4")); print("ANIM_TIME", round(time.time() - t, 2))
