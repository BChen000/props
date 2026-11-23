"""Drop schedule that makes the marbles PLAY A SONG on the xylophone (the Twinkle Twinkle video).

Every marble is timed so its first hit lands on the bar of the next note, exactly on the beat.
Run:  python3 calibrate.py   (once)   then   python3 melody.py   ->  build/melody.json
      python3 sim.py build/melody.json build/melody_sim.npz
To play another song, change MELODY (note names must exist on the ramp: see SCALE in xylophone-ramp/params.py).
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from setlink import *
import numpy as np

# ======================================================================= SETTINGS
SEED = 11
DURATION = 12.6
BEAT = 0.5                    # seconds per quarter note (120 BPM)
FIRST_HIT = 0.2               # time of the first note (marble is already falling at frame 0)
# (note, beat). "Twinkle twinkle little star, how I wonder what you are" in C, octave 6.
MELODY = [('C6', 0), ('C6', 1), ('G6', 2), ('G6', 3), ('A6', 4), ('A6', 5), ('G6', 6),
          ('F6', 8), ('F6', 9), ('E6', 10), ('E6', 11), ('D6', 12), ('D6', 13), ('C6', 14)]
SINGLE_NOTES = 7              # the first 7 notes use one marble each; the rest use pairs
SINGLE_LANES = (-0.022, 0.022)
SINGLE_COLORS = ['red', 'orange', 'yellow', 'green', 'teal', 'blue', 'purple']
PAIR_LANES = ((-0.058, -0.018), (0.018, 0.058))
PAIR_COLORS = [('pink', 'gold'), ('silver', 'red'), ('orange', 'yellow'), ('green', 'teal'), ('blue', 'purple'),
               ('pink', 'silver'), ('gold', 'red')]
ARP = [('C7', 'red'), ('E7', 'yellow'), ('G7', 'teal'), ('C8', 'purple')]   # sparkle after the tune
ARP_BEAT = 15.5
ARP_STEP = 0.125
ARP_LANES = [-0.016, 0.016, -0.048, 0.048]
TOTAL_MARBLES = 50            # the rainbow pour uses whatever is left
POUR_DELAY = 0.2              # after the last arpeggio note
POUR_SPAN = 1.0
POUR_BARS = list(range(6, -1, -1))
POUR_LANES = [-0.048, -0.016, 0.016, 0.048]
POUR_COLORS = ['orange', 'green', 'blue', 'pink', 'gold', 'red', 'yellow', 'teal', 'purple', 'silver']
CALIB = os.path.join(BUILD_DIR, 'fall_calib.json')
OUT = os.path.join(BUILD_DIR, 'melody.json')
# ===================================================================== END SETTINGS

rng = np.random.default_rng(SEED)
cal = {int(k): v for k, v in json.load(open(CALIB)).items()}
marbles = []


def drop(bar, x, t_hit, color, role, jitter=0.0):
    s = bar * BAR_P + BAR_W / 2 + jitter
    p = ramp_point(s, x, 0)
    marbles.append(dict(t=float(t_hit - cal[bar]), pos=[float(x), float(p[1]), spawn_z(p[1])], color=color,
                        role=role, bar=int(bar), t_hit=float(t_hit)))


for i, (nt, b) in enumerate(MELODY[:SINGLE_NOTES]):
    drop(bar_for(nt), SINGLE_LANES[i % 2], FIRST_HIT + b * BEAT, SINGLE_COLORS[i % len(SINGLE_COLORS)], 'melody')
for i, (nt, b) in enumerate(MELODY[SINGLE_NOTES:]):
    for j, x in enumerate(PAIR_LANES[i % 2]):
        drop(bar_for(nt), x, FIRST_HIT + b * BEAT, PAIR_COLORS[i % len(PAIR_COLORS)][j], 'melody2')
t_arp0 = FIRST_HIT + ARP_BEAT * BEAT
for j, (nt, col) in enumerate(ARP):
    drop(bar_for(nt), ARP_LANES[j % len(ARP_LANES)], t_arp0 + j * ARP_STEP, col, 'arp')
lanes = np.array(POUR_LANES)
nrest = TOTAL_MARBLES - len(marbles)
slots = []
for bar in POUR_BARS:
    for l_i in rng.permutation(len(lanes)):
        slots.append((lanes[l_i], bar))
slots = slots[:nrest]
t_r0 = t_arp0 + (len(ARP) - 1) * ARP_STEP + POUR_DELAY
times = t_r0 + POUR_SPAN * (np.arange(nrest) + rng.uniform(0.1, 0.9, nrest)) / nrest
for k in range(nrest):
    x, bar = slots[k]
    drop(bar, x + rng.uniform(-0.001, 0.001), times[k], POUR_COLORS[k % len(POUR_COLORS)], 'pour', jitter=rng.uniform(-0.002, 0.002))

cfg = base_cfg(DURATION)
cfg['marbles'] = marbles
os.makedirs(BUILD_DIR, exist_ok=True)
json.dump(cfg, open(OUT, 'w'), indent=0)
print('saved', OUT, len(marbles), 'marbles; tune ends', FIRST_HIT + MELODY[-1][1] * BEAT, 's; pour', round(t_r0, 3), '->', round(float(times[-1]), 3))
