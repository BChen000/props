"""Plate coverage check for moving-camera shots: how far each frame's corners land outside plate.png
(negative = inside, in plate pixels). Positive values mean smeared edge pixels in the composite.
  python3 plate_cover.py [SHOTS_DIR]
A shot is checked from its render (plate_cam.json + meta.json + plate.png) and, before rendering, from a
camera dry run, cams_dry.json: {"res", "frames": {f: {"cam"}}, "plate", "plate_res"} (see the episode's
flight_common.run_flight `camonly`).
"""
import json, numpy as np, os, sys, cv2
S = os.path.join(sys.argv[1] if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]) else os.environ.get('CPR_SHOTS', os.path.join(os.getcwd(), 'build', 'shots')), '')


def overflow(res, frames, pc, Wp, Hp):
    W, H = res
    Rp = np.array(pc['mw'])[:3, :3]; fp = pc['lens'] / pc['sensor'] * Wp
    worst = -1e9; wf = None
    for k, fr in frames.items():
        R = np.array(fr['cam']['mw'])[:3, :3]; fl = fr['cam']['lens'] / fr['cam']['sensor'] * W
        for (u, v) in ((0, 0), (W, 0), (0, H), (W, H), (W / 2, 0), (W / 2, H), (0, H / 2), (W, H / 2)):
            dc = np.array([(u - W / 2) / fl, (H / 2 - v) / fl, -1.0]); dp = Rp.T @ (R @ dc)
            if dp[2] >= 0:
                o = 1e6
            else:
                px = Wp / 2 + fp * dp[0] / -dp[2]; py = Hp / 2 - fp * dp[1] / -dp[2]
                o = max(-px, px - Wp, -py, py - Hp)
            if o > worst:
                worst = o; wf = k
    return worst, wf


for name in sorted(os.listdir(S)):
    d = S + name + '/'
    if os.path.exists(d + 'plate_cam.json') and os.path.exists(d + 'meta.json') and os.path.exists(d + 'plate.png'):
        pc = json.load(open(d + 'plate_cam.json'))
        m = json.load(open(d + 'meta.json'))
        Hp, Wp = cv2.imread(d + 'plate.png').shape[:2]
        worst, wf = overflow(m['res'], m['frames'], pc, Wp, Hp)
        print(f'{name:5s} plate {Wp}x{Hp} frames {len(m["frames"])} worst overflow {worst:8.1f} px (frame {wf})')
    if os.path.exists(d + 'cams_dry.json'):
        c = json.load(open(d + 'cams_dry.json'))
        Wp, Hp = c['plate_res']
        worst, wf = overflow(c['res'], c['frames'], c['plate'], Wp, Hp)
        print(f'{name:5s} plate {Wp}x{Hp} frames {len(c["frames"])} worst overflow {worst:8.1f} px (frame {wf}) [dry run]')
