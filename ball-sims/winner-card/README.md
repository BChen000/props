# winner-card

The winner reveal:
- the winning ball glides to (540, 875) and grows from r=40 to r=100 in 0.55 s, inside a glow in its colour
- after 0.3 s its label switches from HP to the colour name
- a gold crown (from `../crown-icon`) drops on top, starting at 0.35 s
- 150 confetti pieces rain down
- the "<COLOR> WINS!" box pops into the bottom slot with a one-line story subtitle

**Used in:** Sword Roulette (Nov 2026), "GREEN WINS! Took down the BIG sword!". The look was matched to the winner screen of the channel's Musical Chairs Short.

## What changed in the Ring Escape update (Nov 2026)
The crown is now the shared one from `../crown-icon` (Ring Escape's design: gold gradient, band, jewels), drawn with `draw_crown_cairo()`. It replaced the flat crown that was drawn here. `CROWN_SCALE` (2.0) and `CROWN_DY` (-6 px per unit) keep it about the same size and keep its bottom edge where the old crown sat, so it is slightly larger (about 106 px wide on the winner instead of 84 px). `assets/crown.png` and `preview.png` were redrawn. Nothing else changed.

## Files
- `winner_card.py`: the module. `python winner_card.py` writes `preview.png` and `assets/crown.png`.
- `assets/crown.png`: the crown at 2×, transparent (240×180), for editors.
- `style.json` and `preview.png`.

## Reuse
```python
import sys; sys.path += ["ball-sims/" + d for d in ("style-kit", "glossy-ball", "winner-card")]
import winner_card as wc
confetti = wc.make_confetti(wc.default_palette())            # once
age = video_now - v_reveal
wc.draw_winner_reveal(ctx, age, x_at_reveal, y_at_reveal, (50, 198, 100), "GREEN", "10")
# ... chips / status / bottom slot ...
wc.draw_confetti(ctx, age, confetti)
wc.draw_winner_box(ctx, age, "GREEN WINS!", (50, 198, 100), "Took down the BIG sword!")
```
Draw order in the video: reveal, then chips/status, then confetti, then winner box, then `subscribe-cta`. Show the subscribe button on the same frame as the winner, so people who swipe right after the result still see it. The settings to change (target, timings, crown, box, confetti) are at the top of the file.

## Dependencies
- `../style-kit`, `../glossy-ball`, `../crown-icon`
- `../arena-board`, only for the preview
- pycairo 1.29.2, Python 3.13.18
- Poppins ExtraBold and Bold

No photos or third-party images are included.
