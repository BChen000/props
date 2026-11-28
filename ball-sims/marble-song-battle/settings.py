"""Settings for the marble song-battle Shorts ("Naughty or Nice?", Christmas 2026).

A gold marble falls through a Blender obstacle course and every bounce plays the next melody note.
Six rounds alternate between two teams (3 songs each); a HUD shows the question, the current team and
song, and 3-vs-3 score dots. The video loops seamlessly.

Change the matchup here: TITLE, TEAMS, ROUNDS (song + course style + obstacle + glow + mood).
Songs live in music.py (public-domain melodies only). Everything generated goes to build/
(about 5 GB of frames); don't commit it. Override the folder with the BUILD_DIR environment variable.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
EPISODE = os.environ.get('EPISODE', '')          # another matchup: episodes/<name>.py, built in build_<name>/
BUILD = os.environ.get('BUILD_DIR', os.path.join(HERE, 'build' + ('_' + EPISODE if EPISODE else '')))
PLAN_JSON = os.path.join(BUILD, 'plan.json')
LUT_JSON = os.path.join(BUILD, 'lut.json')
AUDIO = os.path.join(BUILD, 'audio.wav')
FRAMES = os.path.join(BUILD, 'frames')
CHUNKS = os.path.join(BUILD, 'chunks')
THUMBS = os.path.join(BUILD, 'thumb')
TEST = os.path.join(BUILD, 'test')
OUT = os.path.join(BUILD, 'out')
SCENE_BLEND = os.path.join(BUILD, 'scene.blend')
RENDER_DONE = os.path.join(BUILD, 'render.done')

FPS = 30
WIDTH, HEIGHT = 1080, 1920
RENDER_PCT = 80
SAMPLES = 4
CHUNK = 318

TITLE = 'Naughty or Nice?'
TEAMS = {'NAUGHTY': (255, 58, 58), 'NICE': (52, 226, 98)}
DOT_X = {0: 367, 2: 419, 4: 471, 1: 609, 3: 661, 5: 713}

ROUNDS = [
    dict(song='carol_of_the_bells', team='NAUGHTY', style='helix', obst='slab', R=2.1, R1=1.15, turns=2, sgn=+1,
         drift=(0.0, 0.0), glow=(1.0, 0.05, 0.04), e=0.24),
    dict(song='jingle_bells', team='NICE', style='stairs', obst='gift', vf=2.4, A=0.55, Tsw=3.2,
         glow=(0.08, 1.0, 0.25), e=0.30),
    dict(song='sugar_plum', team='NAUGHTY', style='helix', obst='mint', R=2.0, R1=1.3, turns=2, sgn=-1,
         drift=(0.0, 0.0), glow=(1.0, 0.08, 0.40), e=0.26),
    dict(song='deck_the_halls', team='NICE', style='zigzag', obst='ornament', vf=2.1, k=1.9, Lmin=0.22, Lmax=0.95,
         glow=(0.50, 1.0, 0.10), e=0.34),
    dict(song='god_rest_ye', team='NAUGHTY', style='helix', obst='coal', R=2.1, R1=1.15, turns=2, sgn=+1,
         drift=(0.0, 0.0), glow=(1.0, 0.30, 0.02), e=0.24),
    dict(song='we_wish_you', team='NICE', style='stairs', obst='cane', vf=2.5, A=0.45, Tsw=2.6,
         glow=(0.15, 1.0, 0.45), e=0.30),
]

MOODS = [
    dict(fog=(0.085, 0.022, 0.045), sun=(1.0, 0.72, 0.66), sun_e=2.6, amb=1.3),
    dict(fog=(0.17, 0.27, 0.38), sun=(1.0, 0.96, 0.9), sun_e=3.4, amb=1.0),
    dict(fog=(0.10, 0.03, 0.11), sun=(1.0, 0.78, 0.9), sun_e=2.6, amb=1.3),
    dict(fog=(0.09, 0.21, 0.20), sun=(1.0, 0.97, 0.85), sun_e=3.3, amb=1.0),
    dict(fog=(0.10, 0.04, 0.022), sun=(1.0, 0.75, 0.55), sun_e=2.6, amb=1.3),
    dict(fog=(0.18, 0.25, 0.37), sun=(1.0, 0.97, 0.92), sun_e=3.4, amb=1.0),
]
INTRO_MOOD = len(MOODS) - 1

LENS = 22.0
SHIFT_Y = 0.05
CAM_HELIX = (0.0, -0.8, 5.6)
CAM_OTHER = (1.6, 2.0, 5.6)
LOOK_HELIX = (0.0, 0.0, 0.0)
LOOK_OTHER = (0.0, -1.3, -0.9)

FONT_CANDIDATES = [
    ('/usr/share/fonts/truetype/google-fonts/ofl/montserrat/Montserrat[wght].ttf', 'variable'),
    (os.path.expanduser('~/.fonts/Montserrat[wght].ttf'), 'variable'),
    (os.path.expanduser('~/Library/Fonts/Montserrat[wght].ttf'), 'variable'),
    (os.path.expanduser('~/.fonts/Poppins-{w}.ttf'), 'static'),
    (os.path.expanduser('~/Library/Fonts/Poppins-{w}.ttf'), 'static'),
]

THUMB = dict(top=dict(round=1, hit=5, mood=1, dy=-400, t=13.7), bottom=dict(round=0, hit=8, mood=0, dy=190, t=3.6),
             after_frames=7, zoom=0.32, samples=10)

if EPISODE:
    import runpy
    for _k, _v in runpy.run_path(os.path.join(HERE, 'episodes', EPISODE + '.py'), init_globals=dict(globals())).items():
        if not _k.startswith('_') and _k.isupper():
            globals()[_k] = _v
