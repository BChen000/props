# sword-roulette (game template)

The complete code behind the **Sword Roulette** Short (Marble Pop, Nov 2026; 39.67 s, 1080×1920, 30 fps). The episode plays out like this:
- A BIG sword spins like a roulette needle and picks one ball (RED).
- That ball gets the BIG sword and the other five get small swords.
- The balls fight in a real physics simulation. RED knocks out four, then GREEN takes it down in a 10 HP vs 10 HP final duel.
- The final blow plays in slow motion with a zoom and a hit-stop.
- "GREEN WINS!" and the SUBSCRIBE button appear on the same frame, followed by "What do you want to see next?".

Running `bash build.sh` with the shipped settings replays that exact match, with the same story, timing and layout. Since the Ring Escape update (Nov 2026) it differs from the posted video in four places, because the repo now keeps one copy of each piece:
- **Slow-motion vignette** (`../battle-fx`): it now follows the playback speed and darkens the whole frame around the action, so the title dims during slow motion. Before, a fixed vignette sat inside the arena.
- **Crown** (`../winner-card`, from `../crown-icon`): the winner's crown has a gold gradient, a band and jewels, and is slightly larger.
- **Riser** (`../battle-audio`): the slow-motion build-up climbs smoothly instead of in 8 steps.
- **Loudness:** the soundtrack goes through a look-ahead limiter and is normalised to -14 LUFS (the posted video measures about -16.4 LUFS).

Frames outside slow motion and before the winner's crown are unchanged: stills at 5.0, 11.0, 15.0, 26.0, 30.0 and 34.5 s came out pixel-identical to the delivered render. The code that renders the posted version exactly is in the repo's history, in the commit before this update.

## Files
| file | what |
|---|---|
| `settings.py` | **every setting**: seed, all on-screen text, timings, slow motion, physics |
| `sim.py` | deterministic physics: bouncing, orbiting swords, hits, clashes, knockback, end-game hunting |
| `timeline.py` | video time ↔ sim time (slow-mo + hit-stop), roulette, text and status schedule |
| `render.py` | composes the props into frames; stills or ffmpeg chunks |
| `audio.py` | cue sheet: places `battle-audio` sounds on the timeline and masters to WAV |
| `search.py` | finds seeds (matches) with a dramatic story |
| `tune.py` | balance check: big-sword win rate and fight length over many seeds |
| `build.sh` | full render: 4 chunks, 2 at a time, then concat and mux the audio (normalised to -14 LUFS) into `out/sword_roulette.mp4` |

## Make a new episode
```bash
python search.py 0 6000 --outcome upset     # or --outcome big / any; prints candidate seeds + KO order
# put the seed you like in settings.py -> SEED
python timeline.py                          # prints big-sword owner, winner, KO times, video length
python render.py still 2 12 30              # quick look at a few moments (stills/)
bash build.sh                               # about 40 s on 2 CPU cores -> out/sword_roulette.mp4
```
- Don't commit `out/` or `stills/`, which are render outputs.
- The physics really decides the outcome. `search.py` only picks which match to show. The shipped balance gives the big sword about a 51 % win rate and a median fight of 17 s (`python tune.py 150`).
- To rename or recolour the balls, change `NAMES`/`COLORS` in `settings.py` (the defaults come from `../style-kit`). The chip row centres itself for the number of balls: 6 start at x = 42 as shipped, and 4 at x = 210, as in the Marble Olympics special (`../marble-olympics`). With 4 balls `search.py`'s filters are too strict (the BIG sword can't make 3 KOs and lose); `../marble-olympics/pick_seeds.py` has looser ones.
- To make a different game on the same look, copy this folder, replace the rules in `sim.py` (keep its `events`/`states` output), and reuse `render.py`'s composition.

## How time works
The physics runs at 120 Hz in **sim time** `t`. The video runs in **video time** `v`, at 30 fps. `timeline.py` maps between them:
- `v = 6.0` is sim `t = 0`.
- Around each KO the video slows to 0.35×, and to 0.28× for the last 0.85 sim-s before the final blow.
- The final blow freezes for 0.32 s, then plays at 0.45× for 0.5 sim-s.

Every event gets both `t` and `v`. Particles age on sim time, while damage numbers and text age on video time.

## Uses these props
`../style-kit`, `../arena-board`, `../color-chips`, `../glossy-ball`, `../sword`, `../roulette-spinner`, `../battle-fx`, `../winner-card` (with `../crown-icon`), `../subscribe-cta`, `../battle-audio`. They're imported from the sibling folders, so keep the `ball-sims/` layout.

## Dependencies (tested)
- Python 3.13.18
- pycairo 1.29.2 (cairo 1.18.0)
- numpy 2.5.3, scipy 1.18.1 (audio)
- ffmpeg 6.1.1, with libx264 and the built-in AAC encoder
- Poppins (run `python ../style-kit/get_fonts.py`)
- Linux was used for the reference renders (see the font note in `../style-kit/README.md`)

No photos or third-party images are used. Everything is drawn in code.
