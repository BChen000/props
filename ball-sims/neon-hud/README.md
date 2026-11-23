# neon-hud

The on-screen overlay of the navy-and-neon look, drawn with skia-python:
- **Colour chips:** a 2×4 grid of pills, each with a colour dot, the name and a gold count badge. The leader's chip gets a gold outline, a glow and a small crown. A chip pops when its colour scores, and the losers' chips turn grey after the win.
- **Headline** in the centre slot: "PICK YOUR COLOR!", the big countdown number, a pulsing gold "LAST RING!", or "<NAME> WINS!". Each one pops in with a back-out ease.
- **Status line:** "7 RINGS LEFT  •  RED HAS THE CROWN", with the name part in the holder's colour.
- **Captions:** a big bottom caption and a small one under it.
- **Progress bar:** yellow, with a soft glow.

Every function takes plain values (texts, colours, counts, 0–1 animation amounts), so any game can drive it. It is the navy counterpart of `../color-chips` and the text parts of `../arena-board` and `../winner-card`, which use the purple look.

**Used in:** Ring Escape (Nov 2026). `../ring-escape/render.py` (`draw_hud`) shows when each piece appears.

## Files
- `neon_hud.py`: the module. `python neon_hud.py` writes `preview.png`.
- `style.json`: positions, sizes, colours and animation values.
- `preview.png`: a mid-race state (RED holds the crown and just scored, 7 rings left), with no arena.

## Reuse
```python
import sys; sys.path += ["ball-sims/neon-kit", "ball-sims/crown-icon", "ball-sims/neon-hud"]
import neon_hud as hud
from neon_kit import NAMES, BALL_COLORS, SMALLCAP
hud.draw_chips(canvas, NAMES, BALL_COLORS, counts=[1, 0, 1, 0, 1, 0, 0, 0], holder=0, pops=[0.6] + [0] * 7)
hud.draw_count(canvas, 7, scale=hud.pop_scale(age, 0.28, 1.45))     # age = s since the last score
hud.draw_status(canvas, "7 RINGS LEFT  •  ", "RED", BALL_COLORS["RED"])
hud.draw_captions(canvas, "RED BREAKS OUT!", BALL_COLORS["RED"], "BREAK A RING = TAKE THE CROWN", SMALLCAP)
hud.draw_bar(canvas, 0.3)
# after the win: draw_chips(..., winner=i) dims the others; draw_win(canvas, "CYAN", BALL_COLORS["CYAN"], scale=...)
```
- Other pieces: `draw_intro(c, line1, line2, alpha)`, `draw_last_ring(c, tau, scale, text)`.
- The chip grid is laid out for 8 colours. For fewer, pass fewer names; for more, change `CHIP_XS`/`CHIP_YS`.
- The settings to change are at the top of the file: chip positions and size, headline/status/caption rows, the bar and its colours. The text colours come from `../neon-kit`.

## Dependencies (tested)
- `../neon-kit` (colours, DejaVu Sans Bold) and `../crown-icon`
- skia-python 144.1, Python 3.13.18

No photos or third-party images are used.
