"""POWER BALLS settings: every knob for a new video lives here.

Text, colors, names and timing only change the look. Anything under SIMULATION or ABILITY TUNING
changes the fight itself, so SEED will play out differently: run `python search.py seeds` to find a
new dramatic seed after changing those.
"""

# ---------------------------------------------------------------- the fight
SEED = 1774                                    # which fight to render (picked from 6,000 with search.py)

# ---------------------------------------------------------------- fighters (index = spawn corner TL, TR, BL, BR)
NAMES = ['RED', 'BLUE', 'GREEN', 'YELLOW']
COLORS = ['#FE394C', '#2F7EFF', '#21C45D', '#FEC32F']
ABILITIES = ['blaster', 'laser', 'missiles', 'lightning']      # any of these four, repeats allowed
ABILITY_LABELS = ['BLASTER', 'LASER', 'MISSILES', 'LIGHTNING']  # short label on each card
ABILITY_NAMES = ['360° BLASTER', 'LASER BEAM', 'MISSILES', 'LIGHTNING']  # under the intro balls
UPGRADE_LABELS = {                               # floats above the attacker after each hit
    'blaster': '+1 BULLET',
    'laser': 'LASER UP!',
    'missiles': ('+1 MISSILE', 'POWER UP!'),     # (when the missile count grows, other levels)
    'lightning': 'RANGE UP!',
}

# ---------------------------------------------------------------- on-screen text
TITLE = 'POWER BALLS'
SUBTITLE = 'Every hit UPGRADES your power'
WIN_TITLE = 'WE HAVE A WINNER!'
INTRO_TEXT = 'PICK YOUR FIGHTER!'
FIGHT_TEXT = 'FIGHT!'
CAPTION = 'Comment your fighter!'
DUEL_CAPTION = 'FINAL DUEL!'
END_CAPTION = 'Did your fighter win? Comment!'
OUT_TEXT = '{name} IS OUT!'
FINAL_BLOW_TEXT = 'FINAL BLOW...'
WIN_TEXT = '{name} WINS!'
WIN_SUB_ONE = 'with just {hp} HP left!'
WIN_SUB_MANY = 'with {hp} HP left!'

# ---------------------------------------------------------------- video and timing
W, H, FPS = 1080, 1920, 30
T_INTRO = 2.6            # seconds of PICK YOUR FIGHTER before the fight starts
SLOW = 0.25              # slow-motion speed around the final blow
SLOW_LEAD = 0.9          # slow-mo starts this long before the final hit (or right after the hit before it)
SLOW_TAIL = 0.32         # ...and ends this long after it
WIN_DELAY = 1.15         # sim seconds after the final hit before the winner screen
WIN_HOLD = 4.3           # seconds the winner screen stays up
ZOOM_FINAL = 1.32        # camera zoom on the last two fighters during the final blow

# ---------------------------------------------------------------- simulation
ARENA = 872.0            # arena size in px (inner square)
BALL_R = 46.0            # ball radius in px
DT = 1.0 / 240.0         # fixed physics step (keep it: the outcome depends on it)
BASE_SPEED = 400.0       # px/s cruising speed; knockback relaxes back to it
RELAX = 1.3              # how fast speed returns to BASE_SPEED (1/s)
KNOCK = 300.0            # knockback impulse per hit (px/s)
HP = 7
MAX_LEVEL = 10           # power-bar levels; each hit you land is +1 level
FIRST_COOLDOWN = {'blaster': 0.9, 'laser': 1.1, 'missiles': 1.0, 'lightning': 0.8}  # + random 0..0.5 s

# ---------------------------------------------------------------- ability tuning (balanced: each wins ~22-27%)
ABILITY = dict(
    INVULN=0.8,                                                   # i-frames after taking a hit (s)
    # 360 blaster: ring of BL_N0 + level bullets every BL_CD s
    BL_CD=3.6, BL_N0=5, BL_STEP=1, BL_NMAX=16, BL_SPEED=480, BL_R=5, BL_SPIN=0.9,
    # laser: charge (aim line), lock, then a wall-to-wall beam; faster and wider per level
    LZ_CD0=3.1, LZ_CD_STEP=0.08, LZ_CD_MIN=1.5, LZ_CHARGE=0.75, LZ_LOCK=0.18, LZ_FIRE=0.3,
    LZ_W0=22, LZ_W_STEP=2, LZ_TRACK=8, LZ_FIRE_TRACK=1.2,
    # homing missiles: MS_N0 + level // MS_EVERY per volley
    MS_CD=4.0, MS_N0=1, MS_NMAX=6, MS_V0=230.0, MS_V1=420, MS_ACC=650.0, MS_TURN=2.0,
    MS_LIFE=3.0, MS_HIT_R=9.0, MS_SPREAD=1.25, MS_EVERY=2,
    # lightning: zaps the nearest enemy inside the range ring; range grows, chains every LT_CHAIN_EVERY levels
    LT_CD=3.4, LT_RANGE0=190, LT_RANGE_STEP=12, LT_CHAIN_EVERY=5,
)

# ---------------------------------------------------------------- audio
AUDIO_SEED = 1774        # noise texture of the synthesized sounds
SR = 44100
MUSIC_GAIN = 0.2         # music bed under the effects
SFX_GAIN = 0.9
PREGAIN = 1.3            # drives the limiter (higher = louder, more squashed)
LIMIT = 0.80             # limiter ceiling before loudness normalization
LOUDNESS = -14.0         # LUFS target for the final mux (YouTube's reference)
TRUE_PEAK = -1.5
