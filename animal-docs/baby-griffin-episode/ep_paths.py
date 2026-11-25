"""Paths for the Baby Griffin episode. Every other module imports this first.

EP_BUILD (env) is the work folder, default build/ next to this file:
  build/shots/<shot>/   renders (plate.png, base.png, fg/NNNN.png, meta.json), via ../crop-plate-renderer/drv.py
  build/out/<shot>.mp4  composited shots (assemble.py)
  build/audio/          narration_raw.wav, timings.json, final_mix.wav (tts.py, audio_mix.py)
  build/queue/          render queue state (queue.txt, done.txt, logs)
"""
import os, sys

EP = os.path.dirname(os.path.abspath(__file__))
PROPS = os.path.dirname(EP)
BUILD = os.path.join(os.environ.get('EP_BUILD', os.path.join(EP, 'build')), '')
SHOTS = os.path.join(BUILD, 'shots', '')
OUT = os.path.join(BUILD, 'out', '')
AUDIO = os.path.join(BUILD, 'audio', '')
for _d in (SHOTS, OUT, AUDIO):
    os.makedirs(_d, exist_ok=True)
os.environ.setdefault('CPR_SHOTS', SHOTS)          # read by drv.py and comp.py at import
for _p in (os.path.join(PROPS, 'crop-plate-renderer'), os.path.join(PROPS, 'cliff-nest-set'), os.path.join(PROPS, 'griffin'), EP):
    if _p not in sys.path:
        sys.path.insert(0, _p)
