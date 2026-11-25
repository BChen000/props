# props

The code behind GJ's YouTube Shorts, kept so a new video starts from a working pipeline instead of from scratch. Each prop is a folder with runnable code (settings at the top), a `style.json` that pins down the look, a README and a `preview.png`. Rendered videos, font files and build output are not stored here.

AI assistants: read [`CLAUDE.md`](CLAUDE.md) for the workflow and the rules for adding props.

## Quick start
```bash
git clone https://github.com/BChen000/props && cd props
./setup.sh --blender4                       # flags for your prop: see the table below or ./setup.sh's header
cd ball-sims/marble-song-battle && ./make_video.sh
```

## Complete videos: start here
Each of these makes a finished 1080×1920 Short with sound. Times are on a 2-core cloud box with no GPU.

| Prop | Short | Run | Setup flags | Time |
|---|---|---|---|---|
| [`ability-battle-template`](ball-sims/ability-battle-template) | POWER BALLS: four ability balls in a grid arena, every hit upgrades your power | `python make_video.py` | `--skia` | ~1 min |
| [`sword-roulette`](ball-sims/sword-roulette) | Sword Roulette: six balls, one random ball gets the big sword | `bash build.sh` | `--cairo --fonts` | |
| [`ring-escape`](ball-sims/ring-escape) | Ring Escape: "First Marble OUT Wins 👑", 10 rotating neon rings | `search.py` → `sim.py` → `build.py` | `--skia --numba --cairo --fonts` | seed search ~10 min |
| [`xylophone-song-template`](ball-sims/xylophone-song-template) | Marble xylophone: Twinkle Twinkle (50 marbles), 40 marbles | `python3 make_video.py twinkle` | `--bpy --opencv` | ~20 min first, then ~10 min per song |
| [`cloth-faces`](ball-sims/cloth-faces) | 1 Face vs 1,000,000 Faces Blanket (marble, rubber duck) | `HERO=duck ./make_video.sh` | `--bpy --exr --fonts` | ~2.5 h (~70 min with sims cached) |
| [`glass-shatter`](ball-sims/glass-shatter) | 1 KG vs 1,000 KG Ball Smashing Glass | `./make_video.sh` | `--bpy --exr --pybullet --fonts` | ~2 h |
| [`marble-song-battle`](ball-sims/marble-song-battle) | Naughty or Nice?: marble course where every bounce plays a note, 3 vs 3 songs | `./make_video.sh` | `--blender4` | ~1 h 50 min |

## Parts
Pieces of the videos above, usable on their own.

**Shared looks**
- [`style-kit`](ball-sims/style-kit): the Marble Pop look (canvas, six ball colours, UI colours, Poppins text helpers, easing); the pycairo props import it
- [`neon-kit`](ball-sims/neon-kit): the navy-and-neon look (8 marble colours, DejaVu text, grid background); the skia neon props import it
- [`crown-icon`](ball-sims/crown-icon): the gold crown, in skia and pycairo versions
- [`battle-audio`](ball-sims/battle-audio): the channel's synthesized sound kit (Sword Roulette, Ring Escape)

**POWER BALLS** (skia)
- [`ability-fighters`](ball-sims/ability-fighters): the four fighters and every ability visual
- [`battle-screen-layout`](ball-sims/battle-screen-layout): background, title, arena frame and caption
- [`fighter-cards`](ball-sims/fighter-cards): the row of four cards with hearts and power bars
- [`battle-overlays`](ball-sims/battle-overlays): overlays drawn over the arena
- [`impact-fx`](ball-sims/impact-fx): bursts, sparks, damage numbers, shake and the knockout flash
- [`ability-sfx`](ball-sims/ability-sfx): the 21 synthesized sound effects
- [`edm-battle-bed`](ball-sims/edm-battle-bed): the 128 BPM EDM music bed with a tape stop

**Sword Roulette** (pycairo)
- [`arena-board`](ball-sims/arena-board): the game board
- [`color-chips`](ball-sims/color-chips): the scoreboard chips under the title
- [`glossy-ball`](ball-sims/glossy-ball): the ball character
- [`sword`](ball-sims/sword): the orbiting sword
- [`roulette-spinner`](ball-sims/roulette-spinner): the "one random ball gets it" intro
- [`battle-fx`](ball-sims/battle-fx): the fight effects
- [`winner-card`](ball-sims/winner-card): the winner reveal
- [`subscribe-cta`](ball-sims/subscribe-cta): the end-screen subscribe call to action

**Ring Escape** (skia, navy and neon)
- [`escape-rings`](ball-sims/escape-rings): the 10 rotating neon rings
- [`neon-marble`](ball-sims/neon-marble): the glossy neon marble
- [`neon-fx`](ball-sims/neon-fx): particles and camera effects
- [`neon-hud`](ball-sims/neon-hud): the on-screen overlay
- [`question-thumbnail`](ball-sims/question-thumbnail): a two-line question thumbnail over a game scene

**Marble xylophone** (Blender 5.3)
- [`xylophone-ramp`](ball-sims/xylophone-ramp): the 3D glockenspiel ramp set
- [`marble-drop-sim`](ball-sims/marble-drop-sim): marble physics, including drops timed to play a melody
- [`marble-plate-compositor`](ball-sims/marble-plate-compositor): paints ray-traced marbles onto pre-rendered Cycles plates (fast)
- [`glockenspiel-sounds`](ball-sims/glockenspiel-sounds): the soundtrack from hit events
- [`marble-counter`](ball-sims/marble-counter): the ×1…×40! counter
- [`thumbnail-title`](ball-sims/thumbnail-title): thumbnail with title text from a rendered frame

## Layout
- `ball-sims/`: Marble Pop (formerly Fun House 67). Other channels get their own folder; parts shared across channels go in `shared/`.
- `setup.sh`: installs what a prop needs in a fresh session.
- Every prop: `<channel>/<prop-name>/` with code, `style.json`, `README.md`, `preview.png` and `assets/` if needed.
