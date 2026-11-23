# battle-fx

The fight juice:
- **Clash:** a spark burst plus a flash where two blades meet.
- **Hit:** particles in the victim's colour. A BIG-sword hit adds a gold ring.
- **KO:** a 46-particle explosion with a shockwave ring and a white flash.
- **Damage numbers:** a floating yellow "-30" for big hits and a white "-15" for small ones.
- **Screen shake.**
- **Final-blow zoom:** 1.18× about the hit point, with a bump during the hit-stop.
- **Slow-motion vignette:** the frame edges darken as the playback slows down and clear again as it speeds up. The area around the action stays clear.
- **Sword fly-off:** a KO'd ball's sword flies out, spins and falls.

Particles are pre-rolled from `random.Random(1000 + event_index)`, so a re-render is identical. Particle age runs on sim time, so bursts slow down in slow motion. Damage numbers run on video time, so they stay readable.

**Used in:**
- Sword Roulette (Nov 2026): every effect.
- Ring Escape (Nov 2026): the slow-motion vignette only, through `draw_slowmo_vignette_skia()`. Its other effects are in `../neon-fx`.

## What changed in the Ring Escape update (Nov 2026)
The slow-motion vignette is now Ring Escape's design, because it read better on a phone. Before, a fixed 0.6 black vignette appeared inside the arena circle whenever the video was in slow motion. Now:
- its strength follows the playback rate, from clear at normal speed to full at the slowest rate (`vignette_strength(rate)`);
- it covers the whole frame, so the title dims too (the HUD is drawn on top and stays bright);
- it is clear within 35 % of `VIGNETTE_REACH` (760 px) around a focus point and reaches `VIGNETTE_ALPHA` (0.62) of near-black `#02040c` at the edge.

Calling `draw_slowmo_vignette(ctx)` with no `strength` still draws the original look. Nothing else in this prop changed, and `preview.png` is unchanged.

## Files
- `battle_fx.py`: the module. `python battle_fx.py` writes `preview.png`.
- `style.json` and `preview.png`.

## Reuse
```python
import sys; sys.path += ["ball-sims/" + d for d in ("style-kit", "sword", "battle-fx")]
import battle_fx as fx
parts = [fx.make_particles(e["type"], i, big=e["big"], color=victim_rgb) for i, e in enumerate(events)]  # once
# per frame, inside the arena transform:
fx.draw_burst(ctx, e["type"], e["x"], e["y"], sim_now - e["t"], parts[i], big=e["big"], color=victim_rgb)
fx.draw_damage_number(ctx, e["x"], e["y"], 30, video_now - e["v"], big=True)
dx, dy = fx.shake_offset(video_now, events)        # events need keys v, type ("hit"/"kill"), big
z, px, py = fx.zoom_cam(video_now, v_slow, v_final, (x_blow, y_blow))
fx.draw_slowmo_vignette(ctx, strength=fx.vignette_strength(rate), focus=(fx_x, fx_y))  # rate = playback rate
fx.draw_sword_flyoff(ctx, x_ko, y_ko, sword_angle, sim_now - t_ko, big, color)
```
The event format is the one produced by `../sword-roulette/sim.py`: `t` sim time, `v` video time, `type`, `x`, `y`, `big`.
- Vignette focus: Sword Roulette uses the point 80 % of the way from the arena centre to the nearest KO, and averages the strength over the last 0.12 s of video (`VIGNETTE_SMOOTH`) so it fades smoothly. Ring Escape uses the point 80 % of the way to the winner's exit.
- On a skia-python canvas, call `fx.draw_slowmo_vignette_skia(c, fx_x, fx_y, strength)`.

## Dependencies
- `../style-kit`, `../sword`
- `../glossy-ball` and `../arena-board`, only for the preview
- pycairo 1.29.2, Python 3.13.18
- Poppins ExtraBold, for damage numbers
- skia-python 144.1, only for `draw_slowmo_vignette_skia()` (imported when you call it)

No photos or third-party images are included.
