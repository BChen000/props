# marble-live-streams

Three 16:9 YouTube livestreams built from finished marble Shorts, plus the script that runs all three at once from a Mac and ends each one after 11 hours. **Marble music** plays four marble-music Shorts with a "guess the song" card that turns into the title after 10 s. **Ring Escape** plays eight rounds with eight different winners and a round counter. **Spiral** puts the rounds, muted, in a window beside the `../marble-spiral-loop` music box. `compose.py` centres each portrait Short over a blurred fill of itself between two side panels, and encodes every file so it loops forever with `-c:v copy`.

![preview](preview.png)

**Used in:** made for GJ's three simultaneous Marble Pop livestreams (Nov 2026), streamed from his Mac with `streams.sh`. Verified in a 2-core cloud session:
- The three files: `marble_music.mp4` (156.13 s, 4,684 frames), `ring_escape.mp4` (209.87 s, 6,296 frames) and `loop.mp4` (216.00 s, 6,480 frames, no audio). All are 1920×1080 at 30 fps, with a keyframe exactly every 2 s. In the two files with audio, audio and video lengths match to 1 ms.
- Looped through the ffmpeg command in `streams.sh` to a local FLV across at least two seams (music for 400 s, ring and spiral for 450 s; without `-re`, which only sets the pace): no backwards timestamps, no gaps, and keyframes never more than 2.0 s apart.
- `streams.sh` (bash 5 on Linux, with local FLV files in place of YouTube's server):
  - Three streams ran at once and all stopped at the deadline.
  - Keys typed at the prompt had spaces trimmed.
  - A dropped stream retried every 5 s.
  - Ctrl+C stopped everything and left no ffmpeg running.
  - Not run under macOS's bash 3.2 here. The single-stream command it wraps did run on GJ's Mac.
- From a fresh clone, with the four source Shorts and the spiral loop already rendered:
  - `rounds.py 7372` re-rendered round 1, byte-identical to the streamed one, in 51 s.
  - `compose.py music`, `ring` and `spiral` rebuilt the three files in 1.3, 3.3 and 1.8 min. Other jobs were running at the same time; the original music build took 77 s alone.
  - Frame counts matched and the audio was bit-identical.
  - The video matched to within encoder noise: the worst frame of each was 58, 49 and 52 dB PSNR from the streamed file. Even two identical runs don't give byte-identical video (see Gotchas).
  - `compose.py thumb` turned the stairs template's `thumbnail.png` into a 1280×720 thumbnail in the stream layout.
  - `RING_SEED=1234 RING_RACE_DIR=<dir> python3 sim.py record`, the path `rounds.py` takes for a seed with no recorded race, saved the race into that folder.
- The song titles never appear on screen in these four Shorts. They were checked at 2 s and 8 s, and the guess card covers the first 10 s.

## Files
| file | what |
|---|---|
| `compose.py` | the three stream files and stream thumbnails: settings at the top (layout, songs, bitrate, window), Pillow side panels, one ffmpeg filter graph per file |
| `rounds.py` | renders the eight Ring Escape rounds into `build/rounds/` by running `../ring-escape/build.py` with `RING_SEED`, `RING_RACE_DIR` and `RING_OUT_DIR` set; skips finished rounds |
| `streams.sh` | runs the three streams at once on a Mac: asks for the keys, keeps the Mac awake, reconnects, and stops every stream at 11 h |
| `assets/race_*.npz` | the recorded races of seven round seeds (8450's ships with `../ring-escape`), so the rounds replay identically on any machine |
| `style.json` | every value: layout, colours, encode, each stream's contents and length, `streams.sh` settings |
| `preview.png` | one frame of each stream: spiral, music, ring |

## Reuse
```bash
./setup.sh ball-sims          # Python packages, fonts (Montserrat from marble-raytrace-kit), ffmpeg check
# the sources, once each (see their READMEs; about 35 min in all)
(cd ../marble-stairs-song && python3 make_video.py twinkle && python3 make_video.py jingle-bells)
(cd ../marble-twin-stairs && python3 make_video.py ode-to-joy)
(cd ../marble-spiral-round && python3 make_video.py row-row-row)
(cd ../marble-spiral-loop && python3 make_loop.py && python3 music.py)
# the streams
python3 rounds.py             # 8 rounds, about 1 min each -> build/rounds/
python3 compose.py music      # -> build/marble_music.mp4
python3 compose.py ring       # -> build/ring_escape.mp4
python3 compose.py spiral     # -> build/loop.mp4
python3 compose.py thumb ../marble-stairs-song/build/twinkle/thumbnail.png build/thumbnail_music.jpg
```
To stream, put `streams.sh`, `build/loop.mp4`, `build/marble_music.mp4`, `build/ring_escape.mp4` and `../marble-spiral-loop/build/marble_bells_mix.m4a` (renamed `mix.m4a`) in one folder on the Mac. Then run `bash streams.sh` there.

On YouTube, schedule one stream per file (Live Control Room → Manage → Schedule stream). Give each its own stream key, and turn on Auto-start and Auto-stop, so each broadcast starts when its data arrives and ends when `streams.sh` stops sending.

The copy GJ was given (Marble Pop style, see the repo's `CLAUDE.md`; on a livestream, picks go in the chat):

| stream | title | description |
|---|---|---|
| spiral | `Marble Music Box 🎶 Relaxing Rainbow Marble Run LIVE` | `Marbles spiral down a rainbow music box and ring soft bells, nonstop.` / `Pick your marble in the chat ⚪🔵🔴🟢🟡🟣` / `Made with a 3D marble simulation` / `#marbles #relaxingmusic #satisfying #marblerun` |
| music | `Marbles Play Songs 🎵 Guess the Song! LIVE` | `Marbles roll down rainbow stairs and play a song. Can you guess it before the title shows up?` / `Pick your marble in the chat ⚪🔵🔴🟢🟡🟣` / `Made with a 3D marble simulation` / `#marbles #guessthesong #marblemusic #satisfying` |
| ring | `Which Marble Escapes First? 👑 Pick Your Color LIVE` | `8 marbles, 10 spinning rings. First marble out wins the crown!` / `Pick your color in the chat 🔴🔵🟢🟡🟣🟠` / `Made with a physics simulation` / `#marbles #pickyourcolor #whowillwin #satisfying` |

Thumbnails are 1280×720 frames in the stream layout, with no added text: `compose.py thumb` on a template's `thumbnail.png` (music) or on a Short's frame (ring).

**Changing it:**
- Other songs: add `(Short, title)` pairs to `SONGS`. Any 1080×1920, 30 fps Short with audio works, as long as it doesn't show the song's name in the first `REVEAL_S` seconds.
- Other rounds: pass seeds to `rounds.py` (`python3 rounds.py 111 222 ...`; a seed without a recorded race is simulated first and saved to `assets/`). Find seeds with `../ring-escape/search.py`, and set its `AVOID_WINNER = ""` so every colour can win. The shipped eight are the top-scoring seed for each winning colour.
- Two streams instead of three, or a different length: delete a `stream ... &` line, or change `HOURS`, in `streams.sh`.

## Gotchas
- **One key per stream.** A key carries one stream, and each scheduled stream is bound to its own key. `streams.sh` refuses duplicate keys.
- **Auto-stop on, 11 hours.** YouTube can archive a stream that's shorter than 12 hours, and may not capture a longer one at all. `HOURS=11` ends every broadcast well before that. Auto-stop is what ends the broadcast when the data stops; without it, the stream waits for someone to click End stream.
- **Keyframes every 2 s, and frame 0 is one.** The stream copies the video without re-encoding, so the file's GOP is the stream's GOP. Encode anything new with `-g 60 -keyint_min 60 -sc_threshold 0`. Then every seam of `-stream_loop` starts on a keyframe.
- **Upload.** Each stream peaks at about 6.1 Mbps (6 Mbps video cap plus 128k audio), so three need about 20 Mbps of upload.
- **The spiral stream's audio loops separately.** The 216 s video and the 10.45-minute `mix.m4a` are two inputs, each with `-stream_loop -1`, so the music doesn't restart when the picture does.
- **Spiral length.** `loop.mp4` is rounded up to whole 24 s spiral loops (9), so the music box never jumps. The window holds the last round's final frame for the extra 6 s.
- **Downloads get renamed.** Browsers rename a second download (`loop (1).mp4`, `loop-2.mp4`). `streams.sh` stops with a message if a file isn't there under its exact name.
- **The Mac must stay awake and online.** `streams.sh` runs `caffeinate` while it streams, but closing a MacBook's lid still sleeps it.
- **`rounds.py` numbers rounds in the order given,** and `compose.py ring` plays `build/rounds/` in file-name order. Delete old rounds before rendering a new set.
- **The stream files aren't bit-exact between runs.** Two identical runs of the first song differed in 958 of 968 video frames, though the audio was identical and the frames looked the same. To check a rebuild, compare PSNR (`ffmpeg -i a.mp4 -i b.mp4 -lavfi psnr -f null -`), not bytes. The rounds (CRF encode) do come out byte-identical.
- **The script must wait for the streams only.** It used to end with a bare `wait`, which also waits for `caffeinate -w $$`, which waits for the script: on GJ's Mac every stream printed `done` but the script never ended, so Terminal showed `caffeinate` and no prompt, and typed commands went nowhere. It now waits for the stream PIDs and then stops `caffeinate`. Linux has no `caffeinate`, so the first tests missed it.
- **Streams can end a few minutes after the printed stop time.** `-t` counts video time, and video time fell behind the clock during the night: the Nov 26 run started at 06:55 with a 17:55 stop and ended at 17:56 (twin) and 18:03 (spiral, stairs), still well under YouTube's 12 h archive limit. A dropped connection (all three dropped at once at 11:19 that day) reconnected after 5 s on its own.

## What it can't do
- Nothing reacts to chat: the picks people comment don't change anything, and the rounds are pre-rendered, so each file repeats every 2.6–3.6 minutes (about 180–250 times in 11 hours).
- It hasn't been tested what YouTube does with Auto-stop during a longer outage. A dropped connection retries after 5 s, but if YouTube has ended the broadcast by then, the retry has no scheduled stream to go to.
- The Mac has to keep running for the whole stream; nothing here streams from a server.

## Dependencies (tested)
- Python 3.13.18, Pillow 12.3.0
- ffmpeg 6.1.1 with libx264 and the built-in AAC encoder (cloud session); streaming needs only an ffmpeg with the built-in AAC encoder, because the video is copied, not re-encoded
- bash 5.2 (tested); macOS bash 3.2 with `caffeinate` and `date -r` (what `streams.sh` is written for)
- `../marble-raytrace-kit` (font), `../ring-escape` and its siblings (rounds), the four source Shorts' templates, `../marble-spiral-loop`
- Linux x86-64, 2 cores
