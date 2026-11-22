# subscribe-cta

The end-screen call to action, with every time counted from the moment it appears:
- A red SUBSCRIBE pill with a white bell pops in at (540, 1090). It appears on the same frame as the winner announcement, because viewers often swipe away as soon as they see who won.
- At 0.55 s a mouse cursor glides in and taps the button at 1.05 s: the button squishes, a ripple spreads, the bell wobbles and ring lines flash.
- At 1.35 s a two-line prompt fades in: "What do you want to see next?" in yellow and "Tell me in the comments!" in white.

Everything sits inside the arena circle, above the area YouTube's Shorts UI covers.

**Used in:** Sword Roulette (Nov 2026), from 34.26 s to the end. Nothing in it is specific to ball sims, so you can move it to `shared/` if another channel uses it.

## Files
- `subscribe_cta.py`: the module. `python subscribe_cta.py` writes `preview.png` and `assets/`.
- `assets/subscribe_button.png`, `assets/cursor.png`, `assets/bell.png`: transparent sprites for editors.
- `style.json` and `preview.png`.

## Reuse
```python
import sys; sys.path += ["ball-sims/style-kit", "ball-sims/subscribe-cta"]
from subscribe_cta import draw_subscribe_cta
draw_subscribe_cta(ctx, video_now - v_reveal)                       # button, cursor, prompt
draw_subscribe_cta(ctx, age, next_lines=("Which game next?", "Comment below!"))
draw_subscribe_cta(ctx, age, next_lines=None)                       # button + cursor only
```
The settings to change (button position, size, label, colours, tap time, cursor path, prompt text and positions) are at the top of the file. The matching sounds (`click` and `bell`) are in `../battle-audio`.

## Dependencies
- `../style-kit`
- pycairo 1.29.2, Python 3.13.18
- Poppins ExtraBold and Bold

The bell and cursor are simple vector shapes drawn here. No YouTube logo or other third-party image is included.
