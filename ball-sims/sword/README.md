# sword

The sword that orbits a ball, in two variants:
- **Small:** grip 18, blade 100, width 18 px. The crossguard and pommel are in the owner's colour.
- **BIG:** grip 28, blade 200, width 34 px. It has a gold guard and pommel, a gem in the owner's colour and a warm glow.

It also draws the swoosh trail: 9 past poses 0.014 s apart, each a translucent wedge, with a bright edge along the tip path. The same grip, blade and width numbers are used as the physics hitbox in `../sword-roulette`.

**Used in:** Sword Roulette (Nov 2026), for the fighters' swords, the roulette needle and the KO fly-off.

## Files
- `sword.py`: the module. `python sword.py` writes `preview.png` and `assets/`.
- `assets/sword_small_<color>.png` and `assets/sword_big_<color>.png`: transparent sprites at 2× scale, pointing right with the pommel on the left.
- `style.json` and `preview.png`.

## Reuse
```python
import sys; sys.path += ["ball-sims/style-kit", "ball-sims/sword"]
from sword import draw_sword, draw_trail, SMALL, BIG

# attached to a ball of radius 40 at (x, y), angle th (radians, y down => clockwise)
draw_trail(ctx, samples, big=False)                 # samples = [(x, y, th) now, 0.014 s ago, ...]
draw_sword(ctx, x, y, th, 40 - 2, False, (50, 198, 100))
draw_sword(ctx, x, y, th, 38, True, (236, 65, 68))  # BIG sword, red gem
draw_sword(ctx, x, y, th, 38, False, col, scale=0.8, alpha=0.5)
```
- In the video, small swords spin at 4.2 rad/s and the BIG sword at 2.4 rad/s. They reverse when two blades clash.
- To change the size, edit `SMALL` and `BIG` at the top of the file. If you change them for a game, change the physics dims too (`sword-roulette/settings.py`, `PHYSICS`) so the hitbox matches.

## Dependencies
- `../style-kit`
- `../glossy-ball`, only for the preview
- pycairo 1.29.2, Python 3.13.18

No photos or third-party images are included.
