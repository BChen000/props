"""Paints glossy and metal marbles onto the Cycles plates, frame by frame, in numpy.

Each marble is ray-traced as a sphere and lit from the nearest lighting probes
(spherical-harmonic diffuse + mirror reflection). Marbles cast soft shadows from
the key and top lights, darken the plate with contact occlusion, reflect in the
aluminum bars and in each other, hide behind the set using the depth plate, and
get motion blur. Used by render_frame.py and render_video.py.
"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from settings import *
sys.path.insert(0, SET_DIR)
from params import MARBLE_R, TOP, D, N, L, SIM_HZ
import numpy as np
import cv2
from probes import sh_basis, A_HAT

_meta = json.load(open(SCENE_META))
_cam = _meta['camera']
_M = np.array(_cam['matrix'])
C = _M[:3, 3].copy()
R = _M[:3, :3].copy()
TV = (_cam['sensor_h'] / 2) / _cam['lens']
TH = TV * W / H
PERM = [3, 7, 0, 5, 2, 6, 1, 4]


def ray_dirs(px, py):
    nx = px / W * 2 - 1
    ny = 1 - py / H * 2
    d = np.stack([nx * TH, ny * TV, -np.ones_like(nx)], -1) @ R.T
    return d / np.linalg.norm(d, axis=-1, keepdims=True)


def project(X):
    v = (np.asarray(X) - C) @ R
    z = -v[..., 2]
    nx = v[..., 0] / z / TH
    ny = v[..., 1] / z / TV
    return (nx + 1) / 2 * W, (1 - ny) / 2 * H, z


def px_per_m(z):
    return (H / 2) / (z * TV)


def circ_overlap(a, b, d):
    a = np.maximum(a, 1e-7); b = np.maximum(b, 1e-7)
    out = np.zeros_like(d)
    full = d <= np.abs(a - b)
    out[full] = np.pi * np.minimum(a, b)[full] ** 2
    part = (~full) & (d < a + b)
    if part.any():
        A, B, Dd = a[part], b[part], np.maximum(d[part], 1e-9)
        c1 = np.clip((Dd * Dd + A * A - B * B) / (2 * Dd * A), -1, 1)
        c2 = np.clip((Dd * Dd + B * B - A * A) / (2 * Dd * B), -1, 1)
        k = np.maximum((-Dd + A + B) * (Dd + A - B) * (Dd - A + B) * (Dd + A + B), 0)
        out[part] = A * A * np.arccos(c1) + B * B * np.arccos(c2) - 0.5 * np.sqrt(k)
    return out


def tonemap(x, exposure=1.0):
    x = np.maximum(x * exposure, 0)
    k = 0.8
    y = np.where(x < k, x, k + (1 - k) * np.tanh((x - k) / (1 - k)))
    y = np.where(y <= 0.0031308, 12.92 * y, 1.055 * np.power(np.maximum(y, 1e-8), 1 / 2.4) - 0.055)
    return np.clip(y * 255 + 0.5, 0, 255).astype(np.uint8)


class Renderer:
    def __init__(self, sim_file, cfg_file):
        t0 = time.time()
        PD = PLATE_DIR
        self.beauty = np.load(os.path.join(PD, 'beauty.npy')).astype(np.float32)
        key = np.load(os.path.join(PD, 'key_direct.npy')); top = np.load(os.path.join(PD, 'top_direct.npy'))
        self.key = cv2.resize(key, (W, H), interpolation=cv2.INTER_LINEAR).astype(np.float32)
        self.top = cv2.resize(top, (W, H), interpolation=cv2.INTER_LINEAR).astype(np.float32)
        self.rest = np.maximum(self.beauty - self.key - self.top, 0)
        pos2 = np.load(os.path.join(PD, 'g_pos.npy')) - np.array([2, 2, 1.0], np.float32)
        self.dist2 = np.linalg.norm(pos2 - C, axis=-1).astype(np.float32)
        self.pos1 = pos2[1::2, 1::2].astype(np.float32).copy()
        del pos2
        n = np.load(os.path.join(PD, 'g_nrm.npy')) * 2 - 1
        self.nrm = (n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-6)).astype(np.float32)
        self.oid = np.round(np.load(os.path.join(PD, 'g_id.npy'))[..., 0] * 16).astype(np.int16)
        pp = np.load(PROBES_FILE)
        self.ppos, self.eq, self.eqb, self.sh = pp['pos'], pp['eq'], pp['eqb'], pp['sh']
        self.lights = []
        for nm in ('key', 'top'):
            Lm = np.array(_meta['lights'][nm]['matrix']); sx, sy = _meta['lights'][nm]['size']
            self.lights.append((Lm[:3, 3].copy(), np.sqrt(sx * sy / np.pi)))
        d = np.load(sim_file)
        self.traj = d['pos'].astype(np.float64)
        self.tt = d['t']
        self.pre = -float(self.tt[0])
        cfg = json.load(open(cfg_file))
        self.mat = [m['color'] for m in cfg['marbles']]
        self.nm = len(self.mat)
        self.r = MARBLE_R
        print('renderer init %.1fs' % (time.time() - t0), flush=True)

    def centers(self, tau):
        f = (tau + self.pre) * SIM_HZ
        i0 = int(np.clip(np.floor(f), 0, len(self.tt) - 2))
        a = np.clip(f - i0, 0, 1)
        P = self.traj[i0] * (1 - a) + self.traj[i0 + 1] * a
        act = (np.abs(P[:, 0]) < 1.2) & (P[:, 1] > -1.2) & (P[:, 1] < 1.6) & (P[:, 2] < 1.2) & (P[:, 2] > -0.5)
        return P, act

    def probe_w(self, c):
        d2 = ((self.ppos - c) ** 2).sum(1)
        idx = np.argsort(d2)[:2]
        w = 1.0 / (d2[idx] + 1e-4)
        return idx, w / w.sum()

    def eq_lookup(self, maps, idx, w, dirs):
        lon = np.arctan2(dirs[:, 1], dirs[:, 0])
        lat = np.arcsin(np.clip(dirs[:, 2], -1, 1))
        Hh, Ww = maps.shape[1], maps.shape[2]
        u = (lon + np.pi) / (2 * np.pi) * Ww - 0.5
        v = (np.pi / 2 - lat) / np.pi * Hh - 0.5
        x0 = np.floor(u).astype(int); y0 = np.clip(np.floor(v).astype(int), 0, Hh - 1)
        fx = (u - x0)[:, None]; fy = np.clip(v - y0, 0, 1)[:, None]
        x0m = x0 % Ww; x1m = (x0 + 1) % Ww; y1 = np.clip(y0 + 1, 0, Hh - 1)
        out = 0
        for p, wp in zip(idx, w):
            Mp = maps[p]
            out = out + wp * (Mp[y0, x0m] * (1 - fx) * (1 - fy) + Mp[y0, x1m] * fx * (1 - fy) + Mp[y1, x0m] * (1 - fx) * fy + Mp[y1, x1m] * fx * fy)
        return out

    def irr(self, idx, w, n):
        Y = sh_basis(n) * A_HAT
        sh = (self.sh[idx] * w[:, None, None, None]).sum(0)
        return [Y @ sh[c] for c in range(3)]

    def light_occ(self, X, c, r, li):
        cL, RL = self.lights[li]
        v = c - X
        d = np.linalg.norm(v, axis=-1)
        l = cL - X
        DL = np.linalg.norm(l, axis=-1)
        aS = np.arcsin(np.clip(r / np.maximum(d, 1e-6), 0, 1))
        aL = np.arctan(RL / DL)
        cb = np.clip((v * l).sum(-1) / (np.maximum(d, 1e-9) * DL), -1, 1)
        beta = np.arccos(cb)
        f = circ_overlap(aL, aS, beta) / (np.pi * aL * aL)
        f = np.where(d <= r, 1.0, f)
        return np.clip(f, 0, 1)

    def ao_term(self, X, n, c, r):
        v = c - X
        d = np.maximum(np.linalg.norm(v, axis=-1), r)
        cosv = np.clip((v * n).sum(-1) / d, 0, 1)
        return np.clip((r / d) ** 2 * cosv, 0, 1)

    def sphere_hit(self, o, d, c, r):
        oc = o - c
        b = (d * oc).sum(-1)
        cc = (oc * oc).sum(-1) - r * r
        disc = b * b - cc
        t = -b - np.sqrt(np.maximum(disc, 0))
        return np.where((disc > 0) & (t > 1e-5), t, np.inf)

    def material(self, i):
        m = self.mat[i]
        if m in METALS:
            return True, np.array(METALS[m], np.float32)
        return False, np.array(PALETTE[m], np.float32)

    def shade_simple(self, i, X, n, v, P):
        idx, w = self.probe_w(P[i])
        metal, col = self.material(i)
        nv = np.clip((n * v).sum(-1), 0, 1)[:, None]
        rr = 2 * (n * v).sum(-1)[:, None] * n - v
        if metal:
            F = col + (1 - col) * (1 - nv) ** 5
            return F * self.eq_lookup(self.eqb, idx, w, rr)
        Er, Ek, Et = self.irr(idx, w, n)
        F = 0.04 + 0.96 * (1 - nv) ** 5
        return col / np.pi * (Er + Ek + Et) * (1 - F) + F * self.eq_lookup(self.eq, idx, w, rr)

    def shade(self, i, X, n, v, P, act_idx):
        idx, w = self.probe_w(P[i])
        metal, col = self.material(i)
        dd = np.linalg.norm(P[act_idx] - P[i], axis=1)
        nb = [j for j, dj in zip(act_idx, dd) if j != i and dj < 0.12]
        nbs = [j for j, dj in zip(act_idx, dd) if j != i and dj < 0.07]
        nv = np.clip((n * v).sum(-1), 0, 1)[:, None]
        rr = 2 * (n * v).sum(-1)[:, None] * n - v
        tbest = np.full(len(X), np.inf); jbest = np.full(len(X), -1)
        Xo = X + n * 1e-5
        for j in nb:
            t = self.sphere_hit(Xo, rr, P[j], self.r)
            better = t < tbest
            tbest[better] = t[better]; jbest[better] = j
        Lr = self.eq_lookup(self.eqb if metal else self.eq, idx, w, rr)
        for j in np.unique(jbest[jbest >= 0]):
            m = jbest == j
            Xh = Xo[m] + rr[m] * tbest[m][:, None]
            nh = (Xh - P[j]) / self.r
            Lr[m] = self.shade_simple(j, Xh, nh, -rr[m], P)
        if metal:
            F = col + (1 - col) * (1 - nv) ** 5
            return F * Lr
        Er, Ek, Et = self.irr(idx, w, n)
        vk = np.ones(len(X)); vt = np.ones(len(X)); ao = np.zeros(len(X))
        for j in nbs:
            dj = P[j] - P[i]
            for li, vv in ((0, vk), (1, vt)):
                ldir = self.lights[li][0] - P[i]
                ldir = ldir / np.linalg.norm(ldir)
                if dj @ ldir > -self.r:
                    vv *= 1 - self.light_occ(X, P[j], self.r, li)
            ao += self.ao_term(X, n, P[j], self.r)
        ao = np.clip(ao, 0, 0.9)
        E = Er * (1 - ao)[:, None] + Ek * vk[:, None] + Et * vt[:, None]
        F = 0.04 + 0.96 * (1 - nv) ** 5
        return col / np.pi * E * (1 - F) + F * Lr

    def sphere_rect(self, c, rad_m, margin=3):
        px, py, z = project(c)
        if z <= 0.05:
            return None
        rp = rad_m * px_per_m(z) + margin
        x0, x1 = int(np.floor(px - rp)), int(np.ceil(px + rp))
        y0, y1 = int(np.floor(py - rp)), int(np.ceil(py + rp))
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, W), min(y1, H)
        if x1 <= x0 or y1 <= y0:
            return None
        return (x0, x1, y0, y1)

    def influence_rects(self, c):
        out = {'core': None, 'shadow': [], 'refl': None}
        out['core'] = self.sphere_rect(c, self.r * 2.2, 4)
        for li, (cL, RL) in enumerate(self.lights):
            dirv = c - cL; dirv /= np.linalg.norm(dirv)
            lam = []
            sr = (c - TOP) @ D
            hr = (c - TOP) @ N
            if -0.05 < sr < L + 0.05 and hr > 0:
                dn = dirv @ N
                if dn < 0:
                    lam.append(hr / -dn)
            if dirv[2] < 0:
                lam.append((c[2] - 0.005) / -dirv[2])
            lm = min(lam) if lam else 0.3
            pen = self.r + lm * RL / np.linalg.norm(cL - c) * 1.2
            for frac, scale in ((1.0, 1.0), (0.5, 0.7)):
                rr_ = self.sphere_rect(c + dirv * lm * frac, pen * scale + self.r, 4)
                if rr_: out['shadow'].append(rr_)
        hr = (c - TOP) @ N
        sr = (c - TOP) @ D
        if -0.05 < sr < L + 0.05 and 0 < hr < 0.4:
            cm = c - 2 * hr * N
            out['refl'] = self.sphere_rect(cm, self.r * 1.7, 4)
        return out

    @staticmethod
    def union(rs):
        rs = [r for r in rs if r]
        if not rs:
            return None
        return (min(r[0] for r in rs), max(r[1] for r in rs), min(r[2] for r in rs), max(r[3] for r in rs))

    def render(self, t, ns=SAMPLES_PER_PIXEL, nt=SHADOW_TIME_SAMPLES, shutter=SHUTTER):
        taus_t = [t + shutter * ((k + 0.5) / nt - 0.5) for k in range(nt)]
        Pm, actm = self.centers(t)
        act_m = np.where(actm)[0]
        plate_samples = []
        rect_all = []
        for k, tau in enumerate(taus_t):
            P, act = self.centers(tau)
            act_idx = np.where(act)[0]
            rects = {}
            for i in act_idx:
                ir = self.influence_rects(P[i])
                u = self.union([ir['core']] + ir['shadow'] + [ir['refl']])
                if u:
                    ir['union_sh'] = self.union([ir['core']] + ir['shadow'])
                    rects[i] = ir
                    rect_all.append(u)
            plate_samples.append((P, act_idx, rects))
        if not rect_all:
            return self.beauty, None
        X0 = min(r[0] for r in rect_all); X1 = max(r[1] for r in rect_all)
        Y0 = min(r[2] for r in rect_all); Y1 = max(r[3] for r in rect_all)
        bw, bh = X1 - X0, Y1 - Y0
        jit = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1)]
        rnc = np.ones((bh, bw), np.float32); rcs = np.zeros((bh, bw, 3), np.float32); rcw = np.zeros((bh, bw), np.float32)
        for i in act_m:
            ir = self.influence_rects(Pm[i])
            rf = ir['refl']
            if not rf:
                continue
            c = Pm[i]
            x0, x1, y0, y1 = max(rf[0], X0), min(rf[1], X1), max(rf[2], Y0), min(rf[3], Y1)
            if x1 <= x0 or y1 <= y0:
                continue
            ry, rx = np.where(np.isin(self.oid[y0:y1, x0:x1], BAR_OBJECT_IDS))
            if not len(ry):
                continue
            ry = ry + y0; rx = rx + x0
            Xp = self.pos1[ry, rx]; Np = self.nrm[ry, rx]
            dv = Xp - C; dv /= np.linalg.norm(dv, axis=-1, keepdims=True)
            rdir = dv - 2 * (dv * Np).sum(-1)[:, None] * Np
            t1 = np.cross(rdir, np.array([1.0, 0, 0])); t1 /= np.maximum(np.linalg.norm(t1, axis=-1, keepdims=True), 1e-6)
            t2 = np.cross(rdir, t1)
            cov = np.zeros(len(Xp)); colr = np.zeros((len(Xp), 3))
            for (a, b) in jit:
                rd = rdir + 0.07 * a * t1 + 0.11 * b * t2
                rd /= np.linalg.norm(rd, axis=-1, keepdims=True)
                th = self.sphere_hit(Xp + Np * 1e-4, rd, c, self.r)
                m = np.isfinite(th)
                if m.any():
                    Xh = Xp[m] + Np[m] * 1e-4 + rd[m] * th[m][:, None]
                    nh = (Xh - c) / self.r
                    colr[m] += self.shade_simple(i, Xh, nh, -rd[m], Pm)
                    cov[m] += 1
            hit = cov > 0
            if hit.any():
                cv = cov[hit] / len(jit)
                cc = colr[hit] / cov[hit][:, None]
                yy, xx = ry[hit] - Y0, rx[hit] - X0
                rnc[yy, xx] *= 1 - cv
                rcs[yy, xx] += cc * cv[:, None]
                rcw[yy, xx] += cv
        rcov = 1 - rnc
        rcol = rcs / np.maximum(rcw, 1e-6)[..., None]
        FR = BAR_REFLECTION
        shadowed = []
        for k, (P, act_idx, rects) in enumerate(plate_samples):
            vk = np.ones((bh, bw), np.float32); vt = np.ones((bh, bw), np.float32); ao = np.zeros((bh, bw), np.float32)
            for i, ir in rects.items():
                c = P[i]
                u = ir['union_sh']
                if u:
                    ux0, ux1, uy0, uy1 = u
                    Xp = self.pos1[uy0:uy1, ux0:ux1].reshape(-1, 3)
                    Np = self.nrm[uy0:uy1, ux0:ux1].reshape(-1, 3)
                    sl = (slice(uy0 - Y0, uy1 - Y0), slice(ux0 - X0, ux1 - X0))
                    hh, ww = uy1 - uy0, ux1 - ux0
                    vk[sl] *= (1 - self.light_occ(Xp, c, self.r, 0)).reshape(hh, ww)
                    vt[sl] *= (1 - self.light_occ(Xp, c, self.r, 1)).reshape(hh, ww)
                    ao[sl] += self.ao_term(Xp, Np, c, self.r).reshape(hh, ww)
            ao = np.minimum(ao, 0.92)
            b = self.beauty[Y0:Y1, X0:X1]
            sh = b - self.key[Y0:Y1, X0:X1] * (1 - vk)[..., None] - self.top[Y0:Y1, X0:X1] * (1 - vt)[..., None] - self.rest[Y0:Y1, X0:X1] * ao[..., None]
            sh = np.maximum(sh, 0)
            sh = sh * (1 - FR * rcov)[..., None] + FR * rcov[..., None] * rcol
            shadowed.append(sh)
        recs = []
        for s in range(ns):
            tau = t + shutter * ((s + 0.5) / ns - 0.5)
            ox = ((PERM[s] if ns == 8 else (s * 7) % ns) + 0.5) / ns; oy = (s + 0.5) / ns
            P, act = self.centers(tau)
            act_idx = np.where(act)[0]
            zb = np.full((bh, bw), np.inf, np.float32); ib = np.full((bh, bw), -1, np.int32)
            for i in act_idx:
                rc = self.sphere_rect(P[i], self.r, 3)
                if rc is None:
                    continue
                x0, x1, y0, y1 = rc
                x0, x1, y0, y1 = max(x0, X0), min(x1, X1), max(y0, Y0), min(y1, Y1)
                if x1 <= x0 or y1 <= y0:
                    continue
                gy, gx = np.mgrid[y0:y1, x0:x1]
                dirs = ray_dirs(gx + ox, gy + oy)
                th = self.sphere_hit(C, dirs.reshape(-1, 3), P[i], self.r).reshape(gy.shape)
                pd = self.dist2[np.minimum((2 * (gy + oy)).astype(int), 2 * H - 1), np.minimum((2 * (gx + ox)).astype(int), 2 * W - 1)]
                th = np.where(th < pd + 0.002, th, np.inf)
                sl = (slice(y0 - Y0, y1 - Y0), slice(x0 - X0, x1 - X0))
                better = th < zb[sl]
                zb[sl][better] = th[better]
                ib[sl][better] = i
            yy, xx = np.where(ib >= 0)
            if len(yy):
                dirs = ray_dirs(xx + X0 + ox, yy + Y0 + oy)
                ids = ib[yy, xx]
                Xh = C + dirs * zb[yy, xx][:, None]
                nrm_ = (Xh - P[ids]) / self.r
                recs.append((s, yy, xx, ids, nrm_, -dirs))
            else:
                recs.append((s, yy, xx, None, None, None))
        cols = {}
        valid = [r for r in recs if r[3] is not None]
        if valid:
            ids_all = np.concatenate([r[3] for r in valid])
            n_all = np.concatenate([r[4] for r in valid])
            v_all = np.concatenate([r[5] for r in valid])
            col_all = np.zeros((len(ids_all), 3), np.float32)
            for i in np.unique(ids_all):
                m = ids_all == i
                nn = n_all[m] / np.linalg.norm(n_all[m], axis=-1, keepdims=True)
                col_all[m] = self.shade(i, Pm[i] + nn * self.r, nn, v_all[m], Pm, act_m)
            off = 0
            for r in valid:
                cols[r[0]] = col_all[off:off + len(r[3])]
                off += len(r[3])
        acc = np.zeros((bh, bw, 3), np.float32)
        for (s, yy, xx, ids, _, _) in recs:
            col = shadowed[min(s * nt // ns, nt - 1)].copy()
            if ids is not None:
                col[yy, xx] = cols[s]
            acc += col
        acc /= ns
        return acc, (X0, X1, Y0, Y1)

    def frame(self, t, ns=SAMPLES_PER_PIXEL, exposure=EXPOSURE, base=None):
        """Finished 8-bit RGB frame at time t (seconds)."""
        if base is None:
            base = tonemap(self.beauty, exposure)
        acc, box = self.render(t, ns=ns)
        out = base.copy()
        if box is not None:
            X0, X1, Y0, Y1 = box
            out[Y0:Y1, X0:X1] = tonemap(acc, exposure)
        return out
