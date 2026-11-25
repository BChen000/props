"""dragons / demo.py: render either dragon on its own, with the same scenes the episode "The Two Dragons" used.

  python demo.py western    Western dragon head close-up (the episode's s02a still), 720x1280, 48 samples, ~30 s
  python demo.py chinese    Chinese dragon head close-up (s02b), 720x1280, 48 samples
  python demo.py perched    Western dragon on the volcanic perch rock, wings half open, 720x1280
  python demo.py flying     Western dragon wingbeat loop, 28 frames at 640x360 (l_w_side_gold), loops seamlessly
  python demo.py serpent    Chinese dragon swimming through the air, 48-frame loop at 1600x720 (l_c_side_mist)
  python demo.py fossil     the common-ancestor skeleton in the rock (s03), 1080x1920, 64 samples
  python demo.py all

Output: out/renders/<name>/####.png (RGBA, transparent film except fossil) plus meta.json (sun position; for
western also the mouth and mouth_fwd points that ../wildlore-2d-comp's fire_for() aims the fire with).
PREVIEW=1 renders first/middle/last frames at 34 % size and 4 samples into out/renders/prev_<name>/.
The first run also builds the meshes into cache/ (about 1-2 minutes).
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from scene import *
import fossil


def mouth_meta(D):
    m = D["mouth"].matrix_world
    return {"mouth": screen(m.translation), "mouth_fwd": screen(m @ Vector((1.0, 0, -0.2)))}


def western():
    still_w("western", (6.6, -4.4, 4.85), (4.15, 0, 4.45), 50, 2.8, rock=False,
            pose=lambda r: WB.pose_neck(r, pitch=0.12, head_pitch=0.0, head_yaw=-0.1), meta_extra=mouth_meta)


def chinese():
    still_c("chinese", "MIST", head_cam(4.3, 0.35, 1.8, tfwd=0.45, lens=50, fstop=2.8))


def perched():
    still_w("perched", (10.0, -9.0, 1.6), (0.8, 0, 3.4), 30, 5.6, rock=True,
            pose=lambda r: (w_idle(r, 0.4, fold=0.0, lift=0.55), WB.pose_neck(r, pitch=0.18, head_yaw=0.1)))


def flying():
    loop_w("flying", "GOLD", (0.5, -30, 3.0), (0.5, 0, 3.0), 50, (640, 360))


def serpent():
    loop_c("serpent", "MIST", (0, -30, 2.0), 50, (1600, 720))


def fossil_still():
    s = bl.reset(); light(s, "FOSSIL")
    fossil.build()
    cam = bl.camera("cam", (0.9, -3.6, 4.4), (0.2, -0.6, 0.0), lens=28, fstop=6)
    setup_render(s, 1080, 1920, 64, transparent=False, mblur=False)
    render_frames("fossil", [1], None, cam)


MODES = {"western": western, "chinese": chinese, "perched": perched, "flying": flying, "serpent": serpent, "fossil": fossil_still}

if __name__ == "__main__":
    want = sys.argv[1] if len(sys.argv) > 1 else "western"
    for name in (MODES if want == "all" else [want]):
        MODES[name]()
        print("done", name, "->", os.path.join(OUT, ("prev_" if PREVIEW else "") + name))
