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
           "Am": dict(bass=45, mid=[52, 57], sp=[88, 93]), "Em": dict(bass=40, mid=[52, 59], sp=[88, 91]),
           "F": dict(bass=41, mid=[53, 57], sp=[89, 93])}


def _ode():
    p1 = [76, 76, 77, 79, 79, 77, 76, 74, 72, 72, 74, 76, 76, 74, 74, -74]
    p2 = [76, 76, 77, 79, 79, 77, 76, 74, 72, 72, 74, 76, 74, 72, 72, -72]
    h1 = [72, 72, 74, 76, 76, 74, 72, 71, 64, 64, 65, 67, 72, 71, 71, -71]
    h2 = [72, 72, 74, 76, 76, 74, 72, 71, 64, 64, 65, 67, 71, 64, 64, -64]
    c1 = ["C"] * 4 + ["G"] * 4 + ["C"] * 5 + ["G"] * 3
    c2 = ["C"] * 4 + ["G"] * 4 + ["C"] * 4 + ["G"] + ["C"] * 3
    return (p1 + p2 + p1 + p2 + [79, 84, 88, 91], h1 + h2 + h1 + h2 + [76, 79, 84, 88],
            c1 + c2 + c1 + c2 + ["C"] * 4)


def _canon():
    """Pachelbel's Canon in C, one beat per eighth note. The back lane plays the front lane's line one phrase
    (16 beats) later, as the canon does; the ground bass sets the chords, two beats each."""
    def q(line):
        return [x for n in line for x in (n, -n)]
    l1 = q([76, 74, 72, 71, 69, 67, 69, 71])
    l2 = q([84, 83, 81, 79, 77, 76, 77, 74])
    l3 = [84, 88, 91, 89, 88, 84, 88, 86, 84, 81, 84, 79, 77, 81, 79, 77]
    l4 = q([88, 86, 84, 83, 81, 79, 81, 83])
    ground = q([72, 67, 69, 64, 65, 60, 65, 67])
    ch = [c for c in ("C", "G", "Am", "Em", "F", "C", "F", "G") for _ in (0, 1)]
    return (l1 + l2 + l3 + l4 + [79, 84, 88, 91], ground + l1 + l2 + l3 + [76, 79, 84, 88],
            ch * 4 + ["C"] * 4)


_mel, _har, _chd = _ode()
_cn_mel, _cn_har, _cn_chd = _canon()

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
    "canon-in-d": dict(
        name="Canon in D",
        file="Marble_Twin_Stairs_Canon_in_D",
        bpm=132.0,
        hue=60.0,
        sat=0.8,
        bright=0.6,
        rounds=[
            [(MEL_LANE, 0)],
            [(MEL_LANE, 0), (HAR_LANE, 0)],
            [(MEL_LANE, 0), (HAR_LANE, 0), (MEL_LANE, 1), (HAR_LANE, 1)],
            [(MEL_LANE, i // 2) if i % 2 == 0 else (HAR_LANE, i // 2) for i in range(8)],
        ],
        melody=_cn_mel,
        harmony=_cn_har,
        chords=_cn_chd,
    ),
}


def beats_needed(song, tiles=16):
    return sum(max(o for _, o in ents) + tiles for ents in song["rounds"])
