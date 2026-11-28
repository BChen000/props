"""Where everything sits. The room is at the origin (the man stands at 0,0 facing -Y); the desert and the hangar
are far away from it so that each shot only sees its own set."""
import numpy as np

WALL_Y = 1.40
BOARD = dict(cx=0.0, cz=1.62, w=2.6, h=1.6, y=WALL_Y - 0.03)
CORK_Y = BOARD['y'] - 0.012
# board items: name -> (x, z, rot_deg, height); width follows the texture's aspect
ITEMS = {
    'p_header': (0.02, 2.24, -1.5, 0.20),
    'p_cal': (-0.98, 1.93, 4, 0.33),
    'p_clip': (-0.52, 1.50, -3, 0.38),
    'p_forum': (-1.02, 1.22, -2, 0.27),
    'p_stat': (-0.30, 1.02, 3, 0.26),
    'p_farm': (0.62, 1.94, 3, 0.27),
    'p_quote': (0.70, 1.45, 2, 0.27),
    'p_shrimp': (1.06, 1.12, -4, 0.28),
    'p_q': (1.12, 1.93, 6, 0.24),
    'n_who': (-0.36, 2.02, -6, 0.13),
    'n_bots': (0.22, 1.66, 5, 0.13),
    'n_2016': (-1.10, 1.58, 8, 0.12),
    'n_likes': (0.36, 1.07, -5, 0.13),
    'n_amen': (1.17, 1.56, 4, 0.12),
}
PIN_COL = {'p_header': (0.75, 0.05, 0.05), 'p_cal': (0.85, 0.85, 0.85), 'p_clip': (0.75, 0.05, 0.05),
           'p_forum': (0.1, 0.3, 0.8), 'p_stat': (0.85, 0.7, 0.1), 'p_farm': (0.75, 0.05, 0.05),
           'p_quote': (0.75, 0.05, 0.05), 'p_shrimp': (0.1, 0.6, 0.2), 'p_q': (0.85, 0.85, 0.85)}
STRINGS = [('p_header', 'p_cal'), ('p_cal', 'p_clip'), ('p_clip', 'p_forum'), ('p_clip', 'p_stat'), ('p_header', 'p_farm'),
           ('p_farm', 'p_quote'), ('p_quote', 'p_shrimp'), ('p_farm', 'p_q'), ('p_stat', 'p_quote'), ('p_cal', 'p_farm'),
           ('p_forum', 'p_stat'), ('p_q', 'p_shrimp')]

LAMP = np.array([0.0, -0.42, 2.50])        # bulb centre
DESK = dict(x=1.30, y=0.45, rot=-24.0, top=0.76)
CRT_SCREEN_LOCAL = (0.0, -0.205, 0.215)     # screen centre in the CRT's frame (CRT sits on the desk top)
PHONE_LOCAL = (-0.38, -0.12)                # phone on the desk, desk-local xy

DESERT = np.array([3000.0, 0.0, 0.0])     # terrain, runway, hangars, mountains, sky; the gate is at DESERT + GATE
GATE = np.array([0.0, -520.0, 0.0])
HANGAR = np.array([-3000.0, 0.0, 0.0])    # inside a hangar: nine saucers


def item_size(name, tex_wh):
    x, z, rot, h = ITEMS[name]
    w = h * tex_wh[0] / tex_wh[1]
    return w, h


def pin_pos(name, tex_wh):
    x, z, rot, h = ITEMS[name]
    w, h = item_size(name, tex_wh)
    a = np.radians(rot)
    top = np.array([0.0, h / 2 - 0.025])
    dx = top[0] * np.cos(a) - top[1] * np.sin(a)
    dz = top[0] * np.sin(a) + top[1] * np.cos(a)
    return np.array([x + dx, CORK_Y - 0.018, z + dz])


def desk_frame():
    a = np.radians(DESK['rot'])
    R = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    return R, np.array([DESK['x'], DESK['y'], 0.0])
