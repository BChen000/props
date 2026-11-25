# longform-compilation

One command turns a folder of vertical Marble Pop Shorts into a 16:9 long-form "Guess the Marble Song" game video. Each Short plays in a rounded card in the middle while the side panels run the game: guess-the-song countdowns with answer reveals, pick-your-color prompts, a 20-round progress grid and up-next teasers. Rounds are joined by a "marble pop" transition, and the video ends on a never-posted bonus song with space for YouTube's end screen.

![preview](preview.png)

**Used in:** *Guess the Marble Song! 🎵 20 Rounds + a Secret Bonus* (Marble Pop long-form, Nov 2026; 10:29, 18,884 frames, 1920×1080, 30 fps). It was built from the channel's 20 marble Shorts plus a Joy to the World staircase rendered with `../marble-stairs-song`. Verified on the finished file:
- The video and audio streams are both 629.47 s long, and a full decode shows no errors.
- Each of the 14 songs' first notes lands within 10 ms of its planned time, so the cuts, speed-ups and audio assembly stay in sync across the whole video.
- Integrated loudness is −15.0 LUFS with a 4.9 LU loudness range; the sample peak is −0.4 dBFS.
- Stills of the intro, a transition, a countdown, every reveal type, a race ending and the end screen were checked by eye.

## Files
| file | what |
|---|---|
| `settings.py` | every value: paths, canvas, card modes, loudness, transitions, timings and colours, plus `ITEMS`, the running order with each Short's cut points, speed-ups, game type and answers |
| `build.py` | plan → UI assets → one H.264 segment per round (resumable) → sample-accurate audio mix → concat + AAC → thumbnail, chapters, copy |
| `ui.py` | Pillow drawing: blurred backdrop, card mask and shadow, side-panel game UI, countdown, answer pop-in, up-next pill, intro and end-screen panels, marble-pop transition frames, the no-text thumbnail |
| `youtube_copy.py` | title ideas and the description with chapters → `build/youtube_copy.txt` |
| `style.json` | layout, timing, audio and encode values as numbers |
| `preview.png` | nine moments of the finished video |

## Reuse
```bash
./setup.sh ball-sims        # numpy, scipy, Pillow, ffmpeg, Poppins (../style-kit/get_fonts.py)
cd ball-sims/marble-stairs-song && WATERMARK="" python3 make_video.py joy-to-the-world --no-thumb   # the bonus (~7 min)
cd ../longform-compilation
SHORTS_DIR=/path/to/shorts python3 build.py --plan          # timeline only
SHORTS_DIR=/path/to/shorts python3 build.py --stills 0,1    # layout stills of rounds 0 and 1 (~20 s)
SHORTS_DIR=/path/to/shorts python3 build.py                 # everything: ~8 min on 2 cores for 10.5 min of video
```
Outputs in `build/`: the mp4, `thumbnail.png`/`.jpg` (1280×720, no text), `chapters.txt`, `youtube_copy.txt` and `plan.json`.

**A new compilation:** edit `ITEMS` in `settings.py`, then run `--stills` on the rounds you changed before a full build.
- `file` is a glob matched in `SHORTS_DIR`, so upload prefixes don't matter.
- `kind` picks the game:
  - `song`: countdown, then the answer pops in.
  - `race`: pick your color, then "did your color win?" at `end_t`.
  - `run`: a question with an optional reveal (`reveal`, `answer`).
  - `bonus`: the closing song with the end screen.
- `mode`: `zoom` crops a 1080×1480 window from `crop_y`. For the music sets this keeps the round title and drops the watermark, and the marbles come out about 1.3× bigger than `full` (the whole 1080×1920 frame).
- `f0` is the first note in the Short; the cut lands 0.45 s before it. `te` cuts the static tail.
- `speed=[(from, to, factor)]` fast-forwards a slow stretch. The video is retimed and the audio goes through `atempo`, so pitch is kept.

## Gotchas
- **Segments are reused.** Delete `build/segs/seg_NN.mp4` (or set `FORCE=1`) after changing a round. Each segment is self-contained, so other rounds don't need re-rendering; the audio is always rebuilt.
- **Transitions are pre-drawn PNGs.** ffmpeg's `xfade` circle transitions are soft radial dissolves, and a custom `xfade` expression took about 5 s per 1080p frame on 2 cores. So the marble pop is drawn once per colour as 8 cover and 8 uncover RGBA frames and overlaid; the cover frames are delayed with `tpad`.
- **Looped PNG overlays are converted once.** Each one goes through `format` and then the `loop` filter. Without that, ffmpeg re-decodes every overlay PNG on every frame.
- **Loudness:** every clip is gained to −15 LUFS before mixing. The quietest source needed +4.2 dB, so its transients hit the limiter, and AAC adds about 1.5 dB of overshoot. That's why the limiter sits at −2 dB.
- **No spoilers:** the up-next pills and chapter titles never name a song. The names are in the description's spoiler line.
- **Answer titles** wrap to the fewest lines that still allow a big font (at least 46 px for two lines), choosing the split with the shortest longest line.
- **Script names:** a script named like a stdlib module breaks imports (`copy.py` broke Pillow's), hence `youtube_copy.py`.
- **Made for kids:** YouTube turns off comments, cards and end screens on videos set as made for kids. The "comment your score" line and the end-screen panels only do anything on videos that aren't.

## What it can't do
- Sources must be 1080×1920 at 30 fps.
- The progress grid holds 20 rounds (5 × 4), plus one bonus.
- Race and run reveal times are set by hand; it doesn't detect who won.
- There's no narration or music bed: the audio is the Shorts' own plus pop, whoosh, tick and ding from `../battle-audio`.

## Dependencies (tested)
- Python 3.13.18, numpy 2.5.3, scipy 1.18.1, Pillow 12.3.0
- ffmpeg 6.1.1 with libx264 and the built-in AAC encoder
- Poppins Black, ExtraBold, Bold and SemiBold from `../style-kit/get_fonts.py`
- `../battle-audio/assets` and, for the bonus, `../marble-stairs-song`
- Linux x86-64, 2 cores
