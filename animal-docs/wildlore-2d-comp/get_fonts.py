"""Download the two EB Garamond fonts the labels, title and end card use (SIL Open Font License 1.1, Georg Duffner).

The episode used EBGaramond12-Regular.otf and EBGaramond12-Italic.otf as packaged by Ubuntu 24.04
(fonts-ebgaramond 0.016+git20210310.42d4f9f2-1). The upstream repository only has font sources, so this script
takes the two files from that exact package on archive.ubuntu.com and checks every hash.

  python get_fonts.py           -> fonts/ next to this file (gitignored; comp.py looks there first)
  python get_fonts.py --check   -> only report

Unpacking needs one of: dpkg-deb (Debian/Ubuntu), Python 3.14's compression.zstd, `pip install zstandard`, or the zstd tool.
"""
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.join(HERE, "fonts")
DEB_URL = ("https://archive.ubuntu.com/ubuntu/pool/universe/f/fonts-ebgaramond/"
           "fonts-ebgaramond_0.016+git20210310.42d4f9f2-1_all.deb")
DEB_SHA256 = "b74198e51e69e2509b191e141d2b4632d4147b8b7cf19b96edbe26144ee87ee0"
FILES = {
    "EBGaramond12-Regular.otf": "222794214c518fc0c3913585eb1e662a69153ad460a9eb75dde87718fe992a42",
    "EBGaramond12-Italic.otf": "86368d83c243438e640106bc33fd27942a5f70962a334546d1e3b4bb4a42de05",
}
INNER = "./usr/share/fonts/opentype/ebgaramond/"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def have(name):
    p = os.path.join(DEST, name)
    return os.path.exists(p) and sha(open(p, "rb").read()) == FILES[name]


def ar_member(deb, prefix):
    """Return the bytes of the first ar member whose name starts with prefix (a .deb is an ar archive)."""
    assert deb[:8] == b"!<arch>\n", "not a .deb"
    pos = 8
    while pos < len(deb):
        hdr = deb[pos:pos + 60]
        name = hdr[:16].decode().strip().rstrip("/")
        size = int(hdr[48:58].decode().strip())
        body = deb[pos + 60:pos + 60 + size]
        if name.startswith(prefix):
            return name, body
        pos += 60 + size + (size % 2)
    raise KeyError(prefix)


def unzstd(data):
    try:
        from compression import zstd  # Python 3.14+
        return zstd.decompress(data)
    except ImportError:
        pass
    try:
        import zstandard
        return zstandard.ZstdDecompressor().decompressobj().decompress(data)
    except ImportError:
        pass
    if shutil.which("zstd"):
        return subprocess.run(["zstd", "-dc"], input=data, capture_output=True, check=True).stdout
    raise RuntimeError("no zstd decoder: pip install zstandard")


def data_tar(deb, deb_path):
    if shutil.which("dpkg-deb"):
        return subprocess.run(["dpkg-deb", "--fsys-tarfile", deb_path], capture_output=True, check=True).stdout
    name, body = ar_member(deb, "data.tar")
    if name.endswith(".zst"):
        return unzstd(body)
    return body  # .xz / .gz / plain: tarfile opens these itself


def main():
    missing = [n for n in FILES if not have(n)]
    if not missing:
        print("have", ", ".join(os.path.join(DEST, n) for n in FILES))
        return 0
    if "--check" in sys.argv:
        print("missing", ", ".join(missing))
        return 1
    req = urllib.request.Request(DEB_URL, headers={"User-Agent": "curl/8.5.0"})  # the archive rejects Python's default agent
    deb = urllib.request.urlopen(req, timeout=120).read()
    if sha(deb) != DEB_SHA256:
        raise SystemExit("unexpected package hash for " + DEB_URL)
    with tempfile.NamedTemporaryFile(suffix=".deb", delete=False) as tf:
        tf.write(deb)
    try:
        tar = tarfile.open(fileobj=io.BytesIO(data_tar(deb, tf.name)))
    finally:
        os.unlink(tf.name)
    os.makedirs(DEST, exist_ok=True)
    for name in missing:
        b = tar.extractfile(INNER + name).read()
        if sha(b) != FILES[name]:
            raise SystemExit("hash mismatch for " + name)
        with open(os.path.join(DEST, name), "wb") as f:
            f.write(b)
        print("wrote", os.path.join(DEST, name), len(b), "bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
