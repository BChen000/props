"""Speech-recognition check of the narration against the script, line by line (Whisper base.en via sherpa-onnx).
  python3 asr_check.py                                  build/audio/narration_raw.wav + build/audio/timings.json
  python3 asr_check.py build/audio/final_mix.wav        the same over the finished mix
Model: ASR_DIR, or models/sherpa-onnx-whisper-base.en (python3 get_asr_model.py).
"""
import sherpa_onnx, soundfile as sf, numpy as np, json, re, sys, os, librosa
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ep_paths
d = os.path.join(os.environ.get('ASR_DIR', os.path.join(ep_paths.EP, 'models', 'sherpa-onnx-whisper-base.en')), '')
rec = sherpa_onnx.OfflineRecognizer.from_whisper(encoder=d+'base.en-encoder.onnx', decoder=d+'base.en-decoder.onnx', tokens=d+'base.en-tokens.txt', num_threads=2)
wav = sys.argv[1] if len(sys.argv) > 1 else ep_paths.AUDIO + 'narration_raw.wav'
tim = json.load(open(sys.argv[2] if len(sys.argv) > 2 else ep_paths.AUDIO + 'timings.json'))
y, sr = sf.read(wav, dtype='float32')
if y.ndim>1: y=y.mean(1)
if sr!=16000: y = librosa.resample(y, orig_sr=sr, target_sr=16000); sr=16000
norm = lambda s: re.sub(r"[^a-z' ]"," ",s.lower().replace('-',' ')).split()
import difflib
bad=0
for i,t in enumerate(tim):
    a = y[int((t['start']-0.05)*sr):int((t['end']+0.1)*sr)]
    s = rec.create_stream(); s.accept_waveform(sr, a); rec.decode_stream(s)
    hyp = s.result.text.strip()
    r, h = norm(t['text']), norm(hyp)
    sm = difflib.SequenceMatcher(None, r, h)
    diffs = [(r[i1:i2], h[j1:j2]) for op,i1,i2,j1,j2 in sm.get_opcodes() if op!='equal']
    flag = 'OK ' if not diffs else 'DIFF'
    if diffs: bad+=1
    print(f"{flag} [{i}] {hyp}" + (f"   <-- {diffs}" if diffs else ""))
print("lines with differences:", bad)
