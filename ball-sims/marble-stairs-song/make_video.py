#!/usr/bin/env python3
"""One command for a rainbow-staircase marble music Short: marbles drop from a chute and hop down 8 glowing tiles,
one tile per beat, each hit playing the next note of the song; rounds of 1, 2, 3, 5, 8 marbles.

Usage:
  python3 make_video.py twinkle                      # -> build/twinkle/Marble_Staircase_Twinkle.mp4 + thumbnail.png
  python3 make_video.py jingle-bells
  python3 make_video.py twinkle --stills 300,650,900 # PNG stills only (build/twinkle/still_0300.png ...)
  python3 make_video.py twinkle --thumb-only         # just the thumbnail
Options: --thumb-frame N (default: the busiest beat of the last round), --thumb-title (draw the round title on the
thumbnail; off by default), --no-thumb.
Environment: WATERMARK (default "Marble Pop", empty for none), WORKERS (2), CRF (17), SPLIT (balanced | even),
MARBLE_BPM (song's bpm).

Steps: path-trace the static set once (cached by scene hash, ~1.5 min) -> choreography + tray physics (~1 s) ->
music (~20 s) -> marbles composited per frame in WORKERS processes (~2.5 min) -> concat -> AAC at -13 LUFS ->
thumbnail from a closer camera (its own static render, ~1.5 min).
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

import scene as S
import timeline
import music
import tracers
import compositor as C
import pipeline as P

SONG_DIR = os.path.join(BUILD, args.song)
THUMB = os.environ.get("MARBLE_CAM") in ("thumb", "widethumb")
GPREFIX = os.path.join(BUILD, "thumb_g" if THUMB else "g")
log = P.log


def static_render():
    scene_txt = os.path.join(BUILD, "thumb_scene.txt" if THUMB else "scene.txt")
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
    for k in range(S.T):
        ev = [(h["t"], 1.0, GLOW_DECAY) for h in tl["hits"] if h["tile"] == k]
        ev.append((tl["finale_t"] + 0.035 + (S.T - 1 - k) * 0.045, 1.0, FINALE_DECAY))
        glows.append(dict(oid=S.OID_TILE0 + k, col=np.clip(S.TILE_LIN[k] * 1.0, 0, None), events=ev))

    def hidden(mi, c):  # still inside the feeder tube
        if c[0] < 0.5:
            return (c - S.CH_PIVOT) @ S.CH_U < S.TUBE_MOUTH - 1.02 * S.R
        return False

    def spill(k, c):  # nearest point of tile k's top face lights the marble
        tx, ty = S.tile_top(k)
        return np.array([min(max(c[0], tx - S.TILE_HX), tx + S.TILE_HX), ty, min(max(c[2], -S.TILE_HZ), S.TILE_HZ)])

    return C.Compositor(GPREFIX, m["pos"], m["vis"], tl["colors"], glows, titles=tl["titles"],
                        watermark=watermark or None, hidden_fn=hidden, spill_fn=spill), tl, m


def pick_thumb_frame(tl, m):
    """Of the last round's beats with the most marbles on the stairs, the middle one, 1 frame after the hit."""
    pos, vis = m["pos"], m["vis"]
    last_round = max(r for r, _ in tl["entries"])
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


def thumbnail():
    static_render()
    comp, tl, m = compositor(None)
    f = args.thumb_frame if args.thumb_frame is not None else pick_thumb_frame(tl, m)
    img = comp.render(f, title=args.thumb_title, watermark=False)
    out = os.path.join(SONG_DIR, "thumbnail.png")
    Image.fromarray(img).save(out)
    log(f"thumbnail (frame {f}) -> {out}")


def main():
    os.makedirs(SONG_DIR, exist_ok=True)
    if args.worker:
        comp, _, _ = compositor(WATERMARK)
        sys.exit(C.render_video(comp, int(args.worker[0]), int(args.worker[1]), args.worker[2], CRF))
    if THUMB:
        thumbnail()
        return
    need = beats_needed(SONG, S.T)
    if len(SONG["melody"]) < need:
        log(f"warning: the rounds play {need} beats but the melody has {len(SONG['melody'])}; extra beats ring C6")
    tl, _, _ = timeline.build(SONG, SONG_DIR)
    log(f"timeline: {tl['n_frames']} frames ({tl['n_frames'] / S.FPS:.2f} s), {len(tl['entries'])} marbles, "
        f"{len(tl['impacts'])} tray impacts")
    env = dict(os.environ, MARBLE_CAM="widethumb" if os.environ.get("MARBLE_CAM") in ("wide", "widethumb") else "thumb")
    if args.thumb_only:
        subprocess.run([sys.executable, __file__, args.song, *sys.argv[2:]], env=env, check=True)
        return
    static_render()
    if args.stills:
        comp, _, _ = compositor(WATERMARK)
        for fs in args.stills.split(","):
            p = os.path.join(SONG_DIR, f"still_{int(fs):04d}.png")
            Image.fromarray(comp.render(int(fs))).save(p)
            log(p)
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
        extra = [a for a in sys.argv[2:] if a != "--no-thumb"]
        subprocess.run([sys.executable, __file__, args.song, *extra], env=env, check=True)


if __name__ == "__main__":
    main()
