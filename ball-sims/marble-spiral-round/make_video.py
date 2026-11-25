#!/usr/bin/env python3
"""One command for a spiral-round marble music Short: marbles roll down a rainbow helix whose segments each play one
note, so a marble plays the song and marbles two bars apart sing it as a round; rounds of 1, 2, 4 marbles.

Usage:
  python3 make_video.py row-row-row                          # -> build/row-row-row/Marble_Spiral_Row_Your_Boat.mp4
  python3 make_video.py row-row-row --stills 150,1080        # PNG stills only (build/row-row-row/still_0150.png ...)
  python3 make_video.py row-row-row --thumb-only             # just the thumbnail
Options: --thumb-frame N (default: the song's thumb_frame, else the middle of the longest stretch with the most
marbles on the track),
--thumb-title (draw the round title on the thumbnail; off by default), --no-thumb.
Environment: WATERMARK (default "Marble Pop", empty for none), WORKERS (2), CRF (17), SPLIT (balanced | even).

Steps: build the track mesh from the song and path-trace the static set once (cached by scene + mesh hash) ->
choreography + dish physics -> marble lighting table from the tracer's env mode -> music -> marbles composited per
frame in WORKERS processes -> concat -> AAC at -13 LUFS -> thumbnail (same camera).
"""
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.join(HERE, "..", "marble-raytrace-kit")
sys.path.insert(0, HERE)
sys.path.insert(0, KIT)

# ===================================================================== SETTINGS (shipped values)
BUILD = os.environ.get("BUILD_DIR", os.path.join(HERE, "build"))
WATERMARK = os.environ.get("WATERMARK", "Marble Pop")
WORKERS = int(os.environ.get("WORKERS", "2"))
CRF = int(os.environ.get("CRF", "17"))
STATIC_SAMPLES = (49, 64)       # key-light / ambient samples per pixel of the static path trace
NOTE_GLOW = (0.85, 0.22)        # segment flash when a marble reaches it: amplitude, decay (s)
FINALE_GLOW = (0.90, 0.55)      # finale sweep up the track
HOLD_LEVEL = 0.30               # segment stays lit at this level while a marble rolls over it
# ================================================================= END SETTINGS

from songs import SONGS

ap = argparse.ArgumentParser()
ap.add_argument("song", choices=sorted(SONGS))
ap.add_argument("--stills", default="")
ap.add_argument("--thumb-only", action="store_true")
ap.add_argument("--no-thumb", action="store_true")
ap.add_argument("--thumb-frame", type=int, default=None)
ap.add_argument("--thumb-title", action="store_true")
ap.add_argument("--worker", nargs=3, metavar=("F0", "F1", "OUT"))
args = ap.parse_args()
os.environ["MARBLE_SONG"] = args.song
SONG = SONGS[args.song]

import numpy as np
from PIL import Image

import scene as S
import timeline
import music
import tracers
import compositor as C
import pipeline as P

SONG_DIR = os.path.join(BUILD, args.song)
GPREFIX = os.path.join(SONG_DIR, "g")
SCENE_TXT = os.path.join(SONG_DIR, "scene.txt")
MESH = os.path.join(SONG_DIR, "mesh.bin")
log = P.log


def static_render():
    S.build_mesh().write(MESH)
    S.write_scene(SCENE_TXT, os.path.basename(MESH), 2 * S.W, 2 * S.H, *STATIC_SAMPLES)
    binary = tracers.build("meshtrace", BUILD)
    log("static set: path tracing (cached after the first run)...")
    if tracers.render_static(binary, SCENE_TXT, GPREFIX, GPREFIX + ".log", deps=[MESH]):
        log("static set rendered")
    return binary


def env_table(binary):
    """Lighting of every distinct marble position (visibility of the key light, ambient cube, gap, shadow reach)."""
    m = np.load(os.path.join(SONG_DIR, "marbles.npz"))
    pos, vis = m["pos"], m["vis"]
    nf, nm = vis.shape
    keys, pts = {}, []
    idx = np.full((nf, nm), -1, np.int64)
    for f in range(nf):
        for j in range(nm):
            if not vis[f, j]:
                continue
            p = pos[f, j]
            if p[0] < -40:
                continue
            k = tuple(np.round(p, 3))
            if k not in keys:
                keys[k] = len(pts)
                pts.append(p)
            idx[f, j] = keys[k]
    log(f"marble lighting: {len(pts)} positions...")
    res = tracers.env_query(binary, SCENE_TXT, np.array(pts, np.float32), SONG_DIR)
    env = np.full((nf, nm, 21), np.nan, np.float32)
    ok = idx >= 0
    env[ok] = res[idx[ok]]
    np.savez_compressed(os.path.join(SONG_DIR, "env.npz"), env=env)


def compositor(watermark):
    C.configure(S)
    tl = json.load(open(os.path.join(SONG_DIR, "timeline.json")))
    m = np.load(os.path.join(SONG_DIR, "marbles.npz"))
    envtab = np.load(os.path.join(SONG_DIR, "env.npz"))["env"]
    nseg = len(S.SONG)
    ft = tl["finale_t"]
    glows = []
    for k, (p, _) in enumerate(S.SONG):
        ev = [(n["t"], *NOTE_GLOW) for n in tl["notes"] if n["seg"] == k]
        ev.append((ft + 0.04 + (nseg - 1 - k) * 0.045, *FINALE_GLOW))
        hold = [(n["t"], n["t"] + n["dur"]) for n in tl["notes"] if n["seg"] == k]
        glows.append(dict(oid=S.OID_SEG0 + k, col=S.srgb2lin(S.PITCH_SRGB[p]), events=ev, hold=hold))
    seg_th = [S.seg_bounds(k) for k in range(nseg)]
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

    return C.Compositor(GPREFIX, m["pos"], m["vis"], tl["colors"], glows, titles=tl["titles"],
                        watermark=watermark or None, env_fn=env_fn, spill_fn=spill, hold_level=HOLD_LEVEL), tl, m


def pick_thumb_frame(tl):
    """Middle of the longest stretch of the last round with the most marbles on the track."""
    ms = tl["marbles"]
    last = max(mm["round"] for mm in ms)
    track_s = S.TOTAL / S.VEL
    best = (0, 0, 0)
    run = None
    for f in range(tl["n_frames"]):
        t = f / S.FPS
        n = sum(1 for mm in ms if mm["round"] == last and mm["t_in"] <= t <= mm["t_in"] + track_s)
        run = (run[0], f, n) if run and run[2] == n else (f, f, n)
        if (run[2], run[1] - run[0]) > (best[2], best[1] - best[0]):
            best = run
    return (best[0] + best[1]) // 2


def main():
    os.makedirs(SONG_DIR, exist_ok=True)
    if args.worker:
        comp, _, _ = compositor(WATERMARK)
        sys.exit(C.render_video(comp, int(args.worker[0]), int(args.worker[1]), args.worker[2], CRF))
    binary = static_render()
    tl, _, _ = timeline.build(SONG, SONG_DIR)
    log(f"timeline: {tl['n_frames']} frames ({tl['n_frames'] / S.FPS:.2f} s), {len(tl['marbles'])} marbles, "
        f"{len(tl['impacts'])} dish impacts")
    env_table(binary)
    if args.stills or args.thumb_only:
        comp, _, _ = compositor(WATERMARK)
        for fs in [s for s in args.stills.split(",") if s]:
            p = os.path.join(SONG_DIR, f"still_{int(fs):04d}.png")
            Image.fromarray(comp.render(int(fs))).save(p)
            log(p)
        if args.thumb_only:
            thumbnail(comp, tl)
        return
    wav = os.path.join(SONG_DIR, "music.wav")
    m = np.load(os.path.join(SONG_DIR, "marbles.npz"))
    music.build(tl, m["pos"], wav, S.FPS)
    parts = P.run_workers([sys.executable, __file__, args.song], tl["n_frames"], WORKERS, SONG_DIR,
                          P.frame_costs(m["pos"], m["vis"]))
    out = os.path.join(SONG_DIR, SONG["file"] + ".mp4")
    P.mux(parts, wav, out)
    log(f"video -> {out}")
    if not args.no_thumb:
        comp, _, _ = compositor(None)
        thumbnail(comp, tl)


def thumbnail(comp, tl):
    f = args.thumb_frame if args.thumb_frame is not None else SONG.get("thumb_frame")
    if f is None:
        f = pick_thumb_frame(tl)
    out = os.path.join(SONG_DIR, "thumbnail.png")
    Image.fromarray(comp.render(f, title=args.thumb_title, watermark=False)).save(out)
    log(f"thumbnail (frame {f}) -> {out}")


if __name__ == "__main__":
    main()
