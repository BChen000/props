#!/usr/bin/env python3
"""One command for a 3D marble hide-and-seek Short: six marbles hide around a wooden playground while a googly-eyed
seeker counts, then it checks the hiding places one by one; the one it never finds wins. Rendered on the CPU with
../marble-raytrace-kit (no Blender, no GPU), with text and sound from the channel's kits.

Usage:
  python3 make_video.py                          # -> build/Marble_Hide_and_Seek.mp4 + build/thumbnail.png
  python3 make_video.py --stills 150,250,420     # PNG stills only (build/still_0150.png ...)
  python3 make_video.py --thumb-only
  PREVIEW=1 python3 make_video.py --stills 300   # quarter-size set and frames, for quick checks
Options: --thumb-frame N (default: the seeker opening its eyes), --no-thumb, --max-frames N.
Environment: EPISODE (episodes/<name>.py overrides settings), WATERMARK, WORKERS, CRF, BUILD_DIR, PREVIEW.
"""
import argparse
import os
import pickle
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.join(HERE, "..", "marble-raytrace-kit")
sys.path.insert(0, HERE)
sys.path.insert(0, KIT)

ap = argparse.ArgumentParser()
ap.add_argument("--stills", default="")
ap.add_argument("--thumb-only", action="store_true")
ap.add_argument("--no-thumb", action="store_true")
ap.add_argument("--thumb-frame", type=int, default=None)
ap.add_argument("--max-frames", type=int, default=None)
ap.add_argument("--worker", nargs=3, metavar=("F0", "F1", "OUT"))
args = ap.parse_args()

import numpy as np
from PIL import Image

import settings as C
import scene as S
import layout as LY
import mesh as MESH
import bake
import story as ST
import eyes
import overlays
import audio
import tracers
import compositor as CO
import pipeline as P

BUILD = C.BUILD
GPREFIX = os.path.join(BUILD, "g")
TPREFIX = os.path.join(BUILD, "gt")
SCENE_TXT = os.path.join(BUILD, "scene.txt")
MESH_BIN = os.path.join(BUILD, "mesh.bin")
STORY = os.path.join(BUILD, "story.pkl")
log = P.log


def static_render():
    MESH.build_mesh(log).write(MESH_BIN)
    S.write_scene(SCENE_TXT, os.path.basename(MESH_BIN), 2 * S.W, 2 * S.H, *C.STATIC_SAMPLES)
    binary = tracers.build("meshtrace", BUILD)
    log("static set: path tracing (cached after the first run)...")
    fresh = tracers.render_static(binary, SCENE_TXT, GPREFIX, GPREFIX + ".log", deps=[MESH_BIN])
    if fresh or not os.path.exists(TPREFIX + "_D.f32") or \
            os.path.getmtime(TPREFIX + "_D.f32") < os.path.getmtime(os.path.join(HERE, "bake.py")):
        bake.bake(GPREFIX, TPREFIX, log)
    return binary


def env_table(binary):
    out = os.path.join(BUILD, "env.npz")
    x0, x1, z0, z1 = C.MAT
    gx = np.arange(x0, x1 + 0.01, 0.5)
    gz = np.arange(z0, z1 + 0.01, 0.5)
    X, Z = np.meshgrid(gx, gz, indexing="ij")
    pts = np.stack([X.ravel(), np.full(X.size, LY.MAT_Y), Z.ravel()], 1).astype(np.float32)
    key = tracers.file_hash(SCENE_TXT, MESH_BIN)
    if os.path.exists(out) and str(np.load(out)["key"]) == key:
        return
    log(f"marble lighting: {len(pts)} positions...")
    res = tracers.env_query(binary, SCENE_TXT, pts, BUILD)
    np.savez(out, key=key, gx=gx, gz=gz, env=res.reshape(len(gx), len(gz), 21))


def make_env_fn():
    d = np.load(os.path.join(BUILD, "env.npz"))
    gx, gz, tab = d["gx"], d["gz"], d["env"]

    def env_fn(f, mi, c):
        fx = np.clip((c[0] - gx[0]) / (gx[1] - gx[0]), 0, len(gx) - 1.001)
        fz = np.clip((c[2] - gz[0]) / (gz[1] - gz[0]), 0, len(gz) - 1.001)
        i, k = int(fx), int(fz)
        a, b = fx - i, fz - k
        e = (tab[i, k] * (1 - a) * (1 - b) + tab[i + 1, k] * a * (1 - b) + tab[i, k + 1] * (1 - a) * b +
             tab[i + 1, k + 1] * a * b)
        vis = float(e[0])
        lift = c[1] - LY.MAT_Y                       # hopping marbles see more sky and cast longer shadows
        if lift > 0.05:
            vis = min(1.0, vis + 0.25 * lift)
        return vis, e[1:19].reshape(6, 3).astype(np.float64), float(e[19]) + lift, float(e[20]) + lift

    return env_fn


def load_story():
    with open(STORY, "rb") as fh:
        return pickle.load(fh)


def compositor(watermark):
    CO.configure(S)
    CO.WATERMARK_Y = C.WATERMARK_Y
    st = load_story()
    vis = np.ones(st["pos"].shape[:2], bool)
    comp = eyes.EyeCompositor(TPREFIX, st["pos"], vis, st["colors"], [], titles=[], watermark=watermark or None,
                              env_fn=make_env_fn(), eyes=st["eyes"], eye_marble=0)
    ov = overlays.Overlay(st, lambda p: S.project(p)[:2])
    return comp, ov, st


def frame(comp, ov, st, f, text=True):
    img = comp.render(f, title=False, watermark=text)
    return ov.draw(img, f, st["pos"]) if text else img


def render_part(f0, f1, outp):
    comp, ov, st = compositor(C.WATERMARK)
    tmp = outp[:-4] + ".part.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{S.W}x{S.H}", "-r",
           str(S.FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(C.CRF), "-pix_fmt",
           "yuv420p", "-g", "60", tmp]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    for f in range(f0, f1):
        p.stdin.write(frame(comp, ov, st, f).tobytes())
        if (f - f0) % 60 == 0:
            print(f"[{f0}-{f1}] frame {f} elapsed {time.time() - t0:.0f}s", file=sys.stderr, flush=True)
    p.stdin.close()
    rc = p.wait()
    if rc == 0:
        os.replace(tmp, outp)
    return rc


def thumbnail(st):
    comp, ov, _ = compositor(None)
    t_ready = next(t for t, k, _ in st["events"] if k == "ready")
    f = args.thumb_frame if args.thumb_frame is not None else int((t_ready + 0.7) * C.FPS)
    img = frame(comp, ov, st, f, text=False)
    out = os.path.join(BUILD, "thumbnail.png")
    Image.fromarray(img).save(out)
    Image.fromarray(img).save(os.path.join(BUILD, "thumbnail.jpg"), quality=92)
    log(f"thumbnail (frame {f}) -> {out}")


def main():
    os.makedirs(BUILD, exist_ok=True)
    if args.worker:
        sys.exit(render_part(int(args.worker[0]), int(args.worker[1]), args.worker[2]))
    binary = static_render()
    st = ST.build(log)
    with open(STORY, "wb") as fh:
        pickle.dump(st, fh)
    log(f"story: {st['n_frames']} frames ({st['n_frames'] / C.FPS:.2f} s), found order {st['found_order']}, "
        f"winner {C.WINNER}")
    env_table(binary)
    if args.stills or args.thumb_only:
        comp, ov, _ = compositor(C.WATERMARK)
        for fs in [x for x in args.stills.split(",") if x]:
            p = os.path.join(BUILD, f"still_{int(fs):04d}.png")
            Image.fromarray(frame(comp, ov, st, int(fs))).save(p)
            log(p)
        if args.thumb_only:
            thumbnail(st)
        return
    wav = os.path.join(BUILD, "sound.wav")
    audio.build(st, wav, log)
    nfr = min(st["n_frames"], args.max_frames or st["n_frames"])
    parts = P.run_workers([sys.executable, __file__], nfr, C.WORKERS, BUILD)
    out = os.path.join(BUILD, C.FILE + ".mp4")
    P.mux(parts, wav, out)
    log(f"video -> {out}")
    if not args.no_thumb:
        thumbnail(st)


if __name__ == "__main__":
    main()
