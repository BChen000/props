"""The seeker's googly eyes, painted onto the 3D marble itself so they turn, hide behind blocks and catch the light
like the rest of the ball.

EyeCompositor is ../marble-raytrace-kit's Compositor with one change: the marble with index `eye_marble` gets a
per-pixel albedo with two eyes (white with a dark rim, a black pupil with a glint) whose directions come from that
frame's heading, openness and gaze (story.seeker_eyes). Openness 0 is shut (a lash line), 1 open, above 1 wide.
"""
import math

import numpy as np

import compositor as CO
import settings as C


def eye_albedo(n, body, head, openness, gx, gy):
    """Albedo (k, 3) for unit surface normals n (k, 3) of the seeker."""
    E = C.EYE
    f = np.array([math.sin(head), 0.0, math.cos(head)])
    side = np.array([math.cos(head), 0.0, -math.sin(head)])
    up = np.array([0.0, 1.0, 0.0])
    wide = 1.0 + 0.22 * max(0.0, openness - 1.0)
    size = E["size"] * wide
    alb = np.repeat(body[None], len(n), 0)
    lid = 2 * min(1.0, max(0.0, openness)) - 1          # sclera shows below this (eye-local, -1 bottom .. 1 top)
    for sgn in (-1.0, 1.0):
        e = f * math.cos(E["up"]) * math.cos(E["apart"]) + up * math.sin(E["up"]) + \
            side * (sgn * math.cos(E["up"]) * math.sin(E["apart"]))
        e /= np.linalg.norm(e)
        ex = np.cross(up, e)
        ex /= np.linalg.norm(ex)
        ey = np.cross(e, ex)
        ca = n @ e
        ang = np.arccos(np.clip(ca, -1, 1))
        lx = (n @ ex) / math.sin(size)
        ly = (n @ ey) / math.sin(size)
        inside = ang < size
        rim = (ang >= size) & (ang < size + E["ring"])
        if openness < 0.12:                              # shut: a curved lash line
            line = inside & (np.abs(ly + 0.12 + 0.25 * lx * lx) < 0.11)
            alb[line] = (0.02, 0.02, 0.025)
            continue
        show = inside & (ly < lid)
        alb[rim & (ly < lid + 0.05)] = (0.015, 0.015, 0.02)
        alb[show] = (0.92, 0.92, 0.90)
        # pupil
        g = E["gaze"] * (size - E["pupil"])
        p = e * math.cos(g * math.hypot(gx, gy)) + (ex * gx + ey * gy) / max(math.hypot(gx, gy), 1e-6) * \
            math.sin(g * math.hypot(gx, gy))
        p /= np.linalg.norm(p)
        pa = np.arccos(np.clip(n @ p, -1, 1))
        pup = show & (pa < E["pupil"] * wide)
        alb[pup] = (0.01, 0.01, 0.012)
        gl = p + ex * (-0.35 * E["pupil"]) + ey * (0.4 * E["pupil"])
        gl /= np.linalg.norm(gl)
        glint = pup & (np.arccos(np.clip(n @ gl, -1, 1)) < 0.28 * E["pupil"])
        alb[glint] = (0.95, 0.95, 0.95)
        if openness < 0.98:                              # upper lid edge
            edge = inside & (np.abs(ly - lid) < 0.09)
            alb[edge] = (0.02, 0.02, 0.025)
    return alb


class EyeCompositor(CO.Compositor):
    def __init__(self, *a, eyes=None, eye_marble=0, **k):
        super().__init__(*a, **k)
        self.eyes = eyes
        self.eye_marble = eye_marble
        self._f = 0

    def render(self, f, title=True, watermark=True):
        self._f = f
        return super().render(f, title=title, watermark=watermark)

    def draw_marble(self, act, i, b, rc, dirs, Lc, zb, acov, glows):
        m, c, (vis_c, cube, gap, _reach) = act[i]
        x0, y0, x1, y1 = rc
        bx0, by0, bx1, by1 = max(b[0], x0), max(b[1], y0), min(b[2], x1), min(b[3], y1)
        if bx1 <= bx0 or by1 <= by0:
            return
        sl = (slice(by0 - y0, by1 - y0), slice(bx0 - x0, bx1 - x0))
        d = dirs[sl]
        oc = CO.CAM - c
        bb = (d * oc).sum(-1)
        cc = oc @ oc
        q2 = np.maximum(cc - bb * bb, 0)
        q = np.sqrt(q2)
        tmid = -bb
        pxw = tmid * (2 * CO.TH / CO.H2)
        alpha = np.clip(0.5 + (CO.R - q) / pxw, 0, 1)
        if alpha.max() <= 0:
            return
        thit = tmid - np.sqrt(np.maximum(CO.R * CO.R - q2, 0))
        vis = (thit < zb[sl]).astype(np.float32)
        a = alpha * vis
        sel = a > 0
        if not sel.any():
            return
        ds = d[sel]
        th = thit[sel]
        P = CO.CAM[None] + ds * th[:, None]
        n = P - c[None]
        n /= np.linalg.norm(n, axis=1, keepdims=True)
        alb = self.cols[m]
        if m == self.eye_marble and self.eyes is not None:
            e = self.eyes[self._f]
            albp = eye_albedo(n, alb, e[0], e[1], e[2], e[3])
        else:
            albp = np.repeat(alb[None], len(n), 0)
        Sv = np.full(len(P), vis_c)
        Av = np.ones(len(P))
        for j, (mj, cj, _) in enumerate(act):
            if j == i:
                continue
            dvec = cj - c
            dc = np.linalg.norm(dvec)
            near_ao = dc < CO.AO_MAXD + 1.0
            can_sh = dc < CO.SH_MAXD and (dvec @ CO.L) > -0.2 * dc
            if not (near_ao or can_sh):
                continue
            dv = cj[None] - P
            dist = np.maximum(np.sqrt((dv * dv).sum(-1)), 1e-4)
            if can_sh:
                fr, _, _ = CO.sphere_shadow(P, cj)
                Sv *= 1 - fr
            if near_ao:
                Av *= 1 - 0.85 * CO.sphere_ao(n, dv, dist)
        ndl = np.clip(n @ CO.L, 0, None)
        nn = n * n
        E = (nn[:, 0:1] * np.where(n[:, 0:1] > 0, cube[0], cube[1]) +
             nn[:, 1:2] * np.where(n[:, 1:2] > 0, cube[2], cube[3]) +
             nn[:, 2:3] * np.where(n[:, 2:3] > 0, cube[4], cube[5]))
        kdark = 1 - 0.55 * np.clip(-n[:, 1], 0, 1) ** 2 * math.exp(-max(gap, 0) / 0.7)
        diff = albp / np.pi * (CO.LCOL[None] * (ndl * Sv)[:, None] + E * (Av * kdark)[:, None])
        v = -ds
        hv = CO.L[None] + v
        hv /= np.linalg.norm(hv, axis=1, keepdims=True)
        ndh = np.clip((n * hv).sum(1), 0, 1)
        ndv = np.clip((n * v).sum(1), 0, 1)
        Fr = CO.F0 + (1 - CO.F0) * (1 - ndv) ** 5
        spec = (0.85 * (420 + 8) / (8 * np.pi) * ndh ** 420 + 0.22 * (36 + 8) / (8 * np.pi) * ndh ** 36) * CO.F0
        spec = spec * Sv * ndl
        r = ds - 2 * (ds * n).sum(1, keepdims=True) * n
        env = np.where(r[:, 1:2] >= 0, CO.sky_rad(r), cube[3][None] / np.pi * 1.0)
        refl = Fr[:, None] * env * (0.35 + 0.65 * Av[:, None])
        col = diff + spec[:, None] * CO.LCOL[None] + refl
        sub = Lc[sl]
        aa = a[sel][:, None]
        sub[sel] = sub[sel] * (1 - aa) + col * aa
        zsub = zb[sl]
        upd = sel & (a > 0.5)
        zsub[upd] = thit[upd]
        asub = acov[sl]
        asub[sel] = np.maximum(asub[sel], a[sel])
