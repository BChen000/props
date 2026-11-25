"""Settings for the "1 KG vs 1,000 KG Ball Smashing Glass" Shorts.

A steel ball drops on a floating stack of rainbow glass panes; every heavier ball breaks one more pane.
Everything generated goes to build/ (sims ~400 MB, frames ~1 GB); don't commit it.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, 'build')
PLATES = os.path.join(BUILD, 'plates')
SIMS = os.path.join(BUILD, 'sims')
FRAMES = os.path.join(BUILD, 'frames')
FINAL = os.path.join(BUILD, 'final')
OUT = os.path.join(BUILD, 'out')
TIMELINE = os.path.join(BUILD, 'timeline.json')

import math

N_P = 6
HALF = 0.5
T = 0.025
GAP = 0.16
Z_BOT = 0.36
FPS = 30
RHO_STEEL = 7850.0
RHO_GLASS = 2500.0

STAGES = [
    dict(label="1", kg=1, brk=0),
    dict(label="10", kg=10, brk=1),
    dict(label="50", kg=50, brk=2),
    dict(label="100", kg=100, brk=3),
    dict(label="250", kg=250, brk=4),
    dict(label="500", kg=500, brk=5),
    dict(label="1,000", kg=1000, brk=6),
]

PANE_COLORS = [
    (0.74, 0.54, 1.00),
    (0.36, 0.68, 1.00),
    (0.30, 0.88, 0.52),
    (1.00, 0.86, 0.22),
    (1.00, 0.56, 0.18),
    (1.00, 0.28, 0.34),
]


def pane_z(k):
    return Z_BOT + (N_P - 1 - k) * GAP


def ball_r(kg):
    return (3 * kg / (4 * math.pi * RHO_STEEL)) ** (1 / 3)


SIM_ARGS = [
    '--frames 90 --bx 0.01 --by 0.012',
    '--frames 110 --bx 0.02 --by -0.02',
    '--frames 115 --bx -0.02 --by 0.015',
    '--frames 120 --bx -0.025 --by -0.01',
    '--frames 125 --bx 0.025 --by 0.01',
    '--frames 130 --bx -0.015 --by -0.02',
    '--frames 150 --bx 0.015 --by -0.01',
]
HOLD = 6
END = [64, 80, 80, 84, 84, 88, 118]

SPP = 10
CATCHER_SPP = 8
CATCHER_DIV = 6
MAIN_SCALE = 0.8
CHUNK = 48

THUMB_FRAME = 551
THUMB_ZOOM = 1.3
THUMB_CENTER = (520, 1080)

WIDTH, HEIGHT = 1080, 1920
