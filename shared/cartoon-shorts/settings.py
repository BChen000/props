"""Settings for cartoon-shorts: the blob demo (blob.py, build.py), the lit and stick looks of the motivational Shorts
(humanoid.py, motivation.py) and the five cartoon looks (cast.py) with their caption styles and voices."""

FPS = 30
COLORS = dict(
    bg='#0A0A0C', wall='#101014', floor='#0C0C0F',
    blob_top='#F6F4EF', blob_bot='#D6D2C8', eye='#111113',
    shadow='#0D0708', shadow_rim='#C0242E', shadow_eye='#FF4040',
    moon='#6F86A8', window='#1A1C24', bed='#18181E', blanket='#28303E', blanket_hi='#36404F', pillow='#3A4251',
    stand='#141418', clock='#0B0B0D', digits='#FF3434',
    text='#ECE9E4', text_red='#E8C9C9',
    dawn_top='#0B0B10', dawn_mid='#2B1712', dawn_low='#B9552B', sun='#F3A24C', ground='#0D0D10', path='#17171C',
    lamp='#F3C77A', desk='#1A1A20', page='#E9E6DF', page_line='#B9B4AA',
    cal_paper='#E7E3DA', cal_bar='#7A1F24', cal_grid='#BDB8AE', cal_x='#C8262E',
)
GRAIN_ALPHA, GRAIN_FRAMES = 0.06, 8          # film grain drawn over every frame
VIGNETTE = 0.72
SCENE_FADE_IN = 0.08                          # dip from black at each cut (the kit's default is 0.2 s)

# demo timing (seconds)
ALARM_LEAD = 1.7                              # alarm rings before the first whisper
WAKE_GAP, WAKE_LEN = 0.6, 1.7                 # after the last whisper: cut to the close-up, eyes snap open, "no."
MONTAGE = [('day1', 1.3, 'DAY 1.'), ('run', 1.5, ''), ('study', 1.3, ''), ('calendar', 1.9, ''), ('end', 2.7, 'discipline.')]
WHISPERS = ['just five more minutes...', "you're tired.", 'start tomorrow.']

# inner voice: the Story Time narrator pitched down, low-passed and drenched in reverb
VOICE_PITCH = 0.86                            # 0.86 = about 2.6 semitones down, length unchanged
VOICE_REVERB, VOICE_LP = 0.42, 5200
MUSIC = dict(bpm=120, kick=0.55, hat=0.10, piano=0.34, drone=0.16, fx=0.6)

# ---------------------------------------------------------------- the white bean person (humanoid.py), lit look
HUMANOID = dict(head=64, torso=150, torso_w=66, upper=84, fore=78, arm_w=27, thigh=96, shin=92, leg_w=31)   # at s = 1
HUM_COLORS = dict(eye='#121216', catch='#FFFFFF', brow='#1C1B24', mouth='#2A2026', mouth_in='#5A2328')
SHADOW_COLORS = dict(fill='#0E0809', rim='#C0242E', eye='#FF4040')
# the stickman style (python make_short.py <episode> --style stick): same rig, poses and props, drawn as a stick figure
STICK = dict(width=15, head=46, neck=12, color='#F4F2EC', back='#C9C6D4', edge='#20202A', edge_a=0.45, glow=0.16)
# key light for the figures; scenes override with humanoid.light(...). dir points from the figure toward the light
LIGHT_DEFAULT = dict(dir=(-0.55, -0.83), lit='#F7F6FB', shade='#A3A2BE', rim='#8FA8FF', rim_a=0.0, glow=0.10)

# ---------------------------------------------------------------- motivational Shorts (motivation.py)
# nar: the Story Time voice a little lower and slower; sha: the same voice pitched down and slowed (pitch_len < 1
# stretches it), with a little breath noise and reverb. Heavier settings (pitch 0.84, lp 4600, reverb 0.45) made
# Whisper mishear the whispers, so keep them checkable with ../narration-check
VOICES = dict(
    nar=dict(voice='am_michael', speed=0.94, pitch=0.94, pitch_len=1.0, lp=9500, reverb=0.16, gain=1.0, extra_gap=0.14, breath=0.0),
    sha=dict(voice='am_michael', speed=0.9, pitch=0.86, pitch_len=0.93, lp=8000, reverb=0.28, gain=0.95, extra_gap=0.12, breath=0.2),
    old=dict(voice='am_onyx', speed=0.88, pitch=0.97, pitch_len=1.0, lp=7500, reverb=0.2, gain=1.05, extra_gap=0.25, breath=0.06,
             trem=(5.0, 0.07)),
    # story: the storyteller of the five cartoon looks, brighter and quicker than nar
    story=dict(voice='am_michael', speed=1.0, pitch=1.0, pitch_len=1.0, lp=12000, reverb=0.07, gain=1.0, extra_gap=0.02, breath=0.0),
)
LEAD_IN, TAIL = 0.15, 1.2           # silence before the first line; after the last

# ---------------------------------------------------------------- the lit look: captions and colours (motivation.py)
FONTS = dict(pop='Poppins-ExtraBold.ttf', brush='CaveatBrush-Regular.ttf', punch='Bangers-Regular.ttf')  # get_fonts.py
CAP = dict(size=92, words=2, max_chars=15, white='#FFFFFF', key='#FFC93C', pop=0.09, hold=0.35)   # narration chunks
SHA_TEXT = dict(size=104, color='#E8302E', glow='#FF2A2A', write=0.45)       # the shadow's red handwriting
TITLE = dict(size=150, color='#FFFFFF', glow=0.75)                          # DAY 1, no., the end word
DAY = dict(y=232, size=58, color='#FFFFFF', spacing=8)                       # DAY counter at the top
DUST = dict(n=46, color='#FFF3DC', a=0.5)                                    # floating dust in the light
# palettes of the lit sets: (top, bottom) gradients; lit / shade / rim light the figure in that set
NIGHT = dict(wall=('#2B3062', '#1B1E3E'), floor=('#1A1C3A', '#0F1024'), trim='#252950', frame='#3B4174',
             sky=('#141C4A', '#33448A'), moon='#EEF1FF', beam='#B9C6FF', bed=('#3A3F72', '#262A55'),
             blanket=('#5260AE', '#2F3774'), pillow=('#E4E6F6', '#A3A8D0'), stand=('#2A2E5C', '#1A1D3D'),
             lit='#F1F2FF', shade='#8C91C2', rim='#7F8FFF', dust='#C9D3FF')
WARM = dict(wall=('#9E623F', '#6A3F2C'), floor=('#4C2E22', '#26160F'), trim='#5A3628', lamp='#FFD28A', dome='#E9C06F',
            lit='#FFF5E6', shade='#B48E7B', rim='#FFB36B', dust='#FFE2B0', mat=('#3D5C7A', '#2A4157'))
DUSK = dict(sky=('#232A64', '#56488F', '#C06D86', '#F4A36C'), sun='#FFD69A', far='#4A3F7E', win='#FFC37A',
            mid='#2E2A5E', near='#1B193C', ground=('#1A1838', '#0D0C20'), lamp='#FFC77A',
            lit='#FFF1E8', shade='#A894B8', rim='#FFB07A', dust='#FFE0C2')
DAWN = dict(sky=('#1B2255', '#4A3E86', '#C46A8A', '#F7B46C'), sun='#FFE3AA',
            ridges=('#77609E', '#54447F', '#352D62', '#1A1736'), mist='#F3D6E6', lit='#FFF3EA', shade='#A996BC', rim='#FFC080')
GREY = dict(sky=('#232937', '#434C5C', '#6A7385'), far='#3A4150', mid='#2B303C', near='#1E222B', win='#C9A866',
            ground=('#1D2028', '#111318'), lit='#D6DBE6', shade='#7C8396', rim='#9AA6C0')

# ---------------------------------------------------------------- the five cartoon looks (cast.py)
# caption looks, chosen by an episode's CAPTIONS: gold (the motivational look, CAP above), punch (one word at a time in
# a slanted comic font), outline (white words with a black edge), karaoke (the whole line in capitals, words lighting up)
CAP_LOOKS = dict(
    punch=dict(size=150, skew=-0.13, fill='#FFFFFF', key='#FFD23F', edge='#101018', edge_w=15, y=1430, pop=0.09),
    outline=dict(size=86, fill='#FFFFFF', key='#FFD84A', edge='#000000', edge_w=11, y=1440, words=2),
    karaoke=dict(size=62, fill='#FFFFFF', dim=0.34, spacing=1.5, width=900, y=1480, lead=1.18),
)
HUD = dict(x=46, y=150, h=104, gap=14, pad=24, bg='#0E1B25', bg_a=0.86, edge='#2E5A70', label='#8DB9CB', value='#5FE3FF')
# body proportions at s = 1 (px) and default outfits. A look's person stands about 500 px tall at s = 1.
LOOKS = dict(
    whatif=dict(seg=dict(head=60, neck=8, torso=122, torso_w=78, hip_w=17, upper=70, fore=66, thigh=88, shin=84, foot=12),
                limb=13, sleeve=29, pants=31, ink='#121216',
                outfit=dict(top='#2BB5A4', bottom='#3B4150', shoes='#F4F4F0', sleeves='short', hair=None, hat=None)),
    palace=dict(seg=dict(head=96, neck=0, torso=118, torso_w=112, hip_w=20, upper=58, fore=54, thigh=56, shin=52, foot=10),
                limb=24, ink='#2A1A14', ow=5,
                outfit=dict(top='#F3EEE6', trim='#6E3AA8', bottom='#F3EEE6', skin='#F6D2A0', hair='bowl', hat=None,
                            beard=None, robe=True)),
    castle=dict(seg=dict(head=82, neck=0, torso=150, torso_w=118, hip_w=20, upper=60, fore=56, thigh=60, shin=58, foot=10),
                limb=9, ink='#1E1A1C', ow=4,
                outfit=dict(top='#2F7A52', trim='#E2C46A', skin='#FBF7EF', hair='curly', hair_col='#6B3F25', hat=None)),
    desert=dict(seg=dict(head=56, neck=2, torso=104, torso_w=66, hip_w=12, upper=60, fore=56, thigh=66, shin=62, foot=8),
                limb=7, ink='#1A1412', ow=3.5,
                outfit=dict(top='#7A2E52', trim='#D9A441', skin='#E2A86E', hair='bowl', hat=None)),
    pill=dict(seg=dict(head=70, neck=0, torso=150, torso_w=118, hip_w=18, upper=66, fore=62, thigh=76, shin=72, foot=8),
              limb=8, ink='#1B1B1F', ow=6,
              outfit=dict(top='#3F7FD6', skin='#FBFBF7', hair='bowl', hat=None, shoes='#F4F4F0')),
)
