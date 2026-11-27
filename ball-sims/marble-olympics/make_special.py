"""Marble Olympics: the whole long-form special in one command.

  python make_special.py            -> build/marble_olympics_500.mp4, build/thumbnail.png/.jpg, build/copy.txt
                                       (title and description with chapters)
  python make_special.py --plan     -> the running order with start times (no rendering)
  python make_special.py --stills   -> one frame from every segment in build/stills/
  python make_special.py --audio    -> remix the sound and re-mux, keeping build/video_only.mp4
  python make_special.py --thumb    -> build/thumbnail.png/.jpg only (no text, like the channel's thumbnails)
  python make_special.py --style    -> rewrite style.json from settings.py and the last events' results

Renders any missing event with events.py (their templates), then draws the cards and the broadcast frame around each
event at 1920x1080, mixes the cards' music and sounds with the events' own soundtracks, and muxes at -14 LUFS.
"""
import json
import math
import os
import subprocess
import sys

import cairo
import numpy as np

import cards as C
import events as E
import settings as S

sys.path.append(os.path.join(S.BALL_SIMS, "battle-audio"))
import battle_audio as ba  # noqa: E402

FPS, W, H = S.FPS, S.W, S.H
WIPE = 0.5
SR = ba.SR


# --------------------------------------------------------------------------- running order
def plan(results):
    segs = []
    c = S.CARD
    for kind in ("title", "thanks", "teams", "rules"):
        segs.append(dict(kind=kind, dur=c[kind]))
    totals = {t: 0 for t in S.TEAMS}
    winners, history = [], []
    for k, ev in enumerate(S.EVENTS):
        res = results[ev["key"]]
        if ev.get("double") and len(set(totals.values())) == 1:
            segs.append(dict(kind="tied", dur=c["tied"], totals=dict(totals)))
        segs.append(dict(kind="intro", k=k, dur=c["intro"]))
        segs.append(dict(kind="event", k=k, dur=res["win"] + ev.get("keep", S.KEEP_AFTER_WIN), video=res["video"],
                         totals=dict(totals), winners=list(winners)))
        prev = dict(totals)
        for p, tm in enumerate(ev["places"]):
            totals[tm] += S.POINTS[p] * (2 if ev.get("double") else 1)
        winners.append((k, ev["places"][0]))
        history.append(dict(totals))
        segs.append(dict(kind="results", k=k, dur=c["results"]))
        segs.append(dict(kind="standings", k=k, dur=c["standings"], prev=prev, new=dict(totals)))
    order, rk = C.ranks(totals)
    champ = order[0]
    segs.append(dict(kind="champion", dur=c["champion"], champ=champ, totals=dict(totals), story=story(champ, history)))
    segs.append(dict(kind="outro", dur=c["outro"]))
    t = 0
    for s in segs:
        s["n"] = int(round(s["dur"] * FPS))
        s["f0"] = t
        t += s["n"]
    return segs


def story(champ, history):
    before = history[:-1]
    if any(C.ranks(h)[1][champ] == 4 and sum(1 for v in h.values() if v == h[champ]) == 1 for h in before):
        return "From last place to champion!"
    if all(C.ranks(h)[1][champ] == 1 for h in history):
        return "Led from start to finish!"
    return "Won it all in the Grand Final!"


def chapters(segs):
    """YouTube chapters (each must be 10 s or longer, so the tie card opens the Grand Final chapter)."""
    out = []
    for i, s in enumerate(segs):
        if s["kind"] == "title":
            out.append((s["f0"], "Intro"))
        elif s["kind"] == "tied":
            out.append((s["f0"], "Grand Final: 500 Marbles"))
        elif s["kind"] == "intro" and segs[i - 1]["kind"] != "tied":
            ev = S.EVENTS[s["k"]]
            out.append((s["f0"], ("Grand Final: 500 Marbles" if ev.get("double") else
                                  "Event %d: %s" % (s["k"] + 1, ev["name"].title()))))
        elif s["kind"] == "champion":
            out.append((s["f0"], "The Champion"))
    return ["%d:%02d %s" % (f // FPS // 60, f // FPS % 60, n) for f, n in out]


# --------------------------------------------------------------------------- pictures
def draw_card(ctx, s, t, img):
    k = s["kind"]
    if k == "title":
        C.card_title(ctx, t, s["dur"], img)
    elif k == "thanks":
        C.card_thanks(ctx, t, s["dur"], img)
    elif k == "teams":
        C.card_teams(ctx, t, s["dur"])
    elif k == "rules":
        C.card_rules(ctx, t, s["dur"])
    elif k == "intro":
        C.card_intro(ctx, t, s["dur"], s["k"])
    elif k == "results":
        C.podium(ctx, t, s["k"], S.EVENTS[s["k"]]["places"])
    elif k == "standings":
        C.card_standings(ctx, t, s["dur"], s["k"], s["prev"], s["new"])
    elif k == "tied":
        C.card_tied(ctx, t, s["dur"], s["totals"])
    elif k == "champion":
        C.card_champion(ctx, t, s["dur"], s["champ"], s["totals"], s["story"])
    elif k == "outro":
        C.card_outro(ctx, t, s["dur"], img)


def wipe_u(f, segs):
    """Wipe position at global frame f: centred on every segment boundary after the first."""
    for s in segs[1:]:
        d = (f - s["f0"]) / FPS
        if -WIPE / 2 <= d < WIPE / 2:
            return 0.5 + d / WIPE
    return 0.0


def hero_image():
    if not os.path.exists(S.HERO_IMAGE):
        subprocess.run([sys.executable, "make_post.py"], cwd=os.path.dirname(os.path.dirname(S.HERO_IMAGE)),
                       env=dict(os.environ, OUT_SIZE="2160"), check=True)
    return cairo.ImageSurface.create_from_png(S.HERO_IMAGE)


def video_frames(path, n):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", "scale=%d:%d:flags=area" % (S.PANEL_W, H),
                          "-f", "rawvideo", "-pix_fmt", "bgra", "-"], stdout=subprocess.PIPE)
    size = S.PANEL_W * H * 4
    last = None
    for _ in range(n):
        buf = p.stdout.read(size)
        if len(buf) == size:
            last = np.frombuffer(buf, np.uint8).reshape(H, S.PANEL_W, 4)
        yield last
    p.stdout.close()
    p.kill()


def render_video(segs, out, only=None):
    img = hero_image()
    enc = None
    if only is None:
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", "%dx%d" % (W, H),
                                "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", S.PRESET, "-crf", str(S.CRF),
                                "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    frame = np.zeros((H, W, 4), np.uint8)
    surf = cairo.ImageSurface.create_for_data(frame, cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    for si, s in enumerate(segs):
        picks = range(s["n"]) if only is None else [min(s["n"] - 1, int(only * s["n"]))]
        if s["kind"] == "event":
            bg = C.event_frame(s["k"], s["totals"], s["winners"])
            bg.flush()
            bga = np.ndarray((H, W, 4), np.uint8, bg.get_data()).copy()
            src = video_frames(s["video"], s["n"])
        for i in range(s["n"]):
            if s["kind"] == "event":
                v = next(src)
                if i not in picks:
                    continue
                frame[:] = bga
                frame[:, C.PANEL_X:C.PANEL_X + S.PANEL_W] = v
            else:
                if i not in picks:
                    continue
                ctx.save()
                ctx.set_operator(cairo.OPERATOR_SOURCE)
                ctx.set_source_rgba(0, 0, 0, 1)
                ctx.paint()
                ctx.restore()
                draw_card(ctx, s, i / FPS, img)
            u = wipe_u(s["f0"] + i, segs)
            if u > 0:
                surf.mark_dirty()
                C.wipe(ctx, u)
            surf.flush()
            frame[:, :, 3] = 255
            if enc:
                enc.stdin.write(frame.tobytes())
            else:
                from PIL import Image
                os.makedirs(os.path.join(S.BUILD, "stills"), exist_ok=True)
                Image.fromarray(frame[:, :, [2, 1, 0]]).save(os.path.join(S.BUILD, "stills", "%02d_%s.png" % (si, s["kind"])))
            surf.mark_dirty()
        print("segment %2d %-9s %5.1f s done" % (si, s["kind"], s["dur"]), flush=True)
    if enc:
        enc.stdin.close()
        enc.wait()


# --------------------------------------------------------------------------- sound
def event_audio(path, dur):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-t", "%.3f" % dur, "-f", "f32le", "-ac", "2",
                          "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)
    f = int(0.35 * SR)
    if len(x) > f:
        x[-f:] *= np.linspace(1, 0, f)[:, None]
    return x


def sfx_for(s, t0):
    """(time, sound, gain, pan) cues for one card, in absolute seconds."""
    k, cues = s["kind"], []
    if k == "title":
        cues += [(t0 + 0.25, ba.crash(0.5), 0.5, 0), (t0 + 0.25, ba.boom(0.6), 0.6, 0), (t0 + 0.25, ba.fanfare(), 0.8, 0),
                 (t0 + 0.9, ba.pop(0.8), 0.6, 0)]
    elif k == "thanks":
        cues += [(t0 + 0.1, ba.bell_ring(0.7), 0.5, 0)]
    elif k == "teams":
        cues += [(t0 + 0.55 + 0.45 * i, ba.pop(0.9, 700 + 140 * i), 0.7, (i - 1.5) * 0.3) for i in range(4)]
        cues += [(t0 + 2.7, ba.brass_fanfare(0.5), 0.55, 0)]
    elif k == "rules":
        cues += [(t0 + 0.45 + 0.25 * i, ba.ding(0.5, 1318.5 * 2 ** (-i / 12 * 4)), 0.5, 0) for i in range(3)]
        cues += [(t0 + 1.5, ba.clack(0.6), 0.5, 0)]
    elif k == "intro":
        cues += [(t0 + 0.3, ba.taiko(0.9), 0.8, 0), (t0 + 0.32, ba.boom(0.5), 0.5, 0)]
        if S.EVENTS[s["k"]].get("double"):
            cues += [(t0 + 1.5, ba.brass_fanfare(0.6), 0.6, 0)]
    elif k == "results":
        for n in range(3):
            cues += [(t0 + 0.7 + 0.75 * n, ba.ding(0.6, 880 * 2 ** (n * 4 / 12)), 0.55, (n - 1) * 0.3)]
        cues += [(t0 + 2.2, ba.fanfare(), 0.8, 0), (t0 + 3.05, ba.pop(0.5, 500), 0.4, 0.4)]
    elif k == "standings":
        cues += [(t0 + 0.6, ba.sweep_up(1.3, 0.5), 0.5, 0), (t0 + 2.0, ba.ding(0.5), 0.45, 0)]
    elif k == "tied":
        cues += [(t0 + 0.05, ba.boom(0.8), 0.7, 0), (t0 + 0.06, ba.crash(0.5), 0.45, 0)]
        cues += [(t0 + 0.6 + 0.18 * i, ba.pop(0.8, 700 + 140 * i), 0.6, 0) for i in range(4)]
        cues += [(t0 + 2.6, ba.riser(2.6, 0.5), 0.5, 0)]
    elif k == "champion":
        cues += [(t0 + 0.7, ba.crash(0.8), 0.6, 0), (t0 + 0.7, ba.brass_fanfare(0.9), 0.9, 0),
                 (t0 + 1.5, ba.ding(0.7, 1760), 0.5, 0)]
        cues += [(t0 + 2.1, ba.fanfare(), 0.8, 0)]
        cues += [(t0 + 1.9 + 0.32 * i, ba.clap(0.7), 0.65, (-1) ** i * 0.4) for i in range(14)]
    elif k == "outro":
        cues += [(t0 + 0.05, ba.pop(0.7), 0.5, 0), (t0 + 0.6, ba.ding(0.5), 0.4, 0),
                 (t0 + 1.8 + 1.05, ba.click(0.8), 0.6, 0), (t0 + 1.8 + 1.15, ba.bell_ring(0.6), 0.5, 0)]
    return cues


def render_audio(segs, wav):
    ba.reset_rng()
    total = sum(s["n"] for s in segs) / FPS
    n = int((total + 1) * SR)
    L, R = np.zeros(n), np.zeros(n)
    bed = np.zeros(n)
    ev_rms = []
    runs, cur = [], None
    for s in segs:
        t0, t1 = s["f0"] / FPS, (s["f0"] + s["n"]) / FPS
        if s["kind"] == "event":
            x = event_audio(s["video"], s["n"] / FPS)
            i = int(round(t0 * SR))
            m = min(len(x), n - i)
            L[i:i + m] += x[:m, 0]
            R[i:i + m] += x[:m, 1]
            ev_rms.append(np.sqrt(np.mean(x ** 2)))
            cur = None
        else:
            if cur is None:
                cur = [t0, t1]
                runs.append(cur)
            cur[1] = t1
            for (tt, snd, g, pan) in sfx_for(s, t0):
                ba.add_st(L, R, snd, tt, g, pan)
        if s["kind"] != "event":
            pass
    for a, b in runs:
        loop = ba.outro_loop(b - a + 0.2)
        fi, fo = int(0.3 * SR), int(0.5 * SR)
        loop[:fi] *= np.linspace(0, 1, fi)
        loop[-fo:] *= np.linspace(1, 0, fo)
        ba.add(bed, loop, a)
    bed_rms = np.sqrt(np.mean(bed[bed != 0] ** 2)) if np.any(bed) else 1.0
    bed *= S.BED_LEVEL * (np.mean(ev_rms) if ev_rms else 0.1) / bed_rms
    L += bed
    R += bed
    ba.master_and_write(L[:int(total * SR)], R[:int(total * SR)], wav, limit=0.46)


# --------------------------------------------------------------------------- thumbnail (no text, as the channel's)
def thumbnail(img, path):
    surf, ctx = C.new_surface()
    C.hero(ctx, img, 0, 1, dark=0.0, shift=0.456)
    g = cairo.RadialGradient(W / 2, H * 0.42, H * 0.35, W / 2, H * 0.42, W * 0.7)
    g.add_color_stop_rgba(0, 0, 0, 0, 0)
    g.add_color_stop_rgba(1, 0.05, 0.02, 0.1, 0.8)
    ctx.set_source(g)
    ctx.paint()
    from crown_icon import draw_crown_cairo
    draw_crown_cairo(ctx, W / 2, 770, s=4.2, glow=1.6)
    for i, tm in enumerate(S.TEAMS):
        C.ball(ctx, W / 2 + (i - 1.5) * 300 + (i - 1.5) * 60 * (abs(i - 1.5) > 1), 945, 108, tm)
    surf.flush()
    from PIL import Image
    a = np.ndarray((H, W, 4), np.uint8, surf.get_data())[:, :, [2, 1, 0]].copy()
    im = Image.fromarray(a).resize((1280, 720), Image.LANCZOS)
    im.save(path + ".png")
    im.save(path + ".jpg", quality=92)


def write_style(segs, results):
    style = dict(
        prop="marble-olympics",
        canvas=dict(width=W, height=H, fps=FPS, panel_width=S.PANEL_W, crf=S.CRF, preset=S.PRESET,
                    loudness_lufs=S.LOUDNESS[0], bed_level=S.BED_LEVEL),
        teams={t: C.kit_hex(S.TEAM_COLORS[t]) for t in S.TEAMS}, points=S.POINTS, final_multiplier=2,
        events=[dict(e, result=results.get(e["key"], {}).get("places"),
                     win_video_s=round(results.get(e["key"], {}).get("win", 0), 3)) for e in S.EVENTS],
        cards_s=S.CARD, keep_after_win_s=S.KEEP_AFTER_WIN, wipe_s=WIPE,
        running_order=[dict(start_s=round(s["f0"] / FPS, 2), kind=s["kind"], dur_s=round(s["n"] / FPS, 2),
                            event=S.EVENTS[s["k"]]["name"] if "k" in s else None) for s in segs],
        duration_s=round(sum(s["n"] for s in segs) / FPS, 2),
        copy=dict(title=S.YT_TITLE, description=S.YT_DESCRIPTION.format(chapters="\n".join(chapters(segs))),
                  thumbnail="no text: the 500-marble board, a crown and the four team balls"),
    )
    with open(os.path.join(S.HERE, "style.json"), "w", encoding="utf-8") as f:
        json.dump(style, f, indent=1, ensure_ascii=False)
    print("wrote style.json")


def main():
    args = sys.argv[1:]
    os.makedirs(S.BUILD, exist_ok=True)
    saved = os.path.join(S.BUILD, "events", "results.json")
    if ("--plan" in args or "--style" in args) and not os.path.exists(saved):
        sys.exit("no events yet: run python3 events.py first")
    results = json.load(open(saved)) if ("--plan" in args or "--style" in args) else E.main([])
    segs = plan(results)
    total = sum(s["n"] for s in segs) / FPS
    for s in segs:
        print("%6.1f s  %-9s %5.1f s  %s" % (s["f0"] / FPS, s["kind"], s["dur"],
                                            S.EVENTS[s["k"]]["name"] if "k" in s else ""))
    print("total %.1f s = %d:%02d" % (total, total // 60, total % 60))
    copy = os.path.join(S.BUILD, "copy.txt")
    open(copy, "w").write("TITLE\n%s\n\nDESCRIPTION\n%s\n" % (S.YT_TITLE, S.YT_DESCRIPTION.format(
        chapters="\n".join(chapters(segs)))))
    if "--plan" in args:
        print(open(copy).read())
        return
    if "--style" in args:
        return write_style(segs, results)
    if "--stills" in args:
        render_video(segs, None, only=0.6)
        return
    if "--thumb" in args:
        thumbnail(hero_image(), os.path.join(S.BUILD, "thumbnail"))
        return
    vid = os.path.join(S.BUILD, "video_only.mp4")
    wav = os.path.join(S.BUILD, "audio.wav")
    render_audio(segs, wav)
    if "--audio" not in args or not os.path.exists(vid):
        render_video(segs, vid)
    final = os.path.join(S.BUILD, S.OUT_NAME + ".mp4")
    af = ba.loudnorm_filter(wav, *S.LOUDNESS)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", vid, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-af", af, "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                    final], check=True)
    thumbnail(hero_image(), os.path.join(S.BUILD, "thumbnail"))
    print("->", final)


if __name__ == "__main__":
    main()
