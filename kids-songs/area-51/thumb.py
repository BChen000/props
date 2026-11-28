"""Thumbnail candidates (1080x1920, no text): python3 thumb.py -> build/thumb_*.png and build/thumb_sheet.png

  a: the man standing in the beam under the glowing ceiling, closer than in the video
  b: the hangar of nine saucers, lights on
  c: the crowd at the gate at night
"""
import paths  # noqa: F401  (sibling props on sys.path)
import numpy as np
from PIL import Image
import make_video as mv, shots, post
from shots import cam

R, tl = mv.setup()
spans = {s['scene']: s for s in mv.spans_of(tl)}


def shot(scene, lt, camera=None, post_over=None):
    sp = spans[scene]
    x = mv.Ctx(sp)
    fd = shots.SCENES[scene]['fn'](lt, x, sp['start'] + lt)
    if camera is not None:
        fd['cam'] = camera
    img = R.render(fd['items'], fd['cam'], fd['lights'], fd['env'], fd.get('adds', []))
    p = dict(fd.get('post', {})); p.update(post_over or {}); p['grain'] = 0.012
    return post.finish(img, p, 0)


x_end = mv.Ctx(spans['end'])
tb = x_end.E[2] + 0.25
variants = {
    'a': shot('end', tb + 0.38, cam((0.08, -2.35, 1.05), (0.0, 0.0, 1.85), 52, 0, 0), dict(dof=2.0)),
    'b': shot('saucer', 1.0),
    'c': shot('gate', spans['gate']['end'] - spans['gate']['start'] - 0.2),
}
for k, im in variants.items():
    Image.fromarray(im).save(f'build/thumb_{k}.png')
sheet = Image.new('RGB', (1080, 640))
for i, k in enumerate(variants):
    sheet.paste(Image.open(f'build/thumb_{k}.png').resize((360, 640)), (i * 360, 0))
sheet.save('build/thumb_sheet.png')
print('ok')
