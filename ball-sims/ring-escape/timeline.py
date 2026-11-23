"""Ring Escape timeline: the race in sim time, mapped to video time.

- Loads the recorded race (assets/race_<SEED>.npz) or simulates it.
- Rotates the whole race so the winner comes to rest at TARGET_REST_DEG.
- Sorts events into breaks, marble hits, wall bounces and gap-edge hits. Near misses are
  gap-edge hits on the last ring before the win.
- Builds the time map. The physics runs in sim time t; the video runs in video time tau at 30 fps.
  Up to the slow motion t == tau. Around the winning escape the rate ramps down to SLOWMO_RATE and
  back up. After CELEBRATE s the sim time freezes and RESET_FRAMES frames glide everything back to
  frame 0, so the video loops seamlessly.

  python timeline.py   -> frame count, duration, break and near-miss times in both clocks
"""
import json
import math
import os

import numpy as np

import settings as S
import sim

DT = S.DT


def _clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


class Race:
    def __init__(self):
        res = None
        if S.USE_RECORDED_RACE and os.path.exists(S.RACE_FILE):
            rec = sim.load(S.RACE_FILE)
            if rec["seed"] == S.SEED and rec["phys"] == repr(sorted(S.PHYS.items())):
                res = rec
        if res is None:
            res = sim.run()
        self.res = res
        self.P = res["P"].copy()
        self.PHI = res["PHI"].copy()
        self.radii = res["radii"]
        self.gaps = res["gaps"]
        self.NR = len(self.radii)
        self.winner = int(res["winner"])
        self.Tw = res["win_step"] * DT
        self.Tout = res["out_step"] * DT
        wp = self.P[-1, self.winner]
        delta = math.radians(S.TARGET_REST_DEG) - math.atan2(wp[1], wp[0])
        c, s = math.cos(delta), math.sin(delta)
        self.rot = np.array([[c, -s], [s, c]])
        self.P = self.P @ self.rot.T
        self.PHI = self.PHI + delta
        self.nsteps = len(self.P)
        self.breaks, self.mm, self.walls, self.ends = [], [], [], []
        for e in res["ev"]:
            typ = int(e[0])
            t = e[1] * DT
            xy = self.rot @ np.array([e[6], e[7]])
            if typ == sim.EV_BREAK:
                self.breaks.append((t, int(e[2]), int(e[3]), xy))
            elif typ == sim.EV_MM:
                self.mm.append((t, xy, e[4], int(e[2]), int(e[3])))
            elif typ == sim.EV_WALL:
                self.walls.append((t, int(e[2]), int(e[3]), e[4], xy))
            elif typ == sim.EV_END:
                self.ends.append((t, int(e[2]), int(e[3]), e[4], xy))
        self.break_t = [b[0] for b in self.breaks]
        self.final_on = self.break_t[-2]
        near = []
        for t, i, k, sp, xy in self.ends:
            if k == self.NR - 1 and self.final_on < t < self.Tw - 0.2:
                if not near or t - near[-1][0] > S.NEAR_MISS_GAP:
                    near.append((t, i, xy))
        self.near = near
        self.phi0 = self.PHI[0].copy()
        self._build_time_map()

    def _build_time_map(self):
        Tw = self.Tw
        t_slow0, t_slow1 = Tw - S.SLOWMO_FROM, Tw + S.SLOWMO_TO
        t_end = Tw + S.CELEBRATE
        r_min = S.SLOWMO_RATE
        dtau = 1.0 / S.FPS
        ts, rates = [], []
        t, rate = 0.0, 1.0
        while t < t_end:
            ts.append(t)
            rates.append(rate)
            target = r_min if t_slow0 <= t < t_slow1 else 1.0
            if target < rate:
                rate = max(target, rate - dtau / S.SLOWMO_RAMP_IN * (1 - r_min))
            else:
                rate = min(target, rate + dtau / S.SLOWMO_RAMP_OUT * (1 - r_min))
            t += rate * dtau
        self.n_race = len(ts)
        self.n_reset = S.RESET_FRAMES
        self.frame_t = np.array(ts)
        self.frame_rate = np.array(rates)
        self.n_frames = self.n_race + self.n_reset
        self.duration = self.n_frames / S.FPS

    # ------------------------------------------------------------------ queries
    def tau_of(self, t):
        """Video time of sim time t."""
        return float(np.interp(t, self.frame_t, np.arange(self.n_race) / S.FPS))

    def frame_state(self, fi):
        if fi < self.n_race:
            return dict(phase="race", t=float(self.frame_t[fi]), tau=fi / S.FPS, rate=float(self.frame_rate[fi]), u=0.0)
        u = (fi - self.n_race + 1) / (self.n_reset + 1)
        return dict(phase="reset", t=float(self.frame_t[-1]), tau=fi / S.FPS, rate=1.0, u=u)

    def pos(self, t):
        f = _clamp(t / DT, 0, self.nsteps - 1.0001)
        i0 = int(f)
        a = f - i0
        return self.P[i0] * (1 - a) + self.P[i0 + 1] * a

    def phi(self, t):
        f = _clamp(t / DT, 0, self.nsteps - 1.0001)
        i0 = int(f)
        a = f - i0
        return self.PHI[i0] * (1 - a) + self.PHI[i0 + 1] * a

    def n_broken(self, t):
        return sum(1 for b in self.break_t if b <= t)

    def holder(self, t):
        h = None
        for b in self.breaks:
            if b[0] <= t:
                h = b
        return h

    def counts(self, t):
        c = [0] * S.N_MARBLES
        for b in self.breaks:
            if b[0] <= t:
                c[b[1]] += 1
        return c

    def final_gap(self, t):
        g = self.gaps[-1]
        if t > self.Tw:
            x = _clamp((t - self.Tw) / 0.3)
            g *= 1 - x * x * (3 - 2 * x)
        return g


if __name__ == "__main__":
    r = Race()
    print(json.dumps(dict(n_frames=r.n_frames, duration=round(r.duration, 3), winner=S.NAMES[r.winner],
                          win_sim=round(r.Tw, 3), win_video=round(r.tau_of(r.Tw), 3),
                          breaks=[(round(b[0], 3), S.NAMES[b[1]], b[2] + 1, round(r.tau_of(b[0]), 3)) for b in r.breaks],
                          near_misses=[(round(n[0], 3), S.NAMES[n[1]], round(r.tau_of(n[0]), 3)) for n in r.near]),
                     indent=1))
