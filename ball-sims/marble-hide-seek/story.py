"""The hide-and-seek story: who goes where and when, the seeker's eyes, and the cues for text and sound.

Marble 0 is the seeker; marbles 1-6 are the hiders in settings.HIDERS order. Every move rolls along a smooth curve
(Catmull-Rom through waypoints) with a short speed-up and slow-down; hops are parabolas. The script below reads top to
bottom like the video: count and hide, "READY OR NOT!", check the spots one by one, the near miss, "TIME'S UP!", and
the hider nobody found rolls out and wins.

    build() -> dict(pos (frames, 7, 3), eyes (frames, 6): heading, openness, gaze x, gaze y, wide, unused,
                    events [(t, kind, data)], n_frames, colors)
"""
import math

import numpy as np

import settings as C
import layout as LY

ROLL_RAMP = 0.22


def catmull(points, n_per=24):
    p = [np.asarray(q, float) for q in points]
    if len(p) == 2:
        return np.linspace(p[0], p[1], max(2, int(np.linalg.norm(p[1] - p[0]) / 0.15)))
    p = [p[0] - (p[1] - p[0])] + p + [p[-1] + (p[-1] - p[-2])]
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        t = np.linspace(0, 1, n_per, endpoint=False)[:, None]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t +
                          (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(p[-2][None])
    return np.concatenate(out)


class Track:
    """One marble's motion as a list of segments; sample(t) -> (x, y, z)."""

    def __init__(self, xz):
        self.p = np.array(xz, float)
        self.t = 0.0
        self.segs = []

    def move(self, waypoints, speed, t0=None):
        t0 = self.t if t0 is None else max(t0, self.t)
        pl = catmull([self.p] + [np.array(w, float) for w in waypoints])
        d = np.linalg.norm(np.diff(pl, axis=0), axis=1)
        s = np.concatenate([[0], np.cumsum(d)])
        L = s[-1]
        ta = min(ROLL_RAMP, L / max(speed, 1e-6) / 2)
        T = L / speed + ta
        self.segs.append(("move", t0, t0 + T, pl, s, speed, ta))
        self.p = pl[-1].copy()
        self.t = t0 + T
        return self.t

    def hop(self, to_xz, height, dur, t0=None):
        t0 = self.t if t0 is None else max(t0, self.t)
        self.segs.append(("hop", t0, t0 + dur, self.p.copy(), np.array(to_xz, float), height))
        self.p = np.array(to_xz, float)
        self.t = t0 + dur
        return self.t

    def wait(self, t):
        self.t = max(self.t, t)
        return self.t

    def sample(self, t):
        y = LY.MAT_Y
        p = None
        for seg in self.segs:
            if t < seg[1]:
                break
            if seg[0] == "move":
                _, a, b, pl, s, v, ta = seg
                if t >= b:
                    p = pl[-1]
                    continue
                u = t - a
                T = b - a
                L = s[-1]
                if u < ta:
                    dist = 0.5 * v / ta * u * u
                elif u > T - ta:
                    r = T - u
                    dist = L - 0.5 * v / ta * r * r
                else:
                    dist = 0.5 * v * ta + v * (u - ta)
                p = np.array([np.interp(dist, s, pl[:, 0]), np.interp(dist, s, pl[:, 1])])
                return np.array([p[0], y, p[1]])
            if seg[0] == "hop":
                _, a, b, p0, p1, hh = seg
                if t >= b:
                    p = p1
                    continue
                u = (t - a) / (b - a)
                q = p0 + (p1 - p0) * u
                return np.array([q[0], y + 4 * hh * u * (1 - u), q[1]])
        if p is None:
            p = self.segs[0][3][0] if self.segs and self.segs[0][0] == "move" else self.p0
        return np.array([p[0], y, p[1]])


def build(log=print):
    names = [h[0] for h in C.HIDERS]
    ev = []
    seeker = Track(LY.SEEKER_START)
    seeker.p0 = np.array(LY.SEEKER_START, float)
    # hiders start in a fan in front of the seeker
    # who hides where comes from settings.HIDE_AT; everything below is keyed by the hiding spot
    at = {sp: nm for nm, sp in C.HIDE_AT.items()}
    assert sorted(at) == sorted(["tunnel", "stack", "corner", "base", "bridge", "pen"]), "HIDE_AT needs all six spots"
    assert sorted(at.values()) == sorted(names), "HIDE_AT needs every hider once"
    fan = {at["tunnel"]: -75, at["stack"]: -45, at["corner"]: -15, at["base"]: 15, at["bridge"]: 45, at["pen"]: 75}
    tr = {}
    for nm in names:
        a = math.radians(fan[nm])
        st = np.array(LY.SEEKER_START) + 6.6 * np.array([math.sin(a), math.cos(a)])
        tr[nm] = Track(st)
        tr[nm].p0 = st.copy()

    # ---- count and hide
    t_go = C.T_COUNT + 0.25
    for k in range(C.COUNT_FROM):
        ev.append((C.T_COUNT + k, "count", C.COUNT_FROM - k))
    sp = C.HIDE_SPEED
    hide_paths = {
        at["tunnel"]: [(-6.8, -3.0), (-7.6, -11.0), (-7.6, -20.0), (-7.6, -24.2), (-8.7, -25.0),
                       LY.SPOTS["tunnel"]["hide"]],
        at["stack"]: [(-9.5, 0.4), (-19.2, -1.0), (-19.3, -12.6), LY.SPOTS["stack"]["hide"]],
        at["corner"]: [(-6.4, 3.0), (-6.4, 14.6), (-12.8, 15.6), LY.SPOTS["corner"]["hide"]],
        at["base"]: [(-6.2, -4.6), (-6.4, -14.6), (-3.0, -15.6), LY.SPOTS["base"]["hide"]],
        at["bridge"]: [(7.6, 0.6), (14.6, 0.8), LY.SPOTS["bridge"]["hide"]],
        at["pen"]: [(6.0, -5.0), (6.0, -18.5), (6.0, -23.0)],
    }
    starts = {at["tunnel"]: 0.0, at["stack"]: 0.15, at["corner"]: 0.5, at["base"]: 0.75, at["bridge"]: 0.3,
              at["pen"]: 0.05}
    for nm in names:
        tr[nm].move(hide_paths[nm], sp, t0=t_go + starts[nm])
    tr[at["pen"]].hop(LY.SPOTS["pen"]["hide"], 4.2, 0.6)
    ev.append((tr[at["pen"]].t - 0.6, "hop", at["pen"]))
    hidden_by = max(tr[nm].t for nm in names)
    log(f"hiders all hidden by {hidden_by:.2f} s (ready at {C.T_READY:.2f} s)")

    # ---- ready or not
    t_ready = C.T_READY
    ev.append((t_ready, "ready", None))
    face = [(0.0, t_ready, math.pi),          # (t0, t1, heading) overrides; heading 0 = toward the camera
            (t_ready, t_ready + 1.05, 0.0)]   # turns round to face everyone: READY OR NOT!
    eyes_open = [(0.0, 0.0), (t_ready - 0.05, 0.0), (t_ready + 0.25, 1.15), (t_ready + 0.45, 1.0)]
    gaze = [(t_ready + 0.5, (-0.9, 0.0)), (t_ready + 0.75, (0.9, 0.1)), (t_ready + 1.0, (0.0, 0.0))]
    seeker.wait(t_ready + 1.05)
    v = C.SEEK_SPEED
    slots = {at["bridge"]: 10.0, at["pen"]: 6.0, at["corner"]: 2.0, at["stack"]: -2.0, at["tunnel"]: -6.0}
    found_order = []

    def found(nm, spot, look_at):
        t = seeker.t
        face.append((t - 0.35, t + C.LOOK_S, look_at))
        ev.append((t + 0.3, "found", nm))
        gaze.append((t + 0.25, (0.0, -0.15)))
        eyes_open.extend([(t + 0.25, 1.0), (t + 0.35, 1.25), (t + 0.85, 1.0)])
        tr[nm].wait(t + 0.3)
        tr[nm].hop(tr[nm].p, 2.6, 0.42)
        ev.append((t + 0.3, "hop", nm))
        found_order.append(nm)
        return t + C.LOOK_S

    # 1. under the bridge
    seeker.move([(6.0, -0.2), LY.SPOTS["bridge"]["look"]], v)
    t = found(at["bridge"], "bridge", LY.SPOTS["bridge"]["hide"])
    seeker.wait(t)
    t_leave = seeker.t
    seeker.move([(7.6, -2.4), (6.0, -8.0), (6.0, -16.0), LY.SPOTS["pen"]["look"]], v)
    tr[at["bridge"]].move([(14.6, 1.6), (14.6, 8.0), (14.6, 13.6), (12.4, 15.6), (slots[at["bridge"]], LY.FOUND_Z)],
                          15.0, t0=t_leave + 0.45)
    # 2. the pen: the hider jumps out over the wall
    t = found(at["pen"], "pen", LY.SPOTS["pen"]["hide"])
    tr[at["pen"]].hop((6.9, -19.6), 4.6, 0.62)
    ev.append((tr[at["pen"]].t - 0.62, "hop", at["pen"]))
    tr[at["pen"]].move([(6.2, -15.0), (6.0, -4.0), (6.6, 1.0), (slots[at["pen"]], LY.FOUND_Z)], 15.0)
    seeker.wait(tr[at["pen"]].t - 2.0)
    # 3. the arch: nobody there
    seeker.move([(6.0, -16.0), (6.0, -6.0), (6.6, -0.4), LY.SPOTS["arch"]["look"]], v)
    t = seeker.t
    face.append((t - 0.3, t + 1.1, LY.SPOTS["arch"]["hide"]))
    ev.append((t + 0.35, "empty", None))
    gaze.extend([(t + 0.3, (-0.9, 0.2)), (t + 0.6, (0.9, 0.2)), (t + 0.9, (-0.9, 0.2)), (t + 1.15, (0.0, 0.0))])
    seeker.wait(t + 1.2)
    # 4. the corner
    seeker.move([(2.0, 2.4), LY.SPOTS["corner"]["look"]], v)
    t = found(at["corner"], "corner", LY.SPOTS["corner"]["hide"])
    tr[at["corner"]].move([(-14.6, 14.6), (-6.0, 16.2), (slots[at["corner"]], LY.FOUND_Z)], 15.0, t0=t - 0.25)
    seeker.wait(t)
    # 5. behind the stack
    seeker.move([(-6.9, -4.0), LY.SPOTS["stack"]["look"]], v)
    t = found(at["stack"], "stack", LY.SPOTS["stack"]["hide"])
    tr[at["stack"]].move([(-19.3, -12.6), (-19.4, 2.0), (-19.4, 14.0), (-8.0, 16.4), (slots[at["stack"]], LY.FOUND_Z)],
                      16.0, t0=t - 0.25)
    seeker.wait(t)
    # 6. the tunnel: the hider rolls out of the far end
    seeker.move([(-7.2, -18.0), LY.SPOTS["tunnel"]["look"]], v)
    t = found(at["tunnel"], "tunnel", LY.SPOTS["tunnel"]["hide"])
    tr[at["tunnel"]].move([(-17.4, -25.0), (-19.3, -23.0), (-19.4, -17.0), (-19.4, 14.0), (-10.0, 16.4),
                     (slots[at["tunnel"]], LY.FOUND_Z)],
                    17.0, t0=t - 0.2)
    seeker.wait(t)
    # 7. the near miss: back past the tower, looking the wrong way, to where it counted
    seeker.move([(-6.6, -17.0), (-6.6, -8.0), (-5.6, -2.2), (-2.2, 0.4), (0.0, 0.6)], v * 0.85)
    t = seeker.t
    ev.append((t + 0.1, "where", None))
    face.append((t - 0.2, t + 2.6, 0.0))
    gaze.extend([(t + 0.2, (-0.95, 0.3)), (t + 0.6, (0.95, 0.3)), (t + 1.0, (-0.95, 0.3)), (t + 1.4, (0.95, 0.3)),
                 (t + 1.8, (0.0, 0.9)), (t + 2.4, (0.0, 0.0))])
    t_up = t + 2.5
    ev.append((t_up, "timesup", None))
    eyes_open.extend([(t_up, 1.0), (t_up + 0.2, 0.55), (t_up + 0.9, 0.55)])
    # 8. the winner, never found, rolls out from right behind the tower
    w = at["base"]
    tw = tr[w]
    tw.wait(t_up + 0.55)
    tw.move([(5.8, -15.0), (6.2, -10.5), (6.1, -4.0), (5.0, 3.6), (2.0, 7.6)], 12.0)
    ev.append((tw.t, "winner", w))
    tw.hop(tw.p, 2.2, 0.38)
    tw.hop(tw.p, 2.2, 0.38)
    ev.append((tw.t - 0.76, "hop", w))
    ev.append((tw.t - 0.38, "hop", w))
    face.append((t_up + 0.6, 99.0, "winner"))
    eyes_open.extend([(tw.t - 0.76, 0.55), (tw.t - 0.6, 1.3), (tw.t, 1.15)])
    gaze.append((t_up + 0.6, (0.0, -0.2)))
    t_end = tw.t + C.HOLD_S
    n_frames = int(math.ceil(t_end * C.FPS))

    # ---- sample every frame
    order = ["SEEKER"] + names
    tracks = [seeker] + [tr[nm] for nm in names]
    ft = np.arange(n_frames) / C.FPS
    pos = np.zeros((n_frames, len(order), 3))
    for k, trk in enumerate(tracks):
        for f, t in enumerate(ft):
            pos[f, k] = trk.sample(t)
    eyes = seeker_eyes(ft, pos, face, eyes_open, gaze, pos[:, 1 + names.index(w)])
    colors = [C.SEEKER_SRGB] + [h[1] for h in C.HIDERS]
    ev.sort(key=lambda e: e[0])
    check(pos, log)
    return dict(pos=pos, eyes=eyes, events=ev, n_frames=n_frames, colors=colors, names=order,
                found_order=found_order, t_end=t_end)


def seeker_eyes(ft, pos, face, opens, gaze, winner_pos):
    """Heading follows the direction of travel, or a 'face' override (a heading, a point to look at, or 'winner'),
    turning at most ~9 rad/s. Openness and gaze are piecewise-linear keys."""
    n = len(ft)
    sp = pos[:, 0, [0, 2]]
    vel = np.gradient(sp, axis=0) * C.FPS
    want = np.zeros(n)
    have = np.zeros(n, bool)
    for f in range(n):
        t = ft[f]
        ov = None
        for (a, b, tgt) in face:
            if a <= t < b:
                ov = tgt
        if ov is not None:
            if isinstance(ov, str):
                d = winner_pos[f, [0, 2]] - sp[f]
                want[f] = math.atan2(d[0], d[1])
            elif np.ndim(ov) == 0:
                want[f] = float(ov)
            else:
                d = np.asarray(ov, float) - sp[f]
                want[f] = math.atan2(d[0], d[1])
            have[f] = True
        elif np.linalg.norm(vel[f]) > 1.0:
            want[f] = math.atan2(vel[f, 0], vel[f, 1])
            have[f] = True
    head = np.zeros(n)
    cur = math.pi
    for f in range(n):
        if have[f]:
            d = (want[f] - cur + math.pi) % (2 * math.pi) - math.pi
            cur += max(-9.0 / C.FPS, min(9.0 / C.FPS, d))
        head[f] = cur
    ok = np.array([k[0] for k in opens])
    ov = np.array([k[1] for k in opens])
    srt = np.argsort(ok, kind="stable")
    openness = np.interp(ft, ok[srt], ov[srt])
    gk = sorted(gaze, key=lambda k: k[0])
    gt = np.array([k[0] for k in gk])
    gx = np.interp(ft, gt, [k[1][0] for k in gk])
    gy = np.interp(ft, gt, [k[1][1] for k in gk])
    return np.stack([head, openness, gx, gy, np.zeros(n), np.zeros(n)], 1)


def check(pos, log=print):
    """Warns about marbles inside blocks or overlapping each other."""
    n = pos.shape[1]
    bad = LY.blocked(pos[..., 0], pos[..., 2]) & (pos[..., 1] < LY.MAT_Y + 0.3)
    if bad.any():
        f, k = np.argwhere(bad)[0]
        log(f"warning: {bad.sum()} marble-frames inside blocks (first: frame {f}, marble {k} at {pos[f, k].round(2)})")
    worst = (9.0, 0, 0, 0)
    for f in range(len(pos)):
        d = np.linalg.norm(pos[f][:, None] - pos[f][None], axis=-1) + np.eye(n) * 9
        i, j = np.unravel_index(d.argmin(), d.shape)
        if d[i, j] < worst[0]:
            worst = (d[i, j], f, i, j)
    log(f"closest two marbles: {worst[0]:.2f} apart, touching at {2 * C.R:.2f} (frame {worst[1]}, "
        f"marbles {worst[2]} and {worst[3]})")
