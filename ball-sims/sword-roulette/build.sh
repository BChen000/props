#!/usr/bin/env bash
# Render the whole Short: 4 video chunks in parallel (2 at a time), concat, add the soundtrack
# normalised to -14 LUFS (battle_audio.loudnorm_filter, two-pass, linear).
# Output goes to out/ (do not commit it). Usage:  bash build.sh
set -e
cd "$(dirname "$0")"
mkdir -p out
N=$(python3 -c "import timeline as T; print(T.Timeline().n_frames)")
B1=$((N / 4)); B2=$((N / 2)); B3=$((3 * N / 4))
echo "frames: $N"
python3 render.py range 0 $B1 out/s1.mp4 &
python3 render.py range $B1 $B2 out/s2.mp4 &
wait
python3 render.py range $B2 $B3 out/s3.mp4 &
python3 render.py range $B3 $N out/s4.mp4 &
wait
printf "file 's1.mp4'\nfile 's2.mp4'\nfile 's3.mp4'\nfile 's4.mp4'\n" > out/list.txt
ffmpeg -v error -y -f concat -safe 0 -i out/list.txt -c copy out/video_only.mp4
python3 audio.py out/audio.wav
AF=$(python3 -c "import sys; sys.path.append('../battle-audio'); import battle_audio as ba, settings as S; print(ba.loudnorm_filter('out/audio.wav', *S.LOUDNESS))")
ffmpeg -v error -y -i out/video_only.mp4 -i out/audio.wav -map 0:v -map 1:a -c:v copy -af "$AF" -ar 48000 -c:a aac -b:a 192k \
  -shortest -movflags +faststart out/sword_roulette.part.mp4
mv out/sword_roulette.part.mp4 out/sword_roulette.mp4
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,r_frame_rate -of compact out/sword_roulette.mp4
