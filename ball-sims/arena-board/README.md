# arena-board

The game board for the ball-sim Shorts. It covers:
- the background gradient, the pink title (it shrinks to fit 860 px) and the rule line under it
- the round grid arena: centre (540, 1010), radius 445
- the glowing rim: lavender `#9182be` when calm, pink `#f06ec8` during the fight
- the status row at y=405, e.g. "6 LEFT" and "FIGHT!"
- the bottom message slot at y=1575, in plain, pop and duel styles
- the big centre banner ("FIGHT!", "FINAL DUEL!")

**Used in:** Sword Roulette (Nov 2026). Its layout was copied from the channel's Musical Chairs Short, which was made separately.

## Files
- `arena_board.py`: the module. `python arena_board.py` writes `preview.png` and `assets/`.
- `assets/board_blank_calm.png` and `assets/board_blank_fight.png`: 1080×1920 boards with no text, for Manim, Algodoo or video editors.
- `style.json` and `preview.png`.

## Reuse
```python
import sys; sys.path += ["ball-sims/style-kit", "ball-sims/arena-board"]
import arena_board as board

bg = board.make_background("SWORD ROULETTE", "One random ball gets the BIG sword!")  # static, build once
floor = board.make_floor()                                                         # static, build once
# every frame:
ctx.set_source_surface(bg, 0, 0); ctx.paint()
ctx.set_source_surface(floor, 0, 0); ctx.paint()
board.draw_rim(ctx, board.RIM_FIGHT, glow=1.0)          # glow=1.5 during slow motion
# ... draw balls/swords here (after the rim, so swords can poke over it) ...
board.draw_status(ctx, "6 LEFT", "FIGHT!", (244, 114, 208))
board.draw_message(ctx, "plain", ("Comment your color!", (255, 255, 255)), age, remaining, clock)
board.draw_message(ctx, "pop", ("YELLOW IS OUT!", (251, 201, 50)), age, remaining, clock)
board.draw_message(ctx, "duel", (("RED", (236, 65, 68)), ("GREEN", (50, 198, 100))), age, remaining, clock)
board.draw_banner(ctx, "FIGHT!", age, 1.0)              # size=104 for "FINAL DUEL!"
```
The settings to change are at the top of `arena_board.py`: the arena centre and radius, the grid, the rim colours, and the title, status and message positions.

## Dependencies
- `../style-kit`
- pycairo 1.29.2, Python 3.13.18
- Poppins ExtraBold, Black, Bold and Regular

No photos or third-party images are included.
