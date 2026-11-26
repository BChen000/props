"""The two medleys the marbles play: public-domain melodies only (pre-1929), so the bell arrangements made from them
are free to stream. Never add a popular song: those are copyrighted and get Content ID claims.

The marbles hop once per beat, and one beat here is an eighth note: at TAU = 0.5 s a quarter note lasts 1 s (60 BPM),
a calm lullaby tempo. Songs are written in quarter notes (`q`) and converted to eighth-note beats.

A song is a dict:
  name     title (shown in the stream's "now playing" panel)
  meter    beats (eighths) per bar: 8 for 4/4, 6 for 3/4
  pickup   beats before the first downbeat
  voices   melody lines, each [(beat, midi, beats)]; voice 0 is the tune, voice 1 (optional) a canon entry
  chords   [(beat, beats, chord name)]
  length   beats the song lasts (the last note rings to its end)
A medley joins songs with GAP beats of soft arpeggio between them and loops back to the first song.
"""
NOTE_BASE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

# ===================================================================== SETTINGS (shipped values)
GAP = 6                 # beats of arpeggio between songs (3 s)
CHORDS = {              # chord tones (pitch classes as note names) and bass note name
    "C": ("C E G", "C"), "F": ("F A C", "F"), "G": ("G B D", "G"), "G7": ("G B D F", "G"),
    "D": ("D F# A", "D"), "D7": ("D F# A C", "D"), "E": ("E G# B", "E"), "E7": ("E G# B D", "E"),
    "Am": ("A C E", "A"), "Em": ("E G B", "E"), "Dm": ("D F A", "D"),
}
# ================================================================= END SETTINGS


def m(name):
    letter, rest, acc = name[0], name[1:], 0
    while rest and rest[0] in "#b":
        acc += 1 if rest[0] == "#" else -1
        rest = rest[1:]
    return 12 * (int(rest) + 1) + NOTE_BASE[letter] + acc


def pc(name):
    return (NOTE_BASE[name[0]] + (1 if "#" in name else -1 if "b" in name[1:] else 0)) % 12


def line(notes, start=0):
    """[(name, quarters)] -> [(beat, midi, beats)] in eighth-note beats from `start`."""
    out, b = [], start
    for name, qd in notes:
        d = int(round(qd * 2))
        out.append((b, m(name), d))
        b += d
    return out


def bars(names, meter, start=0):
    """One chord name per bar -> [(beat, beats, name)]."""
    return [(start + i * meter, meter, n) for i, n in enumerate(names)]


def per_quarter(names, start=0):
    """One chord name per quarter note -> [(beat, beats, name)], merging repeats."""
    out = []
    for i, n in enumerate(names):
        if out and out[-1][2] == n:
            out[-1][1] += 2
        else:
            out.append([start + 2 * i, 2, n])
    return [tuple(c) for c in out]


def _end(notes):
    return max(b + d for b, _, d in notes)


# --------------------------------------------------------------------------------------------- songs


def twinkle():
    a1 = [("C5", 1), ("C5", 1), ("G5", 1), ("G5", 1), ("A5", 1), ("A5", 1), ("G5", 2)]
    a2 = [("F5", 1), ("F5", 1), ("E5", 1), ("E5", 1), ("D5", 1), ("D5", 1), ("C5", 2)]
    b = [("G5", 1), ("G5", 1), ("F5", 1), ("F5", 1), ("E5", 1), ("E5", 1), ("D5", 2)]
    ca1 = ["C"] * 4 + ["F"] * 2 + ["C"] * 2
    ca2 = ["F"] * 2 + ["C"] * 2 + ["G7"] * 2 + ["C"] * 2
    cb = ["C"] * 2 + ["F"] * 2 + ["C"] * 2 + ["G"] * 2
    mel = line(a1 + a2 + b + b + a1 + a2)
    return dict(name="Twinkle Twinkle Little Star", meter=8, pickup=0, voices=[mel],
                chords=per_quarter(ca1 + ca2 + cb + cb + ca1 + ca2), length=_end(mel))


def frere_jacques(canon=False):
    tune = [("C5", 1), ("D5", 1), ("E5", 1), ("C5", 1)] * 2 + [("E5", 1), ("F5", 1), ("G5", 2)] * 2 + \
           [("G5", 0.5), ("A5", 0.5), ("G5", 0.5), ("F5", 0.5), ("E5", 1), ("C5", 1)] * 2 + \
           [("C5", 1), ("G4", 1), ("C5", 2)] * 2
    mel = line(tune)
    voices = [mel]
    if canon:
        voices.append([(b + 16, p, d) for b, p, d in mel])
    length = _end(voices[-1])
    return dict(name="Are You Sleeping (Frère Jacques)", meter=8, pickup=0, voices=voices,
                chords=bars(["C"] * (length // 8), 8), length=length)


def mary_lamb():
    tune = [("E5", 1), ("D5", 1), ("C5", 1), ("D5", 1), ("E5", 1), ("E5", 1), ("E5", 2),
            ("D5", 1), ("D5", 1), ("D5", 2), ("E5", 1), ("G5", 1), ("G5", 2),
            ("E5", 1), ("D5", 1), ("C5", 1), ("D5", 1), ("E5", 1), ("E5", 1), ("E5", 1), ("E5", 1),
            ("D5", 1), ("D5", 1), ("E5", 1), ("D5", 1), ("C5", 4)]
    mel = line(tune)
    return dict(name="Mary Had a Little Lamb", meter=8, pickup=0, voices=[mel],
                chords=bars(["C", "C", "G", "C", "C", "C", "G", "C"], 8), length=_end(mel))


def silent_night():
    q = [("D5", 1.5), ("E5", 0.5), ("D5", 1), ("B4", 3)]          # "Silent night" (G major)
    tune = q + q + [("A5", 2), ("A5", 1), ("F#5", 3), ("G5", 2), ("G5", 1), ("D5", 3)]
    r = [("E5", 2), ("E5", 1), ("G5", 1.5), ("F#5", 0.5), ("E5", 1)] + q
    tune += r + r
    tune += [("A5", 2), ("A5", 1), ("C6", 1.5), ("A5", 0.5), ("F#5", 1), ("G5", 3), ("B5", 3),
             ("G5", 1), ("D5", 1), ("B4", 1), ("D5", 1.5), ("C5", 0.5), ("A4", 1), ("G4", 6)]
    mel = line(tune)
    ch = ["G"] * 4 + ["D7"] * 2 + ["G"] * 2 + ["C"] * 2 + ["G"] * 2 + ["C"] * 2 + ["G"] * 2 + ["D7"] * 2 + \
         ["G"] * 3 + ["D7"] + ["G"] * 2
    return dict(name="Silent Night", meter=6, pickup=0, voices=[mel], chords=bars(ch, 6), length=_end(mel))


def ode_to_joy():
    head = [("E5", 1), ("E5", 1), ("F5", 1), ("G5", 1), ("G5", 1), ("F5", 1), ("E5", 1), ("D5", 1),
            ("C5", 1), ("C5", 1), ("D5", 1), ("E5", 1)]
    a = head + [("E5", 1.5), ("D5", 0.5), ("D5", 2)]
    a2 = head + [("D5", 1.5), ("C5", 0.5), ("C5", 2)]
    b = [("D5", 1), ("D5", 1), ("E5", 1), ("C5", 1), ("D5", 1), ("E5", 0.5), ("F5", 0.5), ("E5", 1), ("C5", 1),
         ("D5", 1), ("E5", 0.5), ("F5", 0.5), ("E5", 1), ("D5", 1), ("C5", 1), ("D5", 1), ("G4", 2)]
    ca = ["C"] * 4 + ["G"] * 4 + ["C"] * 4 + ["G"] * 4
    ca2 = ["C"] * 4 + ["G"] * 4 + ["C"] * 4 + ["G"] * 2 + ["C"] * 2
    cb = ["G"] * 2 + ["C"] * 2 + ["G"] * 2 + ["C"] * 2 + ["G"] * 2 + ["C", "G"] + ["C"] + ["G"] * 3
    mel = line(a + a2 + b + a2)
    return dict(name="Ode to Joy", meter=8, pickup=0, voices=[mel], chords=per_quarter(ca + ca2 + cb + ca2),
                length=_end(mel))


def minuet_in_g():
    a = [("D5", 1), ("G4", 0.5), ("A4", 0.5), ("B4", 0.5), ("C5", 0.5), ("D5", 1), ("G4", 1), ("G4", 1),
         ("E5", 1), ("C5", 0.5), ("D5", 0.5), ("E5", 0.5), ("F#5", 0.5), ("G5", 1), ("G4", 1), ("G4", 1),
         ("C5", 1), ("D5", 0.5), ("C5", 0.5), ("B4", 0.5), ("A4", 0.5), ("B4", 1), ("C5", 0.5), ("B4", 0.5),
         ("A4", 0.5), ("G4", 0.5)]
    end1 = [("F#4", 1), ("G4", 0.5), ("A4", 0.5), ("B4", 0.5), ("G4", 0.5), ("A4", 3)]
    end2 = [("A4", 1), ("B4", 0.5), ("A4", 0.5), ("G4", 0.5), ("F#4", 0.5), ("G4", 3)]
    mel = line(a + end1 + a + end2)
    ch = ["G", "G", "C", "G", "C", "G", "D", "D", "G", "G", "C", "G", "C", "G", "D7", "G"]
    return dict(name="Minuet in G", meter=6, pickup=0, voices=[mel], chords=bars(ch, 6), length=_end(mel))


def greensleeves():
    verse_a = [("C5", 2), ("D5", 1), ("E5", 1.5), ("F5", 0.5), ("E5", 1), ("D5", 2), ("B4", 1),
               ("G4", 1.5), ("A4", 0.5), ("B4", 1), ("C5", 2), ("A4", 1), ("A4", 1.5), ("G#4", 0.5), ("A4", 1),
               ("B4", 2), ("G#4", 1)]
    chorus_a = [("G5", 3), ("G5", 1.5), ("F#5", 0.5), ("E5", 1), ("D5", 2), ("B4", 1), ("G4", 1.5), ("A4", 0.5),
                ("B4", 1), ("C5", 2), ("A4", 1), ("A4", 1.5), ("G#4", 0.5), ("A4", 1), ("B4", 2), ("G#4", 1)]
    cad = [("C5", 1.5), ("B4", 0.5), ("A4", 1), ("G#4", 1.5), ("F#4", 0.5), ("G#4", 1), ("A4", 3), ("A4", 3)]
    tune = [("A4", 1)] + verse_a + [("E4", 2), ("A4", 1)] + verse_a[:10] + cad + \
           chorus_a + [("E4", 3)] + chorus_a[:9] + cad
    mel = line(tune)
    verse = ["Am", "C", "G", "Em", "Am", "Am", "E", "E", "Am", "C", "G", "Em", "Am", "E", "Am", "Am"]
    chorus = ["C", "C", "G", "Em", "Am", "Am", "E", "E", "C", "C", "G", "Em", "Am", "E", "Am", "Am"]
    return dict(name="Greensleeves", meter=6, pickup=2, voices=[mel],
                chords=[(0, 2, "Am")] + bars(verse + chorus, 6, start=2), length=_end(mel))


def row_your_boat(canon=False):
    notes = [(72, 3), (72, 3), (72, 2), (74, 1), (76, 3), (76, 2), (74, 1), (76, 2), (77, 1), (79, 6),
             (84, 1), (84, 1), (84, 1), (79, 1), (79, 1), (79, 1), (76, 1), (76, 1), (76, 1), (72, 1), (72, 1),
             (72, 1), (79, 2), (77, 1), (76, 2), (74, 1), (72, 6)]
    mel, b = [], 0
    for p, d in notes:                      # already in eighths (6/8)
        mel.append((b, p, d))
        b += d
    voices = [mel]
    if canon:
        voices.append([(b + 12, p, d) for b, p, d in mel])
    length = _end(voices[-1])
    ch = [(0, 36, "C"), (36, 6, "G7"), (42, length - 42, "C")]
    return dict(name="Row, Row, Row Your Boat", meter=6, pickup=0, voices=voices, chords=ch, length=length)


# --------------------------------------------------------------------------------------------- medleys

MEDLEYS = {
    "stairs": [twinkle, frere_jacques, lambda: frere_jacques(canon=True), mary_lamb, silent_night],
    "twin": [ode_to_joy, minuet_in_g, greensleeves, row_your_boat, lambda: row_your_boat(canon=True)],
}
TITLES = {"stairs": "Marble Lullabies", "twin": "Marble Music Box Classics"}


def medley(name):
    """-> (songs, starts, total beats). Songs are placed back to back with GAP beats after each; a repeated song
    (the canon pass) follows its first pass with no gap."""
    songs, starts, b = [], [], 0
    fns = MEDLEYS[name]
    for i, fn in enumerate(fns):
        s = fn()
        songs.append(s)
        starts.append(b)
        nxt = fns[(i + 1) % len(fns)]()
        b += s["length"] + (0 if nxt["name"] == s["name"] else GAP)
    return songs, starts, b
