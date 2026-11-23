# neon-kit

The shared look of the navy-and-neon Marble Pop Shorts (Crown Clash, Ring Escape). It holds the canvas size, the 8 marble colours, the UI colours, the DejaVu Sans Bold text helper, easing, colour helpers, a stable hash for stateless particles, and the navy grid background. The navy props (escape-rings, neon-marble, neon-hud, neon-fx, ring-escape, question-thumbnail) import `neon_kit.py`, so if you change a colour here, they all pick it up.

This is a **different look** from `../style-kit` (Sword Roulette: purple gradient, Poppins, pycairo). These props draw with **skia-python**.

**Used in:** Ring Escape (Nov 2026). Its colours were sampled from the channel's Crown Clash Short, but that video wasn't made with this code.

## Files
- `neon_kit.py`: the module. `python neon_kit.py` checks the font and redraws `preview.png`.
- `get_fonts.py`: installs DejaVu Sans Bold 2.37 (tested here: the downloaded file renders pixel-identically to the one used for the video).
- `style.json`: every value as hex or numbers.
- `preview.png`: palette, UI colours and type specimen.

## Reuse
```python
import sys; sys.path.append("ball-sims/neon-kit")
from neon_kit import NAMES, BALL_COLORS, make_background, draw_text, new_surface, to_bgra, YELLOW

surf = new_surface()                                   # 1080x1920 skia surface
c = surf.getCanvas()
c.drawImage(make_background(title="RING ESCAPE", subtitle="FIRST ONE OUT WINS"), 0, 0)
draw_text(c, "7 RINGS LEFT", 540, 512, 34, YELLOW, spacing=1.0)   # visual centre on y=512
surf.makeImageSnapshot().save("frame.png")             # or to_bgra(img) -> ffmpeg -pix_fmt bgra
```
- `draw_text(c, s, x, y, size, rgb, alpha=1, align="center"|"left"|"right", spacing=0, scale=1, maxw=None, shadow=0)`.
- `make_background(center=(540, 990), glow=..., grid_origin=None, title=None, subtitle=None)` returns a `skia.Image`.
- `hrand(*args)` gives a stable 0..1 number (for particles that render per frame without state).
- The settings to change are at the top of `neon_kit.py`: `NAMES`, `BALL_COLORS` and the UI colour constants.

## Fonts
The font isn't in the repo. DejaVu Sans is free (Bitstream Vera licence plus public-domain changes). You can get it from https://dejavu-fonts.github.io, from the 2.37 release on GitHub, from npm as `dejavu-fonts-ttf@2.37.3`, or on Debian/Ubuntu with `apt install fonts-dejavu-core`. To install it, run `python get_fonts.py`; it puts the font in your user font folder. `python get_fonts.py --local` puts it in `neon-kit/fonts/` instead; don't commit that folder. `typeface()` checks `fonts/` first, then the system, and warns if the advance width of "RING ESCAPE" at 100 px isn't 746 px.

The reference renders were made on Linux x86-64. On another OS or CPU, skia's anti-aliasing can differ by a few pixel levels.

## Dependencies (tested)
- Python 3.13.18
- skia-python 144.1 (`pip install skia-python==144.1`)
- DejaVu Sans Bold 2.37
- `get_fonts.py` fallback only: Node/npm

No photos or third-party images are included.
