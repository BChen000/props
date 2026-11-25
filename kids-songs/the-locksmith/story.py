"""The Locksmith: the story, its sound cues and its music settings (Story Time with Kenji, Nov 2026).

Walter, the only locksmith in a small town, cuts a second copy of every key and lets himself into people's
houses while they're out, until he finds a photo of himself asleep in his own bed.

STORY lines are (scene, caption) or (scene, caption, what the narrator says) and run in screen order; every caption
is one spoken line. scenes.py has one draw function per scene name used here.
"""

TITLE = 'The Locksmith'
STORY = {
    'name': 'the_locksmith',
    'hook': ("He kept a copy of every key he ever made...", "then someone got into HIS house"),
    'lines': [
        ('shop', "Walter was the only locksmith"),
        ('shop', "in a town of four thousand people."),
        ('shop', "For twenty-two years,"),
        ('shop', "every lock in town was his."),
        ('cutting', "Every key, he cut by hand."),
        ('cutting', "And every key,"),
        ('cutting', "he cut twice."),
        ('drawer', "The copies went into a drawer"),
        ('drawer', "in the back of his shop."),
        ('drawer', "Labeled."),
        ('drawer', "Filed."),
        ('drawer', "Every house in town."),
        ('street', "He never stole a thing."),
        ('street', "That was never the point."),
        ('street', "He'd wait for a family to leave for work,"),
        ('street', "and let himself in."),
        ('living', "He'd sit on their couch."),
        ('living', "Read their mail."),
        ('living', "Drink from their mugs."),
        ('living', "Sometimes, he'd even take a nap."),
        ('putback', "Then he'd put everything back."),
        ('putback', "Almost."),
        ('putback', "A mug turned the wrong way."),
        ('putback', "A book one shelf lower."),
        ('couple', "People noticed."),
        ('couple', "But they blamed themselves."),
        ('couple', "Stress. Kids. Getting older."),
        ('mainst', "Nobody suspected the friendly locksmith"),
        ('mainst', "who waved at everyone on Main Street."),
        ('morrison', "Then one afternoon,"),
        ('morrison', "in the Morrison house,"),
        ('morrison', "Walter found something"),
        ('morrison', "on the coffee table."),
        ('photo', "A photo."),
        ('photo', "Of him."),
        ('photo', "Asleep."),
        ('photo', "In his own bed."),
        ('locks', "That night, he changed every lock"),
        ('locks', "in his house."),
        ('locks', "Twice."),
        ('awake', "He sat up until sunrise,"),
        ('awake', "listening."),
        ('awake', "Nothing."),
        ('mug', "In the morning,"),
        ('mug', "his coffee mug was on the counter."),
        ('mug', "Turned the wrong way."),
    ],
}

# music: a storytime-music preset, and its level against the narration's RMS while it speaks (dB)
MUSIC = dict(preset='d-minor', music_db=-3.5)

# sound effects: (scene, line index within that scene, offset s from that line's start, kind, gain[, length s or 'scene'])
EVENTS = [
    ('cutting', 0, -0.1, 'grind', 0.1, 'scene'),   # key machine under the whole cutting scene
    ('street', 3, 0.2, 'click', 0.7),              # "and let himself in."
    ('putback', 1, 0.0, 'boom', 0.35),             # "Almost."
    ('photo', 0, -0.05, 'boom', 0.8),              # "A photo."
    ('locks', 0, 0.2, 'drill', 0.5, 1.6),          # "That night, he changed every lock"
    ('locks', 2, 0.0, 'click', 0.8),               # "Twice."
    ('awake', 2, -0.2, 'whoosh', 0.4),             # "Nothing."
    ('mug', 2, 0.0, 'boom', 0.9),                  # "Turned the wrong way."
    ('mug', 2, 0.02, 'clink', 0.25),
]
