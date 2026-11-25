"""Download the speech-recognition model asr_check.py uses: Whisper base.en for sherpa-onnx (208.6 MB), from the
k2-fsa/sherpa-onnx GitHub release "asr-models", checked against its SHA-256 and unpacked into models/ (don't commit).

  python3 get_asr_model.py          -> models/sherpa-onnx-whisper-base.en/
  python3 get_asr_model.py DIR      -> DIR/sherpa-onnx-whisper-base.en/
"""
import hashlib, os, sys, tarfile, urllib.request

URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-whisper-base.en.tar.bz2"
SHA256 = "475bc7052ce299c007f6d5d5407ba8601f819a2867f6eecee510ed17df581542"
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    dest = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "models")
    final = os.path.join(dest, "sherpa-onnx-whisper-base.en")
    if os.path.exists(os.path.join(final, "base.en-encoder.onnx")):
        print("have", final); return
    os.makedirs(dest, exist_ok=True)
    tar = os.path.join(dest, "sherpa-onnx-whisper-base.en.tar.bz2")
    if not os.path.exists(tar):
        print("downloading", URL)
        urllib.request.urlretrieve(URL, tar + ".part"); os.replace(tar + ".part", tar)
    h = hashlib.sha256()
    with open(tar, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    if h.hexdigest() != SHA256:
        raise SystemExit("SHA-256 mismatch for %s: %s" % (tar, h.hexdigest()))
    with tarfile.open(tar) as t:
        t.extractall(dest, filter="data")
    os.remove(tar)
    print("wrote", final)


if __name__ == "__main__":
    main()
