# ring-escape (game template)

The complete code behind the **Ring Escape** Short (Marble Pop, Nov 2026, posted as "First Marble OUT Wins 👑 Pick Your Color"; 26.07 s, 782 frames, 1080×1920, 30 fps). The episode plays out like this:
- 8 marbles bounce inside 10 spinning neon rings, each with a gap.
- The first marble through a gap breaks that ring and takes the crown. The chips count each colour's breaks.
- The last ring turns gold, and the rings and marbles speed up. Near misses on its gap get a "SO CLOSE" callout.
- The winning escape plays in slow motion. "CYAN WINS!" follows, with confetti and a like/subscribe prompt.
- In the last 16 frames everything glides back to frame 0, so the Short loops seamlessly.

The physics really decides the race. `search.py` only picks which race to show.

## Rebuilding the posted video
`python build.py` with the shipped settings renders `out/ring_escape.mp4`. Its video stream is byte-identical to the delivered file (same H.264 stream checksum).

The soundtrack is not identical. The posted video used Ring Escape's own copies of the sounds. To keep one copy of each sound in the repo, this template now uses `../battle-audio` for every sound, with the `K_*` gains in `audio.py` matching each one's loudness to the posted mix. The cues, timing and music are the same, and the overall loudness is -14.1 LUFS (the posted one was -14.0). The most noticeable difference is the win boom: its low rumble now fades in about 0.7 s instead of 1.5 s. The posted soundtrack's code is in the repo's history, in the commit before this update.

## Files
| file | what |
|---|---|
| `settings.py` | **every setting**: seed, physics, rings, timing, slow motion, all on-screen text |
| `sim.py` | deterministic physics (numba): marbles, spinning rings, gaps, rounded gap ends, ring breaks, win |
| `timeline.py` | the race in sim time mapped to video time (slow motion, loop reset), events sorted for the renderer |
| `render.py` | composes the props into frames: stills, an encoded frame range, or `preview.png` |
| `audio.py` | cue sheet: places `../battle-audio` sounds on the timeline and masters to WAV |
| `build.py` | full render: 4 chunks, 2 at a time, concat, soundtrack, -14 LUFS, mux into `out/ring_escape.mp4` |
| `search.py` | scores thousands of seeds for a good story (early hook, steady breaks, a long last ring, near misses, an underdog winner) |
| `tune.py` | balance check: break and win times over many seeds |
| `assets/race_8450.npz` | the recorded race for seed 8450, so it replays identically on any machine |
| `style.json` | every value: episode facts, physics, timing, text, encoding, sound cues |
| `preview.png` | frame 330 (11 s): GREEN has the crown, 4 rings left |

## Make a new episode
```bash
python search.py 0 40000        # about 10 min on 2 cores; prints the top 12, saves out/top_seeds.json
# put the seed you like in settings.py -> SEED
python sim.py record            # saves assets/race_<SEED>.npz and prints the breaks
python timeline.py              # frame count, duration, break and near-miss times
python render.py still 0 330 700   # out/stills/f0000.png ... check a few frames
python build.py                 # about 1 min on 2 CPU cores -> out/ring_escape.mp4
```
- Don't commit `out/` (videos, stills, WAVs, seed lists). Commit the new `assets/race_<SEED>.npz` if you want the episode to rebuild exactly on another machine (it's about 1.2 MB).
- To render another seed without editing `settings.py`, set `RING_SEED`. `RING_RACE_DIR` (where races are saved and replayed from) and `RING_OUT_DIR` work the same way, e.g. `RING_SEED=7372 RING_RACE_DIR=../marble-live-streams/assets python build.py`. `../marble-live-streams/rounds.py` renders its 8 livestream rounds this way.
- To change the game, edit `PHYS` in `settings.py` (ring spin, gaps, speeds, speed-up), then run `python tune.py 100` to check race lengths before searching. The shipped settings give a median win of 24.8 s, and 77 of 100 races finish within 40 s.
- `search.py` gives a small penalty to races won by `AVOID_WINNER` (GREEN, who won the episode before Ring Escape). Set it to the last episode's winner each time, so CYAN for the next one.
- The thumbnail comes from `../question-thumbnail`, which renders this arena by default.

## How time works
The physics runs at 240 Hz in **sim time** `t`. The video runs at 30 fps in **video time** `tau`. Up to the slow motion they're equal. Around the winning escape (from 0.40 sim-s before to 0.09 after) the rate ramps down to 0.24× and back up. After 1.55 sim-s of celebration the sim freezes, and 16 frames glide everything back to frame 0. Ring breaks, hits and the chips' pops use sim time; the headline pops, captions and win effects use video time.

## Uses these props
`../neon-kit`, `../escape-rings`, `../neon-marble`, `../crown-icon`, `../neon-hud`, `../neon-fx`, `../battle-fx` (slow-motion vignette) and `../battle-audio`. They're imported from the sibling folders, so keep the `ball-sims/` layout. `../battle-fx` in turn imports `../style-kit` and `../sword`.

## Dependencies (tested)
- Python 3.13.18
- skia-python 144.1
- numba 0.68.1, numpy 2.5.3 (physics)
- scipy 1.18.1 (audio)
- pycairo 1.29.2 (imported by `../battle-fx`)
- ffmpeg 6.1.1 with libx264 and the built-in AAC encoder
- DejaVu Sans Bold 2.37 (run `python ../neon-kit/get_fonts.py`)
- The reference render was made on Linux x86-64. On another OS or CPU, skia's anti-aliasing can differ by a pixel level or two, and a race that is simulated instead of replayed from `assets/` can come out differently.

No photos or third-party images are used, and every sound is synthesized. If an episode needs a downloaded image or sound, keep it out of this repo (for example in a local `media/` folder that isn't committed) and note its source in your own notes.
