# roulette-spinner

The "one random ball gets it" intro. Six balls sit on a ring (radius 250, first ball at the top, then clockwise) and the BIG sword spins in the centre like a roulette needle.
- The spin runs from 0.75 s to 4.55 s: 4 turns with a cubic ease-out, plus motion-blur ghosts.
- The ball under the needle grows 1.12× with a white halo, and its chip gets a white border.
- When the needle stops, the chosen ball pulses gold.
- From 4.85 s to 5.35 s the sword flies onto the chosen ball, spinning 1.5 turns, with an attach flash.
- The small swords then pop onto the other balls, 0.06 s apart.

The class also returns the click (tick) times for the soundtrack, one per gap the needle passes.

**Used in:** Sword Roulette (Nov 2026), seconds 0 to 6.

## Files
- `roulette_spinner.py`: the `Roulette` class. `python roulette_spinner.py` writes `preview.png`, a mid-spin frame on the board.
- `style.json` and `preview.png`.

## Reuse
```python
import sys; sys.path += ["ball-sims/" + d for d in ("style-kit", "glossy-ball", "sword", "roulette-spinner")]
from roulette_spinner import Roulette
rl = Roulette(chosen=0, colors=[(236,65,68), (61,131,247), (50,198,100), (251,201,50), (167,91,237), (247,139,44)])
for f in range(int(6.0 * 30)):
    v = f / 30
    pointed = rl.draw(ctx, v)     # draw after the arena floor/rim; returns the index to highlight in the chips
sound_clicks = rl.ticks           # video times for a "tick" sound
```
- `chosen` decides where the needle stops. In Sword Roulette the physics seed picks it.
- Settings are the constructor arguments, with defaults at the top of the file: timings, `turns`, `start_angle`, `ring_r`, `label`, sword dims, and `glow_until` (how long the chosen ball keeps pulsing).

## Dependencies
- `../style-kit`, `../glossy-ball`, `../sword`
- `../arena-board`, only for the preview
- pycairo 1.29.2, Python 3.13.18

No photos or third-party images are included.
