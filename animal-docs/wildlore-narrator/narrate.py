"""wildlore-narrator: the Wildlore documentary voice, an old British male narrator made with Kokoro v1.0 (ONNX).

The voice is a 75/25 blend of Kokoro's British male voices bm_george and bm_lewis, read in en-gb at 0.97 speed
with short clause pauses. A few words Kokoro mispronounces are fixed at the phoneme level (drupelets, anthocyanins,
trellises, cobalt-blue). Each line is trimmed to 30 ms before the first sound and 80 ms after the last.
--polish also runs every line through the Wildlore voice chain from the episode mix (high-pass 75 Hz, +2 dB low
shelf at 170 Hz, -1.5 dB at 420 Hz, +1.5 dB presence at 3.2 kHz, -1 dB air shelf at 9 kHz, 2.5:1 compression,
a small room reverb), at 48 kHz stereo.

  python narrate.py                         -> out/line_00.wav ... + out/lines_info.json, one line of lines.txt each
  python narrate.py my_script.txt --polish  -> also out/polished/line_XX.wav, ready to drop on a timeline
  python narrate.py --say "The jackalope."  -> out/say.wav, for auditioning a single sentence

Get the model once with `python get_models.py`.
"""
import argparse
import json
import os

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------- settings
VOICES = {"bm_george": 0.75, "bm_lewis": 0.25}   # blend weights over Kokoro voice styles
LANG = "en-gb"
SPEED = 0.97
CLAUSE_PAUSE = 0.16                               # seconds added at commas and clause breaks
PHONEME_FIXES = {                                 # Kokoro phonemes -> what the narrator should say
    "dɹˈuːpɛlɪts": "dɹˈuːplɪts",
    "ˈanθəsɪˌanɪnz": "ˌanθəsˈaɪənɪnz",
    "tɹˈɛlaɪzɪz": "tɹˈɛlɪsɪz",
    "kˈəʊbɒltblˈuː": "kˈəʊbɒlt blˈuː",
}
TRIM_DB, PAD_BEFORE, PAD_AFTER = 40, 0.03, 0.08   # silence trim threshold and the breath kept around each line
POLISH_SR = 48000


def model_dir():
    for d in (os.environ.get("KOKORO_DIR", ""), os.path.join(HERE, "models"), "/home/claude/models/kokoro"):
        if d and os.path.exists(os.path.join(d, "kokoro-v1.0.onnx")):
            return d
    raise SystemExit("Kokoro model not found: run python get_models.py (or set KOKORO_DIR)")


def load():
    from kokoro_onnx import Kokoro
    d = model_dir()
    k = Kokoro(os.path.join(d, "kokoro-v1.0.onnx"), os.path.join(d, "voices-v1.0.bin"))
    style = sum(w * k.get_voice_style(v) for v, w in VOICES.items())
    return k, style


def speak(k, style, text):
    import librosa
    ph = k.tokenizer.phonemize(text, lang=LANG)
    for a, b in PHONEME_FIXES.items():
        ph = ph.replace(a, b)
    s, sr = k.create(ph, voice=style, speed=SPEED, lang=LANG, is_phonemes=True, clause_pause=CLAUSE_PAUSE)
    _, idx = librosa.effects.trim(s, top_db=TRIM_DB)
    a = max(0, idx[0] - int(PAD_BEFORE * sr))
    b = min(len(s), idx[1] + int(PAD_AFTER * sr))
    return s[a:b], sr, ph


def polish(x, sr):
    """the voice chain used in the Wildlore mix: EQ, gentle compression and a small room, 48 kHz stereo"""
    import librosa
    from pedalboard import Compressor, HighpassFilter, HighShelfFilter, LowShelfFilter, Pedalboard, PeakFilter, Reverb
    x = librosa.resample(x.astype(np.float32), orig_sr=sr, target_sr=POLISH_SR)
    eq = Pedalboard([HighpassFilter(75), LowShelfFilter(cutoff_frequency_hz=170, gain_db=2.0),
                     PeakFilter(cutoff_frequency_hz=420, gain_db=-1.5, q=1.0), PeakFilter(cutoff_frequency_hz=3200, gain_db=1.5, q=0.8),
                     HighShelfFilter(cutoff_frequency_hz=9000, gain_db=-1.0), Compressor(threshold_db=-20, ratio=2.5, attack_ms=8, release_ms=120)])
    room = Pedalboard([Reverb(room_size=0.18, damping=0.6, wet_level=0.07, dry_level=1.0, width=0.6)])
    y = eq(x[None, :], POLISH_SR)[0]
    return room(np.stack([y, y]).astype(np.float32), POLISH_SR).T


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("script", nargs="?", default=os.path.join(HERE, "lines.txt"), help="one narration line per row")
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--polish", action="store_true")
    ap.add_argument("--say", default=None)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    k, style = load()
    if a.say:
        s, sr, ph = speak(k, style, a.say)
        sf.write(os.path.join(a.out, "say.wav"), s, sr)
        print(round(len(s) / sr, 2), "s", ph)
        return
    lines = [x.strip() for x in open(a.script, encoding="utf-8") if x.strip()]
    info, tot = [], 0.0
    if a.polish:
        os.makedirs(os.path.join(a.out, "polished"), exist_ok=True)
    for i, t in enumerate(lines):
        s, sr, ph = speak(k, style, t)
        sf.write(os.path.join(a.out, f"line_{i:02d}.wav"), s, sr)
        if a.polish:
            sf.write(os.path.join(a.out, "polished", f"line_{i:02d}.wav"), polish(s, sr), POLISH_SR, subtype="PCM_24")
        info.append(dict(i=i, dur=round(len(s) / sr, 3), text=t, ph=ph))
        tot += len(s) / sr
        print(i, round(len(s) / sr, 2), t[:60], flush=True)
    print("TOTAL", round(tot, 2), "s of speech")
    json.dump(info, open(os.path.join(a.out, "lines_info.json"), "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
