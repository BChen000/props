"""The kit's compositor (../marble-raytrace-kit/compositor.py) with a moving set and steel balls.

The set is path-traced once level (the base G-buffer), and once per beam pose only inside the window that the beam,
the baskets and their shadows can touch (boxtrace's crop). Before each frame the window of the G-buffer is swapped
for the frame's pose, so the marbles' shadows, contact AO and depth tests all see the beam where it is. Marble
lighting (the ambient cube etc.) is traced against the box scene with the beam in that pose. Steel balls are drawn
as polished metal: a dark base colour, strong Fresnel reflection of the room and a hard highlight.
"""
import math
import os

import numpy as np

import compositor as CO
import scene as S
import settings as C

STEEL_F0 = 0.78
STEEL_ALBEDO = (52, 54, 58)
STEEL_SKY_H = (0.10, 0.105, 0.115)    # what a steel ball reflects: a dark band at the horizon...
STEEL_SKY_Z = (1.15, 1.17, 1.20)      # ...and a bright room above (the classic polished-ball look)
FEATHER = 40      # px (at 1080 wide, 2x set): the pose window fades into the level set over this margin


def pose_tag(q):
    q = round(float(q), 3) + 0.0          # -0.0 and 0.0 are the same pose
    return f"{q:+.3f}".replace("+", "p").replace("-", "m").replace(".", "_")


class BalanceCompositor(CO.Compositor):
    def __init__(self, base_prefix, pose_dir, window, tl, watermark=None):
        self.tl = tl
        self.win = window
        self.pose_dir = pose_dir
        self.metal = list(tl["metal"])
        cols = [STEEL_ALBEDO if mt else c for c, mt in zip(tl["colors"], self.metal)]
        self._env_cache = {}
        self._pose = None
        self._box_cache = {}
        super().__init__(base_prefix, tl["pos"], tl["vis"], cols, [], titles=[], watermark=watermark,
                         env_fn=self.env)
        x0, y0, w, h = window
        self._vig = self.vig[y0 // 2:(y0 + h) // 2, x0 // 2:(x0 + w) // 2]
        # far from the seesaw a pose differs from the level set only by noise in a few ambient rays: fade it in
        fz = FEATHER * CO.W2 / 1080.0
        wx = np.ones(w)
        wy = np.ones(h)
        r = np.arange(w)
        if x0 > 0:
            wx = np.minimum(wx, np.clip((r + 0.5) / fz, 0, 1))
        if x0 + w < CO.W2:
            wx = np.minimum(wx, np.clip((w - r - 0.5) / fz, 0, 1))
        r = np.arange(h)
        if y0 > 0:
            wy = np.minimum(wy, np.clip((r + 0.5) / fz, 0, 1))
        if y0 + h < CO.H2:
            wy = np.minimum(wy, np.clip((h - r - 0.5) / fz, 0, 1))
        wgt = (wy[:, None] * wx[None, :]).astype(np.float32)
        self._wgt = (wgt * wgt * (3 - 2 * wgt))[..., None]
        self._base = {k: getattr(self, k)[y0:y0 + h, x0:x0 + w].copy() for k in ("D", "A", "O")}

    # ------------------------------------------------------------------ the set in the frame's pose
    def set_pose(self, q):
        if q == self._pose:
            return
        x0, y0, w, h = self.win
        pre = os.path.join(self.pose_dir, "t_" + pose_tag(q))
        wg = self._wgt
        D = np.fromfile(pre + "_D.f32", np.float32).reshape(h, w, 3) * wg + self._base["D"] * (1 - wg)
        A = np.fromfile(pre + "_A.f32", np.float32).reshape(h, w, 3) * wg + self._base["A"] * (1 - wg)
        O = np.fromfile(pre + "_O.f32", np.float32).reshape(h, w, 3) * wg + self._base["O"] * (1 - wg)
        self.D[y0:y0 + h, x0:x0 + w] = D
        self.A[y0:y0 + h, x0:x0 + w] = A
        self.O[y0:y0 + h, x0:x0 + w] = O
        self.Z[y0:y0 + h, x0:x0 + w] = np.fromfile(pre + "_Z.f32", np.float32).reshape(h, w)
        self.N[y0:y0 + h, x0:x0 + w] = np.fromfile(pre + "_N.f32", np.float32).reshape(h, w, 3)
        self.I[y0:y0 + h, x0:x0 + w] = np.fromfile(pre + "_I.u8", np.uint8).reshape(h, w)
        l1 = CO.down2(D + A + O).astype(np.float32)
        self.L1[y0 // 2:(y0 + h) // 2, x0 // 2:(x0 + w) // 2] = l1
        self.static8[y0 // 2:(y0 + h) // 2, x0 // 2:(x0 + w) // 2] = (
            CO.tonemap(l1 * self._vig) * 255 + 0.5).astype(np.uint8)
        self._set_boxes(q)
        self._pose = q

    def _set_boxes(self, q):
        if q not in self._box_cache:
            bx = S.boxes(math.radians(q))
            self._box_cache[q] = (bx, np.array([b["mn"] for b in bx]), np.array([b["mx"] for b in bx]),
                                  np.array([b["rot"] for b in bx]), np.array([b["piv"] for b in bx]),
                                  np.array([b["alb"] for b in bx]))
        CO.BOXES, CO.BMN, CO.BMX, CO.BROT, CO.BPIV, CO.BALB = self._box_cache[q]

    def env(self, f, m, c):
        key = (m, tuple(np.round(c, 2)), self._pose)
        e = self._env_cache.get(key)
        if e is None:
            e = CO.marble_env(c)
            if len(self._env_cache) > 20000:
                self._env_cache.clear()
            self._env_cache[key] = e
        return e

    def render(self, f, title=False, watermark=True):
        self.set_pose(float(self.tl["theta_q"][f]))
        return super().render(f, title=title, watermark=watermark)

    # ------------------------------------------------------------------ steel
    def draw_marble(self, act, i, b, rc, dirs, Lc, zb, acov, glows):
        if not self.metal[act[i][0]]:
            return super().draw_marble(act, i, b, rc, dirs, Lc, zb, acov, glows)
        old = CO.F0, S.SKY_H, S.SKY_Z
        CO.F0, S.SKY_H, S.SKY_Z = STEEL_F0, np.array(STEEL_SKY_H), np.array(STEEL_SKY_Z)
        try:
            return super().draw_marble(act, i, b, rc, dirs, Lc, zb, acov, glows)
        finally:
            CO.F0, S.SKY_H, S.SKY_Z = old
