#!/bin/bash
# Runs several marble streams at once and stops each one after 11 hours.
#
# 1. Put this file in the same folder as the stream files listed in STREAMS below.
# 2. In Terminal:  cd <that folder>  then  bash streams.sh
# 3. Paste one stream key per line, in the order of STREAMS, when it asks (one scheduled stream per key, each with
#    Auto-start ON and Auto-stop ON). Or put the keys in the table instead of paste-key-here, and it won't ask.
# Keep the Terminal window open and the Mac plugged in with the lid open. Ctrl+C stops them all early.

# name     video file                    sound (- = the video's own)   key
STREAMS="
spiral     loop.mp4                      mix.m4a                       paste-key-here
stairs     marble_lullaby_stairs.mp4     -                             paste-key-here
twin       marble_twin_stairs_loop.mp4   -                             paste-key-here
"
HOURS=11

DURATION=${DURATION:-$((HOURS * 3600))}
URL=${URL:-rtmp://a.rtmp.youtube.com/live2}

cd "$(dirname "$0")" || exit 1
names=(); videos=(); sounds=(); keys=()
while read -r n v s k; do
  [ -z "$n" ] && continue
  names+=("$n"); videos+=("$v"); sounds+=("$s"); keys+=("$k")
done <<EOF
$STREAMS
EOF
N=${#names[@]}

i=0
while [ $i -lt $N ]; do
  for f in "${videos[$i]}" "${sounds[$i]}"; do
    [ "$f" = "-" ] && continue
    [ -f "$f" ] || { echo "Missing $f in $(pwd). Rename any loop-2.mp4-style downloads to the exact names."; exit 1; }
  done
  i=$((i + 1))
done

i=0
while [ $i -lt $N ]; do
  case "${keys[$i]}" in
    *paste*|"") read -r -p "Stream key for ${names[$i]} (${videos[$i]}): " k; keys[$i]=$(printf %s "$k" | tr -d '[:space:]');;
  esac
  case "${keys[$i]}" in *paste*|"") echo "A stream key is missing. Run bash streams.sh again and paste all $N."; exit 1;; esac
  j=0
  while [ $j -lt $i ]; do
    if [ "${keys[$j]}" = "${keys[$i]}" ]; then
      echo "Each stream needs its own key (Live Control Room -> key dropdown -> Create new stream key)."; exit 1
    fi
    j=$((j + 1))
  done
  i=$((i + 1))
done

END=$(( $(date +%s) + DURATION ))
clock() { date -r "$1" +%H:%M 2>/dev/null || date -d "@$1" +%H:%M; }

stream() {  # name key video sound
  local name=$1 key=$2 video=$3 sound=$4 left
  while true; do
    left=$(( END - $(date +%s) ))
    [ "$left" -le 20 ] && break
    if [ "$sound" != "-" ]; then
      ffmpeg -nostdin -hide_banner -loglevel error -re -stream_loop -1 -i "$video" -stream_loop -1 -i "$sound" \
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

i=0
while [ $i -lt $N ]; do
  stream "${names[$i]}" "${keys[$i]}" "${videos[$i]}" "${sounds[$i]}" &
  i=$((i + 1))
done

echo "$N streams started at $(clock "$(date +%s)"). They stop by themselves at $(clock "$END")."
echo "Keep this window open. Ctrl+C stops them all early."
wait
echo "All $N streams finished at $(clock "$(date +%s)")."
