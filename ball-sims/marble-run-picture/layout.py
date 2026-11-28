"""The marble run: blocks, the grooves and holes carved into them, and the path a marble's center follows.

Rows step down one cube and forward one row at a time (a wooden staircase); every level ends in a U-turn on a
block that sits on the next level, and the U-turn ends in a hole that drops the marble into the next level's groove,
which tunnels out from under that block. The last level drops through a hole and out of the front face onto the mat.

    pieces()      list of dicts: name, lo, hi (box), carved (bool), oid, top (optional wavy top: x -> y)
    carves()      list of (polyline Nx3, radius): tubes cut out of every carved piece (grooves, holes, tunnels)
    marble_path() dense polyline of the marble center from the rail to the mat, plus its arc length and tags
    EXIT          the point on the front face where marbles roll out onto the mat
"""
import math

import numpy as np

from settings import (B, RG, RH, NCOL, X0, NROW, TURN_R, TURN_IN, WAVE_A, WAVE_N, MEANDER_A, MEANDER_N, BEAM_W,
                      BEAM_H, RAIL_END, RAIL_POSTS, BRIDGE_COL, EXIT_COL, R, MAT_T)

DROP = RG - R                       # a marble in a groove sits this far below the groove's centerline


def xl(c):
    return X0 + c * B


def xr(c):
    return X0 + (c + 1) * B


def xc(c):
    return X0 + (c + 0.5) * B


def zb(r):
    return -(NROW - r) * B


def zf(r):
    return zb(r) + B


def zc(r):
    return zb(r) + B / 2


Y1, Y2, Y3, Y4 = 4 * B, 3 * B, 2 * B, 1 * B      # tops of levels 1-4 (rows 1-4); the rail (row 0) is at Y1
TUNNEL_Y = MAT_T + R + 0.25                       # exit tunnel center: its floor is level with the mat
MAT_Y = MAT_T + R                                 # marble center height on the mat
EXIT = np.array([xc(EXIT_COL), MAT_Y, 0.0])

OID_FLOOR, OID_WALL, OID_BASEBOARD, OID_MAT, OID_POST = 0, 2, 3, 4, 5
OID_BLOCK0 = 10


def wave_top(x):
    """Top of the wave piece (and its groove centerline) between the tower and the first end block."""
    a, b = xr(0), xl(NCOL - 1)
    u = np.clip((np.asarray(x, float) - a) / (b - a), 0, 1)
    return Y1 - WAVE_A * (1 - np.cos(2 * np.pi * WAVE_N * u))


def meander_z(x):
    a, b = xl(NCOL - 1), xr(0)
    u = np.clip((np.asarray(x, float) - a) / (b - a), 0, 1)
    return zc(2) + MEANDER_A * np.sin(2 * np.pi * MEANDER_N * u)


def pieces():
    out = []
    oid = [OID_BLOCK0]

    def add(name, lo, hi, carved=False, top=None):
        out.append(dict(name=name, lo=np.array(lo, float), hi=np.array(hi, float), carved=carved, oid=oid[0],
                        top=top))
        oid[0] += 1

    def cube(c, r, j, carved=False, name=None):
        add(name or f"cube_c{c}r{r}y{j}", (xl(c), j * B, zb(r)), (xr(c), (j + 1) * B, zf(r)), carved)

    for j in range(3):                                 # tower under the first U-turn
        for r in (0, 1):
            cube(0, r, j)
    add("uturn0", (xl(0), 3 * B, zb(0)), (xr(0), 4 * B, zf(1)), True)
    add("rail", (xr(0), Y1 - BEAM_H, zc(0) - BEAM_W / 2), (RAIL_END, Y1, zc(0) + BEAM_W / 2), True)
    add("wave", (xr(0), Y1 - BEAM_H, zc(1) - BEAM_W / 2), (xl(NCOL - 1), Y1, zc(1) + BEAM_W / 2), True,
        top=wave_top)
    for j in range(3):                                 # under the back half of end block 1
        cube(NCOL - 1, 1, j)
    add("end1", (xl(NCOL - 1), 3 * B, zb(1)), (xr(NCOL - 1), 4 * B, zf(2)), True)
    for c in range(NCOL):                              # row 2: level 2 at Y2
        for j in range(2):
            cube(c, 2, j)
        if c > 0:
            cube(c, 2, 2, True, f"level2_c{c}")
    add("end2", (xl(0), 2 * B, zb(2)), (xr(0), 3 * B, zf(3)), True)
    for c in range(NCOL):                              # row 3: level 3 at Y3
        cube(c, 3, 0)
        if c < NCOL - 1:
            cube(c, 3, 1, True, f"level3_c{c}")
    if BRIDGE_COL is not None:
        cube(BRIDGE_COL, 3, 2, True, "bridge")
    add("end3", (xl(NCOL - 1), 1 * B, zb(3)), (xr(NCOL - 1), 2 * B, zf(4)), True)
    for c in range(NCOL):                              # row 4: level 4 at Y4, exit hole in EXIT_COL
        cube(c, 4, 0, c > 0, f"level4_c{c}" if c > 0 else None)
    for k, x in enumerate(RAIL_POSTS):
        add(f"post{k}", (x - 0.9, 0.0, zc(0) - BEAM_W * 0.4), (x + 0.9, Y1 - BEAM_H, zc(0) + BEAM_W * 0.4))
    return out


def _line(p0, p1, n=None):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    if n is None:
        n = max(2, int(np.linalg.norm(p1 - p0) / 0.2) + 1)
    return np.linspace(p0, p1, n)


def grooves():
    """Groove centerlines at the block tops, level by level, each as one polyline (direction of travel)."""
    ux0 = xr(0) - TURN_IN                 # U-turn centers sit TURN_IN inside the end blocks
    ux1 = xl(NCOL - 1) + TURN_IN
    g = {}
    g["rail"] = _line((RAIL_END + 4, Y1, zc(0)), (xr(0), Y1, zc(0)))
    a = np.linspace(0, math.pi, 64)
    arc0 = np.stack([ux0 - TURN_R * np.sin(a), np.full_like(a, Y1), zb(1) - TURN_R * np.cos(a)], 1)
    g["u0"] = np.concatenate([_line((xr(0), Y1, zc(0)), (ux0, Y1, zc(0)), 6)[:-1], arc0[:-1],
                              _line((ux0, Y1, zc(1)), (xr(0), Y1, zc(1)), 6)])
    xs = np.linspace(xr(0), xl(NCOL - 1), 241)
    g["wave"] = np.stack([xs, wave_top(xs), np.full_like(xs, zc(1))], 1)
    arc1 = np.stack([ux1 + TURN_R * np.sin(a), np.full_like(a, Y1), zb(2) - TURN_R * np.cos(a)], 1)
    g["u1"] = np.concatenate([_line((xl(NCOL - 1), Y1, zc(1)), (ux1, Y1, zc(1)), 6)[:-1], arc1])
    g["hole1"] = np.array([[ux1, Y1 + 2.0, zc(2)], [ux1, Y2, zc(2)]])
    xs = np.linspace(xl(NCOL - 1), xr(0), 321)
    g["level2"] = np.concatenate([_line((ux1, Y2, zc(2)), (xl(NCOL - 1), Y2, zc(2)), 6)[:-1],
                                  np.stack([xs, np.full_like(xs, Y2), meander_z(xs)], 1)[:-1],
                                  _line((xr(0), Y2, zc(2)), (ux0, Y2, zc(2)), 6)])
    arc2 = np.stack([ux0 - TURN_R * np.sin(a), np.full_like(a, Y2), zb(3) - TURN_R * np.cos(a)], 1)
    g["u2"] = arc2
    g["hole2"] = np.array([[ux0, Y2 + 2.0, zc(3)], [ux0, Y3, zc(3)]])
    g["level3"] = _line((ux0, Y3, zc(3)), (ux1, Y3, zc(3)))
    arc3 = np.stack([ux1 + TURN_R * np.sin(a), np.full_like(a, Y3), zb(4) - TURN_R * np.cos(a)], 1)
    g["u3"] = arc3
    g["hole3"] = np.array([[ux1, Y3 + 2.0, zc(4)], [ux1, Y4, zc(4)]])
    g["level4"] = _line((ux1, Y4, zc(4)), (xc(EXIT_COL), Y4, zc(4)))
    g["hole4"] = np.array([[xc(EXIT_COL), Y4 + 2.0, zc(4)], [xc(EXIT_COL), TUNNEL_Y, zc(4)]])
    g["exit"] = np.array([[xc(EXIT_COL), TUNNEL_Y, zc(4)], [xc(EXIT_COL), TUNNEL_Y, 3.0]])
    return g


def carves():
    g = grooves()
    out = []
    for k, pl in g.items():
        out.append((pl, RH if (k.startswith("hole") or k == "exit") else RG))
    return out


def marble_path(ds=0.05):
    """Dense marble-center path from the start of the first U-turn to the front face.
    Returns pts (N x 3), s (arc length, 0 at the first U-turn), and per-point tags:
      'roll' in a groove, 'drop' falling down a hole, 'tunnel' rolling inside the block, 'exit' rolling out."""
    g = grooves()
    segs = []

    def groove(name, tag="roll"):
        p = g[name].copy()
        p[:, 1] -= DROP
        segs.append((p, tag))

    groove("u0")
    groove("wave")
    groove("u1")
    hole_drops = [("hole1", Y2), ("hole2", Y3), ("hole3", Y4)]
    nxt = ["level2", "level3", "level4"]
    turns = ["u2", "u3"]
    for i, (h, ybot) in enumerate(hole_drops):
        top = segs[-1][0][-1]
        segs.append((np.array([top, [top[0], ybot - DROP, top[2]]]), "drop"))
        groove(nxt[i])
        if i < 2:
            groove(turns[i])
    last = segs[-1][0][-1]
    segs.append((np.array([last, [last[0], MAT_Y, last[2]]]), "drop"))
    segs.append((np.array([[last[0], MAT_Y, last[2]], [last[0], MAT_Y, 0.0]]), "exit"))
    pts, tags = [], []
    for p, tag in segs:
        d = np.linalg.norm(np.diff(p, axis=0), axis=1)
        s = np.concatenate([[0], np.cumsum(d)])
        n = max(2, int(math.ceil(s[-1] / ds)) + 1)
        si = np.linspace(0, s[-1], n)
        q = np.stack([np.interp(si, s, p[:, k]) for k in range(3)], 1)
        if pts:
            q = q[1:]
        pts.append(q)
        tags += [tag] * len(q)
    pts = np.concatenate(pts)
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    return pts, s, np.array(tags)


def rail_point(s):
    """Queue position for s < 0 (on the rail, right of the first U-turn's start)."""
    s = np.asarray(s, float)
    return np.stack([xr(0) - s, np.full_like(s, Y1 - DROP), np.full_like(s, zc(0))], -1)


def covered(p):
    """True where a marble center is hidden inside the blocks (holes, tunnels under end blocks and the bridge)."""
    p = np.atleast_2d(p)
    hid = np.zeros(len(p), bool)
    for pc in pieces():
        lo, hi = pc["lo"], pc["hi"]
        inside = np.all((p > lo + 1.15) & (p < hi - 1.15), axis=1)
        top_cover = (p[:, 1] < hi[1] - 1.9) & np.all((p[:, [0, 2]] > lo[[0, 2]] + 1.15) &
                                                    (p[:, [0, 2]] < hi[[0, 2]] - 1.15), axis=1) & (p[:, 1] > lo[1] - 2)
        hid |= inside | top_cover
    hid |= (p[:, 2] < -1.15) & (p[:, 1] < MAT_Y + 0.5) & (np.abs(p[:, 0] - EXIT[0]) < 3)
    return hid


if __name__ == "__main__":
    pts, s, tags = marble_path()
    print("path length", s[-1], "points", len(pts))
    for t in ("roll", "drop", "exit"):
        print(t, (tags == t).sum() * 0.05)
    print("pieces", len(pieces()), "carved", sum(p["carved"] for p in pieces()))
    hid = covered(pts)
    print("hidden fraction", hid.mean())
