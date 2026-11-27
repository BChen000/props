"""Where a 16:9 window should sit on a 1080x1920 Short, over time.

follow_colors: finds the race marbles by colour every 0.1 s (a few saturated colours on a pale course), smooths the
centroid with a 0.6 s Gaussian, and returns the window's top edge as keyframes.
keyframes_expr: turns keyframes into a piecewise-linear ffmpeg expression of t for crop's y.
"""
import subprocess

import numpy as np

SRC_W, SRC_H = 1080, 1920
WIN_H = 608                                   # 1080 wide at 16:9
COLOR_RULES = {
    "red": lambda r, g, b: (r > 140) & (g < 90) & (b < 90),
    "blue": lambda r, g, b: (b > 120) & (r < 90) & (b - g > 25),
    "green": lambda r, g, b: (g > 120) & (r < 110) & (g - b > 30),
}


def follow_colors(path, colors, fps=10, w=108, h=192, sigma_s=0.6, bias=0.0):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps={fps},scale={w}:{h}",
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
    fr = np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3).astype(np.int16)
    ys = np.arange(h)[:, None].repeat(w, 1)
    cy = np.full(len(fr), np.nan)
    for i, f in enumerate(fr):
        r, g, b = f[..., 0], f[..., 1], f[..., 2]
        m = np.zeros((h, w), bool)
        for c in colors:
            m |= COLOR_RULES[c](r, g, b)
        if m.sum() >= 2:
            cy[i] = ys[m].mean()
    idx = np.arange(len(cy))
    ok = ~np.isnan(cy)
    cy = np.interp(idx, idx[ok], cy[ok]) if ok.any() else np.full(len(cy), h / 2)
    k = int(3 * sigma_s * fps)
    ker = np.exp(-0.5 * (np.arange(-k, k + 1) / (sigma_s * fps)) ** 2)
    ker /= ker.sum()
    sm = np.convolve(np.pad(cy, k, mode="edge"), ker, mode="valid")
    top = np.clip(sm * SRC_H / h - WIN_H / 2 + bias * WIN_H, 0, SRC_H - WIN_H)
    t = idx / fps
    return [(float(a), float(b)) for a, b in zip(t[::5], top[::5])]


def keyframes_expr(keys):
    """[(t, y), ...] -> nested if() expression, linear between keys, held outside."""
    keys = sorted(keys)
    expr = f"{keys[-1][1]:.1f}"
    for (t0, y0), (t1, y1) in reversed(list(zip(keys[:-1], keys[1:]))):
        seg = f"{y0:.1f}+({y1 - y0:.1f})*(t-{t0:.3f})/{max(t1 - t0, 1e-3):.3f}"
        expr = f"if(lt(t,{t1:.3f}),{seg},{expr})"
    return f"if(lt(t,{keys[0][0]:.3f}),{keys[0][1]:.1f},{expr})"


if __name__ == "__main__":
    import sys
    keys = follow_colors(sys.argv[1], sys.argv[2].split(","))
    print(" ".join(f"{t:.1f}:{y / SRC_H:.2f}" for t, y in keys))
