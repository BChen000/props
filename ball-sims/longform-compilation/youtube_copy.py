#!/usr/bin/env python3
"""Writes build/youtube_copy.txt: three titles for YouTube's A/B test, the description with chapters."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import settings as S  # noqa: E402

# ===================================================================== SETTINGS (shipped values)
N_SONGS = len({it["title"] for it in S.ITEMS if it["kind"] == "song"})   # different songs (Twinkle plays twice)
N_GAMES = sum(it["kind"] in ("race", "run") for it in S.ITEMS)
TITLES = [
    S.TITLE,
    "Can You Guess Every Marble Song? 🎵",
    "Which Song Are the Marbles Playing? 🎵",
]
PREMISE = (f"Marbles roll down rainbow stairs and play {N_SONGS} songs. Guess each one before the answer pops up, "
           f"play {N_GAMES} marble challenges, then stay for a brand-new bonus song!")
COMMENT_LINE = "Comment your score 🔴🟠🟡🟢🔵🟣"
MADE_WITH = "Made with a 3D physics simulation"
HASHTAGS = "#marbles #satisfying #guessthesong #marblemusic #pickyourcolor"


def main():
    ch = open(os.path.join(S.BUILD, "chapters.txt")).read().strip()
    songs = []
    for it in S.ITEMS:
        if it["kind"] in ("song", "bonus") and it["title"] not in songs:
            songs.append(it["title"])
    text = "\n".join([
        "TITLES (main first; all three go into Studio's A/B test)", *TITLES, "",
        "DESCRIPTION", PREMISE, COMMENT_LINE, MADE_WITH, HASHTAGS, "", "Chapters", ch, "",
        "Songs (spoilers!): " + "; ".join(songs),
    ])
    p = os.path.join(S.BUILD, "youtube_copy.txt")
    open(p, "w").write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
