"""Settings for a long-form Marble Pop compilation: 16:9 game-show layout around vertical Shorts.

Every value the build uses lives here. Times are in seconds of the SOURCE Short unless a name says otherwise.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))

# ===================================================================== SETTINGS (shipped values)
SHORTS_DIR = os.environ.get("SHORTS_DIR", "/mnt/user-data/uploads")
BONUS_FILE = os.environ.get("BONUS_FILE", os.path.join(
    HERE, "..", "marble-stairs-song", "build", "joy-to-the-world", "Marble_Staircase_Joy_to_the_World.mp4"))
BUILD = os.environ.get("BUILD_DIR", os.path.join(HERE, "build"))
OUT_NAME = os.environ.get("OUT_NAME", "Guess_the_Marble_Song_Longform.mp4")

W, H, FPS, SR = 1920, 1080, 30, 48000
SPF = SR // FPS                      # audio samples per video frame (1600)
CRF = int(os.environ.get("CRF", "18"))
PRESET = os.environ.get("PRESET", "veryfast")
AUDIO_BITRATE = "192k"

# The vertical Short sits in a rounded card in the middle; the side panels hold the game.
CARD_H, CARD_Y, CARD_R = 1024, 28, 30
MODES = {                             # source crop height (full width 1080) -> card size on the 16:9 canvas
    "zoom": 1480,                     # music sets: drops the empty sky and the bottom watermark, ~1.3x bigger marbles
    "full": 1920,                     # races, the heart run and the xylophone: the whole frame matters
}

TARGET_LUFS = -15.0                   # every clip is gained to this before mixing, so volume never jumps
LIMIT_DBFS = -2.0                     # final peak limiter (AAC overshoots ~1.5 dB on limited transients)
FADE_IN_S, FADE_OUT_S = 0.04, 0.25

TRANSITION_FRAMES = 8                 # "marble pop": a giant marble grows over the end of a clip,
                                      # then the next clip opens out of it (xfade circleopen both times)
INTRO_S = 3.3                         # title over the start of round 1
COUNTDOWN_S = 5                       # guess-the-song countdown (speed round: 3)
COUNTDOWN_LEAD_S = 1.0                # countdown starts this long after the first note
UPNEXT_LEAD_S = 4.0                   # "UP NEXT" slides in this long before a round ends
END_SCREEN_S = 15.0                   # end-screen panels over the last seconds of the bonus

SFX_DIR = os.path.join(HERE, "..", "battle-audio", "assets")
SFX = {                               # name: (file, gain dB)
    "pop": ("pop.wav", 2.0),
    "whoosh": ("whoosh.wav", -14.0),
    "ding": ("ding.wav", -6.0),
    "tick": ("tick.wav", -14.0),
    "fanfare": ("fanfare.wav", -8.0),
}

FONT_DIRS = [os.path.expanduser("~/.fonts"), "/usr/share/fonts/truetype/google-fonts"]
FONTS = {"blk": "Poppins-Black.ttf", "xb": "Poppins-ExtraBold.ttf", "b": "Poppins-Bold.ttf", "sb": "Poppins-SemiBold.ttf"}

# Colours: marbles from the rainbow staircase tiles, UI from ../style-kit
MARBLES = ["#EE3434", "#FA8A1C", "#FACE26", "#96D630", "#24BE60", "#1CC4CC", "#2C76EE", "#9852E4"]
BALL = {"red": "#ec4144", "blue": "#3d83f7", "green": "#32c664", "yellow": "#fbc932", "purple": "#a75bed",
        "orange": "#f78b2c", "white": "#f2f2f2"}
YELLOW, PINK, GOLD, OUTLINE, INK = "#ffd650", "#fb7fd3", "#ffcd46", "#0a0414", "#1b0930"
PANEL_RGBA = (10, 4, 20, 165)
BG_BRIGHTNESS = 0.42                  # blurred-clip backdrop brightness
CHANNEL = "Marble Pop"

INTRO_LINES = (["GUESS", "THE", "MARBLE", "SONG!"], ["20 ROUNDS", "+ a SECRET", "BONUS SONG", "at the end!"])
THUMB_FRAMES = [("row_your_boat", 40.5), ("frere_jacques", 26.0), ("bonus_joy", 31.0)]  # left, middle, right

END_LINES = (["THANKS FOR", "WATCHING!"], "How many did you get?", "Comment your score!")

# The running order. kind: song | race | run | bonus.  ts/te: cut points (source s); f0: first note (source s);
# speed: [(from, to, factor)] fast-forwards slow stretches; reveal/end_t: source s.
ITEMS = [
    dict(key="twinkle_stairs", file="*Marble_Staircase_Twinkle.mp4", kind="song", mode="zoom", crop_y=150,
         f0=1.067, te=31.6, title="Twinkle Twinkle Little Star"),
    dict(key="race_pick_one", file="*marble_race_pick_one*.mp4", kind="race", mode="full",
         ts=0.0, te=31.067, speed=[(8.0, 14.0, 1.4)], colors=["red", "blue"], sub="No switching!", end_t=29.6),
    dict(key="jingle_bells", file="*Marble_Staircase_Jingle_Bells.mp4", kind="song", mode="zoom", crop_y=150,
         f0=1.067, te=37.0, title="Jingle Bells"),
    dict(key="fur_elise", file="*Marble_Tower_Fur_Elise.mp4", kind="song", mode="zoom", crop_y=150,
         f0=1.25, te=28.3, title="Für Elise"),
    dict(key="run_heart", file="*marble_run_short.mp4", kind="run", mode="full", ts=0.0, te=22.4,
         prompt=["WHAT WILL", "THE MARBLES", "MAKE?"], icon="question", reveal=19.5, answer="A HEART!",
         answer_icon="heart", hint="Watch closely!"),
    dict(key="old_macdonald", file="*Marble_Staircase_Old_MacDonald.mp4", kind="song", mode="zoom", crop_y=150,
         f0=1.25, te=31.2, title="Old MacDonald Had a Farm"),
    dict(key="row_your_boat", file="*Marble_Spiral_Row_Your_Boat.mp4", kind="song", mode="zoom", crop_y=150,
         f0=1.8, te=47.0, title="Row, Row, Row Your Boat"),
    dict(key="blue_vs_green", file="*blue_vs_green_round1.mp4", kind="race", mode="full",
         ts=0.0, te=32.2, speed=[(21.0, 27.0, 1.4)], colors=["blue", "green"], sub="First one out wins!", end_t=29.0),
    dict(key="deck_the_halls", file="*marbles_deck_the_halls.mp4", kind="song", mode="zoom", crop_y=150,
         f0=1.4, te=47.2, title="Deck the Halls"),
    dict(key="frere_jacques", file="*Marble_Twin_Stairs_Frere_Jacques.mp4", kind="song", mode="zoom", crop_y=150,
         f0=1.25, te=32.6, title="Frère Jacques"),
    dict(key="twinkle_xylophone", file="*twinkle_marbles_xylophone.mp4", kind="song", mode="full",
         ts=0.0, f0=0.0, te=11.9, title="Twinkle Twinkle Little Star", label="SPEED ROUND!", countdown=3,
         extra="...on a xylophone!"),
    dict(key="mary_lamb", file="*stair_mary_lamb.mp4", kind="song", mode="zoom", crop_y=150,
         f0=1.0, te=27.8, title="Mary Had a Little Lamb"),
    dict(key="run_rainbow", file="*marble_run_rainbow.mp4", kind="run", mode="zoom", crop_y=250, ts=0.5, te=23.4,
         prompt=["WHICH", "COLOR GOES", "LAST?"], colors=["red", "orange", "yellow", "green", "blue", "purple"],
         reveal=19.5, answer="PURPLE!", answer_color="purple", hint="Name every color!"),
    dict(key="happy_birthday", file="*Marble_Piano_Happy_Birthday.mp4", kind="song", mode="zoom", crop_y=150,
         f0=1.25, te=26.5, title="Happy Birthday"),
    dict(key="good_king", file="*Marble_Tower_Good_King_Wenceslas.mp4", kind="song", mode="zoom", crop_y=150,
         f0=1.25, te=35.0, title="Good King Wenceslas"),
    dict(key="merry_christmas", file="*stair_merry_christmas.mp4", kind="song", mode="zoom", crop_y=150,
         f0=1.0, te=21.6, title="We Wish You a Merry Christmas"),
    dict(key="last_marble_wins", file="*last_marble_wins*.mp4", kind="race", mode="full", ts=0.0, te=29.4,
         colors=["red", "blue", "green", "yellow"], sub="Last marble left wins!", end_t=27.6),
    dict(key="ode_to_joy", file="*Marble_Twin_Stairs_Ode_to_Joy.mp4", kind="song", mode="zoom", crop_y=150,
         f0=1.5, te=37.2, title="Ode to Joy"),
    dict(key="jingle_bells_16", file="*Marble_Staircase_Jingle_Bells_copy.mp4", kind="song", mode="zoom",
         crop_y=150, f0=1.0, te=34.3, title="Jingle Bells", extra="...with 16 marbles!"),
    dict(key="run_christmas", file="*marble_run_christmas.mp4", kind="run", mode="zoom", crop_y=250, ts=0.5,
         te=20.8, prompt=["RED, GREEN", "OR WHITE?"], colors=["red", "green", "white"],
         hint="Pick your favorite!"),
    dict(key="bonus_joy", file="BONUS", kind="bonus", mode="zoom", crop_y=150,
         f0=1.067, te=37.0, title="Joy to the World"),
]
