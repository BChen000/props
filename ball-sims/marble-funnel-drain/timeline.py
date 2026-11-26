"""Marble Funnel Drain timeline: sim time <-> video time (slow motion), the camera path, marble positions per frame.

The playback speed is eased between the points in settings.SPEED, and the video runs from sim time T0 to T_END.
The camera holds between equal neighbouring keys in settings.KEYS and eases between different ones (log distance,
smootherstep). The coloured marbles are picked from the drain order: 1st place is the last marble into the hole.
"""
import math

import numpy as np

import settings as S

FPS = S.FPS


def ss5(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * u * (u * (u * 6 - 15) + 10)


def speed(t):
    for k in range(len(S.SPEED) - 1):
        t0, v0 = S.SPEED[k]; t1, v1 = S.SPEED[k + 1]
        if t0 <= t <= t1:
            return v0 + (v1 - v0) * ss5((t - t0) / (t1 - t0))
    return S.SPEED[-1][1]


TG = np.arange(0, S.T_END + 1e-9, 0.0005)
VG = np.array([speed(t) for t in TG])
TAU = np.concatenate([[0.0], np.cumsum(np.diff(TG) / (0.5 * (VG[1:] + VG[:-1])))])
TAU0 = float(np.interp(S.T0, TG, TAU))
TAU = TAU - TAU0
VLEN = float(TAU[-1])
NFR = int(math.floor(VLEN * FPS))


def sim_t(tv):
    return float(np.interp(tv, TAU, TG))


def vid_t(ts):
    return np.interp(ts, TG, TAU)


KEYS = [(t, S.SHOTS[name]) for t, name in S.KEYS]
KV = [float(vid_t(k[0])) for k in KEYS]


def cam_spec(tv):
    for k in range(len(KEYS) - 1):
        if KV[k] <= tv <= KV[k + 1]:
            A = KEYS[k][1]; B = KEYS[k + 1][1]
            if A is B:
                return A
            u = ss5((tv - KV[k]) / (KV[k + 1] - KV[k]))
            out = {}
            out['T'] = tuple(a + (b - a) * u for a, b in zip(A['T'], B['T']))
            out['D'] = math.exp(math.log(A['D']) + (math.log(B['D']) - math.log(A['D'])) * u)
            for key in ('yaw', 'elev', 'hf'):
                out[key] = A[key] + (B[key] - A[key]) * u
            ku = u ** 1.6 if B['kd'] > A['kd'] else 1 - (1 - u) ** 1.6
            out['kd'] = A['kd'] + (B['kd'] - A['kd']) * ku
            return out
    return KEYS[0][1] if tv <= KV[0] else KEYS[-1][1]


def camera_moves(max_len=2.5):
    """Video-time windows of the quick camera moves (for whooshes); slow push-ins are left out."""
    out = []
    for k in range(len(KEYS) - 1):
        if KEYS[k][1] is not KEYS[k + 1][1] and KV[k + 1] - KV[k] <= max_len:
            out.append((KV[k], KV[k + 1]))
    return out


class Episode:
    """The recorded (or simulated) race plus who wears which colour."""

    def __init__(self, path):
        d = np.load(path)
        self.d = d
        self.RX, self.RY, self.RZ, self.RS = d['RX'], d['RY'], d['RZ'], d['RS']
        self.HZ = float(d['rec_hz']); self.NREC = self.RX.shape[0]; self.N = self.RX.shape[1]
        dr = d['drain_t']
        o = np.argsort(dr)
        rest = [int(b) for b in o[:-3] if dr[b] >= 0]
        cand = [b for b in rest if S.FOURTH_OUT_AT - 0.5 < dr[b] < S.FOURTH_OUT_AT + 0.5] or rest
        fourth = min(cand, key=lambda b: abs(dr[b] - S.FOURTH_OUT_AT))
        self.picks = [int(o[-1]), int(o[-2]), int(o[-3]), fourth][:len(S.PLACES)]
        self.btype = np.zeros(self.N, np.int64)
        self.bcol = np.zeros((self.N, 3), np.float64)
        for k, b in enumerate(self.picks):
            self.btype[b] = k + 1
            self.bcol[b] = S.PALETTE[S.PLACES[k]]
        if getattr(S, "TEAM_COLOURS", False):
            self.colour_teams(dr)

    def colour_teams(self, dr):
        """Gives every other marble a team colour, equal teams. A colour only goes to marbles that drain before
        that colour's place marble, so the place marble is its team's last one: 4th place's colour is out when
        it drops, and the winner's colour is the last one left."""
        rng = np.random.default_rng(S.TEAM_SEED)
        k = len(self.picks)
        per = self.N // k
        left = set(range(self.N)) - set(self.picks)
        for place in reversed(range(k)):
            pick = self.picks[place]
            cand = sorted(b for b in left if 0 <= dr[b] < dr[pick])
            n = len(left) if place == 0 else min(per - 1, len(cand))
            chosen = [int(b) for b in rng.choice(cand, size=n, replace=False)] if place else sorted(left)
            for b in chosen:
                self.btype[b] = place + 1
                self.bcol[b] = S.PALETTE[S.PLACES[place]]
            left -= set(chosen)

    def places(self):
        dr = self.d['drain_t']
        return [dict(place=k + 1, colour=S.PLACES[k], marble=b, out_sim_s=round(float(dr[b]), 3),
                     out_video_s=round(float(vid_t(dr[b])), 3)) for k, b in enumerate(self.picks)]

    def pos_at(self, t):
        RX, RY, RZ, RS = self.RX, self.RY, self.RZ, self.RS
        fi = t * self.HZ
        i0 = min(int(math.floor(fi)), self.NREC - 1); i1 = min(i0 + 1, self.NREC - 1)
        a = fi - i0
        st = RS[i0].astype(np.int64)
        same = RS[i1] == RS[i0]
        x = RX[i0].astype(np.float64); y = RY[i0].astype(np.float64); z = RZ[i0].astype(np.float64)
        x = np.where(same, x * (1 - a) + RX[i1] * a, x)
        y = np.where(same, y * (1 - a) + RY[i1] * a, y)
        z = np.where(same, z * (1 - a) + RZ[i1] * a, z)
        return x, y, z, st

    def frame_inputs(self, n, rd):
        tv = n / FPS
        t = sim_t(tv)
        spec = cam_spec(tv)
        cam = rd.make_cam(spec['T'], spec['D'], spec['yaw'], spec['elev'], spec['hf'])
        x, y, z, st = self.pos_at(t)
        v = speed(t)
        dlt = v * 0.5 * S.SHUT / FPS
        xp, yp, zp, sp = self.pos_at(max(t - dlt, 0.0))
        xn, yn, zn, sn = self.pos_at(min(t + dlt, S.T_END))
        subs = [None] * self.N
        for b in np.where(st == 1)[0]:
            p0 = rd.project(cam, x[b], y[b], z[b])
            if p0[2] < 1.0:
                continue
            op = np.zeros(2); on = np.zeros(2)
            if sp[b] == 1:
                pp = rd.project(cam, xp[b], yp[b], zp[b]); op = np.array([pp[0] - p0[0], pp[1] - p0[1]])
            if sn[b] == 1:
                pn = rd.project(cam, xn[b], yn[b], zn[b]); on = np.array([pn[0] - p0[0], pn[1] - p0[1]])
            L = np.hypot(*op) + np.hypot(*on)
            rp = cam[12] / p0[2]
            kmax = int(max(8, min(48, 5000.0 / (rp + 1.0))))
            K = int(min(kmax, max(1, math.ceil(L / 0.6))))
            if K == 1:
                continue
            s = np.linspace(-1, 1, K)
            subs[b] = np.where(s[:, None] < 0, -s[:, None] * op[None, :], s[:, None] * on[None, :])
        return cam, x, y, z, st, subs, spec['kd'], spec['D'], t
