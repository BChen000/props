# glossy-ball

The ball character: a glossy sphere with a white rim, a soft drop shadow and a specular highlight. It has a centred label (the HP number during the fight, the colour name on the winner) and an optional white hit flash. The fight size is r=40 and the winner size is r=100.

**Used in:** Sword Roulette (Nov 2026), for the fighters, the roulette ring and the winner.

## Files
- `glossy_ball.py`: the module. `python glossy_ball.py` writes `preview.png` and `assets/`.
- `assets/ball_<color>.png`: one transparent sprite per colour, r=80 (2× video size), with no label, for Manim, Algodoo or editors.
- `style.json` and `preview.png`.

## Reuse
```python
import sys; sys.path += ["ball-sims/style-kit", "ball-sims/glossy-ball"]
from glossy_ball import draw_ball
draw_ball(ctx, x, y, 40, (236, 65, 68), "100")                 # fight ball with HP
draw_ball(ctx, x, y, 40, (236, 65, 68), "85", flash=0.7)       # flash: 1 -> 0 over 0.16 s after a hit
draw_ball(ctx, 540, 875, 100, (50, 198, 100), "GREEN", label_size=48)   # winner
```
The settings to change are at the top of the file: `BALL_R`, the gradient lighten/darken amounts, the label outline and the flash strength. The colours live in `../style-kit/kit.py`.

## Faces or photos on balls
This prop never used photos, and none are included. If a video needs a face on a ball (for example the Final Form merge videos), keep the photo outside this repo, e.g. in a local `faces/` folder that isn't committed. Paint it inside `ctx.arc(x, y, r)` with `ctx.clip()` before the rim and specular are drawn, and pass the image path in at render time.

## Dependencies
- `../style-kit`
- pycairo 1.29.2, Python 3.13.18
- Poppins ExtraBold, for labels
