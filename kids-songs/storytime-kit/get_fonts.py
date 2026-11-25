"""Install the DejaVu fonts the Story Time props draw with (captions, hook card, signs, labels).

DejaVu fonts are free (Bitstream Vera licence + public-domain changes): https://dejavu-fonts.github.io
Tries the official 2.37 release zip on GitHub, then the npm package dejavu-fonts-ttf@2.37.3.
  python get_fonts.py           -> user font folder (~/.fonts or ~/Library/Fonts), then fc-cache
  python get_fonts.py --local   -> storytime-kit/fonts/ next to this file (gitignored)
Fonts that are already installed (system or user folder) are skipped.
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

FILES = ["DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "DejaVuSerif.ttf", "DejaVuSerif-Bold.ttf", "DejaVuSerif-Italic.ttf",
         "DejaVuSansMono-Bold.ttf", "DejaVuSansCondensed-Bold.ttf"]
ZIP_URL = "https://github.com/dejavu-fonts/dejavu-fonts/releases/download/version_2_37/dejavu-fonts-ttf-2.37.zip"
NPM_PKG = "dejavu-fonts-ttf@2.37.3"
HERE = os.path.dirname(os.path.abspath(__file__))
SEARCH = [os.path.join(HERE, "fonts"), "/usr/share/fonts/truetype/dejavu", os.path.expanduser("~/.fonts"),
          os.path.expanduser("~/.local/share/fonts"), os.path.expanduser("~/Library/Fonts")]


def font_dir(local):
    if local:
        return os.path.join(HERE, "fonts")
    if platform.system() == "Darwin":
        return os.path.expanduser("~/Library/Fonts")
    return os.path.expanduser("~/.fonts")


def missing():
    return [f for f in FILES if not any(os.path.exists(os.path.join(d, f)) for d in SEARCH)]


def from_github(dest, names):
    data = urllib.request.urlopen(ZIP_URL, timeout=60).read()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for f in names:
            name = [n for n in z.namelist() if n.endswith("/" + f)][0]
            with open(os.path.join(dest, f), "wb") as fh:
                fh.write(z.read(name))


def from_npm(dest, names):
    tmp = tempfile.mkdtemp()
    try:
        subprocess.run(["npm", "pack", NPM_PKG, "--silent"], cwd=tmp, check=True, stdout=subprocess.DEVNULL)
        with tarfile.open(glob.glob(os.path.join(tmp, "*.tgz"))[0]) as t:
            for f in names:
                member = [m for m in t.getmembers() if m.name.endswith("/" + f)][0]
                with open(os.path.join(dest, f), "wb") as fh:
                    fh.write(t.extractfile(member).read())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    local = "--local" in sys.argv
    need = FILES if local else missing()
    if not need:
        print("all", len(FILES), "DejaVu fonts already installed")
    else:
        dest = font_dir(local)
        os.makedirs(dest, exist_ok=True)
        try:
            from_github(dest, need)
            print("downloaded", len(need), "fonts from GitHub release 2.37")
        except Exception as e:
            print("GitHub download failed:", e, "- trying npm", NPM_PKG)
            from_npm(dest, need)
            print("installed", len(need), "fonts from npm")
        if not local and shutil.which("fc-cache"):
            subprocess.run(["fc-cache", "-f", dest], check=False)
        print("into", dest)
    sys.path.insert(0, HERE)
    import storytime_kit
    print("storytime_kit loads", len(storytime_kit.TF), "typefaces")


if __name__ == "__main__":
    main()
