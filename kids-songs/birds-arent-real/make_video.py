"""Birds Aren't Real Short: narration timeline -> 3D frames (lowpoly-gl) -> captions -> one mp4 per scene -> join + mix.

  python3 make_video.py narrate                   # the narrator speaks story.py -> build/voice/narration.wav + timeline.json
  python3 make_video.py stills 1.0 12.5 30        # full-size stills at those times -> build/stills/*.png + sheet
  python3 make_video.py render [scene ...]        # render scene files (all, or only the named scenes / indices)
  python3 make_audio.py                           # narration with the tail, music, sfx -> build/mix.wav
  python3 make_video.py final                     # join scenes + mix -> build/birds_arent_real.mp4 (BT.709, tagged)
  python3 make_video.py all                       # narrate, audio, render, final (assets: python3 build_all.py first)
  python3 make_video.py preview [video.mp4]       # redraws preview.png from the finished video
"""
import json
import math
import os
import subprocess
import sys
import time

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paths  # noqa: F401  (sibling props on sys.path)

# ------------------------------------------------------------------ settings
W, H, FPS = 1080, 1920, 30
BUILD = os.path.join(HERE, 'build')
VOICE = os.path.join(BUILD, 'voice')
GLITCH_PAUSE = 0.0            # extra silence before the last line (Dead Internet's head glitch used 0.9)
TAIL_EXTRA = 1.6              # extra silence after the last line, for the pigeon landing
REMAP = {23: 'satire', 24: 'satire', 25: 'satire'}   # line index -> scene
CUT_DIP = 0.12                # dip from black at each cut, seconds
END_FADE = 0.7
X264 = ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p']
FINAL_CRF = 21                # upload file; film grain makes CRF 18 about 180 MB


def timeline():
    tl = json.load(open(os.path.join(VOICE, 'timeline.json')))
    last = tl['lines'][-1]
    for ln in tl['lines']:
        if ln['i'] in REMAP:
            ln['scene'] = REMAP[ln['i']]
    last['start'] += GLITCH_PAUSE; last['end'] += GLITCH_PAUSE
    tl['duration'] += GLITCH_PAUSE + TAIL_EXTRA
    return tl


def narration_with_pause():
    a, sr = sf.read(os.path.join(VOICE, 'narration.wav'))
    tl = json.load(open(os.path.join(VOICE, 'timeline.json')))
    prev, last = tl['lines'][-2], tl['lines'][-1]
    cut = int(((prev['end'] + last['start']) / 2) * sr)
    pad = np.zeros((int(GLITCH_PAUSE * sr),) + a.shape[1:])
    out = np.concatenate([a[:cut], pad, a[cut:], np.zeros((int(TAIL_EXTRA * sr),) + a.shape[1:])])
    path = os.path.join(BUILD, 'narration_paused.wav')
    sf.write(path, out, sr)
    return path, out, sr


def speech_env(audio, sr, n_frames):
    if audio.ndim > 1:
        audio = audio.mean(1)
    hop = sr // FPS
    rms = np.array([np.sqrt(np.mean(audio[i * hop:(i + 1) * hop] ** 2)) if i * hop < len(audio) else 0 for i in range(n_frames)])
    rms /= max(np.percentile(rms, 95), 1e-6)
    k = lambda x, n: np.convolve(x, np.ones(n) / n, mode='same')
    fast, slow = k(rms, 3), k(rms, 15)
    return np.clip((fast - slow) * 2.2, 0, 1)


class Ctx:
    def __init__(self, sp):
        self.T = [ln['start'] - sp['start'] for ln in sp['lines']]
        self.E = [ln['end'] - sp['start'] for ln in sp['lines']]
        self.dur = sp['end'] - sp['start']


def setup():
    import meshkit
    from PIL import Image
    from glr import Renderer
    import shots
    parts = meshkit.load(os.path.join(BUILD, 'assets.npz'))
    R = Renderer(W, H)
    R.add_meshes(parts)
    texwh = {}
    for fn in os.listdir(os.path.join(BUILD, 'tex')):
        name = fn[:-4]
        im = np.asarray(Image.open(os.path.join(BUILD, 'tex', fn)).convert('RGB'))
        R.add_texture(name, im)
        texwh[name] = (im.shape[1], im.shape[0])
    tl = timeline()
    _, audio, sr = narration_with_pause()
    n = int(math.ceil(tl['duration'] * FPS))
    shots.GLOBAL.update(R=R, parts=parts, texwh=texwh, env=speech_env(audio, sr, n))
    return R, tl


def frame(R, tl, spans, t, skia_state):
    import shots, post
    from storytime_kit import caption, active_line
    sp = [s for s in spans if s['start'] <= t < s['end']] or [spans[-1]]
    sp = sp[0]
    sc = shots.SCENES[sp['scene']]
    lt = t - sp['start']
    fd = sc['fn'](lt, Ctx(sp), t)
    img = R.render(fd['items'], fd['cam'], fd['lights'], fd['env'], fd.get('adds', []))
    p = dict(fd.get('post', {}))
    fade = 1.0
    if sp['start'] > 0 and lt < CUT_DIP:
        fade = min(fade, 0.25 + 0.75 * lt / CUT_DIP)
    tail = tl['duration'] - t
    if tail < END_FADE:
        fade = min(fade, max(tail / END_FADE, 0.0))
    p['fade'] = fade
    out = post.finish(img, p, int(round(t * FPS)))
    arr, surf = skia_state
    arr[..., :3] = out; arr[..., 3] = 255
    ln = active_line(tl['lines'], t)
    if ln is not None and t < tl['duration'] - 0.6:
        caption(surf.getCanvas(), ln['text'], sc.get('cap_y', 1420), t - ln['start'] + 0.05)
    return arr


def spans_of(tl):
    from storytime_kit import scene_spans
    return scene_spans(tl)


def stills(times):
    import skia
    from PIL import Image
    R, tl = setup()
    spans = spans_of(tl)
    os.makedirs(os.path.join(BUILD, 'stills'), exist_ok=True)
    arr = np.zeros((H, W, 4), np.uint8); surf = skia.Surface(arr)
    ims = []
    for t in times:
        t0 = time.time()
        a = frame(R, tl, spans, t, (arr, surf))
        im = Image.fromarray(a[..., :3].copy())
        im.save(os.path.join(BUILD, 'stills', f'{t:06.2f}.png'))
        ims.append(im)
        print(f'{t:6.2f}s  {time.time() - t0:.2f}s/frame')
    cols = min(len(ims), 5)
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * 324, rows * 576), (20, 20, 24))
    for i, im in enumerate(ims):
        sheet.paste(im.resize((324, 576), Image.LANCZOS), ((i % cols) * 324, (i // cols) * 576))
    sheet.save(os.path.join(BUILD, 'stills_sheet.png'))


def render(only=None):
    import skia
    R, tl = setup()
    spans = spans_of(tl)
    out_dir = os.path.join(BUILD, 'scenes'); os.makedirs(out_dir, exist_ok=True)
    arr = np.zeros((H, W, 4), np.uint8); surf = skia.Surface(arr)
    files = []
    for k, sp in enumerate(spans):
        f0, f1 = int(round(sp['start'] * FPS)), int(round(sp['end'] * FPS))
        fn = os.path.join(out_dir, f's{k:02d}.mp4'); files.append(fn)
        if only and sp['scene'] not in only and str(k) not in only:
            continue
        if not only and os.path.exists(fn):
            continue
        tmp = os.path.join(out_dir, f's{k:02d}.tmp.mp4')
        cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-'] + X264 + [tmp]
        pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        t0 = time.time()
        for f in range(f0, f1):
            a = frame(R, tl, spans, f / FPS, (arr, surf))
            pr.stdin.write(a.tobytes())
        pr.stdin.close()
        if pr.wait() == 0:
            os.replace(tmp, fn)
        print(f'scene {k:2d} {sp["scene"]:8s} {f1 - f0:4d} frames  {time.time() - t0:6.1f}s', flush=True)
    with open(os.path.join(out_dir, 'list.txt'), 'w') as fh:
        for fn in files:
            fh.write(f"file '{os.path.basename(fn)}'\n")


def preview(video=None):
    """preview.png (720x1280): one frame from the middle of each scene of the finished video, plus the glitch peak."""
    from PIL import Image
    video = video or os.path.join(BUILD, 'birds_arent_real.mp4')
    tl = timeline()
    ts = [(s['start'] + s['end']) / 2 for s in spans_of(tl)] + [tl['duration'] - 2.0, tl['duration'] - 1.2]
    sheet = Image.new('RGB', (720, 1280), (14, 14, 18))
    for i, t in enumerate(ts[:16]):
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.3f}', '-i', video, '-frames:v', '1', '-f', 'rawvideo',
                              '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
        im = Image.frombuffer('RGB', (W, H), raw).resize((180, 320), Image.LANCZOS)
        sheet.paste(im, ((i % 4) * 180, (i // 4) * 320))
    sheet.save(os.path.join(HERE, 'preview.png'), optimize=True)
    print('wrote preview.png')


def narrate_story():
    from narrate import narrate
    import story
    os.makedirs(VOICE, exist_ok=True)
    return narrate(story.STORY, VOICE)


def final(name='birds_arent_real'):
    """Join the scene files, add the mix, and convert the untagged BT.601 picture to tagged BT.709 for YouTube."""
    sc = os.path.join(BUILD, 'scenes')
    joined = os.path.join(sc, 'joined.mp4')
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', os.path.join(sc, 'list.txt'),
                    '-c', 'copy', joined], check=True)
    out = os.path.join(BUILD, name + '.mp4')
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', joined, '-i', os.path.join(BUILD, 'mix.wav'), '-map', '0:v', '-map', '1:a',
                    '-vf', 'scale=in_color_matrix=bt601:out_color_matrix=bt709:in_range=tv:out_range=tv,format=yuv420p',
                    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', str(FINAL_CRF), '-profile:v', 'high', '-level', '4.2',
                    '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
                    '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-shortest', '-movflags', '+faststart', out], check=True)
    print('wrote', out)
    return out


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'render'
    if cmd == 'stills':
        stills([float(v) for v in sys.argv[2:]])
    elif cmd == 'render':
        render(sys.argv[2:] or None)
    elif cmd == 'final':
        final()
    elif cmd == 'narrate':
        narrate_story()
    elif cmd == 'preview':
        preview(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == 'all':
        if not os.path.exists(os.path.join(VOICE, 'timeline.json')):
            narrate_story()
        subprocess.run([sys.executable, os.path.join(HERE, 'make_audio.py')], check=True)
        render()
        final()
