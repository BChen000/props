"""The Baby Griffin narration: Kokoro v1.0 (ONNX), a 65/35 blend of bm_george and bm_lewis in en-gb, pitched down
0.8 semitone with Rubber Band (R3 engine, formants kept) for an older voice, trimmed and laid out with the script's
pauses. Writes build/audio/narration_raw.wav (24 kHz float) and build/audio/timings.json (each line's start/end).

  python3 tts.py                      the shipped read: speed 1.08, tempo 1.0, pause scale 1.15, -0.8 semitones
  python3 tts.py 1.0 1.0 1.0 -0.8     KSPEED TEMPO PAUSE_SCALE SEMITONES (the old positional form still works)

Models: KOKORO_DIR, ../wildlore-narrator/models (python ../wildlore-narrator/get_models.py) or /home/claude/models/kokoro.
Needs the rubberband command-line tool (apt-get install -y rubberband-cli).
"""
import numpy as np, soundfile as sf, json, sys, subprocess, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ep_paths
from script_lines import LINES
from scipy.signal import butter, sosfilt

# ---------------------------------------------------------------- settings (shipped values)
SETTINGS = dict(
    BLEND={'bm_george': 0.65, 'bm_lewis': 0.35},
    LANG='en-gb',
    KSPEED=1.08,          # Kokoro speed for most lines
    TEMPO=1.0,            # Rubber Band time stretch
    PAUSE_SCALE=1.15,     # multiplies each line's pause from script_lines.py
    SEMI=-0.8,            # pitch shift, semitones
    SPECIAL={1: (0.92, 1.0), 19: (0.95, 1.0), 23: (0.95, 1.0), 24: (0.95, 1.0), 13: (1.0, 1.0), 22: (1.0, 1.0), 3: (1.02, 1.0)},  # line: (speed, tempo)
    LEAD_S=0.30,          # silence before the first line
    TEXT_FIXES={'once-soft': 'once soft'},   # Kokoro ran the hyphenated pair together
)
if len(sys.argv) == 5:
    SETTINGS.update(KSPEED=float(sys.argv[1]), TEMPO=float(sys.argv[2]), PAUSE_SCALE=float(sys.argv[3]), SEMI=float(sys.argv[4]))
# ----------------------------------------------------------------


def kokoro():
    from kokoro_onnx import Kokoro
    here = os.path.dirname(os.path.abspath(__file__))
    for d in (os.environ.get('KOKORO_DIR', ''), os.path.join(here, '..', 'wildlore-narrator', 'models'), '/home/claude/models/kokoro'):
        if d and os.path.exists(os.path.join(d, 'kokoro-v1.0.onnx')):
            return Kokoro(os.path.join(d, 'kokoro-v1.0.onnx'), os.path.join(d, 'voices-v1.0.bin'))
    raise SystemExit('Kokoro model not found: run ../wildlore-narrator/get_models.py (or set KOKORO_DIR)')


def trim(a, sr):
    env = np.sqrt(np.convolve(a ** 2, np.ones(240) / 240, 'same'))
    idx = np.where(env > env.max() * 10 ** (-48 / 20))[0]
    return a[max(0, idx[0] - int(0.04 * sr)): idx[-1] + int(0.07 * sr)]


def rb(a, sr, tempo, semi):
    with tempfile.TemporaryDirectory() as td:
        sf.write(td + '/i.wav', a, sr, subtype='FLOAT')
        subprocess.run(['rubberband', '-3', '-q', '-F', '-T', str(tempo), '-p', str(semi), td + '/i.wav', td + '/o.wav'], check=True, capture_output=True)
        o, _ = sf.read(td + '/o.wav', dtype='float32')
    return o


def main():
    S = SETTINGS
    k = kokoro()
    st = sum(w * k.get_voice_style(v) for v, w in S['BLEND'].items())
    segs = []
    for i, (t, p) in enumerate(LINES):
        ks, tp = S['SPECIAL'].get(i, (S['KSPEED'], S['TEMPO']))
        txt = t
        for a_, b_ in S['TEXT_FIXES'].items():
            txt = txt.replace(a_, b_)
        a, sr = k.create(txt, voice=st, speed=ks, lang=S['LANG'])
        a = np.concatenate([np.zeros(int(0.1 * sr), np.float32), a.astype(np.float32), np.zeros(int(0.1 * sr), np.float32)])
        a = rb(a, sr, tp, S['SEMI'])
        a = trim(a, sr)
        fi, fo = int(0.012 * sr), int(0.035 * sr)
        a[:fi] *= np.linspace(0, 1, fi); a[-fo:] *= np.linspace(1, 0, fo)
        segs.append((a, p * S['PAUSE_SCALE'], t, ks * tp))
    out = [np.zeros(int(S['LEAD_S'] * sr), np.float32)]
    timings = []; cur = S['LEAD_S']
    for a, p, t, sp in segs:
        timings.append({"text": t, "start": round(cur, 3), "end": round(cur + len(a) / sr, 3), "eff_speed": round(sp, 3)})
        out.append(a); cur += len(a) / sr
        out.append(np.zeros(int(p * sr), np.float32)); cur += p
    y = np.concatenate(out)
    y = sosfilt(butter(2, 70, 'highpass', fs=sr, output='sos'), y)
    y = y / (np.max(np.abs(y)) + 1e-9) * 0.89
    sf.write(ep_paths.AUDIO + 'narration_raw.wav', y.astype(np.float32), sr, subtype='FLOAT')
    json.dump(timings, open(ep_paths.AUDIO + 'timings.json', 'w'), indent=1)
    print("total narration length:", round(len(y) / sr, 2), "s ->", ep_paths.AUDIO)


if __name__ == '__main__':
    main()
