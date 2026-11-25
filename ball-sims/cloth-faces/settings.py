"""Settings for the "1 Face vs 1,000,000 Faces Blanket" Shorts.

Pick the object under the blankets with HERO (or the HERO environment variable):
  'marble'  big glass cat's-eye marble (the original Short, 30k+ views)
  'duck'    big glossy rubber duck (the sequel)
Everything generated goes to build/ (plates ~200 MB, sims ~250 MB, frames ~1 GB); don't commit it.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, 'build')
PLATES = os.path.join(BUILD, 'plates')
SIMS = os.path.join(BUILD, 'sims')
FRAMES = os.path.join(BUILD, 'frames')
FINAL = os.path.join(BUILD, 'final')
OUT = os.path.join(BUILD, 'out')
TIMELINE = os.path.join(BUILD, 'timeline.json')
FONT_DIR = os.path.expanduser('~/.fonts')

HERO = os.environ.get('HERO', 'duck')

FPS = 30
WIDTH, HEIGHT = 1080, 1920

LABELS = ['1', '4', '16', '64', '256', '10,000', '1,000,000']
COUNTS = [1, 4, 16, 64, 256, 10000, 1000000]

SIM_ARGS = {
    'marble': [
        '--frames 110 --dx 0.06 --dy -0.06',
        '--frames 110 --dx -0.07 --dy 0.05',
        '--frames 115 --dx 0.05 --dy -0.03 --rot 8',
        '--frames 120 --dx -0.04 --dy 0.06 --rot -6',
        '--frames 130 --dx 0.03 --dy -0.04 --rot 5',
        '--frames 200 --dx 0.03 --dy -0.015 --self 1',
        '--frames 230 --dx 0.075 --dy 0.045 --fric 0.25',
    ],
    'duck': [
        '--frames 110 --dx 0.15 --dy 0.05 --quality 10 --cq 4',
        '--frames 110 --dx -0.07 --dy 0.05',
        '--frames 115 --dx 0.05 --dy -0.03 --rot 8',
        '--frames 120 --dx -0.04 --dy 0.06 --rot -6',
        '--frames 130 --dx 0.03 --dy -0.04 --rot 5',
        '--frames 200 --dx 0.0 --dy 0.0 --fric 0.3 --self 1',
        '--frames 230 --dx 0.03 --dy 0.0 --fric 0.25',
    ],
}

SPEC = {
    'marble': [
        dict(hold=3, segs=[(0, 60, 1.0)]),
        dict(hold=5, segs=[(0, 66, 1.0)]),
        dict(hold=5, segs=[(0, 70, 1.0)]),
        dict(hold=5, segs=[(0, 66, 1.0)]),
        dict(hold=5, segs=[(0, 40, 1.0), (40, 70, 1.5), (70, 88, 1.0)]),
        dict(hold=5, segs=[(0, 45, 1.0), (45, 105, 2.0), (105, 132, 1.0)]),
        dict(hold=6, segs=[(0, 20, 1.0), (20, 40, 0.5), (40, 90, 1.0), (90, 124, 1.0)]),
    ],
    'duck': [
        dict(hold=3, segs=[(0, 64, 1.0)]),
        dict(hold=5, segs=[(0, 66, 1.0)]),
        dict(hold=5, segs=[(0, 58, 1.0)]),
        dict(hold=5, segs=[(0, 74, 1.0)]),
        dict(hold=5, segs=[(0, 40, 1.0), (40, 70, 1.5), (70, 86, 1.0)]),
        dict(hold=5, segs=[(0, 40, 1.0), (40, 62, 1.5), (62, 80, 1.0)]),
        dict(hold=6, segs=[(0, 20, 1.0), (20, 40, 0.5), (40, 96, 1.0)]),
    ],
}
REFILL = 20
REFILL_STAGGER = 1.5

SPP = 12
CATCHER_SPP = 8
CATCHER_DIV = 5
MAIN_SCALE = 0.8
CHUNK = 60

THUMB_SIM_FRAME = {'marble': 31, 'duck': 47}
THUMB_LENS = 72
THUMB_TARGET_Z = {'marble': 1.25, 'duck': 1.2}
