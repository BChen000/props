"""two-dragons-episode / shots3d.py: every Blender render of "The Two Dragons", built on ../dragons.

  python shots3d.py <shot>             -> $RENDERS/<shot>/####.png (+ plate.png for rock shots) and meta.json
  PREVIEW=1 python shots3d.py <shot>   first/middle/last frame at 34 % size and 4 samples, into prev_<shot>/
  python shots3d.py --list             all shot names

RENDERS defaults to $WORK/renders, WORK to $TWO_DRAGONS_WORK or build/ next to this file. Finished frames are skipped,
so a stopped render resumes. Shots (frames at 24 fps):
  animated  u05a_n 122  W perched, wings open            u06_n 132  W rears, throat glows
            u07a_n 124  W head close-up, jaw opens, ignition   u07b_n 146  W breathes fire (wide)
            u09a_n 131  C body passes the camera          u09b_n 148  C head, tracking camera
            u16b_n 116  W roars, wings spread
  stills    s02a s18a s05b s05c s19w (W)   s02b s18b s19c s19ct (C)   s03 fossil   t_w t_c thumbnails
  loops     l_w_side_gold l_w_back_gold l_w_side_volc (28-frame wingbeats)
            l_c_side_gold l_c_side_mist l_c_34_storm l_c_up_rain (48-frame serpent loops)
The *_n shots are the first cut's shots with pre-roll and post-roll added for the slower narration: each one's
motion formulas run on fo = f - D, so frames D+1.. reproduce the original shot exactly and the rest extend it.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.environ.get("TWO_DRAGONS_WORK") or os.path.join(HERE, "build")
os.environ.setdefault("RENDERS", os.path.join(WORK, "renders"))
sys.path.insert(0, os.path.join(HERE, "..", "dragons"))
from scene import *


def clamp01(x):
    return min(max(x, 0.0), 1.0)


# ---------------- animated shots ----------------
def shot_u05a_n(D=50):
    s = bl.reset(); info = light(s, "VOLC")
    W = build_w(); rig = W["rig"]; rock = perch_rock()
    N = 72; NT = D + N
    for f in range(1, NT + 1):
        fo = f - D
        t = (fo - 1) / FPS
        u = ease((fo - 14) / 46)
        w_idle(rig, t, fold=lerp(0.85, 0.0, u), lift=lerp(0.32, 0.55, u))
        WB.pose_neck(rig, pitch=lerp(0.0, 0.18, u), head_pitch=lerp(-0.12, 0.0, u), yaw=0.15 * math.sin(t * 0.8), head_yaw=0.1)
        key_rig(rig, f)
    cam = bl.camera("cam", (10.0, -9.0, 1.6), (0.8, 0, 3.4), lens=30, fstop=5.6)
    setup_render(s, 720, 1280, 8)
    rock_plate("u05a_n", rock, W["parts"])
    render_frames("u05a_n", range(1, NT + 1), W["parts"], cam, meta_fn=lambda: {"sun": sun_screen(info)})


def shot_u06_n(D=34, P=12):
    s = bl.reset(); info = light(s, "VOLC")
    W = build_w(); rig = W["rig"]; rock = perch_rock()
    N = 86; NT = D + N + P
    for f in range(1, NT + 1):
        fo = f - D
        t = (fo - 1) / FPS
        u = ease((fo - 6) / 50)
        sx = ease(clamp01((1 - fo) / D))
        w_idle(rig, t, fold=0.3, lift=0.5)
        WB.pose_neck(rig, pitch=lerp(0.0, 0.42, u), yaw=lerp(0.1, -0.05, u) + 0.07 * sx, head_pitch=lerp(-0.1, 0.18, u), jaw=0.06 * u)
        WB.R(rig, "spine2", pitch=0.04 * u)
        W["body"]["glow"] = 0.0
        key_rig(rig, f)
        g = ease((fo - 40) / 40)
        for ob in (W["body"], W["jaw"]):
            ob["glow"] = 0.9 * g
            ob.keyframe_insert('["glow"]', frame=f)
    cam = bl.camera("cam", (10.5, -7.5, 3.8), (2.4, 0, 4.7), lens=40, fstop=4.0)
    setup_render(s, 720, 1280, 6)
    rock_plate("u06_n", rock, W["parts"])
    render_frames("u06_n", range(1, NT + 1), W["parts"], cam, meta_fn=lambda: {"sun": sun_screen(info)})


def shot_u07a_n(D=52):
    s = bl.reset(); info = light(s, "VOLC")
    W = build_w(); rig = W["rig"]
    N = 72; NT = D + N
    pl = bl.point("firelight", (5.9, -0.3, 4.3), energy=0, color=(1.0, 0.45, 0.12), radius=0.8)
    for f in range(1, NT + 1):
        fo = f - D
        t = (fo - 1) / FPS
        u = ease((fo - 4) / 30)
        sx = ease(clamp01((1 - fo) / D))
        w_idle(rig, t, fold=0.3, lift=0.5)
        WB.pose_neck(rig, pitch=lerp(0.42, 0.12, u) - 0.06 * sx, head_pitch=lerp(0.18, -0.08, u),
                     jaw=lerp(0.06, 0.55, ease((fo - 20) / 18)))
        key_rig(rig, f)
        for ob in (W["body"], W["jaw"]):
            ob["glow"] = (lerp(0.9, 1.0, u) - 0.16 * sx) * (1.0 - 0.6 * ease((fo - 50) / 20))
            ob.keyframe_insert('["glow"]', frame=f)
        ign = ease((fo - 40) / 10)
        pl.data.energy = ign * (800 + 260 * math.sin(fo * 1.7) + 180 * math.sin(fo * 3.1))
        pl.data.keyframe_insert("energy", frame=f)
    cam = bl.camera("cam", (7.2, -4.0, 4.7), (4.1, 0, 4.45), lens=45, fstop=2.8)
    setup_render(s, 720, 1280, 6)

    def meta():
        m = W["mouth"].matrix_world.translation
        return {"sun": sun_screen(info), "mouth": screen(m), "mouth_fwd": screen(W["mouth"].matrix_world @ Vector((1.0, 0, -0.2)))}
    render_frames("u07a_n", range(1, NT + 1), W["parts"], cam, meta_fn=meta)


def shot_u07b_n(E=48, NT=146):
    s = bl.reset(); info = light(s, "VOLC")
    W = build_w(); rig = W["rig"]; rock = perch_rock()
    pl = bl.point("firelight", (8.5, 0, 4.6), energy=0, color=(1.0, 0.45, 0.12), radius=2.0)
    for f in range(1, NT + 1):
        t = (f - 1) / FPS
        w_idle(rig, t, fold=0.15, lift=0.55)
        thr = ease((f - 1) / 14)
        WB.pose_neck(rig, pitch=lerp(0.25, -0.05, thr) + 0.03 * math.sin(t * 9), yaw=0.08 * math.sin(t * 1.3),
                     head_pitch=lerp(0.0, -0.12, thr), jaw=0.5 + 0.05 * math.sin(t * 11))
        key_rig(rig, f)
        fire = ease((f - 4) / 6) * (1 - ease((f - 84 - E) / 10))
        pl.data.energy = fire * (5000 + 1500 * math.sin(f * 1.9) + 900 * math.sin(f * 4.3))
        pl.data.keyframe_insert("energy", frame=f)
    cam = bl.camera("cam", (11.0, -10.5, 2.2), (3.0, 0, 3.8), lens=26, fstop=8)
    setup_render(s, 720, 1280, 8)
    rock_plate("u07b_n", rock, W["parts"])

    def meta():
        m = W["mouth"].matrix_world.translation
        return {"sun": sun_screen(info), "mouth": screen(m), "mouth_fwd": screen(W["mouth"].matrix_world @ Vector((1.0, 0, -0.2)))}
    render_frames("u07b_n", range(1, NT + 1), W["parts"], cam, meta_fn=meta)


def shot_u09a_n(D=36):
    pts = [(0, 0, 0), (18, 0, 0), (25, 2.6, 1.0), (32, -2.6, -0.8), (39, 2.6, 1.0), (46, -2.6, -0.8), (53, 2.6, 0.8), (60, -2.2, -0.4), (67, 1.6, 0.3), (80, 0, 0), (100, 0, 0)]
    s, info, C, path = c_setup("MIST", pts)
    N = 95; NT = D + N
    for f in range(1, NT + 1):
        fo = f - D
        x = 11.0 + (27.0 - 11.0) * (fo - 1) / (N - 1)
        bl.key_obj(C["root"], f, loc=(x, 0, 0))
        C["jaw"].rotation_euler = (0, 0.12 + 0.05 * math.sin(fo * 0.15), 0); C["jaw"].keyframe_insert("rotation_euler", frame=f)
    bl.linear_interp(C["root"])
    cam = bl.camera("cam", (32.5, -8.0, -3.4), (28.0, 0, 0.8), lens=27, fstop=8)
    setup_render(s, 720, 1280, 6)
    render_frames("u09a_n", range(1, NT + 1), C["parts"], cam, meta_fn=lambda: {"sun": sun_screen(info)})


def shot_u09b_n(P=56):
    pts = [(0, 0, 0), (30, 0, 0), (40, 0.6, 0.2), (50, -0.5, 0.0), (60, 0.4, 0.1), (70, 0, 0), (90, 0, 0)]
    s, info, C, path = c_setup("MIST", pts)
    N = 92; NT = N + P
    for f in range(1, NT + 1):
        x = 25.0 + 2.5 * (f - 1) / (N - 1)
        bl.key_obj(C["root"], f, loc=(x, 0, 0))
        C["jaw"].rotation_euler = (0, 0.1 + 0.06 * math.sin(f * 0.09), 0); C["jaw"].keyframe_insert("rotation_euler", frame=f)
    bl.linear_interp(C["root"])
    s.frame_set(46)
    h, fw = CB.head_frame(C)
    side = np.cross(fw, [0, 0, 1]); side /= np.linalg.norm(side)
    off = -side * 4.0 + fw * 1.6 + np.array([0, 0, 0.55])
    cam = bl.camera("cam", tuple(h + off), tuple(h), lens=40, fstop=3.2)
    for f in range(1, NT + 1):
        s.frame_set(f)
        hf, _ = CB.head_frame(C)
        cam.location = Vector(tuple(hf + off))
        bl.look_at(cam, tuple(hf + fw * 0.35 + np.array([0, 0, 0.2])))
        cam.keyframe_insert("location", frame=f); cam.keyframe_insert("rotation_euler", frame=f)
    setup_render(s, 720, 1280, 6)
    render_frames("u09b_n", range(1, NT + 1), C["parts"], cam, meta_fn=lambda: {"sun": sun_screen(info)})


def shot_u16b_n(P=28):
    s = bl.reset(); info = light(s, "VOLC")
    W = build_w(); rig = W["rig"]; rock = perch_rock(seed=5)
    N = 88; NT = N + P
    for f in range(1, NT + 1):
        t = (f - 1) / FPS
        u = ease((f - 1) / 26)
        w_idle(rig, t, fold=lerp(0.6, 0.0, u), lift=lerp(0.35, 0.75, u))
        r = ease((f - 30) / 12) * (1 - ease((f - 74) / 12))
        WB.pose_neck(rig, pitch=lerp(0.1, 0.45, u) + 0.06 * r * math.sin(t * 14), yaw=0.15 * r * math.sin(t * 2.2),
                     head_pitch=lerp(0.0, 0.25, r), jaw=0.7 * r)
        WB.R(rig, "spine2", pitch=0.08 * u)
        WB.R(rig, "spine1", pitch=0.06 * u)
        key_rig(rig, f)
    cam = bl.camera("cam", (12.0, 6.5, 0.4), (0.5, 0, 4.2), lens=26, fstop=8)
    setup_render(s, 720, 1280, 6)
    rock_plate("u16b_n", rock, W["parts"])
    render_frames("u16b_n", range(1, NT + 1), W["parts"], cam,
                  meta_fn=lambda: {"sun": sun_screen(info), "mouth": screen(W["mouth"].matrix_world.translation)})


# ---------------- stills, loops, fossil, thumbnails ----------------
def shot_s02a():
    still_w("s02a", (6.6, -4.4, 4.85), (4.15, 0, 4.45), 50, 2.8, rock=False,
            pose=lambda r: WB.pose_neck(r, pitch=0.12, head_pitch=0.0, head_yaw=-0.1))


def shot_s18a():
    still_w("s18a", (4.35, -0.95, 4.62), (4.0, -0.3, 4.55), 70, 2.0, rock=False,
            pose=lambda r: WB.pose_neck(r, pitch=0.0, head_pitch=0.0))


def shot_s05b():
    still_w("s05b", (0.9, -3.5, 2.5), (0.2, -0.75, 2.25), 50, 2.8, rock=False)


def shot_s05c():
    still_w("s05c", (3.5, -2.7, 0.5), (1.6, -1.0, 0.15), 40, 4.0, rock=True)


def shot_s19w():
    still_w("s19w", (-6.0, -6.5, 2.2), (-6.0, 0, 1.75), 45, 4.0, rock=False)


def shot_s02b():
    still_c("s02b", "MIST", head_cam(4.3, 0.35, 1.8, tfwd=0.45, lens=50, fstop=2.8))


def shot_s18b():
    def camf(D):
        dg = bpy.context.evaluated_depsgraph_get()
        eo = D["eyes"][1].evaluated_get(dg)
        me = eo.to_mesh(); co = np.array([v.co[:] for v in me.vertices]); eo.to_mesh_clear()
        mw = np.array(D["eyes"][1].matrix_world); co = co @ mw[:3, :3].T + mw[:3, 3]
        e = co.mean(0)
        h, fw = CB.head_frame(D)
        side = np.cross(fw, [0, 0, 1]); side /= np.linalg.norm(side)
        camp = e + side * 0.95 + fw * 0.35 + np.array([0, 0, 0.12])
        return tuple(camp), tuple(e), 60, 2.4
    still_c("s18b", "MIST", camf)


def shot_s19c():
    def camf(D):
        p = CB.body_point(D, 9.5, 10.5); q = CB.body_point(D, 8.0, 8.4)
        return tuple(p + np.array([0.5, -2.6, -0.2])), tuple(q + np.array([0.2, 0, -0.35])), 40, 3.5
    still_c("s19c", "MIST", camf)


def shot_s19ct():
    def camf(D):
        p = CB.body_point(D, 0.5, 2.5)
        return tuple(p + np.array([1.5, -4.5, 0.5])), tuple(p), 40, 4.0
    still_c("s19ct", "MIST", camf)


def shot_l_w_side_gold():
    loop_w("l_w_side_gold", "GOLD", (0.5, -30, 3.0), (0.5, 0, 3.0), 50, (640, 360))


def shot_l_w_back_gold():
    loop_w("l_w_back_gold", "GOLD", (-20, -17, 6.0), (0.5, 0, 3.2), 50, (640, 360))


def shot_l_w_side_volc():
    loop_w("l_w_side_volc", "VOLC", (0.5, -30, 1.0), (0.5, 0, 3.0), 50, (960, 540))


def shot_l_c_side_gold():
    loop_c("l_c_side_gold", "GOLD", (0, -30, 2.0), 50, (800, 360))


def shot_l_c_side_mist():
    loop_c("l_c_side_mist", "MIST", (0, -30, 2.0), 50, (1600, 720))


def shot_l_c_34_storm():
    loop_c("l_c_34_storm", "STORM", (12, -22, -3.5), 45, (1280, 900))


def shot_l_c_up_rain():
    loop_c("l_c_up_rain", "RAIN", (-5, -24, -5.0), 45, (1280, 1100), up=0.45)


def shot_s03():
    s = bl.reset(); info = light(s, "FOSSIL")
    import fossil
    fossil.build()
    cam = bl.camera("cam", (0.9, -3.6, 4.4), (0.2, -0.6, 0.0), lens=28, fstop=6)
    setup_render(s, 1080, 1920, 64, transparent=False, mblur=False)
    render_frames("s03", [1], None, cam)


def shot_t_w():
    def pose(r):
        WB.pose_neck(r, pitch=0.18, head_pitch=0.05, head_yaw=-0.3, jaw=0.42)
    s = bl.reset(); info = light(s, "VOLC")
    D = build_w(); rig = D["rig"]
    w_idle(rig, 0.4, fold=0.3, lift=0.5); pose(rig); key_rig(rig, 1)
    for ob in (D["body"], D["jaw"]):
        ob["glow"] = 0.8
    bl.point("firelight", (5.6, -0.6, 4.6), energy=900, color=(1.0, 0.45, 0.12), radius=0.6)
    cam = bl.camera("cam", (6.9, -3.6, 5.2), (4.25, 0, 4.75), lens=42, fstop=2.8, fit='HORIZONTAL')
    setup_render(s, 1080, 960, 64, mblur=False)
    render_frames("t_w", [1], D["parts"], cam)


def shot_t_c():
    still_c("t_c", "MIST", head_cam(3.4, 0.45, 2.6, tfwd=0.55, lens=40, fstop=2.8), res=(1080, 960), spp=64, jaw=0.2)


if __name__ == "__main__":
    if sys.argv[-1] == "--list":
        print(" ".join(sorted(k[5:] for k in globals() if k.startswith("shot_"))))
    else:
        globals()["shot_" + sys.argv[-1]]()
