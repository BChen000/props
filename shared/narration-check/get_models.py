"""Download the speech recognizer narration-check uses: OpenAI Whisper small.en, int8 ONNX export by k2-fsa/sherpa-onnx
(MIT licence), from the sherpa-onnx GitHub release "asr-models".

The release archive is 636 MB (it also has float32 weights and test clips). This streams it and keeps only the three
files used, 375 MB in all, checking each one's SHA-256:
  small.en-encoder.int8.onnx, small.en-decoder.int8.onnx, small.en-tokens.txt

  python get_models.py            -> models/whisper-small.en/ next to this file (gitignored)
  python get_models.py --check    -> only report
Set WHISPER_DIR to use a copy that's already somewhere else (check.py reads it too).
"""
import hashlib
import os
import sys
import tarfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DEST = os.environ.get("WHISPER_DIR") or os.path.join(HERE, "models", "whisper-small.en")
URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-whisper-small.en.tar.bz2"
FILES = {
    "small.en-encoder.int8.onnx": "8bdac288f369aa94ee2194059238c465ed82ea9d47ee8fa4a8c0a891873e462f",
    "small.en-decoder.int8.onnx": "710ccf890e10f3faa15f51ec346081a2723c9f3adb6e4da81c6573a5a6f877fb",
    "small.en-tokens.txt": "306cd27f03c1a714eca7108e03d66b7dc042abe8c258b44c199a7ed9838dd930",
}


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def ok(name):
    p = os.path.join(DEST, name)
    return os.path.exists(p) and sha_file(p) == FILES[name]


def main():
    missing = [n for n in FILES if not ok(n)]
    if not missing:
        print("have", DEST)
        return 0
    if "--check" in sys.argv:
        print("missing", ", ".join(missing), "in", DEST)
        return 1
    os.makedirs(DEST, exist_ok=True)
    print("streaming", URL, "(636 MB; keeps 375 MB)")
    resp = urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "curl/8.5.0"}), timeout=120)
    with tarfile.open(fileobj=resp, mode="r|bz2") as tar:
        for m in tar:
            name = os.path.basename(m.name)
            if name not in missing or not m.isfile():
                continue
            out = os.path.join(DEST, name)
            h = hashlib.sha256()
            src = tar.extractfile(m)
            with open(out + ".part", "wb") as f:
                for b in iter(lambda: src.read(1 << 20), b""):
                    h.update(b); f.write(b)
            if h.hexdigest() != FILES[name]:
                os.remove(out + ".part")
                raise SystemExit("hash mismatch for " + name)
            os.replace(out + ".part", out)
            print("wrote", out, m.size, "bytes")
    left = [n for n in FILES if not ok(n)]
    if left:
        raise SystemExit("not found in the archive: " + ", ".join(left))
    return 0


if __name__ == "__main__":
    sys.exit(main())
