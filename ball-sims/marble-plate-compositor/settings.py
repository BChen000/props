"""Settings for marble-plate-compositor. Every path is relative to this folder."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- inputs / outputs
SET_DIR = os.path.join(HERE, '..', 'xylophone-ramp')          # Blender set prop (params.py, .blend, build/)
BLEND = os.path.join(SET_DIR, 'xylophone-ramp.blend')
SCENE_META = os.path.join(SET_DIR, 'build', 'scene_meta.json')  # written by xylophone-ramp/build_set.py
PLATE_DIR = os.path.join(HERE, 'build', 'plate')                # written by render_plates.py
PROBES_FILE = os.path.join(HERE, 'build', 'probes_proc.npz')    # written by probes.py

# ---------------------------------------------------------------- plate render quality (Cycles, CPU)
BEAUTY_SPP = 128       # full-size beauty plate (about 14 min on 2 CPU cores)
LIGHT_SPP = 64         # key-only and top-only direct light, rendered at half size
PROBE_RES = 128        # cube-map face size of each lighting probe
PROBE_SPP = 96
LIGHT_NAMES = ['key', 'top', 'fill']   # lights in the .blend; key and top cast the marble shadows

# ---------------------------------------------------------------- marble looks
# Glossy marbles: linear-RGB albedo under a clear coat. Metal marbles: linear-RGB F0.
PALETTE = {
    'red': (0.78, 0.018, 0.022), 'orange': (0.95, 0.26, 0.008), 'yellow': (0.98, 0.70, 0.02),
    'green': (0.09, 0.58, 0.05), 'teal': (0.0, 0.50, 0.47), 'blue': (0.012, 0.17, 0.88),
    'purple': (0.36, 0.05, 0.75), 'pink': (0.97, 0.21, 0.48),
}
METALS = {'gold': (1.0, 0.70, 0.28), 'silver': (0.93, 0.93, 0.95)}

# ---------------------------------------------------------------- frame rendering
W, H = 1080, 1920
FPS = 30
EXPOSURE = 1.1               # applied before the tone curve
SAMPLES_PER_PIXEL = 8        # antialiasing + motion blur samples inside marble regions
SHUTTER = 1 / 100            # seconds of motion blur
SHADOW_TIME_SAMPLES = 2
BAR_REFLECTION = 0.42        # how strongly the aluminum bars mirror the marbles
BAR_OBJECT_IDS = (2, 3)      # pass_index of bars and screws in the .blend
X264_PRESET = 'veryfast'
CRF = 17
