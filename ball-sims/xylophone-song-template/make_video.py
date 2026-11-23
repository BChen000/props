"""One command for a whole marble-xylophone Short: set -> plates -> drop schedule -> physics -> sound -> frames -> mp4 + thumbnail.

Run:  python3 make_video.py twinkle          (the Twinkle Twinkle video, no text)
      python3 make_video.py forty-marbles    (the 1, 2, 3, 4 ... 40 marbles video, with the counter)
Options: --frames 0:90 (render part of the video)   --force (redo every step)   --workers 2
Steps whose outputs already exist are skipped, so after the first run (about 20 min of Cycles plates)
a new song only costs the simulation and the frame render (about 8 min on 2 cores).
To make a new song: edit MELODY in ../marble-drop-sim/melody.py (or add an entry to VIDEOS below).
"""
import os, sys, argparse, subprocess, time, shutil
HERE = os.path.dirname(os.path.abspath(__file__))

# ======================================================================= SETTINGS
SET = os.path.join(HERE, '..', 'xylophone-ramp')
SIM = os.path.join(HERE, '..', 'marble-drop-sim')
COMP = os.path.join(HERE, '..', 'marble-plate-compositor')
SOUND = os.path.join(HERE, '..', 'glockenspiel-sounds')
COUNTER = os.path.join(HERE, '..', 'marble-counter')
THUMB = os.path.join(HERE, '..', 'thumbnail-title')
OUT_DIR = os.path.join(HERE, 'build')
PY = [sys.executable]                 # Python that has bpy 5.3.0, numpy, scipy, opencv, pillow, matplotlib
FPS = 30
VIDEOS = {
    'twinkle': dict(schedule='melody', duration=12.2, events='role', scale='major', counter=False,
                    split=262, thumb_t=9.5, thumb_preset='fifty-marbles'),
    'forty-marbles': dict(schedule='rounds', duration=12.6, events='physics', scale='pentatonic', counter=True,
                          split=290, thumb_t=9.3, thumb_preset='forty-marbles'),
}
# ===================================================================== END SETTINGS


def run(cmd, cwd=None):
    print('>>', ' '.join(os.path.basename(c) if os.path.isabs(c) else c for c in cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=cwd)


def need(path, force):
    return force or not os.path.exists(path)


def strip_preview(video, out, times=(0.3, 3.0, 8.9, 12.0), width=360):
    import numpy as np
    from PIL import Image
    tiles = []
    for t in times:
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', video, '-frames:v', '1', '-vf', f'scale={width}:-2',
                              '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
        h = len(raw) // (width * 3)
        tiles.append(np.frombuffer(raw, np.uint8).reshape(h, width, 3))
    Image.fromarray(np.concatenate(tiles, 1)).save(out)
    print('saved', out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('video', choices=list(VIDEOS))
    ap.add_argument('--frames', default=None, help='a:b frame range')
    ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    v = VIDEOS[a.video]
    os.makedirs(OUT_DIR, exist_ok=True)
    t0 = time.time()
    if need(os.path.join(SET, 'build', 'scene_meta.json'), a.force):
        run(PY + [os.path.join(SET, 'build_set.py')])
    plate = os.path.join(COMP, 'build', 'plate')
    if need(os.path.join(plate, 'beauty.npy'), a.force):
        run(PY + [os.path.join(COMP, 'render_plates.py'), 'all'])
    if need(os.path.join(COMP, 'build', 'probes_proc.npz'), a.force):
        run(PY + [os.path.join(COMP, 'probes.py')])
    sb = os.path.join(SIM, 'build')
    if v['schedule'] == 'melody':
        if need(os.path.join(sb, 'fall_calib.json'), a.force):
            run(PY + [os.path.join(SIM, 'calibrate.py')])
        run(PY + [os.path.join(SIM, 'melody.py')])
        cfg = os.path.join(sb, 'melody.json')
    else:
        run(PY + [os.path.join(SIM, 'rounds.py')])
        cfg = os.path.join(sb, 'rounds.json')
    simf = os.path.join(OUT_DIR, a.video + '_sim.npz')
    run(PY + [os.path.join(SIM, 'sim.py'), cfg, simf])
    run(PY + [os.path.join(SIM, 'check.py'), simf, cfg])
    evf = os.path.join(OUT_DIR, a.video + '_events.npz')
    run(PY + [os.path.join(SIM, 'events.py'), simf, cfg, evf, '--mode', v['events'], '--scale', v['scale']])
    wav = os.path.join(OUT_DIR, a.video + '.wav')
    run(PY + [os.path.join(SOUND, 'synth.py'), evf, wav, '--duration', str(v['duration'])])
    nfr = int(round(v['duration'] * FPS))
    f0, f1 = (int(x) for x in a.frames.split(':')) if a.frames else (0, nfr)
    cuts = [f0] + ([v['split']] if a.workers == 2 and f0 < v['split'] < f1 else
                   [f0 + (f1 - f0) * k // a.workers for k in range(1, a.workers)]) + [f1]
    procs, parts = [], []
    for k in range(len(cuts) - 1):
        part = os.path.join(OUT_DIR, f'{a.video}_part{k}.mp4')
        cmd = PY + [os.path.join(COMP, 'render_video.py'), simf, cfg, str(cuts[k]), str(cuts[k + 1]), part]
        if v['counter']:
            cmd += ['--overlay', os.path.join(COUNTER, 'counter.py')]
        print('>> frames', cuts[k], '->', cuts[k + 1], flush=True)
        procs.append(subprocess.Popen(cmd, stdout=subprocess.DEVNULL))
        parts.append(part)
    if any(p.wait() for p in procs):
        sys.exit('frame render failed')
    lst = os.path.join(OUT_DIR, a.video + '_parts.txt')
    with open(lst, 'w') as fh:
        fh.writelines(f"file '{os.path.basename(p)}'\n" for p in parts)
    silent = os.path.join(OUT_DIR, a.video + '_silent.mp4')
    run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', silent])
    final = os.path.join(OUT_DIR, a.video + '.mp4')
    tmp = final[:-4] + '.tmp.mp4'
    audio_args = ['-ss', str(f0 / FPS)] if f0 else []
    run(['ffmpeg', '-v', 'error', '-y', '-i', silent] + audio_args + ['-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
         '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', tmp])
    os.replace(tmp, final)
    for p in parts + [lst, silent]:
        os.remove(p)
    if not a.frames:
        frame = os.path.join(OUT_DIR, f'{a.video}_thumb_frame.png')
        run(PY + [os.path.join(COMP, 'render_frame.py'), simf, cfg, '--t', str(v['thumb_t']), '--ns', '16', '--out', frame])
        run(PY + [os.path.join(THUMB, 'make_thumbnail.py'), frame, os.path.join(OUT_DIR, a.video + '_thumbnail.jpg'),
                  '--preset', v['thumb_preset']])
        strip_preview(final, os.path.join(OUT_DIR, a.video + '_strip.png'))
    print('DONE', final, '%.0f s' % (time.time() - t0))


if __name__ == '__main__':
    main()
