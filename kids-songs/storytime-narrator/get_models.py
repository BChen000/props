"""Download the Kokoro v1.0 int8 ONNX model and voice pack the Story Time narrator uses (Apache-2.0, ~120 MB in all).

From the kokoro-onnx GitHub releases (https://github.com/thewh1teagle/kokoro-onnx, tag model-files-v1.0):
  kokoro-v1.0.int8.onnx  (92,361,271 bytes)   sha256 6e742170d309016e5891a994e1ce1559c702a2ccd0075e67ef7157974f6406cb
  voices-v1.0.bin        (28,214,398 bytes)   sha256 bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d

  python get_models.py            -> models/ next to this file (gitignored)
  python get_models.py DIR        -> DIR
narrate.py looks in KOKORO_DIR, then models/ here, then /home/claude/models/kokoro.
This is the int8 model, not the fp32 kokoro-v1.0.onnx the Wildlore narrator uses: they sound slightly different.
"""
import hashlib
import os
import sys
import urllib.request

BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
FILES = {
    "kokoro-v1.0.int8.onnx": (92361271, "6e742170d309016e5891a994e1ce1559c702a2ccd0075e67ef7157974f6406cb"),
    "voices-v1.0.bin": (28214398, "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d"),
}
HERE = os.path.dirname(os.path.abspath(__file__))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    dest = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "models")
    os.makedirs(dest, exist_ok=True)
    for name, (size, digest) in FILES.items():
        out = os.path.join(dest, name)
        if os.path.exists(out) and os.path.getsize(out) == size:
            print("have", out)
            continue
        print("downloading", name, "...", flush=True)
        urllib.request.urlretrieve(BASE + name, out + ".part")
        if sha256(out + ".part") != digest:
            os.remove(out + ".part")
            raise SystemExit(f"{name}: checksum mismatch, download removed")
        os.replace(out + ".part", out)
        print("wrote", out, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()
