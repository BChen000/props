#!/usr/bin/env python3
"""Long-form Marble Pop compilation: stitches vertical Shorts into one 16:9 "Guess the Marble Song" game video.

Usage:
  python3 build.py                 # everything -> build/<OUT_NAME> + chapters.txt + plan.json
  python3 build.py --plan          # print the timeline only
  python3 build.py --stills 0,4    # render UI assets and one still per listed round (build/still_XX.png)
  python3 build.py --only 3        # render one round's segment (build/segs/seg_03.mp4)
Rounds already rendered in build/segs are reused; delete a segment (or set FORCE=1) to redo it.
"""
import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import settings as S  # noqa: E402
import ui  # noqa: E402

FORCE = os.environ.get("FORCE") == "1"
T = S.TRANSITION_FRAMES
ASSETS = os.path.join(S.BUILD, "assets")
SEGS = os.path.join(S.BUILD, "segs")


def sh(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def probe_vdur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                          "stream=duration", "-of", "default=nw=1:nk=1", p]).strip())


def resolve(item):
    if item["file"] == "BONUS":
        p = os.path.abspath(S.BONUS_FILE)
        if not os.path.exists(p):
            sys.exit(f"bonus video missing: {p} (render it with ../marble-stairs-song first, or set BONUS_FILE)")
        return p
    hits = sorted(f for f in os.listdir(S.SHORTS_DIR) if fnmatch.fnmatch(f, item["file"]))
    if len(hits) != 1:
        sys.exit(f"{item['key']}: pattern {item['file']} matched {hits} in {S.SHORTS_DIR}")
    return os.path.join(S.SHORTS_DIR, hits[0])


# ----------------------------------------------------------------------------------------------- plan
def plan():
    items, start = [], 0
    n = len(S.ITEMS)
    total_rounds = sum(1 for it in S.ITEMS if it["kind"] != "bonus")
    for i, it in enumerate(S.ITEMS):
        it = dict(it)
        it["idx"] = i
        it["path"] = resolve(it)
        vdur = probe_vdur(it["path"])
        ts = it["ts"] if "ts" in it else max(0.0, it["f0"] - 0.45)
        ts_f = int(round(ts * S.FPS))
        te_f = min(int(round(it["te"] * S.FPS)), int(vdur * S.FPS + 1e-6))
        pieces, cur = [], ts_f
        for a, b, k in it.get("speed", []):
            a_f, b_f = int(round(a * S.FPS)), int(round(b * S.FPS))
            pieces += [(cur, a_f, 1.0), (a_f, b_f, k)]
            cur = b_f
        pieces.append((cur, te_f, 1.0))
        frames = sum((b - a) / k for a, b, k in pieces)
        N = int(np.floor(frames)) - 1
        it.update(ts_f=ts_f, te_f=te_f, pieces=pieces, N=N, start=start, D=N / S.FPS, vdur=vdur,
                  first=i == 0, last=i == n - 1, total=total_rounds)

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
            ev["end"] = local(it["end_t"])
        if not it["last"]:
            ev["upnext"] = it["D"] - S.UPNEXT_LEAD_S
        if it["kind"] == "bonus":
            ev["endscreen"] = it["D"] - S.END_SCREEN_S
        it["ev"] = ev
        items.append(it)
        start += N
    for i, it in enumerate(items):
        nxt = items[i + 1] if i + 1 < n else None
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
        print(f"{it['idx']:2d} {fmt_t(it['start'] / S.FPS):>5} {it['key']:18s} {it['kind']:5s} {it['mode']:4s} "
              f"src {it['ts_f'] / S.FPS:5.2f}-{it['te_f'] / S.FPS:5.2f} -> {it['D']:5.2f}s  {ev}")


# ----------------------------------------------------------------------------------------------- assets
def grab(path, t):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1",
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
    return Image.frombytes("RGB", (1080, 1920), raw[:1080 * 1920 * 3])


def make_assets(it):
    d = os.path.join(ASSETS, f"{it['idx']:02d}_{it['key']}")
    os.makedirs(d, exist_ok=True)
    lay = ui.Layout(it["mode"])
    it["lay"] = lay
    t_bg = (it["ts_f"] + 0.7 * (it["te_f"] - it["ts_f"])) / S.FPS
    bg = ui.backdrop(grab(it["path"], t_bg))
    base, static_ui = ui.static_layer(it, lay, it["idx"], it["total"], bg)
    if it["kind"] == "run" and it.get("hint"):
        hint = ui.layer(S.W, S.H)
        ui.draw_text(hint, it["hint"], lay.lx, 880, "xb", 36, (255, 255, 255), stroke=5)
        static_ui.alpha_composite(ui.down(hint))
    ui.compose_static(base, static_ui).save(os.path.join(d, "static.png"))
    sprites = []   # (file, x, y, t0, t1, x_expr)

    def save(img, name):
        p = os.path.join(d, name)
        img.save(p)
        return p
    ev, D = it["ev"], it["D"]
    if it["kind"] in ("song", "bonus"):
        sp, x, y = ui.song_prompt(lay, it["kind"])
        sprites.append((save(sp, "prompt.png"), x, y, 0, ev["reveal"], None))
        for k in range(ev["count"], 0, -1):
            cdi = ui.countdown(lay, k, ev["count"])
            t0 = ev["cd"] + (ev["count"] - k)
            sprites.append((save(cdi, f"cd{k}.png"), lay.lx - cdi.width // 2, 690 - cdi.height // 2, t0, t0 + 1, None))
        block = ui.answer_block(lay, it["title"], it.get("extra"), points=it["kind"] == "song")
        bx, by = 0, 330
    elif it["kind"] == "run" and ev.get("reveal") is not None:
        if it.get("icon") == "question":
            q = ui.layer(300, 300)
            ui.paste_center(q, ui.marble(110 * ui.SS, S.YELLOW), 150 * ui.SS, 150 * ui.SS)
            ui.draw_text(q, "?", 150, 156, "blk", 150, ui.rgb(S.INK), shadow=False, anchor="mm")
            q = ui.down(q)
            sprites.append((save(q, "question.png"), lay.lx - 150, 660 - 150, 0, ev["reveal"], None))
        block = ui.answer_block(lay, it["answer"], header="IT'S...", icon="heart" if it.get("answer_icon") else
                                ("marble" if it.get("answer_color") else None), color=it.get("answer_color"))
        bx, by = 0, 440
    else:
        block = None
    if block is not None:
        t0 = ev["reveal"]
        cx, cy = bx + block.width / 2, by + block.height / 2
        for j, f in enumerate(ui.pop_frames(block)):
            sprites.append((save(f, f"pop{j}.png"), int(cx - f.width / 2) // 2 * 2, int(cy - f.height / 2) // 2 * 2,
                            t0 + j / S.FPS, t0 + (j + 1) / S.FPS - 1e-4, None))
        sprites.append((save(block, "answer.png"), bx, by, t0 + 5 / S.FPS, D + 1, None))
    if it["kind"] == "race":
        e = ui.race_end(lay)
        sprites.append((save(e, "race_end.png"), 0, 790, ev["end"], D + 1, None))
    if it.get("next"):
        u = ui.upnext(it["next"], gold=it["next"].startswith("SECRET"))
        x0 = int(lay.rx - u.width / 2)
        t0 = ev["upnext"]
        sprites.append((save(u, "upnext.png"), x0, 870 - u.height // 2, t0, D + 1,
                        f"max({x0},{S.W}-(t-{t0:.4f})*3200)"))
    if it["first"]:
        sprites.append((save(ui.intro_overlay(lay, bg), "intro.png"), 0, 0, 0, S.INTRO_S, None))
    if it["kind"] == "bonus":
        sprites.append((save(ui.endscreen_overlay(lay, bg), "endscreen.png"), 0, 0, ev["endscreen"], D + 1, None))
    it["sprites"] = sprites
    it["static"] = os.path.join(d, "static.png")
    mask = os.path.join(ASSETS, f"mask_{it['mode']}.png")
    if not os.path.exists(mask):
        ui.card_mask(lay).save(mask)
    it["mask"] = mask
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


# ----------------------------------------------------------------------------------------------- video
def still_frame(it, t):
    """Composite one frame in Python (same layers as the ffmpeg graph) to check the layout."""
    lay = it["lay"]
    src_t = None
    acc = 0.0
    for a, b, k in it["pieces"]:
        seg = (b - a) / k / S.FPS
        if t <= acc + seg:
            src_t = a / S.FPS + (t - acc) * k
            break
        acc += seg
    fr = grab(it["path"], src_t if src_t is not None else it["te_f"] / S.FPS - 0.1)
    cy = it.get("crop_y", 0) if it["mode"] == "zoom" else 0
    card = fr.crop((0, cy, 1080, cy + lay.crop_h)).resize((lay.cw, S.CARD_H), Image.BICUBIC).convert("RGBA")
    card.putalpha(Image.open(it["mask"]))
    out = Image.open(it["static"]).convert("RGBA")
    out.alpha_composite(card, (lay.cx, S.CARD_Y))
    for f, x, y, t0, t1, xe in it["sprites"]:
        if t0 <= t < t1:
            out.alpha_composite(Image.open(f).convert("RGBA"), (int(x), int(y)))
    return out.convert("RGB")


def render_segment(it):
    out = os.path.join(SEGS, f"seg_{it['idx']:02d}.mp4")
    if os.path.exists(out) and not FORCE:
        return out
    lay = it["lay"]
    inputs = ["-i", it["path"], "-i", it["static"], "-i", it["mask"]]
    g = []
    loop = "loop=loop=-1:size=1:start=0,setpts=N/(30*TB),settb=1/30"
    pcs = it["pieces"]
    if len(pcs) == 1:
        a, b, _ = pcs[0]
        g.append(f"[0:v]trim=start_frame={a}:end_frame={b},setpts=PTS-STARTPTS[src]")
    else:
        g.append(f"[0:v]split={len(pcs)}" + "".join(f"[p{j}]" for j in range(len(pcs))))
        for j, (a, b, k) in enumerate(pcs):
            g.append(f"[p{j}]trim=start_frame={a}:end_frame={b},setpts=(PTS-STARTPTS)/{k}[q{j}]")
        g.append("".join(f"[q{j}]" for j in range(len(pcs))) + f"concat=n={len(pcs)}:v=1:a=0[src]")
    crop = f"crop=1080:{lay.crop_h}:0:{it.get('crop_y', 0)}," if it["mode"] == "zoom" else ""
    g.append(f"[src]fps=30,settb=1/30,{crop}scale={lay.cw}:{S.CARD_H}:flags=bicubic,format=yuva420p[c0]")
    g.append(f"[2:v]format=gray,{loop}[m]")
    g.append("[c0][m]alphamerge[card]")
    g.append(f"[1:v]format=yuv420p,{loop}[bg]")
    g.append(f"[bg][card]overlay=x={lay.cx}:y={S.CARD_Y}:shortest=1[v0]")
    cur, k = "v0", 3
    for j, (f, x, y, t0, t1, xe) in enumerate(it["sprites"]):
        inputs += ["-i", f]
        g.append(f"[{k}:v]format=yuva420p,{loop}[s{j}]")
        xs = f"'{xe}'" if xe else str(int(x))
        g.append(f"[{cur}][s{j}]overlay=x={xs}:y={int(y)}:enable='between(t,{t0:.4f},{t1:.4f})'[v{j + 1}]")
        cur = f"v{j + 1}"
        k += 1
    if not it["first"]:
        inputs += ["-framerate", str(S.FPS), "-i", os.path.join(it["trans_in"], "uncover_%02d.png")]
        g.append(f"[{k}:v]format=yuva420p,settb=1/30,setpts=N/(30*TB)[uin]")
        g.append(f"[{cur}][uin]overlay=0:0:eof_action=pass:enable='lt(t,{T / S.FPS:.4f})'[xin]")
        cur, k = "xin", k + 1
    if not it["last"]:
        inputs += ["-framerate", str(S.FPS), "-i", os.path.join(it["trans_out"], "cover_%02d.png")]
        g.append(f"[{k}:v]format=yuva420p,tpad=start={it['N'] - T}:color=black@0,settb=1/30,setpts=N/(30*TB)[cout]")
        g.append(f"[{cur}][cout]overlay=0:0:eof_action=pass:"
                 f"enable='gte(t,{(it['N'] - T) / S.FPS - 0.001:.4f})'[xout]")
        cur, k = "xout", k + 1
    g.append(f"[{cur}]format=yuv420p[vout]")
    script = os.path.join(SEGS, f"seg_{it['idx']:02d}.filter")
    open(script, "w").write(";\n".join(g))
    tmp = out + ".part.mp4"
    sh(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex_script", script, "-map", "[vout]",
        "-frames:v", str(it["N"]), "-c:v", "libx264", "-preset", S.PRESET, "-crf", str(S.CRF), "-profile:v", "high",
        "-level:v", "4.1", "-pix_fmt", "yuv420p", "-g", "60", "-r", str(S.FPS), "-an", tmp])
    n = int(subprocess.check_output(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                                     "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", tmp]).strip())
    if n != it["N"]:
        sys.exit(f"{it['key']}: rendered {n} frames, expected {it['N']}")
    os.replace(tmp, out)
    return out


# ----------------------------------------------------------------------------------------------- audio
def load_sfx():
    from scipy.signal import resample_poly
    import wave
    out = {}
    for name, (fn, gain) in S.SFX.items():
        w = wave.open(os.path.join(S.SFX_DIR, fn))
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        if w.getnchannels() == 2:
            a = a.reshape(-1, 2).mean(1)
        if w.getframerate() != S.SR:
            a = resample_poly(a, S.SR, w.getframerate()).astype(np.float32)
        out[name] = a * 10 ** (gain / 20)
    return out


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
    a = a[:n] if len(a) >= n else np.vstack([a, np.zeros((n - len(a), 2), np.float32)])
    return a


def loudness(a):
    p = os.path.join(S.BUILD, "tmp_lufs.f32")
    a.astype(np.float32).tofile(p)
    o = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-f", "f32le", "-ar", str(S.SR), "-ac", "2", "-i", p,
                        "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    os.remove(p)
    v = re.findall(r"I:\s+(-?[\d.]+) LUFS", o)
    return float(v[-1]) if v else None


def build_audio(items):
    total = sum(it["N"] for it in items) * S.SPF
    mix = np.zeros((total, 2), np.float32)
    sfx = load_sfx()
    report = []

    def add(name, t_sec):
        s = sfx[name]
        i0 = int(round(t_sec * S.SR))
        if i0 >= total:
            return
        seg = s[: total - i0]
        mix[i0:i0 + len(seg)] += seg[:, None]
    for it in items:
        a = item_audio(it)
        lufs = loudness(a)
        gain = 0.0 if lufs is None or lufs < -70 else S.TARGET_LUFS - lufs
        a *= 10 ** (gain / 20)
        fi, fo = int(S.FADE_IN_S * S.SR), int(S.FADE_OUT_S * S.SR)
        a[:fi] *= np.linspace(0, 1, fi, dtype=np.float32)[:, None]
        if not it["last"]:
            a[-fo:] *= np.linspace(1, 0, fo, dtype=np.float32)[:, None]
        else:
            fo2 = int(1.2 * S.SR)
            a[-fo2:] *= np.linspace(1, 0, fo2, dtype=np.float32)[:, None]
        i0 = it["start"] * S.SPF
        mix[i0:i0 + len(a)] += a
        t0, ev = it["start"] / S.FPS, it["ev"]
        if not it["first"]:
            add("pop", t0)
            add("whoosh", t0 - T / S.FPS - 0.05)
        if "count" in ev:
            for k in range(min(3, ev["count"]), 0, -1):
                add("tick", t0 + ev["cd"] + ev["count"] - k)
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
        report.append((it["key"], lufs, gain))
    p = os.path.join(S.BUILD, "mix.f32")
    mix.tofile(p)
    for k, l, g in report:
        print(f"  audio {k:18s} {l if l is not None else float('nan'):6.1f} LUFS  gain {g:+5.1f} dB")
    return p


# ----------------------------------------------------------------------------------------------- outputs
def chapters(items):
    lines = []
    for it in items:
        t = it["start"] / S.FPS
        name = {"song": "Guess the song", "race": "Marble race: pick your color", "run": "Marble run",
                "bonus": "BONUS: a brand-new song"}[it["kind"]]
        if it.get("label"):
            name = it["label"].title().rstrip("!") + ": guess the song"
        if it["kind"] == "bonus":
            lines.append(f"{fmt_t(t)} {name}")
        else:
            lines.append(f"{fmt_t(t)} Round {it['idx'] + 1}: {name}")
    return lines


def mux(items, audio):
    lst = os.path.join(SEGS, "list.txt")
    with open(lst, "w") as f:
        for it in items:
            f.write(f"file 'seg_{it['idx']:02d}.mp4'\n")
    out = os.path.join(S.BUILD, S.OUT_NAME)
    lim = 10 ** (S.LIMIT_DBFS / 20)
    sh(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst,
        "-f", "f32le", "-ar", str(S.SR), "-ac", "2", "-i", audio, "-map", "0:v", "-map", "1:a",
        "-c:v", "copy", "-af", f"alimiter=limit={lim:.4f}:attack=3:release=60:level=false",
        "-c:a", "aac", "-b:a", S.AUDIO_BITRATE, "-ar", str(S.SR), "-movflags", "+faststart", out])
    return out


def make_thumbnail(items):
    by = {it["key"]: it for it in items}
    frames = [grab(by[k]["path"], t) for k, t in S.THUMB_FRAMES]
    th = ui.thumbnail(frames)
    th.save(os.path.join(S.BUILD, "thumbnail.png"))
    th.save(os.path.join(S.BUILD, "thumbnail.jpg"), quality=92)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--stills", default="")
    ap.add_argument("--still-t", default="")
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    os.makedirs(SEGS, exist_ok=True)
    items = plan()
    print_plan(items)
    if args.plan:
        return
    sel = [int(x) for x in (args.stills or args.only).split(",") if x != ""] or list(range(len(items)))
    for it in items:
        if it["idx"] in sel:
            make_assets(it)
    if args.stills:
        ts = [float(x) for x in args.still_t.split(",")] if args.still_t else None
        for i in sel:
            it = items[i]
            for t in (ts or [0.5, it["ev"].get("reveal", it["D"] / 2) - 1.5, it["ev"].get("reveal", 0) + 0.6,
                             it["D"] - 1.0]):
                t = min(max(t, 0), it["D"] - 0.05)
                p = os.path.join(S.BUILD, f"still_{i:02d}_{t:05.2f}.png")
                still_frame(it, t).save(p)
                print(p)
        return
    for it in items:
        if it["idx"] in sel:
            print(f"render {it['idx']:2d} {it['key']} ({it['N']} frames)", flush=True)
            render_segment(it)
    if args.only:
        return
    audio = build_audio(items)
    out = mux(items, audio)
    make_thumbnail(items)
    ch = chapters(items)
    open(os.path.join(S.BUILD, "chapters.txt"), "w").write("\n".join(ch) + "\n")
    json.dump([{k: v for k, v in it.items() if k in ("idx", "key", "kind", "start", "N", "D", "ev", "ts_f", "te_f",
                                                     "pieces", "path")} for it in items],
              open(os.path.join(S.BUILD, "plan.json"), "w"), indent=1, default=str)
    subprocess.run([sys.executable, os.path.join(HERE, "youtube_copy.py")], check=True, stdout=subprocess.DEVNULL)
    print(out)
    print("\n".join(ch))


if __name__ == "__main__":
    main()
