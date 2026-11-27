"""Every setting of the "30 GLASS vs 10 STEEL" balance Short, in one place (shipped values).

Units: the marble radius is 1 (call it a centimetre), gravity is real, and y is up, x to the right, z toward the
camera; the floor is y = 0 and the seesaw's pivot is on the z axis through PIVOT. The beam angle THETA is
counter-clockwise as the camera sees it, so THETA > 0 lifts the right (steel) side.
Override any value per episode with EPISODE=<name> (episodes/<name>.py runs at the end and reassigns what differs).
"""
import math
import os
import runpy

HERE = os.path.dirname(os.path.abspath(__file__))
PREVIEW = bool(os.environ.get("PREVIEW"))
BUILD = os.environ.get("BUILD_DIR", os.path.join(HERE, "build_preview" if PREVIEW else "build"))

# ----------------------------------------------------------------------------------------------- video
W, H, FPS = (540, 960, 30) if PREVIEW else (1080, 1920, 30)
FILE = "Glass_vs_Steel_Balance"
WATERMARK = os.environ.get("WATERMARK", "Marble Pop")
WATERMARK_Y = 0.968
WORKERS = int(os.environ.get("WORKERS", "2"))
CRF = int(os.environ.get("CRF", "17"))
SAMPLES = (16, 25)          # boxtrace key-light and ambient samples per pixel of the 2x set (clean once halved)

# ----------------------------------------------------------------------------------------------- the two teams
R = 1.0
G = 981.0 * 5.0 / 7.0      # marbles roll, so they speed up at 5/7 g on a slope; falls use the same value
# name, count, mass per marble (glass 2.5 g/cm3 vs steel 7.85 g/cm3: same size, 3.14 times the mass), colour, metal
LEFT = dict(name="GLASS", n=30, mass=1.0, srgb=(236, 60, 64), metal=False)
RIGHT = dict(name="STEEL", n=10, mass=7.85 / 2.5, srgb=(206, 210, 218), metal=True)

# ----------------------------------------------------------------------------------------------- the seesaw
PIVOT = (0.0, 16.0, 0.0)
THETA_MAX = math.radians(8.0)   # the beam rests on a stop post at either end of its swing
BEAM_HALF, BEAM_T, BEAM_HZ = 16.5, 1.0, 1.6
ARM = 12.5                      # pivot to the middle of each basket
BASKET_HX, BASKET_HZ = 4.6, 3.0  # inside half-width (x) and half-depth (z)
BASKET_WALL = 0.5
BASKET_H = 5.0                  # side and back walls, above the basket floor
BASKET_FRONT_H = 2.0            # a low front wall, so the camera sees in
BEAM_MASS = 80.0                # beam + both baskets, in glass-marble masses (sets how heavy the swing feels)
PIVOT_DAMP = 0.08               # bearing friction (fraction of critical, for a 1-marble imbalance)
STOP_K, STOP_ZETA = 1.0e8, 0.35

# ----------------------------------------------------------------------------------------------- the two tracks
# Planks are given by the left and right ends of their top surface. Glass: one long, nearly flat shelf from
# off-screen left to a lip above the left basket. Steel: a zigzag of three planks from off-screen right, with end
# stops at the turns; the last one drops the ball into the right basket.
GLASS_RAMP = ((-75.0, 30.4), (-17.0, 29.8))
GLASS_SPAWN = (-42.0, 14.0)     # where each glass marble starts (x) and its push (units/s)
STEEL_ZIG = [((12.6, 39.0), (48.0, 41.1)),           # rolls left
             ((9.8, 35.5), (20.4, 34.2)),            # rolls right
             ((18.6, 29.4), (23.2, 30.2))]           # rolls left, off the end into the basket
STEEL_SPAWN = (45.0, -8.0)
STEEL_WALLS = [(9.2, 9.8, 34.3, 42.7), (23.2, 23.8, 28.8, 37.7)]   # x0, x1, y0, y1 end stops at the turns
TRACK_HZ = 1.25                 # half-width inside the rails
RAIL_H = 1.0

# ----------------------------------------------------------------------------------------------- the race
# When each marble lands in its basket (seconds). Glass comes in waves, steel one at a time; the totals are
# designed so the lead changes hands and the 10th steel ball decides it. schedule.py checks the design.
LAND_RIGHT = [0.6, 4.0, 5.2, 9.4, 10.6, 11.8, 16.6, 17.6, 18.6, 20.6]
LAND_LEFT = ([1.4 + 0.25 * k for k in range(8)] + [6.2 + 0.25 * k for k in range(10)] +
             [12.8 + 0.25 * k for k in range(12)])
HOLD_S = 3.4                    # winner card after the decisive tip
T_LEAD = 3.0                    # the physics starts this long before the video, so the first marbles are on their way
SIM_HZ = 6000
REC_HZ = 240

# ----------------------------------------------------------------------------------------------- look (sRGB)
WALL_SRGB = (200, 210, 222)
FLOOR_SRGB = (214, 180, 132)
WOOD_SRGB = (222, 190, 140)
STAND_SRGB = (150, 102, 62)
LEFT_BASKET_SRGB = (64, 120, 226)
RIGHT_BASKET_SRGB = (226, 196, 146)
PIN_SRGB = (60, 62, 68)

# ----------------------------------------------------------------------------------------------- camera and light
CAM_TARGET = (0.0, 23.0, 0.0)
CAM_AZ = math.radians(0.0)
CAM_EL = math.radians(17.0)
CAM_DIST = 162.0
CAM_FOVY = math.radians(31.0)
CAM_SHIFT = (0.0, 0.0)
LIGHT_FROM = (-0.42, 1.0, 0.62)
LIGHT_ANG = math.radians(11.0)
LIGHT_COL = (2.15, 2.08, 1.96)
SKY_Z = (0.62, 0.66, 0.72)
SKY_H = (0.58, 0.60, 0.64)
EXPOSURE = 0.86
VIG = 0.10
FOG_START, FOG_DIST = 400.0, 200.0

# ----------------------------------------------------------------------------------------------- text
TITLE1 = f"{LEFT['n']} {LEFT['name']} vs {RIGHT['n']} {RIGHT['name']}"
TITLE2 = "WHICH SIDE WINS?"
TITLE_Y = 0.052
COUNT_Y = 0.142
STATUS_Y = 0.80
TEXT_FILL = (255, 255, 255)
HIGHLIGHT = (255, 214, 80)

SOUND_SEED = 7

EPISODE = os.environ.get("EPISODE", "")
if EPISODE:
    _ep = os.path.join(HERE, "episodes", EPISODE + ".py")
    for _k, _v in runpy.run_path(_ep, init_globals=dict(globals())).items():
        if not _k.startswith("_") and _k.isupper():
            globals()[_k] = _v
