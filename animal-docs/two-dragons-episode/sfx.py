"""two-dragons-episode / sfx.py: the episode's sound-effect cue sheet, built with ../creature-sfx.

Writes $WORK/audio/sfx.wav (48 kHz stereo, 173.04 s). Times are in seconds of the final cut. Beds are listed in
times of the first (sped-up) cut and mapped through W(), which follows the re-timed edit shot by shot; events that
belong to an animated render (wings opening, rearing growl, roar, ignition) are placed from that render's frames.
Keep the order of the generator calls: they share one seeded noise stream, which is what makes the file reproducible.
"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "creature-sfx"))
from sfx_lib import *

WORK = os.environ.get("TWO_DRAGONS_WORK") or os.path.join(HERE, "build")
DUR = 4153 / 24.0
# shot starts (frames) in the first cut -> in the final cut, for re-timing cues written against the first cut
_OC = [0, 100, 129, 164, 282, 384, 456, 504, 562, 648, 720, 816, 961, 1056, 1148, 1223, 1279, 1466, 1523, 1570, 1694, 1730, 1769,
       1848, 1936, 2028, 2146, 2201, 2257, 2414, 2524, 2563, 2616, 2690, 2880]
_NC = [0, 145, 185, 237, 404, 557, 671, 724, 809, 938, 1042, 1188, 1380, 1510, 1654, 1764, 1849, 2125, 2204, 2266, 2452, 2508, 2555,
       2684, 2798, 2904, 3060, 3150, 3225, 3462, 3618, 3675, 3753, 3865, 4153]


def W(t):
    return float(np.interp(t * 24.0, _OC, _NC)) / 24.0


def WS(lst):
    return [(W(a), W(b), g) for a, b, g in lst]


T = Track(DUR, seed=11)
N = T.N

# ---------------- beds ----------------
wind = wind_bed(T.rng, N)
for t0, t1, g in WS([(0.0, 6.9, 1.0), (6.8, 11.8, 0.5), (11.7, 16.1, 1.0), (47.8, 53.4, 0.9), (108.9, 120.0, 0.9), (34.0, 40.1, 0.5),
                     (80.6, 89.5, 0.45), (72.0, 73.8, 0.4), (91.6, 94.1, 0.3)]):
    T.bed(wind, t0, t1, g, 0.6)

volc = volcano_bed(T.rng, N, cracks=1600)
for t0, t1, g in WS([(16.0, 34.1, 1.0), (70.5, 72.2, 0.9), (73.6, 80.8, 1.0), (89.3, 91.8, 0.7), (100.5, 105.2, 0.5), (4.1, 5.45, 0.6),
                     (94.0, 95.7, 0.5), (105.1, 106.9, 0.8), (63.4, 65.5, 0.8)]):
    T.bed(volc, t0, t1, g, 0.4)

river = river_bed(T.rng, N, bubbles=5000)
for t0, t1, g in [(W(61.0), 2204 / 24.0 + 0.12, 1.0), (2266 / 24.0 - 0.42, W(70.5), 1.0)] + WS([(72.1, 73.8, 1.0)]):
    T.bed(river, t0, t1, g, 0.8)

rain = rain_bed(T.rng, N, ticks=20000)
for t0, t1, g in WS([(53.3, 61.2, 0.85), (106.8, 109.1, 1.0)]) + [(2266 / 24.0 - 0.42, W(70.7), 0.6), (95.2, W(70.7), 0.6)]:
    T.bed(rain, t0, t1, g, 0.4)

gust = gust_bed(T.rng, N)
T.bed(gust, W(53.3), W(61.2), 1.0, 0.5)

# ---------------- events ----------------
for f0, sd in ((64, 48), (173, 95), (228, 150)):             # sh12 lightning flashes (frames into the shot)
    T.add(thunder(T.rng, seed=sd), (1849 + f0) / 24.0 + 0.12, 0.5)
T.add(thunder(T.rng, 3.5, crack=False, seed=9), 3675 / 24.0 + 0.01, 0.5)   # sh22 opens on a flash

T.flaps(0, 145, 0.35); T.flaps(404, 153, 0.18); T.flaps(2555, 129, 0.8); T.flaps(3753, 112, 0.35); T.flaps(3865, 212, 0.25)
ROAR_T = (2684 + 31.2) / 24.0                                  # u16b_n frame 31: jaw fully open
T.add(whoosh(T.rng, 2.4, 120, 1200, 0.45), (557 + 100) / 24.0 - 0.45 * 2.4, 0.9)   # u05a_n wings opening
T.add(whoosh(T.rng, 1.8, 90, 700, 0.5), ROAR_T - 0.9, 0.9)
T.add(whoosh(T.rng, 3.5, 100, 900, 0.35), (1380 + 74) / 24.0 - 0.35 * 3.5, 1.0)    # u09a_n passes the camera
T.add(whoosh(T.rng, 2.0, 150, 1500, 0.5), W(52.0) - 1.0, 0.8)
T.add(whoosh(T.rng, 3.0, 120, 1100, 0.5), W(86.3) - 1.5, 0.7)
T.add(whoosh(T.rng, 2.2, 100, 900, 0.5), W(67.6) - 1.1, 0.6)
T.add(whoosh(T.rng, 1.6, 150, 1300, 0.5), W(107.8) - 0.8, 0.6)

T.add(growl(3.2, 46, 1, 0.8), (809 + 43.2) / 24.0)              # u06_n starts to rear
T.add(roar(2.1, 92, 3, 0.34), ROAR_T)

T_FIRE = 1042 / 24.0                                            # sh07b: fire on from its first frame, faded by frame 140
T.add(fire_roar(T.rng, (1042 + 140) / 24.0 + 0.08 - T_FIRE, 1, 0.34), T_FIRE)
T.add(whoosh(T.rng, 1.0, 200, 3000, 0.6), T_FIRE - 0.5, 0.4)
T.add(fire_roar(T.rng, 1.3, 2, 0.35, attack=0.5), (938 + 91) / 24.0)        # u07a_n ignition
T.add(fire_roar(T.rng, 2.6, 3, 0.55, attack=0.05), 2204 / 24.0 - 0.01)     # sh14a
T.add(fire_roar(T.rng, 2.45, 4, 0.55, attack=0.05), 3618 / 24.0 - 0.01)    # sh21

os.makedirs(os.path.join(WORK, "audio"), exist_ok=True)
print("raw peak", T.write(os.path.join(WORK, "audio", "sfx.wav")))
print("sfx done", os.path.join(WORK, "audio", "sfx.wav"))
