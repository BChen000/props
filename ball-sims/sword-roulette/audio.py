"""Sword Roulette soundtrack: the cue sheet that places battle-audio sounds on the timeline.

  python audio.py out/audio.wav
"""
import os
import sys

import numpy as np
from scipy.ndimage import uniform_filter1d

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(_HERE, "..", "battle-audio"))

import battle_audio as ba  # noqa: E402
import settings as S  # noqa: E402
import timeline as T  # noqa: E402


def build(tl, out_path):
    ba.reset_rng(ba.RNG_SEED)
    dur = tl.v_end + 0.3
    n = int(dur * ba.SR)
    L = np.zeros(n)
    Rr = np.zeros(n)
    music = np.zeros(n)

    # --- intro
    sus = ba.suspense_music(T.V_FIGHT)
    fade = np.ones(len(sus))
    fade[-int(0.25 * ba.SR):] = np.linspace(1, 0, int(0.25 * ba.SR))
    ba.add(music, sus * fade * 1.15, 0.0)
    ba.add_st(L, Rr, ba.whoosh(0.5, 0.35, 200, 2500), T.SPIN_START - 0.1)
    for i, tt in enumerate(tl.ticks):
        ba.add_st(L, Rr, ba.tick(0.55, 2200 + 30 * (i % 3)), tt)
    ba.add_st(L, Rr, ba.ding(0.55), T.SPIN_END)
    ba.add_st(L, Rr, ba.crash(0.25, 1.2), T.SPIN_END)
    ba.add_st(L, Rr, ba.whoosh(0.5, 0.6, 400, 5000), T.FLY_START)
    ba.add_st(L, Rr, ba.shing(0.6), T.FLY_END - 0.02)
    ba.add_st(L, Rr, ba.kick(0.8), T.FLY_END)
    order = [k for k in range(tl.n) if k != tl.chosen]
    for m, k in enumerate(order):
        ba.add_st(L, Rr, ba.pop(0.35, 700 + 90 * m), T.POP_START + m * T.POP_STEP, pan=0.0)
    ba.add_st(L, Rr, ba.taiko(0.9), T.FIGHT_TXT)
    ba.add_st(L, Rr, ba.crash(0.35, 1.6), T.FIGHT_TXT)

    # --- battle music (stops at the final blow)
    bm_len = tl.v_final - T.V_FIGHT
    bm = ba.battle_music(bm_len + 0.05)
    ba.add(music, bm * 0.85, T.V_FIGHT)

    # duck + low-pass the music during slow motion, cut at the final blow
    tv = np.arange(n) / ba.SR
    rate = np.array([tl.rate_at_v(v) if T.V_FIGHT <= v < tl.v_final + 0.6 else 1.0
                     for v in np.arange(0, dur, 0.01)])
    slow = np.interp(tv, np.arange(0, dur, 0.01), (rate < 0.5).astype(float))
    # smooth the slow-mo mask
    slow = uniform_filter1d(slow, size=int(0.12 * ba.SR))
    music_lp = ba.lowpass(music, 500, 2)
    music = music * (1 - slow) * (1 - 0.35 * slow) + music_lp * slow * 0.65
    cut = int(tl.v_final * ba.SR)
    fl = int(0.06 * ba.SR)
    music[cut:cut + fl] *= np.linspace(1, 0, fl)
    music[cut + fl:int(tl.v_reveal * ba.SR)] = 0

    # --- fight sfx
    clash_count = 0
    for e in tl.events:
        v = e["v"]
        pan = (e.get("x", 540) - 540) / 540 * 0.6
        r = tl.rate_at_v(v + 1e-4)
        sm = 1.0 / max(r, 0.45) if r < 0.9 else 1.0
        if e["type"] == "clash":
            x = ba.clash_sfx(e["big"], 0.42 if e["big"] else 0.3)
            clash_count += 1
        elif e["type"] == "hit":
            x = ba.hit_sfx(e["big"], 0.85 if e["big"] else 0.6)
        elif e["type"] == "kill":
            final = e is tl.kills[-1]
            x = ba.boom(1.0 if final else 0.75, 1.4 if final else 0.9)
            if final:
                ba.add_st(L, Rr, ba.crash(0.5, 2.2), v)
            ba.add_st(L, Rr, ba.pop(0.3, 520), v + 0.02, pan=pan)
        else:
            continue
        if sm > 1.01:
            x = ba.slowdown(x, min(sm, 1.9))
        ba.add_st(L, Rr, x, v, pan=pan)

    # final duel banner + slow-mo build-up
    if tl.v_duel:
        ba.add_st(L, Rr, ba.taiko(0.8), tl.v_duel + S.DUEL_BANNER_DELAY)
        ba.add_st(L, Rr, ba.whoosh(0.45, 0.35, 300, 3000), tl.v_duel + S.DUEL_BANNER_DELAY - 0.05)
    v_slow = tl.v_slow
    ba.add_st(L, Rr, ba.riser(tl.v_final - v_slow, 0.22), v_slow)
    hb = v_slow + 0.1
    while hb < tl.v_final - 0.3:
        ba.add_st(L, Rr, ba.heartbeat(0.55), hb)
        hb += 0.75

    # --- winner
    ba.add_st(L, Rr, ba.fanfare(), tl.v_reveal)
    for k_, dt in enumerate((0.0, 0.12, 0.25)):
        ba.add_st(L, Rr, ba.highpass(ba.noise(0.15), 2500) * ba.env_ad(int(0.15 * ba.SR), 0.001, 0.04) * 0.35,
               tl.v_reveal + dt, pan=(-0.6, 0.6, 0.0)[k_])
    ba.add_st(L, Rr, ba.pop(0.35, 600), tl.v_reveal + 0.02)
    ol = ba.outro_loop(tl.v_end - tl.v_reveal - 1.6 + 0.3)
    ofade = np.ones(len(ol))
    fi = int(0.6 * ba.SR)
    ofade[:fi] = np.linspace(0, 1, fi)
    fo = int(0.8 * ba.SR)
    ofade[-fo:] = np.linspace(1, 0, fo)
    ba.add(music, ol * ofade * 1.1, tl.v_reveal + 1.6)
    # subscribe tap
    tap = tl.v_reveal + 1.05
    ba.add_st(L, Rr, ba.click(0.6), tap)
    ba.add_st(L, Rr, ba.bell_ring(0.35), tap + 0.03)
    ba.add_st(L, Rr, ba.pop(0.25, 1100), tl.v_reveal + 1.35)

    L += music
    Rr += music
    st = ba.master_and_write(L, Rr, out_path)
    rms = np.sqrt(np.mean(st ** 2))
    print(f"wrote {out_path}: {len(st) / ba.SR:.2f}s, rms {rms:.3f}, clashes {clash_count}")


if __name__ == "__main__":
    tl = T.Timeline()
    build(tl, sys.argv[1] if len(sys.argv) > 1 else "audio.wav")
