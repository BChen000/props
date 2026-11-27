"""Text -> marble positions. Spells any short text ("500", "1K") with touching marbles on the board.

Each glyph is drawn big, then filled lane by lane like a contour-parallel toolpath: marble centres sit on the
iso-lines of the glyph's inner distance field at 1, 3, 5... marble radii from the edge, spaced one marble apart.
A short relaxation removes the few overlaps left at sharp corners and keeps every marble inside its glyph.
Units: marble radius 1 (as in ../marble-funnel-drain); x to the right, y away from the camera.
"""
import glob
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
from scipy.spatial import cKDTree
from skimage import measure
from skimage.morphology import skeletonize

RES = 40.0  # raster pixels per unit


def find_font(name):
    dirs = [os.environ.get("FONT_DIR", ""), os.path.expanduser("~/.fonts"), os.path.expanduser("~/.local/share/fonts"),
            os.path.expanduser("~/Library/Fonts"), "/Library/Fonts", "/usr/share/fonts", "/usr/local/share/fonts"]
    for d in dirs:
        if d and os.path.isdir(d):
            hits = glob.glob(os.path.join(d, "**", name), recursive=True)
            if hits:
                return hits[0]
    raise FileNotFoundError("%s not found: run ../style-kit/get_fonts.py (or ./setup.sh ball-sims)" % name)


def glyph_mask(text, font_path, height, track, stroke=0.0):
    """Binary mask of the text, its cap height scaled to `height` units, plus the glyph index of every pixel.
    stroke > 0: monoline letters instead. The font's skeleton is redrawn with a round pen `stroke` units wide, so
    every stroke holds exactly stroke/2 marbles side by side and the lanes run straight (use a light weight)."""
    if stroke > 0:
        m, g, r0, c0 = glyph_mask(text, font_path, height - stroke, track)
        h1 = np.ptp(np.where(_monoline(m, stroke).any(1))[0]) / RES
        m, g, r0, c0 = glyph_mask(text, font_path, (height - stroke) ** 2 / max(h1 - stroke, 1e-3), track)
        mono = _monoline(m, stroke)
        near = ndimage.distance_transform_edt(g < 0, return_distances=False, return_indices=True)
        g = g[near[0], near[1]]
        g[~mono] = -1
        rows, cols = np.where(mono)
        return mono.astype(np.uint8), g, (rows.min() + rows.max()) / 2.0, (cols.min() + cols.max()) / 2.0
    probe = ImageFont.truetype(font_path, 1000)
    im = Image.new("L", (1400 * max(len(text), 1), 1400), 0)
    ImageDraw.Draw(im).text((50, 1100), text, font=probe, fill=255, anchor="ls")
    ys = np.where(np.asarray(im).max(1) > 127)[0]
    size = 1000.0 * height * RES / (ys[-1] - ys[0] + 1)
    font = ImageFont.truetype(font_path, int(round(size)))
    pad = int(4 * RES)
    adv = [font.getlength(c) for c in text]
    wpx = int(sum(adv) + track * RES * (len(text) - 1) + 2 * pad)
    hpx = int(height * RES * 1.25 + 2 * pad)
    base = pad + int(height * RES * 1.1)
    mask = np.zeros((hpx, wpx), np.uint8)
    gid = np.full((hpx, wpx), -1, np.int16)
    x = float(pad)
    for k, c in enumerate(text):
        im = Image.new("L", (wpx, hpx), 0)
        ImageDraw.Draw(im).text((x, base), c, font=font, fill=255, anchor="ls")
        a = np.asarray(im) > 127
        mask |= a.astype(np.uint8)
        gid[a] = k
        x += adv[k] + track * RES
    rows, cols = np.where(mask > 0)
    return mask, gid, (rows.min() + rows.max()) / 2.0, (cols.min() + cols.max()) / 2.0


def _monoline(mask, stroke):
    sk = skeletonize(mask > 0)
    return ndimage.distance_transform_edt(~sk) <= stroke / 2.0 * RES


def _along(c, spacing, rng):
    """Marbles at equal arc length along a closed contour (rows, cols in px). Short loops get one marble."""
    seg = np.hypot(*np.diff(c, axis=0).T)
    L = seg.sum() / RES
    n = int(L / spacing)
    while n >= 2 and (L / np.pi) * np.sin(np.pi / n) < spacing * 0.98:
        n -= 1
    if n <= 1:
        return c.mean(0)[None, :]
    s = np.concatenate([[0.0], np.cumsum(seg)])
    t = (rng.random() + np.arange(n)) * (s[-1] / n)
    return np.stack([np.interp(t, s, c[:, 0]), np.interp(t, s, c[:, 1])], 1)


def layout(text="500", font="Poppins-Black.ttf", height=20.0, track=3.0, spacing=2.06, lane=2.0, first=1.0,
           lanes=1, stroke=0.0, iters=600, seed=1):
    """Returns P (N, 2) marble centres in units, centred on the text, and the glyph index of each marble.
    lanes: how many lanes deep to fill (1 = one ring of marbles inside every edge, which gives two-marble strokes)."""
    rng = np.random.default_rng(seed)
    mask, gid, r0, c0 = glyph_mask(text, find_font(font), height, track, stroke)
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, cv2.DIST_MASK_PRECISE).astype(np.float64) / RES
    pts = []
    d = first
    while d < dist.max() and d < first + lanes * lane - 1e-6:
        for c in measure.find_contours(dist, d):
            if len(c) > 2:
                pts.append(_along(c, spacing, rng))
        d += lane
    P = np.concatenate(pts, 0)                                   # (row, col) px
    gy, gx = np.gradient(dist)
    gn = np.hypot(gx, gy) + 1e-9
    gy, gx = gy / gn, gx / gn
    for _ in range(iters):
        moved = 0.0
        pr = cKDTree(P).query_pairs(spacing * RES, output_type="ndarray")
        if len(pr):
            v = P[pr[:, 1]] - P[pr[:, 0]]
            dd = np.hypot(v[:, 0], v[:, 1]) + 1e-9
            push = 0.5 * (spacing * RES - dd)[:, None] * v / dd[:, None] * 0.6
            np.add.at(P, pr[:, 0], -push)
            np.add.at(P, pr[:, 1], push)
            moved = push.max()
        dv = ndimage.map_coordinates(dist, P.T, order=1, mode="nearest")
        out = dv < first
        if out.any():
            fy = ndimage.map_coordinates(gy, P[out].T, order=1, mode="nearest")
            fx = ndimage.map_coordinates(gx, P[out].T, order=1, mode="nearest")
            P[out, 0] += (first - dv[out]) * RES * fy
            P[out, 1] += (first - dv[out]) * RES * fx
        if moved < 0.01 * RES and not out.any():
            break
    keep = np.ones(len(P), bool)                                 # drop whatever still overlaps
    for i, j in sorted(cKDTree(P).query_pairs(2.0 * RES * 0.97), key=lambda p: -p[0]):
        if keep[i] and keep[j]:
            keep[j] = False
    P = P[keep]
    g = gid[np.clip(P[:, 0].round().astype(int), 0, gid.shape[0] - 1), np.clip(P[:, 1].round().astype(int), 0, gid.shape[1] - 1)]
    xy = np.stack([(P[:, 1] - c0) / RES, (r0 - P[:, 0]) / RES], 1)
    o = np.lexsort((xy[:, 0], -xy[:, 1]))
    return xy[o], g[o]


def colour_mix(P, n_colours, seed=1, touch=2.5):
    """Team colours spread evenly: each marble takes the least-used colour none of its neighbours has."""
    rng = np.random.default_rng(seed)
    nb = cKDTree(P).query_ball_point(P, touch)
    col = np.full(len(P), -1)
    used = np.zeros(n_colours, int)
    for i in rng.permutation(len(P)):
        taken = {col[j] for j in nb[i] if col[j] >= 0}
        free = [k for k in range(n_colours) if k not in taken] or list(range(n_colours))
        k = min(free, key=lambda k: (used[k], rng.random()))
        col[i] = k
        used[k] += 1
    return col
