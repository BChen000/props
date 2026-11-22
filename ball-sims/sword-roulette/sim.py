"""Sword Roulette physics simulation (deterministic, seed-driven, pure Python).

Six balls bounce inside a circular arena. One ball (the roulette pick) carries a
BIG sword, the others small swords. Swords orbit their ball. A blade touching an
enemy ball deals damage + knockback; two blades touching clash (both reverse spin).
When few balls remain they steer toward each other (and slightly toward the centre).
Tune the numbers in settings.PHYSICS.
"""
import math
import random

import settings

CX, CY = settings.ARENA_CX, settings.ARENA_CY   # arena centre (px)
ARENA_R = settings.ARENA_R                      # drawn arena radius
WALL_R = ARENA_R - 8.0          # collision radius for ball centres' outer limit
RING_R = settings.RING_R        # roulette ring radius (start positions)
NAMES = settings.NAMES
N = len(NAMES)

DEFAULT = settings.PHYSICS


def ring_pos(i):
    a = -math.pi / 2 + i * (2 * math.pi / N)
    return CX + RING_R * math.cos(a), CY + RING_R * math.sin(a), a


def blade_seg(x, y, th, r, sw):
    c, s = math.cos(th), math.sin(th)
    a = r + sw["grip"]
    b = a + sw["blade"]
    return x + c * a, y + s * a, x + c * b, y + s * b


def pt_seg(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = ((px - ax) * dx + (py - ay) * dy) / L2 if L2 > 0 else 0.0
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    qx, qy = ax + t * dx, ay + t * dy
    return math.hypot(px - qx, py - qy), qx, qy


def seg_seg(p1x, p1y, q1x, q1y, p2x, p2y, q2x, q2y):
    """Closest points between two segments (Ericson). Returns dist, c1, c2."""
    d1x, d1y = q1x - p1x, q1y - p1y
    d2x, d2y = q2x - p2x, q2y - p2y
    rx, ry = p1x - p2x, p1y - p2y
    a = d1x * d1x + d1y * d1y
    e = d2x * d2x + d2y * d2y
    f = d2x * rx + d2y * ry
    c = d1x * rx + d1y * ry
    b = d1x * d2x + d1y * d2y
    denom = a * e - b * b
    s = 0.0
    if denom > 1e-9:
        s = (b * f - c * e) / denom
        s = 0.0 if s < 0 else (1.0 if s > 1 else s)
    t = (b * s + f) / e
    if t < 0:
        t = 0.0
        s = -c / a
        s = 0.0 if s < 0 else (1.0 if s > 1 else s)
    elif t > 1:
        t = 1.0
        s = (b - c) / a
        s = 0.0 if s < 0 else (1.0 if s > 1 else s)
    c1x, c1y = p1x + d1x * s, p1y + d1y * s
    c2x, c2y = p2x + d2x * t, p2y + d2y * t
    return math.hypot(c1x - c2x, c1y - c2y), c1x, c1y, c2x, c2y


def run(seed, P=None, record=True, chosen=None, post=0.0):
    P = P or DEFAULT
    rng = random.Random(seed)
    if chosen is None:
        chosen = rng.randrange(N)
    else:
        rng.randrange(N)  # keep RNG stream identical
    dt, r = P["dt"], P["ball_r"]
    S = P["speed"]
    x, y, vx, vy, th, om, hp, alive, sw = [], [], [], [], [], [], [], [], []
    for i in range(N):
        px, py, a = ring_pos(i)
        x.append(px)
        y.append(py)
        ang = rng.uniform(0, 2 * math.pi)
        vx.append(S * math.cos(ang))
        vy.append(S * math.sin(ang))
        s = P["big"] if i == chosen else P["small"]
        sw.append(s)
        th.append(a + math.pi if i == chosen else a)  # big points inward, small outward
        om.append(s["omega"] * (1 if rng.random() < 0.5 else -1))
        hp.append(P["hp"])
        alive.append(True)
    hit_cd = {}
    clash_cd = {}
    events = []
    states = []
    t = 0.0
    step = 0
    relax_k = math.exp(-dt / P["relax"])
    winner = None
    while t < P["max_time"]:
        if record:
            states.append((tuple(x), tuple(y), tuple(th), tuple(hp), tuple(alive)))
        live = [i for i in range(N) if alive[i]]
        if len(live) <= 1:
            if winner is None:
                winner = live[0] if live else -1
                end_t = t + post
            if t >= end_t or not live:
                break
            i = live[0]
            x[i] += vx[i] * dt
            y[i] += vy[i] * dt
            th[i] += om[i] * dt
            dx, dy = x[i] - CX, y[i] - CY
            d = math.hypot(dx, dy)
            lim = WALL_R - r
            if d > lim:
                nx, ny = dx / d, dy / d
                x[i], y[i] = CX + nx * lim, CY + ny * lim
                vn = vx[i] * nx + vy[i] * ny
                if vn > 0:
                    vx[i] -= 2 * vn * nx
                    vy[i] -= 2 * vn * ny
            s = math.hypot(vx[i], vy[i]) or 1.0
            ns = S + (s - S) * relax_k
            vx[i] *= ns / s
            vy[i] *= ns / s
            t += dt
            continue
        # integrate
        for i in live:
            x[i] += vx[i] * dt
            y[i] += vy[i] * dt
            th[i] += om[i] * dt
        # walls
        for i in live:
            dx, dy = x[i] - CX, y[i] - CY
            d = math.hypot(dx, dy)
            lim = WALL_R - r
            if d > lim:
                nx, ny = dx / d, dy / d
                x[i], y[i] = CX + nx * lim, CY + ny * lim
                vn = vx[i] * nx + vy[i] * ny
                if vn > 0:
                    vx[i] -= 2 * vn * nx
                    vy[i] -= 2 * vn * ny
        # ball-ball
        for a_ in range(len(live)):
            i = live[a_]
            for b_ in range(a_ + 1, len(live)):
                j = live[b_]
                dx, dy = x[j] - x[i], y[j] - y[i]
                d = math.hypot(dx, dy)
                if 0 < d < 2 * r:
                    nx, ny = dx / d, dy / d
                    ov = (2 * r - d) / 2
                    x[i] -= nx * ov
                    y[i] -= ny * ov
                    x[j] += nx * ov
                    y[j] += ny * ov
                    rel = (vx[j] - vx[i]) * nx + (vy[j] - vy[i]) * ny
                    if rel < 0:
                        vx[i] += rel * nx
                        vy[i] += rel * ny
                        vx[j] -= rel * nx
                        vy[j] -= rel * ny
        segs = {i: blade_seg(x[i], y[i], th[i], r, sw[i]) for i in live}
        # clashes
        for a_ in range(len(live)):
            i = live[a_]
            for b_ in range(a_ + 1, len(live)):
                j = live[b_]
                key = (i, j)
                if clash_cd.get(key, -1) > t:
                    continue
                si, sj = segs[i], segs[j]
                d, c1x, c1y, c2x, c2y = seg_seg(*si, *sj)
                if d < (sw[i]["width"] + sw[j]["width"]) * 0.5:
                    om[i] = -om[i]
                    om[j] = -om[j]
                    dx, dy = x[j] - x[i], y[j] - y[i]
                    dd = math.hypot(dx, dy) or 1.0
                    nx, ny = dx / dd, dy / dd
                    pu = P["clash_push"]
                    vx[i] -= nx * pu
                    vy[i] -= ny * pu
                    vx[j] += nx * pu
                    vy[j] += ny * pu
                    clash_cd[key] = t + P["clash_cd"]
                    hit_cd[(i, j)] = max(hit_cd.get((i, j), -1), t + 0.12)
                    hit_cd[(j, i)] = max(hit_cd.get((j, i), -1), t + 0.12)
                    events.append(dict(t=t, type="clash", i=i, j=j,
                                       x=(c1x + c2x) / 2, y=(c1y + c2y) / 2,
                                       big=(i == chosen or j == chosen)))
        # hits
        for i in live:
            if not alive[i]:
                continue
            ax, ay, bx, by = segs[i]
            hw = sw[i]["width"] * 0.5
            for j in live:
                if j == i or not alive[j]:
                    continue
                if hit_cd.get((i, j), -1) > t:
                    continue
                d, qx, qy = pt_seg(x[j], y[j], ax, ay, bx, by)
                if d < r + hw:
                    dmg = sw[i]["dmg"]
                    hp[j] = max(0, hp[j] - dmg)
                    dx, dy = x[j] - x[i], y[j] - y[i]
                    dd = math.hypot(dx, dy) or 1.0
                    k = sw[i]["knock"]
                    vx[j] += dx / dd * k
                    vy[j] += dy / dd * k
                    hit_cd[(i, j)] = t + P["hit_cd"]
                    # contact point on the victim's rim, toward the blade
                    ex, ey = qx - x[j], qy - y[j]
                    el = math.hypot(ex, ey) or 1.0
                    events.append(dict(t=t, type="hit", i=i, j=j, dmg=dmg,
                                       x=x[j] + ex / el * r, y=y[j] + ey / el * r,
                                       big=(i == chosen), hp=hp[j]))
                    if hp[j] <= 0:
                        alive[j] = False
                        events.append(dict(t=t, type="kill", i=i, j=j, x=x[j], y=y[j],
                                           big=(i == chosen), victim_big=(j == chosen)))
        # gentle hunting: steer velocity toward the nearest enemy (more as fewer remain)
        nl = sum(alive)
        sk = P["seek"].get(nl, 0.0) * dt
        if sk > 0:
            for i in live:
                if not alive[i]:
                    continue
                best, bd = None, 1e18
                for j in live:
                    if j != i and alive[j]:
                        d2 = (x[j] - x[i]) ** 2 + (y[j] - y[i]) ** 2
                        if d2 < bd:
                            best, bd = j, d2
                if best is None:
                    continue
                # aim between the enemy and the arena centre so fights don't hug the wall
                tx = 0.7 * x[best] + 0.3 * CX
                ty = 0.7 * y[best] + 0.3 * CY
                want = math.atan2(ty - y[i], tx - x[i])
                cur = math.atan2(vy[i], vx[i])
                diff = (want - cur + math.pi) % (2 * math.pi) - math.pi
                rot = max(-sk, min(sk, diff))
                c, s_ = math.cos(rot), math.sin(rot)
                vx[i], vy[i] = vx[i] * c - vy[i] * s_, vx[i] * s_ + vy[i] * c
        # speed relaxation
        for i in live:
            if not alive[i]:
                continue
            s = math.hypot(vx[i], vy[i])
            if s < 1e-6:
                ang = rng.uniform(0, 2 * math.pi)
                vx[i], vy[i] = S * math.cos(ang), S * math.sin(ang)
                continue
            ns = S + (s - S) * relax_k
            vx[i] *= ns / s
            vy[i] *= ns / s
        t += dt
        step += 1
    kills = [e for e in events if e["type"] == "kill"]
    fight_end = kills[-1]["t"] if kills and winner is not None else t
    return dict(seed=seed, chosen=chosen, winner=winner, duration=fight_end, events=events,
                states=states, dt=dt, P=P)


def summary(res):
    ch = res["chosen"]
    kills = [e for e in res["events"] if e["type"] == "kill"]
    big_kills = sum(1 for e in kills if e["i"] == ch)
    order = [(round(e["t"], 2), NAMES[e["j"]], NAMES[e["i"]]) for e in kills]
    big_death = next((e["t"] for e in kills if e["j"] == ch), None)
    return dict(seed=res["seed"], chosen=NAMES[ch], winner=NAMES[res["winner"]] if res["winner"] is not None and res["winner"] >= 0 else None,
                big_won=res["winner"] == ch, big_kills=big_kills, duration=round(res["duration"], 2),
                order=order, big_death=big_death,
                hits=sum(1 for e in res["events"] if e["type"] == "hit"),
                clashes=sum(1 for e in res["events"] if e["type"] == "clash"))
