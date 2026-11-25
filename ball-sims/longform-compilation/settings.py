"""Settings for a full-screen 16:9 Marble Pop "Guess the Marble Song" long-form video.

Every round fills the frame: music rounds are 16:9 re-renders from the marble templates (MARBLE_CAM=wide), and Shorts
without a template are reframed (a colour-tracked crop, a two-camera split, or an extended studio backdrop).
The game sits on top as overlays. Times are seconds of the SOURCE video unless a name says otherwise.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PROPS = os.path.abspath(os.path.join(HERE, ".."))

# ===================================================================== SETTINGS (shipped values)
SHORTS_DIR = os.environ.get("SHORTS_DIR", "/mnt/user-data/uploads")
WIDE_BUILD = os.environ.get("WIDE_BUILD", "build_wide")      # BUILD_DIR the 16:9 template renders were made with
BUILD = os.environ.get("BUILD_DIR", os.path.join(HERE, "build"))
OUT_NAME = os.environ.get("OUT_NAME", "Guess_the_Marble_Song_Fullscreen.mp4")

W, H, FPS, SR = 1920, 1080, 30, 48000
SPF = SR // FPS
CRF = int(os.environ.get("CRF", "18"))
PRESET = os.environ.get("PRESET", "veryfast")
AUDIO_BITRATE = "192k"

TARGET_LUFS = -15.0
LIMIT_DBFS = -3.0                      # AAC adds ~1.8 dB of overshoot: true peak ends near -1 dBTP
FADE_IN_S, FADE_OUT_S = 0.04, 0.25
RENDER_TAIL_S = 1.2                    # cut from the end of a 16:9 render (its last notes ring ~2.4 s)
CUT_BEFORE_NOTE_S = 0.45               # music rounds start this long before their first note

TRANSITION_FRAMES = 8
INTRO_S = 3.3
COUNTDOWN_S = 5
COUNTDOWN_LEAD_S = 1.0
UPNEXT_LEAD_S = 4.0
END_SCREEN_S = 15.0
RACE_PROMPT_S = 6.5                    # "PICK YOUR COLOR!" panel at the start of a race

SFX_DIR = os.path.join(PROPS, "battle-audio", "assets")
SFX = {"pop": ("pop.wav", 2.0), "whoosh": ("whoosh.wav", -14.0), "ding": ("ding.wav", -6.0),
       "tick": ("tick.wav", -14.0)}
BEDS = {"battle": ["battle_loop.wav", "battle_loop_lead.wav"], "suspense": ["suspense_loop.wav"],
        "outro": ["outro_loop.wav"]}
BED_LUFS, BED_SFX_LUFS = -21.0, -16.0
BED_FADE_IN_S, BED_FADE_OUT_S = 0.6, 0.8

FONT_DIRS = [os.path.expanduser("~/.fonts"), "/usr/share/fonts/truetype/google-fonts"]
FONTS = {"blk": "Poppins-Black.ttf", "xb": "Poppins-ExtraBold.ttf", "b": "Poppins-Bold.ttf", "sb": "Poppins-SemiBold.ttf"}
MARBLES = ["#EE3434", "#FA8A1C", "#FACE26", "#96D630", "#24BE60", "#1CC4CC", "#2C76EE", "#9852E4"]
BALL = {"red": "#ec4144", "blue": "#3d83f7", "green": "#32c664", "yellow": "#fbc932", "purple": "#a75bed",
        "orange": "#f78b2c", "white": "#f2f2f2"}
YELLOW, PINK, GOLD, OUTLINE, INK = "#ffd650", "#fb7fd3", "#ffcd46", "#0a0414", "#1b0930"
PANEL_RGBA = (14, 6, 30, 178)
CHANNEL = "Marble Pop"

# Overlay layout on the 1920x1080 frame
PILL_XY = (40, 30)                     # round pill, top-left
DOTS_Y = 126                           # 20 progress marbles + the bonus, under the pill
LOGO_RIGHT, LOGO_Y = 1880, 62
PANEL = dict(x=1430, y=196, w=450, h=556)   # game panel on the right (the sets leave that sky empty)
EQ_SIZE = (390, 186)
BAR = dict(cx=960, y=1046, w=1180)     # round progress bar along the bottom
UPNEXT_Y = 968

INTRO_LINES = ("GUESS THE MARBLE SONG!", "20 ROUNDS + A SECRET BONUS SONG")
END_LINES = (["THANKS FOR", "WATCHING!"], "How many did you get?", "Comment your score!")
TITLE = "Guess the Marble Song! 🎵 20 Rounds + a Secret Bonus"

# Running order.  src: ("wide", template, song) a 16:9 template render | ("short", glob) a vertical Short.
# frame: how a Short fills 16:9 -- dict(track=[colours]) | dict(keys=[(t, top fraction)]) | dict(split=(yl, yr))
#        | dict(extend=True).  kind: song | race | run | bonus.
ITEMS = [
    dict(key="twinkle", src=("wide", "marble-stairs-song", "twinkle"), kind="song", title="Twinkle Twinkle Little Star"),
    dict(key="race_pick_one", src=("short", "*marble_race_pick_one*.mp4"), kind="race", frame=dict(track=["red", "blue"], tail=[(29.5, 0.05), (31.1, 0.05)]),
         ts=0.9, te=31.067, speed=[(8.0, 14.0, 1.4)], colors=["red", "blue"], sub="No switching!", end_t=29.4,
         bed="battle"),
    dict(key="london", src=("wide", "marble-twin-stairs", "london-bridge"), kind="song", title="London Bridge"),
    dict(key="mary", src=("wide", "marble-stairs-song", "mary-lamb"), kind="song", title="Mary Had a Little Lamb"),
    dict(key="run_heart", src=("short", "*marble_run_short.mp4"), kind="run", frame=dict(split=(240, 840)),
         ts=0.0, te=22.4, prompt="WHAT WILL THE MARBLES MAKE?", reveal=19.5, answer="A HEART!", answer_icon="heart",
         bed="outro"),
    dict(key="elise", src=("wide", "marble-twin-stairs", "fur-elise"), kind="song", title="Für Elise"),
    dict(key="row", src=("wide", "marble-spiral-round", "row-row-row"), kind="song", title="Row, Row, Row Your Boat"),
    dict(key="blue_vs_green", src=("short", "*blue_vs_green_round1.mp4"), kind="race",
         frame=dict(track=["blue", "green"]), ts=0.0, te=32.2, speed=[(21.0, 27.0, 1.4)], colors=["blue", "green"],
         sub="First one out wins!", end_t=29.0, bed="battle"),
    dict(key="jingle", src=("wide", "marble-stairs-song", "jingle-bells"), kind="song", title="Jingle Bells"),
    dict(key="bday", src=("wide", "marble-twin-stairs", "happy-birthday"), kind="song", title="Happy Birthday"),
    dict(key="xylophone", src=("short", "*twinkle_marbles_xylophone.mp4"), kind="song",
         frame=dict(vcam=[(0.0, 540, 690, 608, 0), (9.6, 540, 700, 608, 0), (11.4, 540, 1120, 608, 0),
                          (12.2, 540, 1140, 608, 0)]),   # the ramp at full width, then down to the basket
         ts=0.0, f0=0.0, te=11.9, title="Twinkle Twinkle Little Star", label="SPEED ROUND!", countdown=3,
         extra="...on a xylophone!"),
    dict(key="oldmac", src=("wide", "marble-stairs-song", "old-macdonald"), kind="song", title="Old MacDonald Had a Farm"),
    dict(key="run_rainbow", src=("short", "*marble_run_rainbow.mp4"), kind="run", frame=dict(split=(300, 840)),
         ts=0.5, te=23.4, prompt="WHICH COLOR GOES LAST?", reveal=19.5, answer="PURPLE!", answer_color="purple",
         bed="outro"),
    dict(key="wenceslas", src=("wide", "marble-twin-stairs", "good-king"), kind="song", title="Good King Wenceslas"),
    dict(key="deck", src=("wide", "marble-stairs-song", "deck-the-halls"), kind="song", title="Deck the Halls"),
    dict(key="frere", src=("wide", "marble-twin-stairs", "frere-jacques"), kind="song", title="Frère Jacques"),
    dict(key="last_marble", src=("short", "*last_marble_wins*.mp4"), kind="race",
         # virtual camera (vcam.py): (t, cx, cy, view height, roll). The top-down stretches are turned a quarter turn so
         # the whole swirl fits the 16:9 frame; the perspective close-ups stay upright at the Short's full width.
         frame=dict(vcam=[(0.0, 540, 880, 608, 0), (2.0, 540, 880, 608, 0), (2.8, 540, 960, 1080, 90),
                          (7.3, 540, 960, 1080, 90), (8.1, 540, 960, 608, 0), (11.4, 540, 960, 608, 0),
                          (12.2, 540, 1000, 1000, 90), (13.5, 540, 985, 880, 90), (14.5, 530, 985, 780, 90),
                          (16.0, 550, 975, 660, 90), (17.5, 545, 980, 610, 90), (21.4, 540, 980, 600, 90),
                          (22.2, 540, 1072, 608, 0), (29.4, 540, 1110, 608, 0)]),
         ts=0.0, te=29.4, colors=["red", "blue", "green", "yellow"], sub="Last marble left wins!", end_t=27.6,
         bed="suspense"),
    dict(key="merry", src=("wide", "marble-stairs-song", "merry-christmas"), kind="song",
         title="We Wish You a Merry Christmas"),
    dict(key="ode", src=("wide", "marble-twin-stairs", "ode-to-joy"), kind="song", title="Ode to Joy"),
    dict(key="run_christmas", src=("short", "*marble_run_christmas.mp4"), kind="run", frame=dict(split=(300, 840)),
         ts=0.5, te=20.8, prompt="RED, GREEN OR WHITE?", colors=["red", "green", "white"], bed="outro"),
    dict(key="bonus", src=("wide", "marble-stairs-song", "joy-to-the-world"), kind="bonus", title="Joy to the World"),
]

THUMB_BUILD = os.environ.get("THUMB_BUILD", "build_thumb")  # BUILD_DIR of the templates' widethumb renders
THUMBNAILS = [   # thumbs.py -> build/thumbnail_<name>.jpg, no text (GJ's best thumbnails had none)
    dict(name="A_twin_stairs", still=("marble-twin-stairs", "ode-to-joy"), cam="widethumb"),
    dict(name="B_staircase", still=("marble-stairs-song", "jingle-bells"), cam="wide"),   # spawns widethumb
    dict(name="C_collage", grid=[   # 2x2, all music rounds; "still" = a template's title-free --thumb-only render
        dict(src=("still", "marble-stairs-song", "build_thumb", "jingle-bells")),
        dict(src=("still", "marble-twin-stairs", "build_wide", "happy-birthday"), cam="wide", box=(180, 130, 1600)),
        dict(src=("still", "marble-spiral-round", "build_wide", "row-row-row"), cam="wide", box=(307, 250, 960)),
        dict(src=("reframe", "xylophone"), t=10.0),
    ]),
]
