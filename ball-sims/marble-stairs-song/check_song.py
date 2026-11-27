"""Checks a song's soundtrack against songs.py, beat by beat, without listening to it.

Usage: python3 check_song.py <song> [<song> ...]

Rebuilds the music log with music.py and checks that on every beat the melody voice plays the written note (a held
note plays its octave sparkle, a rest a chord sparkle), and that the bass and chord tones match the beat's chord
whenever more marbles hit. Builds the song's timeline first if build/<song>/timeline.json is missing (about 1 s).
Prints one line per song; any mismatch is listed by beat.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.environ.get("BUILD_DIR", os.path.join(HERE, "build"))


def check(name):
    sys.path.insert(0, HERE)
    sys.path.insert(0, os.path.join(HERE, "..", "marble-raytrace-kit"))
    from songs import SONGS, VOICING
    song = SONGS[name]
    os.environ["MARBLE_BPM"] = str(song["bpm"])
    import timeline
    import music
    out = os.path.join(BUILD, name)
    path = os.path.join(out, "timeline.json")
    if not os.path.exists(path):
        os.makedirs(out, exist_ok=True)
        timeline.build(song, out)
    tl = json.load(open(path))
    log = music.build(tl, song, os.path.join(out, "check_music.wav"))
    bad = []
    if [r[0] for r in log] != list(range(len(song["melody"]))):
        bad.append("the hits don't cover every beat of the melody exactly once")
    for b, t, n, voices in log:
        mel, ch = song["melody"][b], VOICING[song["chords"][b]]
        want = mel if mel > 0 else (-mel + 12 if mel < 0 else None)
        ok = voices[0] == want if want is not None else voices[0] in ch["sp"]
        if n > 1:
            ok = ok and voices[1] == ch["bass"]
        if n > 2:
            ok = ok and voices[2:5] == ch["inner"][:len(voices[2:5])]
        if not ok:
            bad.append("beat %d: melody %s, chord %s, played %s" % (b, mel, song["chords"][b], voices))
    print("%s: %d beats, %s" % (name, len(log), "every beat matches songs.py" if not bad else "%d problems" % len(bad)))
    for line in bad:
        print("  " + line)
    return not bad


if __name__ == "__main__":
    names = sys.argv[1:]
    if not names:
        sys.exit(__doc__)
    if len(names) > 1:          # one process per song: MARBLE_BPM is read when scene.py is imported
        codes = [subprocess.run([sys.executable, __file__, n]).returncode for n in names]
        sys.exit(max(codes))
    sys.exit(0 if check(names[0]) else 1)
