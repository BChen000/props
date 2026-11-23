"""Ring Escape cue sheet: places ../battle-audio sounds on the video timeline and masters to WAV.

Every sound comes from the channel's one sound kit, battle_audio.py: tick, ding, metal, boom,
whoosh, riser, heartbeat, kick, hat and crash, plus the Ring Escape additions (clack, shatter,
sweep_up, clap, brass_chord, brass_fanfare, mountain_king).
The K_* factors keep each sound at the loudness the Ring Escape mix was balanced with (RMS-matched
to the sounds the posted video used).

  python audio.py out/audio.wav
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(_HERE, "..", "battle-audio"))
import battle_audio as ba  # noqa: E402

import settings as S  # noqa: E402
from timeline import Race  # noqa: E402

CHIME_NOTES = [71, 74, 76, 78, 81, 83, 86, 88, 90]   # ring 1..9 break chime: B minor pentatonic, rising
FINAL_RING_CHORD = (47, 54, 59, 62)                  # B minor brass stab when the last ring becomes active
K_TICK, K_KICK, K_HEART, K_CRASH = 1.005, 1.103, 1.073, 1.896
K_BOOM_START, K_BOOM_FINAL, K_BOOM_WIN, K_BOOM_NEAR = 0.810, 0.921, 1.022, 0.515
K_WHOOSH_UP, K_WHOOSH_NEAR, K_WHOOSH_DOWN = 0.774, 0.624, 0.522
K_METAL_FINAL, K_METAL_SMALL = 0.929, 0.963
K_DING_CHIME, K_DING_OCT, K_DING_SPARK = 1.727, 1.136, 0.823
K_RISER_SLOWMO, K_RISER_RESET = 0.846, 0.497


def build(race, out_path):
    ba.reset_rng()
    sr = ba.SR
    dur = race.duration
    L, R = np.zeros(int((dur + 1) * sr)), np.zeros(int((dur + 1) * sr))
    add = lambda x, t, g=1.0, pan=0.0: ba.add_st(L, R, x, t, g, max(-1.0, min(1.0, pan)))  # noqa: E731
    tau_w = race.tau_of(race.Tw)
    tau_final = race.tau_of(race.break_t[-2])
    tau_slow = race.tau_of(race.Tw - S.SLOWMO_FROM)
    tau_cut = tau_slow + 0.05

    ba.mountain_king(L, R, tau_final, tau_slow, tau_cut)

    add(ba.boom(1.0, 1.0), 0.0, 0.85 * K_BOOM_START)
    add(ba.whoosh(0.35, 1.0, 300, 3000), 0.0, 0.25 * K_WHOOSH_UP)
    add(ba.clack(1.0, 3800), 0.0, 0.25)

    last_tick = -1.0
    for (t, i, k, sp, xy) in race.walls:
        tau = race.tau_of(t)
        if tau > tau_w + 2.5 or tau - last_tick < 0.02:
            continue
        last_tick = tau
        g = 0.05 * min(1.0, sp / 700.0)
        if tau_slow <= tau < tau_w:
            g *= 1.6
        add(ba.tick(1.0, 1500 + 90 * k), tau, g * K_TICK, xy[0] / 520)
    last_cl = -1.0
    for (t, xy, sp, i, j) in race.mm:
        tau = race.tau_of(t)
        if sp < 60 or tau - last_cl < 0.015:
            continue
        last_cl = tau
        add(ba.clack(1.0, 3200 + 900 * ((i * 7 + j * 3) % 5) / 4), tau, 0.13 * min(1.0, sp / 900.0), xy[0] / 520)

    for (t, i, k, xy) in race.breaks[:-1]:
        tau = race.tau_of(t)
        note = CHIME_NOTES[k]
        add(ba.shatter(1.0, 100 + k), tau, 0.42, xy[0] / 600)
        add(ba.ding(1.0, ba.midi(note), 1.4), tau, 0.22 * K_DING_CHIME, xy[0] / 700)
        add(ba.ding(1.0, ba.midi(note + 12), 0.6), tau + 0.07, 0.07 * K_DING_OCT, -xy[0] / 700)
        for q, m in enumerate((note + 7, note + 12, note + 19)):
            add(ba.ding(1.0, ba.midi(m), 0.25), tau + 0.16 + 0.05 * q, 0.05 * K_DING_SPARK, 0.4)

    for (t, i, k, sp, xy) in race.ends:
        tau = race.tau_of(t)
        if tau > tau_w + 0.3:
            continue
        if k == race.NR - 1:
            g = 0.3 if tau_slow <= tau <= tau_w else 0.2
            add(ba.metal(1250, 0.6, 1.0), tau, g * K_METAL_FINAL, xy[0] / 520)
        else:
            add(ba.metal(1700, 0.3, 1.0), tau, 0.07 * K_METAL_SMALL, xy[0] / 520)
    for (t, i, xy) in race.near:
        tau = race.tau_of(t)
        add(ba.whoosh(0.4, 1.0, 600, 2600), tau - 0.05, 0.16 * K_WHOOSH_NEAR, xy[0] / 520)
        add(ba.boom(1.0, 0.35), tau, 0.25 * K_BOOM_NEAR)

    add(ba.boom(1.0, 1.3), tau_final, 0.8 * K_BOOM_FINAL)
    add(ba.brass_chord(FINAL_RING_CHORD, 1.1, 1.0), tau_final, 0.5)
    add(ba.sweep_up(0.5, 1.0, 300, 1400), tau_final + 0.35, 0.12)
    hb_t = tau_final + 1.2
    while hb_t < tau_slow:
        add(ba.heartbeat(1.0), hb_t, 0.18 * K_HEART)
        hb_t += 0.86 - 0.25 * min(1.0, (hb_t - tau_final) / max(0.1, tau_slow - tau_final))

    add(ba.whoosh(0.35, 1.0, 2000, 300), tau_slow - 0.05, 0.22 * K_WHOOSH_DOWN)
    hb = tau_slow + 0.05
    while hb < tau_w - 0.2:
        add(ba.heartbeat(1.0), hb, 0.55 * K_HEART)
        hb += 0.62
    add(ba.riser(max(0.3, tau_w - tau_slow), 1.0), tau_slow, 0.12 * K_RISER_SLOWMO)

    add(ba.boom(1.0, 1.6), tau_w, 1.0 * K_BOOM_WIN)
    add(ba.crash(1.0, 1.8), tau_w, 0.16 * K_CRASH)
    add(ba.brass_fanfare(1.0), tau_w, 1.0)
    rng = np.random.default_rng(3)
    for q in range(40):
        d = rng.uniform(0.0, 1.6)
        add(ba.clack(1.0, rng.uniform(2500, 6000)), tau_w + d, 0.03 * (1 - d / 1.8), rng.uniform(-0.8, 0.8))

    tau_reset = race.n_race / S.FPS
    rlen = dur - tau_reset + 0.12
    add(ba.riser(rlen, 1.0, 250, 3500), dur - rlen, 0.3 * K_RISER_RESET)
    add(ba.sweep_up(rlen, 1.0, 200, 900), dur - rlen, 0.05)

    n = int(dur * sr)
    ba.master_and_write(L[:n], R[:n], out_path, drive=1.33, ceiling=0.5, end_fade=0.0, limit=0.46)
    return out_path


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(S.OUT_DIR, "audio.wav")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    build(Race(), out)
    print("wrote", out)
