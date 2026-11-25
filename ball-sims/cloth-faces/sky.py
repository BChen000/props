"""Painted cartoon sky (gradient + soft cumulus). Writes build/plates/sky.png and sky_lin.npy.
Run:  python3 sky.py   (add --small for a quick 540x960 look)"""
import sys, os
import numpy as np
from PIL import Image

W, H = (540, 960) if "--small" in sys.argv else (1080, 1920)
HORIZON = 0.47
rng = np.random.default_rng(11)
perm = rng.permutation(256)
perm = np.concatenate([perm, perm])
ang = rng.uniform(0, 2 * np.pi, 256)
grads = np.stack([np.cos(ang), np.sin(ang)], 1)


def perlin(x, y):
    xi, yi = np.floor(x).astype(int), np.floor(y).astype(int)
    xf, yf = x - xi, y - yi
    xi &= 255
    yi &= 255
    def g(ix, iy, dx, dy):
        gr = grads[perm[perm[ix] + iy]]
        return gr[..., 0] * dx + gr[..., 1] * dy
    u = xf * xf * xf * (xf * (xf * 6 - 15) + 10)
    v = yf * yf * yf * (yf * (yf * 6 - 15) + 10)
    n00 = g(xi, yi, xf, yf)
    n10 = g((xi + 1) & 255, yi, xf - 1, yf)
    n01 = g(xi, (yi + 1) & 255, xf, yf - 1)
    n11 = g((xi + 1) & 255, (yi + 1) & 255, xf - 1, yf - 1)
    return (n00 * (1 - u) + n10 * u) * (1 - v) + (n01 * (1 - u) + n11 * u) * v


def fbm(x, y, oct=5):
    s, a, f = 0.0, 1.0, 1.0
    for i in range(oct):
        s = s + a * perlin(x * f + 17.3 * i, y * f - 9.1 * i)
        a *= 0.5
        f *= 2.05
    return s


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


CLUSTERS = [
    (0.93, 0.19, 0.62, 1.00),
    (0.05, 0.31, 0.50, 0.85),
    (0.63, 0.405, 0.30, 0.55),
    (0.30, 0.445, 0.20, 0.40),
    (1.02, 0.44, 0.20, 0.35),
]


def make(out_png, out_npy):
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float64)
    yn, xn = ys / H, xs / W
    top = np.array([0.22, 0.47, 0.88])
    mid = np.array([0.44, 0.67, 0.95])
    hor = np.array([0.80, 0.89, 0.98])
    t = np.clip(yn / HORIZON, 0, 1)[..., None]
    sky = np.where(t < 0.55, top + (mid - top) * (t / 0.55), mid + (hor - mid) * ((t - 0.55) / 0.45))
    nx = np.zeros((H, W)); ny = np.zeros((H, W)); nz = np.zeros((H, W))
    base = np.zeros((H, W))
    acc = np.full((H, W), 1e-30)
    K = 7.0
    aspect = H / W
    for ci, (cx, cy, cw, size) in enumerate(CLUSTERS):
        n = int(26 + 30 * size)
        for k in range(n):
            u = rng.normal(0, 0.33)
            px = cx + u * cw * 0.5
            hump = np.exp(-(u / 0.5) ** 2)
            r = cw * (0.10 + 0.13 * hump) * rng.uniform(0.6, 1.15)
            rx, ry = r, r * W / H
            py = cy - rng.uniform(0, 1) * ry * 1.3 * hump
            x0, x1 = int(max(0, (px - rx * 1.3) * W)), int(min(W, (px + rx * 1.3) * W))
            y0, y1 = int(max(0, (py - ry * 1.3) * H)), int(min(H, (cy + ry * 0.4) * H))
            if x1 <= x0 or y1 <= y0:
                continue
            sx, sy = xn[y0:y1, x0:x1], yn[y0:y1, x0:x1]
            dx, dy = (sx - px) / rx, (sy - py) / ry
            d2 = dx * dx + dy * dy
            val = 1.0 - d2
            val = np.where(sy > cy, val - (sy - cy) / ry * 6.0, val)
            w = np.exp(np.clip(K * val, -60, 60))
            nzv = np.sqrt(np.clip(1 - d2, 0, 1))
            acc[y0:y1, x0:x1] += w
            nx[y0:y1, x0:x1] += w * dx
            ny[y0:y1, x0:x1] += w * dy
            nz[y0:y1, x0:x1] += w * nzv
            bv = np.clip(1 - (cy - sy) / (ry * 1.4), 0, 1)
            base[y0:y1, x0:x1] += w * bv
    best = np.log(acc) / K
    nx /= acc; ny /= acc; nz /= acc; base /= acc
    nn = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2) + 1e-9
    nx /= nn; ny /= nn; nz /= nn
    noise = fbm(xn * 10.0, yn * 10.0 * aspect, 6)
    d = best + 0.30 * noise
    alpha = smooth(-0.05, 0.30, d)
    L = np.array([-0.55, -0.62, 0.56]); L /= np.linalg.norm(L)
    ndl = nx * L[0] + ny * L[1] + nz * L[2]
    ndl = ndl + 0.35 * fbm(xn * 16, yn * 16 * aspect, 5)
    lit = np.clip(0.42 + 0.7 * ndl, 0, 1)
    clight = np.array([1.0, 0.995, 0.975])
    cshadow = np.array([0.66, 0.72, 0.83])
    col = cshadow + (clight - cshadow) * lit[..., None]
    col = col * (1 - 0.18 * base[..., None])
    fade = smooth(-0.04, 0.09, HORIZON - yn)
    a = (alpha * (0.25 + 0.75 * fade))[..., None]
    img = np.clip(sky * (1 - a) + col * a, 0, 1)
    Image.fromarray((img * 255 + 0.5).astype(np.uint8)).save(out_png)
    lin = np.where(img <= 0.04045, img / 12.92, ((img + 0.055) / 1.055) ** 2.4)
    np.save(out_npy, lin.astype(np.float32))


if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import settings as CFG
    os.makedirs(CFG.PLATES, exist_ok=True)
    make(os.path.join(CFG.PLATES, 'sky.png'), os.path.join(CFG.PLATES, 'sky_lin.npy'))
