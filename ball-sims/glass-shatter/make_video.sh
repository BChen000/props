#!/bin/bash
# End to end: sims -> plate -> timeline -> frames -> counter + sound -> mp4 + thumbnail.
# Usage:  PY=python3 ./make_video.sh        (PY must have bpy 5.3.0 and pybullet; ~2 h on 2 cores)
set -e
cd "$(dirname "$0")"
PY=${PY:-python3}
$PY run_sims.py
$PY plates.py 96
$PY build_timeline.py
$PY run_render.py
N=$($PY -c "import json,settings as C;print(json.load(open(C.TIMELINE))['total'])")
$PY overlay.py build/timeline.json build/frames build/final 0 $N
$PY audio.py
ffmpeg -v error -y -framerate 30 -i build/final/f_%04d.png -i build/out/audio.wav -c:v libx264 -preset slow -crf 16 \
  -pix_fmt yuv420p -profile:v high -c:a aac -b:a 192k -ar 48000 -movflags +faststart -shortest build/out/short.mp4
$PY thumb.py
echo "done: build/out/short.mp4 and build/out/thumbnail.jpg"
