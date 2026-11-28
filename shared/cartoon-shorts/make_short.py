"""Builds one motivational Short from episodes/<name>.py, in either style.

  python make_short.py five_more_minutes                -> build/five_more_minutes/five_more_minutes.mp4 + thumb.png
  python make_short.py five_more_minutes --style stick  -> build/five_more_minutes_stick/... (stick figures)
  python make_short.py five_more_minutes --stills       -> build/<name>/stills.png, one frame per scene
  python make_short.py five_more_minutes --frames 3,9.5 -> full-size frames
  python make_short.py five_more_minutes --only 2,5     -> re-render those scenes (0-based), keep the rest
"""
import argparse
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'episodes'))
import motivation  # noqa: E402
import humanoid  # noqa: E402

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('episode')
    ap.add_argument('--style', default='lit', choices=['lit', 'stick'])
    ap.add_argument('--stills', action='store_true')
    ap.add_argument('--frames', default=None)
    ap.add_argument('--only', default=None)
    a = ap.parse_args()
    humanoid.use_style(a.style)
    motivation.OUT_TAG[0] = '' if a.style == 'lit' else '_' + a.style
    ep = importlib.import_module(a.episode)
    motivation.build(ep, stills=a.stills, frames=[float(v) for v in a.frames.split(',')] if a.frames else None,
                     only=[int(k) for k in a.only.split(',')] if a.only else None)
