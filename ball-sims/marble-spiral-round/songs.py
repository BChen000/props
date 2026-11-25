"""Songs for the spiral round. Add a song by adding an entry to SONGS.

The spiral track is built from the song: one colored segment per note, as long as the note (length per eighth note
LE in scene.py), so a marble rolling at constant speed plays the tune, and marbles that follow it two bars apart sing
it as a round (canon). Each segment always plays its own pitch.

notes        [(midi, eighths)]; 72 = C5. Pitches need a color in PITCH_SRGB.
eighth       seconds per eighth note (0.21 s = 95 dotted-quarter beats per minute)
bar_eighths  eighths per bar, 6 for 6/8 (default) or 8 for 4/4; rounds enter 2 bars apart
rounds       marbles per round; a round's marbles enter 2 bars apart (CANON_BARS in timeline.py)
thumb_frame  optional: the thumbnail's frame (default: picked from the last round)
"""

PITCH_SRGB = {72: (238, 50, 50), 74: (250, 138, 28), 76: (250, 206, 38), 77: (44, 196, 96), 79: (36, 150, 240),
              84: (176, 84, 232)}

SONGS = {
    "row-row-row": dict(
        name="Row Row Row Your Boat",
        file="Marble_Spiral_Row_Your_Boat",
        notes=[(72, 3), (72, 3), (72, 2), (74, 1), (76, 3), (76, 2), (74, 1), (76, 2), (77, 1), (79, 6),
               (84, 1), (84, 1), (84, 1), (79, 1), (79, 1), (79, 1), (76, 1), (76, 1), (76, 1), (72, 1), (72, 1),
               (72, 1), (79, 2), (77, 1), (76, 2), (74, 1), (72, 6)],
        eighth=0.21,
        bar_eighths=6,
        rounds=[1, 2, 4],
        thumb_frame=1080,       # the upload's thumbnail (36.0 s: all 4 marbles of the last round on the track)
    ),
}
