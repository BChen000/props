# battle-audio

The channel's one sound kit, synthesized with numpy and scipy. There are no samples and nothing is downloaded.

**Music:**
- an A-minor chiptune battle loop at 152 BPM (Am–F–C–G), with a square-wave lead on every other phrase
- a suspense pulse for the roulette
- a C-major outro loop at 118 BPM
- a victory fanfare (chiptune, C major)
- `mountain_king()`: Grieg's "In the Hall of the Mountain King" (1875, public domain) as a B-minor synth arrangement that speeds up from 132 to 168 to 196 BPM, with kick, clap and hats
- a B-major brass win fanfare

**SFX:** roulette tick, ding, whoosh, sword "shing", metal clashes (small and big), sword hits (small and big), KO boom and final KO, taiko, slow-motion heartbeat and riser, pop, click, notification bell, kick, snare, hi-hat, crash, marble clack, glass shatter, power-up sweep, hand clap and a brass stab.

**Used in:**
- Sword Roulette (Nov 2026). Its cue sheet is `../sword-roulette/audio.py`.
- Ring Escape (Nov 2026). Its cue sheet is `../ring-escape/audio.py`. Every sound in that video comes from this kit.

## What changed in the Ring Escape update (Nov 2026)
- **Added** Ring Escape's sounds that had no match here: `clack()`, `shatter()`, `sweep_up()`, `clap()`, `brass_chord()`, `brass_fanfare()` and `mountain_king()`, plus `saw_pluck()` and `bass_pluck()`, which they use.
- **Ring Escape now uses this kit's** tick, ding, metal, boom, whoosh, heartbeat, kick, hat and crash instead of its own near-copies. Ring Escape's `K_*` gains keep each one at the loudness its mix was balanced with.
- **`riser()` was replaced** by Ring Escape's reverse whoosh: a one-octave noise band climbs from 250 to 3500 Hz in 24 cross-faded steps (the old one climbed in 8 audible steps) and swells as (t/dur)^2.2. At 3 s it has the same loudness as the old riser, so existing gains still fit. It sounds smoother, so Sword Roulette's slow-mo build-up changed too.
- **Loudness:** `master_and_write(..., limit=0.46)` adds a look-ahead limiter, and `loudnorm_filter()` returns the ffmpeg filter that brings the mix to -14 LUFS / -1 dBTP when you mux. Both Shorts use them. Without `limit`, `master_and_write()` behaves as before.
- Every other file in `assets/` is byte-identical to the previous version. The new sounds are exported last, so the older files keep their exact noise.

## Files
- `battle_audio.py`: the library. `python battle_audio.py` renders `assets/*.wav` and `preview.png` (about 15 s).
- `assets/*.wav`: 32 mono 16-bit 44.1 kHz files (peaks capped at 0.99).
  - The 25 Sword Roulette sounds are at the volumes used in its mix.
  - The 7 Ring Escape sounds (`clack`, `shatter`, `sweep_up`, `clap`, `brass_stab`, `fanfare_brass`, `mountain_king`) are at a usable level; their mix gains are in `../ring-escape/audio.py`.
  - `mountain_king.wav` is a 16 s demo. In a video, call `mountain_king()` so the tempo ramp lands on your own timeline.
  - The loops are cut at the bar line, so the last hit's tail is trimmed by a few hundredths of a second.
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
ba.add_st(L, R, ba.riser(3.0, 0.22), 9.0)                   # slow-mo build-up
ba.add_st(L, R, ba.boom(0.75), 12.05)
ba.add_st(L, R, ba.shatter(0.42, seed=101), 13.0, pan=0.3)  # glass break
L += music; R += music
ba.master_and_write(L, R, "audio.wav", limit=0.46)          # peak-normalise, tanh, limiter, 0.4 s fade
af = ba.loudnorm_filter("audio.wav")                        # -14 LUFS, -1 dBTP, linear gain
# ffmpeg -i video.mp4 -i audio.wav -map 0:v -map 1:a -c:v copy -af "<af>" -ar 48000 -c:a aac -b:a 192k out.mp4
```
- Mountain King music: `ba.mountain_king(L, R, tau_final, tau_slow, tau_cut, t0=0.0)`. It speeds up from 132 to 168 BPM until `tau_final`, then to 196 BPM until `tau_slow` (with a doubled lead and a kick on every beat), and stops at `tau_cut`. Times are in seconds after `t0`.
- To make an event sound slow-motion, use `ba.slowdown(x, 1 / rate)`, capped at 1.9.
- If you only need the sounds in an editor, use the files in `assets/`.

## Dependencies (tested)
- Python 3.13.18
- numpy 2.5.3
- scipy 1.18.1
- ffmpeg 6.1.1, only for `loudnorm_filter()`
- pycairo 1.29.2 and the Poppins font (see `../style-kit`), only for `preview.png`

No recorded audio or third-party samples are included. If a video ever needs a licensed or downloaded sound, keep it out of this repo (for example in a local `media/` folder next to that video's build that isn't committed) and note its source and licence in the video's README.
