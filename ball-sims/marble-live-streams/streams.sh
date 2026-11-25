#!/bin/bash
# Runs the three marble streams at once and stops each one after 11 hours.
#
# 1. Put this file in the same folder as loop.mp4, mix.m4a, marble_music.mp4 and ring_escape.mp4.
# 2. In Terminal:  cd <that folder>  then  bash streams.sh
# 3. Paste the three stream keys when it asks (one per scheduled stream, each with Auto-start ON and Auto-stop ON).
#    Or paste them below instead of paste-key-...-here, and it won't ask.
# Keep the Terminal window open and the Mac plugged in with the lid open. Ctrl+C stops all three early.

KEY_SPIRAL="paste-key-1-here"        # loop.mp4 + mix.m4a
KEY_MUSIC="paste-key-2-here"         # marble_music.mp4
KEY_RING="paste-key-3-here"          # ring_escape.mp4
HOURS=11

DURATION=${DURATION:-$((HOURS * 3600))}
URL=${URL:-rtmp://a.rtmp.youtube.com/live2}

cd "$(dirname "$0")" || exit 1
for f in loop.mp4 mix.m4a marble_music.mp4 ring_escape.mp4; do
  [ -f "$f" ] || { echo "Missing $f in $(pwd). Rename any loop-2.mp4-style downloads to the exact names."; exit 1; }
done
case "$KEY_SPIRAL" in *paste*|"") read -r -p "Stream key for the spiral stream (loop.mp4): " KEY_SPIRAL;; esac
case "$KEY_MUSIC" in *paste*|"") read -r -p "Stream key for the music stream (marble_music.mp4): " KEY_MUSIC;; esac
case "$KEY_RING" in *paste*|"") read -r -p "Stream key for the ring stream (ring_escape.mp4): " KEY_RING;; esac
KEY_SPIRAL=$(printf %s "$KEY_SPIRAL" | tr -d '[:space:]')
KEY_MUSIC=$(printf %s "$KEY_MUSIC" | tr -d '[:space:]')
KEY_RING=$(printf %s "$KEY_RING" | tr -d '[:space:]')
for k in "$KEY_SPIRAL" "$KEY_MUSIC" "$KEY_RING"; do
  case "$k" in *paste*|"") echo "A stream key is missing. Run bash streams.sh again and paste all three."; exit 1;; esac
done
if [ "$KEY_SPIRAL" = "$KEY_MUSIC" ] || [ "$KEY_SPIRAL" = "$KEY_RING" ] || [ "$KEY_MUSIC" = "$KEY_RING" ]; then
  echo "Each stream needs its own key (Live Control Room -> key dropdown -> Create new stream key)."; exit 1
fi

END=$(( $(date +%s) + DURATION ))
clock() { date -r "$1" +%H:%M 2>/dev/null || date -d "@$1" +%H:%M; }

stream() {  # name key video [audio]
  local name=$1 key=$2 video=$3 audio=$4 left
  while true; do
    left=$(( END - $(date +%s) ))
    [ "$left" -le 20 ] && break
    if [ -n "$audio" ]; then
      ffmpeg -nostdin -hide_banner -loglevel error -re -stream_loop -1 -i "$video" -stream_loop -1 -i "$audio" \
        -map 0:v -map 1:a -c:v copy -c:a aac -b:a 128k -ar 44100 -t "$left" -f flv "$URL/$key"
    else
      ffmpeg -nostdin -hide_banner -loglevel error -re -stream_loop -1 -i "$video" \
        -map 0:v -map 0:a -c:v copy -c:a aac -b:a 128k -ar 44100 -t "$left" -f flv "$URL/$key"
    fi
    left=$(( END - $(date +%s) ))
    [ "$left" -le 20 ] && break
    echo "$(date +%H:%M:%S) $name: connection dropped, reconnecting in 5 s"
    sleep 5
  done
  echo "$(date +%H:%M:%S) $name: done"
}

trap 'trap - INT TERM; echo; echo "Stopping all streams..."; kill 0; exit 130' INT TERM
caffeinate -i -w $$ 2>/dev/null &

stream "spiral" "$KEY_SPIRAL" loop.mp4 mix.m4a &
stream "music " "$KEY_MUSIC" marble_music.mp4 &
stream "ring  " "$KEY_RING" ring_escape.mp4 &

echo "3 streams started at $(clock "$(date +%s)"). They stop by themselves at $(clock "$END")."
echo "Keep this window open. Ctrl+C stops all three early."
wait
echo "All three streams finished at $(clock "$(date +%s)")."
