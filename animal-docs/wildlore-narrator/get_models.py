"""Download the Kokoro v1.0 ONNX model and voice pack the Wildlore narrator uses (Apache-2.0, ~350 MB in all).

From the kokoro-onnx GitHub releases (https://github.com/thewh1teagle/kokoro-onnx, tag model-files-v1.0):
  kokoro-v1.0.onnx  (325,532,387 bytes)
  voices-v1.0.bin   (28,214,398 bytes)

  python get_models.py            -> models/ next to this file (don't commit it)
  python get_models.py DIR        -> DIR
narrate.py looks in KOKORO_DIR, then models/ here, then /home/claude/models/kokoro.
"""
import os
import sys
import urllib.request

BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
FILES = {"kokoro-v1.0.onnx": 325532387, "voices-v1.0.bin": 28214398}
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    dest = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "models")
    os.makedirs(dest, exist_ok=True)
    for name, size in FILES.items():
        out = os.path.join(dest, name)
        if os.path.exists(out) and os.path.getsize(out) == size:
            print("have", out)
            continue
        print("downloading", name, "...", flush=True)
        urllib.request.urlretrieve(BASE + name, out + ".part")
        os.replace(out + ".part", out)
        print("wrote", out, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()
