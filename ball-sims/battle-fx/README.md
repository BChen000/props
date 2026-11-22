# battle-fx

The fight juice:
- **Clash:** a spark burst plus a flash where two blades meet.
- **Hit:** particles in the victim's colour. A BIG-sword hit adds a gold ring.
- **KO:** a 46-particle explosion with a shockwave ring and a white flash.
- **Damage numbers:** a floating yellow "-30" for big hits and a white "-15" for small ones.
- **Screen shake.**
- **Final-blow zoom:** 1.18× about the hit point, with a bump during the hit-stop.
- **Slow-motion vignette.**
- **Sword fly-off:** a KO'd ball's sword flies out, spins and falls.

Particles are pre-rolled from `random.Random(1000 + event_index)`, so a re-render is identical. Particle age runs on sim time, so bursts slow down in slow motion. Damage numbers run on video time, so they stay readable.

**Used in:** Sword Roulette (Nov 2026).

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
fx.draw_slowmo_vignette(ctx)
fx.draw_sword_flyoff(ctx, x_ko, y_ko, sword_angle, sim_now - t_ko, big, color)
```
The event format is the one produced by `../sword-roulette/sim.py`: `t` sim time, `v` video time, `type`, `x`, `y`, `big`.

## Dependencies
- `../style-kit`, `../sword`
- `../glossy-ball` and `../arena-board`, only for the preview
- pycairo 1.29.2, Python 3.13.18
- Poppins ExtraBold, for damage numbers

No photos or third-party images are included.
