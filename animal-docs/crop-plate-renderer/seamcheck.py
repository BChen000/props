"""Seam check for cropped renders: how much each crop's border strips differ from base.png (0-255 scale, 98th pct).
  python3 seamcheck.py [SHOTS_DIR] s06 s08 ...      > 7.5 flags a visible seam
"""
import sys, json, numpy as np, cv2, os
D0 = os.path.join(sys.argv[1] if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]) else os.environ.get('CPR_SHOTS', os.path.join(os.getcwd(), 'build', 'shots')), '')
def check(name, every=4):
    d = D0 + name + '/'
    meta = json.load(open(d + 'meta.json'))
    W, H = meta['res']
    b = cv2.imread(d + 'base.png', cv2.IMREAD_UNCHANGED).astype(np.float32) / 255.0
    base = b[:, :, :3] * b[:, :, 3:4] + 0.5 * (1 - b[:, :, 3:4])
    res = []
    for k in sorted(meta['frames'], key=int)[::every]:
        rec = meta['frames'][k]
        if not rec.get('bbox'):
            continue
        x0, y0, x1, y1 = rec['bbox']
        im = cv2.imread(d + 'fg/%04d.png' % int(k), cv2.IMREAD_UNCHANGED).astype(np.float32) / 255.0
        hh, ww = min(y1 - y0, im.shape[0]), min(x1 - x0, im.shape[1])
        im = im[:hh, :ww]
        c = im[:, :, :3] * im[:, :, 3:4] + 0.5 * (1 - im[:, :, 3:4])
        Dm = cv2.GaussianBlur(np.abs(c - base[y0:y0 + hh, x0:x0 + ww]).mean(axis=2), (0, 0), 3)
        s = 7; v = []
        if x0 > 0: v.append(np.percentile(Dm[:, :s], 98))
        if x1 < W: v.append(np.percentile(Dm[:, -s:], 98))
        if y0 > 0: v.append(np.percentile(Dm[:s, :], 98))
        if y1 < H: v.append(np.percentile(Dm[-s:, :], 98))
        res.append((round(max(v) * 255, 1) if v else 0, int(k)))
    res.sort(reverse=True)
    bad = sum(1 for a, b_ in res if a > 7.5)
    print(name, 'checked', len(res), 'bad(>7.5)', bad, 'worst', res[:3], flush=True)
_names = sys.argv[2:] if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]) else sys.argv[1:]
for n in _names:
    check(n)
