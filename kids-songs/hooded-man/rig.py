"""The hooded man's rest pose: pivots in metres. Z is up, he faces -Y, and his right side is -X (screen-left)."""
import numpy as np

HIPS = np.array([0.0, 0.0, 0.98])
HEAD = np.array([0.0, 0.010, 1.553])
SHOULDER = {'R': np.array([-0.172, 0.014, 1.402]), 'L': np.array([0.172, 0.014, 1.402])}
UPPER, FORE = 0.285, 0.255
SIDE = {'R': -1.0, 'L': 1.0}

COLORS = {
    'skin': (0.40, 0.40, 0.41),
    'hat': (0.21, 0.21, 0.22),
    'band': (0.035, 0.035, 0.04),
    'hoodie': (0.030, 0.031, 0.035),
    'hoodie_rib': (0.022, 0.022, 0.026),
    'string': (0.05, 0.05, 0.055),
    'aglet': (0.55, 0.56, 0.58),
    'pants': (0.035, 0.04, 0.055),
    'shoe': (0.02, 0.02, 0.02),
    'sole': (0.35, 0.35, 0.35),
}

HAND_POSES = {
    'relax': dict(prox=22, dist=28, spread=3, thumb=(25, 15), index=None),
    'open': dict(prox=4, dist=4, spread=7, thumb=(10, 5), index=None),
    'point': dict(prox=88, dist=100, spread=0, thumb=(55, 45), index=(2, 2)),
    'fist': dict(prox=90, dist=105, spread=0, thumb=(60, 50), index=None),
}
