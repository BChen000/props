"""Every setting of the "Last One Spinning Wins" Short, in one place (shipped values).

Units: the marble radius is R. y is up, x to the right, z toward the camera; the table top is y = 0 and the dish is
centred on the origin. Override any value per episode with EPISODE=<name> (episodes/<name>.py runs at the end of
this file and only reassigns what differs).
"""
import math
import os
import runpy

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.environ.get("BUILD_DIR", os.path.join(HERE, "build_preview" if os.environ.get("PREVIEW") else "build"))

# ----------------------------------------------------------------------------------------------- video
W, H, FPS = 1080, 1920, 30
if os.environ.get("PREVIEW"):
    W, H = 540, 960
FILE = "Last_One_Spinning_Wins"
WATERMARK = os.environ.get("WATERMARK", "Marble Pop")
WATERMARK_Y = 0.968
WORKERS = int(os.environ.get("WORKERS", "2"))
CRF = int(os.environ.get("CRF", "17"))
STATIC_SAMPLES = (25, 36)
if os.environ.get("PREVIEW"):
    STATIC_SAMPLES = (9, 16)

# ----------------------------------------------------------------------------------------------- marbles
R = 1.3
MARBLES = [("RED", (236, 65, 68)), ("BLUE", (61, 131, 247)), ("GREEN", (50, 198, 100)), ("YELLOW", (251, 201, 50)),
           ("PURPLE", (167, 91, 237)), ("ORANGE", (247, 139, 44)), ("PINK", (255, 105, 180)), ("CYAN", (40, 205, 220))]

# ----------------------------------------------------------------------------------------------- the dish
RD = 15.5                 # inner radius of the rim (where a marble's surface touches it: centre at RD - R)
RIM_T = 1.6               # rim thickness
RIM_H = 3.4               # rim height above the dish floor at the edge
FLOOR_Y = 3.4             # dish floor height (at the rim) above the table: a thick turned platter
RH = 2.55                 # hole radius
S0, S1 = 0.030, 0.0035    # floor: gentle cone toward the hole + bowl rising to the rim
DEP, SIG = 1.4, 4.6       # funnel dip around the hole
PEGS = [(r * math.cos(a), r * math.sin(a)) for r, a in ((9.0, math.radians(30)), (9.0, math.radians(150)),
                                                         (9.0, math.radians(270)))]
PEG_R = 0.75              # wooden pegs that marbles bounce off
PEG_H = 2.6
TABLE = (-60.0, 60.0, -70.0, 50.0)
MC_STEP = 0.1
ROUND = 0.16

# ----------------------------------------------------------------------------------------------- physics
SEED = int(os.environ.get("SEED", "0"))           # 0: use SHIPPED_SEED
SHIPPED_SEED = 1207
SIM_T = 60.0
V_SPIN = (31.0, 42.0)     # launch speeds along the rim, spread evenly and shuffled (radii per second)
CRR, GAM = 0.45, 0.006     # rolling resistance (units/s^2) and linear drag (1/s)
WALL_E = 0.55             # restitution off the rim
PEG_E = 0.75              # restitution off the pegs
NEAR_MISS = 0.75          # a marble passing this close to the hole's edge without falling counts as SO CLOSE

# ----------------------------------------------------------------------------------------------- timing
SLOWMO = 0.55             # playback speed for the final duel
HOLD_S = 3.0              # winner card after the last one is crowned
CLOSE_FROM, CLOSE_TO = 1.2, 1.6   # the close-up of the last drop: at most this long before and after it (sim s),
                                  # and only while every marble in play stays inside the close camera's frame

# ----------------------------------------------------------------------------------------------- light-ups
PEG_FLASH = (1.4, 0.26)   # a peg lights up in the colour of the marble that hit it: (strength at a hard hit, decay s)
HOLE_FLASH = (1.3, 0.35)  # the hole glows in the colour of each marble it swallows

# ----------------------------------------------------------------------------------------------- colours (sRGB)
DISH_SRGB = (172, 118, 72)                         # darker than the table, as in the original
PEG_SRGB = (96, 60, 36)                            # dark walnut pegs that flash in colour when hit
TABLE_SRGB = (226, 196, 152)

# ----------------------------------------------------------------------------------------------- cameras and light
CAMS = {
    "main": dict(target=(0.0, 1.6, 0.5), el=60.0, dist=122.0, fovy=31.0),
    "close": dict(target=(0.0, 2.2, 0.5), el=48.0, dist=64.0, fovy=31.0),
}
CAM = os.environ.get("SPIN_CAM", "main")
CAM_TARGET = CAMS[CAM]["target"]
CAM_AZ = math.radians(0.0)
CAM_EL = math.radians(CAMS[CAM]["el"])
CAM_DIST = CAMS[CAM]["dist"]
CAM_FOVY = math.radians(CAMS[CAM]["fovy"])
CAM_SHIFT = (0.0, 0.0)
LIGHT_FROM = (-0.45, 1.0, 0.18)
LIGHT_ANG = math.radians(16.0)
LIGHT_COL = (2.05, 1.98, 1.86)
SKY_Z = (0.90, 0.93, 0.98)
SKY_H = (0.78, 0.80, 0.84)
EXPOSURE = 0.92
VIG = 0.12
FOG_START, FOG_DIST = 400.0, 200.0
WALL_SRGB = (206, 208, 210)                       # unused backdrop colour (rays never miss the table)
FLOOR_SRGB = TABLE_SRGB

# ----------------------------------------------------------------------------------------------- text
TITLE1, TITLE2 = "LAST ONE SPINNING", "WINS"
TITLE_Y = 0.050
CHIPS_Y = 0.150
STATUS_Y = 0.765
TEXT_FILL = (255, 255, 255)
HIGHLIGHT = (255, 214, 80)

# ----------------------------------------------------------------------------------------------- sound
SOUND_SEED = 7

EPISODE = os.environ.get("EPISODE", "")
if EPISODE:
    _ep = os.path.join(HERE, "episodes", EPISODE + ".py")
    for _k, _v in runpy.run_path(_ep, init_globals=dict(globals())).items():
        if not _k.startswith("_") and _k.isupper():
            globals()[_k] = _v
