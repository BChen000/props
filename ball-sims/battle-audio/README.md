# battle-audio

The whole soundtrack kit, synthesized with numpy and scipy. There are no samples and nothing is downloaded.

**Music:**
- an A-minor chiptune battle loop at 152 BPM (Am–F–C–G), with a square-wave lead on every other phrase
- a suspense pulse for the roulette
- a C-major outro loop at 118 BPM
- a victory fanfare

**SFX:** roulette tick, ding, whoosh, sword "shing", metal clashes (small and big), sword hits (small and big), KO boom and final KO, taiko, slow-motion heartbeat and riser, pop, click, notification bell, kick, snare, hi-hat and crash.

**Used in:** Sword Roulette (Nov 2026). Its cue sheet is `../sword-roulette/audio.py`.

## Files
- `battle_audio.py`: the library. `python battle_audio.py` renders `assets/*.wav` and `preview.png`.
- `assets/*.wav`: 25 mono 16-bit 44.1 kHz files, at the volumes used in the mix (peaks capped at 0.99). The loops are cut at the bar line, so the last hit's tail is trimmed by a few hundredths of a second.
- `preview.png`: a waveform sheet with each sound's length and purpose.
- `style.json`: tempos, keys, progressions, mix gains and mastering values.

## Reuse
```python
import sys; sys.path.append("ball-sims/battle-audio")
import numpy as np, battle_audio as ba
ba.reset_rng()                                   # same noise every run (seed 7)
n = int(40 * ba.SR); L, R = np.zeros(n), np.zeros(n); music = np.zeros(n)
ba.add(music, ba.battle_music(20.0) * 0.85, 6.0)            # music from 6 s
ba.add_st(L, R, ba.clash_sfx(big=True, vol=0.42), 7.3, pan=-0.2)
ba.add_st(L, R, ba.hit_sfx(big=False, vol=0.6), 8.1)
ba.add_st(L, R, ba.boom(0.75), 12.05)
L += music; R += music
ba.master_and_write(L, R, "audio.wav")           # peak-normalise, tanh soft clip, 0.4 s fade
```
- To make an event sound slow-motion, use `ba.slowdown(x, 1 / rate)`, capped at 1.9.
- If you only need the sounds in an editor, use the files in `assets/`.

## Dependencies (tested)
- Python 3.13.18
- numpy 2.5.3
- scipy 1.18.1
- pycairo 1.29.2, only for `preview.png`

No recorded audio or third-party samples are included.
