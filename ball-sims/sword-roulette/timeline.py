"""Everything time-related: roulette, sim-time mapping (slow-mo + hit-stop), text + status cues."""
import bisect
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
for _dep in ("style-kit", "glossy-ball", "sword", "roulette-spinner"):
    sys.path.append(os.path.join(_HERE, "..", _dep))

import settings as S  # noqa: E402
import sim  # noqa: E402
from roulette_spinner import Roulette  # noqa: E402

FPS = S.FPS
SEED = S.SEED
SPIN_START, SPIN_END = S.SPIN_START, S.SPIN_END
FLY_START, FLY_END = S.FLY_START, S.FLY_END
POP_START, POP_STEP = S.POP_START, S.POP_STEP
V_FIGHT = S.V_FIGHT
FIGHT_TXT = S.FIGHT_TXT
REVEAL_AFTER_FINAL = S.REVEAL_AFTER_FINAL
OUTRO = S.OUTRO
COLORS = S.COLORS
NAMES = S.NAMES
WHITE = (255, 255, 255)
YELLOW = (255, 214, 80)
PINK = (244, 114, 208)


class Timeline:
    def __init__(self, seed=SEED):
        self.res = res = sim.run(seed, post=6.0)
        self.P = res["P"]
        self.dt = res["dt"]
        self.states = res["states"]
        self.events = res["events"]
        self.chosen = res["chosen"]
        self.winner = res["winner"]
        self.n = len(NAMES)
        kills = [e for e in self.events if e["type"] == "kill"]
        self.kills = kills
        self.t_final = kills[-1]["t"]
        self._build_timemap()
        for e in self.events:
            e["v"] = self.v_of_s(e["t"])
        self.v_final = kills[-1]["v"]
        self.v_reveal = self.v_final + REVEAL_AFTER_FINAL
        self.v_end = self.v_reveal + OUTRO
        self.n_frames = int(round(self.v_end * FPS))
        # final duel starts when 2 remain
        self.v_duel = kills[-2]["v"] if len(kills) >= 2 else None
        self.duel_pair = None
        if len(kills) >= 2:
            dead = {e["j"] for e in kills[:-1]}
            self.duel_pair = [i for i in range(self.n) if i not in dead]
        self.v_slow = self.v_of_s(self.t_final - S.SLOWMO_FINAL[0])
        self.roulette = Roulette(
            self.chosen, [COLORS[n] for n in NAMES], center=(sim.CX, sim.CY), ring_r=sim.RING_R,
            start_angle=S.START_ANGLE, turns=S.SPIN_TURNS, spin_start=SPIN_START, spin_end=SPIN_END,
            fly_start=FLY_START, fly_end=FLY_END, pop_start=POP_START, pop_step=POP_STEP,
            glow_until=V_FIGHT + 0.3, ball_r=self.P["ball_r"],
            small_dims=self.P["small"], big_dims=self.P["big"], label=str(self.P["hp"]))
        self.ticks = self.roulette.ticks
        self._texts()

    # ---------------- sim-time mapping with slow motion ----------------
    def _rate(self, s):
        tf = self.t_final
        if tf - S.SLOWMO_FINAL[0] <= s < tf:
            return S.SLOWMO_FINAL[1]
        if tf <= s < tf + S.SLOWMO_AFTER[0]:
            return S.SLOWMO_AFTER[1]
        before, after, rate = S.SLOWMO_KO
        for e in self.kills[:-1]:
            if e["t"] - before <= s < e["t"] + after:
                return rate
        return 1.0

    def _build_timemap(self):
        dv = 1.0 / (FPS * 8)
        V, S_ = [V_FIGHT], [0.0]
        v, s = V_FIGHT, 0.0
        froze = False
        s_max = (len(self.states) - 2) * self.dt
        while s < s_max:
            if not froze and s >= self.t_final:
                # hit-stop freeze on the final blow
                s = self.t_final
                for _ in range(int(S.HITSTOP / dv)):
                    v += dv
                    V.append(v)
                    S_.append(s)
                froze = True
            v += dv
            s = min(s + self._rate(s) * dv, s_max)
            V.append(v)
            S_.append(s)
        self.V, self.S = V, S_

    def s_of_v(self, v):
        """Sim time shown at video time v."""
        if v <= V_FIGHT:
            return 0.0
        k = bisect.bisect_right(self.V, v) - 1
        if k >= len(self.V) - 1:
            return self.S[-1]
        a = (v - self.V[k]) / (self.V[k + 1] - self.V[k])
        return self.S[k] + a * (self.S[k + 1] - self.S[k])

    def v_of_s(self, s):
        """First video time showing sim time s."""
        k = bisect.bisect_left(self.S, s)
        k = min(k, len(self.V) - 1)
        return self.V[k]

    def rate_at_v(self, v):
        return self._rate(self.s_of_v(v)) if v >= V_FIGHT else 1.0

    # ---------------- sim state lookup ----------------
    def state(self, s):
        """Interpolated (x, y, th, hp, alive) lists at sim time s."""
        f = s / self.dt
        i = int(math.floor(f))
        i = max(0, min(i, len(self.states) - 2))
        a = min(max(f - i, 0.0), 1.0)
        x0, y0, t0, hp0, al0 = self.states[i]
        x1, y1, t1, _, _ = self.states[i + 1]
        n = self.n
        xs = [x0[k] + (x1[k] - x0[k]) * a for k in range(n)]
        ys = [y0[k] + (y1[k] - y0[k]) * a for k in range(n)]
        ts = [t0[k] + (t1[k] - t0[k]) * a for k in range(n)]
        return xs, ys, ts, list(hp0), list(al0)

    # ---------------- roulette ----------------
    def pointer_angle(self, v):
        return self.roulette.pointer_angle(v)

    def pointed_ball(self, v):
        return self.roulette.pointed_ball(v)

    # ---------------- on-screen text schedule ----------------
    def _texts(self):
        cn = NAMES[self.chosen]
        msgs = []   # (v0, v1, kind, payload)
        msgs.append((0.0, SPIN_END + 0.15, "plain", (S.INTRO_PROMPT, WHITE)))
        msgs.append((SPIN_END + 0.15, V_FIGHT + 0.6, "pop", (S.GOT_SWORD.format(name=cn), COLORS[cn])))
        big_dead_v = None
        for e in self.kills:
            if e["j"] == self.chosen:
                big_dead_v = e["v"]
        d_end = self.v_duel if self.v_duel else self.v_final
        if big_dead_v and big_dead_v < d_end:
            msgs.append((V_FIGHT + 0.6, big_dead_v, "plain", (S.FIGHT_PROMPT, WHITE)))
            msgs.append((big_dead_v, d_end, "plain", (S.AFTER_BIG_DOWN_PROMPT, WHITE)))
        else:
            msgs.append((V_FIGHT + 0.6, d_end, "plain", (S.FIGHT_PROMPT, WHITE)))
        if self.v_duel:
            a, b = self.duel_pair
            if b == self.chosen:
                a, b = b, a
            msgs.append((self.v_duel, self.v_final, "duel",
                         ((NAMES[a], COLORS[NAMES[a]]), (NAMES[b], COLORS[NAMES[b]]))))
        kill_msgs = []
        for e in self.kills:
            vn = NAMES[e["j"]]
            dur = 1.7 if e is not self.kills[-1] else REVEAL_AFTER_FINAL
            kill_msgs.append((e["v"], e["v"] + dur, "pop", (S.OUT_MSG.format(name=vn), COLORS[vn])))
        self.msgs = msgs
        self.kill_msgs = kill_msgs

    def bottom_text(self, v):
        if v >= self.v_reveal:
            return None
        for m in reversed(self.kill_msgs):
            if m[0] <= v < m[1]:
                return m
        for m in reversed(self.msgs):
            if m[0] <= v < m[1]:
                return m
        return None

    def status(self, v):
        """(left text, (right text, right colour))"""
        left = S.STATUS_LEFT.format(n=self.n - sum(1 for e in self.kills if e["v"] <= v))
        if v < SPIN_START:
            right = (S.STATUS_PICK, PINK)
        elif v < SPIN_END:
            right = (S.STATUS_SPIN, YELLOW)
        elif v < V_FIGHT:
            right = (S.STATUS_GOT, YELLOW)
        elif self.v_duel is not None and v >= self.v_reveal:
            right = (S.STATUS_WIN, YELLOW)
        elif self.v_duel is not None and v >= self.v_duel:
            right = (S.STATUS_DUEL, YELLOW)
        else:
            right = (S.STATUS_FIGHT, PINK)
        return left, right

    def win_subtitle(self):
        w = self.winner
        if w == self.chosen:
            return S.WIN_SUB_BIG
        if any(e["i"] == w and e["j"] == self.chosen for e in self.kills):
            return S.WIN_SUB_KILLER
        return S.WIN_SUB_SURVIVOR


if __name__ == "__main__":
    tl = Timeline()
    print("chosen", NAMES[tl.chosen], "winner", NAMES[tl.winner])
    print("final blow v", round(tl.v_final, 2), "reveal", round(tl.v_reveal, 2), "end", round(tl.v_end, 2),
          "frames", tl.n_frames)
    if tl.v_duel:
        print("duel v", round(tl.v_duel, 2), [NAMES[i] for i in tl.duel_pair])
    print("ticks", len(tl.ticks))
    for e in tl.kills:
        print("KO", NAMES[e["j"]], "by", NAMES[e["i"]], "sim", round(e["t"], 2), "video", round(e["v"], 2))
