# color-chips

The scoreboard row under the title: six chips, 156×66 px each, starting at x=42 with 168 px spacing, at y=285. Each chip has:
- a colour dot and the colour name in Poppins Bold
- an HP bar with a white "damage trail" that holds for 0.18 s, then slides down until 0.68 s
- an optional border: white for the roulette pointer, gold for the big-sword owner, yellow for the winner
- an optional gold tag above it ("BIG SWORD")
- a pink strike and dimming when the ball is OUT

**Used in:** Sword Roulette (Nov 2026).

## Files
- `color_chips.py`: the module. `python color_chips.py` writes `preview.png`, which shows a tagged chip, a pointer border, a winner border, a damage trail and two OUT chips.
- `style.json` and `preview.png`.

## Reuse
```python
import sys; sys.path += ["ball-sims/style-kit", "ball-sims/color-chips"]
import color_chips as chips

hp, trail = chips.hp_with_trail(hits, now)        # hits = [(time, hp_before, hp_after), ...]
chips.draw_chips(ctx, [
    dict(name="RED", color=(236, 65, 68), hp=70, trail=85, dead=False,
         border=((255, 205, 70), 4), tag=dict(text="BIG SWORD", scale=1.0, dim=False)),
    dict(name="BLUE", color=(61, 131, 247), hp=0, trail=0, dead=True),
    # ... six chips, left to right
], max_hp=100)
```
The layout is built for 6 chips across 1080 px. For more balls, change `CHIP_STEP` and `CHIP_W` at the top of the file.

## Dependencies
- `../style-kit`
- pycairo 1.29.2, Python 3.13.18
- Poppins Bold and ExtraBold

No photos or third-party images are included.
