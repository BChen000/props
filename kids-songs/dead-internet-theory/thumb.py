"""Thumbnail candidates (1080x1920, no text): python3 thumb.py -> build/thumb_*.png"""
import paths  # noqa: F401  (sibling props on sys.path)
import numpy as np
from PIL import Image
import make_video as mv, shots, post
from shots import room_frame, cam, dist, HEADC
from poses import G

R, tl = mv.setup()
shots.GLOBAL['env'] = None
variants = {
    'a': dict(c=cam((0.06, -1.18, 1.52), (0, 0, 1.62), 31, 0, 0), keys=[(0, dict(head=(-3, 4, -5)))], glitch=0.0),
    'b': dict(c=cam((0.06, -1.18, 1.52), (0, 0, 1.62), 31, 0, 0), keys=[(0, dict(head=(-3, 4, -5)))], glitch=0.22),
    'c': dict(c=cam((0.55, -2.45, 1.40), (0.05, 0.6, 1.62), 44, 0, 0), keys=[(0, dict(G['present_R'], head=(-2, -6, 0)))], glitch=0.0),
}
for k, v in variants.items():
    fd = room_frame(10.0, 10.0, v['c'], v['keys'], dict(dof=5 if k != 'c' else 2.5, focus=dist(v['c'], HEADC), grain=0.012), glitch=v['glitch'])
    img = R.render(fd['items'], fd['cam'], fd['lights'], fd['env'], fd['adds'])
    out = post.finish(img, fd['post'], 0)
    Image.fromarray(out).save(f'build/thumb_{k}.png')
sheet = Image.new('RGB', (1080, 640))
for i, k in enumerate('abc'):
    sheet.paste(Image.open(f'build/thumb_{k}.png').resize((360, 640)), (i * 360, 0))
sheet.save('build/thumb_sheet.png')
