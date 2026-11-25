"""Turn portrait (1080x1920) marble Shorts into 16:9 loops for 24/7 YouTube livestreams.

  python3 compose.py music  [out]    the SONGS Shorts with a guess-the-song card       -> build/marble_music.mp4
  python3 compose.py ring   [out]    the rounds from rounds.py, with a round counter   -> build/ring_escape.mp4
  python3 compose.py spiral [out]    ../marble-spiral-loop with the rounds muted in a window -> build/loop.mp4
  python3 compose.py thumb IN [out]  a 1280x720 stream thumbnail from a portrait frame -> build/thumbnail.jpg

music and ring: each Short sits centred at 608x1080 over a blurred, darkened fill of itself, between two
side panels drawn with Pillow, and keeps its own audio. Everything is encoded once at YouTube live settings
(1920x1080, 30 fps, H.264 at 6 Mbps with a keyframe every 2 s, AAC 192k at 48 kHz), so streams.sh can loop
the files forever with -stream_loop -1 and -c:v copy. spiral has no audio: streams.sh pairs it with the
bell mix of ../marble-spiral-loop.
"""
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SIMS = os.path.dirname(HERE)

# ---- settings (shipped values) ----
BUILD = os.environ.get("STREAMS_BUILD", os.path.join(HERE, "build"))
ROUNDS = os.environ.get("STREAMS_ROUNDS", os.path.join(BUILD, "rounds"))   # rounds.py writes round_XX_<seed>.mp4
FONT = os.environ.get("STREAMS_FONT", os.path.join(SIMS, "marble-raytrace-kit", "fonts", "Montserrat[wght].ttf"))
W, H = 1920, 1080
FG_W = 608                     # the Short at full height
FG_X = (W - FG_W) // 2
LEFT = (70, 230, 600, 850)     # side panels: x0, y0, x1, y1
RIGHT = (1320, 230, 1850, 850)
BITRATE = "6M"
REVEAL_S = 10.0                # music: the title replaces "guess the song" after this many seconds
SONGS = [                      # (Short, relative to ball-sims/, title); render each with its template first
    ("marble-stairs-song/build/twinkle/Marble_Staircase_Twinkle.mp4", "Twinkle Twinkle Little Star"),
    ("marble-twin-stairs/build/ode-to-joy/Marble_Twin_Stairs_Ode_to_Joy.mp4", "Ode to Joy"),
    ("marble-stairs-song/build/jingle-bells/Marble_Staircase_Jingle_Bells.mp4", "Jingle Bells"),
    ("marble-spiral-round/build/row-row-row/Marble_Spiral_Row_Your_Boat.mp4", "Row, Row, Row Your Boat"),
]
SPIRAL_LOOP = os.path.join(SIMS, "marble-spiral-loop", "build", "marble_spiral_loop.mp4")
SPIRAL_LOOP_FRAMES = 720       # 24 s; the spiral stream is a whole number of loops long
WINDOW = (380, 676, 90, 262)   # spiral stream: w, h, x, y of the muted Ring Escape window
WINDOW_ORDER = (4, 7, 2, 5, 8, 1, 6, 3)   # round order in the window, different from the ring stream's

MUSIC_DOTS = [(246, 246, 246), (88, 196, 250), (255, 122, 98), (255, 112, 190), (92, 228, 168), (255, 206, 64),
              (172, 128, 255)]   # the 7 marble colours of the marble-raytrace-kit Shorts
RING_NAMES = ["RED", "BLUE", "GREEN", "YELLOW", "PURPLE", "ORANGE", "PINK", "CYAN"]
RING_COLORS = {"RED": (255, 68, 79), "BLUE": (52, 137, 255), "GREEN": (68, 218, 120), "YELLOW": (254, 217, 52),
               "PURPLE": (172, 108, 255), "ORANGE": (255, 146, 56), "PINK": (254, 118, 198), "CYAN": (33, 217, 230)}
GOLD = (255, 206, 64)
WHITE = (255, 255, 255)
SOFT = (200, 210, 230)


def font(size, weight="ExtraBold"):
    f = ImageFont.truetype(FONT, size)
    f.set_variation_by_name(weight)
    return f


def panel(d, box):
    d.rounded_rectangle(box, 38, fill=(8, 12, 30, 165), outline=(255, 255, 255, 46), width=2)


def center_text(d, cx, y, s, f, fill):
    d.text((cx - d.textlength(s, font=f) / 2, y), s, font=f, fill=fill)
    bb = f.getbbox(s)
    return y + bb[3]


def wrap(d, s, f, maxw):
    lines, cur = [], ""
    for word in s.split():
        t = (cur + " " + word).strip()
        if d.textlength(t, font=f) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = word
    return lines + [cur]


def dots(d, cx, y, colors, r=24, gap=16, per_row=4):
    rows = [colors[i:i + per_row] for i in range(0, len(colors), per_row)]
    for ri, row in enumerate(rows):
        total = len(row) * 2 * r + (len(row) - 1) * gap
        x0 = cx - total / 2 + r
        for i, c in enumerate(row):
            x, yy = x0 + i * (2 * r + gap), y + r + ri * (2 * r + gap)
            d.ellipse((x - r, yy - r, x + r, yy + r), fill=c + (255,), outline=(255, 255, 255, 120), width=3)
            d.ellipse((x - r * 0.45, yy - r * 0.62, x - r * 0.05, yy - r * 0.25), fill=(255, 255, 255, 110))
    return y + len(rows) * (2 * r + gap)


def music_overlay(path, title, k, n, reveal):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    lc = (LEFT[0] + LEFT[2]) / 2
    panel(d, LEFT)
    y = center_text(d, lc, LEFT[1] + 50, "MARBLE", font(66, "Black"), WHITE)
    y = center_text(d, lc, y + 8, "MUSIC", font(66, "Black"), GOLD)
    d.line((LEFT[0] + 60, y + 34, LEFT[2] - 60, y + 34), fill=(255, 255, 255, 60), width=2)
    y += 70
    if not reveal:
        y = center_text(d, lc, y, "GUESS THE SONG", font(44, "Black"), GOLD)
        y = center_text(d, lc, y + 26, "before the title shows up", font(28, "SemiBold"), SOFT)
        center_text(d, lc, y + 30, "?", font(120, "Black"), (255, 255, 255, 230))
    else:
        y = center_text(d, lc, y, "NOW PLAYING", font(30, "Bold"), SOFT)
        y += 22
        for ln in wrap(d, title, font(46, "Black"), LEFT[2] - LEFT[0] - 70)[:3]:
            y = center_text(d, lc, y, ln, font(46, "Black"), WHITE) + 10
    center_text(d, lc, LEFT[3] - 70, f"SONG {k} OF {n}", font(28, "Bold"), SOFT)
    rc = (RIGHT[0] + RIGHT[2]) / 2
    panel(d, RIGHT)
    y = center_text(d, rc, RIGHT[1] + 50, "PICK YOUR", font(54, "Black"), WHITE)
    y = center_text(d, rc, y + 6, "MARBLE", font(54, "Black"), GOLD)
    y = dots(d, rc, y + 50, MUSIC_DOTS, r=26, gap=18, per_row=4)
    y = center_text(d, rc, y + 24, "Follow it all the way down", font(28, "SemiBold"), SOFT)
    center_text(d, rc, y + 12, "and comment your color!", font(28, "SemiBold"), SOFT)
    center_text(d, rc, RIGHT[3] - 70, "Subscribe for more marble music", font(24, "Bold"), SOFT)
    im.save(path)


def ring_overlay(path, k, n):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    lc = (LEFT[0] + LEFT[2]) / 2
    panel(d, LEFT)
    y = center_text(d, lc, LEFT[1] + 50, "RING", font(76, "Black"), WHITE)
    y = center_text(d, lc, y + 6, "ESCAPE", font(76, "Black"), (33, 217, 230))
    y = center_text(d, lc, y + 30, "FIRST MARBLE OUT", font(34, "Black"), GOLD)
    y = center_text(d, lc, y + 10, "WINS THE CROWN", font(34, "Black"), GOLD)
    d.line((LEFT[0] + 60, y + 36, LEFT[2] - 60, y + 36), fill=(255, 255, 255, 60), width=2)
    y = center_text(d, lc, y + 70, "ROUND", font(32, "Bold"), SOFT)
    center_text(d, lc, y + 14, f"{k} / {n}", font(96, "Black"), WHITE)
    rc = (RIGHT[0] + RIGHT[2]) / 2
    panel(d, RIGHT)
    y = center_text(d, rc, RIGHT[1] + 50, "PICK YOUR", font(54, "Black"), WHITE)
    y = center_text(d, rc, y + 6, "COLOR", font(54, "Black"), GOLD)
    y += 46
    r, gap, per = 28, 34, 4
    for ri in range(2):
        row = RING_NAMES[ri * per:(ri + 1) * per]
        total = per * 2 * r + (per - 1) * gap
        x0 = rc - total / 2 + r
        for i, name in enumerate(row):
            x, yy = x0 + i * (2 * r + gap), y + r
            c = RING_COLORS[name]
            d.ellipse((x - r, yy - r, x + r, yy + r), fill=c + (255,), outline=(255, 255, 255, 140), width=3)
            f = font(17, "Bold")
            d.text((x - d.textlength(name, font=f) / 2, yy + r + 8), name, font=f, fill=SOFT)
        y += 2 * r + 46
    y = center_text(d, rc, y + 14, "Comment your pick", font(28, "SemiBold"), SOFT)
    center_text(d, rc, y + 12, "before the round ends!", font(28, "SemiBold"), SOFT)
    center_text(d, rc, RIGHT[3] - 70, "Subscribe to see who wins next", font(24, "Bold"), SOFT)
    im.save(path)


def spiral_overlay(path):
    """Spiral stream panels: a frame for the muted window on the left, pick-your-marble top right, a label
    bottom right. All outside the centre strip that the Shorts feed shows."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    box = (70, 185, 490, 960)
    panel(d, box)
    cx = (box[0] + box[2]) / 2
    center_text(d, cx, box[1] + 22, "WHO ESCAPES FIRST?", font(30, "Black"), (33, 217, 230))
    box = (1400, 64, 1856, 404)
    panel(d, box)
    cx = (box[0] + box[2]) / 2
    y = center_text(d, cx, box[1] + 34, "PICK YOUR", font(44, "Black"), WHITE)
    y = center_text(d, cx, y + 4, "MARBLE", font(44, "Black"), GOLD)
    y = dots(d, cx, y + 30, MUSIC_DOTS, r=21, gap=14, per_row=4)
    center_text(d, cx, y + 14, "and comment your color!", font(25, "SemiBold"), SOFT)
    box2 = (1360, 900, 1856, 1016)
    panel(d, box2)
    cx2 = (box2[0] + box2[2]) / 2
    y = center_text(d, cx2, box2[1] + 22, "MARBLE MUSIC BOX", font(36, "Black"), WHITE)
    center_text(d, cx2, y + 8, "calm bells, nonstop", font(24, "SemiBold"), SOFT)
    im.save(path)


def window_mask(path, w, h, r=26):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    m.save(path)


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                          "stream=nb_read_packets,r_frame_rate,width,height", "-of", "json", path],
                         capture_output=True, text=True, check=True).stdout
    s = json.loads(out)["streams"][0]
    num, den = map(int, s["r_frame_rate"].split("/"))
    return int(s["nb_read_packets"]), num / den, s["width"], s["height"]


def live_encode(out):
    """Encoder flags for a file that streams with -c:v copy: constant 2 s GOPs, capped bitrate."""
    buf = f"{2 * int(BITRATE.rstrip('M'))}M"
    return ["-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-b:v", BITRATE, "-maxrate", BITRATE,
            "-bufsize", buf, "-g", "60", "-keyint_min", "60", "-sc_threshold", "0", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", out]


def build(segments, out):
    """segments: list of dict(src, overlays=[(png, enable_expr or None)]). Joined with their own audio."""
    args, fc, cat = ["ffmpeg", "-v", "error", "-y"], [], []
    idx = 0
    for i, sg in enumerate(segments):
        nf, fps, w, h = probe(sg["src"])
        assert (w, h) == (1080, 1920) and abs(fps - 30) < 1e-6, (sg["src"], w, h, fps)
        dur = nf / 30.0
        args += ["-i", sg["src"]]
        vi = idx
        idx += 1
        fc.append(f"[{vi}:v]setpts=PTS-STARTPTS,split=2[bg{i}][fg{i}]")
        fc.append(f"[bg{i}]scale=480:-2,crop=480:270,gblur=sigma=7,eq=brightness=-0.16:saturation=0.85,"
                  f"scale=1920:1080:flags=bicubic[bb{i}]")
        fc.append(f"[fg{i}]scale={FG_W}:1080:flags=lanczos[ff{i}]")
        fc.append(f"[bb{i}][ff{i}]overlay={FG_X}:0[c{i}_0]")
        cur = f"c{i}_0"
        for j, (png, enable) in enumerate(sg["overlays"]):
            args += ["-i", png]
            oi = idx
            idx += 1
            en = f":enable='{enable}'" if enable else ""
            fc.append(f"[{cur}][{oi}:v]overlay=0:0:eof_action=repeat{en}[c{i}_{j + 1}]")
            cur = f"c{i}_{j + 1}"
        fc.append(f"[{cur}]trim=end_frame={nf},setpts=PTS-STARTPTS,format=yuv420p[v{i}]")
        fc.append(f"[{vi}:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=0:{dur:.6f},"
                  f"asetpts=PTS-STARTPTS[a{i}]")
        cat += [f"[v{i}][a{i}]"]
    fc.append("".join(cat) + f"concat=n={len(segments)}:v=1:a=1[v][a]")
    enc = live_encode(out)
    args += ["-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]"] + enc[:-3] + \
            ["-c:a", "aac", "-b:a", "192k", "-ar", "48000"] + enc[-3:]
    subprocess.run(args, check=True)


def overlays_dir():
    d = os.path.join(BUILD, "overlays")
    os.makedirs(d, exist_ok=True)
    return d


def rounds():
    names = sorted(p for p in os.listdir(ROUNDS) if p.endswith(".mp4")) if os.path.isdir(ROUNDS) else []
    if not names:
        sys.exit(f"No rounds in {ROUNDS}. Run python3 rounds.py first.")
    return [os.path.join(ROUNDS, p) for p in names]


def music(out):
    od = overlays_dir()
    segs = []
    for k, (rel, title) in enumerate(SONGS, 1):
        src = os.path.join(SIMS, rel)
        if not os.path.exists(src):
            sys.exit(f"Missing {rel}. Render it with that template's make_video.py first.")
        a, b = os.path.join(od, f"music_{k}_guess.png"), os.path.join(od, f"music_{k}_title.png")
        music_overlay(a, title, k, len(SONGS), False)
        music_overlay(b, title, k, len(SONGS), True)
        segs.append(dict(src=src, overlays=[(a, f"lt(t,{REVEAL_S})"), (b, f"gte(t,{REVEAL_S})")]))
    build(segs, out)


def ring(out):
    od = overlays_dir()
    clips = rounds()
    segs = []
    for k, src in enumerate(clips, 1):
        png = os.path.join(od, f"ring_{k}.png")
        ring_overlay(png, k, len(clips))
        segs.append(dict(src=src, overlays=[(png, None)]))
    build(segs, out)


def spiral(out):
    """The spiral loop repeated under a window that plays the rounds muted. The length is rounded up to whole
    spiral loops, so the spiral never jumps; the last round's final frame holds until then."""
    if not os.path.exists(SPIRAL_LOOP):
        sys.exit("Missing ../marble-spiral-loop/build/marble_spiral_loop.mp4. Run its make_loop.py first.")
    od = overlays_dir()
    panels, mask = os.path.join(od, "spiral_panels.png"), os.path.join(od, "window_mask.png")
    spiral_overlay(panels)
    ww, wh, wx, wy = WINDOW
    window_mask(mask, ww, wh)
    all_rounds = rounds()
    clips = [all_rounds[i - 1] for i in WINDOW_ORDER if i <= len(all_rounds)]
    total = sum(probe(c)[0] for c in clips)
    n_out = -(-total // SPIRAL_LOOP_FRAMES) * SPIRAL_LOOP_FRAMES
    args = ["ffmpeg", "-v", "error", "-y", "-stream_loop", "-1", "-i", SPIRAL_LOOP, "-i", panels,
            "-loop", "1", "-i", mask]
    fc = []
    for i, c in enumerate(clips):
        args += ["-i", c]
        fc.append(f"[{3 + i}:v]setpts=PTS-STARTPTS,scale={ww}:{wh}:flags=lanczos,format=yuv420p[r{i}]")
    fc.append("".join(f"[r{i}]" for i in range(len(clips))) + f"concat=n={len(clips)}:v=1:a=0[rr]")
    fc.append(f"[rr]tpad=stop_mode=clone:stop={n_out - total},format=yuva420p[rw]")
    fc.append(f"[2:v]format=gray,trim=end_frame={n_out}[mk]")
    fc.append("[rw][mk]alphamerge[win]")
    fc.append(f"[0:v]trim=end_frame={n_out},setpts=PTS-STARTPTS[base]")
    fc.append("[base][1:v]overlay=0:0:eof_action=repeat[b1]")
    fc.append(f"[b1][win]overlay={wx}:{wy}:eof_action=pass,format=yuv420p[v]")
    args += ["-filter_complex", ";".join(fc), "-map", "[v]", "-an", "-frames:v", str(n_out)] + live_encode(out)
    subprocess.run(args, check=True)


def thumb(src, out):
    """1280x720: the portrait frame centred over a blurred, darkened fill of itself (the stream layout)."""
    fc = ("[0:v]split=2[bg][fg];[bg]scale=480:-2,crop=480:270,gblur=sigma=7,eq=brightness=-0.16:saturation=0.85,"
          "scale=1280:720:flags=bicubic[bb];[fg]scale=-2:720:flags=lanczos[ff];[bb][ff]overlay=(W-w)/2:0")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-filter_complex", fc, "-frames:v", "1",
                    "-q:v", "2", out], check=True)


if __name__ == "__main__":
    modes = {"music": "marble_music.mp4", "ring": "ring_escape.mp4", "spiral": "loop.mp4"}
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    os.makedirs(BUILD, exist_ok=True)
    if mode == "thumb" and len(sys.argv) > 2:
        dst = sys.argv[3] if len(sys.argv) > 3 else os.path.join(BUILD, "thumbnail.jpg")
        thumb(sys.argv[2], dst)
    elif mode in modes:
        dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(BUILD, modes[mode])
        {"music": music, "ring": ring, "spiral": spiral}[mode](dst)
    else:
        sys.exit(__doc__)
    print("wrote", dst)
