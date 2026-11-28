"""Settings for the stickman demo: a bare black stick figure in a detailed, painted-looking island world, told as a
"what if" survival Short with the Story Time narrator and one caption per line. stickman.py draws, build.py assembles."""

FPS = 30
STICK = dict(color='#121212', width=17, head=36,                   # at s = 1 (the figure is about 440 px tall)
             torso=150, neck=16, upper=92, fore=86, thigh=104, shin=100)
HORIZON = 980                                                        # sea meets sky
GROUND = 1318                                                        # where feet stand on the island
ISLAND = dict(cx=540, cy=1330, rx=470, ry=84)                       # the dry sand top; wet sand and foam ring it
CAP_Y = 560                                                          # captions sit in the sky

# time of day: sky stops (top -> horizon), sea (near horizon -> foreground), sand, light on the scene
TOD = dict(
    dawn=dict(sky=['#22325C', '#6F5A80', '#E1896B', '#F5C27C'], sea=['#5F6F8E', '#1F3354'], sand='#DDBF94', wet='#B79B76',
              body=('sun', '#FFD58A', 300, 960, 64), light=0.85),
    day=dict(sky=['#3D8CCF', '#78B6E3', '#D2EAF3'], sea=['#3CA0C0', '#155C80'], sand='#EDD5A3', wet='#CDB07C',
             body=('sun', '#FFF6C8', 860, 300, 58), light=1.0),
    night=dict(sky=['#03060E', '#0A1324', '#172A4B'], sea=['#13294A', '#06101E'], sand='#5E5B6B', wet='#45465A',
               body=('moon', '#E8EEF5', 820, 420, 52), light=0.35),
    morning=dict(sky=['#5B9BD4', '#A6CBE5', '#F2DCB2'], sea=['#3E9AB6', '#175E7E'], sand='#EBD3A0', wet='#CBAE7A',
                 body=('sun', '#FFE9B4', 200, 380, 60), light=0.95),
)

STORY = dict(name='stickman_demo', hook=('', ''), lines=[
    ('island', 'What if you were stranded'),
    ('island', 'on a tiny island?'),
    ('day1', 'Day one.'),
    ('day1', 'You find coconuts.'),
    ('day2', 'Day two.'),
    ('day2', 'You make a fire.'),
    ('day3', 'Day three.'),
    ('day3', 'A ship appears.'),
    ('swim', 'Would you swim for it?'),
])
MUSIC = dict(preset='d-minor', music_db=-8.0, ocean=0.22, fx=0.6)
