#!/usr/bin/env python3
"""One command for a twin-staircase marble music Short: two rainbow staircases side by side, the front one playing
the melody and the back one the harmony, one tile per beat; rounds of 1, 2, 4, 8 marbles.

Usage:
  python3 make_video.py ode-to-joy                           # -> build/ode-to-joy/Marble_Twin_Stairs_Ode_to_Joy.mp4
  python3 make_video.py ode-to-joy --stills 300,840          # PNG stills only (build/ode-to-joy/still_0300.png ...)
  python3 make_video.py ode-to-joy --thumb-only              # just the thumbnail
Options: --thumb-frame N (default: the busiest beat of the last round), --thumb-title (draw the round title on the
thumbnail; off by default), --no-thumb.
Environment: WATERMARK (default "Marble Pop", empty for none), WORKERS (2), CRF (17), SPLIT (balanced | even),
MARBLE_BPM (song's bpm).

Steps: path-trace the static set once (cached by scene hash) -> choreography + tray physics -> music -> marbles
composited per frame in WORKERS processes -> concat -> AAC at -13 LUFS -> thumbnail (same camera).
"""
import argparse
import json
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
GLOW_DECAY = 0.20               # s, tile glow after a hit
FINALE_DECAY = 0.50             # s, tile glow of the finale sweep
# ================================================================= END SETTINGS

from songs import SONGS, beats_needed

ap = argparse.ArgumentParser()
ap.add_argument("song", choices=sorted(SONGS))
ap.add_argument("--stills", default="")
ap.add_argument("--thumb-only", action="store_true")
ap.add_argument("--no-thumb", action="store_true")
ap.add_argument("--thumb-frame", type=int, default=None)
ap.add_argument("--thumb-title", action="store_true")
ap.add_argument("--worker", nargs=3, metavar=("F0", "F1", "OUT"))
args = ap.parse_args()
SONG = SONGS[args.song]
os.environ.setdefault("MARBLE_BPM", str(SONG["bpm"]))

import numpy as np
from PIL import Image

import look
HUE, SAT, BRIGHT = float(SONG.get("hue", 0.0)), float(SONG.get("sat", 1.0)), float(SONG.get("bright", 1.0))
look.set_hue(HUE, SAT, BRIGHT)  # before importing scene, which copies the studio colours
import scene as S
import timeline
import music
import tracers
import compositor as C
import pipeline as P

SONG_DIR = os.path.join(BUILD, args.song)
LOOK_TAG = ((f"_hue{HUE:g}" if HUE else "") + (f"_sat{SAT:g}" if SAT != 1.0 else "")
            + (f"_bright{BRIGHT:g}" if BRIGHT != 1.0 else ""))
GPREFIX = os.path.join(BUILD, "g" + LOOK_TAG)
log = P.log


def static_render():
    scene_txt = os.path.join(BUILD, "scene%s.txt" % LOOK_TAG)
    S.write_scene(scene_txt, 2 * S.W, 2 * S.H, *STATIC_SAMPLES)
    binary = tracers.build("boxtrace", BUILD)
    log("static set: path tracing (cached after the first run)...")
    if tracers.render_static(binary, scene_txt, GPREFIX, GPREFIX + ".log"):
        log("static set rendered")


def compositor(watermark):
    C.configure(S)
    tl = json.load(open(os.path.join(SONG_DIR, "timeline.json")))
    m = np.load(os.path.join(SONG_DIR, "marbles.npz"))
    glows = []
    for k in range(S.NT):
        ev = [(h["t"], 1.0, GLOW_DECAY) for h in tl["hits"] if h["tile"] == k]
        ev.append((tl["finale_t"] + 0.035 + (S.T - 1 - k % S.T) * 0.05, 1.0, FINALE_DECAY))
        glows.append(dict(oid=S.OID_TILE0 + k, col=np.clip(S.TILE_LIN[k] * 1.0, 0, None), events=ev))

    def spill(k, c):  # nearest point of tile k's top face lights the marble
        tx, ty, tz = S.tile_pos(k)
        return np.array([min(max(c[0], tx - S.TILE_HX), tx + S.TILE_HX), ty,
                         min(max(c[2], tz - S.TILE_HZ), tz + S.TILE_HZ)])

    return C.Compositor(GPREFIX, m["pos"], m["vis"], tl["colors"], glows, titles=tl["titles"],
                        watermark=watermark or None, spill_fn=spill), tl, m


def pick_thumb_frame(tl, m):
    """Of the last round's beats with the most marbles on the stairs, the middle one, 1 frame after the hit."""
    pos, vis = m["pos"], m["vis"]
    last_round = max(e[0] for e in tl["entries"])
    beats = sorted({h["beat"] for h in tl["hits"] if h["round"] == last_round})
    counts = []
    for b in beats:
        f = min(int(round((tl["t0"] + b * tl["tau"]) * S.FPS)) + 1, tl["n_frames"] - 1)
        p = pos[f]
        on = (vis[f] & (p[:, 0] > -1.5) & (p[:, 0] < (S.T - 1) * S.DX + 1.5) & (p[:, 1] > S.TRAY_TOP + S.R)).sum()
        counts.append((on, f))
    most = max(c for c, _ in counts)
    frames = [f for c, f in counts if c == most]
    return frames[len(frames) // 2]


def thumbnail(comp, tl, m):
    f = args.thumb_frame if args.thumb_frame is not None else pick_thumb_frame(tl, m)
    out = os.path.join(SONG_DIR, "thumbnail.png")
    Image.fromarray(comp.render(f, title=args.thumb_title, watermark=False)).save(out)
    log(f"thumbnail (frame {f}) -> {out}")


def main():
    os.makedirs(SONG_DIR, exist_ok=True)
    if args.worker:
        comp, _, _ = compositor(WATERMARK)
        sys.exit(C.render_video(comp, int(args.worker[0]), int(args.worker[1]), args.worker[2], CRF))
    need = beats_needed(SONG, S.T)
    if len(SONG["melody"]) < need:
        log(f"warning: the rounds play {need} beats but the melody has {len(SONG['melody'])}")
    static_render()
    tl, _, _ = timeline.build(SONG, SONG_DIR)
    log(f"timeline: {tl['n_frames']} frames ({tl['n_frames'] / S.FPS:.2f} s), {len(tl['entries'])} marbles, "
        f"{len(tl['impacts'])} tray impacts")
    if args.stills or args.thumb_only:
        comp, tl, m = compositor(WATERMARK)
        for fs in [s for s in args.stills.split(",") if s]:
            p = os.path.join(SONG_DIR, f"still_{int(fs):04d}.png")
            Image.fromarray(comp.render(int(fs))).save(p)
            log(p)
        if args.thumb_only:
            thumbnail(comp, tl, m)
        return
    wav = os.path.join(SONG_DIR, "music.wav")
    music.build(tl, SONG, wav)
    m = np.load(os.path.join(SONG_DIR, "marbles.npz"))
    parts = P.run_workers([sys.executable, __file__, args.song], tl["n_frames"], WORKERS, SONG_DIR,
                          P.frame_costs(m["pos"], m["vis"]))
    out = os.path.join(SONG_DIR, SONG["file"] + ".mp4")
    P.mux(parts, wav, out)
    log(f"video -> {out}")
    if not args.no_thumb:
        comp, tl, m = compositor(None)
        thumbnail(comp, tl, m)


if __name__ == "__main__":
    main()
