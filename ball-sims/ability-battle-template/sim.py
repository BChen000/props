"""Deterministic 4-ball ability battle simulation (POWER BALLS).

Coordinates are arena-local pixels, 0..AS on both axes. One random.Random(seed) drives everything that
affects the outcome, and the physics runs at a fixed step, so a seed always replays the same fight.
Cosmetic effects (particles, sparks) live in render.py with their own RNG and never change the result.
"""
import math
import random

import settings as S

AS = S.ARENA
R = S.BALL_R
DT = S.DT
BASE_SPEED = S.BASE_SPEED
KNOCK = S.KNOCK
RELAX = S.RELAX
MAX_LEVEL = S.MAX_LEVEL
NAMES = S.NAMES
P = dict(S.ABILITY)


def ang_diff(a, b):
    d = (b - a) % (2 * math.pi)
    if d > math.pi:
        d -= 2 * math.pi
    return d


class Ball:
    def __init__(self, i, x, y, vx, vy):
        self.i = i
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.hp = S.HP
        self.alive = True
        self.inv = 0.0
        self.level = 0
        self.hits = 0
        self.ko_t = None
        self.cd = 0.0
        self.aim = 0.0
        self.lz_state = 'idle'
        self.lz_timer = 0.0
        self.lz_target = None
        self.fire_t = -9.0  # last time the ability fired (for visuals)


class Bullet:
    __slots__ = ('owner', 'x', 'y', 'vx', 'vy', 'alive', 'born')

    def __init__(self, owner, x, y, vx, vy, born):
        self.owner, self.x, self.y, self.vx, self.vy = owner, x, y, vx, vy
        self.alive = True
        self.born = born


class Missile:
    __slots__ = ('owner', 'x', 'y', 'ang', 'speed', 'target', 'age', 'alive', 'id')

    def __init__(self, owner, x, y, ang, speed, target, mid):
        self.owner, self.x, self.y, self.ang, self.speed = owner, x, y, ang, speed
        self.target = target
        self.age = 0.0
        self.alive = True
        self.id = mid


class Sim:
    def __init__(self, seed, params=None, abilities=None):
        self.p = dict(P)
        if params:
            self.p.update(params)
        self.abil = list(abilities or S.ABILITIES)
        self.rng = random.Random(seed)
        self.seed = seed
        self.t = 0.0
        self.step_i = 0
        self.events = []
        self.bullets = []
        self.missiles = []
        self.mid = 0
        self.winner = None
        self.t_end = None
        self.over = False
        self.bl_phase = self.rng.uniform(0, 2 * math.pi)
        m = 170.0
        spawns = [(m, m), (AS - m, m), (m, AS - m), (AS - m, AS - m)]
        self.balls = []
        for i, (x, y) in enumerate(spawns):
            base = math.atan2(AS / 2 - y, AS / 2 - x)
            a = base + self.rng.uniform(-1.3, 1.3)
            self.balls.append(Ball(i, x, y, BASE_SPEED * math.cos(a), BASE_SPEED * math.sin(a)))
        for b in self.balls:
            b.cd = S.FIRST_COOLDOWN[self.abil[b.i]] + self.rng.uniform(0, 0.5)
        for bb in self.balls:
            bb.aim = math.atan2(AS / 2 - bb.y, AS / 2 - bb.x)

    # ------------------------------------------------------------------ helpers
    def ev(self, etype, **kw):
        kw['type'] = etype
        kw['t'] = self.t
        kw['step'] = self.step_i
        self.events.append(kw)

    def enemies(self, b):
        return [o for o in self.balls if o.alive and o is not b]

    def nearest(self, b, x=None, y=None, exclude=()):
        x = b.x if x is None else x
        y = b.y if y is None else y
        best, bd = None, 1e18
        for o in self.balls:
            if o.alive and o is not b and o not in exclude:
                d = (o.x - x) ** 2 + (o.y - y) ** 2
                if d < bd:
                    best, bd = o, d
        return best

    def blaster_rot(self, t=None):
        t = self.t if t is None else t
        return self.bl_phase + self.p['BL_SPIN'] * t

    def bl_count(self, b):
        return min(self.p['BL_N0'] + self.p['BL_STEP'] * b.level, self.p['BL_NMAX'])

    def ms_count(self, b):
        return min(self.p['MS_N0'] + b.level // self.p['MS_EVERY'], self.p['MS_NMAX'])

    def lz_width(self, b):
        return self.p['LZ_W0'] + self.p['LZ_W_STEP'] * b.level

    def lz_cd(self, b):
        return max(self.p['LZ_CD_MIN'], self.p['LZ_CD0'] - self.p['LZ_CD_STEP'] * b.level)

    def lt_range(self, b):
        return self.p['LT_RANGE0'] + self.p['LT_RANGE_STEP'] * b.level

    def lt_chain(self, b):
        return 1 + b.level // self.p['LT_CHAIN_EVERY']

    def beam_end(self, x, y, a):
        c, s = math.cos(a), math.sin(a)
        ts = []
        if c > 1e-9:
            ts.append((AS - x) / c)
        elif c < -1e-9:
            ts.append(-x / c)
        if s > 1e-9:
            ts.append((AS - y) / s)
        elif s < -1e-9:
            ts.append(-y / s)
        L = min(ts) if ts else AS
        return x + c * L, y + s * L

    def damage(self, victim, attacker, kind, sx, sy):
        if not victim.alive or victim.inv > 0 or self.over:
            return False
        victim.hp -= 1
        victim.inv = self.p['INVULN']
        dx, dy = victim.x - sx, victim.y - sy
        d = math.hypot(dx, dy)
        if d < 1e-6:
            a = self.rng.uniform(0, 2 * math.pi)
            dx, dy, d = math.cos(a), math.sin(a), 1.0
        victim.vx += KNOCK * dx / d
        victim.vy += KNOCK * dy / d
        lvl_before = attacker.level
        attacker.level = min(attacker.level + 1, MAX_LEVEL)
        attacker.hits += 1
        self.ev('hit', victim=victim.i, attacker=attacker.i, kind=kind, x=victim.x, y=victim.y,
                hp=victim.hp, sx=sx, sy=sy, upgraded=attacker.level > lvl_before, level=attacker.level)
        if victim.hp <= 0:
            victim.alive = False
            victim.ko_t = self.t
            self.ev('ko', victim=victim.i, attacker=attacker.i, x=victim.x, y=victim.y)
            for bl in self.bullets:
                if bl.owner == victim.i and bl.alive:
                    bl.alive = False
                    self.ev('fizzle', x=bl.x, y=bl.y, owner=victim.i, what='bullet')
            for ms in self.missiles:
                if ms.owner == victim.i and ms.alive:
                    ms.alive = False
                    self.ev('fizzle', x=ms.x, y=ms.y, owner=victim.i, what='missile')
            alive = [b for b in self.balls if b.alive]
            if len(alive) <= 1:
                self.over = True
                self.t_end = self.t
                self.winner = alive[0].i if alive else None
                self.ev('end', winner=self.winner)
        return True

    # ------------------------------------------------------------------ abilities
    def do_blaster(self, b):
        p = self.p
        b.cd -= DT
        if b.cd > 0 or not self.enemies(b):
            return
        n = self.bl_count(b)
        rot = self.blaster_rot()
        for k in range(n):
            a = rot + 2 * math.pi * k / n
            c, s = math.cos(a), math.sin(a)
            self.bullets.append(Bullet(b.i, b.x + c * (R + 12), b.y + s * (R + 12),
                                       c * p['BL_SPEED'], s * p['BL_SPEED'], self.t))
        b.cd = p['BL_CD']
        b.fire_t = self.t
        self.ev('blaster', owner=b.i, n=n, x=b.x, y=b.y, rot=rot)

    def do_laser(self, b):
        p = self.p
        tgt = self.nearest(b)
        if b.lz_state == 'idle':
            if tgt is not None:
                want = math.atan2(tgt.y - b.y, tgt.x - b.x)
                d = ang_diff(b.aim, want)
                mx = 2.5 * DT
                b.aim += max(-mx, min(mx, d))
            b.cd -= DT
            if b.cd <= 0 and tgt is not None:
                b.lz_state = 'charge'
                b.lz_timer = p['LZ_CHARGE']
                b.lz_target = tgt.i
                self.ev('laser_charge', owner=b.i)
        elif b.lz_state == 'charge':
            t2 = self.balls[b.lz_target]
            if not t2.alive:
                t2 = tgt
                if t2 is not None:
                    b.lz_target = t2.i
            if t2 is not None and b.lz_timer > p['LZ_LOCK']:
                want = math.atan2(t2.y - b.y, t2.x - b.x)
                d = ang_diff(b.aim, want)
                mx = p['LZ_TRACK'] * DT
                b.aim += max(-mx, min(mx, d))
            b.lz_timer -= DT
            if b.lz_timer <= 0:
                b.lz_state = 'fire'
                b.lz_timer = p['LZ_FIRE']
                b.fire_t = self.t
                self.ev('laser_fire', owner=b.i, aim=b.aim, width=self.lz_width(b))
        elif b.lz_state == 'fire':
            t2 = self.balls[b.lz_target] if b.lz_target is not None else None
            if t2 is not None and t2.alive and p['LZ_FIRE_TRACK'] > 0:
                want = math.atan2(t2.y - b.y, t2.x - b.x)
                d = ang_diff(b.aim, want)
                mx = p['LZ_FIRE_TRACK'] * DT
                b.aim += max(-mx, min(mx, d))
            w = self.lz_width(b)
            x0, y0 = b.x, b.y
            x1, y1 = self.beam_end(x0, y0, b.aim)
            dx, dy = x1 - x0, y1 - y0
            L2 = dx * dx + dy * dy
            for o in self.enemies(b):
                u = max(0.0, min(1.0, ((o.x - x0) * dx + (o.y - y0) * dy) / L2))
                px, py = x0 + u * dx, y0 + u * dy
                if (o.x - px) ** 2 + (o.y - py) ** 2 <= (R + w / 2) ** 2:
                    self.damage(o, b, 'laser', px, py)
            b.lz_timer -= DT
            if b.lz_timer <= 0:
                b.lz_state = 'idle'
                b.cd = self.lz_cd(b)

    def do_missiles(self, b):
        p = self.p
        tgt = self.nearest(b)
        if tgt is not None:
            want = math.atan2(tgt.y - b.y, tgt.x - b.x)
            d = ang_diff(b.aim, want)
            mx = 4.0 * DT
            b.aim += max(-mx, min(mx, d))
        b.cd -= DT
        if b.cd > 0 or tgt is None:
            return
        n = self.ms_count(b)
        ens = sorted(self.enemies(b), key=lambda o: (o.x - b.x) ** 2 + (o.y - b.y) ** 2)
        for k in range(n):
            target = ens[k % len(ens)]
            if n == 1:
                off = 0.0
            else:
                off = -p['MS_SPREAD'] + 2 * p['MS_SPREAD'] * k / (n - 1)
            a = b.aim + off + self.rng.uniform(-0.12, 0.12)
            c, s = math.cos(a), math.sin(a)
            self.missiles.append(Missile(b.i, b.x + c * (R + 6), b.y + s * (R + 6), a,
                                         p['MS_V0'], target.i, self.mid))
            self.mid += 1
        b.cd = p['MS_CD']
        b.fire_t = self.t
        self.ev('missile_launch', owner=b.i, n=n, x=b.x, y=b.y)

    def do_lightning(self, b):
        p = self.p
        if b.cd > 0:
            b.cd -= DT
            return
        rng_ = self.lt_range(b)
        cands = [o for o in self.enemies(b)
                 if math.hypot(o.x - b.x, o.y - b.y) - R <= rng_]
        if not cands:
            return
        cands.sort(key=lambda o: (o.x - b.x) ** 2 + (o.y - b.y) ** 2)
        targets = [cands[0]]
        chain = self.lt_chain(b)
        while len(targets) < chain:
            prev = targets[-1]
            nxt = None
            bd = 1e18
            for o in self.enemies(b):
                if o in targets:
                    continue
                d = math.hypot(o.x - prev.x, o.y - prev.y) - R
                if d <= rng_ and d < bd:
                    nxt, bd = o, d
            if nxt is None:
                break
            targets.append(nxt)
        pts = [(b.x, b.y)] + [(o.x, o.y) for o in targets]
        ids = [o.i for o in targets]
        self.ev('lightning', owner=b.i, targets=ids, pts=pts)
        prevx, prevy = b.x, b.y
        for o in targets:
            self.damage(o, b, 'lightning', prevx, prevy)
            prevx, prevy = o.x, o.y
        b.cd = p['LT_CD']
        b.fire_t = self.t

    # ------------------------------------------------------------------ step
    def step(self):
        p = self.p
        alive = [b for b in self.balls if b.alive]
        for b in alive:
            if b.inv > 0:
                b.inv = max(0.0, b.inv - DT)
        if not self.over:
            for b in alive:
                if not b.alive:
                    continue
                getattr(self, 'do_' + self.abil[b.i])(b)
        else:
            for b in alive:
                if self.abil[b.i] == 'laser' and b.lz_state != 'idle':
                    b.lz_state = 'idle'
        alive = [b for b in self.balls if b.alive]
        for b in alive:
            b.x += b.vx * DT
            b.y += b.vy * DT
            hit_wall = False
            if b.x < R:
                b.x = R
                b.vx = abs(b.vx)
                hit_wall = True
            elif b.x > AS - R:
                b.x = AS - R
                b.vx = -abs(b.vx)
                hit_wall = True
            if b.y < R:
                b.y = R
                b.vy = abs(b.vy)
                hit_wall = True
            elif b.y > AS - R:
                b.y = AS - R
                b.vy = -abs(b.vy)
                hit_wall = True
            if hit_wall:
                j = self.rng.uniform(-0.07, 0.07)
                c, s = math.cos(j), math.sin(j)
                b.vx, b.vy = b.vx * c - b.vy * s, b.vx * s + b.vy * c
                if b.x <= R + 1e-6:
                    b.vx = abs(b.vx)
                if b.x >= AS - R - 1e-6:
                    b.vx = -abs(b.vx)
                if b.y <= R + 1e-6:
                    b.vy = abs(b.vy)
                if b.y >= AS - R - 1e-6:
                    b.vy = -abs(b.vy)
        n = len(alive)
        for ia in range(n):
            a = alive[ia]
            for ib in range(ia + 1, n):
                c = alive[ib]
                dx, dy = c.x - a.x, c.y - a.y
                d2 = dx * dx + dy * dy
                if d2 < (2 * R) ** 2:
                    d = math.sqrt(d2) or 1e-6
                    nx, ny = dx / d, dy / d
                    vrel = (a.vx - c.vx) * nx + (a.vy - c.vy) * ny
                    if vrel > 0:
                        a.vx -= vrel * nx
                        a.vy -= vrel * ny
                        c.vx += vrel * nx
                        c.vy += vrel * ny
                        self.ev('bump', a=a.i, b=c.i, x=(a.x + c.x) / 2, y=(a.y + c.y) / 2, v=vrel)
                    ov = 2 * R - d
                    a.x -= nx * ov / 2
                    a.y -= ny * ov / 2
                    c.x += nx * ov / 2
                    c.y += ny * ov / 2
        for b in alive:
            sp = math.hypot(b.vx, b.vy)
            if sp < 1e-6:
                a = self.rng.uniform(0, 2 * math.pi)
                b.vx, b.vy, sp = math.cos(a), math.sin(a), 1.0
            target = BASE_SPEED
            ns = sp + (target - sp) * min(1.0, RELAX * DT)
            ns = max(150.0, min(1000.0, ns))
            b.vx *= ns / sp
            b.vy *= ns / sp
        br = p['BL_R']
        for bl in self.bullets:
            if not bl.alive:
                continue
            bl.x += bl.vx * DT
            bl.y += bl.vy * DT
            if bl.x < 0 or bl.x > AS or bl.y < 0 or bl.y > AS:
                bl.alive = False
                self.ev('bullet_wall', x=min(max(bl.x, 0), AS), y=min(max(bl.y, 0), AS), owner=bl.owner)
                continue
            for o in alive:
                if o.i == bl.owner or not o.alive:
                    continue
                if (o.x - bl.x) ** 2 + (o.y - bl.y) ** 2 < (R + br) ** 2:
                    bl.alive = False
                    ok = self.damage(o, self.balls[bl.owner], 'bullet', bl.x, bl.y)
                    if not ok:
                        self.ev('absorb', x=bl.x, y=bl.y, owner=bl.owner, victim=o.i)
                    break
        self.bullets = [bl for bl in self.bullets if bl.alive]
        for ms in self.missiles:
            if not ms.alive:
                continue
            tg = self.balls[ms.target]
            if not tg.alive:
                owner = self.balls[ms.owner]
                nt = self.nearest(owner, ms.x, ms.y)
                if nt is not None:
                    ms.target = nt.i
                    tg = nt
            if tg.alive and tg.i != ms.owner:
                want = math.atan2(tg.y - ms.y, tg.x - ms.x)
                d = ang_diff(ms.ang, want)
                mx = p['MS_TURN'] * DT
                ms.ang += max(-mx, min(mx, d))
            ms.speed = min(p['MS_V1'], ms.speed + p['MS_ACC'] * DT)
            ms.x += math.cos(ms.ang) * ms.speed * DT
            ms.y += math.sin(ms.ang) * ms.speed * DT
            ms.age += DT
            if ms.x < 0 or ms.x > AS or ms.y < 0 or ms.y > AS:
                ms.alive = False
                self.ev('missile_explode', x=min(max(ms.x, 0), AS), y=min(max(ms.y, 0), AS),
                        owner=ms.owner, hit=False, id=ms.id)
                continue
            if ms.age > p['MS_LIFE']:
                ms.alive = False
                self.ev('missile_explode', x=ms.x, y=ms.y, owner=ms.owner, hit=False, id=ms.id)
                continue
            for o in alive:
                if o.i == ms.owner or not o.alive:
                    continue
                if (o.x - ms.x) ** 2 + (o.y - ms.y) ** 2 < (R + p['MS_HIT_R']) ** 2:
                    ms.alive = False
                    ok = self.damage(o, self.balls[ms.owner], 'missile', ms.x, ms.y)
                    self.ev('missile_explode', x=ms.x, y=ms.y, owner=ms.owner, hit=ok, id=ms.id)
                    break
        self.missiles = [m for m in self.missiles if m.alive]
        self.t += DT
        self.step_i += 1


def run(seed, params=None, max_t=120.0, abilities=None):
    s = Sim(seed, params, abilities)
    while not s.over and s.t < max_t:
        s.step()
    return s
