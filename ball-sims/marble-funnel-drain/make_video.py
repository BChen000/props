"""Marble Funnel Drain: the whole Short in one command.

  python make_video.py                     -> build/marble_funnel_drain.mp4 + build/thumbnail.png (+ .jpg)
  python make_video.py --stills 0,300,720  -> build/stills/still_<n>.png only, to check a change
  python make_video.py --thumb-only        -> build/thumbnail.png only
  python make_video.py --info              -> length, frames and when each colour drops out
  python make_video.py --where 7.8         -> where the coloured marbles are at sim time 7.8 s (to aim shots)
  python make_video.py --max-frames 90     -> a short test build of the first 90 frames
  python make_video.py --style             -> rewrite style.json from settings.py and the race

Frames render in WORKERS processes (one numba thread each), get encoded per worker, joined with the concat demuxer
and muxed with the synthesized soundtrack.
"""
import json
import os
import subprocess
import sys
import time

os.environ.setdefault("NUMBA_NUM_THREADS", "1")
import numpy as np  # noqa: E402

import settings as S  # noqa: E402
import timeline as TL  # noqa: E402
from sim import sim_path  # noqa: E402

HERE = S.HERE


def renderer():
    import render as rd
    return rd, rd.Renderer()


def render_segment(n0, n1, outfile):
    ep = TL.Episode(sim_path())
    rd, ren = renderer()
    tmp = outfile[:-4] + ".part.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (rd.W, rd.H),
           "-r", str(TL.FPS), "-i", "-", "-c:v", "libx264", "-preset", S.PRESET, "-crf", str(S.CRF),
           "-pix_fmt", "yuv420p", "-threads", "1", "-movflags", "+faststart", tmp]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    for n in range(n0, n1):
        cam, x, y, z, st, subs, kd, zf, t = ep.frame_inputs(n, rd)
        img = ren.frame(cam, x, y, z, st, ep.btype, ep.bcol, subs, kd=kd, zf=zf, grain_seed=n)
        p.stdin.write(img.tobytes())
        if (n - n0) % 20 == 0:
            print("%s %d/%d (sim %.2f s)  %.0f s" % (os.path.basename(outfile), n - n0, n1 - n0, t, time.time() - t0), flush=True)
    p.stdin.close()
    rc = p.wait()
    if rc == 0:
        os.replace(tmp, outfile)
    print("done", outfile, rc, "%.0f s" % (time.time() - t0), flush=True)
    return rc


def stills(ns):
    from PIL import Image
    ep = TL.Episode(sim_path())
    rd, ren = renderer()
    os.makedirs(os.path.join(S.BUILD, "stills"), exist_ok=True)
    for n in ns:
        t1 = time.time()
        cam, x, y, z, st, subs, kd, zf, t = ep.frame_inputs(n, rd)
        img = ren.frame(cam, x, y, z, st, ep.btype, ep.bcol, subs, kd=kd, zf=zf, grain_seed=n)
        path = os.path.join(S.BUILD, "stills", "still_%04d.png" % n)
        Image.fromarray(img).save(path)
        print("still %d  video %.2f s  sim %.2f s  %.1f s -> %s" % (n, n / TL.FPS, t, time.time() - t1, path), flush=True)


def thumbnail():
    from PIL import Image
    ep = TL.Episode(sim_path())
    rd, ren = renderer()
    s = S.THUMB
    f = int(round(s["t"] * ep.HZ))
    cam = rd.make_cam(s["T"], s["D"], s["yaw"], s["elev"], s["hf"])
    img = ren.frame(cam, ep.RX[f].astype(np.float64), ep.RY[f].astype(np.float64), ep.RZ[f].astype(np.float64),
                    ep.RS[f].astype(np.int64), ep.btype, ep.bcol, None, kd=s["kd"], zf=s["D"], grain_seed=3)
    os.makedirs(S.BUILD, exist_ok=True)
    png = os.path.join(S.BUILD, "thumbnail.png")
    Image.fromarray(img).save(png)
    Image.fromarray(img).convert("RGB").save(os.path.join(S.BUILD, "thumbnail.jpg"), quality=95)
    print("thumbnail ->", png)


def info():
    ep = TL.Episode(sim_path())
    print("video %.2f s, %d frames at %d fps (sim %.2f -> %.2f s)" % (TL.VLEN, TL.NFR, TL.FPS, S.T0, S.T_END))
    print("camera keys (video s):", [(name, round(kv, 2)) for (_, name), kv in zip(S.KEYS, TL.KV)])
    for p in ep.places():
        print("place %d %-6s marble %3d  out at sim %.2f s = video %.2f s" % (p["place"], p["colour"], p["marble"], p["out_sim_s"], p["out_video_s"]))
    return ep


def where(t):
    """Where the coloured marbles are at sim time t: for aiming the CLOSE shot and the thumbnail."""
    ep = TL.Episode(sim_path())
    f = int(round(t * ep.HZ))
    for k, b in enumerate(ep.picks):
        print("%-6s marble %3d at x %6.1f  y %6.1f  (%s)" % (S.PLACES[k], b, ep.RX[f, b], ep.RY[f, b],
                                                         {0: "not poured yet", 1: "rolling", 2: "falling", 3: "gone"}[int(ep.RS[f, b])]))


def write_style():
    ep = TL.Episode(sim_path())
    style = dict(
        prop="marble-funnel-drain",
        canvas=dict(width=S.W, height=S.H, fps=S.FPS, renderer="numba CPU ray-caster (render.py)"),
        episode=dict(seed=S.SEED, frames=TL.NFR, duration_s=round(TL.VLEN, 3), sim_start_s=S.T0, sim_end_s=S.T_END,
                     marbles=S.SIM["N"], places=ep.places(),
                     loop="last frame = opening shot over the empty board; frame 0 = same shot as the first marbles arrive"),
        physics=S.SIM, look={k: v for k, v in S.LOOK.items()}, palette=S.PALETTE, places=S.PLACES,
        shots=S.SHOTS, keys=S.KEYS, speed=S.SPEED, shutter=S.SHUT, thumbnail=S.THUMB,
        camera_moves_video_s=[[round(a, 3), round(b, 3)] for a, b in TL.camera_moves()],
        encoding=dict(codec="libx264", preset=S.PRESET, crf=S.CRF, pix_fmt="yuv420p", audio="aac 192k 48 kHz",
                      volume_db=S.VOLUME_DB, loudness_lufs=-14.1),
        copy=dict(title="Last Marble Left WINS 🕳️ Pick Your Color",
                  description=["480 marbles swirl into one hole. The last color left wins!",
                               "Pick your color in the comments 🔴🔵🟢🟡", "Made with a 3D physics simulation",
                               "#marbles #satisfying #3d #pickyourcolor #whowillwin"],
                  thumbnail="no text"),
    )
    with open(os.path.join(HERE, "style.json"), "w", encoding="utf-8") as f:
        json.dump(style, f, indent=1, ensure_ascii=False)
    print("wrote style.json")


def build(max_frames=None):
    t0 = time.time()
    ep = info()
    renderer()  # builds the cached world maps once, before the workers start
    nfr = TL.NFR if max_frames is None else min(max_frames, TL.NFR)
    split = S.SPLIT_AT if max_frames is None else nfr // 2
    seg_dir = os.path.join(S.BUILD, "segments")
    os.makedirs(seg_dir, exist_ok=True)
    ranges = [(0, nfr)] if S.WORKERS < 2 or split <= 0 or split >= nfr else [(0, split), (split, nfr)]
    procs, files = [], []
    for k, (a, b) in enumerate(ranges):
        out = os.path.join(seg_dir, "seg_%d_%d.mp4" % (a, b))
        files.append(out)
        env = dict(os.environ, NUMBA_NUM_THREADS="1")
        procs.append(subprocess.Popen([sys.executable, os.path.abspath(__file__), "--segment", str(a), str(b), out], env=env, cwd=HERE))
    if any(p.wait() != 0 for p in procs):
        sys.exit("a render worker failed")
    from audio import make_audio
    wav = make_audio(ep, os.path.join(S.BUILD, "soundtrack.wav"))
    lst = os.path.join(seg_dir, "list.txt")
    with open(lst, "w") as f:
        f.writelines("file '%s'\n" % p for p in files)
    name = S.OUT_NAME if max_frames is None else "%s_first%d" % (S.OUT_NAME, nfr)
    final = os.path.join(S.BUILD, name + ".mp4")
    tmp = final[:-4] + ".part.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-af", "volume=%gdB" % S.VOLUME_DB,
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, final)
    if max_frames is None:
        thumbnail()
    print("done in %.1f min -> %s" % ((time.time() - t0) / 60, final))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--segment"]:
        sys.exit(render_segment(int(a[1]), int(a[2]), a[3]))
    elif a[:1] == ["--stills"]:
        stills([int(v) for v in a[1].split(",")])
    elif a[:1] == ["--thumb-only"]:
        thumbnail()
    elif a[:1] == ["--info"]:
        info()
    elif a[:1] == ["--where"]:
        where(float(a[1]))
    elif a[:1] == ["--style"]:
        write_style()
    elif a[:1] == ["--max-frames"]:
        build(int(a[1]))
    else:
        build()
