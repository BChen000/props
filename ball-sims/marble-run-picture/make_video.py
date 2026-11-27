#!/usr/bin/env python3
"""One command for a wooden marble run Short that ends in a picture: marbles roll off a rail, wind down a staircase
of wooden blocks (U-turns, a wave piece, a meander, hidden drops through holes) and out of the front face onto a felt
mat, where each new marble pushes the growing picture outward. Rendered on the CPU with ../marble-raytrace-kit.

Usage:
  python3 make_video.py                         # -> build/Marble_Run_Heart.mp4 + build/thumbnail.png
  python3 make_video.py --stills 90,360,690      # PNG stills only (build/still_0090.png ...)
  python3 make_video.py --thumb-only
  PREVIEW=1 python3 make_video.py --stills 300   # quarter-size set and frames, for quick checks
Options: --thumb-frame N (default: the finished picture), --no-thumb, --max-frames N (a short test video).
Environment: EPISODE (episodes/<name>.py overrides settings), WATERMARK, WORKERS, CRF, BUILD_DIR, PREVIEW.

Steps: set mesh (marching cubes, ~3 s) -> path-trace the static set once (cached by scene + mesh hash, ~7 min at
full size) -> bake wood grain, floor boards and felt into it -> timeline + picture physics -> marble lighting
tables from the tracer's env mode -> soundtrack -> frames in WORKERS processes -> concat -> AAC at -13 LUFS ->
thumbnail.
"""
import argparse
import json
import os
import subprocess
import sys

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
import timeline
import audio
import tracers
import compositor as CO
import pipeline as P

BUILD = C.BUILD
GPREFIX = os.path.join(BUILD, "g")
TPREFIX = os.path.join(BUILD, "gt")
SCENE_TXT = os.path.join(BUILD, "scene.txt")
MESH_BIN = os.path.join(BUILD, "mesh.bin")
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


def env_tables(binary):
    """Marble lighting looked up by position: along the run (by arc length) and on a grid over the mat."""
    out = os.path.join(BUILD, "env.npz")
    pts, s, tags = LY.marble_path()
    s_tab = np.arange(-60.0, s[-1] + 0.25, 0.25)
    p_run = np.where((s_tab < 0)[:, None], LY.rail_point(np.minimum(s_tab, 0)),
                     np.stack([np.interp(np.maximum(s_tab, 0), s, pts[:, k]) for k in range(3)], 1))
    gx = np.arange(LY.EXIT[0] - C.MAT_HALF_W, LY.EXIT[0] + C.MAT_HALF_W + 0.01, 0.5)
    gz = np.arange(-1.0, C.MAT_DEPTH + 0.01, 0.5)
    X, Z = np.meshgrid(gx, gz, indexing="ij")
    p_mat = np.stack([X.ravel(), np.full(X.size, LY.MAT_Y), Z.ravel()], 1)
    allp = np.concatenate([p_run, p_mat]).astype(np.float32)
    key = tracers.file_hash(SCENE_TXT, MESH_BIN) + str(allp.sum())
    if os.path.exists(out):
        d = np.load(out)
        if str(d["key"]) == key:
            return
    log(f"marble lighting: {len(allp)} positions...")
    res = tracers.env_query(binary, SCENE_TXT, allp, BUILD)
    np.savez(out, key=key, s_tab=s_tab, run=res[:len(p_run)], gx=gx, gz=gz,
             mat=res[len(p_run):].reshape(len(gx), len(gz), 21))


def make_env_fn():
    d = np.load(os.path.join(BUILD, "env.npz"))
    s_tab, run, gx, gz, mat = d["s_tab"], d["run"], d["gx"], d["gz"], d["mat"]
    m = np.load(os.path.join(BUILD, "marbles.npz"))
    sarr, onmat = m["s"], m["mat"]

    def env_fn(f, mi, c):
        if onmat[f, mi]:
            fx = np.clip((c[0] - gx[0]) / (gx[1] - gx[0]), 0, len(gx) - 1.001)
            fz = np.clip((c[2] - gz[0]) / (gz[1] - gz[0]), 0, len(gz) - 1.001)
            i, k = int(fx), int(fz)
            a, b = fx - i, fz - k
            e = (mat[i, k] * (1 - a) * (1 - b) + mat[i + 1, k] * a * (1 - b) + mat[i, k + 1] * (1 - a) * b +
                 mat[i + 1, k + 1] * a * b)
        else:
            sv = sarr[f, mi]
            if not np.isfinite(sv):
                return None
            fs = np.clip((sv - s_tab[0]) / (s_tab[1] - s_tab[0]), 0, len(s_tab) - 1.001)
            i = int(fs)
            a = fs - i
            e = run[i] * (1 - a) + run[i + 1] * a
        return float(e[0]), e[1:19].reshape(6, 3).astype(np.float64), float(e[19]), float(e[20])

    return env_fn


def compositor(watermark):
    CO.configure(S)
    CO.WATERMARK_Y = C.WATERMARK_Y
    tl = json.load(open(os.path.join(BUILD, "timeline.json")))
    m = np.load(os.path.join(BUILD, "marbles.npz"))
    pos = np.nan_to_num(m["pos"].astype(np.float64), nan=-100.0)
    return CO.Compositor(TPREFIX, pos, m["vis"], tl["colors"], [], titles=[], watermark=watermark or None,
                         env_fn=make_env_fn()), tl, m


def render_part(comp, f0, f1, outp):
    """Like compositor.render_video, but a frame whose marbles haven't moved is reused."""
    import time
    tmp = outp[:-4] + ".part.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{S.W}x{S.H}", "-r",
           str(S.FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(C.CRF), "-pix_fmt",
           "yuv420p", "-g", "60", tmp]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    prev_key, prev_img = None, None
    for f in range(f0, f1):
        key = (comp.pos[f].round(4).tobytes(), comp.vis[f].tobytes())
        img = prev_img if key == prev_key else comp.render(f)
        prev_key, prev_img = key, img
        p.stdin.write(img.tobytes())
        if (f - f0) % 30 == 0:
            print(f"[{f0}-{f1}] frame {f} elapsed {time.time() - t0:.0f}s", file=sys.stderr, flush=True)
    p.stdin.close()
    rc = p.wait()
    if rc == 0:
        os.replace(tmp, outp)
    return rc


def thumbnail(tl):
    comp, _, _ = compositor(None)
    f = args.thumb_frame if args.thumb_frame is not None else (C.THUMB_FRAME or tl["n_frames"] - 1)
    img = comp.render(f, title=False, watermark=False)
    out = os.path.join(BUILD, "thumbnail.png")
    Image.fromarray(img).save(out)
    Image.fromarray(img).save(os.path.join(BUILD, "thumbnail.jpg"), quality=92)
    log(f"thumbnail (frame {f}) -> {out}")


def main():
    os.makedirs(BUILD, exist_ok=True)
    if args.worker:
        comp, _, _ = compositor(C.WATERMARK)
        sys.exit(render_part(comp, int(args.worker[0]), int(args.worker[1]), args.worker[2]))
    binary = static_render()
    tl = timeline.build(BUILD, log)
    env_tables(binary)
    if args.stills or args.thumb_only:
        comp, _, _ = compositor(C.WATERMARK)
        for fs in [x for x in args.stills.split(",") if x]:
            p = os.path.join(BUILD, f"still_{int(fs):04d}.png")
            Image.fromarray(comp.render(int(fs))).save(p)
            log(p)
        if args.thumb_only:
            thumbnail(tl)
        return
    m = np.load(os.path.join(BUILD, "marbles.npz"))
    wav = os.path.join(BUILD, "sound.wav")
    audio.build(tl, m, wav, log)
    nfr = min(tl["n_frames"], args.max_frames or tl["n_frames"])
    parts = P.run_workers([sys.executable, __file__], nfr, C.WORKERS, BUILD,
                          P.frame_costs(m["pos"][:nfr], m["vis"][:nfr]))
    out = os.path.join(BUILD, C.FILE + ".mp4")
    P.mux(parts, wav, out)
    log(f"video -> {out}")
    if not args.no_thumb:
        thumbnail(tl)


if __name__ == "__main__":
    main()
