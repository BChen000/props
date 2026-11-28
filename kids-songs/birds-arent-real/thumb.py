"""Thumbnail candidates (1080x1920, no text): python3 thumb.py -> build/thumb_*.png and build/thumb_sheet.png

  a: the pigeon on his hat, red eye on, closer than in the video
  b: the specimen stage under the glowing "12,000,000,000"
  c: pigeons charging on the power line
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


xe = mv.Ctx(spans['end'])
t_led = xe.T[1] + 0.25 + 1.15 + 0.45 + 0.6
xl = mv.Ctx(spans['lore'])
xw = mv.Ctx(spans['wires'])
variants = {
    'a': shot('end', t_led + 0.2, cam((0.05, -1.55, 1.95), (0.0, 0.0, 1.88), 31, 0, 0), dict(dof=4.0)),
    'b': shot('lore', xl.T[2] + 0.9),
    'c': shot('wires', xw.T[1] + 0.5),
}
for k, im in variants.items():
    Image.fromarray(im).save(f'build/thumb_{k}.png')
sheet = Image.new('RGB', (1080, 640))
for i, k in enumerate(variants):
    sheet.paste(Image.open(f'build/thumb_{k}.png').resize((360, 640)), (i * 360, 0))
sheet.save('build/thumb_sheet.png')
print('ok')
