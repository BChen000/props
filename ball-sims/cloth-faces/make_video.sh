#!/bin/bash
# End to end: sky -> sims -> plates -> timeline -> frames -> counter + sound -> mp4 + thumbnail.
# Usage:  HERO=duck PY=python3 ./make_video.sh        (PY must have bpy 5.3.0; ~2.5 h on 2 cores)
set -e
cd "$(dirname "$0")"
PY=${PY:-python3}
export HERO=${HERO:-duck}
$PY sky.py
$PY run_sims.py
$PY plates.py -- base 256
$PY plates.py -- stack 96 0,1,2,3,4,5
$PY build_timeline.py
$PY run_render.py
N=$($PY -c "import json,settings as C;print(json.load(open(C.TIMELINE))['total'])")
$PY overlay.py build/timeline.json build/frames build/final 0 $N
$PY audio.py
ffmpeg -v error -y -framerate 30 -i build/final/f_%04d.png -i build/out/audio.wav -c:v libx264 -preset slow -crf 16 \
  -pix_fmt yuv420p -profile:v high -c:a aac -b:a 192k -ar 48000 -movflags +faststart -shortest build/out/short_$HERO.mp4
$PY thumb.py
echo "done: build/out/short_$HERO.mp4 and build/out/thumb_raw.png"
