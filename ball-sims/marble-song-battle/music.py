"""Song library: public-domain melodies (pre-1929) written as beats, so each melody note can be a marble hit.

Each song returns a dict: name, team, bpm, meter (beats per bar), notes [(beat, midi, beats, is_hit)],
chords [(beat, beats, [midi...], bass_midi)], style (accompaniment: trap/pop/pizz/dark/waltz),
downbeat, end_beat and transpose (semitones added to the melody). Non-hit notes (is_hit False) are
played as a flourish without a marble hit (for runs faster than ~0.15 s per note).
Only add melodies that are in the public domain: popular songs are copyrighted and get Content ID claims.
Run `python3 music.py` to print hit counts and the shortest/longest gap per song.
"""
NOTE_BASE = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def m(name):
    letter = name[0]
    rest = name[1:]
    acc = 0
    while rest and rest[0] in '#b':
        acc += 1 if rest[0] == '#' else -1
        rest = rest[1:]
    return 12 * (int(rest) + 1) + NOTE_BASE[letter] + acc


def chord(root, quality):
    r = m(root)
    iv = {
        'maj': [0, 4, 7], 'min': [0, 3, 7], '7': [0, 4, 7, 10], 'm7': [0, 3, 7, 10],
        'dim7': [0, 3, 6, 9], '7b9': [0, 4, 7, 10, 13],
    }[quality]
    return [r + i for i in iv]


def carol_of_the_bells():
    bpm, beats_per_bar = 168, 3
    notes = []
    low = [('Bb4', 0, 1), ('A4', 1, 0.5), ('Bb4', 1.5, 0.5), ('G4', 2, 1)]
    high = [('D5', 0, 1), ('C5', 1, 0.5), ('D5', 1.5, 0.5), ('Bb4', 2, 1)]
    for bar in range(8):
        for n, b, d in (low if bar < 4 else high):
            notes.append((bar * 3 + b, m(n), d, True))
    notes.append((24, m('G4'), 3, True))
    prog = [('G2', chord('G3', 'min')), ('F2', [m('F3'), m('G3'), m('Bb3'), m('D4')]),
            ('Eb2', chord('C4', 'min')), ('D2', [m('D3'), m('G3'), m('Bb3')])]
    chords = []
    for bar in range(8):
        bass, ch = prog[bar % 4]
        chords.append((bar * 3, 3, ch, m(bass)))
    chords.append((24, 3, chord('G3', 'min'), m('G2')))
    return dict(name='Carol of the Bells', team='NAUGHTY', bpm=bpm, meter=beats_per_bar,
                notes=notes, chords=chords, style='trap', downbeat=0, end_beat=27, transpose=12)


def jingle_bells():
    bpm = 200
    N = [
        (0, 'B4', 1), (1, 'B4', 1), (2, 'B4', 2),
        (4, 'B4', 1), (5, 'B4', 1), (6, 'B4', 2),
        (8, 'B4', 1), (9, 'D5', 1), (10, 'G4', 1.5), (11.5, 'A4', 0.5),
        (12, 'B4', 4),
        (16, 'C5', 1), (17, 'C5', 1), (18, 'C5', 1.5), (19.5, 'C5', 0.5),
        (20, 'C5', 1), (21, 'B4', 1), (22, 'B4', 1), (23, 'B4', 0.5), (23.5, 'B4', 0.5),
        (24, 'B4', 1), (25, 'A4', 1), (26, 'A4', 1), (27, 'B4', 1),
        (28, 'A4', 2), (30, 'D5', 2),
    ]
    notes = [(b, m(n), d, True) for b, n, d in N]
    G = chord('G3', 'maj')
    chords = [(0, 4, G, m('G2')), (4, 4, G, m('G2')), (8, 4, G, m('G2')), (12, 4, G, m('G2')),
              (16, 4, chord('C4', 'maj'), m('C3')), (20, 4, G, m('G2')),
              (24, 4, chord('A3', '7'), m('A2')), (28, 4, chord('D3', '7'), m('D3')),
              (32, 4, G, m('G2'))]
    return dict(name='Jingle Bells', team='NICE', bpm=bpm, meter=4, notes=notes, chords=chords,
                style='pop', downbeat=0, end_beat=34, transpose=12)


def sugar_plum():
    bpm = 100 * 4
    phrase = [(0, 'G5'), (1, 'E5'), (2, 'G5'), (4, 'F#5'), (6, 'D#5'), (8, 'E5'),
              (10, 'D5'), (11, 'D5'), (12, 'D5'), (14, 'C#5'), (15, 'C#5'), (16, 'C#5'),
              (18, 'C5'), (19, 'C5'), (20, 'C5'), (22, 'B4'), (24, 'C5'), (26, 'B4')]
    notes = []
    for b, n in phrase:
        notes.append((b, m(n), 2 if b in (2, 4, 6, 8, 12, 16, 20, 22, 24, 26) else 1, True))
    notes.append((28, m('E5'), 0.5, True))
    for b, n in [(28.5, 'D5'), (29, 'C5'), (29.5, 'B4'), (30, 'A#4'), (30.5, 'B4')]:
        notes.append((b, m(n), 0.5, False))
    for b, n in phrase:
        notes.append((32 + b, m(n), 2 if b in (2, 4, 6, 8, 12, 16, 20, 22, 24, 26) else 1, True))
    notes.append((60, m('E5'), 6, True))
    E2 = m('E2')
    seq = [(0, chord('E3', 'min')), (4, chord('B2', '7')), (8, chord('E3', 'min')),
           (12, chord('E3', 'm7')), (16, [m('C#3'), m('E3'), m('G3'), m('A3')]),
           (20, chord('A2', 'min')), (24, chord('B2', '7b9')), (28, chord('E3', 'min'))]
    chords = []
    for off in (0, 32):
        for b, ch in seq:
            chords.append((off + b, 4, ch, E2 if b not in (4, 24) else m('B1')))
    chords.append((60, 6, chord('E3', 'min'), E2))
    return dict(name='Sugar Plum Fairy', team='NAUGHTY', bpm=bpm, meter=8, notes=notes,
                chords=chords, style='pizz', downbeat=0, end_beat=66, transpose=0)


def deck_the_halls():
    bpm = 190
    line = [(0, 'D5', 1.5), (1.5, 'C5', 0.5), (2, 'B4', 1), (3, 'A4', 1),
            (4, 'G4', 1), (5, 'A4', 1), (6, 'B4', 1), (7, 'G4', 1),
            (8, 'A4', 0.5), (8.5, 'B4', 0.5), (9, 'C5', 0.5), (9.5, 'A4', 0.5), (10, 'B4', 1.5),
            (11.5, 'A4', 0.5), (12, 'G4', 1), (13, 'F#4', 1), (14, 'G4', 2)]
    notes = []
    for off in (0, 16):
        for b, n, d in line:
            notes.append((off + b, m(n), d, True))
    G, D7 = chord('G3', 'maj'), chord('D3', '7')
    seq = [(0, 4, G, 'G2'), (4, 3, G, 'G2'), (7, 1, D7, 'D3'), (8, 2, D7, 'D3'),
           (10, 1.5, G, 'B2'), (11.5, 0.5, D7, 'D3'), (12, 1, G, 'G2'), (13, 1, D7, 'D3'),
           (14, 2, G, 'G2')]
    chords = []
    for off in (0, 16):
        for b, d, ch, bass in seq:
            chords.append((off + b, d, ch, m(bass)))
    return dict(name='Deck the Halls', team='NICE', bpm=bpm, meter=4, notes=notes, chords=chords,
                style='pop', downbeat=0, end_beat=34, transpose=12)


def god_rest_ye():
    bpm = 190
    line = ['E4', 'E4', 'B4', 'B4', 'A4', 'G4', 'F#4', 'E4', 'D4', 'E4', 'F#4', 'G4', 'A4', 'B4']
    notes = []
    for off in (0, 16):
        for i, n in enumerate(line):
            notes.append((off + i, m(n), 3 if i == 13 else 1, True))
    Em, D, C, Am, B7 = chord('E3', 'min'), chord('D3', 'maj'), chord('C3', 'maj'), chord('A2', 'min'), chord('B2', '7')
    seq = [(1, 4, Em, 'E2'), (5, 3, Em, 'E2'), (8, 1, D, 'D2'), (9, 2, C, 'C2'), (11, 2, Am, 'A1'),
           (13, 3, B7, 'B1'), (16, 1, Em, 'E2')]
    chords = []
    for off in (0, 16):
        for b, d, ch, bass in seq:
            if off == 16 and b == 16:
                continue
            chords.append((off + b, d, ch, m(bass)))
    chords.append((32, 4, Em, m('E2')))
    return dict(name='God Rest Ye Merry Gentlemen', team='NAUGHTY', bpm=bpm, meter=4, notes=notes,
                chords=chords, style='dark', downbeat=1, end_beat=35, transpose=12)


def we_wish_you():
    bpm = 180
    N = [(0, 'D4', 1),
         (1, 'G4', 1), (2, 'G4', 0.5), (2.5, 'A4', 0.5), (3, 'G4', 0.5), (3.5, 'F#4', 0.5),
         (4, 'E4', 1), (5, 'E4', 1), (6, 'E4', 1),
         (7, 'A4', 1), (8, 'A4', 0.5), (8.5, 'B4', 0.5), (9, 'A4', 0.5), (9.5, 'G4', 0.5),
         (10, 'F#4', 1), (11, 'D4', 1), (12, 'D4', 1),
         (13, 'B4', 1), (14, 'B4', 0.5), (14.5, 'C5', 0.5), (15, 'B4', 0.5), (15.5, 'A4', 0.5),
         (16, 'G4', 1), (17, 'E4', 1), (18, 'D4', 0.5), (18.5, 'D4', 0.5),
         (19, 'E4', 1), (20, 'A4', 1), (21, 'F#4', 1),
         (22, 'G4', 3)]
    notes = [(b, m(n), d, True) for b, n, d in N]
    seq = [(1, 3, chord('G3', 'maj'), 'G2'), (4, 3, chord('C3', 'maj'), 'C2'), (7, 3, chord('A2', '7'), 'A1'),
           (10, 3, chord('D3', '7'), 'D2'), (13, 3, chord('B2', '7'), 'B1'), (16, 3, chord('E3', 'min'), 'E2'),
           (19, 1, chord('C3', 'maj'), 'C2'), (20, 2, chord('D3', '7'), 'D2'), (22, 3, chord('G3', 'maj'), 'G2')]
    chords = [(b, d, ch, m(bass)) for b, d, ch, bass in seq]
    return dict(name='We Wish You a Merry Christmas', team='NICE', bpm=bpm, meter=3, notes=notes,
                chords=chords, style='waltz', downbeat=1, end_beat=25, transpose=12)


# ---- "Fire or Ice?" (Nov 2026): three wild pieces against three calm ones, all classical and public domain ----
def mountain_king():
    """Grieg, In the Hall of the Mountain King (1875): the theme once, in B minor, one beat per eighth note."""
    bpm = 210
    N = [(0, 'B3', 1), (1, 'C#4', 1), (2, 'D4', 1), (3, 'E4', 1), (4, 'F#4', 1), (5, 'D4', 1), (6, 'F#4', 2),
         (8, 'E#4', 1), (9, 'C#4', 1), (10, 'E#4', 2), (12, 'E4', 1), (13, 'C4', 1), (14, 'E4', 2),
         (16, 'B3', 1), (17, 'C#4', 1), (18, 'D4', 1), (19, 'E4', 1), (20, 'F#4', 1), (21, 'D4', 1), (22, 'F#4', 1),
         (23, 'B4', 1), (24, 'A4', 1), (25, 'F#4', 1), (26, 'D4', 1), (27, 'F#4', 1), (28, 'A4', 4), (32, 'B3', 3)]
    notes = [(b, m(n), d, True) for b, n, d in N]
    Bm, Cs7, Cmaj, D = chord('B2', 'min'), chord('C#3', '7'), chord('C3', 'maj'), chord('D3', 'maj')
    seq = [(0, 8, Bm, 'B1'), (8, 4, Cs7, 'C#2'), (12, 4, Cmaj, 'C2'), (16, 8, Bm, 'B1'), (24, 8, D, 'D2'),
           (32, 3, Bm, 'B1')]
    chords = [(b, d, ch, m(bass)) for b, d, ch, bass in seq]
    return dict(name='Hall of the Mountain King', team='FIRE', bpm=bpm, meter=8, notes=notes, chords=chords,
                style='dark', downbeat=0, end_beat=35, transpose=12)


def turkish_march():
    """Mozart, Rondo alla Turca (1784): the opening phrase twice, in A minor, one beat per eighth note."""
    bpm = 200
    line = [(0, 'B4', 0.5), (0.5, 'A4', 0.5), (1, 'G#4', 0.5), (1.5, 'A4', 0.5), (2, 'C5', 2),
            (4, 'D5', 0.5), (4.5, 'C5', 0.5), (5, 'B4', 0.5), (5.5, 'C5', 0.5), (6, 'E5', 2),
            (8, 'F5', 0.5), (8.5, 'E5', 0.5), (9, 'D#5', 0.5), (9.5, 'E5', 0.5), (10, 'B5', 0.5), (10.5, 'A5', 0.5),
            (11, 'G#5', 0.5), (11.5, 'A5', 0.5), (12, 'B5', 0.5), (12.5, 'A5', 0.5), (13, 'G#5', 0.5),
            (13.5, 'A5', 0.5), (14, 'C6', 2)]
    notes = []
    for off in (0, 16):                       # sixteenths off the eighth-note grid play as flourishes
        notes += [(off + b, m(n), d, d >= 1 or b % 1 == 0) for b, n, d in line]
    notes.append((32, m('A5'), 4, True))
    Am, E7 = chord('A2', 'min'), chord('E3', '7')
    seq = [(0, 4, Am, 'A1'), (4, 4, E7, 'E2'), (8, 4, Am, 'A1'), (12, 2, E7, 'E2'), (14, 2, Am, 'A1')]
    chords = [(off + b, d, ch, m(bass)) for off in (0, 16) for b, d, ch, bass in seq]
    chords.append((32, 4, Am, m('A1')))
    return dict(name='Turkish March', team='FIRE', bpm=bpm, meter=4, notes=notes, chords=chords,
                style='pop', downbeat=0, end_beat=36, transpose=0)


def bumblebee():
    """Rimsky-Korsakov, Flight of the Bumblebee (1900): the chromatic opening; the marble hits every eighth note
    and the sixteenths between are played as flourishes."""
    bpm = 200
    a = ['E5', 'D#5', 'D5', 'C#5', 'C5', 'F5', 'E5', 'D#5']
    b = ['E5', 'D#5', 'D5', 'C#5', 'C5', 'C#5', 'D5', 'D#5']
    c = ['A5', 'G#5', 'G5', 'F#5', 'F5', 'A#5', 'A5', 'G#5']
    d = ['A5', 'G#5', 'G5', 'F#5', 'F5', 'F#5', 'G5', 'G#5']
    e = ['E5', 'D#5', 'D5', 'C#5', 'C5', 'B4', 'C5', 'B4']
    notes = []
    for bar, ns in enumerate([a, b, a, b, c, d, e]):
        for i, n in enumerate(ns):
            notes.append((bar * 4 + i * 0.5, m(n), 0.5, i % 2 == 0))
    notes.append((28, m('A4'), 3, True))
    Am, E7, Dm = chord('A2', 'min'), chord('E3', '7'), chord('D3', 'min')
    seq = [(0, 4, Am, 'A1'), (4, 4, E7, 'E2'), (8, 4, Am, 'A1'), (12, 4, E7, 'E2'), (16, 4, Dm, 'D2'),
           (20, 4, Dm, 'D2'), (24, 4, E7, 'E2'), (28, 3, Am, 'A1')]
    chords = [(b_, d_, ch, m(bass)) for b_, d_, ch, bass in seq]
    return dict(name='Flight of the Bumblebee', team='FIRE', bpm=bpm, meter=4, notes=notes, chords=chords,
                style='trap', downbeat=0, end_beat=31, transpose=0)


def swan_lake():
    """Tchaikovsky, Swan Lake (1876): the swan theme, in B minor, one beat per quarter note."""
    bpm = 112
    N = [(0, 'F#4', 2), (2, 'B4', 0.5), (2.5, 'C#5', 0.5), (3, 'D5', 0.5), (3.5, 'E5', 0.5),
         (4, 'F#5', 3), (7, 'D5', 1), (8, 'F#5', 3), (11, 'D5', 1), (12, 'F#5', 3), (15, 'B4', 0.5),
         (15.5, 'D5', 0.5), (16, 'B4', 4)]
    notes = [(b, m(n), d, True) for b, n, d in N]
    Bm, G, Em = chord('B2', 'min'), chord('G2', 'maj'), chord('E3', 'min')
    seq = [(0, 4, Bm, 'B1'), (4, 4, Bm, 'B1'), (8, 4, G, 'G1'), (12, 4, Em, 'E2'), (16, 4, Bm, 'B1')]
    chords = [(b, d, ch, m(bass)) for b, d, ch, bass in seq]
    return dict(name='Swan Lake', team='ICE', bpm=bpm, meter=4, notes=notes, chords=chords,
                style='pizz', downbeat=0, end_beat=20, transpose=12)


def fur_elise():
    """Beethoven, Für Elise (1810): the opening, in A minor, one beat per eighth note (3/8)."""
    bpm = 150
    N = [(0, 'E5', 0.5), (0.5, 'D#5', 0.5),
         (1, 'E5', 0.5), (1.5, 'D#5', 0.5), (2, 'E5', 0.5), (2.5, 'B4', 0.5), (3, 'D5', 0.5), (3.5, 'C5', 0.5),
         (4, 'A4', 1.5), (5.5, 'C4', 0.5), (6, 'E4', 0.5), (6.5, 'A4', 0.5),
         (7, 'B4', 1.5), (8.5, 'E4', 0.5), (9, 'G#4', 0.5), (9.5, 'B4', 0.5),
         (10, 'C5', 1.5), (11.5, 'E4', 0.5), (12, 'E5', 0.5), (12.5, 'D#5', 0.5),
         (13, 'E5', 0.5), (13.5, 'D#5', 0.5), (14, 'E5', 0.5), (14.5, 'B4', 0.5), (15, 'D5', 0.5), (15.5, 'C5', 0.5),
         (16, 'A4', 1.5), (17.5, 'C4', 0.5), (18, 'E4', 0.5), (18.5, 'A4', 0.5),
         (19, 'B4', 1.5), (20.5, 'E4', 0.5), (21, 'C5', 0.5), (21.5, 'B4', 0.5),
         (22, 'A4', 3)]
    notes = [(b, m(n), d, True) for b, n, d in N]
    Am, E = chord('A2', 'min'), chord('E2', 'maj')
    seq = [(0, 4, Am, 'A1'), (4, 3, Am, 'A1'), (7, 3, E, 'E2'), (10, 3, Am, 'A1'), (13, 3, Am, 'A1'),
           (16, 3, Am, 'A1'), (19, 3, E, 'E2'), (22, 3, Am, 'A1')]
    chords = [(b, d, ch, m(bass)) for b, d, ch, bass in seq]
    return dict(name='Für Elise', team='ICE', bpm=bpm, meter=3, notes=notes, chords=chords,
                style='waltz', downbeat=1, end_beat=25, transpose=12)


def brahms_lullaby():
    """Brahms, Lullaby (Wiegenlied, 1868): the first verse, in C major, one beat per quarter note (3/4)."""
    bpm = 126
    N = [(0, 'E5', 0.5), (0.5, 'E5', 0.5),
         (1, 'G5', 1.5), (2.5, 'E5', 0.5), (3, 'E5', 1),
         (4, 'G5', 2), (6, 'E5', 0.5), (6.5, 'G5', 0.5),
         (7, 'C6', 1), (8, 'B5', 1.5), (9.5, 'A5', 0.5),
         (10, 'A5', 1), (11, 'G5', 1), (12, 'D5', 0.5), (12.5, 'E5', 0.5),
         (13, 'F5', 1), (14, 'D5', 1), (15, 'D5', 0.5), (15.5, 'E5', 0.5),
         (16, 'F5', 2), (18, 'D5', 0.5), (18.5, 'F5', 0.5),
         (19, 'B5', 0.5), (19.5, 'A5', 0.5), (20, 'G5', 1), (21, 'B5', 1),
         (22, 'C6', 3)]
    notes = [(b, m(n), d, True) for b, n, d in N]
    C, G7 = chord('C3', 'maj'), chord('G2', '7')
    seq = [(0, 1, C, 'C2'), (1, 3, C, 'C2'), (4, 3, C, 'C2'), (7, 3, G7, 'G1'), (10, 3, G7, 'G1'), (13, 3, G7, 'G1'),
           (16, 3, G7, 'G1'), (19, 3, G7, 'G1'), (22, 3, C, 'C2')]
    chords = [(b, d, ch, m(bass)) for b, d, ch, bass in seq]
    return dict(name="Brahms' Lullaby", team='ICE', bpm=bpm, meter=3, notes=notes, chords=chords,
                style='waltz', downbeat=1, end_beat=25, transpose=0)


LIBRARY = {
    'carol_of_the_bells': carol_of_the_bells,
    'jingle_bells': jingle_bells,
    'sugar_plum': sugar_plum,
    'deck_the_halls': deck_the_halls,
    'god_rest_ye': god_rest_ye,
    'we_wish_you': we_wish_you,
    'mountain_king': mountain_king,
    'turkish_march': turkish_march,
    'bumblebee': bumblebee,
    'swan_lake': swan_lake,
    'fur_elise': fur_elise,
    'brahms_lullaby': brahms_lullaby,
}


def songs():
    import settings
    out = []
    for r in settings.ROUNDS:
        s = LIBRARY[r['song']]()
        s['team'] = r['team']
        out.append(s)
    return out


SONGS = songs()

if __name__ == '__main__':
    for s in SONGS:
        spb = 60.0 / s['bpm']
        hits = [n for n in s['notes'] if n[3]]
        gaps = [(hits[i + 1][0] - hits[i][0]) * spb for i in range(len(hits) - 1)]
        print(f"{s['name']:32s} hits={len(hits):3d} span={(hits[-1][0] - hits[0][0]) * spb:5.2f}s "
              f"min_gap={min(gaps):.3f} max_gap={max(gaps):.3f}")
