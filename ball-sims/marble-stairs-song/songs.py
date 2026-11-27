"""Songs for the rainbow staircase. Add a song by adding an entry to SONGS.

Every marble hits one tile per beat, and each beat plays the next note of the song, so the melody is written as one
MIDI note per beat:
    72 = C5 ... 81 = A5    a struck melody note
    -n                     note n held from the beat before: a soft sparkle an octave up instead of a new strike
    0                      rest: a soft sparkle from the chord
When several marbles hit at once, the highest tile plays the melody and the others add bass, chord tones and
sparkles (see VOICING), so later rounds with more marbles sound fuller.

rounds   marbles per round (the "1 MARBLE" ... "8 MARBLES" titles)
offsets  per round, the beat each marble leaves the chute, counted from the round's first marble. Rounds follow
         each other with no gap, so the song needs sum(last offset + 8) beats; make_video.py checks this.
chords   one chord name per beat (keys of VOICING)
"""

C5, D5, E5, F5, G5, A5 = 72, 74, 76, 77, 79, 81
C6, E6, G6, C7 = 84, 88, 91, 96

VOICING = {
    "C": dict(bass=48, inner=[64, 67, 60], sp=[84, 88, 91]),
    "F": dict(bass=41, inner=[69, 60, 65], sp=[89, 93, 84]),
    "G": dict(bass=43, inner=[59, 62, 67], sp=[86, 91, 83]),
    "G7": dict(bass=43, inner=[59, 65, 67], sp=[86, 89, 91]),
}
GAINS = [1.0, 0.55, 0.30, 0.26, 0.22, 0.17, 0.15, 0.13]


def _twinkle():
    a1 = [C5, C5, G5, G5, A5, A5, G5, -G5]
    a2 = [F5, F5, E5, E5, D5, D5, C5, -C5]
    b = [G5, G5, F5, F5, E5, E5, D5, -D5]
    end = [E5, G5, C6, E6, G6, C7]
    ca1 = ["C"] * 4 + ["F"] * 2 + ["C"] * 2
    ca2 = ["F"] * 2 + ["C"] * 2 + ["G7"] * 2 + ["C"] * 2
    cb = ["C"] * 2 + ["F"] * 2 + ["C"] * 2 + ["G"] * 2
    return a1 + a2 + b + b + a1 + a2 + end, ca1 + ca2 + cb + cb + ca1 + ca2 + ["C"] * len(end)


def _jingle():
    p1 = [E5, E5, E5, -E5, E5, E5, E5, -E5, E5, G5, C5, D5, E5, -E5, 0, 0]
    p2 = [F5, F5, F5, F5, F5, E5, E5, E5, E5, D5, D5, E5, D5, -D5, G5, -G5]
    p4 = [F5, F5, F5, F5, F5, E5, E5, E5, G5, G5, F5, D5, C5, -C5, 0, 0]
    ch1 = ["C"] * 10 + ["C", "G"] + ["C"] * 4
    ch2 = ["F"] * 4 + ["C"] * 4 + ["C", "G", "G", "C"] + ["G7"] * 4
    ch4 = ["F"] * 4 + ["C"] * 4 + ["G7"] * 4 + ["C"] * 4
    return p1 + p2 + p1 + p4, ch1 + ch2 + ch1 + ch4


def _joy():
    B5 = 83
    p1 = [C6, B5, A5, G5, F5, E5, D5, C5, -C5]
    p2 = [G5, A5, A5, B5, B5, C6, -C6]
    p3 = [C6, C6, B5, A5, G5, G5, F5, E5, -E5]
    p5 = [E5, E5, E5, E5, E5, F5, G5, -G5]
    p6 = [F5, E5, D5, D5, D5, E5, F5, -F5]
    p7 = [E5, D5, C5, C6, A5, G5, F5, E5, F5, E5, D5, C5, -C5, -C5]
    c1 = ["C", "C", "F", "C", "F", "C", "G7", "C", "C"]
    c2 = ["C", "F", "F", "G", "G", "C", "C"]
    c3 = ["C", "C", "G", "F", "C", "C", "G7", "C", "C"]
    c5 = ["C", "C", "C", "C", "C", "G7", "C", "C"]
    c6 = ["G7", "C", "G", "G", "G", "C", "G7", "G7"]
    c7 = ["C", "G", "C", "C", "F", "C", "F", "C", "F", "C", "G7", "C", "C", "C"]
    return p1 + p2 + p3 + p3 + p5 + p6 + p7, c1 + c2 + c3 + c3 + c5 + c6 + c7


G4, A4, B4, FS5, B5 = 67, 69, 71, 78, 83


def _mary():
    v = [E5, D5, C5, D5, E5, E5, E5, -E5, D5, D5, D5, -D5, E5, G5, G5, -G5,
         E5, D5, C5, D5, E5, E5, E5, E5, D5, D5, E5, D5, C5, -C5, -C5, 0]
    c = ["C"] * 8 + ["G7"] * 4 + ["C"] * 4 + ["C"] * 8 + ["G7"] * 4 + ["C"] * 4
    return v + v, c + c


def _oldmac():
    l1 = [C5, C5, C5, G4, A4, A4, G4, -G4, E5, E5, D5, D5, C5, -C5, -C5, G4]
    l2 = [C5, C5, C5, G4, A4, A4, G4, -G4, E5, E5, D5, D5, C5, -C5, -C5, 0]
    c = ["C"] * 4 + ["F", "F", "C", "C"] + ["C", "C", "G7", "G7"] + ["C"] * 4
    return l1 + l2 + l1 + l2, c * 4


def _deck():
    a = [G5, F5, E5, D5, C5, D5, E5, C5, D5, E5, F5, D5, E5, D5, C5, B4, C5, -C5]
    b = [D5, E5, F5, D5, E5, F5, G5, D5, E5, FS5, G5, A5, B5, C6, B5, A5, G5, -G5]
    ca = ["C", "C", "C", "G7", "C", "G7", "C", "C", "G7", "C", "F", "G7", "C", "G7", "C", "G", "C", "C"]
    cb = ["G7", "C", "G7", "G7", "C", "G7", "C", "G7", "C", "G", "G", "F", "G", "C", "G", "F", "G", "G"]
    return a + a + b + a, ca + ca + cb + ca


def _merry():
    v = [G4, C5, C5, D5, C5, B4, A4, A4, A4, D5, D5, E5, D5, C5, B4, G4,
         G4, E5, E5, F5, E5, D5, C5, A4, G4, G4, A4, D5, B4, C5, -C5, 0]
    c = ["G7", "C", "C", "C", "C", "C", "F", "F", "F", "G", "G", "G", "G", "G", "G", "G",
         "G7", "C", "C", "C", "C", "C", "F", "F", "C", "C", "F", "G7", "G7", "C", "C", "C"]
    return v + v, c + c


_tw_mel, _tw_ch = _twinkle()
_jb_mel, _jb_ch = _jingle()
_joy_mel, _joy_ch = _joy()
_mary_mel, _mary_ch = _mary()
_om_mel, _om_ch = _oldmac()
_deck_mel, _deck_ch = _deck()
_merry_mel, _merry_ch = _merry()

SONGS = {
    "twinkle": dict(
        name="Twinkle Twinkle Little Star",
        file="Marble_Staircase_Twinkle",
        bpm=112.5,
        rounds=[1, 2, 3, 5, 8],
        offsets=[[0], [0, 1], [0, 1, 2], [0, 1, 2, 3, 4], [0, 1, 2, 3, 4, 5, 6, 7]],
        melody=_tw_mel,
        chords=_tw_ch,
    ),
    "jingle-bells": dict(
        name="Jingle Bells",
        file="Marble_Staircase_Jingle_Bells",
        bpm=112.5,
        rounds=[1, 2, 3, 5, 8],
        offsets=[[0], [0, 3], [0, 2, 4], [0, 2, 3, 5, 7], [0, 1, 2, 4, 5, 7, 8, 10]],
        melody=_jb_mel,
        chords=_jb_ch,
    ),
    "joy-to-the-world": dict(
        name="Joy to the World",
        file="Marble_Staircase_Joy_to_the_World",
        bpm=112.5,
        rounds=[1, 2, 3, 5, 8],
        offsets=[[0], [0, 3], [0, 2, 4], [0, 2, 3, 5, 7], [0, 1, 2, 4, 5, 7, 8, 10]],
        melody=_joy_mel,
        chords=_joy_ch,
    ),
    "mary-lamb": dict(
        name="Mary Had a Little Lamb",
        file="Marble_Staircase_Mary_Had_a_Little_Lamb",
        bpm=112.5,
        rounds=[1, 2, 3, 5, 8],
        offsets=[[0], [0, 3], [0, 2, 4], [0, 2, 3, 5, 7], [0, 1, 2, 4, 5, 7, 8, 10]],
        melody=_mary_mel,
        chords=_mary_ch,
    ),
    "old-macdonald": dict(
        name="Old MacDonald Had a Farm",
        file="Marble_Staircase_Old_MacDonald",
        bpm=112.5,
        rounds=[1, 2, 3, 5, 8],
        offsets=[[0], [0, 3], [0, 2, 4], [0, 2, 3, 5, 7], [0, 1, 2, 4, 5, 7, 8, 10]],
        melody=_om_mel,
        chords=_om_ch,
    ),
    "deck-the-halls": dict(
        name="Deck the Halls",
        file="Marble_Staircase_Deck_the_Halls",
        bpm=112.5,
        rounds=[1, 2, 3, 5, 8],
        offsets=[[0], [0, 4], [0, 3, 6], [0, 2, 4, 6, 8], [0, 2, 3, 5, 7, 9, 11, 14]],
        melody=_deck_mel,
        chords=_deck_ch,
    ),
    "merry-christmas": dict(
        name="We Wish You a Merry Christmas",
        file="Marble_Staircase_We_Wish_You_a_Merry_Christmas",
        bpm=112.5,
        rounds=[1, 2, 3, 5, 8],
        offsets=[[0], [0, 3], [0, 2, 4], [0, 2, 3, 5, 7], [0, 1, 2, 4, 5, 7, 8, 10]],
        melody=_merry_mel,
        chords=_merry_ch,
    ),
}


def beats_needed(song, tiles=8):
    return sum(offs[-1] + tiles for offs in song["offsets"])
