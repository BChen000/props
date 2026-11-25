"""narration-check / asr.py: offline English speech recognition with Whisper small.en (int8) through sherpa-onnx.

    from asr import transcribe
    text = transcribe("narration.wav", t0=12.3, t1=17.9)     # seconds; whole file if t0 is None

Settings (environment): WHISPER_DIR (default models/whisper-small.en next to this file, filled by get_models.py),
ASR_THREADS (default 2). Audio of any rate is resampled to 16 kHz, padded with 0.5 s of silence on both sides and
decoded in 28 s chunks, because Whisper's window is 30 s.
"""
import os
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
WHISPER_DIR = os.environ.get("WHISPER_DIR") or os.path.join(HERE, "models", "whisper-small.en")
THREADS = int(os.environ.get("ASR_THREADS", "2"))
_REC = None


def recognizer():
    global _REC
    if _REC is None:
        import sherpa_onnx
        enc = os.path.join(WHISPER_DIR, "small.en-encoder.int8.onnx")
        if not os.path.exists(enc):
            raise FileNotFoundError(enc + ": run python get_models.py (or set WHISPER_DIR)")
        _REC = sherpa_onnx.OfflineRecognizer.from_whisper(
            encoder=enc, decoder=os.path.join(WHISPER_DIR, "small.en-decoder.int8.onnx"),
            tokens=os.path.join(WHISPER_DIR, "small.en-tokens.txt"),
            num_threads=THREADS, language="en", task="transcribe")
    return _REC


def load(path, t0=None, t1=None):
    a, sr = sf.read(path, dtype="float32", always_2d=True)
    a = a.mean(axis=1)
    if t0 is not None:
        a = a[max(0, int(t0 * sr)):int(t1 * sr)]
    return a, sr


def transcribe(path, t0=None, t1=None):
    a, sr = load(path, t0, t1)
    if sr != 16000:
        import scipy.signal as ss
        a = ss.resample_poly(a, 16000, sr).astype(np.float32)
        sr = 16000
    a = np.concatenate([np.zeros(int(0.5 * sr), np.float32), a.astype(np.float32), np.zeros(int(0.5 * sr), np.float32)])
    rec = recognizer()
    out = []
    step = 28 * sr
    for i in range(0, len(a), step):
        s = rec.create_stream()
        s.accept_waveform(sr, a[i:i + step])
        rec.decode_stream(s)
        out.append(s.result.text.strip())
    return " ".join(x for x in out if x)


if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        print(os.path.basename(p), "=>", transcribe(p))
