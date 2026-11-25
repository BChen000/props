"""Songs for the twin staircase. Add a song by adding an entry to SONGS.

Two lanes of 16 tiles. Every marble hits one tile per beat; each beat plays the next note of the song:
the front (melody) lane plays `melody[beat]`, the back (harmony) lane plays `harmony[beat]`. Notes are MIDI numbers
(72 = C5); a negative number is the previous note held (a soft sparkle an octave up in the melody lane, a soft
chord tone in the harmony lane). Extra marbles on the same lane at the same beat add sparkles (melody lane) or
bass and chord tones (harmony lane, see VOICING).

rounds   per round, the marbles as (lane, beat offset from the round's start); MEL_LANE = 1 is in front.
         Rounds follow each other with no gap, so the song needs sum(max offset + 16) beats.
chords   one chord name per beat (keys of VOICING)
"""

MEL_LANE, HAR_LANE = 1, 0

VOICING = {"C": dict(bass=48, mid=[55, 60], sp=[88, 91]), "G": dict(bass=43, mid=[50, 55], sp=[86, 91]),
           "F": dict(bass=41, mid=[53, 57], sp=[89, 93]), "G7": dict(bass=43, mid=[53, 59], sp=[86, 89]),
           "Am": dict(bass=45, mid=[52, 57], sp=[88, 93]), "E": dict(bass=40, mid=[56, 59], sp=[88, 92])}
CHORD_PCS = {"C": (0, 4, 7), "G": (7, 11, 2), "F": (5, 9, 0), "G7": (7, 11, 2, 5), "Am": (9, 0, 4), "E": (4, 8, 11)}


def harmonize(melody, chords, low=3, high=9):
    """A harmony line from the chords: under each struck melody note, the highest chord tone 3-9 semitones below it;
    held melody notes hold the harmony too."""
    out, prev = [], None
    for m, c in zip(melody, chords):
        if m > 0:
            cands = [n for n in range(m - high, m - low + 1) if n % 12 in CHORD_PCS[c]]
            prev = max(cands) if cands else m - 5
            out.append(prev)
        else:
            out.append(-prev if prev else -(abs(m) - 5))
    return out


def _ode():
    p1 = [76, 76, 77, 79, 79, 77, 76, 74, 72, 72, 74, 76, 76, 74, 74, -74]
    p2 = [76, 76, 77, 79, 79, 77, 76, 74, 72, 72, 74, 76, 74, 72, 72, -72]
    h1 = [72, 72, 74, 76, 76, 74, 72, 71, 64, 64, 65, 67, 72, 71, 71, -71]
    h2 = [72, 72, 74, 76, 76, 74, 72, 71, 64, 64, 65, 67, 71, 64, 64, -64]
    c1 = ["C"] * 4 + ["G"] * 4 + ["C"] * 5 + ["G"] * 3
    c2 = ["C"] * 4 + ["G"] * 4 + ["C"] * 4 + ["G"] + ["C"] * 3
    return (p1 + p2 + p1 + p2 + [79, 84, 88, 91], h1 + h2 + h1 + h2 + [76, 79, 84, 88],
            c1 + c2 + c1 + c2 + ["C"] * 4)



G4, A4, B4, C5, D5, DS5, E5, F5, G5, A5, B5 = 67, 69, 71, 72, 74, 75, 76, 77, 79, 81, 83
C4, E4, GS4, C6, D6, E6, F6, G6, C7 = 60, 64, 68, 84, 86, 88, 89, 91, 96
ODE_ROUNDS = [
    [(MEL_LANE, 0)],
    [(MEL_LANE, 0), (HAR_LANE, 0)],
    [(MEL_LANE, 0), (HAR_LANE, 0), (MEL_LANE, 1), (HAR_LANE, 1)],
    [(MEL_LANE, i // 2) if i % 2 == 0 else (HAR_LANE, i // 2) for i in range(8)],
]


def _london():
    v = [G5, A5, G5, F5, E5, F5, G5, -G5, D5, E5, F5, -F5, E5, F5, G5, -G5,
         G5, A5, G5, F5, E5, F5, G5, -G5, D5, -D5, G5, -G5, E5, C5, -C5, -C5]
    c = ["C"] * 8 + ["G"] * 4 + ["C"] * 4 + ["C"] * 8 + ["G"] * 4 + ["C"] * 4
    mel, ch = v + v + [E5, G5, C6, -C6], c + c + ["C"] * 4
    return mel, harmonize(mel, ch), ch


def _frere():
    p = [C5, D5, E5, C5, C5, D5, E5, C5, E5, F5, G5, -G5, E5, F5, G5, -G5,
         G5, A5, G5, F5, E5, C5, G5, A5, G5, F5, E5, C5, C5, G4, C5, -C5, C5, G4, C5, -C5]
    mel = p + p
    har = [48, -48, -48, -48, 55, -55, -55, -55] + [m - 12 if m > 0 else m + 12 for m in mel[:-8]]
    return mel, har, ["C"] * len(mel)


def _bday():
    l1 = [G5, G5, A5, G5, C6, B5, -B5]
    l2 = [G5, G5, A5, G5, D6, C6, -C6]
    l3 = [G5, G5, G6, E6, C6, B5, A5, -A5]
    l4 = [F6, F6, E6, C6, D6, C6, -C6, -C6]
    c = (["C"] * 4 + ["G7"] * 3 + ["G7"] * 5 + ["C"] * 2 + ["C"] * 4 + ["F"] * 4 + ["F", "F", "C", "C", "G7", "C", "C", "C"])
    v = l1 + l2 + l3 + l4
    mel, ch = v + v + [C6, E6, G6, C7, -C7, -C7, -C7, -C7], c + c + ["C"] * 8
    return mel, harmonize(mel, ch), ch


def _wenceslas():
    l1 = [C5, C5, C5, D5, C5, C5, G4, -G4]
    l2 = [A4, G4, A4, B4, C5, -C5, C5, -C5]
    l5 = [G5, F5, E5, D5, E5, D5, C5, -C5]
    c1 = ["C", "C", "C", "G", "C", "C", "G", "G"]
    c2 = ["F", "C", "F", "G", "C", "C", "C", "C"]
    c5 = ["C", "F", "C", "G", "C", "G", "C", "C"]
    mel = l1 + l2 + l1 + l2 + l5 + l2 + l1 + l2 + [E5, G5, C6, -C6]
    ch = c1 + c2 + c1 + c2 + c5 + c2 + c1 + c2 + ["C"] * 4
    return mel, harmonize(mel, ch), ch


def _elise():
    a = [E5, DS5, E5, DS5, E5, B4, D5, C5, A4, -A4, C4, E4, A4, B4, -B4, E4, GS4, B4, C5, -C5]
    a2 = [E4, E5, DS5, E5, DS5, E5, B4, D5, C5, A4, -A4, C4, E4, A4, B4, -B4, E4, C5, B4, A4, -A4, -A4]
    ca = ["Am"] * 10 + ["Am", "Am", "Am", "E", "E"] + ["E", "E", "E", "Am", "Am"]
    ca2 = ["Am"] * 11 + ["Am", "Am", "Am", "E", "E"] + ["Am", "Am", "E", "Am", "Am", "Am"]
    mel = a + a2 + a + [E4, C5, B4, A4, -A4, -A4]
    ch = ca + ca2 + ca + ["Am", "Am", "E", "Am", "Am", "Am"]
    return mel, harmonize(mel, ch), ch

_mel, _har, _chd = _ode()

SONGS = {
    "ode-to-joy": dict(
        name="Ode to Joy",
        file="Marble_Twin_Stairs_Ode_to_Joy",
        bpm=120.0,
        rounds=[
            [(MEL_LANE, 0)],
            [(MEL_LANE, 0), (HAR_LANE, 0)],
            [(MEL_LANE, 0), (HAR_LANE, 0), (MEL_LANE, 1), (HAR_LANE, 1)],
            [(MEL_LANE, i // 2) if i % 2 == 0 else (HAR_LANE, i // 2) for i in range(8)],
        ],
        melody=_mel,
        harmony=_har,
        chords=_chd,
    ),
    "london-bridge": dict(
        name="London Bridge",
        file="Marble_Twin_Stairs_London_Bridge",
        bpm=120.0,
        rounds=ODE_ROUNDS,
        melody=_london()[0],
        harmony=_london()[1],
        chords=_london()[2],
    ),
    "frere-jacques": dict(
        name="Frere Jacques",
        file="Marble_Twin_Stairs_Frere_Jacques",
        bpm=120.0,
        rounds=[[(MEL_LANE, 0)], [(MEL_LANE, 0), (HAR_LANE, 0)], [(MEL_LANE, 0), (HAR_LANE, 0), (MEL_LANE, 2), (HAR_LANE, 2)], [(MEL_LANE, 2 * (i // 2)) if i % 2 == 0 else (HAR_LANE, 2 * (i // 2)) for i in range(8)]],
        melody=_frere()[0],
        harmony=_frere()[1],
        chords=_frere()[2],
    ),
    "happy-birthday": dict(
        name="Happy Birthday",
        file="Marble_Twin_Stairs_Happy_Birthday",
        bpm=120.0,
        rounds=ODE_ROUNDS,
        melody=_bday()[0],
        harmony=_bday()[1],
        chords=_bday()[2],
    ),
    "good-king": dict(
        name="Good King Wenceslas",
        file="Marble_Twin_Stairs_Good_King_Wenceslas",
        bpm=120.0,
        rounds=ODE_ROUNDS,
        melody=_wenceslas()[0],
        harmony=_wenceslas()[1],
        chords=_wenceslas()[2],
    ),
    "fur-elise": dict(
        name="Fur Elise",
        file="Marble_Twin_Stairs_Fur_Elise",
        bpm=120.0,
        rounds=ODE_ROUNDS,
        melody=_elise()[0],
        harmony=_elise()[1],
        chords=_elise()[2],
    ),
}


def beats_needed(song, tiles=16):
    return sum(max(o for _, o in ents) + tiles for ents in song["rounds"])
