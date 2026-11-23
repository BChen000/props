"""Install DejaVu Sans Bold, the one font the neon-kit props use.

DejaVu fonts are free (Bitstream Vera licence + public-domain changes): https://dejavu-fonts.github.io
Tries the official 2.37 release zip on GitHub, then the npm package dejavu-fonts-ttf@2.37.3.
Installs into your user font folder and refreshes fontconfig.
  python get_fonts.py           -> user font folder (~/.fonts or ~/Library/Fonts)
  python get_fonts.py --local   -> neon-kit/fonts/ next to this file (don't commit it)
"""
import glob
import io
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile

FILE = "DejaVuSans-Bold.ttf"
ZIP_URL = "https://github.com/dejavu-fonts/dejavu-fonts/releases/download/version_2_37/dejavu-fonts-ttf-2.37.zip"
NPM_PKG = "dejavu-fonts-ttf@2.37.3"
HERE = os.path.dirname(os.path.abspath(__file__))


def font_dir(local):
    if local:
        return os.path.join(HERE, "fonts")
    if platform.system() == "Darwin":
        return os.path.expanduser("~/Library/Fonts")
    return os.path.expanduser("~/.fonts")


def from_github(dest):
    data = urllib.request.urlopen(ZIP_URL, timeout=60).read()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        name = [n for n in z.namelist() if n.endswith("/" + FILE)][0]
        with open(os.path.join(dest, FILE), "wb") as f:
            f.write(z.read(name))


def from_npm(dest):
    tmp = tempfile.mkdtemp()
    try:
        subprocess.run(["npm", "pack", NPM_PKG, "--silent"], cwd=tmp, check=True, stdout=subprocess.DEVNULL)
        with tarfile.open(glob.glob(os.path.join(tmp, "*.tgz"))[0]) as t:
            member = [m for m in t.getmembers() if m.name.endswith("/" + FILE)][0]
            with open(os.path.join(dest, FILE), "wb") as f:
                f.write(t.extractfile(member).read())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    local = "--local" in sys.argv
    dest = font_dir(local)
    os.makedirs(dest, exist_ok=True)
    try:
        from_github(dest)
        print("downloaded from GitHub release 2.37")
    except Exception as e:
        print("GitHub download failed:", e, "- trying npm", NPM_PKG)
        from_npm(dest)
        print("installed from npm")
    if not local and shutil.which("fc-cache"):
        subprocess.run(["fc-cache", "-f", dest], check=False)
    print("installed", os.path.join(dest, FILE))
    sys.path.insert(0, HERE)
    import neon_kit
    neon_kit._TF = None
    neon_kit.typeface()
    print("neon_kit finds the font")


if __name__ == "__main__":
    main()
