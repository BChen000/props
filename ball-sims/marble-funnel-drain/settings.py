"""Marble Funnel Drain: every setting you would change, in one place.

Physics and board, which marbles get colours, the look (lights, wood, exposure), the camera shots, slow motion,
the loop, the thumbnail shot and the encoding. Everything else in this folder reads from here.
Units: the marble radius is 1 (so a marble is 2 units wide); sim time and video time are in seconds.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.environ.get("BUILD_DIR", os.path.join(HERE, "build"))

# --------------------------------------------------------------------------- episode
SEED = int(os.environ.get("SEED", 3))
USE_RECORDED_SIM = os.environ.get("USE_RECORDED_SIM", "1") == "1"   # replay assets/drain_seed<SEED>.npz if it exists
RECORDED_SIM = os.path.join(HERE, "assets", f"drain_seed{SEED}.npz")
OUT_NAME = os.environ.get("OUT_NAME", "marble_funnel_drain")

# --------------------------------------------------------------------------- physics (sim.py)
SIM = dict(
    N=480, T=40.0, seed=SEED,
    pour=3.2,                                   # marbles are released over this many seconds
    vx0=-28.0, vy0=-24.0,                       # launch velocity (down and to the left)
    sx0=-10.0, sx1=10.0, sy0=52.5, sy1=55.5,    # spawn band, beyond the top of every shot
    S0=0.02, S1=0.003,                          # board: gentle cone + bowl rising toward the walls
    DEP=2.5, SIG=6.5,                           # funnel: depth and width of the dip around the hole
    RH=2.2,                                     # hole radius used by the physics
    zeta=0.5,                                   # marble-marble collision damping ratio
    crr=4.0, gam=0.15,                          # rolling resistance (units/s^2) and linear drag (1/s)
    mu_t=0.08,                                  # tangential friction between marbles
    BA=22.6, BB=47.3, BYC=9.7, BRC=13.0,        # invisible walls: rounded rectangle half-width, half-height, centre y, corner radius
)

# --------------------------------------------------------------------------- colours (picked from the drain order)
PLACES = ["GREEN", "BLUE", "RED", "YELLOW"]    # 1st = last marble into the hole, 2nd, 3rd, 4th
FOURTH_OUT_AT = 15.7                           # 4th place: the marble draining closest to this sim time (+-0.5 s)
TEAM_COLOURS = False                           # True: every marble wears one of the PLACES colours (equal teams), and
                                               # each place's marble is the last of its colour, so its drop knocks that
                                               # colour out; False: the 4 place marbles are coloured, the rest chrome
TEAM_SEED = 1                                  # with TEAM_COLOURS: which marbles get which colour (the race is the same)
PALETTE = {                                    # linear-light albedo; chrome marbles have none
    "RED": (0.90, 0.03, 0.02),
    "BLUE": (0.03, 0.17, 0.95),
    "GREEN": (0.04, 0.72, 0.06),
    "YELLOW": (0.98, 0.72, 0.02),
}

# --------------------------------------------------------------------------- look (render.py)
W, H, FPS = 1080, 1920, 30
LOOK = dict(
    S0=SIM["S0"], S1=SIM["S1"], DEP=SIM["DEP"], SIG=SIM["SIG"],
    RH=2.05,                                    # hole radius as drawn (the shipped video drew it smaller than the physics hole)
    L=(-0.25, 0.45, 1.0),                       # key softbox direction (above, slightly back-left)
    L2=(-0.55, -0.55, 0.62),                    # white fill strip, front-left (reflections only)
    L3=(0.85, 0.45, 0.32), C3=(0.8, 1.4, 3.6),  # blue accent strip, back-right, low (reflections only)
    L4=(-0.85, 0.35, 0.30), C4=(3.2, 0.8, 2.4), # magenta accent strip, back-left, low (reflections only)
    KI=2.0, KA=0.9,                             # key and ambient strength on the floor and the coloured marbles
    ALPHA=0.13,                                 # key light angular radius (soft shadows)
    SB=14.0, SB2=3.0,                           # softbox and fill strip brightness in reflections
    BEND=0.1,                                   # how much the wood grain bends into the funnel
    EXPO=0.26, F0F=0.05,                        # exposure; floor lacquer reflectance at normal incidence
    BLOOM=0.22, VIG=0.38,                       # highlight glow; vignette
    WOOD_SEED=7,
    EARLY=(0.44, 0.22, 0.10), LATE=(0.20, 0.085, 0.035),   # hardwood earlywood / latewood albedo
)

# --------------------------------------------------------------------------- camera shots (timeline.py)
# A shot is a target point T, distance D, heading yaw (deg, 0 = looking toward +y), elevation (deg above the
# board), hf = tan(half horizontal field of view), and kd = depth-of-field blur at infinity in pixels (0 = off).
SHOTS = dict(
    OPEN=dict(T=(-9.0, 30.5, 1.5), D=24.0, yaw=0.0, elev=56.0, hf=0.27, kd=12.0),    # close-up as the flood pours in
    MAIN=dict(T=(0.0, 1.0, 0.0), D=118.0, yaw=0.0, elev=66.0, hf=0.20, kd=0.0),      # angled overview
    MAIN2=dict(T=(0.0, 0.5, 0.0), D=86.0, yaw=0.0, elev=63.0, hf=0.20, kd=0.0),      # end of the slow push-in
    CLOSE=dict(T=(0.0, -16.6, 1.6), D=20.0, yaw=0.0, elev=29.0, hf=0.24, kd=28.0),   # low close-up of the swirl's edge
    FINALE=dict(T=(0.0, 0.0, -0.2), D=18.0, yaw=20.0, elev=40.0, hf=0.27, kd=16.0),  # the last marbles at the hole
)
# (sim time, shot): the camera holds between equal neighbours and eases between different ones
KEYS = [(0.0, "OPEN"), (1.05, "OPEN"), (2.55, "MAIN"), (6.6, "MAIN"), (7.25, "CLOSE"), (8.65, "CLOSE"), (9.3, "MAIN"),
        (10.2, "MAIN"), (19.85, "MAIN2"), (20.45, "FINALE"), (25.65, "FINALE"), (26.95, "OPEN")]

# --------------------------------------------------------------------------- timing (timeline.py)
# playback speed (sim seconds per video second) at sim times, eased between points
SPEED = [(0.0, 0.55), (1.15, 0.55), (1.75, 1.0), (6.6, 1.0), (7.2, 0.45), (8.7, 0.45), (9.3, 1.0), (12.0, 1.0),
         (12.6, 1.3), (19.2, 1.3), (19.9, 0.7), (25.6, 0.7), (26.0, 1.15), (60.0, 1.15)]
T0 = 0.3          # sim time of video frame 0 (the first marbles are just entering the opening shot)
T_END = 26.95     # sim time of the last frame (back at the opening shot, empty board: the loop point)
SHUT = 0.45       # motion blur: shutter as a fraction of a frame
NBR = 5.5         # neighbour radius for marble-to-marble reflections

# --------------------------------------------------------------------------- thumbnail (no text)
THUMB = dict(t=8.2, T=(-0.3, -17.9, 1.6), D=16.0, yaw=40.0, elev=33.0, hf=0.27, kd=30.0)

# --------------------------------------------------------------------------- build
WORKERS = 2
SPLIT_AT = 385     # first frame of the second worker (balances the shipped timeline on 2 cores)
CRF, PRESET = 17, "fast"
VOLUME_DB = -2.5   # applied when muxing; the shipped soundtrack lands at -14.1 LUFS

# --------------------------------------------------------------------------- other episodes
# The values above are the shipped first episode (seed 3). EPISODE=<name> runs episodes/<name>.py right here, so an
# episode file only has to reassign what differs (seed, colours, close-up and thumbnail aim, finale timing).
EPISODE = os.environ.get("EPISODE", "")
if EPISODE:
    _ep = os.path.join(HERE, "episodes", EPISODE + ".py")
    with open(_ep, encoding="utf-8") as _f:
        exec(compile(_f.read(), _ep, "exec"))
