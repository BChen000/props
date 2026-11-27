"""Every setting of the 3D marble hide-and-seek Short, in one place (shipped values).

Units: the marble radius is 1. y is up, x to the right, z toward the camera; the floor is y = 0 and the felt mat
covers the play area. Override any value per episode with EPISODE=<name> (episodes/<name>.py runs at the end of this
file and only reassigns what differs).
"""
import math
import os
import runpy

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.environ.get("BUILD_DIR", os.path.join(HERE, "build_preview" if os.environ.get("PREVIEW") else "build"))

# ----------------------------------------------------------------------------------------------- video
W, H, FPS = 1080, 1920, 30
if os.environ.get("PREVIEW"):            # quarter-size set and frames for quick checks
    W, H = 540, 960
R = 1.55                         # bigger than the kit's usual 1.0, so the seeker's eyes read on a phone
FILE = "Marble_Hide_and_Seek"
WATERMARK = os.environ.get("WATERMARK", "Marble Pop")
WATERMARK_Y = 0.968
WORKERS = int(os.environ.get("WORKERS", "2"))
CRF = int(os.environ.get("CRF", "17"))
STATIC_SAMPLES = (25, 36)        # key-light / ambient samples per pixel of the static path trace (2x size)
if os.environ.get("PREVIEW"):
    STATIC_SAMPLES = (9, 16)

# ----------------------------------------------------------------------------------------------- the cast
# (name, sRGB) of the six hiders, in chip order (the channel's ball colours, ../style-kit)
HIDERS = [("RED", (236, 65, 68)), ("BLUE", (61, 131, 247)), ("GREEN", (50, 198, 100)),
          ("YELLOW", (251, 201, 50)), ("PURPLE", (167, 91, 237)), ("ORANGE", (247, 139, 44))]
SEEKER_SRGB = (246, 246, 244)    # the seeker: a white marble with big googly eyes
EYE = dict(apart=0.42, up=0.70, size=0.43, pupil=0.21, ring=0.07, gaze=0.55)   # angles in radians on the sphere

# who hides where (spot names from layout.SPOTS). The seeker checks the spots in a fixed order: bridge, pen, the empty
# arch, corner, stack, tunnel; the hider at "base" (right behind the tower it counts against) is never found and wins.
HIDE_AT = {"GREEN": "bridge", "RED": "pen", "YELLOW": "corner", "ORANGE": "stack", "BLUE": "tunnel",
           "PURPLE": "base"}

# ----------------------------------------------------------------------------------------------- blocks and room
B = 6.4                          # cube size
ROUND = 0.16                     # rounded block edges
MC_STEP = 0.1                    # marching-cubes grid for carved pieces
RT = 2.15                        # tunnel radius
WALL_H = 2.6                     # low walls of the pen and the corner
WALL_T = 1.2
ROOM_WALL_Z = -46.0
ROOM_WALL_H = 120.0
BASEBOARD_H, BASEBOARD_D = 2.6, 0.45
MAT = (-21.0, 21.0, -34.0, 24.0)  # felt mat x0, x1, z0, z1
MAT_T = 0.22

# ----------------------------------------------------------------------------------------------- colours (sRGB)
WOOD_SRGB = (224, 200, 166)
FLOOR_SRGB = (214, 208, 200)
WALL_SRGB = (206, 208, 210)
BASEBOARD_SRGB = (238, 238, 236)
MAT_SRGB = (90, 148, 74)

# ----------------------------------------------------------------------------------------------- story timing (s)
COUNT_FROM = 5                   # the seeker counts 5..1 with its eyes shut
T_COUNT = 0.6                    # "5" appears
T_READY = T_COUNT + COUNT_FROM   # "READY OR NOT!"
SEEK_SPEED = 13.0                # seeker rolling speed (radii per second)
HIDE_SPEED = 13.5
LOOK_S = 0.9                     # the seeker pauses this long at a spot it checks
HOLD_S = 3.2                     # winner card held at the end

# ----------------------------------------------------------------------------------------------- camera and light
CAM_TARGET = (0.0, 0.0, -10.5)
CAM_AZ = math.radians(0.0)
CAM_EL = math.radians(58.0)
CAM_DIST = 120.0
CAM_FOVY = math.radians(31.0)
CAM_SHIFT = (0.0, 0.0)
LIGHT_FROM = (-0.45, 1.0, 0.18)
LIGHT_ANG = math.radians(16.0)
LIGHT_COL = (2.05, 1.98, 1.86)
SKY_Z = (0.90, 0.93, 0.98)
SKY_H = (0.78, 0.80, 0.84)
EXPOSURE = 0.92
VIG = 0.10
FOG_START, FOG_DIST = 400.0, 200.0

# ----------------------------------------------------------------------------------------------- text
TITLE = "HIDE AND SEEK"
TITLE_Y = 0.055
STATUS_Y = 0.128
CHIPS_Y = 0.200
TEXT_FILL = (255, 255, 255)
HIGHLIGHT = (255, 214, 80)       # ../style-kit HIGHLIGHT

# ----------------------------------------------------------------------------------------------- sound
SOUND_SEED = 7
MUSIC_GAIN = 0.55
MUSIC_BPM = (104, 132, 160)      # Hall of the Mountain King: sneaking, then faster as hiders are found

EPISODE = os.environ.get("EPISODE", "")
if EPISODE:
    _ep = os.path.join(HERE, "episodes", EPISODE + ".py")
    for _k, _v in runpy.run_path(_ep, init_globals=dict(globals())).items():
        if not _k.startswith("_") and _k.isupper():
            globals()[_k] = _v
WINNER = next(nm for nm, spot in HIDE_AT.items() if spot == "base")
