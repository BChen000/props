"""Contact sheet of the cut: the middle frame of each of the 29 segments, with the shot timeline (green) and the
narration lines (blue) underneath. Reads build/out/<shot>.mp4 and build/audio/timings.json.

  python3 contact_sheet.py            -> build/contact_sheet.png (720x1280)
"""
import os, sys, json, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ep_paths
from assemble import SHOTS

W, H, COLS = 720, 1280, 6
CW = W // COLS; CH = int(CW * 16 / 9)


def frame(shot, n):
    cmd = ['ffmpeg', '-loglevel', 'error', '-i', ep_paths.OUT + shot + '.mp4', '-vf', f"select='eq(n\\,{n})',scale={CW}:{CH}",
           '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
    return Image.frombytes('RGB', (CW, CH), subprocess.run(cmd, capture_output=True, check=True).stdout)


def main():
    im = Image.new('RGB', (W, H), (18, 18, 20))
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype('DejaVuSans.ttf', 13)
    except OSError:
        font = ImageFont.load_default()
    for i, (s, n) in enumerate(SHOTS):
        x, y = (i % COLS) * CW, (i // COLS) * CH
        im.paste(frame(s, n // 2), (x, y))
        d.text((x + 4, y + 3), s, fill=(255, 255, 255), font=font, stroke_width=2, stroke_fill=(0, 0, 0))
    top = (len(SHOTS) + COLS - 1) // COLS * CH + 12
    total = sum(n for _, n in SHOTS) / 24.0
    sx = lambda t: 10 + (W - 20) * t / total
    t = 0.0
    for i, (s, n) in enumerate(SHOTS):
        d.rectangle([sx(t), top, sx(t + n / 24.0) - 1, top + 26], fill=(70, 150, 90) if i % 2 == 0 else (50, 120, 70))
        t += n / 24.0
    tim = json.load(open(ep_paths.AUDIO + 'timings.json'))
    for i, ln in enumerate(tim):
        yy = top + 34 + (i % 2) * 14
        d.rectangle([sx(ln['start']), yy, sx(ln['end']), yy + 10], fill=(80, 130, 210))
    for k in range(0, int(total) + 1, 30):
        d.line([sx(k), top + 66, sx(k), top + 72], fill=(200, 200, 200))
        d.text((sx(k) - 8, top + 74), f'{k // 60}:{k % 60:02d}', fill=(200, 200, 200), font=font)
    d.text((10, top + 94), f'29 segments, {total:.2f} s; green: shots, blue: the 25 narration lines', fill=(200, 200, 200), font=font)
    out = ep_paths.BUILD + 'contact_sheet.png'
    im.save(out)
    print('wrote', out)


if __name__ == '__main__':
    main()
