#!/bin/bash
# End to end: plan -> audio -> mood LUT -> Blender render (post encodes chunks alongside) -> mp4 -> thumbnail.
# Usage:  ./make_video.sh        (BLENDER must be Blender 4.0/4.1; ~1 h 45 min on 2 cores, mostly the render)
set -e
cd "$(dirname "$0")"
PY=${PY:-python3}
BLENDER=${BLENDER:-blender}
BUILD=$($PY -c "import settings;print(settings.BUILD)")
mkdir -p "$BUILD"
$PY export.py
$PY audio.py
$BLENDER -b --python mood_lut.py > "$BUILD/lut.log" 2>&1
$BLENDER -b --python scene.py -- full > "$BUILD/render.log" 2>&1 &
RENDER=$!
nice -n 19 $PY post.py watch
wait $RENDER
$PY post.py concat
$BLENDER -b "$BUILD/scene.blend" --python thumb_render.py > "$BUILD/thumb.log" 2>&1
$PY thumb.py
echo "done: $BUILD/out/short.mp4 and $BUILD/out/thumbnail.jpg"
