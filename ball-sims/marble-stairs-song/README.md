# marble-stairs-song (game template)

One command for a rainbow-staircase marble music Short, in the "Satisfying 3D Sims" format. Marbles roll out of a chute and hop down 8 glowing tiles, one tile per beat, and every hit plays the next note of the song. Rounds of 1, 2, 3, 5 and 8 marbles make the music fuller each time. Built on `../marble-raytrace-kit`.

![preview](preview.png)

**Used in:** the two staircase Shorts on Marble Pop (Nov 2026, uploaded as Fun House 67). The first, *Twinkle Twinkle Little Star*, broke the channel's view record (11.6k views within days, when no earlier Short had passed 1.3k); *Jingle Bells* followed. Both were rebuilt from this folder with `SPLIT=even WATERMARK="Fun House 67"`, and the default build ran from a fresh clone:
- `jingle-bells`:
  - The finished mp4's video and audio streams are bit-identical to the upload (same stream MD5).
  - Along the way, stills 600 and 920 matched the original renders pixel for pixel, the timeline and marble paths matched exactly, and `music.wav` matched byte for byte.
- `twinkle`:
  - The video stream is bit-identical to the upload.
  - The soundtrack is not. The upload used an earlier, shorter bell voice whose code wasn't kept, so the template plays the song with the later bell voice from the Jingle Bells video.
  - The notes, chords and timing are the upload's. They were read back from its audio by pitch tracking, and the G-vs-G7 choices by checking for D4 vs F4.
- Thumbnails: with `--thumb-title`, the automatically picked frames (769 and 897) match the uploads' clean thumbnails to within JPEG noise (43–44 dB PSNR). The default thumbnail is the same picture without the title, because the channel's thumbnails have no text unless GJ asks for it.

- `joy-to-the-world` (Nov 2026): the never-posted bonus round of the long-form compilation (`../longform-compilation`). It reuses Jingle Bells' rounds and entry offsets with a 64-beat melody whose first round is the hymn's falling scale, one note per tile as the first marble rolls down. Rendered from this folder with `WATERMARK="" python3 make_video.py joy-to-the-world --no-thumb`: 1128 frames, 37.6 s, music −11.1 LUFS gained to −13; stills 300 and 850 were checked by eye. The melody was written from the tune (Antioch), not pitch-tracked from a recording.
- **16:9 versions** for the full-screen long-form (Nov 2026): `twinkle`, `mary-lamb`, `old-macdonald`, `jingle-bells`, `deck-the-halls`, `merry-christmas` and `joy-to-the-world`, rendered with `MARBLE_RES=1920x1080 MARBLE_CAM=wide BUILD_DIR=build_wide WATERMARK=""`. Each came out 1920×1080 with its video and audio streams the same length (968 to 1256 frames), and the rounds were checked by eye in the long-form's segments. From a fresh clone, `--stills 300` of `mary-lamb` at 16:9 gave the same scene hash and a byte-identical timeline, and the still matches frame 300 of the render to 42.2 dB PSNR (H.264 noise). `mary-lamb`, `old-macdonald`, `deck-the-halls` and `merry-christmas` are new: their melodies were written from the public-domain tunes, one note per beat, not pitch-tracked from recordings. The close 16:9 thumbnail camera (`widethumb`) made the long-form's staircase thumbnail.

## Files
| file | what |
|---|---|
| `make_video.py` | the whole pipeline: static set → choreography → music → frames (2 workers) → mp4 at −13 LUFS → thumbnail |
| `songs.py` | the songs: melody (one note per beat), chords, rounds and when each marble leaves the chute |
| `scene.py` | the set: 8 tiles, pillars, chute with feeder tube, tray; hop physics from the BPM; main and thumbnail cameras, plus 16:9 `wide` and `widethumb` |
| `timeline.py` | exact hops (a parabola per beat) + tray physics at 1/1200 s; hits, impacts, round titles, finale |
| `music.py` | hits → melody, bass, chord tones and sparkles; tray clacks; finale chord and sparkle run |
| `style.json` | every value: videos, set, cameras, colors, physics, music rules, text |
| `preview.png` | four moments of `twinkle`: rounds of 1, 3, 5 and 8 marbles |

## Reuse
```bash
./setup.sh ball-sims                       # or: pip install numpy scipy pillow && python3 ../marble-raytrace-kit/get_fonts.py
python3 make_video.py twinkle              # -> build/twinkle/Marble_Staircase_Twinkle.mp4 + thumbnail.png
python3 make_video.py jingle-bells         # -> build/jingle-bells/Marble_Staircase_Jingle_Bells.mp4 + thumbnail.png
python3 make_video.py joy-to-the-world     # -> build/joy-to-the-world/Marble_Staircase_Joy_to_the_World.mp4 + thumbnail.png
python3 make_video.py twinkle --stills 300,650,900    # PNG stills only, to check a change
python3 make_video.py twinkle --thumb-only --thumb-title --thumb-frame 769
# 16:9 (also: mary-lamb, old-macdonald, deck-the-halls, merry-christmas)
MARBLE_RES=1920x1080 MARBLE_CAM=wide BUILD_DIR=build_wide WATERMARK= python3 make_video.py mary-lamb --no-thumb
MARBLE_RES=1920x1080 MARBLE_CAM=wide BUILD_DIR=build_thumb python3 make_video.py jingle-bells --thumb-only  # close camera
```
On a 2-core cloud session, *Jingle Bells* takes 5.4 minutes once the static sets are cached, nearly all of it rendering frames. The first run adds about 3 minutes to path-trace the set and the thumbnail camera's set; both are cached afterwards. `SPLIT=even WATERMARK="Fun House 67"` rebuilds the uploads exactly. By default the frames are split by estimated cost, which keeps both workers busy, and the watermark says Marble Pop.

**A new song:**
1. Add an entry to `SONGS` in `songs.py`:
   - `melody`: one MIDI note per beat. A negative number holds the previous note, and 0 is a rest.
   - `chords`: one chord per beat, from `VOICING`: C, F, G or G7.
   - `rounds`, and per round the beat `offsets` at which its marbles leave the chute.
2. The rounds play `sum(last offset + 8)` beats back to back. `make_video.py` warns if the melody is shorter than that.
3. Render a few `--stills` first, then the full video.
4. Write the title and description by the channel's copy rules in the repo's `CLAUDE.md`. The default thumbnail is the busiest beat of the last round, with no text.

## Gotchas
- **The melody is per beat, not per note.** A long note is the note followed by negative copies of it. A marble that hits on a beat with no melody note left plays a high C.
- **One marble per beat from the chute.** Offsets in a round must all differ; two on the same beat would overlap on every tile.
- **The voices add up from the top tile down:** melody, bass, then 3 chord tones, then sparkles. Rounds with more marbles automatically sound fuller, so keep the important note on the marble highest up the stairs.
- **`MARBLE_BPM`** (default: the song's `bpm`) changes the hop physics: gravity is solved so each hop lasts exactly one beat. The chute moves with it, so a new tempo means a new static render (1.5 min).
- **The thumbnail camera** (`MARBLE_CAM=thumb`, closer, from more to the side) has its own static set in `build/thumb_g_*`. `make_video.py` runs it in a second process.
- **16:9:** `MARBLE_RES=1920x1080` (read by `../marble-raytrace-kit/look.py`) with `MARBLE_CAM=wide` frames the whole set for landscape, and the thumbnail step then uses the closer `widethumb` camera. `WIDE_FOVY`, `WIDE_AZ`, `WIDE_EL`, `WIDE_DIST` and `WIDE_TARGET` override either one. Give each camera its own `BUILD_DIR`: the set is cached per folder by scene hash, so a different camera in the same folder re-renders it (about 6 minutes at 16:9).
- Marble colors cycle after 19 marbles. The tray is sized for the 19 marbles of the shipped videos, so many more will crowd it.
- Don't commit `build/`: it holds the G-buffers (about 450 MB per camera), the WAVs and the mp4s.

## What it can't do
- The staircase always has 8 tiles. The tile pans, the voicing order and the camera framing assume 8.
- There's no pause between rounds, no tempo change within a video, and no camera move.
- Only C-major voicings are defined (C, F, G, G7). Other keys need new `VOICING` entries.
- All marbles drop from the same chute. For two staircases, use `../marble-twin-stairs`; for a round (canon), use `../marble-spiral-round`.
- It can't play back the Twinkle upload's original bell sound (see **Used in**).

## Dependencies (tested)
- Python 3.13.18, numpy 2.5.3, scipy 1.18.1, Pillow 12.3.0
- gcc 13.3.0 with OpenMP
- ffmpeg 6.1.1 with libx264 and the built-in AAC encoder
- `../marble-raytrace-kit`, including its Montserrat font (`get_fonts.py`)
- Linux x86-64, 2 cores
