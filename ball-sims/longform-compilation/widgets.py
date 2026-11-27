"""Overlay widgets that move every frame, driven by the round's own audio:
- a rainbow equalizer (8 glossy bars with falling peak caps), inside the game panel
- a marble progress bar along the bottom: a swirl marble rolls to a checkered flag over the round
- the current round's progress marble, pulsing on every note
All three are packed into one RGBA strip per frame and piped to ffmpeg, which crops and places them."""
import numpy as np
from PIL import Image, ImageDraw

import settings as S
import ui

EQ_W, EQ_H = S.EQ_SIZE
BAR_W, BAR_H = S.BAR["w"], 64
PULSE = 48
BANDS = 8


def features(audio):
    """audio: (n, 2) float32 at S.SR, one round. Per-frame band levels (N, 8) in 0..1 and a note envelope (N,)."""
    x = audio.mean(1)
    n_frames = len(x) // S.SPF
    win = 2048
    pad = np.concatenate([np.zeros(win), x, np.zeros(win)]).astype(np.float32)
    centers = np.arange(n_frames) * S.SPF + S.SPF // 2 + win
    idx = centers[:, None] + np.arange(-win // 2, win // 2)[None, :]
    mag = np.abs(np.fft.rfft(pad[idx] * np.hanning(win)[None, :].astype(np.float32), axis=1))
    freqs = np.fft.rfftfreq(win, 1 / S.SR)
    edges = np.geomspace(150, 6000, BANDS + 1)
    band = np.stack([mag[:, (freqs >= edges[i]) & (freqs < edges[i + 1])].mean(1) for i in range(BANDS)], 1)
    db = 20 * np.log10(band + 1e-7)
    lo, hi = np.percentile(db, 25, axis=0), np.percentile(db, 99, axis=0)
    v = np.clip((db - lo) / np.maximum(hi - lo, 6), 0, 1) ** 1.3
    lev = np.zeros_like(v)
    for k in range(len(v)):
        lev[k] = np.maximum(v[k], (lev[k - 1] if k else 0) * 0.86)
    logm = np.log1p(mag[:, (freqs > 100) & (freqs < 8000)] * 10)
    flux = np.r_[0, np.clip(np.diff(logm, axis=0), 0, None).sum(1)]
    ref = np.percentile(flux, 97) + 1e-6
    env = np.zeros(len(flux))
    for k in range(len(flux)):
        env[k] = max(np.clip((flux[k] / ref - 0.35) / 0.65, 0, 1), (env[k - 1] if k else 0) * 0.78)
    return lev.astype(np.float32), env.astype(np.float32)


def _aa(fn, w, h, ss=4):
    im = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    fn(ImageDraw.Draw(im), ss)
    return im.resize((w, h), Image.LANCZOS)


def _swirl_marble(r, color, n=36):
    """A glass marble with a white swirl ribbon at n roll angles (the light stays top-left)."""
    out = []
    size = 2 * r * 3
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    nx, ny = (xx + 0.5) / (size / 2) - 1, (yy + 0.5) / (size / 2) - 1
    rr = nx ** 2 + ny ** 2
    inside = (rr <= 1).astype(np.float32)
    nz = np.sqrt(np.clip(1 - rr, 0, 1))
    L = np.array([-0.45, -0.6, 0.66])
    L /= np.linalg.norm(L)
    lam = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1)
    spec = np.clip(2 * lam * nz - L[2], 0, 1) ** 40
    base = np.array(ui.rgb(color), np.float32) / 255
    for i in range(n):
        a = 2 * np.pi * i / n
        u = nx * np.cos(a) - nz * np.sin(a)
        band = np.clip(1 - np.abs(np.sin(3.2 * u + 1.4 * ny)) / 0.28, 0, 1) * (nz > 0.05)
        col = base[None, None, :] * (0.4 + 0.7 * lam[..., None])
        col = col * (1 - 0.75 * band[..., None]) + band[..., None] * 0.95 * (0.55 + 0.45 * lam[..., None])
        col = np.clip(col + spec[..., None] * 0.9 + ((1 - nz) ** 3 * 0.3)[..., None], 0, 1)
        out.append(Image.fromarray(np.dstack([col * 255, inside[..., None] * 255]).astype(np.uint8), "RGBA")
                   .resize((2 * r, 2 * r), Image.LANCZOS))
    return out


class Widgets:
    def __init__(self, it, lev, env):
        self.lev, self.env, self.N = lev, env, it["N"]
        self.W, self.H = max(BAR_W, EQ_W), EQ_H + BAR_H + PULSE
        self.peaks = np.zeros(BANDS)
        gap = 10
        self.bw = (EQ_W - gap * (BANDS - 1)) // BANDS
        self.bx = [i * (self.bw + gap) for i in range(BANDS)]
        self.caps, self.bodies = [], []
        for i in range(BANDS):
            c = ui.rgb(S.MARBLES[i])
            hi = tuple(min(255, int(v * 0.55 + 255 * 0.45)) for v in c)
            w = self.bw
            self.caps.append(_aa(lambda d, s, c=c, hi=hi, w=w: (
                d.ellipse([0, 0, w * s - 1, w * s - 1], fill=c + (255,)),
                d.ellipse([w * s * 0.2, w * s * 0.12, w * s * 0.45, w * s * 0.45], fill=hi + (200,))), w, w))
            body = Image.new("RGBA", (w, EQ_H), c + (255,))
            bd = ImageDraw.Draw(body)
            bd.rectangle([int(w * 0.2), 0, int(w * 0.38), EQ_H], fill=hi + (150,))
            bd.rectangle([w - max(2, w // 8), 0, w, EQ_H], fill=tuple(int(v * 0.7) for v in c) + (255,))
            self.bodies.append(body)
        self.peak_cap = _aa(lambda d, s, w=self.bw: d.rounded_rectangle([0, 0, w * s - 1, 8 * s - 1], radius=4 * s,
                                                                         fill=(255, 255, 255, 235)), self.bw, 8)
        self.r = 24
        self.gx0, self.gx1 = self.r + 6, BAR_W - 70
        gy, gh = BAR_H // 2, 22
        self.gy = gy

        def groove(d, s):
            d.rounded_rectangle([(self.gx0 - 18) * s, (gy - gh / 2) * s, (self.gx1 + 18) * s, (gy + gh / 2) * s],
                                radius=gh / 2 * s, fill=(10, 4, 20, 170), outline=(255, 255, 255, 170), width=3 * s)
        self.groove = _aa(groove, BAR_W, BAR_H)
        fill = np.zeros((gh - 10, self.gx1 - self.gx0 + 18, 4), np.uint8)
        cols = np.array([ui.rgb(c) for c in S.MARBLES], np.float32)
        t = np.linspace(0, len(cols) - 1, fill.shape[1])
        i0 = np.floor(t).astype(int)
        i1 = np.minimum(i0 + 1, len(cols) - 1)
        fill[..., :3] = (cols[i0] * (1 - (t - i0))[:, None] + cols[i1] * (t - i0)[:, None])[None].astype(np.uint8)
        fill[..., 3] = 255
        fill[:3, :, :3] = np.minimum(255, fill[:3, :, :3].astype(int) + 70).astype(np.uint8)
        self.fill = Image.fromarray(fill, "RGBA")
        self.fill_y = gy - (gh - 10) // 2
        flag = Image.new("RGBA", (BAR_W, BAR_H), (0, 0, 0, 0))
        fd = ImageDraw.Draw(flag)
        fx = self.gx1 + 26
        fd.rectangle([fx, gy - 28, fx + 4, gy + 22], fill=(235, 235, 235, 255))
        sq = 8
        for row in range(3):
            for col in range(4):
                fd.rectangle([fx + 5 + col * sq, gy - 28 + row * sq, fx + 4 + (col + 1) * sq, gy - 29 + (row + 1) * sq],
                             fill=(20, 20, 20, 255) if (row + col) % 2 else (250, 250, 250, 255))
        self.flag = flag
        color = S.MARBLES[it["idx"] % len(S.MARBLES)] if it["kind"] != "bonus" else S.GOLD
        self.rolls = _swirl_marble(self.r, color)
        self.pulses = []
        base_r = 11 if it["kind"] == "bonus" else 8
        for k in range(13):
            sc = 1 + 0.6 * k / 12
            im = Image.new("RGBA", (PULSE * 2, PULSE * 2), (0, 0, 0, 0))
            c = PULSE
            rr = (base_r + 4) * sc * 2
            ImageDraw.Draw(im).ellipse([c - rr, c - rr, c + rr, c + rr], outline=(255, 255, 255, 255), width=5)
            ui.paste_center(im, ui.marble(base_r * sc * 2, color), c, c)
            self.pulses.append(im.resize((PULSE, PULSE), Image.LANCZOS))

    def frame(self, k):
        im = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        lev = self.lev[min(k, len(self.lev) - 1)]
        self.peaks = np.maximum(lev, self.peaks - 0.018)
        span = EQ_H - self.bw - 18
        for i in range(BANDS):
            h = int(12 + lev[i] * span)
            top = EQ_H - h
            im.alpha_composite(self.bodies[i].crop((0, 0, self.bw, h)), (self.bx[i], top))
            im.alpha_composite(self.caps[i], (self.bx[i], top - self.bw // 2))
            py = EQ_H - int(12 + self.peaks[i] * span) - self.bw // 2 - 12
            im.alpha_composite(self.peak_cap, (self.bx[i], max(0, py)))
        p = min(1.0, k / max(1, self.N - 1))
        x = self.gx0 + p * (self.gx1 - self.gx0)
        bar = self.groove.copy()
        wf = int(x - self.gx0 + 14)
        if wf > 2:
            bar.alpha_composite(self.fill.crop((0, 0, wf, self.fill.height)), (self.gx0 - 13, self.fill_y))
        bar.alpha_composite(self.flag)
        roll = self.rolls[int((x - self.gx0) / self.r * 180 / np.pi / 10) % len(self.rolls)]
        bar.alpha_composite(roll, (int(x - self.r), self.gy - self.r))
        im.alpha_composite(bar, (0, EQ_H))
        e = self.env[min(k, len(self.env) - 1)]
        im.alpha_composite(self.pulses[int(round(e * 12))], (0, EQ_H + BAR_H))
        return im.tobytes()
