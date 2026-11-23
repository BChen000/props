# neon-marble

The glossy marble of the navy-and-neon look, drawn with skia-python. Each marble has a soft offset shadow, a radial gradient (light at the top left, dark at the rim), a faint light arc on the lower right, a tilted specular highlight and a small sparkle. The module also draws:
- the motion trail (8 fading circles behind a fast marble)
- the pulsing gold ring around the crown holder, with a gold halo for the winner
- the dimmed losers after the win
- an optional centred label (HP, a number or a name) and a white hit flash

This is a **different look** from `../glossy-ball` (the purple-theme ball in pycairo, with a white rim and a label). The comparison kept both.

**Used in:** Ring Escape (Nov 2026), at r = 22 px with all 8 colours.

## Changes from the video
- Ring Escape's marbles (r = 22) render exactly as in the posted video.
- Sprites larger than the video size now get a wider transparent margin (0.9 r), so their shadow isn't cut off. In the video's code the shadow was clipped from about r = 30 up.
- The label and hit-flash options are new. Ring Escape doesn't use them.

## Files
- `neon_marble.py`: the module. `python neon_marble.py` writes `preview.png` and `assets/`.
- `assets/marble_<colour>.png`: the 8 marbles at 4× (r = 88 px, 336×336, transparent), for video editors.
- `style.json`: the gradient, shadow, highlight, trail, holder ring and glow values.
- `preview.png`: the 8 colours, the video size with trails, holder/winner/loser states, and the label and hit flash.

## Reuse
```python
import sys; sys.path += ["ball-sims/neon-kit", "ball-sims/neon-marble"]
from neon_kit import BALL_COLORS
from neon_marble import marble_sprite, draw_marble, draw_trail, draw_holder_ring
red = marble_sprite(BALL_COLORS["RED"])                 # build once per colour; r = 22 by default
draw_trail(canvas, past_centres, BALL_COLORS["RED"])    # newest first, every TRAIL_DT = 0.011 s
draw_holder_ring(canvas, x, y, tau, winner_glow=False)  # tau = video time, for the pulse
draw_marble(canvas, red, x, y)                          # dim=True for a loser after the win
big = marble_sprite(BALL_COLORS["BLUE"], r=40)
draw_marble(canvas, big, x, y, label="85", flash=0.6, r=40)
```
- `marble_sprite(rgb, r=22, big=1.0, pad=None)` returns `(skia.Image, half_size)`. `big` multiplies the radius.
- The settings to change are at the top of the file: radius, gradient strengths, shadow, trail, holder ring, glow, dim and flash.

## Dependencies (tested)
- `../neon-kit` (colours and the DejaVu Sans Bold label font)
- skia-python 144.1, Python 3.13.18

No photos or third-party images are used. If a video needs a face or picture on a marble, keep that image out of this repo (for example in a local `faces/` folder that isn't committed), and draw it inside `marble_sprite()`, clipped to the circle, after the gradient and before the highlight.
