# marble-funnel-drain (game template)

The complete code behind the Marble Pop Short **"Last Marble Left WINS 🕳️ Pick Your Color"** (Nov 2026; 30.8 s, 924 frames, 1080×1920, 30 fps), a glossy 3D marble drain rendered on the CPU with no Blender and no GPU. The episode plays out like this:
- 0–1.4 s: a low close-up as 480 chrome marbles flood across a lacquered hardwood board, in slow motion.
- By 3.2 s the camera has pulled back to an angled overview. The flood sweeps down the left side, along the bottom and up into a spiral around a funnel with a hole in the middle.
- 7–12 s: the camera swoops down to a low close-up with depth of field. The four coloured marbles (red, blue, green, yellow) roll past in focus, in slow motion.
- 12–21 s: a slow push-in as the disk drains and shrinks to a ring of marbles circling the rim. Yellow drops out at 18.0 s.
- 22–29.6 s: a close-up at the hole in slow motion. Red drops at 26.3 s, then blue at 27.5 s, and green, the last marble on the board, wins at 29.3 s. A chime plays for each colour that drops out, and a short arpeggio for the winner.
- The camera then glides back to the opening shot over the empty board, so frame 0 follows the last frame seamlessly.

The physics really decides the order the marbles drain in. Every marble is identical; the colours are given afterwards, from the drain order (see **Gotchas**).

![preview](preview.png)

**Used in:** the "Last Marble Left WINS" Short made for Marble Pop (Nov 2026, delivered as `last_marble_wins_v3.mp4`). Verified on a 2-core cloud session, running from this folder:
- `python sim.py --compare` re-simulates seed 3 and gets arrays bit-identical to `assets/drain_seed3.npz` (positions, states, events, drain times).
- `--stills 0,300,600,720` (opening, low close-up, push-in, finale) match the frames rendered for the delivered video pixel for pixel, and match the delivered mp4 itself to 41–43 dB PSNR (H.264 noise).
- `--thumb-only` matches the delivered thumbnail pixel for pixel. `audio.py` reproduces the delivered soundtrack WAV sample for sample.
- `python make_video.py --max-frames 60` builds a 2-second test video end to end (two workers, concat, soundtrack, mux).
- `python make_video.py` with the shipped settings rebuilt `build/marble_funnel_drain.mp4` byte-identical to the delivered file (same MD5 for the whole file, 82,965,910 bytes) in 18.9 minutes, and `build/thumbnail.jpg` byte-identical to the delivered thumbnail.

## Files
| file | what |
|---|---|
| `settings.py` | **every setting**: physics and board, colours and how they're picked, look (lights, wood, exposure), camera shots and keys, slow motion, thumbnail, encoding |
| `sim.py` | deterministic physics (numba): soft-sphere marbles rolling on the board's height field, invisible rounded walls, the hole; writes positions at 120 Hz plus every impact for the sound |
| `render.py` | the renderer (numba): board ray-cast with a glossy lacquer that reflects the marbles, ray-traced chrome and metallic marbles, soft shadows, motion blur, depth of field, bloom, ACES tone map |
| `timeline.py` | sim time ↔ video time (eased slow motion), the camera path between shots, marble positions per frame, which marbles get colours |
| `audio.py` | the soundtrack, synthesized from the simulation's impacts and drops: steel clicks, rolling noise, drops into the hole, whooshes on camera moves, chimes |
| `make_video.py` | the whole pipeline: frames in 2 workers → soundtrack → mux → thumbnail; also `--stills`, `--thumb-only`, `--info`, `--where`, `--max-frames`, `--style` |
| `assets/drain_seed3.npz` | the recorded race for seed 3 (6.8 MB), so it replays identically on any machine |
| `style.json` | every value plus the episode facts (frames, places, out times), camera moves and the YouTube copy |
| `preview.png` | six moments: opening close-up, overview, low close-up, push-in, finale, last two |

## Reuse
```bash
./setup.sh ball-sims            # or: pip install numpy scipy numba opencv-python pillow (plus ffmpeg)
python3 make_video.py --info    # length, camera keys, when each colour drops out
python3 make_video.py --stills 0,300,600,720
python3 make_video.py           # -> build/marble_funnel_drain.mp4 + build/thumbnail.png/.jpg
```
A full build takes about 19 minutes on a 2-core cloud session. A fresh clone adds about 20 s to build the board's world maps, which are then cached in `build/cache/`. The slowest frames are the low close-up (about 3–5 s each); overview frames with a still camera take about 1 s.

**A new episode:**
1. Pick a new race: `SEED=7 USE_RECORDED_SIM=0 python3 sim.py`, then `SEED=7 USE_RECORDED_SIM=0 python3 make_video.py --info`. Look at the last gaps it prints. A good finale has the last three marbles dropping about a second apart, not together.
2. Change `PLACES` for other colours or another order. 4th place is the marble draining closest to `FOURTH_OUT_AT`; pick a time in the overview so that elimination is visible.
3. Aim the shots: `--where 7.8` prints where the coloured marbles are at a sim time. Move `SHOTS["CLOSE"]` (and the `KEYS` around it) to where they roll past, and point `THUMB` at a moment with several colours close together.
4. Render `--stills` of the busiest moments, then the full video. To keep the new race reproducible, copy `build/sim_seed7.npz` to `assets/drain_seed7.npz`.
5. Copy (Marble Pop style, see the repo's `CLAUDE.md`): title `Last Marble Left WINS 🕳️ Pick Your Color`; description `480 marbles swirl into one hole. The last color left wins!` / `Pick your color in the comments 🔴🔵🟢🟡` / `Made with a 3D physics simulation` / `#marbles #satisfying #3d #pickyourcolor #whowillwin`. The thumbnail has no text.

## Gotchas
- **The colours are assigned after the simulation.** The winner is whichever marble happens to drain last, 2nd and 3rd are the two before it, and 4th is picked by time. The race itself is real physics with identical marbles.
- **Re-simulating on another machine can give a different race.** The sim is chaotic and numba's floating point can differ between CPUs. That's why the recorded race ships in `assets/` and is used by default (`USE_RECORDED_SIM=1`).
- **The finale depends on friction.** With `crr=8, gam=0.2` and a 2.05 hole, the last 20 marbles drop within 0.4 s and you can't see who's last. The shipped `crr=4, gam=0.15, RH=2.2` leaves about 40 marbles circling the rim and dropping one by one. Much lower friction (`crr=3, gam=0.1`) leaves stragglers orbiting for 15 s.
- **The hole is drawn smaller than the physics hole** (`LOOK["RH"]=2.05` vs `SIM["RH"]=2.2`). These are the shipped values, kept so the video reproduces; for a new video set them equal.
- **Keep the spawn band out of every shot.** Marbles appear at y 52.5–55.5; a shot that sees past y ≈ 51 on the board shows them popping in. The walls are invisible, so shots also shouldn't look past the board's edges, where no marble ever goes.
- **Camera elevation 29° or more.** The board ray-cast assumes rays steeper than the board's slopes, and grazing views can glitch at the funnel rim. Keep the top edge of the frame below the horizon too.
- **Depth of field cheats on blurry marbles.** Chrome marbles blurred by more than 7 px skip neighbour reflections and motion blur. That's invisible under the blur and roughly halves the close-up render time.
- **The opening is the loop point.** The last key must be the first shot (`OPEN`), and `T0` should be when the first marbles reach that shot's top edge. Then frame 0 continues the last frame.
- Don't commit `build/`: it holds the cache, stills, segments, the WAV and the mp4.

## What it can't do
- There's no on-screen text, winner card or end screen; this format has none. Use `../thumbnail-title` or `../winner-card` if you want them.
- One board shape with one hole. Marbles can't leave the surface (no jumps or ramps) except by falling into the hole.
- Chrome and glossy metallic colours only: no glass or transparent marbles.
- The camera can't roll or shake, and a held shot can't drift (the board ray-cast is cached only while the camera is still; a moving camera costs about 1 s more per frame).
- The board is only lit by the fixed studio set-up in `LOOK`: one key softbox, one fill strip and two accent strips.

## Dependencies (tested)
- Python 3.13.18, numpy 2.5.3, scipy 1.18.1, numba 0.68.1, opencv-python 5.0.0, Pillow 12.3.0
- ffmpeg 6.1.1 with libx264 and the built-in AAC encoder
- Linux x86-64, 2 cores
