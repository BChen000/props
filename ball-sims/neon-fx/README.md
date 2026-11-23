# neon-fx

The particle and camera effects of the navy-and-neon look, drawn with skia-python:
- `burst()`: 18 particles in the breaker's colour when a marble breaks a ring (0.7 s)
- `sparks()`: 5 small white sparks on a hard marble-on-marble hit (0.3 s)
- `edge_sparks()`: 9 gold sparks and a soft glow when a marble clips a gap edge, i.e. a near miss (0.45 s)
- `shockwave()`: a gold ring expanding from the winner (0.6 s)
- `confetti()`: 150 spinning pieces in the marble colours plus white and gold, bursting from the winner and falling (2.6 s)
- `start_ring()`: a white ring bursting out of the centre on frame 0 (0.5 s)
- `shake()`: the screen-shake offset from recent ring breaks and the win

Every effect is stateless. You give it the event's position, its age in seconds and a seed, and it draws that moment, so frames can be rendered in any order or in parallel. The randomness comes from `neon_kit.hrand()`.

The slow-motion vignette isn't here. Both looks share the one in `../battle-fx` (`draw_slowmo_vignette_skia()`).

This is the navy counterpart of `../battle-fx`'s particles. A side-by-side comparison in Nov 2026 rated battle-fx's versions stronger for most effects (richer bursts, sparks that are easier to see on a phone). These are kept as part of the navy look, so Ring Escape rebuilds exactly as posted.

**Used in:** Ring Escape (Nov 2026).

## Files
- `neon_fx.py`: the module. `python neon_fx.py` writes `preview.png`.
- `style.json`: counts, speeds, lifetimes, sizes and colours of every effect.
- `preview.png`: each effect frozen at one moment, with its age.

## Reuse
```python
import sys; sys.path += ["ball-sims/neon-kit", "ball-sims/neon-fx"]
import neon_fx as fx
sx, sy = fx.shake([(t - bt, bt) for bt in break_times], win_age)   # translate the arena layer by this
fx.burst(canvas, x, y, breaker_rgb, t - bt, seed=bt)                # age in sim time: slows in slow motion
fx.sparks(canvas, x, y, t - hit_t, seed=hit_t)                       # only for hits faster than SPARK_MIN_SPEED
fx.edge_sparks(canvas, x, y, t - edge_t, seed=edge_t)
fx.shockwave(canvas, win_x, win_y, tau - tau_win)                    # age in video time
fx.confetti(canvas, win_x, win_y, tau - tau_win, colors=[...])
fx.start_ring(canvas, 540, 990, tau)
```
- Ring Escape passes sim time for the burst, sparks and break shake, so they slow down in slow motion, and video time for the win effects, so they stay lively. It shows edge sparks only on the last ring.
- The settings to change are at the top of the file: lifetimes, spark speed threshold, gold colours, extra confetti colours and shake strength.

## Dependencies (tested)
- `../neon-kit`, and its DejaVu Sans Bold font for the preview labels only
- skia-python 144.1, Python 3.13.18

No photos or third-party images are used.
