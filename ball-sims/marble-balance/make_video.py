#!/usr/bin/env python3
"""One command for a "30 GLASS vs 10 STEEL — WHICH SIDE WINS?" balance Short: glass marbles roll in from the left,
steel balls come down a zigzag on the right, both drop into the baskets of a wooden seesaw, and the heavier side
goes down. The physics is real (a steel ball has 3.14 times the mass of a glass marble of the same size), and the
landing times in settings.py are designed so the lead changes hands and the 10th steel ball decides it.

Rendered on the CPU with ../marble-raytrace-kit: boxtrace path-traces the set once level, then only the window the
seesaw touches for every beam pose the video needs (cached); the compositor swaps that window in per frame and paints
the marbles (steel as polished metal). Text and sound from the channel's kits.

Usage:
  python3 make_video.py                         # -> build/Glass_vs_Steel_Balance.mp4 + build/thumbnail.png
  python3 make_video.py --stills 20,300,630     # check frames first (renders only the poses they need)
  python3 make_video.py --thumb-only
  PREVIEW=1 python3 make_video.py --stills 300  # half-size set and frames
  python3 schedule.py                           # the designed totals and lead changes for the landing times
Environment: EPISODE, WATERMARK, WORKERS, CRF, BUILD_DIR, PREVIEW.
"""
import argparse
import json
import math
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
import scipy.ndimage as ndi
from PIL import Image

import settings as C
import scene as S
import sim as SIM
import timeline as TL
import bake
import balance_comp as BC
import overlays
import audio
import tracers
import compositor as CO
import pipeline as P

BUILD = C.BUILD
POSES = os.path.join(BUILD, "poses")
TLP = os.path.join(BUILD, "timeline.pkl")
WINP = os.path.join(BUILD, "window.json")
log = P.log
W2, H2 = 2 * S.W, 2 * S.H


def full_render(tag, theta):
    sc = os.path.join(BUILD, f"scene_{tag}.txt")
    S.write_scene(sc, W2, H2, *C.SAMPLES, theta=theta)
    t0 = time.time()
    if tracers.render_static(tracers.build("boxtrace", BUILD), sc, os.path.join(BUILD, f"g_{tag}")):
        log(f"set {tag} path-traced in {time.time() - t0:.0f} s")
    return os.path.join(BUILD, f"g_{tag}")


def load(prefix, ext, ch, win=None):
    x0, y0, w, h = win or (0, 0, W2, H2)
    dt = np.uint8 if ext == "I" else np.float32
    a = np.fromfile(f"{prefix}_{ext}.{'u8' if ext == 'I' else 'f32'}", dt)
    return a.reshape(h, w, ch) if ch > 1 else a.reshape(h, w)


def static_sets():
    """Level set (whole image) and the window the moving parts can change, from the two end poses."""
    g0 = full_render("p0", 0.0)
    if not os.path.exists(os.path.join(BUILD, "gt_p0_D.f32")) or os.path.getmtime(
            os.path.join(BUILD, "gt_p0_D.f32")) < os.path.getmtime(g0 + "_D.f32"):
        bake.bake(g0, os.path.join(BUILD, "gt_p0"), 0.0)
        log("textures baked into the level set")
    key = tracers.file_hash(os.path.join(BUILD, "scene_p0.txt"))
    if os.path.exists(WINP) and json.load(open(WINP)).get("key") == key:
        return tuple(json.load(open(WINP))["window"])
    ends = [full_render("pmax", C.THETA_MAX), full_render("pmin", -C.THETA_MAX)]
    base = load(g0, "D", 3) + load(g0, "A", 3) + load(g0, "O", 3)
    z0, i0 = load(g0, "Z", 1), load(g0, "I", 1)
    mask = np.zeros((H2, W2), bool)
    sc = W2 / 1080.0
    for g in ends:
        lit = load(g, "D", 3) + load(g, "A", 3) + load(g, "O", 3)
        # the beam's shadows and bounce light; the per-pixel noise of a few ambient rays that hit it is blurred out
        # (it's blended away at the window's feathered edge instead)
        mask |= np.abs(ndi.gaussian_filter((lit - base).mean(-1), 6 * sc)) > 0.004
        mask |= (load(g, "I", 1) != i0) | (np.abs(load(g, "Z", 1) - z0) > 1e-3)
    ys, xs = np.nonzero(mask)
    m = int(BC.FEATHER * sc) + 24
    x0, x1 = max(0, xs.min() - m) // 2 * 2, min(W2, (xs.max() + m + 2) // 2 * 2)
    y0, y1 = max(0, ys.min() - m) // 2 * 2, min(H2, (ys.max() + m + 2) // 2 * 2)
    win = (int(x0), int(y0), int(x1 - x0), int(y1 - y0))
    json.dump(dict(key=key, window=win), open(WINP, "w"))
    log(f"moving window {win} ({100.0 * win[2] * win[3] / (W2 * H2):.0f}% of the image)")
    return win


def pose_sets(poses, win):
    """The window of the set for each beam pose (degrees), path-traced once and cached."""
    os.makedirs(POSES, exist_ok=True)
    x0, y0, w, h = win
    todo = [q for q in poses if not os.path.exists(os.path.join(POSES, "t_" + BC.pose_tag(q) + "_D.f32"))]
    if todo:
        log(f"{len(todo)} beam poses to path-trace (window {w}x{h})...")
    binary = tracers.build("boxtrace", BUILD)
    t0 = time.time()
    for k, q in enumerate(todo):
        tag = BC.pose_tag(q)
        g = os.path.join(POSES, "g_" + tag)
        if q == 0.0:
            base = os.path.join(BUILD, "g_p0")
            for ext, ch in (("D", 3), ("A", 3), ("O", 3), ("Z", 1), ("N", 3), ("I", 1)):
                a = load(base, ext, ch)[y0:y0 + h, x0:x0 + w]
                a.tofile(f"{g}_{ext}.{'u8' if ext == 'I' else 'f32'}")
        else:
            sc = os.path.join(POSES, f"scene_{tag}.txt")
            S.write_scene(sc, W2, H2, *C.SAMPLES, theta=math.radians(q), crop=win)
            subprocess.run([os.path.abspath(binary), sc, os.path.abspath(g)], check=True, stdout=subprocess.DEVNULL)
        bake.bake(g, os.path.join(POSES, "t_" + tag), math.radians(q), window=win)
        for ext in ("D", "A"):
            os.remove(f"{g}_{ext}.f32")
        if (k + 1) % 5 == 0 or k + 1 == len(todo):
            el = time.time() - t0
            log(f"  poses {k + 1}/{len(todo)} ({el:.0f} s, ~{el / (k + 1) * (len(todo) - k - 1):.0f} s left)")


def compositor():
    CO.configure(S)
    CO.WATERMARK_Y = C.WATERMARK_Y
    with open(TLP, "rb") as fh:
        tl = pickle.load(fh)
    win = tuple(json.load(open(WINP))["window"])
    comp = BC.BalanceCompositor(os.path.join(BUILD, "gt_p0"), POSES, win, tl, watermark=C.WATERMARK or None)
    ov = overlays.Overlay(tl, lambda p: S.project(p)[:2])
    return comp, ov, tl


def frame(comp, ov, tl, f, text=True):
    img = comp.render(f, watermark=text)
    return ov.draw(img, f) if text else img


def render_part(f0, f1, outp):
    comp, ov, tl = compositor()
    tmp = outp[:-4] + ".part.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{S.W}x{S.H}", "-r",
           str(S.FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(C.CRF), "-pix_fmt",
           "yuv420p", "-g", "60", tmp]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    for f in range(f0, f1):
        p.stdin.write(frame(comp, ov, tl, f).tobytes())
        if (f - f0) % 60 == 0:
            print(f"[{f0}-{f1}] frame {f} elapsed {time.time() - t0:.0f}s", file=sys.stderr, flush=True)
    p.stdin.close()
    rc = p.wait()
    if rc == 0:
        os.replace(tmp, outp)
    return rc


def thumb_frame(tl):
    """Default thumbnail: the deciding marble in the air over its basket, just before it lands and tips the beam."""
    return int((float(max(tl["land"])) - 0.05) * C.FPS)


def main():
    os.makedirs(BUILD, exist_ok=True)
    if args.worker:
        sys.exit(render_part(int(args.worker[0]), int(args.worker[1]), args.worker[2]))
    simd = SIM.run(log)
    SIM.check(simd, log)
    tl = TL.build(simd, log)
    with open(TLP, "wb") as fh:
        pickle.dump(tl, fh)
    win = static_sets()
    if args.stills or args.thumb_only:
        want = [int(x) for x in args.stills.split(",") if x]
        tf = args.thumb_frame if args.thumb_frame is not None else thumb_frame(tl)
        pose_sets(sorted({float(tl["theta_q"][f]) for f in want + ([tf] if args.thumb_only else [])}), win)
        comp, ov, tl = compositor()
        for f in want:
            p = os.path.join(BUILD, f"still_{f:04d}.png")
            Image.fromarray(frame(comp, ov, tl, f)).save(p)
            log(p)
        if args.thumb_only:
            img = frame(comp, ov, tl, tf, text=False)
            Image.fromarray(img).save(os.path.join(BUILD, "thumbnail.png"))
            log(f"thumbnail (frame {tf})")
        return
    nfr = min(tl["n_frames"], args.max_frames or tl["n_frames"])
    pose_sets(sorted({float(q) for q in tl["theta_q"][:nfr]}), win)
    wav = os.path.join(BUILD, "sound.wav")
    audio.build(tl, wav, log)
    k = C.WORKERS * 2
    cuts = [round(nfr * i / k) for i in range(k + 1)]
    jobs = [(cuts[i], cuts[i + 1], os.path.join(BUILD, f"part_{i:02d}.mp4")) for i in range(k)]
    log(f"rendering {nfr} frames in {k} parts, {C.WORKERS} at a time...")
    procs = []
    for a, b, outp in jobs:
        while sum(p.poll() is None for p in procs) >= C.WORKERS:
            time.sleep(0.5)
        procs.append(subprocess.Popen([sys.executable, __file__, "--worker", str(a), str(b), outp]))
    if any(p.wait() for p in procs):
        sys.exit("a render worker failed")
    out = os.path.join(BUILD, C.FILE + ".mp4")
    P.mux([j[2] for j in jobs], wav, out)
    log(f"video -> {out}")
    if not args.no_thumb:
        tf = args.thumb_frame if args.thumb_frame is not None else thumb_frame(tl)
        comp, ov, tl = compositor()
        Image.fromarray(frame(comp, ov, tl, tf, text=False)).save(os.path.join(BUILD, "thumbnail.png"))
        log(f"thumbnail (frame {tf})")


if __name__ == "__main__":
    main()
