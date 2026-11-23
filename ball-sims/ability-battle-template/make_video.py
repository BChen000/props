#!/usr/bin/env python3
"""make_video: one command from settings.py to a finished POWER BALLS Short (out/power_balls.mp4).

    python make_video.py                       # SEED from settings.py, 2 parallel render jobs
    python make_video.py --seed 4512 --jobs 4 --out out/yellow_wins.mp4

Steps: timeline (sim + video clock) -> render frame chunks in parallel (H.264, CRF 18) -> join without
re-encoding -> synthesize audio -> mux with two-pass loudnorm to -14 LUFS / -1.5 dBTP (AAC 192k).
Needs ffmpeg with libx264 on PATH. About a minute on 2 cores for the 52 s video.
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import settings as S

HERE = Path(__file__).resolve().parent


def _opt(args, name, default, cast=str):
    return cast(args[args.index(name) + 1]) if name in args else default


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        sys.exit(f'failed: {" ".join(map(str, cmd))}\n{r.stderr[-1500:]}')
    return r


def main():
    args = sys.argv[1:]
    seed = _opt(args, '--seed', S.SEED, int)
    jobs = _opt(args, '--jobs', 2, int)
    out_dir = HERE / 'out'
    final = Path(_opt(args, '--out', str(out_dir / 'power_balls.mp4')))
    out_dir.mkdir(exist_ok=True)
    final.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    import render
    D = render.Director(seed)
    tl_path = out_dir / 'timeline.json'
    T = render.timeline(D, tl_path)
    total = T['total']
    print(f'seed {seed}: {S.NAMES[D.winner]} wins, {total} frames ({total / S.FPS:.1f} s)')

    step = -(-total // jobs)
    chunks = []
    procs = []
    for j in range(jobs):
        k0, k1 = j * step, min(total, (j + 1) * step)
        if k0 >= k1:
            break
        path = out_dir / f'chunk_{j}.mp4'
        chunks.append(path)
        procs.append(subprocess.Popen([sys.executable, str(HERE / 'render.py'), 'chunk', str(k0), str(k1), str(path),
                                       '--seed', str(seed)], cwd=HERE))
    for p in procs:
        if p.wait() != 0:
            sys.exit('a render chunk failed')
    print(f'rendered {len(chunks)} chunks in {time.time() - t0:.0f}s')

    lst = out_dir / 'chunks.txt'
    lst.write_text(''.join(f"file '{c.name}'\n" for c in chunks))
    silent = out_dir / 'video_noaudio.mp4'
    run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(lst), '-c', 'copy', str(silent)])

    import audio
    wav = out_dir / 'audio.wav'
    audio.write(wav, audio.build(T))
    print(f'audio done at {time.time() - t0:.0f}s')

    target = f'I={S.LOUDNESS}:TP={S.TRUE_PEAK}:LRA=11'
    r = run(['ffmpeg', '-hide_banner', '-i', str(wav), '-af', f'loudnorm={target}:print_format=json', '-f', 'null', '-'])
    m = json.loads(re.search(r'\{[^{}]*"input_i"[^{}]*\}', r.stderr, re.S).group(0))
    af = (f"loudnorm={target}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
          f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true:print_format=summary")
    tmp = final.with_name(final.stem + '.part.mp4')
    run(['ffmpeg', '-v', 'error', '-y', '-i', str(silent), '-i', str(wav), '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
         '-af', af, '-ar', str(S.SR), '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', str(tmp)])
    os.replace(tmp, final)
    if '--keep' not in args:
        for c in chunks + [lst, silent]:
            c.unlink(missing_ok=True)
    print(f'wrote {final} in {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
