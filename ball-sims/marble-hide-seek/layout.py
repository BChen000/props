"""The hide-and-seek playground: wooden hiding places on a felt mat, and where marbles hide and the seeker looks.

    pieces()   blocks as dicts: name, lo, hi (box), carved (bool), oid; carved pieces get the tubes from carves()
    carves()   (polyline, radius) tunnels cut through the carved blocks
    SPOTS      name -> dict(hide=(x, z) where a marble hides, look=(x, z) where the seeker stands to check it,
               exit=[(x, z), ...] how a found marble leaves it, hop=True if it has to jump a wall to get out)
    blocked(x, z)  True where a marble center can't be (inside a block, with a marble radius of margin)

Ground plan (x right, z toward the camera), seen from above:
    back row     tunnel (left)                pen (right)
    middle row   stack (left)     base tower (center, where the seeker counts)     bridge (right)
    front row    corner walls (left)                arch (right)
    front edge   the row where found marbles wait
"""
import numpy as np

from settings import B, R, RT, WALL_H, WALL_T, MAT_T

MAT_Y = MAT_T + R                     # marble center height on the mat
Y0 = MAT_T                            # blocks stand on the mat

OID_FLOOR, OID_WALL, OID_BASEBOARD, OID_MAT = 0, 2, 3, 4
OID_BLOCK0 = 10

# block centers (x, z) and footprints
BASE = (0.0, -9.0)                    # 2 cubes stacked
STACK = (-14.0, -7.0)                 # 2 cubes stacked
TUNNEL = (-12.5, -25.0)               # 1 cube, tunnel along x
PEN = (13.2, -25.0)                   # open box: outer size 9 x 9
PEN_OUT = 9.0
BRIDGE = (14.6, -7.0)                 # two pillars and a beam across, the gap along x
BRIDGE_GAP = 4.8
ARCH = (14.6, 8.0)                    # 1 cube, tunnel along z
CORNER = (-12.0, 8.0)                 # L of two low walls: right side and back side of the hiding spot
FOUND_Z = 16.4                        # found marbles line up here
FOUND_X = [-10.0, -6.0, -2.0, 2.0, 6.0, 10.0]
SEEKER_START = (0.0, BASE[1] + B / 2 + R + 0.35)


def pieces():
    out = []
    oid = [OID_BLOCK0]

    def add(name, lo, hi, carved=False):
        out.append(dict(name=name, lo=np.array(lo, float), hi=np.array(hi, float), carved=carved, oid=oid[0]))
        oid[0] += 1

    def cube(name, cx, cz, level=0, carved=False):
        add(name, (cx - B / 2, Y0 + level * B, cz - B / 2), (cx + B / 2, Y0 + (level + 1) * B, cz + B / 2), carved)

    cube("base0", *BASE)
    cube("base1", *BASE, level=1)
    cube("stack0", *STACK)
    cube("stack1", *STACK, level=1)
    cube("tunnel", *TUNNEL, carved=True)
    cube("arch", *ARCH, carved=True)
    px, pz = PEN
    h = PEN_OUT / 2
    add("pen_back", (px - h, Y0, pz - h), (px + h, Y0 + WALL_H, pz - h + WALL_T))
    add("pen_front", (px - h, Y0, pz + h - WALL_T), (px + h, Y0 + WALL_H, pz + h))
    add("pen_left", (px - h, Y0, pz - h + WALL_T), (px - h + WALL_T, Y0 + WALL_H, pz + h - WALL_T))
    add("pen_right", (px + h - WALL_T, Y0, pz - h + WALL_T), (px + h, Y0 + WALL_H, pz + h - WALL_T))
    bx, bz = BRIDGE
    pw = 3.2
    g = BRIDGE_GAP / 2
    add("bridge_l", (bx - g - pw, Y0, bz - pw / 2), (bx - g, Y0 + 4.8, bz + pw / 2))
    add("bridge_r", (bx + g, Y0, bz - pw / 2), (bx + g + pw, Y0 + 4.8, bz + pw / 2))
    add("bridge_top", (bx - g - pw - 0.4, Y0 + 4.8, bz - pw / 2 - 0.2), (bx + g + pw + 0.4, Y0 + 6.4, bz + pw / 2 + 0.2))
    cx, cz = CORNER
    add("corner_side", (cx + 1.6, Y0, cz - 3.2), (cx + 1.6 + WALL_T, Y0 + WALL_H + 0.6, cz + 4.4))
    add("corner_back", (cx - 5.6, Y0, cz - 3.2), (cx + 1.6 + WALL_T, Y0 + WALL_H + 0.6, cz - 3.2 + WALL_T))
    return out


TUNNEL_Y = MAT_T + RT - 0.04          # tunnel floors are level with the mat


def carves():
    tx, tz = TUNNEL
    ax, az = ARCH
    return [(np.array([[tx - B, TUNNEL_Y, tz], [tx + B, TUNNEL_Y, tz]]), RT),
            (np.array([[ax, TUNNEL_Y, az - B], [ax, TUNNEL_Y, az + B]]), RT)]


SPOTS = {
    "base":   dict(hide=(0.4, BASE[1] - B / 2 - R - 0.5), look=SEEKER_START, exit=[(4.6, -15.0), (5.0, -3.0), (0.0, 6.0)]),
    "stack":  dict(hide=(-14.0, STACK[1] - B / 2 - R - 0.5), look=(-8.4, -11.8),
                   exit=[(-8.6, -11.0), (-7.6, 2.0)]),
    "tunnel": dict(hide=(TUNNEL[0], TUNNEL[1]), look=(TUNNEL[0] + B / 2 + 2.2, TUNNEL[1]),
                   exit=[(TUNNEL[0] - B / 2 - 2.4, TUNNEL[1]), (-19.0, -17.0), (-19.0, 0.5), (-15.0, 4.0)]),
    "pen":    dict(hide=(PEN[0], PEN[1]), look=(PEN[0] - PEN_OUT / 2 - R - 0.9, PEN[1] + 0.5), hop=True,
                   exit=[(PEN[0] - PEN_OUT / 2 - 2.2, PEN[1] + 3.5), (6.0, -16.0), (6.0, 1.0)]),
    "bridge": dict(hide=(BRIDGE[0], BRIDGE[1]), look=(BRIDGE[0] - 3.0, BRIDGE[1] + 6.2), exit=[(BRIDGE[0], 1.5)]),
    "corner": dict(hide=(CORNER[0] - 2.6, CORNER[1] + 1.6), look=(CORNER[0] + 5.6, CORNER[1] - 6.0),
                   exit=[(CORNER[0] - 2.6, CORNER[1] + 7.0)]),
    "arch":   dict(hide=(ARCH[0], ARCH[1]), look=(ARCH[0] - B / 2 - R - 1.0, ARCH[1] - B / 2 - R - 0.6), exit=[]),
}


def blocked(x, z, margin=None):
    """True where a marble center at (x, z) on the mat would overlap a block (tunnels count as free)."""
    m = R + 0.05 if margin is None else margin
    x, z = np.asarray(x, float), np.asarray(z, float)
    out = np.zeros(np.broadcast(x, z).shape, bool)
    for pc in pieces():
        lo, hi = pc["lo"], pc["hi"]
        if lo[1] > MAT_Y + R:                       # bridge deck, upper cubes: marbles pass underneath
            continue
        inside = (x > lo[0] - m) & (x < hi[0] + m) & (z > lo[2] - m) & (z < hi[2] + m)
        if pc["name"] == "tunnel":
            inside &= ~(np.abs(z - TUNNEL[1]) < RT - R + 0.05)
        if pc["name"] == "arch":
            inside &= ~(np.abs(x - ARCH[0]) < RT - R + 0.05)
        out |= inside
    return out
