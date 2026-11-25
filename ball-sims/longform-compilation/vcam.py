"""A virtual camera that turns a vertical 1080x1920 Short into a full-screen 1920x1080 clip.

Keys are (t, cx, cy, vh, roll): the view's centre in source pixels, its height in source pixels (608 = the full width
of the Short, 1080 = the whole Short turned on its side) and its roll in degrees (0 = upright, 90 = the Short turned a
quarter turn, which fits a top-down shot exactly). Between keys the camera eases in and out. The view is always kept
inside the source: during a roll it pushes in just enough that no corner leaves the picture, so there are no borders.

python3 vcam.py <in.mp4> <out.mp4> 't,cx,cy,vh,roll;t,cx,cy,vh,roll;...'
"""
import math
import subprocess
import sys

import cv2
import numpy as np

SRC_W, SRC_H = 1080, 1920
OUT_W, OUT_H = 1920, 1080
ASPECT = OUT_W / OUT_H


def _ease(x):
    return x * x * (3 - 2 * x)


def vh_max(roll):
    c, s = abs(math.cos(math.radians(roll))), abs(math.sin(math.radians(roll)))
    return min(SRC_W / (ASPECT * c + s), SRC_H / (ASPECT * s + c))


def camera(keys, t):
    keys = sorted(keys)
    if t <= keys[0][0]:
        k = keys[0][1:]
    elif t >= keys[-1][0]:
        k = keys[-1][1:]
    else:
        for a, b in zip(keys[:-1], keys[1:]):
            if a[0] <= t <= b[0]:
                u = _ease((t - a[0]) / max(b[0] - a[0], 1e-6))
                k = [p + (q - p) * u for p, q in zip(a[1:], b[1:])]
                break
    cx, cy, vh, roll = k
    vh = min(vh, vh_max(roll) - 0.5)
    c, s = abs(math.cos(math.radians(roll))), abs(math.sin(math.radians(roll)))
    hx = (ASPECT * vh * c + vh * s) / 2
    hy = (ASPECT * vh * s + vh * c) / 2
    cx = min(max(cx, hx), SRC_W - hx)
    cy = min(max(cy, hy), SRC_H - hy)
    return cx, cy, vh, roll


def matrix(cx, cy, vh, roll):
    """Output pixel -> source pixel."""
    sc = vh / OUT_H
    c, s = math.cos(math.radians(roll)), math.sin(math.radians(roll))
    a, b, cc, d = c * sc, -s * sc, s * sc, c * sc
    return np.array([[a, b, cx - a * OUT_W / 2 - b * OUT_H / 2],
                     [cc, d, cy - cc * OUT_W / 2 - d * OUT_H / 2]], np.float64)


def render(src, out, keys, fps=30, crf=14, t_end=None):
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                            "-s", f"{OUT_W}x{OUT_H}", "-r", str(fps), "-i", "-", "-i", src,
                            "-map", "0:v", "-map", "1:a?", "-c:a", "copy", "-shortest",
                            "-vf", "unsharp=5:5:0.45:5:5:0", "-c:v", "libx264", "-preset", "veryfast",
                            "-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart", out],
                           stdin=subprocess.PIPE)
    n = SRC_W * SRC_H * 3
    i = 0
    while True:
        buf = dec.stdout.read(n)
        if len(buf) < n or (t_end is not None and i / fps > t_end):
            break
        fr = np.frombuffer(buf, np.uint8).reshape(SRC_H, SRC_W, 3)
        m = matrix(*camera(keys, i / fps))
        o = cv2.warpAffine(fr, m, (OUT_W, OUT_H), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP,
                           borderMode=cv2.BORDER_REFLECT_101)
        enc.stdin.write(o.tobytes())
        i += 1
    enc.stdin.close()
    dec.stdout.close()
    dec.kill()
    dec.wait()
    if enc.wait() != 0:
        sys.exit(f"vcam: encoding {out} failed")
    return i


if __name__ == "__main__":
    ks = [tuple(float(v) for v in k.split(",")) for k in sys.argv[3].split(";")]
    print(render(sys.argv[1], sys.argv[2], ks), "frames")
