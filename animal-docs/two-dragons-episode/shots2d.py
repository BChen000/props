"""two-dragons-episode / shots2d.py: the episode's edit. Every shot is composited here from the Blender renders.

  python shots2d.py sh01 sh02a ...          -> $WORK/shots/<shot>.mp4 (1080x1920, 24 fps, x264 CRF 17)
  python shots2d.py all                     every shot in CUTS order
  python shots2d.py prev sh12 64,173,229    single frames as JPEGs in $WORK/prev/

CUTS lists each shot's first frame in the final cut (4153 frames, 173.04 s), placed on the narration's phrases
(see ../../shared/narration-check). Shot functions f_<shot>(i, t, n) get the frame index within the shot, its time in
seconds and the shot length. Reads renders from $RENDERS (default $WORK/renders); WORK is $TWO_DRAGONS_WORK or build/.
Helpers (dragon, sprite, west_frame, fire_for, label_layer, panel, ...) live in ../wildlore-2d-comp/layers.py.
"""
import sys, os, math, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.environ.get("TWO_DRAGONS_WORK") or os.path.join(HERE, "build")
os.environ.setdefault("RENDERS", os.path.join(WORK, "renders"))
sys.path.insert(0, os.path.join(HERE, "..", "wildlore-2d-comp"))
import numpy as np, cv2
from layers import *
import layers as _layers

OUTD = os.path.join(WORK, "shots")
os.makedirs(OUTD, exist_ok=True)
SPRITE_RES.update({"l_w_side_gold": 2.0, "l_w_back_gold": 2.0, "l_w_side_volc": 1.3333, "l_c_side_gold": 2.0})

CUTS = [("sh01", 0), ("sh02a", 145), ("sh02b", 185), ("sh03", 237), ("sh04", 404), ("sh05a", 557), ("sh05b", 671),
        ("sh05c", 724), ("sh06", 809), ("sh07a", 938), ("sh07b", 1042), ("sh08", 1188), ("sh09a", 1380), ("sh09b", 1510),
        ("sh10", 1654), ("sh11", 1764), ("sh12", 1849), ("sh13", 2125), ("sh14a", 2204), ("sh14b", 2266), ("sh15a", 2452),
        ("sh15b", 2508), ("sh16a", 2555), ("sh16b", 2684), ("sh17a", 2798), ("sh17b", 2904), ("sh18a", 3060),
        ("sh18b", 3150), ("sh19", 3225), ("sh20", 3462), ("sh21", 3618), ("sh22", 3675), ("sh23", 3753), ("sh24", 3865)]
TOTAL = 4153


def span(name):
    for i, (n, s) in enumerate(CUTS):
        if n == name:
            e = CUTS[i + 1][1] if i + 1 < len(CUTS) else TOTAL
            return s, e
    raise KeyError(name)


# ---------------- cached backgrounds ----------------


def title_layer():
    return cached("title", lambda: text_layer([("THE TWO DRAGONS", 0.205 * H, 74, False, 9, 1.0),
                                               ("Draco ignivomus  ·  Draco nubivagus", 0.205 * H + 78, 40, True, 1, 0.92)]))


# ---------------- WEST volcano helpers ----------------


# ================= shot functions =================
def f_sh01(i, t, n):
    img = gold_sky(t, hz=0.56, sun=(0.7, 0.49)).copy()
    x = lerp(-0.08 * W, 0.72 * W, i / n); y = 0.38 * H + 8 * math.sin(t * 2.2)
    spc = sprite("l_c_side_gold", i, lerp(0.95 * W, 0.62 * W, i / n), 0.445 * H + 6 * math.sin(t * 1.1), 0.15, ang=-2,
                 flip=True, haze=(0.97, 0.74, 0.58), k=0.5)
    img = over(img, spc)
    sp = sprite("l_w_side_gold", i, x, y, 0.3, ang=-3, haze=(0.95, 0.7, 0.55), k=0.3)
    img = over(img, sp)
    img = add_text(img, title_layer(), ssf(6, 22, i) * (1 - ssf(n - 22, n - 7, i)))
    return finish(img, i, zoom=push(i, n, 1.0, 1.04))


def f_sh02a(i, t, n):
    bg = volc(0.0, 0.45, sun=(0.15, 0.4), blur_px=18).copy()
    img = over(bg, dragon("s02a", 0, gain=(0.96, 0.8, 0.8)))
    img = img + embers("s02a", t, n=60, size=(2, 5), amt=0.6) * 0.6
    img = add_text(img, label_layer("Western dragon", "Draco ignivomus"), fade(i, n, 3, 2))
    return finish(img, i, zoom=push(i, n, 1.03, 1.08))


def f_sh02b(i, t, n):
    bg = mist_bg(0.0, 0.5, blur_px=18).copy()
    img = over(bg, dragon("s02b", 0))
    img = mist_over(img, "s02b", t, 0.75, 1.0, 0.35, speed=25)
    img = add_text(img, label_layer("Chinese dragon", "Draco nubivagus", 0.6), fade(i, n, 3, 3))
    return finish(img, i, zoom=push(i, n, 1.03, 1.08))


def f_sh03(i, t, n):
    im = load_rgba(seq("s03")[0])[..., :3]
    z = push(i, n, 1.2, 1.1)
    img = im * col((1.04, 0.98, 0.9))
    dust = embers("dust", t, n=60, seed=8, speed=12, size=(1.0, 2.0), tint=(0.9, 0.8, 0.65), amt=0.35)
    img = img + dust
    return finish(img, i, zoom=z, pan=(40, lerp(-70, -50, i / n)), vig=0.45)


def f_sh04(i, t, n):
    img = gold_sky(t + 4, hz=0.6, sun=(0.5, 0.54), seed=6).copy()
    u = ssf(0, 1, i / n)
    xw = lerp(0.46 * W, 0.12 * W, u); yw = lerp(0.4 * H, 0.33 * H, u)
    xc = lerp(0.54 * W, 0.86 * W, u); yc = lerp(0.42 * H, 0.47 * H, u)
    img = over(img, sprite("l_c_side_gold", i, xc, yc, lerp(0.16, 0.26, u), ang=-4, haze=(1.0, 0.78, 0.6), k=0.35))
    img = over(img, sprite("l_w_side_gold", i, xw, yw, lerp(0.17, 0.26, u), flip=True, ang=6, haze=(1.0, 0.78, 0.6), k=0.35))
    return finish(img, i, zoom=push(i, n, 1.0, 1.03))


def f_sh05a(i, t, n):
    hz = hz_from((10, -9, 1.6), (0.8, 0, 3.4), 30)
    return finish(west_frame("u05a_n", i, t, hz, plate_name="u05a_n"), i, zoom=push(i, n, 1.0, 1.05))


def f_sh05b(i, t, n):
    bg = volc(0.0, 0.5, blur_px=20).copy()
    img = over(bg, dragon("s05b", 0, gain=(0.96, 0.8, 0.8)))
    br = 1.0 + 0.006 * math.sin(t * 2 * math.pi / 3.0)
    return finish(img, i, zoom=push(i, n, 1.04, 1.1) * br)


def f_sh05c(i, t, n):
    bg = volc(0.0, 0.42, blur_px=14).copy()
    img = over(bg, dragon("s05c", 0, gain=(0.96, 0.8, 0.8)))
    img = img + embers("s05c", t, n=50, size=(1.5, 3.5), amt=0.5)
    return finish(img, i, zoom=push(i, n, 1.0, 1.06), pan=(0, lerp(10, -10, i / n)))


def f_sh06(i, t, n):
    hz = hz_from((10.5, -7.5, 3.8), (2.4, 0, 4.7), 40)
    return finish(west_frame("u06_n", i, t, hz, plate_name="u06_n", blur_px=3), i, zoom=push(i, n, 1.0, 1.05))


U07A_R0, U07A_D = 3, 52


def f_sh07a(i, t, n):
    hz = hz_from((7.2, -4.0, 4.7), (4.1, 0, 4.45), 45)
    j = i + U07A_R0; jo = j - U07A_D
    m = meta("u07a_n")
    p = mpos(m, "mouth", j); q = mpos(m, "mouth_fwd", j)
    def fire(img):
        if p is None:
            return img
        dx, dy = q[0] - p[0], q[1] - p[1]
        ox, oy, ppm = mouth_gap(p, q, back=0.18, down=0.3)
        ang = -math.degrees(math.atan2(dy, dx))
        ig = ssf(40, 56, jo)
        img = sparks(img, ox, oy, ang - 8, t, n=40, seed=3, spread=0.35, speed=1.6 * ppm,
                     life=0.45, intensity=ssf(34, 44, jo))
        if ig > 0:
            img = fire_jet(img, ox, oy, ang - 8, 1.9 * ppm * (0.3 + 0.7 * ig), t, intensity=ig,
                           w0=0.07 * ppm, w1=0.45 * ppm * (0.4 + 0.6 * ig), grow=1.0, smoke=False)
        return img
    img = west_frame("u07a_n", j, t, hz, fire=fire, blur_px=14, emb=0.5)
    return finish(img, i, zoom=push(i, n, 1.0, 1.04))


def f_sh07b(i, t, n, offset=0, zoom=(1.0, 1.06), center=None):
    j = i + offset
    hz = hz_from((11.0, -10.5, 2.2), (3.0, 0, 3.8), 26)
    fire = fire_for("u07b_n", j, t + offset / FPS, 0, 140)
    img = west_frame("u07b_n", j, t + offset / FPS, hz, fire=fire, plate_name="u07b_n")
    pan = (0.0, 0.0)
    if center is not None:
        pan = ((W / 2 - center[0]) * (zoom[0] - 1), (H / 2 - center[1]) * (zoom[0] - 1))
    return finish(img, j, zoom=push(i, n, *zoom), pan=pan)


# ---------------- EAST ----------------
def f_sh08(i, t, n):
    img = mist_bg(t, hz=0.6, shift=4.0).copy()
    i0 = 68
    if i > i0:
        k = (i - i0) / (n - i0)
        sp = sprite("l_c_side_mist", i, lerp(0.15 * W, 0.42 * W, k), 0.47 * H, 0.12, ang=-6,
                    haze=(0.88, 0.9, 0.88), k=0.55)
        sp *= ssf(0, 0.3, k)
        img = over(img, sp)
    img = mist_over(img, "sh08a", t, 0.55, 0.85, 0.55, speed=16)
    return finish(img, i, zoom=push(i, n, 1.0, 1.06), vig=0.25)


def f_sh09a(i, t, n):
    bg = mist_bg(0.0, hz=0.93, layers=3).copy()
    img = over(bg, dragon("u09a_n", i))
    img = mist_over(img, "sh09a", t, 0.75, 1.05, 0.5, speed=20)
    return finish(img, i, zoom=push(i, n, 1.0, 1.04), vig=0.25)


def f_sh09b(i, t, n):
    bg = mist_bg(0.0, hz=0.5, blur_px=16).copy()
    img = over(bg, dragon("u09b_n", i))
    img = mist_over(img, "sh09b", t, 0.78, 1.05, 0.35, speed=26)
    return finish(img, i, zoom=push(i, n, 1.0, 1.03), vig=0.25)


def f_sh10(i, t, n):
    bg = mist_bg(t, hz=0.66, blur_px=3, shift=10.0).copy()
    x = lerp(0.2 * W, 0.3 * W, i / n)
    img = over(bg, sprite("l_c_side_mist", i, x, 0.45 * H, 0.95, ang=-4, haze=(0.88, 0.9, 0.88), k=0.08))
    img = mist_over(img, "sh10", t, 0.7, 1.05, 0.45, speed=30)
    return finish(img, i, zoom=1.02, vig=0.25)


def f_sh11(i, t, n):
    img = bright_sky(t)
    y = lerp(0.85 * H, 0.32 * H, ssf(0, 1, i / n)); x = lerp(0.35 * W, 0.62 * W, i / n)
    img = over(img, sprite("l_c_side_mist", i, x, y, 0.55, ang=38, haze=(0.9, 0.92, 0.95), k=0.12))
    a = ss(0.4, 1.4, scroll(150, 31, -t * 260 + 450, 0, pad=1200)) * 0.8 * ss(0.0, 0.3, np.linspace(0, 1, H))[:, None]
    img = img * (1 - a[..., None]) + col((0.97, 0.97, 0.98)) * a[..., None]
    return finish(img, i, zoom=1.02, vig=0.22)


FLASHES = [(64, 0.62, 0.22, 3), (173, 0.16, 0.18, 5), (228, 0.7, 0.3, 8)]


def f_sh12(i, t, n):
    fl = 0.0; fxy = (0.6, 0.3); bolt_img = None
    for f0, fx, fy, sd in FLASHES:
        d = i - f0
        if 0 <= d < 10:
            k = [1.0, 0.35, 0.9, 0.5, 0.25, 0.12, 0.06, 0.03, 0.0, 0.0][d]
            if k > fl:
                fl = k; fxy = (fx, fy)
                if d < 6:
                    b = cached(("bolt", sd), lambda: bolt(sd, fx * W, 0.0, (fx - 0.05) * W, (fy + 0.35) * H))
                    bolt_img = b * k
    img = storm_bg(t, flash=fl, flash_xy=fxy)
    if bolt_img is not None:
        img = img + col((0.85, 0.9, 1.0)) * (bolt_img + blur(bolt_img, 6) * 1.5 + blur(bolt_img, 30) * 0.6)[..., None]
    x = lerp(0.22 * W, 0.78 * W, i / n); y = 0.5 * H + 40 * math.sin(t * 0.9)
    sp = sprite("l_c_34_storm", i, x, y, 0.72, ang=-8, gain=(1 + 0.8 * fl, 1 + 0.9 * fl, 1 + 1.1 * fl))
    img = over(img, sp)
    st = cached("streaktex", lambda: fft_noise(2048, beta=3.0, seed=77, lowcut=10, aniso=8.0))
    s_ = ss(1.4, 2.6, rolled(st, 0, t * 700)) * 0.22
    img = img + col((0.7, 0.75, 0.85)) * s_[..., None]
    img = rain_over(img, "storm", t, amt=0.8, n=700)
    return finish(img, i, zoom=push(i, n, 1.0, 1.04), vig=0.4)


def f_sh13(i, t, n):
    img = mist_bg(0.0, hz=0.5, river=True, mood="rain").copy()
    k = i / n
    img = over(img, sprite("l_c_side_mist", i, lerp(0.2 * W, 0.62 * W, k), lerp(0.18 * H, 0.42 * H, k), lerp(0.5, 0.34, k), ang=-22,
                           haze=(0.62, 0.66, 0.67), k=lerp(0.1, 0.3, k)))
    img = mist_over(img, "sh13", t, 0.55, 0.8, 0.5, speed=14, colr=(0.68, 0.72, 0.72))
    return finish(img, i, zoom=push(i, n, 1.0, 1.05), vig=0.3)


def f_sh14a(i, t, n):
    return np.ascontiguousarray(f_sh07b(i, t, n, offset=36, zoom=(1.18, 1.24), center=None)[:, ::-1])


def f_sh14b(i, t, n):
    hz = 0.42
    img = mist_bg(0.0, hz=hz, river=True, mood="rain").copy()
    k = i / n
    x = lerp(-0.1 * W, 1.0 * W, k); y = 0.6 * H
    sp = sprite("l_c_side_mist", i, x, y, 0.55, ang=-2, haze=(0.62, 0.66, 0.67), k=0.12, gain=(0.85, 0.9, 0.95))
    wl = int((hz + 0.3) * H)
    refl = sp[::-1].copy()
    shift = 2 * wl - H
    refl = np.roll(refl, shift - int(0.05 * H), axis=0)
    rip = noise(H, W, 5, 55, octaves=3, aniso=6.0)
    mx = (np.arange(W, dtype=np.float32)[None, :] + rip * 6).astype(np.float32)
    my = np.repeat(np.arange(H, dtype=np.float32)[:, None], W, axis=1)
    refl = cv2.remap(refl, mx, my, cv2.INTER_LINEAR)
    rm = (np.arange(H)[:, None] > wl).astype(np.float32)
    refl = blur(refl, 2.5) * rm[..., None] * 0.45
    img = over(img, refl)
    img = over(img, sp)
    img = mist_over(img, "sh14b", t, 0.6, 0.75, 0.3, speed=18, colr=(0.68, 0.72, 0.72))
    img = rain_over(img, "river", t, amt=lerp(0.5, 1.1, ssf(0.1, 0.6, k)), n=900, colr=(0.78, 0.82, 0.86))
    return finish(img, i, zoom=1.02, vig=0.32)


def f_sh15a(i, t, n):
    img = volc(t, 0.8, sun=(0.2, 0.72), vx=0.55, vh=0.44, vw=0.62).copy()
    img = img + embers("sh15a", t, n=80, amt=0.7)
    return finish(img, i, zoom=push(i, n, 1.0, 1.04))


def f_sh15b(i, t, n):
    img = mist_bg(t, hz=0.55, river=True, shift=6.0).copy()
    img = mist_over(img, "sh15b", t, 0.6, 0.85, 0.5, speed=14)
    return finish(img, i, zoom=push(i, n, 1.0, 1.04), vig=0.25)


def f_sh16a(i, t, n):
    img = volc(t, 0.74, sun=(0.82, 0.66), vx=0.38, vh=0.36, vw=0.58).copy()
    k = i / n
    sp = sprite("l_w_side_volc", i, lerp(1.08 * W, 0.12 * W, k), lerp(0.42 * H, 0.36 * H, k) + 10 * math.sin(t * 2.4), 0.48,
                flip=True, ang=4, haze=VHAZE, k=0.12)
    img = over(img, sp)
    img = img + embers("sh16a", t, n=110, amt=0.8)
    return finish(img, i, zoom=push(i, n, 1.0, 1.03))


def f_sh16b(i, t, n):
    hz = hz_from((12.0, 6.5, 0.4), (0.5, 0, 4.2), 26)
    img = west_frame("u16b_n", i, t, hz, plate_name="u16b_n", sun=(0.8, 0.62))
    shake = ssf(30, 36, i) * (1 - ssf(70, 80, i))
    pan = (4 * shake * math.sin(i * 2.1), 3 * shake * math.sin(i * 2.9))
    return finish(img, i, zoom=push(i, n, 1.0, 1.04), pan=pan)


KNEAR = (0.6 + 0.26, 4, 0.3, 0.55, 0.2, 0.34, 0.1)


def f_sh17a(i, t, n):
    img = mist_bg(t, hz=0.6, layers=3, shift=3.0).copy()
    k = i / n
    x = lerp(0.1 * W, 0.8 * W, k); y = 0.52 * H + 0.04 * H * math.sin(k * 6)
    sp = sprite("l_c_side_mist", i, x, y, 0.13, ang=-6 + 10 * math.cos(k * 6), haze=(0.88, 0.9, 0.88), k=0.45)
    img = over(img, sp)
    by, nn, h0, h1, w0, w1, ha = KNEAR
    img = karst_layer(img, by, 40 + 33, nn, h0, h1, w0, w1, (0.08, 0.15, 0.12), (0.88, 0.9, 0.88), ha, t=t,
                      x_shift=3.0 * t, veg=(0.05, 0.14, 0.07), mist=0.5, mist_h=0.16, mist_col=(0.92, 0.94, 0.92))
    img = mist_over(img, "sh17a", t, 0.62, 0.95, 0.45, speed=12)
    return finish(img, i, zoom=push(i, n, 1.0, 1.04), vig=0.25)


def f_sh17b(i, t, n):
    img = mist_bg(t, hz=0.56, layers=2, shift=8.0).copy()
    k = i / n
    x = lerp(-0.25 * W, 1.25 * W, k); y = 0.5 * H + 0.07 * H * math.sin(k * 5.0)
    ang = -10 * math.cos(k * 5.0)
    sp = sprite("l_c_side_mist", i, x, y, 0.5, ang=ang, haze=(0.88, 0.9, 0.88), k=0.14)
    img = over(img, sp)
    img = karst_layer(img, 0.56 + 0.26, 51, 3, 0.36, 0.6, 0.2, 0.3, (0.08, 0.15, 0.12), (0.88, 0.9, 0.88), 0.08, t=t,
                      x_shift=14.0 * t, veg=(0.05, 0.14, 0.07), mist=0.45, mist_h=0.18, mist_col=(0.92, 0.94, 0.92),
                      xs=[0.22 * W, 0.68 * W, 1.12 * W])
    img = mist_over(img, "sh17b", t, 0.7, 1.05, 0.4, speed=20)
    return finish(img, i, zoom=1.02, vig=0.25)


def f_sh18a(i, t, n):
    bg = volc(0.0, 0.5, blur_px=20).copy()
    img = over(bg, dragon("s18a", 0, gain=(0.96, 0.84, 0.84)))
    gl = 0.08 * (0.6 + 0.4 * math.sin(t * 9) * math.sin(t * 4.3))
    img = screen(img, col((1.0, 0.5, 0.15)) * gl)
    return finish(img, i, zoom=push(i, n, 1.0, 1.12))


def f_sh18b(i, t, n):
    bg = mist_bg(0.0, hz=0.5, blur_px=20).copy()
    img = over(bg, dragon("s18b", 0))
    return finish(img, i, zoom=push(i, n, 1.0, 1.12), vig=0.3)


PAIRS = [(("s05b", (0.5, 0.45), 1.15), ("s19c", (0.5, 0.36), 1.25)),
         (("s19w", (0.5, 0.45), 1.0), ("s19ct", (0.5, 0.5), 1.0)),
         (("s05c", (0.5, 0.55), 1.0), ("s19c", (0.4, 0.62), 1.15)),
         (("s18a", (0.5, 0.5), 1.0), ("s02b", (0.42, 0.4), 1.05))]


SEGS19 = [0, 41, 79, 110, 237]


def f_sh19(i, t, n):
    k = max(j for j in range(4) if SEGS19[j] <= i)
    li = i - SEGS19[k]; ln = SEGS19[k + 1] - SEGS19[k]
    (a, fa, za), (b, fb, zb) = PAIRS[k]
    top = panel(a, fa, za, volc(0.0, 0.5, blur_px=20), li, ln, gain=(0.96, 0.8, 0.8))
    bot = panel(b, fb, zb, mist_bg(0.0, hz=0.5, blur_px=20), li, ln)
    img = np.zeros((H, W, 3), np.float32)
    img[:H // 2 - 2] = top; img[H // 2 + 2:] = bot
    img[H // 2 - 2:H // 2 + 2] = 0.92
    return finish(img, i, vig=0.25)


def f_sh20(i, t, n):
    hz = hz_from((10, -9, 1.6), (0.8, 0, 3.4), 30)
    seqf = list(range(60, 72)) + list(range(70, 60, -1))
    top = west_frame("u05a_n", 50 + seqf[(i // 2) % len(seqf)], t, hz, plate_name="u05a_n", emb=0.6)
    z = push(i, n, 1.07, 1.0)
    M = np.array([[z, 0, W / 2 - 0.5 * W * z], [0, z, (H / 2 - 2) / 2 - 0.47 * H * z]], np.float32)
    top = cv2.warpAffine(top, M, (W, H // 2 - 2), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    bimg = mist_bg(t, hz=0.62, shift=4.0).copy()
    bimg = over(bimg, sprite("l_c_side_mist", i, lerp(0.3 * W, 0.62 * W, i / n), 0.5 * H, 0.32, ang=-4, haze=(0.88, 0.9, 0.88), k=0.2))
    bimg = mist_over(bimg, "sh20", t, 0.62, 0.9, 0.45, speed=16)
    M2 = np.array([[z, 0, W / 2 - 0.5 * W * z], [0, z, (H / 2 - 2) / 2 - 0.5 * H * z]], np.float32)
    bot = cv2.warpAffine(bimg, M2, (W, H // 2 - 2), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    img = np.zeros((H, W, 3), np.float32)
    img[:H // 2 - 2] = top; img[H // 2 + 2:] = bot
    img[H // 2 - 2:H // 2 + 2] = 0.92
    return finish(img, i, vig=0.25)


def f_sh21(i, t, n):
    return f_sh07b(i, t, n, offset=20, zoom=(1.12, 1.18))


def f_sh22(i, t, n):
    img = storm_bg(t + 3, flash=0.25 * ssf(0, 4, i) * (1 - ssf(10, 30, i)), flash_xy=(0.5, 0.2))
    k = i / n
    img = over(img, sprite("l_c_up_rain", i, lerp(0.45 * W, 0.58 * W, k), lerp(0.66 * H, 0.38 * H, k), 0.75, ang=-10, gain=(1.1, 1.15, 1.2)))
    img = rain_over(img, "sh22", t, amt=1.0, n=900, angle=0.08)
    return finish(img, i, zoom=push(i, n, 1.0, 1.05), vig=0.35)


def f_sh23(i, t, n):
    img = gold_sky(t + 8, hz=0.62, sun=(0.62, 0.56), seed=8).copy()
    k = i / n
    img = over(img, sprite("l_c_side_gold", i, lerp(0.26 * W, 0.6 * W, k), 0.46 * H + 12 * math.sin(t * 1.3), 0.34, ang=-3,
                           haze=(1.0, 0.8, 0.62), k=0.2))
    img = over(img, sprite("l_w_side_gold", i, lerp(0.34 * W, 0.66 * W, k), 0.33 * H + 10 * math.sin(t * 2.4), 0.36, ang=-2,
                           haze=(1.0, 0.8, 0.62), k=0.2))
    return finish(img, i, zoom=push(i, n, 1.0, 1.03))


def f_sh24(i, t, n):
    img = gold_sky(t + 12, hz=0.6, sun=(0.56, 0.52), seed=9).copy()
    k = ssf(0, 1, i / (n - 50))
    sc = lerp(0.42, 0.08, k)
    img = over(img, sprite("l_w_back_gold", i, lerp(0.3 * W, 0.53 * W, k), lerp(0.36 * H, 0.47 * H, k), sc,
                           haze=(1.0, 0.82, 0.62), k=lerp(0.15, 0.6, k)))
    img = over(img, sprite("l_c_side_gold", i, lerp(0.62 * W, 0.6 * W, k), lerp(0.5 * H, 0.5 * H, k), lerp(0.3, 0.07, k), ang=-12,
                           haze=(1.0, 0.82, 0.62), k=lerp(0.15, 0.6, k)))
    img = finish(img, i, zoom=push(i, n, 1.0, 1.05))
    if i < 12:
        sp = span("sh23")
        nn = sp[1] - sp[0]
        prev = f_sh23(nn + i, (nn + i) / FPS, nn)
        a = ssf(0, 12, i)
        img = prev * (1 - a) + img * a
    endk = ssf(n - 92, n - 66, i)
    img = img * (1 - endk)
    tl = cached("endtitle", lambda: text_layer([("THE TWO DRAGONS", 0.47 * H, 70, False, 9, 1.0),
                                                ("Draco ignivomus  ·  Draco nubivagus", 0.47 * H + 74, 38, True, 1, 0.85)]))
    img = add_text(img, tl, ssf(n - 64, n - 52, i))
    return img


FUNCS = {name: globals()["f_" + name] for name, _ in CUTS}


def render(name, frames=None, preview_dir=None):
    s, e = span(name)
    n = e - s
    fn = FUNCS[name]
    if preview_dir:
        os.makedirs(preview_dir, exist_ok=True)
        for i in frames:
            img = fn(i, i / FPS, n)
            cv2.imwrite(os.path.join(preview_dir, "%s_%03d.jpg" % (name, i)), (np.clip(img, 0, 1)[..., ::-1] * 255).astype(np.uint8),
                        [cv2.IMWRITE_JPEG_QUALITY, 85])
        return
    import comp as _c
    _layers._BG.clear(); _c._ICACHE.clear()
    if len(_c._NCACHE) > 40:
        _c._NCACHE.clear()
    w = Writer(os.path.join(OUTD, name + ".mp4"))
    t0 = time.time()
    for i in range(n):
        w.write(fn(i, i / FPS, n))
    rc = w.close()
    print("SHOT", name, n, "frames", "%.1fs" % (time.time() - t0), "rc", rc, flush=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "prev":
        name = args[1]; fr = [int(x) for x in args[2].split(",")]
        render(name, fr, os.path.join(WORK, "prev"))
    else:
        for nm in ([n for n, _ in CUTS] if args == ["all"] else args):
            render(nm)
