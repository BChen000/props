# crown-icon

The gold crown of the Marble Pop Shorts: three points, a vertical gold gradient, a dark-gold outline, a band, red-blue-red jewels and an optional soft glow. It is one design with two backends, so the skia props and the pycairo props draw the same crown:
- `draw_crown(c, x, y, s=1.0, alpha=1.0, glow=0.0)` for a skia-python canvas
- `draw_crown_cairo(ctx, x, y, s=1.0, alpha=1.0, glow=0.0)` for a pycairo context

The crown is centred at (x, y). At `s=1.0` it is about 56 px wide and 35 px tall. `glow` (0 to 2) adds a soft gold halo.

**Used in:**
- Ring Escape (Nov 2026): it hops onto the marble that broke the latest ring, sits in the holder's chip, and grows on the winner.
- The Ring Escape thumbnail (`../question-thumbnail`).
- Sword Roulette (Nov 2026), through `../winner-card`. Since this update it replaces winner-card's old flat crown, which the comparison found less finished at the sizes the videos use.

## Files
- `crown_icon.py`: the module. `python crown_icon.py` writes `preview.png`.
- `style.json`: the outline points, colours, band, jewels, glow and the sizes each video uses.
- `preview.png`: the sizes the videos use, drawn by both backends (skia on top, pycairo below).

## Reuse
```python
import sys; sys.path += ["ball-sims/crown-icon"]
from crown_icon import draw_crown, draw_crown_cairo
draw_crown(canvas, 540, 640, s=3.0, glow=1.6)          # skia: thumbnail size
draw_crown_cairo(ctx, 540, 760, s=1.9, alpha=0.8)      # pycairo: winner-card size, fading in
```
- The settings to change are at the top of the file: the gradient colours, band, outline, jewels and glow.
- Sizes used so far: 0.55 in a chip, 1.0 with glow 0.6 on a marble, 1.9 in the winner reveal, and 3.0 with glow 1.6 on a thumbnail.
- The two backends differ only in the glow: skia blurs a disc, and pycairo uses a radial gradient with the same profile.

## Dependencies (tested)
- Python 3.13.18
- skia-python 144.1, for `draw_crown()`
- pycairo 1.29.2, for `draw_crown_cairo()`
- Each backend is imported only when you call its function. `preview.png` needs both, plus `../neon-kit` and DejaVu Sans Bold for the labels.

No photos or third-party images are included. The crown is drawn from code, so there is no image file.
