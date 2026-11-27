#!/usr/bin/env python3
"""One command for a "Last One Spinning Wins" Short: eight marbles spin around a turned wooden dish, bounce off pegs
and each other, and drop through the hole in the middle one by one; the last one still spinning wins. Real physics
(sim.py) picks the order; the video fast-forwards quiet stretches, slows down and cuts to a close-up for the last
knock-out. Rendered on the CPU with ../marble-raytrace-kit (one static set per camera), text and sound from the
channel's kits.

Usage:
  python3 make_video.py                         # -> build/Last_One_Spinning_Wins.mp4 + build/thumbnail.png
  python3 make_video.py --stills 30,300,640
  python3 make_video.py --thumb-only
  PREVIEW=1 python3 make_video.py --stills 300  # quarter-size sets and frames
  python3 sim.py --search 1-800                 # rank races for a new episode, then SEED=<n>
Environment: SEED (default settings.SHIPPED_SEED), EPISODE, WATERMARK, WORKERS, CRF, BUILD_DIR, PREVIEW.
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
ap.add_argument("--static", action="store_true", help="(internal) trace and bake this process's camera")
ap.add_argument("--frames", default="", help="(internal) render these frames to PNG with this process's camera")
ap.add_argument("--worker", nargs=3, metavar=("F0", "F1", "OUT"))
args = ap.parse_args()

import numpy as np
from PIL import Image

import settings as C
import scene as S
import dish
import bake
import sim as SIM
import timeline as TL
import overlays
import audio
import tracers
import compositor as CO
import pipeline as P

BUILD = C.BUILD
CAM = C.CAM
MESH_BIN = os.path.join(BUILD, "mesh.bin")
TLP = os.path.join(BUILD, "timeline.pkl")
log = P.log


def gp(cam):
    return os.path.join(BUILD, f"g_{cam}"), os.path.join(BUILD, f"gt_{cam}"), os.path.join(BUILD, f"scene_{cam}.txt")


def static_render():
    g, t, sc = gp(CAM)
    S.write_scene(sc, os.path.basename(MESH_BIN), 2 * S.W, 2 * S.H, *C.STATIC_SAMPLES)
    binary = tracers.build("meshtrace", BUILD)
    log(f"static set ({CAM} camera): path tracing (cached after the first run)...")
    fresh = tracers.render_static(binary, sc, g, g + ".log", deps=[MESH_BIN])
    if fresh or not os.path.exists(t + "_D.f32") or os.path.getmtime(t + "_D.f32") < os.path.getmtime(
            os.path.join(HERE, "bake.py")):
        bake.bake(g, t, log)


def env_table():
    out = os.path.join(BUILD, "env.npz")
    _, _, sc = gp("main")
    gx = np.arange(-C.RD, C.RD + 0.01, 0.5)
    X, Z = np.meshgrid(gx, gx, indexing="ij")
    r = np.hypot(X, Z)
    rc = np.clip(r, C.RH, C.RD - C.R)
    h = SIM.floor_y(rc)
    s = C.S0 + C.S1 * rc + 2 * C.DEP * rc / C.SIG ** 2 * np.exp(-(rc / C.SIG) ** 2)
    Y = h + C.R * np.sqrt(1 + s * s)
    pts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1).astype(np.float32)
    key = tracers.file_hash(sc, MESH_BIN)
    if os.path.exists(out) and str(np.load(out)["key"]) == key:
        return
    log(f"marble lighting: {len(pts)} positions...")
    res = tracers.env_query(tracers.build("meshtrace", BUILD), sc, pts, BUILD)
    np.savez(out, key=key, gx=gx, env=res.reshape(len(gx), len(gx), 21))


def make_env_fn():
    d = np.load(os.path.join(BUILD, "env.npz"))
    gx, tab = d["gx"], d["env"]

    def env_fn(f, mi, c):
        fx = np.clip((c[0] - gx[0]) / (gx[1] - gx[0]), 0, len(gx) - 1.001)
        fz = np.clip((c[2] - gx[0]) / (gx[1] - gx[0]), 0, len(gx) - 1.001)
        i, k = int(fx), int(fz)
        a, b = fx - i, fz - k
        e = (tab[i, k] * (1 - a) * (1 - b) + tab[i + 1, k] * a * (1 - b) + tab[i, k + 1] * (1 - a) * b +
             tab[i + 1, k + 1] * a * b)
        return float(e[0]), e[1:19].reshape(6, 3).astype(np.float64), float(e[19]), float(e[20])

    return env_fn


def glow_list(tl):
    """Light-ups: a peg flashes in the colour of the marble that hit it (one glow element per peg and colour), and
    the hole glows in the colour of each marble it swallows."""
    out = []
    a, dec = C.PEG_FLASH
    for k in range(len(C.PEGS)):
        for i, col in enumerate(tl["colors"]):
            evs = [(t, a * min(1.0, v[0] / 22.0) ** 0.7, dec) for t, kind, v in tl["events"]
                   if kind == "peg" and v[3] == k and v[4] == i]
            if evs:
                out.append(dict(oid=dish.OID_PEGS[k], col=S.srgb2lin(col), events=evs))
    a, dec = C.HOLE_FLASH
    for i, col in enumerate(tl["colors"]):
        evs = [(t, a, dec) for t, kind, v in tl["events"] if kind == "out" and v == tl["names"][i]]
        if evs:
            out.append(dict(oid=dish.OID_HOLE, col=S.srgb2lin(col), events=evs))
    return out


def compositor(watermark):
    CO.configure(S)
    CO.WATERMARK_Y = C.WATERMARK_Y
    with open(TLP, "rb") as fh:
        tl = pickle.load(fh)
    _, t, _ = gp(CAM)
    comp = CO.Compositor(t, tl["pos"], tl["vis"], tl["colors"], glow_list(tl), titles=[],
                         watermark=watermark or None, env_fn=make_env_fn())
    ov = overlays.Overlay(tl, lambda p: S.project(p)[:2])
    return comp, ov, tl


def frame(comp, ov, tl, f, text=True):
    img = comp.render(f, title=False, watermark=text)
    return ov.draw(img, f, tl["pos"]) if text else img


def render_part(f0, f1, outp):
    comp, ov, tl = compositor(C.WATERMARK)
    tmp = outp[:-4] + ".part.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{S.W}x{S.H}", "-r",
           str(S.FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(C.CRF), "-pix_fmt",
           "yuv420p", "-g", "60", tmp]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    for f in range(f0, f1):
        p.stdin.write(frame(comp, ov, tl, f).tobytes())
        if (f - f0) % 60 == 0:
            print(f"[{CAM} {f0}-{f1}] frame {f} elapsed {time.time() - t0:.0f}s", file=sys.stderr, flush=True)
    p.stdin.close()
    rc = p.wait()
    if rc == 0:
        os.replace(tmp, outp)
    return rc


def thumb_frame(tl):
    """Default thumbnail: the first marble teetering on the edge of the hole, everyone still in."""
    return int(min(t for t, k, _ in tl["events"] if k == "out") * C.FPS)


def sub(cam, *extra):
    env = dict(os.environ, SPIN_CAM=cam)
    return subprocess.Popen([sys.executable, __file__, *extra], env=env)


def main():
    os.makedirs(BUILD, exist_ok=True)
    if args.worker:
        sys.exit(render_part(int(args.worker[0]), int(args.worker[1]), args.worker[2]))
    if args.static:
        static_render()
        return
    if args.frames:
        comp, ov, tl = compositor(C.WATERMARK)
        for fs in args.frames.split(","):
            f, kind = fs.split(":")
            f = int(f)
            if kind == "thumb":
                img = frame(comp, ov, tl, f, text=False)
                Image.fromarray(img).save(os.path.join(BUILD, "thumbnail.png"))
                Image.fromarray(img).save(os.path.join(BUILD, "thumbnail.jpg"), quality=92)
                log(f"thumbnail (frame {f}, {CAM} camera)")
            else:
                p = os.path.join(BUILD, f"still_{f:04d}.png")
                Image.fromarray(frame(comp, ov, tl, f)).save(p)
                log(p)
        return
    dish.build_mesh(log).write(MESH_BIN)
    for cam in ("main", "close"):
        if sub(cam, "--static").wait():
            sys.exit("static render failed")
    seed = C.SEED or C.SHIPPED_SEED
    simd = SIM.run(seed)
    tl = TL.build(simd, log)
    with open(TLP, "wb") as fh:
        pickle.dump(tl, fh)
    env_table()
    cam_of = tl["cam"]
    if args.stills or args.thumb_only:
        want = [int(x) for x in args.stills.split(",") if x]
        for cam in ("main", "close"):
            fr = [f"{f}:still" for f in want if cam_of[f] == cam]
            tf = args.thumb_frame if args.thumb_frame is not None else thumb_frame(tl)
            if args.thumb_only and cam == cam_of[tf]:
                fr.append(f"{tf}:thumb")
            if fr and sub(cam, "--frames", ",".join(fr)).wait():
                sys.exit("still render failed")
        return
    wav = os.path.join(BUILD, "sound.wav")
    audio.build(tl, wav, log)
    nfr = min(tl["n_frames"], args.max_frames or tl["n_frames"])
    # runs of frames from one camera, cut into chunks that WORKERS processes render at a time
    jobs, f = [], 0
    chunk = max(45, -(-nfr // (2 * C.WORKERS)))
    while f < nfr:
        g = f
        while g < nfr and cam_of[g] == cam_of[f]:
            g += 1
        k = max(1, round((g - f) / chunk))
        cuts = [f + round((g - f) * i / k) for i in range(k + 1)]
        for i in range(k):
            jobs.append((cam_of[f], cuts[i], cuts[i + 1], os.path.join(BUILD, f"part_{len(jobs):02d}_{cam_of[f]}.mp4")))
        f = g
    log(f"rendering {nfr} frames in {len(jobs)} parts, {C.WORKERS} at a time...")
    procs = []
    for cam, a, b, outp in jobs:
        while sum(p.poll() is None for p in procs) >= C.WORKERS:
            time.sleep(0.5)
        procs.append(sub(cam, "--worker", str(a), str(b), outp))
    if any(p.wait() for p in procs):
        sys.exit("a render worker failed")
    parts = [j[3] for j in jobs]
    out = os.path.join(BUILD, C.FILE + ".mp4")
    P.mux(parts, wav, out)
    log(f"video -> {out}")
    if not args.no_thumb:
        f = args.thumb_frame if args.thumb_frame is not None else thumb_frame(tl)
        sub(cam_of[f], "--frames", f"{f}:thumb").wait()


if __name__ == "__main__":
    main()
