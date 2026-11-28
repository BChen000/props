"""Draws every set piece on one sheet with ../../shared/lowpoly-gl: python3 preview.py -> preview.png (720x1280).

  OUT=path.png python3 preview.py     -> somewhere else
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
from PIL import Image, ImageDraw
import sets as S
import meshkit as mk
from meshkit import add, join, plane
from glr import Renderer, T, R3, euler
import post

# ------------------------------------------------------------------ settings
TILE = (240, 320)
GRID = (3, 4)
OUT = os.environ.get('OUT', os.path.join(HERE, 'preview.png'))
VIEW = np.array([0.55, -1.0, 0.42])        # camera direction from the piece: front-right, a little above
BG = (0.05, 0.055, 0.07)


def pieces():
    """name -> list of (part, colour); parts are added to meshkit.PARTS."""
    mk.PARTS.clear()
    out = {}
    p, pc = S.person(3)
    pu, puc = S.person(5, arms_up=True)
    board, stick = S.sign()
    add('person', p.moved((-0.35, 0.0, 0.0)), pc)
    add('person_up', pu.moved((0.35, 0.0, 0.0)), puc)
    add('sign_board', board.moved((0.35, -0.13, 1.12)), (0.92, 0.86, 0.72))
    add('sign_stick', stick.moved((0.35, -0.13, 1.12)), (0.55, 0.42, 0.28))
    out['person + sign'] = ['person', 'person_up', 'sign_board', 'sign_stick']
    pg = S.pigeon()
    for nm, col in (('body', (0.46, 0.49, 0.56)), ('beak', (0.25, 0.2, 0.18)), ('legs', (0.7, 0.3, 0.3)), ('eyes', (0.95, 0.55, 0.15)),
                    ('led', (1.0, 0.1, 0.05))):
        add('pg_' + nm, pg[nm], col)
    for nm in ('wing_L', 'wing_R'):
        add('pg_' + nm, pg[nm], (0.36, 0.38, 0.45), pivot=S.WING_PIVOT[nm])
    out['pigeon'] = ['pg_body', 'pg_beak', 'pg_legs', 'pg_eyes', 'pg_led', 'pg_wing_L', 'pg_wing_R']
    for key, fn, cols in (('car', S.car, dict(body=(0.62, 0.1, 0.1), glass=(0.05, 0.07, 0.1), wheels=(0.03, 0.03, 0.03), lights=(0.9, 0.9, 0.85))),
                          ('truck', S.truck, dict(body=(0.8, 0.8, 0.78), glass=(0.05, 0.06, 0.08), wheels=(0.03, 0.03, 0.03), lights=(1, 1, 1)))):
        d = fn()
        for nm, col in cols.items():
            add(f'{key}_{nm}', d[nm], col)
        out[key] = [f'{key}_{nm}' for nm in cols]
    u = S.u2()
    add('u2_body', u['body'], (0.62, 0.64, 0.68)); add('u2_canopy', u['canopy'], (0.05, 0.07, 0.1))
    out['u2'] = ['u2_body', 'u2_canopy']
    j = S.jet()
    add('jet_body', j['body'], (0.85, 0.86, 0.88)); add('jet_stripe', j['stripe'], (0.75, 0.1, 0.1))
    out['jet'] = ['jet_body', 'jet_stripe']
    sc = S.saucer(2.0)
    add('saucer_body', sc['body'], (0.55, 0.57, 0.6)); add('saucer_dome', sc['dome'], (0.2, 0.3, 0.34)); add('saucer_lights', sc['lights'], (0.6, 0.95, 1.0))
    out['saucer'] = ['saucer_body', 'saucer_dome', 'saucer_lights']
    add('hangar', S.hangar(36, 44), (0.42, 0.42, 0.4))
    add('runway', S.runway(120, 30)[0].moved((0, -60, 0)), (0.08, 0.08, 0.085))
    out['hangar + runway'] = ['hangar', 'runway']
    pole, ins = S.pole(9.0)
    add('pole', pole, (0.3, 0.24, 0.18)); add('pole_ins', ins, (0.75, 0.78, 0.72))
    out['pole'] = ['pole', 'pole_ins']
    bb, frame = S.billboard(12, 4, 6)
    add('bb_board', bb, (0.92, 0.9, 0.86)); add('bb_frame', frame, (0.25, 0.26, 0.28))
    out['billboard'] = ['bb_board', 'bb_frame']
    rails, panel = S.fence(16, 2.2)
    add('fence_rails', rails, (0.45, 0.46, 0.48)); add('fence_panel', panel, (0.6, 0.62, 0.64))
    out['fence'] = ['fence_rails', 'fence_panel']
    t, tc = S.terrain(160, 30, 3.0, 3, cols=((0.0, (0.26, 0.17, 0.11)), (1.0, (0.40, 0.29, 0.19))))
    m, mc = S.mountains(60, 60, (6, 20), 4, arc=(math.radians(40), math.radians(140)))
    add('terrain', t, tc); add('mountains', m.moved((0, 10, 0)), mc)
    out['terrain + mountains'] = ['terrain', 'mountains']
    return out


def frame_cam(names, fov=35.0):
    P = np.concatenate([mk.PARTS[n]['pos'] for n in names]).astype(float)
    lo, hi = P.min(0), P.max(0)
    c = (lo + hi) / 2
    r = np.linalg.norm(hi - lo) / 2
    aspect = TILE[0] / TILE[1]
    hf = 2 * math.atan(math.tan(math.radians(fov / 2)) * aspect)
    d = r / math.tan(hf / 2) * 1.05
    v = VIEW / np.linalg.norm(VIEW)
    return dict(eye=tuple(c + v * d), target=tuple(c), fov=fov, far=max(100.0, 4 * d))


def main():
    ps = pieces()
    R = Renderer(*TILE)
    R.add_meshes(dict(mk.PARTS))
    env = dict(amb_top=(0.22, 0.24, 0.28), amb_bot=(0.06, 0.06, 0.06), fog_col=BG, fog_d=0.0, bg=BG)
    sheet = Image.new('RGB', (TILE[0] * GRID[0], TILE[1] * GRID[1]))
    d = ImageDraw.Draw(sheet)
    for i, (label, names) in enumerate(ps.items()):
        cam = frame_cam(names)
        items = []
        for n in names:
            M_ = np.eye(4)
            if n.startswith('pg_wing'):
                side = 1 if n.endswith('L') else -1
                M_ = T(S.WING_PIVOT[n[3:]]) @ R3(euler(0, -side * 0.55, 0))
            items.append((n, M_, dict(spec=0.4, emit=(3.0, 0.3, 0.2) if n == 'pg_led' else (0, 0, 0))))
        lights = [dict(type='dir', dir=(0.4, 0.6, -0.7), col=(1.0, 0.95, 0.88), energy=1.15, spec=0.5),
                  dict(type='dir', dir=(-0.6, -0.2, -0.3), col=(0.5, 0.6, 0.9), energy=0.35, spec=0.0)]
        img = R.render(items, cam, lights, env, [])
        tile = Image.fromarray(post.finish(img, dict(exposure=1.0, vignette=0.25, grain=0.0, bloom=0.1)))
        x, y = (i % GRID[0]) * TILE[0], (i // GRID[0]) * TILE[1]
        sheet.paste(tile, (x, y))
        d.text((x + 10, y + 8), label, fill=(225, 225, 230))
    sheet.save(OUT)
    print('->', OUT)


if __name__ == '__main__':
    main()
