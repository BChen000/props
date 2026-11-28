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
optional:
hue           turns the studio (floor, sky, background, stand) around the colour wheel by this many degrees, so
              a video doesn't look like the others; the rainbow tiles keep their colours. 0 = the shipped blue-gray.
              100 rose pink (sat 0.9), -95 sage green (sat 0.7), 40 with bright 0.35 a dark indigo night
sat, bright   scale the studio's colourfulness and brightness after the turn (1 = as turned)
marble_shift  starts the marble colours at this index of timeline.MARBLE_SRGB (0 = the white first marble)
"""

G4, A4 = 67, 69
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


def _mary():
    a = [E5, D5, C5, D5, E5, E5, E5, -E5]
    b = [D5, D5, D5, -D5, E5, G5, G5, -G5]
    a2 = [E5, D5, C5, D5, E5, E5, E5, E5]
    end = [D5, D5, E5, D5, C5, -C5, 0, 0]
    ca = ["C"] * 8
    cb = ["G"] * 4 + ["C"] * 4
    cend = ["G7", "G7", "C", "G7"] + ["C"] * 4
    return (a + b + a2 + end) * 2, (ca + cb + ca + cend) * 2


def _macdonald():
    farm = [C5, C5, C5, G4, A4, A4, G4, -G4]
    eio = [E5, E5, D5, D5, C5, -C5, 0, 0]
    pickup = eio[:7] + [G4]
    run = [G4, C5, E5, G5, C6, E6, G6, C7]
    cf = ["C"] * 4 + ["F", "F", "C", "C"]
    ce = ["C", "C", "G7", "G7"] + ["C"] * 4
    return farm + pickup + farm + eio + farm + eio + run, (cf + ce) * 3 + ["C"] * len(run)


def _frere():
    a = [C5, D5, E5, C5]
    b = [E5, F5, G5, -G5]
    c = [G5, A5, G5, F5, E5, C5]
    d = [C5, G4, C5, -C5]
    ca, cb = ["C"] * 4, ["C", "G7", "C", "C"]
    cc, cd = ["C", "F", "C", "G7", "C", "C"], ["C", "G", "C", "C"]
    mel = a + a + b + b + c + c + d + d + c + c + d + d
    return mel, ca + ca + cb + cb + cc + cc + cd + cd + cc + cc + cd + cd


def _joy():
    B5 = 83
    joy = [C6, B5, A5, G5, F5, E5, D5, C5]
    king = [G5, A5, A5, B5, B5, C6, -C6, -C6]
    room = [C6, C6, B5, A5, G5, G5, F5, E5]
    sing1 = [E5, E5, E5, E5, E5, F5, G5, -G5]
    sing2 = [D5, D5, D5, D5, D5, E5, F5, -F5]
    end = [C5, C6, A5, G5, F5, E5, F5, E5, D5, C5, -C5, -C5]
    cj = ["C", "G", "F", "C", "F", "C", "G", "C"]
    ck = ["C", "F", "F", "G", "G", "C", "C", "C"]
    cr = ["C", "C", "G", "F", "C", "C", "G7", "C"]
    cs1 = ["C"] * 5 + ["G7", "C", "C"]
    cs2 = ["G"] * 5 + ["C", "G7", "G7"]
    ce = ["C", "C", "F", "C", "F", "C", "G7", "C", "G7", "C", "C", "C"]
    return joy + king + room + room + sing1 + sing2 + end, cj + ck + cr + cr + cs1 + cs2 + ce


def _silent():
    B5, D6, F6 = 83, 86, 89
    night = [G5, A5, G5, E5, -E5, -E5]
    calm = [D6, -D6, D6, B5, -B5, -B5]
    bright = [C6, -C6, C6, G5, -G5, -G5]
    round_ = [A5, -A5, A5, C6, B5, A5]
    sleep = [D6, -D6, D6, F6, D6, B5]
    peace = [C6, -C6, -C6, E6, -E6, -E6]
    sleep2 = [C6, G5, E5, G5, F5, D5]
    end = [C5, -C5, -C5, -C5, -C5, -C5]
    mel = night + night + calm + bright + round_ + night + round_ + night + sleep + peace + sleep2 + end
    c = lambda name: [name] * 6
    ch = (c("C") + c("C") + c("G7") + c("C") + c("F") + c("C") + c("F") + c("C") + c("G7") + c("C")
          + ["C"] * 3 + ["G7"] * 3 + c("C"))
    return mel, ch


_tw_mel, _tw_ch = _twinkle()
_sn_mel, _sn_ch = _silent()
_jb_mel, _jb_ch = _jingle()
_ml_mel, _ml_ch = _mary()
_om_mel, _om_ch = _macdonald()
_fj_mel, _fj_ch = _frere()
_jw_mel, _jw_ch = _joy()

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
    "mary-lamb": dict(
        name="Mary Had a Little Lamb",
        file="Marble_Staircase_Mary_Had_a_Little_Lamb",
        bpm=112.5,
        hue=100.0,
        sat=0.9,
        marble_shift=1,
        rounds=[1, 2, 3, 5, 8],
        offsets=[[0], [0, 3], [0, 3, 6], [0, 2, 4, 6, 8], [0, 1, 2, 3, 4, 5, 6, 7]],
        melody=_ml_mel,
        chords=_ml_ch,
    ),
    "old-macdonald": dict(
        name="Old MacDonald Had a Farm",
        file="Marble_Staircase_Old_MacDonald",
        bpm=120.0,
        hue=-95.0,
        sat=0.7,
        marble_shift=5,
        rounds=[1, 2, 3, 5, 8],
        offsets=[[0], [0, 1], [0, 2, 4], [0, 1, 2, 3, 4], [0, 1, 2, 3, 4, 5, 6, 7]],
        melody=_om_mel,
        chords=_om_ch,
    ),
    "frere-jacques": dict(
        name="Frère Jacques (Are You Sleeping)",
        file="Marble_Staircase_Frere_Jacques",
        bpm=112.5,
        hue=40.0,
        bright=0.35,
        marble_shift=7,
        rounds=[1, 2, 3, 5, 8],
        offsets=[[0], [0, 2], [0, 1, 2], [0, 1, 2, 4, 5], [0, 1, 2, 3, 4, 5, 6, 7]],
        melody=_fj_mel,
        chords=_fj_ch,
    ),
    "joy-to-the-world": dict(
        name="Joy to the World",
        file="Marble_Staircase_Joy_to_the_World",
        bpm=112.5,
        hue=130.0,
        sat=1.7,
        bright=0.45,
        marble_shift=4,
        rounds=[1, 2, 3, 5, 8],
        offsets=[[0], [0, 3], [0, 2, 4], [0, 1, 3, 4, 6], [0, 1, 2, 3, 4, 5, 6, 7]],
        melody=_jw_mel,
        chords=_jw_ch,
    ),
    "silent-night": dict(
        name="Silent Night",
        file="Marble_Staircase_Silent_Night",
        bpm=150.0,
        hue=172.0,
        sat=1.4,
        bright=0.42,
        marble_shift=11,
        rounds=[1, 2, 3, 5, 8],
        offsets=[[0], [0, 6], [0, 4, 8], [0, 2, 5, 8, 11], [0, 1, 2, 3, 4, 5, 6, 7]],
        melody=_sn_mel,
        chords=_sn_ch,
    ),
}


def beats_needed(song, tiles=8):
    return sum(offs[-1] + tiles for offs in song["offsets"])
