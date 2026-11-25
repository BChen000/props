#!/usr/bin/env python3
"""Full-screen Marble Pop long-form: 16:9 template renders + reframed Shorts as "Guess the Marble Song" rounds.

Usage:
  python3 build.py --plan            # timeline only
  python3 build.py --only 3,4        # render those rounds' segments (build/segs/seg_NN.mp4) and stop
  python3 build.py                   # everything -> build/<OUT_NAME>, chapters.txt, plan.json, youtube_copy.txt
  python3 build.py --render-wide     # first makes the music rounds' missing 16:9 template renders (~2 h for 14)
Rendered segments are reused; delete one (or FORCE=1) to redo it. A music round needs its 16:9 template render, e.g.
  cd ../marble-stairs-song && MARBLE_RES=1920x1080 MARBLE_CAM=wide BUILD_DIR=build_wide WATERMARK= \\
      python3 make_video.py twinkle --no-thumb
"""
import argparse
import fnmatch
import glob
import json
import os
import re
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import settings as S  # noqa: E402
import track  # noqa: E402
import vcam  # noqa: E402
import ui  # noqa: E402
import widgets as WG  # noqa: E402

FORCE = os.environ.get("FORCE") == "1"
T = S.TRANSITION_FRAMES
ASSETS = os.path.join(S.BUILD, "assets")
SEGS = os.path.join(S.BUILD, "segs")
AUD = os.path.join(S.BUILD, "audio")
LOOP = "loop=loop=-1:size=1:start=0,setpts=N/(30*TB),settb=1/30"


def sh(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def probe_vdur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                          "stream=duration", "-of", "default=nw=1:nk=1", p]).strip())


def resolve(it):
    if it["src"][0] == "wide":
        _, tpl, song = it["src"]
        d = os.path.join(S.PROPS, tpl, S.WIDE_BUILD, song)
        hits = [f for f in glob.glob(os.path.join(d, "*.mp4")) if not os.path.basename(f).startswith("part")]
        if len(hits) != 1:
            if os.environ.get("PLAN_LENIENT") == "1":
                return None
            sys.exit(f"{it['key']}: need exactly one finished 16:9 render in {d}, found {hits}")
        return hits[0]
    hits = sorted(f for f in os.listdir(S.SHORTS_DIR) if fnmatch.fnmatch(f, it["src"][1]))
    if len(hits) != 1:
        sys.exit(f"{it['key']}: pattern {it['src'][1]} matched {hits} in {S.SHORTS_DIR}")
    return os.path.join(S.SHORTS_DIR, hits[0])


def first_note(it):
    """Seconds of the first note: the template's own timeline when there is one, else the first loud 10 ms."""
    if "f0" in it:
        return it["f0"]
    tl = os.path.join(os.path.dirname(it["path"]), "timeline.json")
    if it["src"][0] == "wide" and os.path.exists(tl):
        hits = [h["t"] for h in json.load(open(tl)).get("hits", []) if "t" in h]
        if hits:
            return min(hits)
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", it["path"], "-ac", "1", "-ar", "8000", "-f", "f32le", "-"])
    a = np.frombuffer(raw, np.float32)
    n = len(a) // 80
    rms = 20 * np.log10(np.sqrt((a[:n * 80].reshape(n, 80) ** 2).mean(1)) + 1e-9)
    return float(np.argmax(rms > -35) * 0.01)


# ----------------------------------------------------------------------------------------------- plan
def plan():
    items, start = [], 0
    total = sum(1 for it in S.ITEMS if it["kind"] != "bonus")
    for i, it in enumerate(S.ITEMS):
        it = dict(it)
        it.update(idx=i, path=resolve(it), first=i == 0, last=i == len(S.ITEMS) - 1, total=total)
        vdur = probe_vdur(it["path"]) if it["path"] else 37.6
        if it["kind"] in ("song", "bonus"):
            it["f0"] = first_note(it) if it["path"] else 1.067
        ts = it["ts"] if "ts" in it else max(0.0, it["f0"] - S.CUT_BEFORE_NOTE_S)
        te = it["te"] if "te" in it else vdur - S.RENDER_TAIL_S
        ts_f, te_f = int(round(ts * S.FPS)), min(int(round(te * S.FPS)), int(vdur * S.FPS + 1e-6))
        pieces, cur = [], ts_f
        for a, b, k in it.get("speed", []):
            a_f, b_f = int(round(a * S.FPS)), int(round(b * S.FPS))
            pieces += [(cur, a_f, 1.0), (a_f, b_f, k)]
            cur = b_f
        pieces.append((cur, te_f, 1.0))
        N = int(np.floor(sum((b - a) / k for a, b, k in pieces))) - 1
        it.update(ts_f=ts_f, te_f=te_f, pieces=pieces, N=N, start=start, D=N / S.FPS, vdur=vdur)

        def local(t, pieces=pieces):
            tf, out = t * S.FPS, 0.0
            for a, b, k in pieces:
                if tf <= a:
                    break
                out += (min(tf, b) - a) / k
            return out / S.FPS
        it["local"] = local
        ev = {}
        if it["kind"] in ("song", "bonus"):
            f0 = local(it["f0"]) if it["f0"] > ts else 0.0
            count = it.get("countdown", S.COUNTDOWN_S)
            cd = max(f0 + S.COUNTDOWN_LEAD_S, (S.INTRO_S + 0.4) if i == 0 else 0.0)
            ev.update(f0=f0, cd=cd, count=count, reveal=cd + count)
        if it["kind"] == "run" and it.get("reveal"):
            ev["reveal"] = local(it["reveal"])
        if it["kind"] == "race":
            ev.update(prompt_end=S.RACE_PROMPT_S, end=local(it["end_t"]))
        if not it["last"]:
            ev["upnext"] = it["D"] - S.UPNEXT_LEAD_S
        if it["kind"] == "bonus":
            ev["endscreen"] = it["D"] - S.END_SCREEN_S
        it["ev"] = ev
        items.append(it)
        start += N
    for i, it in enumerate(items):
        nxt = items[i + 1] if i + 1 < len(items) else None
        it["next"] = None if not nxt else {"song": "MYSTERY SONG", "race": "MARBLE RACE", "run": "MARBLE RUN",
                                           "bonus": "SECRET BONUS!"}[nxt["kind"]]
        it["color_in"] = S.MARBLES[(i - 1) % len(S.MARBLES)]
        it["color_out"] = S.MARBLES[i % len(S.MARBLES)]
    return items


def fmt_t(sec):
    sec = int(sec)
    return f"{sec // 60}:{sec % 60:02d}"


def print_plan(items):
    tot = sum(it["N"] for it in items)
    print(f"{len(items)} rounds, {tot} frames = {tot / S.FPS:.1f} s ({fmt_t(tot / S.FPS)})")
    for it in items:
        ev = " ".join(f"{k}={v:.2f}" for k, v in it["ev"].items())
        print(f"{it['idx']:2d} {fmt_t(it['start'] / S.FPS):>5} {it['key']:14s} {it['kind']:5s} "
              f"src {it['ts_f'] / S.FPS:5.2f}-{it['te_f'] / S.FPS:5.2f} -> {it['D']:5.2f}s  {ev}")


# ----------------------------------------------------------------------------------------------- overlay assets
def make_assets(it):
    d = os.path.join(ASSETS, f"{it['idx']:02d}_{it['key']}")
    os.makedirs(d, exist_ok=True)
    sprites = []   # (file, x, y, t0, t1, x_expr)

    def add(img, name, x, y, t0, t1, xe=None):
        p = os.path.join(d, name)
        img.save(p)
        sprites.append((p, int(x), int(y), t0, t1, xe))
    ev, D, k = it["ev"], it["D"], it["kind"]
    img, x, y = ui.corner_left(it["idx"], it["total"], k, it.get("label"))
    add(img, "corner_left.png", x, y, 0, D + 1)
    img, x, y = ui.corner_logo()
    add(img, "logo.png", x, y, 0, D + 1)
    it["n_static"] = len(sprites)

    def pop_in(img, x, y, t0, name, t1=D + 1):
        cx, cy = x + img.width / 2, y + img.height / 2
        for j, f in enumerate(ui.pop_frames(img)):
            add(f, f"{name}_pop{j}.png", cx - f.width / 2, cy - f.height / 2, t0 + j / S.FPS, t0 + (j + 1) / S.FPS - 1e-4)
        add(img, f"{name}.png", x, y, t0 + 5 / S.FPS, t1)
    if k in ("song", "bonus"):
        img, x, y = ui.panel_guess(k, it.get("label"))
        add(img, "panel_guess.png", x, y, S.INTRO_S if it["first"] else 0, ev["reveal"])
        for n in range(ev["count"], 0, -1):
            img, x, y = ui.countdown(n, ev["count"])
            t0 = ev["cd"] + (ev["count"] - n)
            add(img, f"cd{n}.png", x, y, t0, t0 + 1)
        img, x, y = ui.panel_answer(it["title"], it.get("extra"))
        pop_in(img, x, y, ev["reveal"], "panel_answer", ev.get("endscreen", D + 1))   # the end screen replaces it
    elif k == "race":
        img, x, y = ui.panel_race_start(it["colors"], it["sub"])
        add(img, "panel_race.png", x, y, 0, ev["prompt_end"])
        img, x, y = ui.chip_race(it["colors"])
        add(img, "chip.png", x, y, ev["prompt_end"], ev["end"])
        img, x, y = ui.panel_race_end()
        pop_in(img, x, y, ev["end"], "panel_end")
    elif k == "run":
        img, x, y = ui.banner(it["prompt"])
        add(img, "banner.png", x, y, 0, ev.get("reveal", D + 1))
        if ev.get("reveal") is not None:
            img, x, y = ui.run_reveal(it["answer"], "heart" if it.get("answer_icon") else
                                      ("marble" if it.get("answer_color") else None), it.get("answer_color"))
            pop_in(img, x, y, ev["reveal"], "reveal")
    it["n_panels"] = len(sprites)
    if it.get("next"):
        u = ui.upnext(it["next"], gold=it["next"].startswith("SECRET"))
        x0, t0 = S.W - 40 - u.width, ev["upnext"]
        add(u, "upnext.png", x0, S.UPNEXT_Y - u.height // 2, t0, D + 1, f"max({x0},{S.W}-(t-{t0:.4f})*3200)")
    if it["first"]:
        add(ui.intro_overlay(), "intro.png", 0, 0, 0, S.INTRO_S)
    if k == "bonus":
        add(ui.endscreen_overlay(), "endscreen.png", 0, 0, ev["endscreen"], D + 1)
    it["sprites"] = sprites
    for c in (it["color_in"], it["color_out"]):
        td = os.path.join(ASSETS, f"trans_{c.lstrip('#')}")
        if not os.path.exists(os.path.join(td, f"uncover_{T - 1:02d}.png")):
            os.makedirs(td, exist_ok=True)
            cov, unc = ui.transition_frames(c)
            for j, (a, b) in enumerate(zip(cov, unc)):
                a.save(os.path.join(td, f"cover_{j:02d}.png"), compress_level=1)
                b.save(os.path.join(td, f"uncover_{j:02d}.png"), compress_level=1)
    it["trans_in"] = os.path.join(ASSETS, f"trans_{it['color_in'].lstrip('#')}")
    it["trans_out"] = os.path.join(ASSETS, f"trans_{it['color_out'].lstrip('#')}")


# ----------------------------------------------------------------------------------------------- base picture
def pieces_graph(label_in, pcs, out):
    g = []
    if len(pcs) == 1:
        a, b, _ = pcs[0]
        g.append(f"[{label_in}]trim=start_frame={a}:end_frame={b},setpts=PTS-STARTPTS[{out}]")
    else:
        g.append(f"[{label_in}]split={len(pcs)}" + "".join(f"[{out}p{j}]" for j in range(len(pcs))))
        for j, (a, b, k) in enumerate(pcs):
            g.append(f"[{out}p{j}]trim=start_frame={a}:end_frame={b},setpts=(PTS-STARTPTS)/{k}[{out}q{j}]")
        g.append("".join(f"[{out}q{j}]" for j in range(len(pcs))) + f"concat=n={len(pcs)}:v=1:a=0[{out}]")
    return g


def crop_keys(it):
    fr = it.get("frame", {})
    if "keys" in fr:
        return [(t, f * track.SRC_H) for t, f in fr["keys"]]
    cache = os.path.join(ASSETS, f"track_{it['key']}.json")
    if os.path.exists(cache):
        keys = [tuple(k) for k in json.load(open(cache))]
        if "tail" in fr:
            keys = [k for k in keys if k[0] < fr["tail"][0][0] - 0.6] + [(t, f * track.SRC_H) for t, f in fr["tail"]]
        return keys
    keys = track.follow_colors(it["path"], fr["track"])
    json.dump(keys, open(cache, "w"))
    if "tail" in fr:
        keys = [k for k in keys if k[0] < fr["tail"][0][0] - 0.6] + [(t, f * track.SRC_H) for t, f in fr["tail"]]
    return keys


def vcam_input(it):
    """The round's picture through the virtual camera, rendered once into build/reframe/ (about 3 min for 30 s)."""
    keys = it["frame"]["vcam"]
    out = os.path.join(S.BUILD, "reframe", f"{it['key']}.mp4")
    sig = out + ".json"
    want = json.dumps([it["path"], keys, it["te_f"]])
    if not (os.path.exists(out) and os.path.exists(sig) and open(sig).read() == want):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        print(f"  vcam {it['key']}", flush=True)
        vcam.render(it["path"], out, keys, t_end=it["te_f"] / S.FPS + 1.0)
        open(sig, "w").write(want)
    return out


def base_graph(it):
    """Filters that turn input 0 into a 1920x1080 [base] stream for this round."""
    fr = it.get("frame", {})
    if it["src"][0] == "wide" or "vcam" in fr:
        g = pieces_graph("0:v", it["pieces"], "src")
        g.append("[src]fps=30,settb=1/30,format=yuv420p[base]")
    elif "track" in fr or "keys" in fr:
        y = track.keyframes_expr(crop_keys(it))
        g = [f"[0:v]crop=1080:{track.WIN_H}:0:'{y}'[cr]"] + pieces_graph("cr", it["pieces"], "src")
        g.append("[src]fps=30,settb=1/30,scale=1920:1080:flags=lanczos,unsharp=5:5:0.55:5:5:0,format=yuv420p[base]")
    elif "split" in fr:
        yl, yr = fr["split"]
        g = pieces_graph("0:v", it["pieces"], "src")
        g.append("[src]fps=30,settb=1/30,split=2[sa][sb]")
        g.append(f"[sa]crop=960:1080:60:{yl}[sl]")
        g.append(f"[sb]crop=960:1080:60:{yr}[sr]")
        g.append("[sl][sr]hstack=inputs=2,drawbox=x=955:y=0:w=10:h=1080:color=white@0.92:t=fill,format=yuv420p[base]")
    elif fr.get("extend"):
        g = pieces_graph("0:v", it["pieces"], "src")
        g.append("[src]fps=30,settb=1/30,scale=608:1080:flags=lanczos,pad=1920:1080:656:0,"
                 "fillborders=left=656:right=656:mode=smear,split=2[ea][eb]")
        g.append("[ea]boxblur=26:2[eblur]")
        g.append("[eb]crop=608:1080:656:0[ecen]")
        g.append("[eblur][ecen]overlay=656:0,format=yuv420p[base]")
    else:
        sys.exit(f"{it['key']}: no frame rule for a vertical Short")
    return g


def eq_window(it):
    ev, D = it["ev"], it["D"]
    if it["kind"] in ("song", "bonus"):
        return ev["reveal"] + 0.2, (ev["endscreen"] if "endscreen" in ev else D + 1)
    return None


def render_segment(it):
    out = os.path.join(SEGS, f"seg_{it['idx']:02d}.mp4")
    if os.path.exists(out) and not FORCE:
        return out
    audio, lev, env = prepare_audio(it)
    wg = WG.Widgets(it, lev, env)
    vin = vcam_input(it) if "vcam" in it.get("frame", {}) else it["path"]
    inputs = ["-i", vin, "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{wg.W}x{wg.H}", "-r", str(S.FPS),
              "-i", "pipe:0"]
    g = base_graph(it)
    eh, bh, ph = WG.EQ_H, WG.BAR_H, WG.PULSE
    g.append("[1:v]format=yuva420p,settb=1/30,setpts=N/(30*TB),split=3[w1][w2][w3]")
    g.append(f"[w1]crop={WG.EQ_W}:{eh}:0:0[weq]")
    g.append(f"[w2]crop={WG.BAR_W}:{bh}:0:{eh}[wbar]")
    g.append(f"[w3]crop={ph}:{ph}:0:{eh + bh}[wpm]")
    bx, by = S.BAR["cx"] - WG.BAR_W // 2, S.BAR["y"] - bh // 2
    g.append(f"[base][wbar]overlay=x={bx}:y={by}[o0]")
    cur, k = "o0", 2
    sprites = it["sprites"]
    for j, (f, x, y, t0, t1, xe) in enumerate(sprites):
        inputs += ["-i", f]
        g.append(f"[{k}:v]format=yuva420p,{LOOP}[s{j}]")
        xs = f"'{xe}'" if xe else str(x)
        g.append(f"[{cur}][s{j}]overlay=x={xs}:y={y}:enable='between(t,{t0:.4f},{t1:.4f})'[v{j}]")
        cur, k = f"v{j}", k + 1
        if j == it["n_static"] - 1:
            dx, dy = ui.dots_layout(it["total"])[it["total"] if it["kind"] == "bonus" else it["idx"]]
            g.append(f"[{cur}][wpm]overlay=x={int(dx - ph / 2)}:y={int(dy - ph / 2)}[vp]")
            cur = "vp"
        if j == it["n_panels"] - 1:
            win = eq_window(it)
            if win:
                P = S.PANEL
                ex, ey = P["x"] + (P["w"] - WG.EQ_W) // 2, P["y"] + P["h"] - WG.EQ_H - 22
                g.append(f"[{cur}][weq]overlay=x={ex}:y={ey}:enable='between(t,{win[0]:.4f},{win[1]:.4f})'[veq]")
                cur = "veq"
            else:
                g.append("[weq]nullsink")
    if not it["first"]:
        inputs += ["-framerate", str(S.FPS), "-i", os.path.join(it["trans_in"], "uncover_%02d.png")]
        g.append(f"[{k}:v]format=yuva420p,settb=1/30,setpts=N/(30*TB)[uin]")
        g.append(f"[{cur}][uin]overlay=0:0:eof_action=pass:enable='lt(t,{T / S.FPS:.4f})'[xin]")
        cur, k = "xin", k + 1
    if not it["last"]:
        inputs += ["-framerate", str(S.FPS), "-i", os.path.join(it["trans_out"], "cover_%02d.png")]
        g.append(f"[{k}:v]format=yuva420p,tpad=start={it['N'] - T}:color=black@0,settb=1/30,setpts=N/(30*TB)[cout]")
        g.append(f"[{cur}][cout]overlay=0:0:eof_action=pass:enable='gte(t,{(it['N'] - T) / S.FPS - 0.001:.4f})'[xout]")
        cur, k = "xout", k + 1
    g.append(f"[{cur}]format=yuv420p[vout]")
    script = os.path.join(SEGS, f"seg_{it['idx']:02d}.filter")
    open(script, "w").write(";\n".join(g))
    tmp = out + ".part.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex_script", script, "-map", "[vout]",
           "-frames:v", str(it["N"]), "-c:v", "libx264", "-preset", S.PRESET, "-crf", str(S.CRF), "-profile:v", "high",
           "-level:v", "4.1", "-pix_fmt", "yuv420p", "-g", "60", "-r", str(S.FPS), "-an", tmp]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for f in range(it["N"]):
            proc.stdin.write(wg.frame(f))
        proc.stdin.close()
    except BrokenPipeError:
        pass
    if proc.wait() != 0:
        sys.exit(f"{it['key']}: ffmpeg failed (filter script {script})")
    n = int(subprocess.check_output(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                                     "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", tmp]).strip())
    if n != it["N"]:
        sys.exit(f"{it['key']}: rendered {n} frames, expected {it['N']}")
    os.replace(tmp, out)
    return out


# ----------------------------------------------------------------------------------------------- audio
def load_wav(path):
    from scipy.signal import resample_poly
    import wave
    w = wave.open(path)
    a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    if w.getnchannels() == 2:
        a = a.reshape(-1, 2).mean(1)
    if w.getframerate() != S.SR:
        a = resample_poly(a, S.SR, w.getframerate()).astype(np.float32)
    return a


def item_audio(it):
    pcs = it["pieces"]
    g = ["[0:a]aresample=48000,aformat=sample_fmts=flt:channel_layouts=stereo,asplit=%d" % len(pcs)
         + "".join(f"[p{j}]" for j in range(len(pcs)))]
    for j, (a, b, k) in enumerate(pcs):
        tempo = f",atempo={k}" if k != 1.0 else ""
        g.append(f"[p{j}]atrim=start={a / S.FPS:.6f}:end={b / S.FPS:.6f},asetpts=PTS-STARTPTS{tempo}[q{j}]")
    g.append("".join(f"[q{j}]" for j in range(len(pcs))) + f"concat=n={len(pcs)}:v=0:a=1[a]")
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", it["path"], "-filter_complex", ";".join(g),
                                   "-map", "[a]", "-f", "f32le", "-"])
    a = np.frombuffer(raw, np.float32).reshape(-1, 2).copy()
    n = it["N"] * S.SPF
    return a[:n] if len(a) >= n else np.vstack([a, np.zeros((n - len(a), 2), np.float32)])


def loudness(a):
    p = os.path.join(S.BUILD, "tmp_lufs.f32")
    a.astype(np.float32).tofile(p)
    o = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-f", "f32le", "-ar", str(S.SR), "-ac", "2", "-i", p,
                        "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    os.remove(p)
    v = re.findall(r"I:\s+(-?[\d.]+) LUFS", o)
    return float(v[-1]) if v else None


def gain_to(a, target):
    l = loudness(a)
    if l is None or l < -70:
        return a, l, 0.0
    return a * np.float32(10 ** ((target - l) / 20)), l, target - l


def bed_track(name, n):
    loops = [load_wav(os.path.join(S.SFX_DIR, f)) for f in S.BEDS[name]]
    parts, total, i = [], 0, 0
    while total < n:
        parts.append(loops[i % len(loops)])
        total += len(parts[-1])
        i += 1
    b = np.concatenate(parts)[:n].copy()
    fi, fo = int(S.BED_FADE_IN_S * S.SR), int(S.BED_FADE_OUT_S * S.SR)
    b[:fi] *= np.linspace(0, 1, fi, dtype=np.float32)
    b[-fo:] *= np.linspace(1, 0, fo, dtype=np.float32)
    return np.stack([b, b], 1)


def prepare_audio(it):
    """The round's finished audio (cut, sped up, music bed under SFX-only rounds, loudness, fades) and its widget
    features, cached in build/audio so the widgets and the final mix use the same samples."""
    os.makedirs(AUD, exist_ok=True)
    base = os.path.join(AUD, f"item_{it['idx']:02d}")
    sig = json.dumps([it["path"], it["pieces"], it["N"], it.get("bed"), S.TARGET_LUFS, S.BED_LUFS, S.BED_SFX_LUFS])
    if os.path.exists(base + ".json") and json.load(open(base + ".json")).get("sig") == sig and not FORCE:
        z = np.load(base + "_feat.npz")
        return np.fromfile(base + ".f32", np.float32).reshape(-1, 2), z["lev"], z["env"]
    a = item_audio(it)
    info = {"sig": sig}
    if it.get("bed"):
        a, info["sfx_lufs"], _ = gain_to(a, S.BED_SFX_LUFS)
        b, info["bed_raw_lufs"], _ = gain_to(bed_track(it["bed"], len(a)), S.BED_LUFS)
        a = a + b
    a, info["lufs"], info["gain"] = gain_to(a, S.TARGET_LUFS)
    fi, fo = int(S.FADE_IN_S * S.SR), int((1.2 if it["last"] else S.FADE_OUT_S) * S.SR)
    a[:fi] *= np.linspace(0, 1, fi, dtype=np.float32)[:, None]
    a[-fo:] *= np.linspace(1, 0, fo, dtype=np.float32)[:, None]
    a = a.astype(np.float32)
    a.tofile(base + ".f32")
    lev, env = WG.features(a)
    np.savez(base + "_feat.npz", lev=lev, env=env)
    json.dump(info, open(base + ".json", "w"))
    return a, lev, env


def build_audio(items):
    total = sum(it["N"] for it in items) * S.SPF
    mix = np.zeros((total, 2), np.float32)
    sfx = {n: load_wav(os.path.join(S.SFX_DIR, f)) * np.float32(10 ** (g / 20)) for n, (f, g) in S.SFX.items()}

    def add(name, t_sec):
        i0 = int(round(t_sec * S.SR))
        if 0 <= i0 < total:
            s = sfx[name][: total - i0]
            mix[i0:i0 + len(s)] += s[:, None]
    for it in items:
        a, _, _ = prepare_audio(it)
        info = json.load(open(os.path.join(AUD, f"item_{it['idx']:02d}.json")))
        i0 = it["start"] * S.SPF
        mix[i0:i0 + len(a)] += a
        t0, ev = it["start"] / S.FPS, it["ev"]
        if not it["first"]:
            add("pop", t0)
            add("whoosh", t0 - T / S.FPS - 0.05)
        if "count" in ev:
            for n in range(min(3, ev["count"]), 0, -1):
                add("tick", t0 + ev["cd"] + ev["count"] - n)
        if "reveal" in ev:
            add("ding", t0 + ev["reveal"])
        if "end" in ev:
            add("pop", t0 + ev["end"])
        if "upnext" in ev:
            add("whoosh", t0 + ev["upnext"] - 0.05)
        if it["first"]:
            add("pop", t0 + S.INTRO_S)
        if "endscreen" in ev:
            add("pop", t0 + ev["endscreen"])
        print(f"  audio {it['key']:14s} {info.get('lufs', float('nan')):6.1f} LUFS gain {info.get('gain', 0):+5.1f} dB"
              + (f"  bed {it['bed']}" if it.get("bed") else ""))
    p = os.path.join(S.BUILD, "mix.f32")
    mix.tofile(p)
    return p


# ----------------------------------------------------------------------------------------------- outputs
def chapters(items):
    out = []
    for it in items:
        name = {"song": "Guess the song", "race": "Marble race: pick your color", "run": "Marble run",
                "bonus": "BONUS: a brand-new song"}[it["kind"]]
        if it.get("label"):
            name = it["label"].title().rstrip("!") + ": guess the song"
        prefix = "" if it["kind"] == "bonus" else f"Round {it['idx'] + 1}: "
        out.append(f"{fmt_t(it['start'] / S.FPS)} {prefix}{name}")
    return out


def mux(items, audio):
    lst = os.path.join(SEGS, "list.txt")
    with open(lst, "w") as f:
        for it in items:
            f.write(f"file 'seg_{it['idx']:02d}.mp4'\n")
    out = os.path.join(S.BUILD, S.OUT_NAME)
    lim = 10 ** (S.LIMIT_DBFS / 20)
    sh(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-f", "f32le", "-ar", str(S.SR),
        "-ac", "2", "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
        "-af", f"alimiter=limit={lim:.4f}:attack=3:release=60:level=false", "-c:a", "aac", "-b:a", S.AUDIO_BITRATE,
        "-ar", str(S.SR), "-movflags", "+faststart", out])
    return out


def render_wide():
    """Makes every missing 16:9 template render in ITEMS, one after another (6-9 min each on 2 cores)."""
    for it in S.ITEMS:
        if it["src"][0] != "wide":
            continue
        _, tpl, song = it["src"]
        tdir = os.path.join(S.PROPS, tpl)
        bdir = os.path.join(tdir, S.WIDE_BUILD)
        if [f for f in glob.glob(os.path.join(bdir, song, "*.mp4")) if not os.path.basename(f).startswith("part")]:
            continue
        print(f"16:9 render: {tpl} {song}", flush=True)
        env = dict(os.environ, MARBLE_RES="1920x1080", MARBLE_CAM="wide", BUILD_DIR=bdir, WATERMARK="")
        subprocess.run([sys.executable, "make_video.py", song, "--no-thumb"], cwd=tdir, env=env, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--render-wide", action="store_true", help="first make the missing 16:9 template renders")
    args = ap.parse_args()
    if args.render_wide:
        render_wide()
    os.makedirs(SEGS, exist_ok=True)
    items = plan()
    print_plan(items)
    if args.plan:
        return
    sel = [int(x) for x in args.only.split(",") if x != ""] or list(range(len(items)))
    for it in items:
        if it["idx"] in sel and it["path"]:
            make_assets(it)
            print(f"render {it['idx']:2d} {it['key']} ({it['N']} frames)", flush=True)
            render_segment(it)
    if args.only:
        return
    out = mux(items, build_audio(items))
    ch = chapters(items)
    open(os.path.join(S.BUILD, "chapters.txt"), "w").write("\n".join(ch) + "\n")
    json.dump([{k: v for k, v in it.items() if k in ("idx", "key", "kind", "start", "N", "D", "ev", "ts_f", "te_f", "f0",
                                                     "pieces", "path")} for it in items],
              open(os.path.join(S.BUILD, "plan.json"), "w"), indent=1, default=str)
    subprocess.run([sys.executable, os.path.join(HERE, "youtube_copy.py")], check=True, stdout=subprocess.DEVNULL)
    print(out)
    print("\n".join(ch))


if __name__ == "__main__":
    main()
