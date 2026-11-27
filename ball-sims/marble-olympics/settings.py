"""Marble Olympics: every setting of the long-form special in one place.

Four teams play five events made from the repo's game templates, with points for each place, a standings card after
every event and a champion at the end. The events are rendered by their own templates (events.py); this folder adds
the 1920x1080 broadcast frame, the cards and the soundtrack around them (make_special.py).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BALL_SIMS = os.path.abspath(os.environ.get("BALL_SIMS", os.path.join(HERE, "..")))
BUILD = os.environ.get("BUILD_DIR", os.path.join(HERE, "build"))
sys.path.append(os.path.join(BALL_SIMS, "style-kit"))
from kit import BALL_COLORS  # noqa: E402

# --------------------------------------------------------------------------- canvas
W, H, FPS = 1920, 1080, 30
PANEL_W = 608                       # each vertical event video is scaled to 608x1080 in the middle
CRF, PRESET = 20, "veryfast"
LOUDNESS = (-14, -1.0, 11)          # integrated LUFS, true peak dBTP, LRA of the final mix
BED_LEVEL = 0.75                    # card music RMS as a share of the events' soundtracks

# --------------------------------------------------------------------------- teams and scoring
TEAMS = ["RED", "BLUE", "GREEN", "YELLOW"]
TEAM_COLORS = {t: BALL_COLORS[t] for t in TEAMS}
POINTS = [3, 2, 1, 0]               # 1st, 2nd, 3rd, 4th; the grand final counts double
MEDALS = [(255, 205, 70), (205, 214, 226), (214, 142, 84), None]   # gold, silver, bronze, none

# --------------------------------------------------------------------------- the events
# template: the folder in ball-sims/ that renders it. set: settings.py lines replaced in a copy of the template.
# places: the finishing order the seed plays out (1st to 4th); events.py checks it against the template's own sim.
EVENTS = [
    dict(key="power-balls", name="POWER BALLS", rule="Every hit UPGRADES your power",
         template="ability-battle-template", set=dict(SEED=2494),
         places=["GREEN", "YELLOW", "BLUE", "RED"]),
    dict(key="sword-roulette", name="SWORD ROULETTE", rule="One random ball gets the BIG sword",
         template="sword-roulette", set=dict(SEED=2496, NAMES=["RED", "BLUE", "GREEN", "YELLOW"]),
         places=["YELLOW", "RED", "GREEN", "BLUE"]),
    dict(key="laser-wars", name="LASER WARS", rule="Everyone gets a LASER",
         template="ability-battle-template",
         set=dict(SEED=2900, ABILITIES=["laser"] * 4, ABILITY_LABELS=["LASER"] * 4, ABILITY_NAMES=["LASER BEAM"] * 4,
                  TITLE="LASER WARS", SUBTITLE="Everyone gets a LASER"),
         places=["RED", "BLUE", "YELLOW", "GREEN"]),
    dict(key="blaster-battle", name="BLASTER BATTLE", rule="Everyone gets the 360° BLASTER",
         template="ability-battle-template",
         set=dict(SEED=2241, ABILITIES=["blaster"] * 4, ABILITY_LABELS=["BLASTER"] * 4,
                  ABILITY_NAMES=["360° BLASTER"] * 4, TITLE="BLASTER BATTLE", SUBTITLE="Everyone gets the 360° BLASTER"),
         places=["BLUE", "GREEN", "RED", "YELLOW"]),
    dict(key="grand-final", name="GRAND FINAL", rule="500 marbles, one for every subscriber. Last color left WINS",
         template="marble-funnel-drain", episode="olympics500", double=True, keep=0.7,
         places=["BLUE", "YELLOW", "RED", "GREEN"]),
]
KEEP_AFTER_WIN = 2.6                # seconds after the win kept before the results card (`keep` per event)

# --------------------------------------------------------------------------- copy on screen
SHOW = "MARBLE OLYMPICS"
SPECIAL = "500 SUBSCRIBER SPECIAL"
THANKS = ("THANK YOU FOR 500 SUBSCRIBERS!", "To celebrate: 4 teams, 5 events, 1 champion.")
PICK = ("PICK YOUR COLOR!", "Comment it below and cheer for your team")
TIED = ("ALL FOUR TEAMS ARE TIED!", "The GRAND FINAL decides everything")
OUTRO = ("THANK YOU FOR 500 SUBSCRIBERS!", "Next stop: 1,000!", "Did your color win? Comment below!")
HERO_IMAGE = os.path.join(BALL_SIMS, "marble-milestone-post", "build", "milestone_500.png")   # title background

# --------------------------------------------------------------------------- card lengths (s)
CARD = dict(title=7.0, thanks=6.0, teams=7.5, rules=7.0, intro=4.0, results=7.5, standings=7.0, tied=7.0,
            champion=11.0, outro=10.0)
OUT_NAME = os.environ.get("OUT_NAME", "marble_olympics_500")

# --------------------------------------------------------------------------- YouTube copy (chapters are filled in)
YT_TITLE = "MARBLE OLYMPICS 🏅 Pick Your Color! (500 Subscriber Special)"
YT_DESCRIPTION = """4 teams. 5 events. Only 1 champion! Thank you for 500 subscribers 🎉
Pick your color in the comments 🔴🔵🟢🟡

{chapters}

Made with physics simulations
#marbles #satisfying #pickyourcolor #whowillwin #marbleolympics"""
