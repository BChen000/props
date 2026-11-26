#!/usr/bin/env python3
"""One command for an endless 16:9 marble-music loop for a 24/7 YouTube livestream: marbles flow down a rainbow
staircase forever, each hop playing a note of a medley of public-domain songs, and the video loops seamlessly
(picture and sound), so `ffmpeg -stream_loop -1` can repeat it with no visible or audible seam.

Usage:
  python3 make_loop.py stairs              # -> build/stairs/marble_lullaby_stairs.mp4 (+ thumbnail.jpg)
  python3 make_loop.py twin                # -> build/twin/marble_twin_stairs_loop.mp4 (+ thumbnail.jpg)
  python3 make_loop.py stairs --stills 0,1200      # PNG stills (with panels) to check a change
  python3 make_loop.py stairs --audio-only         # just build/<loop>/music.wav
  python3 make_loop.py stairs --thumb-only         # just build/<loop>/thumbnail.jpg
  python3 make_loop.py stairs --encode-only        # re-run the final encode from the rendered parts
Environment: WORKERS (2), VIDEO_BITRATE (6M), PANELS (1; 0 for a clean picture), BUILD_DIR.

Steps: static set path-traced once at 2x (cached by scene hash) -> choreography (positions, hits, glows) -> music
(circular, so it loops) -> frames in WORKERS processes -> side panels (Pillow) -> one H.264 encode at YouTube live
settings (VIDEO_BITRATE, keyframe every 2 s, no scene-cut keyframes) with the music as AAC 192k.
"""
import argparse
import importlib
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
WORKERS = int(os.environ.get("WORKERS", "2"))
VIDEO_BITRATE = os.environ.get("VIDEO_BITRATE", "6M")
PANELS = os.environ.get("PANELS", "1") != "0"
PART_CRF = 10                   # near-lossless intermediate parts, re-encoded once at the end
KEYINT = 60                     # 2 s at 30 fps: YouTube live wants keyframes every 2 s (never over 4)
ENCODE_PRESET = "medium"
STATIC_SAMPLES = (49, 64)       # key-light / ambient samples per pixel of the static path trace
GLOW = (1.0, 0.20)              # tile flash on a hit: amplitude, decay (s), as in the Shorts
OUT_NAMES = {"stairs": "marble_lullaby_stairs.mp4", "twin": "marble_twin_stairs_loop.mp4"}
THUMB_CROP = {"stairs": (380, 190), "twin": (330, 150)}   # top-left of the 1280x720 thumbnail cut from the frame
AUDIO_CODEC = ["-c:a", "alac"]   # lossless, so the sound loops with no seam (AAC adds a small step there)
# ================================================================= END SETTINGS

ap = argparse.ArgumentParser()
ap.add_argument("loop", choices=sorted(OUT_NAMES))
ap.add_argument("--stills", default="")
ap.add_argument("--audio-only", action="store_true")
ap.add_argument("--encode-only", action="store_true")
ap.add_argument("--thumb-only", action="store_true")
ap.add_argument("--worker", nargs=3, metavar=("F0", "F1", "OUT"))
args = ap.parse_args()

import numpy as np
from PIL import Image

S = importlib.import_module(f"{args.loop}_set")
import loop as LP
import medleys as MD
import music as MU
import panels as PN
import tracers
import compositor as C
import pipeline as P

OUT = os.path.join(BUILD, args.loop)
GPREFIX = os.path.join(OUT, "g")
SCENE_TXT = os.path.join(OUT, "scene.txt")
log = P.log


def static_render():
    os.makedirs(OUT, exist_ok=True)
    S.write_scene(SCENE_TXT, 2 * S.W, 2 * S.H, *STATIC_SAMPLES)
    binary = tracers.build("boxtrace", BUILD)
    log("static set: path tracing (cached after the first run)...")
    if tracers.render_static(binary, SCENE_TXT, GPREFIX, GPREFIX + ".log"):
        log("static set rendered")


def compositor():
    C.configure(S)
    tl = json.load(open(os.path.join(OUT, "timeline.json")))
    m = np.load(os.path.join(OUT, "marbles.npz"))
    glows = []
    for k, evs in enumerate(tl["glows"]):
        lane, i = divmod(k, S.T)
        glows.append(dict(oid=S.tile_oid(lane, i), col=np.clip(S.TILE_LIN[k], 0, None),
                          events=[(t, *GLOW) for t in evs]))
    return C.Compositor(GPREFIX, m["pos"], m["vis"], tl["colors"], glows, titles=[], watermark=None,
                        hidden_fn=lambda mi, c: S.hidden(c), spill_fn=S.spill), tl


def timeline():
    songs, starts, total = MD.medley(args.loop)
    data, pos, vis, hits, knocks = LP.build(S, total, OUT)
    log(f"timeline: {data['n_frames']} frames ({data['n_frames'] / S.FPS / 60:.2f} min), {len(data['marbles'])} "
        f"marbles a loop, up to {int(vis.sum(1).max())} on screen; seam check {LP.seam_check(S, data)} (want 0)")
    return data, hits, knocks


def music(data, hits, knocks):
    wav = os.path.join(OUT, "music.wav")
    ev, songs, starts, total = MU.notes(args.loop, hits, knocks, S.TAU, S.T)
    integ, peak = MU.render(ev, total * S.TAU, wav)
    jump, step = MU.seam_jump(wav)
    log(f"music: {len(ev)} notes, {integ:.1f} LUFS, peak {peak:.1f} dBFS, loop seam step {jump:.4f} "
        f"(99.9% of steps are under {step:.4f})")
    for s, st in zip(songs, starts):
        log(f"  {st * S.TAU / 60:5.2f} min  {s['name']}")
    return wav, songs, starts, total


def encode(parts, wav, overlays, out):
    lst = os.path.join(OUT, "parts.txt")
    with open(lst, "w") as fh:
        fh.writelines(f"file '{os.path.abspath(p)}'\n" for p in parts)
    rate = VIDEO_BITRATE
    bufsize = f"{2 * int(rate.rstrip('M'))}M" if rate.endswith("M") else rate
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav]
    fc, cur = [], "0:v"
    for i, (png, t0, t1) in enumerate(overlays):
        cmd += ["-i", png]
        en = "" if t0 is None else f":enable='between(t,{t0:.3f},{t1:.3f})'"
        fc.append(f"[{cur}][{i + 2}:v]overlay=0:0:eof_action=repeat{en}[o{i}]")
        cur = f"o{i}"
    vmap = f"[{cur}]" if overlays else "0:v"
    if overlays:
        cmd += ["-filter_complex", ";".join(fc)]
    tmp = out[:-4] + ".part.mp4"
    cmd += ["-map", vmap, "-map", "1:a", "-c:v", "libx264", "-preset", ENCODE_PRESET, "-b:v", rate, "-maxrate", rate,
            "-bufsize", bufsize, "-g", str(KEYINT), "-keyint_min", str(KEYINT), "-sc_threshold", "0",
            "-pix_fmt", "yuv420p", *AUDIO_CODEC, "-movflags", "+faststart", tmp]
    subprocess.run(cmd, check=True)
    os.replace(tmp, out)
    os.remove(lst)


def overlays(songs, starts, total):
    """Static panels plus one 'now playing' card per song, shown from half way through the gap before it."""
    if not PANELS:
        return []
    d = os.path.join(OUT, "panels")
    os.makedirs(d, exist_ok=True)
    base = os.path.join(d, "base.png")
    PN.base_panel(base, args.loop)
    out = [(base, None, None)]
    L = total * S.TAU
    names = []
    for i, s in enumerate(songs):
        if names and names[-1][0] == s["name"]:
            continue
        names.append((s["name"], starts[i]))
    for i, (name, st) in enumerate(names):
        png = os.path.join(d, f"song_{i + 1}.png")
        PN.song_panel(png, args.loop, name, i + 1, len(names))
        nxt = names[(i + 1) % len(names)][1] if i + 1 < len(names) else total
        a = max(0.0, (st - MD.GAP / 2) * S.TAU) if i else 0.0
        b = (nxt - MD.GAP / 2) * S.TAU
        out.append((png, a, b - 1e-3))
        if i == 0:
            first = png
    out.append((first, L - MD.GAP / 2 * S.TAU, L + 1))
    return out


def stills(comp, frames, ovs):
    for fs in frames:
        f = int(fs)
        img = Image.fromarray(comp.render(f)).convert("RGBA")
        t = f / S.FPS
        for png, a, b in ovs:
            if a is None or a <= t <= b:
                img.alpha_composite(Image.open(png).convert("RGBA"))
        p = os.path.join(OUT, f"still_{f:05d}.png")
        img.convert("RGB").save(p)
        log(p)


def thumbnail(comp, data):
    """Two frames after a hit (tiles still glowing), at the beat with the most marbles on the stairs, cut to
    1280x720 around the set at full resolution; no text."""
    m = np.load(os.path.join(OUT, "marbles.npz"))
    per_beat = round(S.TAU * S.FPS)
    counts = []
    for f in range(2, data["n_frames"], per_beat):
        on = m["vis"][f] & (m["pos"][f][:, 0] > -1.0) & (m["pos"][f][:, 0] < S.T * S.DX)
        counts.append((int(on.sum()), f))
    most = max(c for c, _ in counts)
    best = [f for c, f in counts if c == most]
    bf = best[len(best) // 2]
    img = Image.fromarray(comp.render(bf))
    out = os.path.join(OUT, "thumbnail.jpg")
    x0, y0 = THUMB_CROP[args.loop]
    img.crop((x0, y0, x0 + 1280, y0 + 720)).save(out, quality=92)
    log(f"thumbnail (frame {bf}) -> {out}")


def main():
    if args.worker:
        comp, _ = compositor()
        sys.exit(C.render_video(comp, int(args.worker[0]), int(args.worker[1]), args.worker[2], PART_CRF))
    data, hits, knocks = timeline()
    wav, songs, starts, total = music(data, hits, knocks)
    if args.audio_only:
        return
    static_render()
    if args.thumb_only:
        comp, _ = compositor()
        thumbnail(comp, data)
        return
    ovs = overlays(songs, starts, total)
    if args.stills:
        comp, _ = compositor()
        stills(comp, [s for s in args.stills.split(",") if s], ovs)
        return
    m = np.load(os.path.join(OUT, "marbles.npz"))
    if args.encode_only:
        parts = [os.path.join(OUT, f"part{i + 1}.mp4") for i in range(WORKERS)]
    else:
        parts = P.run_workers([sys.executable, __file__, args.loop], data["n_frames"], WORKERS, OUT,
                              P.frame_costs(m["pos"], m["vis"]))
    out = os.path.join(OUT, OUT_NAMES[args.loop])
    log("final encode...")
    encode(parts, wav, ovs, out)
    log(f"loop -> {out}")
    comp, _ = compositor()
    thumbnail(comp, data)


if __name__ == "__main__":
    main()
