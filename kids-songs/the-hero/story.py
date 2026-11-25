"""The Hero: the story, its sound cues and its music settings (Story Time with Kenji, Nov 2026).

A homeless man saves billionaire Victor Hale from the river, is taken in, and inherits half his fortune. Nobody
asked who loosened the railing, and now a young man watches Leo's morning run.

STORY lines are (scene, caption) or (scene, caption, what the narrator says) and run in screen order; every caption
is one spoken line. scenes.py has one draw function per scene name used here.
"""

TITLE = 'The Hero'
STORY = {
    'name': 'the_hero',
    'hook': ("A homeless man saved a billionaire from drowning...", "nobody asked why he was there"),
    'lines': [
        ('jog', "Every morning at 5 a.m.,", "Every morning at five a.m.,"),
        ('jog', "billionaire Victor Hale"),
        ('jog', "ran the same path along the river."),
        ('jog', "Same route."),
        ('jog', "Same time."),
        ('jog', "For eleven years."),
        ('railing', "One foggy morning,"),
        ('railing', "he stopped at the bend to stretch,"),
        ('railing', "leaned on the railing,"),
        ('railing', "and it gave way."),
        ('water', "The water was freezing."),
        ('water', "And Victor couldn't swim."),
        ('rescue', "A homeless man named Leo"),
        ('rescue', "jumped in after him"),
        ('rescue', "and dragged him to shore."),
        ('viral', "Someone filmed the whole thing."),
        ('viral', "By noon, it had ten million views."),
        ('mansion', "Victor gave Leo a job."),
        ('mansion', "A home."),
        ('mansion', "A seat at his family's table."),
        ('kids', "His children hated it."),
        ('kids', "“He's using you, Dad.”", "He's using you, Dad."),
        ('kids', "Victor didn't care."),
        ('will', "He rewrote his will."),
        ('will', "Half of everything"),
        ('will', "would go to the man who saved his life."),
        ('funeral', "Fourteen months later,"),
        ('funeral', "Victor's heart gave out in his sleep."),
        ('inherit', "Leo inherited"),
        ('inherit', "four hundred million dollars."),
        ('court', "The family sued."),
        ('court', "They lost."),
        ('court', "The judge called Leo"),
        ('court', "the only person who ever showed up for him."),
        ('reveal', "But nobody ever asked"),
        ('reveal', "why a homeless man was waiting"),
        ('reveal', "at that exact bend,"),
        ('reveal', "at 5 a.m., in the fog.", "at five a.m., in the fog."),
        ('reveal', "Or who loosened the railing"),
        ('reveal', "the night before."),
        ('present', "Today, Leo runs that same path."),
        ('present', "Every morning at 5 a.m.", "Every morning at five a.m."),
        ('present', "Same route."),
        ('present', "Same time."),
        ('present', "And lately,"),
        ('present', "there's a young man on the bench by the bend."),
        ('present', "Watching."),
    ],
}

# music: a storytime-music preset, and its level against the narration's RMS while it speaks (dB)
MUSIC = dict(preset='g-minor', music_db=-4.1)

# sound effects: (scene, line index within that scene, offset s from that line's start, kind, gain[, length s or 'scene'])
EVENTS = [
    ('railing', 3, 0.1, 'whoosh', 0.5),            # "and it gave way."
    ('railing', 3, 0.5, 'splash', 0.9),
    ('rescue', 1, 0.5, 'splash', 0.8),             # "jumped in after him"
    ('court', 1, -0.05, 'gavel', 0.9),             # "They lost."
    ('reveal', 0, -0.05, 'boom', 0.8),             # "But nobody ever asked"
    ('reveal', 4, -0.25, 'whoosh', 0.4),           # "Or who loosened the railing"
    ('present', 6, -0.05, 'boom', 0.9),            # "Watching."
]
