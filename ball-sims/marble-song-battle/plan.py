"""Physics planner: turns the songs' hit times into a marble path and an obstacle course.

Between hits the marble flies on an exact ballistic arc, so it lands on the next obstacle exactly on the
note. Each obstacle is tilted so its normal is along the velocity change (a true reflection). The drop per
hop is c * g * dt^2 / 2 with c picked per hop to hit a target restitution `e` (from settings.ROUNDS);
a drop of more than g * dt^2 / 2 would need a downward launch, i.e. a bounce into the block.
Course styles: 'helix' (a narrowing funnel, camera looks down its axis), 'stairs' (forward with a sway)
and 'zigzag' (side to side). Rounds are joined by two-rail ramps that set the next round's speed.
Run `python3 plan.py` to print bounce stats and collision checks (all should be 0).
"""
import json
import math
import numpy as np
import settings
from music import SONGS

FPS = settings.FPS
G = 9.81
GV = np.array([0.0, 0.0, -G])
RM = 0.2
HEAD = np.array([0.0, -1.0])
ESTAR = 0.32
RAIL_A = 0.115
RAIL_R = 0.022

ROUNDS = [dict(r) for r in settings.ROUNDS]

OBST = {
    'slab': dict(kind='box', L=0.66, W=0.40, H=0.16, across=True),
    'gift': dict(kind='box', L=0.44, W=0.44, H=0.40, across=False),
    'mint': dict(kind='disc', D=0.46, H=0.10),
    'ornament': dict(kind='sphere', radius=0.23),
    'coal': dict(kind='sphere', radius=0.21),
    'cane': dict(kind='box', L=0.80, W=0.20, H=0.18, across=True),
}


def unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


class Rail:
    def __init__(self, S, TS, E, TE, l1, l2):
        self.P = [np.array(S, float), np.array(S, float) + TS * l1, np.array(E, float) - TE * l2, np.array(E, float)]
        u = np.linspace(0, 1, 3001)[:, None]
        P0, P1, P2, P3 = self.P
        self.pts = ((1 - u) ** 3) * P0 + 3 * ((1 - u) ** 2) * u * P1 + 3 * (1 - u) * u * u * P2 + (u ** 3) * P3
        seg = np.linalg.norm(np.diff(self.pts, axis=0), axis=1)
        self.s = np.concatenate([[0.0], np.cumsum(seg)])
        self.length = self.s[-1]

    def roll(self, v0, loss=0.9):
        z = self.pts[:, 2]
        v2 = v0 ** 2 + (10.0 / 7.0) * G * (z[0] - z) - loss * self.s
        v = np.sqrt(np.maximum(v2, 0.3))
        dt = np.diff(self.s) / (0.5 * (v[1:] + v[:-1]))
        self.T = np.concatenate([[0.0], np.cumsum(dt)])
        self.v = v
        return self.T[-1], v[-1]

    def pos_at(self, tau):
        return np.array([np.interp(tau, self.T, self.pts[:, k]) for k in range(3)])

    def translated(self, d):
        r = Rail.__new__(Rail)
        r.P = [p + d for p in self.P]
        r.pts = self.pts + d
        r.s = self.s
        r.length = self.length
        r.T = self.T
        r.v = self.v
        return r


def vertical_profile(times, vz_in0, estar):
    n = len(times)
    dts = [times[i + 1] - times[i] for i in range(n - 1)]
    cs = []
    prev_in = abs(vz_in0)
    for i, dt in enumerate(dts):
        c = 1.0 - estar * prev_in / (0.5 * G * dt)
        c = min(0.92, max(0.08, c))
        cs.append(c)
        prev_in = 0.5 * G * dt * (1 + c)
    dz = [-c * 0.5 * G * dt * dt for c, dt in zip(cs, dts)]
    return dz


def layout(rd, P0, Vin0, times):
    n = len(times)
    dz = vertical_profile(times, Vin0[2], rd['e'])
    P = [np.array(P0, float)]
    t0 = times[0]
    extra = {}
    if rd['style'] == 'helix':
        h = HEAD
        left = np.array([-h[1], h[0]])
        C0 = P0[:2] + rd['R'] * left * rd['sgn']
        th0 = math.atan2(P0[1] - C0[1], P0[0] - C0[0])
        T = times[-1] - t0
        omega = rd['sgn'] * 2 * math.pi * rd['turns'] / T
        drift = np.array(rd['drift'])
        R1 = rd.get('R1', rd['R'])
        for j in range(1, n):
            th = th0 + omega * (times[j] - t0)
            C = C0 + drift * (times[j] - t0)
            Rt = rd['R'] + (R1 - rd['R']) * (times[j] - t0) / T
            xy = C + Rt * np.array([math.cos(th), math.sin(th)])
            P.append(np.array([xy[0], xy[1], P[-1][2] + dz[j - 1]]))
        extra = dict(C0=C0, drift=drift, t0=t0, omega=omega)
    elif rd['style'] == 'stairs':
        f = HEAD
        s = np.array([-f[1], f[0]])
        for j in range(1, n):
            tt = times[j] - t0
            xy = P0[:2] + f * rd['vf'] * tt + s * rd['A'] * math.sin(2 * math.pi * tt / rd['Tsw'])
            P.append(np.array([xy[0], xy[1], P[-1][2] + dz[j - 1]]))
    elif rd['style'] == 'zigzag':
        f = HEAD
        s = np.array([-f[1], f[0]])
        lat = rd['Lmax'] * 0.5
        base0 = P0[:2] - s * lat
        for j in range(1, n):
            dt = times[j] - times[j - 1]
            L = min(rd['Lmax'], max(rd['Lmin'], rd['k'] * dt)) * 0.5
            lat = -math.copysign(L, lat)
            xy = base0 + f * rd['vf'] * (times[j] - t0) + s * lat
            P.append(np.array([xy[0], xy[1], P[-1][2] + dz[j - 1]]))
    return P, extra


def bounce_stats(Vin, Vout):
    n = unit(Vout - Vin)
    vin_n = -np.dot(Vin, n)
    vout_n = np.dot(Vout, n)
    e = vout_n / vin_n if vin_n > 1e-6 else 99
    return n, e


def rail_from(S, VS, v_target, Lh=4.2, dtb=0.30):
    vS = np.linalg.norm(VS)
    TS = VS / vS
    beta = math.radians(12)
    TE = unit(np.array([HEAD[0] * math.cos(beta), HEAD[1] * math.cos(beta), math.sin(beta)]))
    dz = (vS ** 2 - v_target ** 2) * 7.0 / (10.0 * G)
    for _ in range(40):
        E = S + np.array([HEAD[0] * Lh, HEAD[1] * Lh, -dz])
        rail = Rail(S, TS, E, TE, Lh * 0.42, Lh * 0.38)
        Tr, vE = rail.roll(vS)
        dz -= (vE - v_target) * 0.15
    VE = vE * TE
    PF = E + VE * dtb + 0.5 * GV * dtb * dtb
    VinF = VE + GV * dtb
    return dict(S=S, E=E, rail=rail, Tr=Tr, vE=vE, VS=VS, VE=VE, PF=PF, VinF=VinF, dtb=dtb)


def target_speed(rd, times):
    if rd['style'] == 'helix':
        T = times[-1] - times[0]
        sp = rd['R'] * 2 * math.pi * rd['turns'] / T
    else:
        sp = rd['vf']
    return sp / math.cos(math.radians(12))


def obstacle_frame(h, kindspec):
    n = h['n']
    d = h['Vin'] + h['Vout']
    d = d - np.dot(d, n) * n
    if np.linalg.norm(d) < 1e-6:
        d = np.array([1.0, 0, 0]) - n[0] * n
    xm = unit(d)
    ym = np.cross(n, xm)
    if kindspec.get('across'):
        xm, ym = ym, -xm
    return np.column_stack([xm, ym, n])


def plan():
    songs = SONGS
    S0 = np.array([0.0, 0.0, 0.0])
    VS0 = np.array([0.0, -2.6, -2.2])
    song_times = []
    for s in songs:
        spb = 60.0 / s['bpm']
        hb = [nn[0] for nn in s['notes'] if nn[3]]
        song_times.append([(b - hb[0]) * spb for b in hb])

    rails = []
    segments = []
    tr = rail_from(S0, VS0, target_speed(ROUNDS[0], song_times[0]))
    rails.append(dict(kind='intro', t0=0.0, t1=tr['Tr'], data=tr))
    segments.append(dict(kind='rail', t0=0.0, t1=tr['Tr'], rail=tr['rail']))
    segments.append(dict(kind='fly', t0=tr['Tr'], t1=tr['Tr'] + tr['dtb'], P=tr['E'], V=tr['VE']))
    t_first = tr['Tr'] + tr['dtb']
    PF, VinF = tr['PF'], tr['VinF']
    all_hits, rounds_out, end_info = [], [], None
    for k, s in enumerate(songs):
        rd = ROUNDS[k]
        times = [t_first + x for x in song_times[k]]
        P, extra = layout(rd, PF, VinF, times)
        rinfo = dict(k=k, name=s['name'], team=s['team'], t_start=times[0], t_last=times[-1],
                     style=rd['style'], obst=rd['obst'])
        if rd['style'] == 'helix':
            rinfo.update(C0=extra['C0'].tolist(), drift=extra['drift'].tolist(), ht0=extra['t0'])
        Vin, Vout = [VinF], []
        for j in range(len(P) - 1):
            dt = times[j + 1] - times[j]
            vo = (P[j + 1] - P[j]) / dt - 0.5 * GV * dt
            Vout.append(vo)
            Vin.append(vo + GV * dt)
            segments.append(dict(kind='fly', t0=times[j], t1=times[j + 1], P=P[j], V=vo))
        PL, VinL = P[-1], Vin[-1]
        if k < len(songs) - 1:
            dta = 0.30
            hsp = max(2.2, np.linalg.norm(VinL[:2]))
            vo = np.array([HEAD[0] * hsp, HEAD[1] * hsp, 0.34 * abs(VinL[2])])
            S = PL + vo * dta + 0.5 * GV * dta * dta
            VS = vo + GV * dta
            Vout.append(vo)
            segments.append(dict(kind='fly', t0=times[-1], t1=times[-1] + dta, P=PL, V=vo))
            tr = rail_from(S, VS, target_speed(ROUNDS[k + 1], song_times[k + 1]))
            t_r0 = times[-1] + dta
            rails.append(dict(kind='mid', t0=t_r0, t1=t_r0 + tr['Tr'], data=tr))
            segments.append(dict(kind='rail', t0=t_r0, t1=t_r0 + tr['Tr'], rail=tr['rail']))
            segments.append(dict(kind='fly', t0=t_r0 + tr['Tr'], t1=t_r0 + tr['Tr'] + tr['dtb'], P=tr['E'], V=tr['VE']))
            t_first = t_r0 + tr['Tr'] + tr['dtb']
            PF, VinF = tr['PF'], tr['VinF']
            rinfo['t_next'] = t_first
        else:
            best = None
            for nf in range(6, 20):
                tend = math.ceil(times[-1] * FPS + nf) / FPS
                dta = tend - times[-1]
                vo = VS0 - GV * dta
                n_, e_ = bounce_stats(VinL, vo)
                score = abs(e_ - 0.4) + 0.3 * abs(dta - 0.33)
                if n_[2] > 0.3 and e_ > 0 and (best is None or score < best[0]):
                    best = (score, dta, tend, vo)
            _, dta, tend, vo = best
            Vout.append(vo)
            S_end = PL + VS0 * dta - 0.5 * GV * dta * dta
            segments.append(dict(kind='fly', t0=times[-1], t1=tend, P=PL, V=vo))
            end_info = dict(t_end=tend, S_end=S_end, delta=S_end - S0, dta=dta)
            rinfo['t_next'] = tend
        for j in range(len(P)):
            n_, e_ = bounce_stats(Vin[j], Vout[j])
            all_hits.append(dict(k=k, j=j, t=times[j], P=P[j], Vin=Vin[j], Vout=Vout[j], n=n_, e=e_,
                                 obst=rd['obst'], glow=rd['glow']))
        rounds_out.append(rinfo)
    return dict(hits=all_hits, rails=rails, segments=segments, rounds=rounds_out, end=end_info, S0=S0, VS0=VS0)


def marble_pos(segments, t):
    for sg in segments:
        if sg['t0'] - 1e-9 <= t <= sg['t1'] + 1e-9:
            tau = t - sg['t0']
            if sg['kind'] == 'fly':
                return sg['P'] + sg['V'] * tau + 0.5 * GV * tau * tau
            return sg['rail'].pos_at(tau)
    return None


def build_obstacles(pl):
    hits = pl['hits']
    by_round = {}
    for h in hits:
        by_round.setdefault(h['k'], []).append(h)
    obs = []
    for k, hs in by_round.items():
        for i, h in enumerate(hs):
            spec = OBST[h['obst']]
            prev_d = np.linalg.norm(h['P'] - hs[i - 1]['P']) if i > 0 else 9
            next_d = np.linalg.norm(hs[i + 1]['P'] - h['P']) if i + 1 < len(hs) else 9
            near = min(prev_d, next_d)
            o = dict(k=k, j=h['j'], t=h['t'], type=h['obst'], kind=spec['kind'], glow=list(h['glow']))
            n = h['n']
            if spec['kind'] == 'sphere':
                rad = min(spec['radius'], 0.42 * near)
                o['radius'] = rad
                o['center'] = h['P'] - (RM + rad) * n
                o['R'] = obstacle_frame(h, spec)
            elif spec['kind'] == 'disc':
                D = min(spec['D'], 0.86 * near)
                o['size'] = [D, D, spec['H']]
                o['center'] = h['P'] - (RM + spec['H'] / 2) * n
                o['R'] = obstacle_frame(h, spec)
            else:
                if spec['across']:
                    W = min(spec['W'], 0.68 * near)
                    L = spec['L']
                else:
                    W = L = min(spec['L'], 0.82 * near)
                o['size'] = [L, W, spec['H']] if not spec['across'] else [L, W, spec['H']]
                o['center'] = h['P'] - (RM + spec['H'] / 2) * n
                o['R'] = obstacle_frame(h, spec)
            obs.append(o)
    return obs


def sdf_obstacle(o, p):
    if o['kind'] == 'sphere':
        return np.linalg.norm(p - o['center'], axis=-1) - o['radius']
    q = (p - o['center']) @ o['R']
    hs = np.array(o['size']) / 2
    if o['kind'] == 'disc':
        r = np.linalg.norm(q[..., :2], axis=-1)
        d = np.stack([r - hs[0], np.abs(q[..., 2]) - hs[2]], axis=-1)
    else:
        d = np.abs(q) - hs
    outside = np.linalg.norm(np.maximum(d, 0), axis=-1)
    inside = np.minimum(np.max(d, axis=-1), 0)
    return outside + inside


def rail_tubes(rail):
    pts = rail.pts[::20]
    T = np.gradient(pts, axis=0)
    T = T / np.linalg.norm(T, axis=1, keepdims=True)
    side = np.cross(T, np.array([0, 0, 1.0]))
    side /= np.linalg.norm(side, axis=1, keepdims=True)
    up = np.cross(side, T)
    hc = math.sqrt((RM + RAIL_R) ** 2 - RAIL_A ** 2)
    L = pts - up * hc + side * RAIL_A
    Rr = pts - up * hc - side * RAIL_A
    return pts, T, side, up, L, Rr, hc


def checks(pl, obs, verbose=True):
    segs = pl['segments']
    t_end = pl['end']['t_end']
    ts = np.arange(0, t_end, 1 / 240)
    M = np.array([marble_pos(segs, t) for t in ts])
    issues = []
    centers = np.array([o['center'] for o in obs])
    for i, o in enumerate(obs):
        near = np.where(np.linalg.norm(M - o['center'], axis=1) < 1.6)[0]
        if len(near) == 0:
            continue
        d = sdf_obstacle(o, M[near]) - RM
        tt = ts[near]
        bad = (d < -0.015) & (np.abs(tt - o['t']) > 0.03)
        if bad.any():
            issues.append(('marble-hits-obstacle', o['k'], o['j'], float(tt[bad][0]), float(d[bad].min())))
        cont = np.abs(tt - o['t']) <= 0.03
        if cont.any() and d[cont].min() < -0.03:
            issues.append(('contact-penetration', o['k'], o['j'], float(d[cont].min())))
    for i in range(len(obs)):
        for j2 in range(i + 1, len(obs)):
            if np.linalg.norm(centers[i] - centers[j2]) > 1.3:
                continue
            o1, o2 = obs[i], obs[j2]
            g = np.linspace(-0.5, 0.5, 7)
            if o2['kind'] == 'sphere':
                pts = o2['center'] + o2['radius'] * np.array([[a, b, c] for a in g for b in g for c in g])
            else:
                hs = np.array(o2['size'])
                pts = np.array([o2['center'] + o2['R'] @ (np.array([a, b, c]) * hs) for a in g for b in g for c in g])
            if (sdf_obstacle(o1, pts) < -0.005).any():
                issues.append(('obstacle-overlap', o1['k'], o1['j'], o2['k'], o2['j']))
    for rr in pl['rails']:
        pts, T, side, up, L, Rr, hc = rail_tubes(rr['data']['rail'])
        for o in obs:
            if np.min(np.linalg.norm(pts - o['center'], axis=1)) > 2.0:
                continue
            for nm, line in (('center', pts), ('L', L), ('R', Rr)):
                rad = RM if nm == 'center' else RAIL_R
                d = sdf_obstacle(o, line) - rad
                if (d < 0.0).any():
                    issues.append(('rail-' + nm + '-hits-obstacle', rr['kind'], round(rr['t0'], 2), o['k'], o['j'], float(d.min())))
    if verbose:
        for it in issues:
            print(*it)
        print('issues:', len(issues))
    return issues, ts, M


if __name__ == '__main__':
    pl = plan()
    print('t_end', pl['end']['t_end'], 'frames', pl['end']['t_end'] * FPS, 'delta', np.round(pl['end']['delta'], 2))
    for r in pl['rounds']:
        print(r['k'], r['name'], round(r['t_start'], 2), round(r['t_last'], 2), round(r['t_next'], 2))
    es = np.array([h['e'] for h in pl['hits']])
    nz = np.array([h['n'][2] for h in pl['hits']])
    print('e range %.2f..%.2f  median %.2f  nz min %.2f' % (es.min(), es.max(), np.median(es), nz.min()))
    for h in pl['hits']:
        if h['e'] < 0.08 or h['e'] > 1.1 or h['n'][2] < 0.35:
            print('odd', h['k'], h['j'], round(h['t'], 2), 'e=%.2f nz=%.2f' % (h['e'], h['n'][2]))
    for rr in pl['rails']:
        d = rr['data']
        print('rail', rr['kind'], 't0=%.2f Tr=%.2f vS=%.2f vE=%.2f dip=%.2f rise=%.2f' % (
            rr['t0'], d['Tr'], np.linalg.norm(d['VS']), d['vE'], d['rail'].pts[:, 2].min() - d['S'][2], d['E'][2] - d['S'][2]))
    obs = build_obstacles(pl)
    print('obstacles', len(obs))
    checks(pl, obs)
