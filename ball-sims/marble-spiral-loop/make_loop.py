#!/usr/bin/env python3
"""One command for a seamless landscape marble loop, made as a 24/7 livestream background: marbles roll in along a
rail at the top left, spiral down a rainbow helix and leave along a rail to the right, forever. The last frame leads
straight into the first, so `ffmpeg -stream_loop -1` can repeat it without a visible seam.

Usage:
  python3 make_loop.py                     # -> build/marble_spiral_loop.mp4 (1920x1080, 30 fps, no audio)
  python3 make_loop.py --stills 0,360      # PNG stills only (build/still_0000.png ...)
Environment: WORKERS (2), WATERMARK (default none), VIDEO_BITRATE (6M), BUILD_DIR.

Steps: track mesh + static set path-traced once (cached by scene + mesh hash) -> periodic marble paths and segment
glows -> marble lighting table from the tracer's env mode -> frames in WORKERS processes -> one H.264 encode at
YouTube live settings (CBR-style VIDEO_BITRATE, keyframe every 2 s, no scene-cut keyframes).
"""
import argparse
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.join(HERE, "..", "marble-raytrace-kit")
sys.path.insert(0, HERE)
sys.path.insert(0, KIT)

# ===================================================================== SETTINGS (shipped values)
BUILD = os.environ.get("BUILD_DIR", os.path.join(HERE, "build"))
WATERMARK = os.environ.get("WATERMARK", "")
WORKERS = int(os.environ.get("WORKERS", "2"))
VIDEO_BITRATE = os.environ.get("VIDEO_BITRATE", "6M")
PART_CRF = 10                   # near-lossless intermediate parts, re-encoded once at the end
KEYINT = 60                     # 2 s at 30 fps: YouTube live wants keyframes every 2 s (never over 4)
STATIC_SAMPLES = (49, 64)       # key-light / ambient samples per pixel of the static path trace
FLASH = (0.45, 0.30)            # segment flash when a marble rolls onto it: amplitude, decay (s)
HOLD_LEVEL = 0.30               # segment stays lit at this level while a marble rolls over it
OUT_NAME = "marble_spiral_loop.mp4"
# ================================================================= END SETTINGS

ap = argparse.ArgumentParser()
ap.add_argument("--stills", default="")
ap.add_argument("--worker", nargs=3, metavar=("F0", "F1", "OUT"))
args = ap.parse_args()

import numpy as np
from PIL import Image

import scene as S
import timeline as T
import tracers
import compositor as C
import pipeline as P

GPREFIX = os.path.join(BUILD, "g")
SCENE_TXT = os.path.join(BUILD, "scene.txt")
MESH = os.path.join(BUILD, "mesh.bin")
log = P.log


def static_render():
    os.makedirs(BUILD, exist_ok=True)
    S.build_mesh().write(MESH)
    S.write_scene(SCENE_TXT, os.path.basename(MESH), 2 * S.W, 2 * S.H, *STATIC_SAMPLES)
    binary = tracers.build("meshtrace", BUILD)
    log("static set: path tracing (cached after the first run)...")
    if tracers.render_static(binary, SCENE_TXT, GPREFIX, GPREFIX + ".log", deps=[MESH]):
        log("static set rendered")
    return binary


def env_table(binary, pos, vis):
    """Lighting of every distinct marble position (key-light visibility, ambient cube, gap, shadow reach)."""
    nf, nm = vis.shape
    keys, pts = {}, []
    idx = np.full((nf, nm), -1, np.int64)
    for f in range(nf):
        for j in np.nonzero(vis[f])[0]:
            p = pos[f, j]
            if p[0] < -45:
                continue
            k = tuple(np.round(p, 3))
            if k not in keys:
                keys[k] = len(pts)
                pts.append(p)
            idx[f, j] = keys[k]
    log(f"marble lighting: {len(pts)} positions...")
    res = tracers.env_query(binary, SCENE_TXT, np.array(pts, np.float32), BUILD)
    env = np.full((nf, nm, 21), np.nan, np.float32)
    ok = idx >= 0
    env[ok] = res[idx[ok]]
    np.savez_compressed(os.path.join(BUILD, "env.npz"), env=env)


def compositor():
    C.configure(S)
    tl = json.load(open(os.path.join(BUILD, "timeline.json")))
    m = np.load(os.path.join(BUILD, "marbles.npz"))
    envtab = np.load(os.path.join(BUILD, "env.npz"))["env"]
    glows = []
    for g in tl["glows"]:
        k = g["seg"]
        glows.append(dict(oid=S.OID_SEG0 + k, col=S.srgb2lin(S.seg_srgb(k)),
                          events=[(t, *FLASH) for t in g["events"]], hold=[tuple(h) for h in g["hold"]]))
    seg_th = [S.seg_bounds(k) for k in range(S.N_SEG)]
    turns = int(S.TH_E / (2 * math.pi)) + 3

    def env_fn(f, mi, c):
        e = envtab[f, mi]
        if not np.isfinite(e[0]):
            return None
        return float(e[0]), e[1:19].reshape(6, 3).astype(np.float64), float(e[19]), float(e[20])

    def spill(k, c):  # nearest point of segment k on the turn of the helix the marble is on
        ta, tb = seg_th[k]
        th0 = math.atan2(c[2], c[0]) % (2 * math.pi)
        best = None
        for nn in range(-1, turns):
            thc = th0 + 2 * math.pi * nn
            if ta - 1.0 <= thc <= tb + 1.0:
                if best is None or abs(S.y_top(thc) + 1 - c[1]) < abs(S.y_top(best) + 1 - c[1]):
                    best = thc
        if best is None:
            return None
        thq = min(max(best, ta), tb)
        return np.array([S.RC * math.cos(thq), S.y_top(thq), S.RC * math.sin(thq)])

    return C.Compositor(GPREFIX, m["pos"], m["vis"], tl["colors"], glows, titles=[],
                        watermark=WATERMARK or None, env_fn=env_fn, spill_fn=spill, hold_level=HOLD_LEVEL), tl


def encode(parts, out):
    lst = os.path.join(BUILD, "parts.txt")
    with open(lst, "w") as fh:
        fh.writelines(f"file '{os.path.abspath(p)}'\n" for p in parts)
    rate = VIDEO_BITRATE
    bufsize = f"{2 * int(rate.rstrip('M'))}M" if rate.endswith("M") else rate
    tmp = out[:-4] + ".part.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-an",
                    "-c:v", "libx264", "-preset", "slow", "-b:v", rate, "-maxrate", rate, "-bufsize", bufsize,
                    "-g", str(KEYINT), "-keyint_min", str(KEYINT), "-sc_threshold", "0", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, out)
    os.remove(lst)


def main():
    if args.worker:
        comp, _ = compositor()
        sys.exit(C.render_video(comp, int(args.worker[0]), int(args.worker[1]), args.worker[2], PART_CRF))
    binary = static_render()
    tl, pos, vis = T.build(BUILD)
    log(f"timeline: {tl['n_frames']} frames ({T.LOOP_S:.1f} s loop), {len(T.GAPS)} marbles per loop, "
        f"up to {int(vis.sum(1).max())} on screen; seam error {T.loop_check(pos, vis):.2e} units")
    env_table(binary, pos, vis)
    if args.stills:
        comp, _ = compositor()
        for fs in [s for s in args.stills.split(",") if s]:
            p = os.path.join(BUILD, f"still_{int(fs):04d}.png")
            Image.fromarray(comp.render(int(fs))).save(p)
            log(p)
        return
    parts = P.run_workers([sys.executable, __file__], tl["n_frames"], WORKERS, BUILD, P.frame_costs(pos, vis))
    out = os.path.join(BUILD, OUT_NAME)
    encode(parts, out)
    log(f"loop -> {out}")


if __name__ == "__main__":
    main()
