"""Install the Poppins weights the ball-sims props use (Regular, SemiBold, Bold, ExtraBold, Black).

Poppins is free (SIL Open Font License 1.1): https://fonts.google.com/specimen/Poppins
Tries the Google Fonts GitHub repo first, then falls back to the npm package
@fontsource/poppins (woff2 -> ttf with fontTools). Installs into the user font folder
and refreshes fontconfig. Usage:  python get_fonts.py
"""
import glob
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

WEIGHTS = {"Regular": 400, "SemiBold": 600, "Bold": 700, "ExtraBold": 800, "Black": 900}
GOOGLE_URL = "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-{}.ttf"
FONTSOURCE = "@fontsource/poppins@5.3.0"


def font_dir():
    if platform.system() == "Darwin":
        return os.path.expanduser("~/Library/Fonts")
    return os.path.expanduser("~/.fonts")


def is_font(path):
    try:
        with open(path, "rb") as f:
            magic = f.read(4)
        return magic in (b"\x00\x01\x00\x00", b"true", b"OTTO")
    except OSError:
        return False


def from_google(dest):
    ok = {}
    for name in WEIGHTS:
        out = os.path.join(dest, f"Poppins-{name}.ttf")
        try:
            urllib.request.urlretrieve(GOOGLE_URL.format(name), out)
        except Exception:
            pass
        ok[name] = is_font(out)
        if not ok[name] and os.path.exists(out):
            os.remove(out)
    return ok


def from_fontsource(dest, names):
    from fontTools.ttLib import TTFont  # pip install fonttools brotli
    tmp = tempfile.mkdtemp()
    try:
        subprocess.run(["npm", "pack", FONTSOURCE, "--silent"], cwd=tmp, check=True,
                       stdout=subprocess.DEVNULL)
        tgz = glob.glob(os.path.join(tmp, "*.tgz"))[0]
        with tarfile.open(tgz) as t:
            try:
                t.extractall(tmp, filter="data")
            except TypeError:  # Python without tar filters
                t.extractall(tmp)
        for name in names:
            w = WEIGHTS[name]
            src = os.path.join(tmp, "package", "files", f"poppins-latin-{w}-normal.woff2")
            f = TTFont(src)
            f.flavor = None
            f.save(os.path.join(dest, f"Poppins-{name}.ttf"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    dest = font_dir()
    os.makedirs(dest, exist_ok=True)
    ok = from_google(dest)
    missing = [n for n, good in ok.items() if not good]
    if missing:
        print("Google Fonts download failed for", missing, "- using npm @fontsource/poppins")
        from_fontsource(dest, missing)
    if shutil.which("fc-cache"):
        subprocess.run(["fc-cache", "-f"], check=False)
    print("Installed Poppins", ", ".join(WEIGHTS), "into", dest)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import kit
    if kit.check_fonts():
        print("Font check passed.")


if __name__ == "__main__":
    main()
