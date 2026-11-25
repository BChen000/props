"""Builds this episode from scratch: narration -> soundtrack -> picture -> one mp4 (1080x1920, 30 fps, AAC 192k).

  python build.py                 -> out/<name>.mp4, plus out/narration.wav, timeline.json, mix.wav, scenes/
  python build.py --stills        -> out/stills.png, one frame per scene (needs only the narration; no encoding)
  python build.py --frames 2,31.5 -> out/frame_2.00.png, out/frame_31.50.png at full size
  python build.py --only 4,9      -> re-render scenes 4 and 9 (0-based, in screen order), keep the rest, re-join
  python build.py --audio-only    -> narration and mix, no picture
Set STORYTIME_OUT to write somewhere other than out/. Spoken lines are cached in out/lines/, so a rebuild after
editing a few captions only re-speaks those lines.
"""
import argparse
import importlib.util
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
for p in ('storytime-kit', 'storytime-narrator', 'storytime-music'):
    sys.path.insert(0, os.path.join(HERE, '..', p))
import music  # noqa: E402
import narrate  # noqa: E402
import storytime_kit as kit  # noqa: E402

OUT = os.environ.get('STORYTIME_OUT', os.path.join(HERE, 'out'))


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + '.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--stills', action='store_true')
    ap.add_argument('--frames', default=None)
    ap.add_argument('--only', default=None)
    ap.add_argument('--audio-only', action='store_true')
    a = ap.parse_args()
    t0 = time.time()
    story = load('story')
    os.makedirs(OUT, exist_ok=True)
    tl = narrate.narrate(story.STORY, OUT)
    if a.stills or a.frames:
        scenes = load('scenes').SCENES
        if a.stills:
            title = [story.TITLE, f'{tl["duration"]:.1f} s, {len(kit.scene_spans(tl))} scenes, {len(tl["lines"])} lines',
                     'Story Time with Kenji', 'one frame from the middle of each scene']
            print('wrote', kit.contact_sheet(tl, scenes, os.path.join(OUT, 'stills.png'), title=title))
        if a.frames:
            from PIL import Image
            ts = [float(x) for x in a.frames.split(',')]
            for t, f in zip(ts, kit.render(tl, scenes, None, frames_at=ts)):
                p = os.path.join(OUT, f'frame_{t:.2f}.png')
                Image.fromarray(f).save(p)
                print('wrote', p)
        return
    mix = music.mix(os.path.join(OUT, 'narration.wav'), tl, os.path.join(OUT, 'mix.wav'), events=story.EVENTS, **story.MUSIC)
    if a.audio_only:
        return
    scenes = load('scenes').SCENES
    only = [int(k) for k in a.only.split(',')] if a.only else None
    kit.render(tl, scenes, os.path.join(OUT, 'scenes'), only=only)
    mp4 = kit.concat_and_mux(os.path.join(OUT, 'scenes'), mix, os.path.join(OUT, story.STORY['name'] + '.mp4'))
    print('DONE', mp4, f'{tl["duration"]:.2f} s video in {time.time() - t0:.0f} s')


if __name__ == '__main__':
    main()
