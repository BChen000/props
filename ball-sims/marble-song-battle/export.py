"""Builds build/plan.json for the Blender scene, the audio and the post step.

Adds the camera path (top-down over helix funnels, chase cam behind the marble elsewhere, Gaussian-smoothed
anchor), the loop seam (obstacles and rails visible in the first/last frames are copied by the course's
end-to-start offset, so the last frame flows into the first) and the note list with global times.
Prints camera checks: frames where an obstacle hides the marble, and frames where the camera passes
within 1.2 m of an obstacle.
"""
import json
import math
import os
import numpy as np
import settings
from music import SONGS
import plan as P

FPS = P.FPS


def gauss_smooth(arr, sigma_frames):
    r = int(sigma_frames * 4)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma_frames) ** 2)
    k /= k.sum()
    out = np.empty_like(arr)
    pad = np.pad(arr, ((r, r), (0, 0)), mode='edge')
    for c in range(arr.shape[1]):
        out[:, c] = np.convolve(pad[:, c], k, mode='valid')
    return out


def look_quat(cam, target, up_hint=np.array([0.0, 1.0, 0.0])):
    f = P.unit(target - cam)
    upw = np.array([0.0, 0.0, 1.0])
    r = np.cross(f, upw)
    if np.linalg.norm(r) < 0.05:
        r = np.cross(f, up_hint)
    r = P.unit(r)
    u = np.cross(r, f)
    Rm = np.column_stack([r, u, -f])
    tr = np.trace(Rm)
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        w = 0.25 * s
        x = (Rm[2, 1] - Rm[1, 2]) / s
        y = (Rm[0, 2] - Rm[2, 0]) / s
        z = (Rm[1, 0] - Rm[0, 1]) / s
    else:
        i = int(np.argmax(np.diag(Rm)))
        if i == 0:
            s = math.sqrt(1.0 + Rm[0, 0] - Rm[1, 1] - Rm[2, 2]) * 2
            w = (Rm[2, 1] - Rm[1, 2]) / s; x = 0.25 * s; y = (Rm[0, 1] + Rm[1, 0]) / s; z = (Rm[0, 2] + Rm[2, 0]) / s
        elif i == 1:
            s = math.sqrt(1.0 + Rm[1, 1] - Rm[0, 0] - Rm[2, 2]) * 2
            w = (Rm[0, 2] - Rm[2, 0]) / s; x = (Rm[0, 1] + Rm[1, 0]) / s; y = 0.25 * s; z = (Rm[1, 2] + Rm[2, 1]) / s
        else:
            s = math.sqrt(1.0 + Rm[2, 2] - Rm[0, 0] - Rm[1, 1]) * 2
            w = (Rm[1, 0] - Rm[0, 1]) / s; x = (Rm[0, 2] + Rm[2, 0]) / s; y = (Rm[1, 2] + Rm[2, 1]) / s; z = 0.25 * s
    return [w, x, y, z], Rm


CAM_HELIX = np.array(settings.CAM_HELIX)
CAM_OTHER = np.array(settings.CAM_OTHER)
LOOK_HELIX = np.array(settings.LOOK_HELIX)
LOOK_OTHER = np.array(settings.LOOK_OTHER)


def build():
    pl = P.plan()
    obs = P.build_obstacles(pl)
    T = pl['end']['t_end']
    D = pl['end']['delta']
    N = int(round(T * FPS))
    segs = pl['segments']
    rounds = pl['rounds']

    def marble(t):
        k = math.floor(t / T)
        return P.marble_pos(segs, t - k * T) + k * D

    def helix_of(t):
        tt = t - math.floor(t / T) * T
        for r in rounds:
            if r['style'] == 'helix' and r['t_start'] <= tt <= r['t_last']:
                return r
        return None

    def anchor(t):
        k = math.floor(t / T)
        tt = t - k * T
        m = P.marble_pos(segs, tt)
        r = helix_of(t)
        if r is not None:
            C = np.array(r['C0']) + np.array(r['drift']) * (tt - r['ht0'])
            a = np.array([C[0], C[1], m[2]])
        else:
            a = m
        return a + k * D

    pad = 4 * FPS
    tf = (np.arange(-pad, N + pad)) / FPS
    A = np.array([anchor(t) for t in tf])
    def top_mode(t):
        tt = t - math.floor(t / T) * T
        for r in rounds:
            if r['style'] == 'helix' and r['t_start'] - 0.2 <= tt <= r['t_next'] - 0.1:
                return 1.0
        return 0.0
    W = np.array([[top_mode(t)] for t in tf])
    As = A.copy()
    As[:, :2] = gauss_smooth(A[:, :2], 0.35 * FPS)
    As[:, 2:] = gauss_smooth(A[:, 2:], 0.30 * FPS)
    Ws = gauss_smooth(W, 0.45 * FPS)
    As, Ws = As[pad:pad + N], Ws[pad:pad + N, 0]
    Mpos = np.array([marble(f / FPS) for f in range(N)])
    cams, quats, rots = [], [], []
    for f in range(N):
        off = CAM_HELIX * Ws[f] + CAM_OTHER * (1 - Ws[f])
        lk = LOOK_HELIX * Ws[f] + LOOK_OTHER * (1 - Ws[f])
        c = As[f] + off
        q, Rm = look_quat(c, As[f] + lk)
        cams.append(c)
        quats.append(q)
        rots.append(Rm)
    cams = np.array(cams)

    def visible(p, frames_):
        tv = 18.0 / settings.LENS
        th = 18.0 * 9 / 16 / settings.LENS
        for f in frames_:
            Rm = rots[f]
            v = np.asarray(p) - cams[f]
            fwd = -Rm[:, 2]
            d = v @ fwd
            if d < 0.3 or d > 90:
                continue
            x = (v @ Rm[:, 0]) / d / th
            y = (v @ Rm[:, 1]) / d / tv - 2 * settings.SHIFT_Y
            if abs(x) < 1.25 and abs(y) < 1.25:
                return True
        return False
    fs0 = list(range(0, 20, 2))
    fs1 = list(range(N - 20, N, 2))
    copies = []
    for o in obs:
        if visible(o['center'], fs0):
            c = dict(o); c['center'] = o['center'] + D; c['t'] = o['t'] + T; c['copy'] = True
            copies.append(c)
        if visible(o['center'], fs1):
            c = dict(o); c['center'] = o['center'] - D; c['t'] = o['t'] - T; c['copy'] = True
            copies.append(c)
    allobs = obs + copies
    print('seam copies', len(copies))

    rails_out = []
    rail_list = [(rr['kind'], rr['t0'], rr['data']['rail']) for rr in pl['rails']]
    intro_rail = pl['rails'][0]['data']['rail']
    extra = []
    for kind, t0, rail in rail_list:
        pts = rail.pts[::60]
        if any(visible(p, fs0) for p in pts) and kind != 'intro':
            extra.append((kind + '_cp', t0 + T, rail.translated(D)))
        if any(visible(p, fs1) for p in pts):
            extra.append((kind + '_cm', t0 - T, rail.translated(-D)))
    rail_list.append(('end', T, intro_rail.translated(D)))
    rail_list += extra
    print('rail copies', [x[0] for x in extra])
    for kind, t0, rail in rail_list:
        if rail is None:
            continue
        pts, Tg, side, up, L, Rr, hc = P.rail_tubes(rail)
        s = rail.s[::20]
        cross = []
        sp = 0.42
        si = sp * 0.5
        while si < s[-1] - 0.1:
            i = int(np.searchsorted(s, si))
            i = min(i, len(pts) - 1)
            c0 = pts[i] - up[i] * hc
            arc = []
            for a in np.linspace(0, math.pi, 9):
                arc.append((c0 + side[i] * P.RAIL_A * math.cos(a) - up[i] * P.RAIL_A * 0.9 * math.sin(a)).tolist())
            cross.append(arc)
            si += sp
        rails_out.append(dict(kind=kind, t0=t0, L=L.tolist(), R=Rr.tolist(), cross=cross))

    notes = []
    for r, s in zip(rounds, SONGS):
        spb = 60.0 / s['bpm']
        hb0 = [nn[0] for nn in s['notes'] if nn[3]][0]
        t0 = r['t_start']
        for b, midi, d, is_hit in s['notes']:
            notes.append(dict(t=t0 + (b - hb0) * spb, midi=midi + s.get('transpose', 0), dur=d * spb, hit=is_hit, k=r['k']))
        r['spb'] = spb
        r['beat0_t'] = t0 - hb0 * spb
    out = dict(
        fps=FPS, N=N, T=T, delta=D.tolist(),
        marble=Mpos.tolist(), cam=cams.tolist(), quat=quats, anchor=As.tolist(),
        obstacles=[dict(k=o['k'], j=o['j'], t=o['t'], type=o['type'], kind=o['kind'], glow=o['glow'],
                        center=np.asarray(o['center']).tolist(), R=np.asarray(o['R']).tolist(),
                        size=o.get('size'), radius=o.get('radius'), copy=o.get('copy', False)) for o in allobs],
        rails=rails_out,
        rounds=[dict(k=r['k'], name=r['name'], team=r['team'], t_start=r['t_start'], t_last=r['t_last'],
                     t_next=r['t_next'], style=r['style'], obst=r['obst'], spb=r['spb'], beat0_t=r['beat0_t'],
                     meter=SONGS[r['k']]['meter'], end_beat=SONGS[r['k']]['end_beat'], downbeat=SONGS[r['k']]['downbeat'])
                for r in rounds],
        rail_times=[[rr['t0'], rr['t1']] for rr in pl['rails']],
        notes=notes,
    )
    return out, pl, allobs, Mpos, cams, rots


def camera_checks(out, allobs, Mpos, cams):
    centers = np.array([o['center'] for o in allobs])
    occl = []
    close = []
    for f in range(len(Mpos)):
        c, m = cams[f], Mpos[f]
        dc = np.linalg.norm(centers - c, axis=1)
        if dc.min() < 1.2:
            i = int(dc.argmin())
            close.append((f, allobs[i]['k'], allobs[i]['j'], round(float(dc.min()), 2)))
        seg = c + (m - c) * np.linspace(0, 1, 60)[:, None]
        L = np.linalg.norm(m - c)
        keep = np.linalg.norm(seg - m, axis=1) > P.RM * 1.05
        seg = seg[keep]
        mid = (c + m) / 2
        cand = np.where(np.linalg.norm(centers - mid, axis=1) < L / 2 + 1.0)[0]
        for i in cand:
            d = P.sdf_obstacle(allobs[i], seg)
            if d.min() < 0:
                occl.append((f, allobs[i]['k'], allobs[i]['j']))
                break
    return occl, close


if __name__ == '__main__':
    out, pl, allobs, Mpos, cams, rots = build()
    occl, close = camera_checks(out, allobs, Mpos, cams)
    print('frames', out['N'], 'T', out['T'])
    print('occluded frames', len(occl), occl[:40])
    print('camera close to obstacle frames', len(close), close[:20])
    os.makedirs(settings.BUILD, exist_ok=True)
    with open(settings.PLAN_JSON, 'w') as fh:
        json.dump(out, fh)
    print('obstacles total', len(out['obstacles']), 'rails', len(out['rails']))
