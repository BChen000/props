"""Marble Milestone Post: one command for a square image of team-colour marbles spelling a number.

  python make_post.py              -> build/milestone_500.png + .jpg (OUT_SIZE square, no text) + .json (counts)
  SIZE=1080 python make_post.py    -> a quick draft rendered at 1080 (the shipped render is 2160, downsampled)
  python make_post.py --plan       -> layout only: marble count per colour and character, and a top-down plan
  TEXT=10K CAM_X=5 CAM_D=100 python make_post.py   -> another number (see README: Reuse)
  python make_post.py --style      -> rewrite style.json from settings.py and the last build's counts

Lays the marbles out with layout.py, sets them on the funnel board of ../marble-funnel-drain (one character
centred on the hole), and renders a still with that prop's ray-caster.
"""
import json
import math
import os
import sys
import time

os.environ.setdefault("NUMBA_NUM_THREADS", str(os.cpu_count() or 2))
import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import layout as LY  # noqa: E402
import settings as S  # noqa: E402

sys.path.append(S.DRAIN)


def marbles():
    P, g = LY.layout(S.TEXT, S.FONT, S.HEIGHT, S.TRACK, S.SPACING, stroke=S.STROKE, seed=S.LAYOUT_SEED)
    sel = P[g == S.HOLE_IN] if S.HOLE_IN >= 0 else P
    centre = (sel.min(0) + sel.max(0)) / 2.0
    P = P - centre
    col = LY.colour_mix(P, len(S.COLOURS), seed=S.COLOUR_SEED)
    return P, g, col


def plan(P, col, path):
    s = 12.0
    x0, y0 = P.min(0) - 3; x1, y1 = P.max(0) + 3
    im = Image.new("RGB", (int((x1 - x0) * s), int((y1 - y0) * s)), (120, 72, 40))
    d = ImageDraw.Draw(im)
    for (x, y), k in zip(P, col):
        c = tuple(int(255 * min(1.0, v) ** (1 / 2.2)) for v in S.PALETTE[S.COLOURS[k]])
        cx, cy = (x - x0) * s, (y1 - y) * s
        d.ellipse([cx - s, cy - s, cx + s, cy + s], fill=c)
    if S.HOLE_IN >= 0:
        cx, cy = -x0 * s, y1 * s
        r = S.LOOK["RH"] * s
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(0, 0, 0))
    im.save(path)


def render(P, col):
    import render as rd
    rh = S.LOOK["RH"]
    r = np.hypot(P[:, 0], P[:, 1])
    if (r < rh + 1.2).any():
        sys.exit("a marble sits over the hole: centre another character on it (HOLE_IN) or change HEIGHT/TRACK")
    bx = P[:, 0].astype(np.float64).copy()
    by = P[:, 1].astype(np.float64).copy()
    bz = np.array([rd.surf_h(v) + math.sqrt(1.0 + rd.surf_s(v) ** 2) for v in r])
    state = np.ones(len(P), np.int64)
    btype = (col + 1).astype(np.int64)
    bcol = np.array([S.PALETTE[S.COLOURS[k]] for k in col], np.float64)
    c = S.CAM
    cam = rd.make_cam(c["T"], c["D"], c["yaw"], c["elev"], c["hf"])
    xs, ys, _ = zip(*[rd.project(cam, x, y, z) for x, y, z in zip(bx, by, bz)])
    print("text spans x %.0f-%.0f px, y %.0f-%.0f px of %d" % (min(xs), max(xs), min(ys), max(ys), S.SIZE))
    check_frame(rd, cam)
    ren = rd.Renderer(cache_dir=os.path.join(S.BUILD, "cache"))
    t = time.time()
    img = ren.frame(cam, bx, by, bz, state, btype, bcol, None, kd=c["kd"] * S.SIZE / 1080.0, zf=c["D"], grain_seed=5)
    print("rendered %dx%d in %.1f s" % (S.SIZE, S.SIZE, time.time() - t))
    vis = visible(rd, ren, cam, bx, by, bz)
    print("visible: %d of %d marbles show at least half their disc (least visible %.0f%%)"
          % ((vis >= 0.5).sum(), len(vis), 100 * vis.min()))
    if S.OUT_SIZE != S.SIZE:
        img = cv2.resize(img, (S.OUT_SIZE, S.OUT_SIZE), interpolation=cv2.INTER_AREA)
    return img, vis


def check_frame(rd, cam):
    """The board's wood and light maps only cover x -40..40, y -60..70: past that the floor renders blank."""
    x0, y0 = rd.MX0, rd.MY0
    x1, y1 = x0 + rd.NMX * rd.MR, y0 + rd.NMY * rd.MR
    for px in np.linspace(0, S.SIZE, 9):
        for py in (0.0, S.SIZE / 2.0, float(S.SIZE)):
            dx, dy, dz = rd.pixel_ray(cam, px, py)
            t = -cam[2] / dz
            x, y = cam[0] + t * dx, cam[1] + t * dy
            if not (x0 < x < x1 and y0 < y < y1):
                sys.exit("the frame shows the board past its maps at (%.0f, %.0f): lower CAM_D or HEIGHT" % (x, y))


def visible(rd, ren, cam, bx, by, bz):
    """Share of each marble's disc not hidden by nearer marbles or cut by the frame, from the depth buffer:
    the count a viewer can make in a "guess how many marbles" post."""
    out = np.zeros(len(bx))
    for b in range(len(bx)):
        px, py, dep = rd.project(cam, bx[b], by[b], bz[b])
        rp = cam[12] / dep * 0.9
        y, x = np.ogrid[int(py - rp):int(py + rp) + 1, int(px - rp):int(px + rp) + 1]
        disc = (x - px) ** 2 + (y - py) ** 2 <= rp * rp
        inside = (x >= 0) & (x < S.SIZE) & (y >= 0) & (y < S.SIZE)
        zz = ren.zcam[np.clip(y, 0, S.SIZE - 1), np.clip(x, 0, S.SIZE - 1)]
        out[b] = (disc & inside & (np.abs(zz - dep) < 1e-3)).sum() / max(disc.sum(), 1)
    return out


COPY = dict(  # the YouTube post that went with the 500 image (Nov 2026)
    post=["🎉 WE HIT 500 SUBSCRIBERS! 🎉",
          "Thank you SO much for watching and picking your colors. You made this happen! 💛",
          "",
          "How many marbles did it take to make this 500? 🤔",
          "Comment your guess 👇 Closest guess gets pinned 📌",
          "",
          "Next stop: 1,000! 🔴🔵🟢🟡"],
    answer=142,
    image_text=["THANK YOU!", "SUBSCRIBERS", "HOW MANY MARBLES?"],
)


def write_style():
    res = os.path.join(S.BUILD, S.OUT_NAME + ".json")
    out = {k: v for k, v in json.load(open(res)).items() if k not in ("positions", "colours")} if os.path.exists(res) else {}
    style = dict(
        prop="marble-milestone-post",
        canvas=dict(width=S.SIZE, height=S.SIZE, out=S.OUT_SIZE, renderer="../marble-funnel-drain/render.py"),
        text=dict(text=S.TEXT, font=S.FONT, height=S.HEIGHT, stroke=S.STROKE, track=S.TRACK, spacing=S.SPACING,
                  lanes="two per stroke (iso-lines 1 radius inside the monoline outline)"),
        colours=S.COLOURS, palette_linear={k: S.PALETTE[k] for k in S.COLOURS}, colour_seed=S.COLOUR_SEED,
        hole_in=S.HOLE_IN, camera=S.CAM, look="../marble-funnel-drain settings.LOOK, unchanged",
        result=out, copy=COPY if S.TEXT == "500" else None,
    )
    with open(os.path.join(S.HERE, "style.json"), "w", encoding="utf-8") as f:
        json.dump(style, f, indent=1, ensure_ascii=False)
    print("wrote style.json")


def main():
    if "--style" in sys.argv:
        return write_style()
    os.makedirs(S.BUILD, exist_ok=True)
    P, g, col = marbles()
    counts = {S.COLOURS[k]: int((col == k).sum()) for k in range(len(S.COLOURS))}
    per_char = {"%d:%s" % (k, ch): int((g == k).sum()) for k, ch in enumerate(S.TEXT)}
    info = dict(text=S.TEXT, marbles=int(len(P)), per_colour=counts, per_character=per_char)
    print(json.dumps(info))
    base = os.path.join(S.BUILD, S.OUT_NAME)
    plan(P, col, base + "_plan.png")
    if "--plan" in sys.argv:
        return
    img, vis = render(P, col)
    Image.fromarray(img).save(base + ".png")
    Image.fromarray(img).save(base + ".jpg", quality=93)
    info["visible"] = int((vis >= 0.5).sum())
    with open(base + ".json", "w") as f:
        json.dump(dict(info, positions=np.round(P, 3).tolist(), colours=[S.COLOURS[k] for k in col]), f)
    print("->", base + ".png")


if __name__ == "__main__":
    main()
