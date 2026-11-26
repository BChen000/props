"""The tunes of the Marble Pop marble music Shorts, written once more for the calm stream mix (music.py).

All of them are public-domain melodies (pre-1929), so the bell arrangements made from them are free to stream. Never
add a popular song: those are copyrighted and get Content ID claims.

Each song is a dict:
  name     title
  bpm      beats per minute (a beat is a quarter note, an eighth in 6/8, a sixteenth for Sugar Plum)
  meter    beats per bar
  notes    [(beat, midi, beats)] the melody
  chords   [(beat, beats, tones, bass)] tones are MIDI chord tones (any octave), bass a MIDI bass note
  end      beat where the tune ends
  passes   the arrangement, one dict per time through: style "soft" | "flow" | "sparkle" and optional canon
           (melody entries in beats, for a round)
Sources: marble-stairs-song (Twinkle, Jingle Bells), marble-spiral-round (Row Row Row), marble-twin-stairs
(Ode to Joy), marble-song-battle (Deck the Halls, We Wish You, God Rest Ye, Sugar Plum) and London Bridge.
"""
NOTE_BASE = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def m(name):
    letter, rest, acc = name[0], name[1:], 0
    while rest and rest[0] in '#b':
        acc += 1 if rest[0] == '#' else -1
        rest = rest[1:]
    return 12 * (int(rest) + 1) + NOTE_BASE[letter] + acc


def chord(root, quality):
    iv = {'maj': [0, 4, 7], 'min': [0, 3, 7], '7': [0, 4, 7, 10], 'm7': [0, 3, 7, 10], '7b9': [0, 4, 7, 10, 13]}
    return [m(root) + i for i in iv[quality]]


CH = {
    "C": (chord('C4', 'maj'), m('C3')), "F": (chord('F3', 'maj'), m('F2')), "G": (chord('G3', 'maj'), m('G2')),
    "G7": (chord('G3', '7'), m('G2')), "D7": (chord('D3', '7'), m('D3')), "E7": (chord('E3', '7'), m('E2')),
    "Am": (chord('A3', 'min'), m('A2')), "Em": (chord('E3', 'min'), m('E2')), "D": (chord('D3', 'maj'), m('D2')),
    "B7": (chord('B2', '7'), m('B1')),
}


def line(notes, start=0.0):
    """[(name, beats)] -> [(beat, midi, beats)] from `start`."""
    out, b = [], start
    for name, d in notes:
        out.append((b, m(name), d))
        b += d
    return out


def runs(names, start=0.0):
    """One chord name per beat -> [(beat, beats, tones, bass)], merging repeats."""
    out = []
    for i, n in enumerate(names):
        if out and out[-1][4] == n:
            out[-1][1] += 1
        else:
            out.append([start + i, 1, *CH[n], n])
    return [(b, d, t, ba) for b, d, t, ba, _ in out]


def spans(items, start=0.0):
    """[(beat, beats, name)] -> chords."""
    return [(start + b, d, *CH[n]) for b, d, n in items]


def twinkle():
    a1 = [("C5", 1), ("C5", 1), ("G5", 1), ("G5", 1), ("A5", 1), ("A5", 1), ("G5", 2)]
    a2 = [("F5", 1), ("F5", 1), ("E5", 1), ("E5", 1), ("D5", 1), ("D5", 1), ("C5", 2)]
    b = [("G5", 1), ("G5", 1), ("F5", 1), ("F5", 1), ("E5", 1), ("E5", 1), ("D5", 2)]
    ca1 = ["C"] * 4 + ["F"] * 2 + ["C"] * 2
    ca2 = ["F"] * 2 + ["C"] * 2 + ["G7"] * 2 + ["C"] * 2
    cb = ["C"] * 2 + ["F"] * 2 + ["C"] * 2 + ["G"] * 2
    return dict(name="Twinkle Twinkle Little Star", bpm=80, meter=4, notes=line(a1 + a2 + b + b + a1 + a2),
                chords=runs(ca1 + ca2 + cb + cb + ca1 + ca2), end=48,
                passes=[dict(style="soft"), dict(style="flow"), dict(style="sparkle")])


def jingle_bells():
    p1 = [("E5", 1), ("E5", 1), ("E5", 2), ("E5", 1), ("E5", 1), ("E5", 2), ("E5", 1), ("G5", 1), ("C5", 1.5),
          ("D5", 0.5), ("E5", 4)]
    p2 = [("F5", 1), ("F5", 1), ("F5", 1.5), ("F5", 0.5), ("F5", 1), ("E5", 1), ("E5", 1), ("E5", 0.5), ("E5", 0.5),
          ("E5", 1), ("D5", 1), ("D5", 1), ("E5", 1), ("D5", 2), ("G5", 2)]
    p4 = [("F5", 1), ("F5", 1), ("F5", 1), ("F5", 1), ("F5", 1), ("E5", 1), ("E5", 1), ("E5", 0.5), ("E5", 0.5),
          ("G5", 1), ("G5", 1), ("F5", 1), ("D5", 1), ("C5", 4)]
    ch = (["C"] * 16 + ["F"] * 4 + ["C"] * 4 + ["D7"] * 4 + ["G7"] * 4 + ["C"] * 16 + ["F"] * 4 + ["C"] * 4
          + ["G7"] * 4 + ["C"] * 4)
    return dict(name="Jingle Bells", bpm=112, meter=4, notes=line(p1 + p2 + p1 + p4), chords=runs(ch), end=64,
                passes=[dict(style="flow"), dict(style="sparkle")])


def ode_to_joy():
    head = [("E5", 1), ("E5", 1), ("F5", 1), ("G5", 1), ("G5", 1), ("F5", 1), ("E5", 1), ("D5", 1), ("C5", 1),
            ("C5", 1), ("D5", 1), ("E5", 1)]
    a = head + [("E5", 1.5), ("D5", 0.5), ("D5", 2)]
    a2 = head + [("D5", 1.5), ("C5", 0.5), ("C5", 2)]
    b = [("D5", 1), ("D5", 1), ("E5", 1), ("C5", 1), ("D5", 1), ("E5", 0.5), ("F5", 0.5), ("E5", 1), ("C5", 1),
         ("D5", 1), ("E5", 0.5), ("F5", 0.5), ("E5", 1), ("D5", 1), ("C5", 1), ("D5", 1), ("G4", 2)]
    ca = ["C"] * 4 + ["G"] * 4 + ["C"] * 4 + ["G"] * 4
    ca2 = ["C"] * 4 + ["G"] * 4 + ["C"] * 4 + ["G"] * 2 + ["C"] * 2
    cb = ["G"] * 2 + ["C"] * 2 + ["G"] * 2 + ["C"] * 2 + ["G"] * 2 + ["C", "G"] + ["C"] + ["G"] * 3
    return dict(name="Ode to Joy", bpm=88, meter=4, notes=line(a + a2 + b + a2), chords=runs(ca + ca2 + cb + ca2),
                end=64, passes=[dict(style="soft"), dict(style="sparkle")])


def deck_the_halls():
    l1 = [("G5", 1.5), ("F5", 0.5), ("E5", 1), ("D5", 1), ("C5", 1), ("D5", 1), ("E5", 1), ("C5", 1), ("D5", 0.5),
          ("E5", 0.5), ("F5", 0.5), ("D5", 0.5), ("E5", 1.5), ("D5", 0.5), ("C5", 1), ("B4", 1), ("C5", 2)]
    l3 = [("D5", 1.5), ("E5", 0.5), ("F5", 1), ("D5", 1), ("E5", 1.5), ("F5", 0.5), ("G5", 1), ("D5", 1),
          ("E5", 0.5), ("F#5", 0.5), ("G5", 1), ("A5", 0.5), ("B5", 0.5), ("C6", 1), ("B5", 1), ("A5", 1), ("G5", 2)]
    l4 = [("G5", 1.5), ("F5", 0.5), ("E5", 1), ("D5", 1), ("C5", 1), ("D5", 1), ("E5", 1), ("C5", 1), ("A5", 0.5),
          ("A5", 0.5), ("A5", 0.5), ("A5", 0.5), ("G5", 1.5), ("F5", 0.5), ("E5", 1), ("D5", 1), ("C5", 2)]
    c1 = [(0, 7, "C"), (7, 3, "G7"), (10, 1.5, "C"), (11.5, 0.5, "G7"), (12, 1, "C"), (13, 1, "G7"), (14, 2, "C")]
    c3 = [(0, 4, "G7"), (4, 2, "C"), (6, 2, "G"), (8, 2, "D7"), (10, 2, "G"), (12, 2, "D7"), (14, 2, "G")]
    c4 = [(0, 2, "C"), (2, 2, "G7"), (4, 4, "C"), (8, 2, "F"), (10, 2, "G7"), (12, 2, "G7"), (14, 2, "C")]
    return dict(name="Deck the Halls", bpm=100, meter=4, notes=line(l1 + l1 + l3 + l4),
                chords=spans(c1) + spans(c1, 16) + spans(c3, 32) + spans(c4, 48), end=64,
                passes=[dict(style="flow"), dict(style="sparkle")])


def row_row_row():
    notes = [(72, 3), (72, 3), (72, 2), (74, 1), (76, 3), (76, 2), (74, 1), (76, 2), (77, 1), (79, 6),
             (84, 1), (84, 1), (84, 1), (79, 1), (79, 1), (79, 1), (76, 1), (76, 1), (76, 1), (72, 1), (72, 1),
             (72, 1), (79, 2), (77, 1), (76, 2), (74, 1), (72, 6)]
    out, b = [], 0
    for p, d in notes:
        out.append((b, p, d))
        b += d
    chords = [(0, 36, *CH["C"]), (36, 6, *CH["G7"]), (42, 6, *CH["C"])]
    return dict(name="Row Row Row Your Boat", bpm=190, meter=6, notes=out, chords=chords, end=48,
                passes=[dict(style="soft"), dict(style="flow", canon=[0, 12]),
                        dict(style="sparkle", canon=[0, 12, 24, 36])])


def london_bridge():
    mel = [("G5", 1.5), ("A5", 0.5), ("G5", 1), ("F5", 1), ("E5", 1), ("F5", 1), ("G5", 2), ("D5", 1), ("E5", 1),
           ("F5", 2), ("E5", 1), ("F5", 1), ("G5", 2), ("G5", 1.5), ("A5", 0.5), ("G5", 1), ("F5", 1), ("E5", 1),
           ("F5", 1), ("G5", 2), ("D5", 2), ("G5", 2), ("E5", 1), ("C5", 3)]
    ch = ["C"] * 8 + ["G"] * 4 + ["C"] * 4 + ["C"] * 8 + ["G"] * 4 + ["C"] * 4
    return dict(name="London Bridge", bpm=96, meter=4, notes=line(mel), chords=runs(ch), end=32,
                passes=[dict(style="soft"), dict(style="flow"), dict(style="sparkle")])


def we_wish_you():
    N = [(0, 'G4', 1), (1, 'C5', 1), (2, 'C5', 0.5), (2.5, 'D5', 0.5), (3, 'C5', 0.5), (3.5, 'B4', 0.5),
         (4, 'A4', 1), (5, 'A4', 1), (6, 'A4', 1), (7, 'D5', 1), (8, 'D5', 0.5), (8.5, 'E5', 0.5), (9, 'D5', 0.5),
         (9.5, 'C5', 0.5), (10, 'B4', 1), (11, 'G4', 1), (12, 'G4', 1), (13, 'E5', 1), (14, 'E5', 0.5),
         (14.5, 'F5', 0.5), (15, 'E5', 0.5), (15.5, 'D5', 0.5), (16, 'C5', 1), (17, 'A4', 1), (18, 'G4', 0.5),
         (18.5, 'G4', 0.5), (19, 'A4', 1), (20, 'D5', 1), (21, 'B4', 1), (22, 'C5', 3)]
    c = [(1, 3, "C"), (4, 3, "F"), (7, 3, "D7"), (10, 3, "G7"), (13, 3, "E7"), (16, 3, "Am"), (19, 1, "F"),
         (20, 2, "G7"), (22, 3, "C")]
    return dict(name="We Wish You a Merry Christmas", bpm=126, meter=3, notes=[(b, m(n), d) for b, n, d in N],
                chords=spans(c), end=25, passes=[dict(style="soft"), dict(style="flow"), dict(style="sparkle")])


def god_rest_ye():
    mel = ['E5', 'E5', 'B5', 'B5', 'A5', 'G5', 'F#5', 'E5', 'D5', 'E5', 'F#5', 'G5', 'A5', 'B5']
    notes = []
    for off in (0, 16):
        for i, n in enumerate(mel):
            notes.append((off + i, m(n), 3 if i == 13 else 1))
    seq = [(1, 4, "Em"), (5, 3, "Em"), (8, 1, "D"), (9, 2, "C"), (11, 2, "Am"), (13, 3, "B7")]
    chords = spans(seq) + [(16, 1, *CH["Em"])] + spans(seq, 16) + [(32, 3, *CH["Em"])]
    return dict(name="God Rest Ye Merry Gentlemen", bpm=96, meter=4, notes=notes, chords=chords, end=35,
                passes=[dict(style="soft"), dict(style="sparkle")])


def sugar_plum():
    phrase = [(0, 'G5'), (1, 'E5'), (2, 'G5'), (4, 'F#5'), (6, 'D#5'), (8, 'E5'), (10, 'D5'), (11, 'D5'),
              (12, 'D5'), (14, 'C#5'), (15, 'C#5'), (16, 'C#5'), (18, 'C5'), (19, 'C5'), (20, 'C5'), (22, 'B4'),
              (24, 'C5'), (26, 'B4')]
    long_ = (2, 4, 6, 8, 12, 16, 20, 22, 24, 26)
    notes = []
    for off in (0, 32):
        for b, n in phrase:
            notes.append((off + b, m(n), 2 if b in long_ else 1))
        if off == 0:
            notes.append((28, m('E5'), 0.5))
            notes += [(b, m(n), 0.5) for b, n in [(28.5, 'D5'), (29, 'C5'), (29.5, 'B4'), (30, 'A#4'), (30.5, 'B4')]]
    notes.append((60, m('E5'), 6))
    seq = [(0, chord('E3', 'min')), (4, chord('B2', '7')), (8, chord('E3', 'min')), (12, chord('E3', 'm7')),
           (16, [m('C#3'), m('E3'), m('G3'), m('A3')]), (20, chord('A2', 'min')), (24, chord('B2', '7b9')),
           (28, chord('E3', 'min'))]
    chords = []
    for off in (0, 32):
        for b, ch in seq:
            chords.append((off + b, 4, ch, m('B1') if b in (4, 24) else m('E2')))
    chords.append((60, 6, chord('E3', 'min'), m('E2')))
    return dict(name="Dance of the Sugar Plum Fairy", bpm=300, meter=8, notes=notes, chords=chords, end=66,
                passes=[dict(style="soft"), dict(style="flow"), dict(style="sparkle")])


PLAYLIST = [twinkle, jingle_bells, ode_to_joy, deck_the_halls, row_row_row, we_wish_you, london_bridge, sugar_plum,
            god_rest_ye]
