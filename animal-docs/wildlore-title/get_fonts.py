"""Download the two fonts the Wildlore title uses, from the google/fonts GitHub repo (SIL Open Font License).

  Cinzel[wght].ttf                     variable 400-900; the title uses 700 (THE) and 900 (BLUE, RASPBERRY)
  CormorantGaramond-Italic[wght].ttf   variable 300-700; the species line uses weight 560

With fontTools installed it also writes CormorantGaramond-Italic-560.ttf, a static instance at weight 560. ffmpeg's
drawtext can't pick a weight from a variable font, and this static file is what the shipped video and thumbnails used.

  python get_fonts.py           -> your user font folder (~/.fonts or ~/Library/Fonts)
  python get_fonts.py --local   -> wildlore-title/fonts/ next to this file (don't commit it)
"""
import os
import platform
import sys
import urllib.request

BASE = "https://raw.githubusercontent.com/google/fonts/main/ofl/"
FILES = {
    "Cinzel[wght].ttf": "cinzel/Cinzel%5Bwght%5D.ttf",
    "CormorantGaramond-Italic[wght].ttf": "cormorantgaramond/CormorantGaramond-Italic%5Bwght%5D.ttf",
}
STATIC_NAME, STATIC_WGHT = "CormorantGaramond-Italic-560.ttf", 560
HERE = os.path.dirname(os.path.abspath(__file__))


def font_dir(local):
    if local:
        return os.path.join(HERE, "fonts")
    if platform.system() == "Darwin":
        return os.path.expanduser("~/Library/Fonts")
    return os.path.expanduser("~/.fonts")


def main():
    dest = font_dir("--local" in sys.argv)
    os.makedirs(dest, exist_ok=True)
    for name, path in FILES.items():
        out = os.path.join(dest, name)
        if os.path.exists(out) and os.path.getsize(out) > 10000:
            print("have", out)
            continue
        data = urllib.request.urlopen(BASE + path, timeout=60).read()
        with open(out, "wb") as f:
            f.write(data)
        print("wrote", out, len(data), "bytes")
    static = os.path.join(dest, STATIC_NAME)
    try:
        from fontTools.ttLib import TTFont
        from fontTools.varLib import instancer
        f = TTFont(os.path.join(dest, "CormorantGaramond-Italic[wght].ttf"))
        instancer.instantiateVariableFont(f, {"wght": STATIC_WGHT}).save(static)
        print("wrote", static)
    except ImportError:
        print("fontTools not installed: skipped", STATIC_NAME, "(pip install fonttools)")


if __name__ == "__main__":
    main()
