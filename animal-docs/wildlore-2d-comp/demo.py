"""wildlore-2d-comp / demo.py: one 1080x1920 frame of each look, the same recipes the episode's shots use.

  python demo.py              -> out/<panel>.png for every panel below, plus out/sheet.png (all of them, 720x1280)
  python demo.py storm volcano    only those panels
  python demo.py --clip storm     out/storm.mp4, 2 s through Writer (ffmpeg, x264 CRF 17)

Panels: gold, volcano, karst, storm, bright, river, label, title, endcard.
Dragons are composited when their renders exist in RENDERS (default ../dragons/out/renders):
`python ../dragons/demo.py western flying serpent` makes the three used here. Without them the panels are backdrops only.
"""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np, cv2
from layers import *

OUT = os.path.join(HERE, "out")
SPRITE_RES.update({"flying": 2.0})          # the demo wingbeat loop is 640x360, rendered at half the episode's sprite scale
T = 1.5                                       # seconds into the animated layers


def have(shot):
    return len(seq(shot)) > 0


def p_gold():
    img = gold_sky(T, hz=0.56, sun=(0.7, 0.49)).copy()
    if have("flying"):
        img = over(img, sprite("flying", 6, 0.42 * W, 0.4 * H, 0.3, ang=-3, haze=(0.95, 0.7, 0.55), k=0.3))
    return finish(img, 0)


def p_volcano():
    hz = hz_from((6.6, -4.4, 4.85), (4.15, 0, 4.45), 50)
    fire = fire_for("western", 0, T, 0, 10 ** 6) if have("western") else None
    if have("western"):
        return finish(west_frame("western", 0, T, hz, fire=fire, blur_px=10), 0)
    img = volc(T, 0.62).copy()
    img = fire_jet(img, 0.2 * W, 0.55 * H, -8, 0.7 * W, T, w0=12, w1=180)
    img = sparks(img, 0.2 * W, 0.55 * H, -8, T, n=50, seed=7, speed=500)
    return finish(img + embers("v", T), 0)


def p_karst():
    img = mist_bg(T, hz=0.6).copy()
    img = mist_over(img, "k", T, 0.55, 0.85, 0.45, speed=14)
    return finish(img, 0)


def p_storm():
    fx, fy, k = 0.62, 0.22, 1.0
    img = storm_bg(T, flash=k, flash_xy=(fx, fy))
    b = bolt(3, fx * W, 0.0, (fx - 0.05) * W, (fy + 0.35) * H)
    img = img + col((0.85, 0.9, 1.0)) * (b + blur(b, 6) * 1.5 + blur(b, 30) * 0.6)[..., None]   # bolt first,
    if have("serpent"):                                                                            # dragon in front
        img = over(img, sprite("serpent", 10, 0.36 * W, 0.62 * H, 0.5, ang=-8, gain=(1.8, 1.9, 2.1)))
    st = fft_noise(2048, beta=3.0, seed=77, lowcut=10, aniso=8.0)
    img = img + col((0.7, 0.75, 0.85)) * (ss(1.4, 2.6, rolled(st, 0, T * 700)) * 0.22)[..., None]
    return finish(rain_over(img, "storm", T, amt=0.8, n=700), 0, vig=0.4)


def p_bright():
    img = bright_sky(T).copy()
    if have("serpent"):
        img = over(img, sprite("serpent", 20, 0.5 * W, 0.45 * H, 0.42, ang=-28))
    return finish(img, 0)


def p_river():
    img = mist_bg(0.0, hz=0.42, river=True, mood="rain").copy()
    img = mist_over(img, "r", T, 0.6, 0.75, 0.3, speed=18, colr=(0.68, 0.72, 0.72))
    return finish(rain_over(img, "river", T, amt=1.0, colr=(0.78, 0.82, 0.86)), 0, zoom=1.02)


def p_label():
    img = volc(0.0, 0.5, blur_px=20).copy()
    return finish(add_text(img, label_layer("Western dragon", "Draco ignivomus"), 1.0), 0)


def p_title():
    img = gold_sky(T, hz=0.56, sun=(0.7, 0.49)).copy()
    tl = text_layer([("THE TWO DRAGONS", 0.205 * H, 74, False, 9, 1.0),
                     ("Draco ignivomus  ·  Draco nubivagus", 0.205 * H + 78, 40, True, 1, 0.92)])
    return finish(add_text(img, tl, 1.0), 0)


def p_endcard():
    img = np.zeros((H, W, 3), np.float32)
    tl = text_layer([("THE TWO DRAGONS", 0.47 * H, 70, False, 9, 1.0),
                     ("Draco ignivomus  ·  Draco nubivagus", 0.47 * H + 74, 38, True, 1, 0.85)])
    return add_text(img, tl, 1.0)


PANELS = {"gold": p_gold, "volcano": p_volcano, "karst": p_karst, "storm": p_storm, "bright": p_bright,
          "river": p_river, "label": p_label, "title": p_title, "endcard": p_endcard}


def save(name, img):
    cv2.imwrite(os.path.join(OUT, name + ".png"), (np.clip(img, 0, 1)[..., ::-1] * 255 + 0.5).astype(np.uint8))


def clip(name, seconds=2.0):
    global T
    w = Writer(os.path.join(OUT, name + ".mp4"))
    for i in range(int(seconds * FPS)):
        T = 1.5 + i / FPS
        w.write(PANELS[name]())
    print("wrote", os.path.join(OUT, name + ".mp4"), "rc", w.close())


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    args = sys.argv[1:]
    if args and args[0] == "--clip":
        clip(args[1] if len(args) > 1 else "storm")
        sys.exit(0)
    names = args or list(PANELS)
    tiles = []
    for nm in names:
        img = PANELS[nm]()
        save(nm, img)
        tiles.append(cv2.resize(img, (240, 426), interpolation=cv2.INTER_AREA))
        print("wrote", os.path.join(OUT, nm + ".png"))
    if not args:
        rows = [np.hstack(tiles[k:k + 3]) for k in range(0, 9, 3)]
        save("sheet", np.vstack(rows))
        print("wrote", os.path.join(OUT, "sheet.png"))
