"""Marble Milestone Post: every setting in one place (most can be overridden from the environment).

A square still of glossy team-colour marbles spelling a number ("500") on the lacquered hardwood board of
../marble-funnel-drain, rendered with that prop's ray-caster. This file is also the `settings` module that
render.py imports: it takes the drain's look and palette unchanged and overrides the canvas size.
"""
import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DRAIN = os.environ.get("DRAIN_DIR", os.path.join(HERE, "..", "marble-funnel-drain"))
BUILD = os.environ.get("BUILD_DIR", os.path.join(HERE, "build"))

_spec = importlib.util.spec_from_file_location("_drain_settings", os.path.join(DRAIN, "settings.py"))
_drain = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_drain)


def _env(name, default, kind=float):
    v = os.environ.get(name)
    return default if v in (None, "") else kind(v)


# --------------------------------------------------------------------------- what to spell
TEXT = _env("TEXT", "500", str)
FONT = _env("FONT", "Poppins-Regular.ttf", str)   # style-kit font, used for its skeleton only (see STROKE)
HEIGHT = _env("HEIGHT", 22.0)       # cap height in marble radii (11 marbles tall)
STROKE = _env("STROKE", 4.15)       # monoline pen width: two marbles side by side in every stroke, with round ends
TRACK = _env("TRACK", 3.0)          # extra gap between characters
SPACING = 2.06                      # centre-to-centre distance along a lane (2.0 = touching)
LAYOUT_SEED = 1

# --------------------------------------------------------------------------- colours
COLOURS = _env("COLOURS", "RED,BLUE,GREEN,YELLOW", str).split(",")   # teams from PALETTE, mixed so neighbours differ
COLOUR_SEED = _env("COLOUR_SEED", 1, int)
PALETTE = _drain.PALETTE

# --------------------------------------------------------------------------- where it sits and the camera
HOLE_IN = _env("HOLE_IN", 1, int)   # which character's opening is centred on the funnel hole (-1: the whole text)
CAM = dict(T=(_env("CAM_X", -0.6), _env("CAM_Y", -7.0), 0.0),   # aim point on the board (the hole is the origin)
           D=_env("CAM_D", 123.0),                              # distance: larger = smaller text
           yaw=0.0, elev=60.0, hf=0.25,
           kd=_env("CAM_KD", 30.0))                             # depth-of-field blur in px at 1080 wide

# --------------------------------------------------------------------------- output
SIZE = _env("SIZE", 2160, int)       # square render; 2160 downsamples to a crisp 1080 post image
OUT_SIZE = _env("OUT_SIZE", 1080, int)
OUT_NAME = _env("OUT_NAME", "milestone_%s" % TEXT.lower(), str)

# --------------------------------------------------------------------------- read by ../marble-funnel-drain/render.py
W = H = SIZE
LOOK = dict(_drain.LOOK)
NBR = _drain.NBR
TEAM_COLOURS = True
