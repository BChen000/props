#!/usr/bin/env python3
"""Writes build/youtube_copy.txt (title, description with chapters) from settings and build/chapters.txt."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import settings as S  # noqa: E402

# ===================================================================== SETTINGS (shipped values)
TITLE = "Guess the Marble Song! 🎵 20 Rounds + a Secret Bonus"
ALT_TITLES = ["Can You Guess Every Marble Song? 🎵", "Marbles Play 20 Songs 🎵 Can You Guess Them All?"]
PREMISE = ("Marbles roll down rainbow stairs and play 20 songs. Guess each one before the answer pops up, "
           "then stay for a brand-new bonus song!")
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
        "TITLE", TITLE, "", "Other title ideas:", *("- " + t for t in ALT_TITLES), "",
        "DESCRIPTION", PREMISE, COMMENT_LINE, MADE_WITH, HASHTAGS, "", "Chapters", ch, "",
        "Songs (spoilers!): " + ", ".join(songs),
    ])
    p = os.path.join(S.BUILD, "youtube_copy.txt")
    open(p, "w").write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
