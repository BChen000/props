"""The hide-and-seek soundtrack, built from the channel's sound kit (../battle-audio, synthesized, seeded): clock
ticks for the countdown, a whoosh and ding for READY OR NOT!, Grieg's "In the Hall of the Mountain King" (public
domain) speeding up while the seeker searches, a ding that climbs with every marble found, an uh-oh for the empty
spot, a heartbeat for the last search, a buzzer for TIME'S UP!, then the brass fanfare, claps and confetti pops.
Rolling marbles add a soft felt rumble that follows their speed.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "battle-audio"))
import battle_audio as ba

import settings as C


def build(story, out_wav, log=print):
    ba.reset_rng(C.SOUND_SEED)
    SR = ba.SR
    dur = story["n_frames"] / C.FPS + 0.3
    n = int(dur * SR)
    L, Rr = np.zeros(n), np.zeros(n)
    ev = story["events"]
    t_ready = next(t for t, k, _ in ev if k == "ready")
    t_up = next(t for t, k, _ in ev if k == "timesup")
    finds = [t for t, k, _ in ev if k == "found"]
    # music: sneaking from just after READY, faster from the 4th find, cut at TIME'S UP
    t0 = t_ready + 0.75
    tau_final = (finds[3] if len(finds) > 3 else t_up - 4) - t0
    tau_cut = t_up - t0
    mL, mR = np.zeros(n), np.zeros(n)
    ba.mountain_king(mL, mR, tau_final, tau_cut, tau_cut, t0=t0, bpm=C.MUSIC_BPM)
    L += mL * C.MUSIC_GAIN
    Rr += mR * C.MUSIC_GAIN
    ba.add_st(L, Rr, ba.whoosh(0.5, 0.35, 400, 4000), 0.0)
    count_bed = ba.suspense_music(t_ready + 0.4, 120)
    count_bed *= np.minimum(1.0, (len(count_bed) - np.arange(len(count_bed))) / (0.3 * SR))
    ba.add_st(L, Rr, count_bed, 0.2, 0.32)
    ba.add_st(L, Rr, ba.pop(0.5, 700), 0.05)
    for t, k, v in ev:
        if k == "count":
            ba.add_st(L, Rr, ba.tick(0.9, 1900), t)
            ba.add_st(L, Rr, ba.pop(0.35, 520), t + 0.01)
        elif k == "ready":
            ba.add_st(L, Rr, ba.whoosh(0.55, 0.5, 300, 3500), t - 0.1)
            ba.add_st(L, Rr, ba.ding(0.45, 1568.0, 0.9), t)
        elif k == "found":
            i = finds.index(t)
            f = [1046.5, 1174.7, 1318.5, 1396.9, 1568.0, 1760.0][min(i, 5)]
            ba.add_st(L, Rr, ba.ding(0.5, f, 1.0), t)
            ba.add_st(L, Rr, ba.pop(0.55, 900), t)
            ba.add_st(L, Rr, ba.clap(0.25), t + 0.08, 1.0, 0.2)
        elif k == "hop":
            ba.add_st(L, Rr, ba.sweep_sine(260, 620, 0.16, 2.0) * ba.env_ad(int(0.16 * SR), 0.004, 0.06), t, 0.22)
        elif k == "empty":
            ba.add_st(L, Rr, ba.note("tri", 76, 0.16, 0.5), t)
            ba.add_st(L, Rr, ba.note("tri", 71, 0.3, 0.5), t + 0.18)
        elif k == "where":
            for q in range(3):
                ba.add_st(L, Rr, ba.heartbeat(0.9), t + 0.15 + q * 0.75)
        elif k == "timesup":
            t_win = next(tt for tt, kk, _ in ev if kk == "winner")
            ba.add_st(L, Rr, ba.riser(max(0.6, t_win - t - 0.9), 0.3), t + 0.8)
            bz = (ba.square(98, 0.7, 8) + 0.6 * ba.square(104, 0.7, 8)) * ba.env_ad(int(0.7 * SR), 0.01, 0.5)
            ba.add_st(L, Rr, ba.lowpass(bz, 2200), t, 0.55)
            ba.add_st(L, Rr, ba.boom(0.5), t)
        elif k == "winner":
            ba.add_st(L, Rr, ba.brass_fanfare(1.0), t, 0.9)
            tail = dur - (t + 1.6)
            if tail > 0.5:
                ol = ba.outro_loop(tail, 118)
                ol *= np.minimum(1.0, np.arange(len(ol)) / (0.4 * SR))
                ba.add_st(L, Rr, ol, t + 1.6, 0.45)
            ba.add_st(L, Rr, ba.crash(0.45, 1.6), t + 0.32)
            for q in range(6):
                ba.add_st(L, Rr, ba.clap(0.35), t + 0.5 + q * 0.18, 1.0, -0.3 + 0.12 * q)
            for q in range(8):
                ba.add_st(L, Rr, ba.pop(0.25, 600 + 90 * q), t + 0.05 + 0.04 * q, 1.0, -0.6 + 0.17 * q)
    # felt rumble from rolling marbles
    pos = story["pos"]
    sp = np.linalg.norm(np.gradient(pos[:, :, [0, 2]], axis=0), axis=-1) * C.FPS
    on = pos[:, :, 1] < C.MAT_T + C.R + 0.3
    inten = np.where(on, np.clip(sp / 14.0, 0, 1.4), 0.0)
    pan = np.clip(pos[:, :, 0] / 22.0, -1, 1)
    lw = (inten * (1 - pan) / 2).sum(1)
    rw = (inten * (1 + pan) / 2).sum(1)
    tf = (np.arange(len(lw)) + 0.5) / C.FPS
    ts = np.arange(n) / SR
    rumble = ba.lowpass(ba.noise(dur), 900)
    rumble = ba.highpass(rumble, 90)
    L += 0.06 * rumble[:n] * np.interp(ts, tf, lw)
    Rr += 0.06 * rumble[:n] * np.interp(ts, tf, rw)
    ba.master_and_write(L, Rr, out_wav, limit=0.46)
    log("soundtrack written")
