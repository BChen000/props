"""dragons / scene.py: lighting presets, the volcanic perch rock, the render loop and pose/shot helpers for both dragons.

Settings (environment):
  RENDERS   where render_frames() writes <shot>/####.png and <shot>/meta.json (default: out/renders next to this file)
  PREVIEW=1 quick look: renders only the first, middle and last frame at 34 % size and 4 samples, into prev_<shot>/
Frames that already exist are skipped, so a stopped render resumes where it left off.
"""
import bpy, sys, os, math, json, time, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bl, envs
import wd_build as WB
import cd_build as CB
from mathutils import Vector, Euler, Matrix
from bpy_extras.object_utils import world_to_camera_view

OUT = os.environ.get("RENDERS") or os.path.join(HERE, "out", "renders")
FPS = 24


def ease(x):
    return bl.smoothstep(x)


def lerp(a, b, t):
    return a + (b - a) * t


# ---------------- lighting presets ----------------
def light(s, preset):
    if preset == "VOLC":
        envs.world_color(s, (0.16, 0.08, 0.08), (0.95, 0.42, 0.2), strength=0.8)
        sun = bl.sun("sun", bl.sun_dir(9, 115), energy=4.2, color=(1.0, 0.5, 0.25), angle=0.04)
        under = bl.area("lava", (2, 0, -6), (2, 0, 3), energy=2500, size=12, color=(1.0, 0.32, 0.08))
        return dict(sun_el=9, sun_az=115)
    if preset == "GOLD":
        envs.world_color(s, (0.3, 0.38, 0.6), (1.0, 0.72, 0.5), strength=0.65)
        bl.sun("sun", bl.sun_dir(8, 70), energy=4.5, color=(1.0, 0.62, 0.36), angle=0.03)
        return dict(sun_el=8, sun_az=70)
    if preset == "MIST":
        envs.world_color(s, (0.55, 0.66, 0.74), (0.86, 0.9, 0.88), strength=1.1)
        bl.sun("sun", bl.sun_dir(28, 60), energy=2.4, color=(1.0, 0.93, 0.82), angle=0.15)
        return dict(sun_el=28, sun_az=60)
    if preset == "STORM":
        envs.world_color(s, (0.1, 0.12, 0.16), (0.28, 0.31, 0.36), strength=0.9)
        bl.sun("sun", bl.sun_dir(35, 40), energy=1.0, color=(0.75, 0.82, 1.0), angle=0.3)
        return dict(sun_el=35, sun_az=40)
    if preset == "RAIN":
        envs.world_color(s, (0.32, 0.4, 0.46), (0.6, 0.66, 0.68), strength=1.0)
        bl.sun("sun", bl.sun_dir(30, 50), energy=1.2, color=(0.9, 0.95, 1.0), angle=0.3)
        return dict(sun_el=30, sun_az=50)
    if preset == "FOSSIL":
        envs.world_color(s, (0.25, 0.28, 0.35), (0.6, 0.5, 0.4), strength=0.35)
        bl.sun("sun", bl.sun_dir(14, 160), energy=5.0, color=(1.0, 0.78, 0.55), angle=0.02)
        return dict(sun_el=14, sun_az=160)


def perch_rock(seed=2, flat_r=3.2, size=26.0, drop=9.0, color=((0.035, 0.03, 0.03), (0.11, 0.09, 0.08)), lava=True):
    n = 260
    xs = np.linspace(-size / 2, size / 2, n)
    X, Y = np.meshgrid(xs, xs)
    Xc = X + 0.6
    R = np.sqrt((Xc / 1.35) ** 2 + (Y / 1.0) ** 2)
    noise = envs.fbm2(n, 7, seed, base=5, persist=0.55)
    hi = envs.fbm2(n, 5, seed + 3, base=20, persist=0.5)
    plateau = np.where(R < flat_r, 0.0, -drop * np.clip((R - flat_r) / 6.0, 0, 1) ** 1.4)
    feet_mask = np.clip((R - 2.2) / 2.0, 0, 1)
    h = plateau + (0.55 * noise + 0.18 * hi) * (0.15 + 0.85 * feet_mask) - 0.02
    h = np.where(R < 2.6, np.minimum(h, np.minimum(-0.01 + 0.012 * hi, 0.0)), h)
    ob = envs.grid_mesh("perch", h, size, size)
    m = envs.rock_mat("perchrock", color[0], color[1], scale=0.35, bump=0.8,
                      lava=((1.0, 0.3, 0.05), 0.62, 6.0) if lava else None)
    ob.data.materials.append(m)
    return ob


# ---------------- render loop ----------------
def setup_render(s, w, h, spp, transparent=True, mblur=True, thresh=0.04):
    bl.render_settings(s, w, h, spp, transparent=transparent, mblur=mblur, thresh=thresh)


PREVIEW = os.environ.get("PREVIEW") == "1"


def render_frames(name, frames, border_objs=None, cam=None, meta_fn=None, still=False):
    s = bpy.context.scene
    frames = list(frames)
    if PREVIEW:
        frames = [frames[0], frames[len(frames) // 2], frames[-1]] if len(frames) > 2 else frames
        s.render.resolution_percentage = 34
        s.cycles.samples = 4
        name = "prev_" + name
    d = os.path.join(OUT, name); os.makedirs(d, exist_ok=True)
    meta = {}
    mpath = os.path.join(d, "meta.json")
    if os.path.exists(mpath):
        meta = json.load(open(mpath))
    t0 = time.time()
    for i, f in enumerate(frames):
        out = os.path.join(d, "%04d.png" % i)
        s.frame_set(f)
        if meta_fn is not None:
            meta[str(i)] = meta_fn()
        if os.path.exists(out):
            continue
        if border_objs is not None:
            bl.auto_border(border_objs, cam or s.camera)
        else:
            s.render.use_border = False
        s.render.filepath = out
        bpy.ops.render.render(write_still=True)
        print("FRAME", name, i, "%.1fs" % (time.time() - t0), flush=True)
    json.dump(meta, open(mpath, "w"))


def screen(p, cam=None):
    s = bpy.context.scene
    c = world_to_camera_view(s, cam or s.camera, Vector(p))
    return [c.x, 1 - c.y, c.z]


def sun_screen(info, cam=None):
    el = math.radians(info["sun_el"]); az = math.radians(info["sun_az"])
    d = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
    s = bpy.context.scene
    cam = cam or s.camera
    p = cam.matrix_world.translation + d * 5000
    return screen(p, cam)


def rock_plate(name, rock, dragon_parts, spp=32):
    """render the static rock once (transparent film), then make it a holdout for the animated frames."""
    s = bpy.context.scene
    d = os.path.join(OUT, ("prev_" if PREVIEW else "") + name); os.makedirs(d, exist_ok=True)
    out = os.path.join(d, "plate.png")
    if not os.path.exists(out):
        for p in dragon_parts:
            p.hide_render = True
        keep = s.cycles.samples
        s.cycles.samples = 4 if PREVIEW else spp
        s.render.use_border = False
        s.frame_set(1)
        s.render.filepath = out
        bpy.ops.render.render(write_still=True)
        s.cycles.samples = keep
        for p in dragon_parts:
            p.hide_render = False
    rock.is_holdout = True

# ---------------- W dragon motion ----------------
def w_idle(rig, t, fold=0.85, lift=0.32, breathe=1.0):
    br = math.sin(2 * math.pi * t / 3.2)
    WB.R(rig, "spine1", pitch=0.012 * br * breathe)
    WB.R(rig, "spine2", pitch=-0.01 * br * breathe)
    WB.pose_tail(rig, t, amp=0.05, freq=0.22, lift=0.05)
    WB.pose_wings(rig, lift=lift + 0.02 * br, fold=fold)


def w_flap(rig, t, period=1.15, amp=1.0, base_lift=0.05, glide=0.0):
    ph = 2 * math.pi * t / period
    a = amp * (1 - glide)
    lift = base_lift + 0.55 * a * math.cos(ph)
    fold = 0.32 * a * max(0.0, math.sin(ph - math.pi)) if math.sin(ph) < 0 else 0.0
    sweep = -0.12 * a * math.sin(ph)
    WB.pose_wings(rig, lift=lift, sweep=sweep, fold=fold)
    for s_, sfx in ((1, ".L"), (-1, ".R")):
        pb = rig.pose.bones["wing2" + sfx]
        pb.rotation_euler.x += -0.25 * a * math.cos(ph - 0.6)
        for i in range(1, 5):
            rig.pose.bones["f%db%s" % (i, sfx)].rotation_euler.x += -0.12 * a * math.cos(ph - 1.0)
    rig.pose.bones["root"].location = (0, 0, 0)
    bob = 0.22 * a * math.sin(ph - 0.5)
    rig.pose.bones["root"].location = (0, bob, 0)
    WB.pose_legs_flight(rig, 1.0)
    WB.pose_tail(rig, t, amp=0.07, freq=0.5 / period, lift=0.02)
    for i in range(5):
        WB.R(rig, "neck%d" % i, pitch=0.04 * a * math.sin(ph - 1.2) - 0.02, yaw=0.0)
    WB.R(rig, "head", pitch=-0.05 * a * math.sin(ph - 1.2) - 0.08)


def key_rig(rig, f):
    WB.key_all(rig, f)


def build_w(prefix="W"):
    D = WB.build(prefix)
    return D


def still_w(name, cam_loc, target, lens, fstop, rock=True, pose=None, res=(720, 1280), spp=48, meta_extra=None):
    s = bl.reset(); info = light(s, "VOLC")
    D = build_w(); rig = D["rig"]
    objs = list(D["parts"])
    if rock:
        objs.append(perch_rock())
    w_idle(rig, 0.4, fold=0.3, lift=0.5)
    if pose:
        pose(rig)
    key_rig(rig, 1)
    cam = bl.camera("cam", cam_loc, target, lens=lens, fstop=fstop)
    setup_render(s, res[0], res[1], spp, mblur=False)
    render_frames(name, [1], objs, cam, meta_fn=lambda: dict({"sun": sun_screen(info)}, **(meta_extra(D) if meta_extra else {})))


def c_setup(preset, path_pts):
    s = bl.reset(); info = light(s, preset)
    D = CB.build("C")
    path = CB.make_path("cpath", path_pts)
    CB.attach_path(D, path)
    return s, info, D, path


def still_c(name, preset, cam_fn, res=(720, 1280), spp=48, rootx=25.0, jaw=0.12):
    pts = [(0, 0, 0), (30, 0, 0), (40, 0.8, 0.25), (50, -0.8, 0.0), (60, 0.6, 0.1), (70, 0, 0), (90, 0, 0)]
    s, info, D, path = c_setup(preset, pts)
    D["root"].location.x = rootx
    D["jaw"].rotation_euler.y = jaw
    bpy.context.view_layer.update()
    camloc, tgt, lens, fstop = cam_fn(D)
    cam = bl.camera("cam", camloc, tgt, lens=lens, fstop=fstop, fit='HORIZONTAL' if res[0] > res[1] else 'VERTICAL')
    setup_render(s, res[0], res[1], spp, mblur=False)
    render_frames(name, [1], D["parts"], cam, meta_fn=lambda: {"sun": sun_screen(info)})


def head_cam(dist, up, fwd, tfwd=0.1, lens=50, fstop=2.8, side_sign=-1, tup=0.15):
    def f(D):
        h, fw = CB.head_frame(D)
        side = np.cross(fw, [0, 0, 1]); side /= np.linalg.norm(side)
        camp = h + side_sign * side * dist + fw * fwd + np.array([0, 0, up])
        return tuple(camp), tuple(h + fw * tfwd + np.array([0, 0, tup])), lens, fstop
    return f


def loop_w(name, preset, cam_loc, target, lens, res, N=28, period_frames=28):
    s = bl.reset(); info = light(s, preset)
    D = build_w(); rig = D["rig"]
    for f in range(1, N + 2):
        t = (f - 1) / FPS
        w_flap(rig, t, period=period_frames / FPS)
        key_rig(rig, f)
    cam = bl.camera("cam", cam_loc, target, lens=lens, fit='HORIZONTAL')
    setup_render(s, res[0], res[1], 12)
    render_frames(name, range(1, N + 1), D["parts"], cam, meta_fn=lambda: {"sun": sun_screen(info),
                  "center": screen((0.5, 0, 3.0))})


def loop_c(name, preset, cam_rel, lens, res, N=48, lam=24.0, A=1.2, B=1.3, up=0.0):
    pts = []
    for i in range(0, 17):
        x = i * lam / 4
        pts.append((x, A * math.sin(2 * math.pi * x / lam), B * math.sin(2 * math.pi * x / lam + 1.2) + up * x))
    xs = np.linspace(0, lam, 2001)
    yy = A * np.sin(2 * np.pi * xs / lam); zz = B * np.sin(2 * np.pi * xs / lam + 1.2) + up * xs
    Llam = float(np.sum(np.sqrt(np.diff(xs) ** 2 + np.diff(yy) ** 2 + np.diff(zz) ** 2)))
    s, info, D, path = c_setup(preset, pts)
    x0 = 1.0 * lam
    for f in range(1, N + 2):
        bl.key_obj(D["root"], f, loc=(x0 + Llam * (f - 1) / N, 0, 0))
        D["jaw"].rotation_euler = (0, 0.1, 0); D["jaw"].keyframe_insert("rotation_euler", frame=f)
    bl.linear_interp(D["root"])
    cam = bl.camera("cam", (0, 0, 0), None, lens=lens, fit='HORIZONTAL')
    ratio = lam / Llam
    for f in range(1, N + 2):
        cx = (x0 + 9.0) * ratio + lam * (f - 1) / N
        loc = Vector((cx + cam_rel[0], cam_rel[1], cam_rel[2] + up * cx))
        cam.location = loc
        bl.look_at(cam, (cx, 0, up * cx))
        cam.keyframe_insert("location", frame=f); cam.keyframe_insert("rotation_euler", frame=f)
    bl.linear_interp(cam)
    setup_render(s, res[0], res[1], 10)
    render_frames(name, range(1, N + 1), D["parts"], cam, meta_fn=lambda: {"sun": sun_screen(info)})
