# escape-rings

The Ring Escape board: 10 concentric neon rings, each with a rotating gap. Marbles bounce inside, and the first one through a gap breaks that ring.
- The ring to escape next is bright, and white dots mark its gap ends. Rings further out are dimmed.
- The last ring turns gold and pulses. On the win it flashes white and its gap closes.
- A broken ring shatters into 26 spinning fragments with a flash wave.
- In the loop reset, broken rings fade back in and every ring rotates back to its start angle, so the video loops seamlessly.

Ring colours go from violet (inner) to cyan (outer).

**Used in:** Ring Escape (Nov 2026).

## Files
- `escape_rings.py`: the module. `python escape_rings.py` redraws `preview.png` (top: start of a race; bottom: last ring, with ring 9 shattering).
- `style.json` and `preview.png`.

## Reuse
```python
import sys, math; sys.path += ["ball-sims/neon-kit", "ball-sims/escape-rings"]
from escape_rings import ring_radii, draw_arena_disc, draw_rings, GAPS_DEG
radii = ring_radii()                                   # 10 rings, 110..452 px
gaps = [math.radians(g) for g in GAPS_DEG]
phases = [...]                                         # current angle of each gap (rad), from your physics
broken = [None] * 10                                   # or seconds since ring k broke -> it shatters
draw_arena_disc(c, 540, 990)
draw_rings(c, 540, 990, radii, phases, gaps, broken, cur=0)
draw_rings(c, 540, 990, radii, phases, gaps, broken, cur=9, final_active=True, pulse_tau=tau)  # gold last ring
```
- `won_flash=0..1` flashes the last ring white. Close its gap yourself by passing a smaller last gap.
- `reset=dict(u, ue, phases0, gaps0)` draws the loop-reset pass.
- The physics that goes with the board (collisions with arcs and the rounded gap ends) is in `../ring-escape/sim.py`.
- The settings to change are at the top of the file: ring count, radii, gaps, colours, widths, glow, pulse and shatter.

## Dependencies (tested)
- `../neon-kit`
- skia-python 144.1, Python 3.13.18

No photos or third-party images are used.
