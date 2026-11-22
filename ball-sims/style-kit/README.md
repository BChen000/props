# style-kit

The shared look of the Marble Pop (formerly Fun House 67) ball-sim Shorts. It holds the canvas size, the six ball colours, the UI colours, the Poppins text helpers, easing curves and the rounded-rectangle helper. Every other `ball-sims` prop imports `kit.py`, so if you change a colour here, every prop picks it up.

**Used in:** Sword Roulette (Nov 2026). Its colours and fonts were matched to the channel's Musical Chairs Short, but that video wasn't made with this code.

## Files
- `kit.py`: the module. `python kit.py` checks the fonts and redraws `preview.png`.
- `get_fonts.py`: installs Poppins Regular, SemiBold, Bold, ExtraBold and Black.
- `style.json`: every value in the kit as hex or numbers.
- `preview.png`: the palette and type specimen.

## Reuse
```python
import sys; sys.path.append("ball-sims/style-kit")
from kit import BALL_COLORS, NAMES, text, rich_text, rounded_rect, paint_background, new_canvas, check_fonts

check_fonts()                                   # warns if a Poppins weight is missing
surf, ctx = new_canvas()                        # 1080x1920 ARGB surface + cairo context
paint_background(ctx)                           # purple -> black gradient
text(ctx, "6 LEFT", 320, 405, "xb", 40, (155, 217, 251))   # cap height centred on y=405
surf.write_to_png("frame.png")
```
- Font keys: `xb` ExtraBold 800, `blk` Black 900, `b` Bold 700, `sb` SemiBold 600, `r` Regular 400.
- `text(ctx, s, x, y, font, size, color, align="c"|"l"|"r", outline=RGB, ow=px, alpha, scale, shadow=(dx, dy, RGB, a))`.
- The settings to change are at the top of `kit.py`: `NAMES`, `BALL_COLORS` and the UI colour constants.

## Fonts
Poppins is free under the SIL Open Font License 1.1. You can get it from https://fonts.google.com/specimen/Poppins, from https://github.com/google/fonts/tree/main/ofl/poppins, or from npm as `@fontsource/poppins@5.3.0`. To install it, run `python get_fonts.py`. It tries Google Fonts first, then falls back to npm, converting the woff2 files to ttf with fontTools.

The reference renders were made on Linux, where fontconfig resolves names like "Poppins ExtraBold". On macOS, cairo's toy font API may pick a different face. `check_fonts()` measures text widths to catch that, so render in Linux (or Docker) if it warns.

## Dependencies (tested versions)
- Python 3.13.18
- pycairo 1.29.2 (cairo 1.18.0)
- Poppins fonts
- `get_fonts.py` fallback only: fonttools 4.67.0, brotli 1.2.1, Node 22.23.5 / npm 10.9.9

No photos or third-party images are included.
