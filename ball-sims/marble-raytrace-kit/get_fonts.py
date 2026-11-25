"""Downloads Montserrat (variable weight), the font of the "N MARBLES" round titles and the watermark.

Montserrat is free under the SIL Open Font License 1.1 (https://fonts.google.com/specimen/Montserrat).
The file comes from the google/fonts GitHub repo at a pinned commit and is checked against its SHA-256,
so titles render exactly like the shipped videos. It goes to fonts/ next to this script (gitignored).
Usage:  python3 get_fonts.py
"""
import hashlib
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
COMMIT = "83c62e30d87daa70216dab6b984d00d20d96d585"
URL = f"https://raw.githubusercontent.com/google/fonts/{COMMIT}/ofl/montserrat/Montserrat%5Bwght%5D.ttf"
SHA256 = "0f7b311b2f3279e4eef9b2f968bcdbab6e28f4daeb1f049f4f278a902bcd82f7"
OUT = os.path.join(HERE, "fonts", "Montserrat[wght].ttf")


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    if os.path.exists(OUT) and sha(OUT) == SHA256:
        print(f"ok       {OUT}")
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".part"
    urllib.request.urlretrieve(URL, tmp)
    got = sha(tmp)
    if got != SHA256:
        os.remove(tmp)
        print(f"FAILED   Montserrat: sha256 {got} != {SHA256}")
        return 1
    os.replace(tmp, OUT)
    print(f"ok       {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
