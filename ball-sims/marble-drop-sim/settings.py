"""Settings for marble-drop-sim. Every path is relative to this folder."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))

SET_DIR = os.path.join(HERE, '..', 'xylophone-ramp')            # params.py + build/ of the set
SCENE_META = os.path.join(SET_DIR, 'build', 'scene_meta.json')   # camera, used to start marbles just above the frame
BASKET_TUBE = os.path.join(SET_DIR, 'build', 'basket_tube.npz')  # basket rope mesh, used as the collider
BUILD_DIR = os.path.join(HERE, 'build')

# How to run the bpy scripts (sim.py) from calibrate.py and the template:
# None = this same Python with `pip install bpy==5.3.0`; or e.g. ['blender', '--background', '--python']
BLENDER_CMD = None

# ---------------------------------------------------------------- physics (Blender rigid body / Bullet)
PHYS = dict(bar_fric=0.5, bar_rest=0.65, bask_fric=0.8, bask_rest=0.45,
            m_fric=0.6, m_rest=0.42, lin=0.8, ang=0.9)   # lin/ang damping slow the roll to ~1.5 s per ramp
PREROLL = 0.3          # seconds simulated before the video starts
SUBSTEPS = 4           # per 1/240 s frame
SOLVER_ITERS = 30
WORLD_SCALE = 10.0     # simulate 10x bigger (with 10x gravity) for stable contacts

# ---------------------------------------------------------------- invisible safety guards
# None of the marbles touched them in either video; they only stop rare escapes.
SIDE_GUARD_GAP = 0.012     # beyond each bar end
SIDE_GUARD_HEIGHT = 0.08
RIM_GUARD = dict(r=0.158, z0=0.06, z1=0.10)

# ---------------------------------------------------------------- drops
SPAWN_MARGIN = 0.008       # marbles start this far above the top edge of the frame
