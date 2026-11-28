"""Named gestures for the hooded man, in torso space (origin at the hips pivot; shoulders at about z=+0.42)."""
from man import REST, rest_arm

ARMS_DOWN = dict(R=rest_arm('R'), L=rest_arm('L'))
G = {
    'rest': {},
    'explain_R': dict(R=dict(w=(-0.20, -0.30, 0.22), f=(0.15, -0.85, 0.35), p=(0.1, 0.1, 1), g='open')),
    'present_R': dict(R=dict(w=(-0.36, -0.20, 0.30), f=(-0.75, -0.55, 0.25), p=(0.1, -0.3, 1), g='open')),
    'point_back_R': dict(R=dict(w=(-0.42, -0.02, 0.48), f=(-0.85, 0.40, 0.25), p=(0, -0.3, -1), g='point', pole=(0, 0.1, -0.1))),
    'finger_up_R': dict(R=dict(w=(-0.12, -0.28, 0.43), f=(0.05, -0.1, 1), p=(0.15, -1, 0), g='point')),
    'shrug': dict(R=dict(w=(-0.32, -0.24, 0.22), f=(-0.45, -0.75, 0.3), p=(0, 0, 1), g='open'),
                  L=dict(w=(0.32, -0.24, 0.22), f=(0.45, -0.75, 0.3), p=(0, 0, 1), g='open'), head=(-2, 0, 8)),
    'point_cam_R': dict(R=dict(w=(-0.05, -0.40, 0.50), f=(0.08, -1, 0.17), p=(0.35, 0, -1), g='point')),
    'temple_R': dict(R=dict(w=(-0.125, -0.07, 0.50), f=(0.32, -0.12, 1), p=(1, 0.1, 0), g='point', pole=(-0.1, 0, -0.1))),
    'small_shrug': dict(R=dict(w=(-0.27, -0.24, 0.20), f=(-0.35, -0.8, 0.3), p=(0, 0, 1), g='open'),
                        L=dict(w=(0.27, -0.24, 0.20), f=(0.35, -0.8, 0.3), p=(0, 0, 1), g='open')),
    'hand_chest_R': dict(R=dict(w=(-0.07, -0.17, 0.25), f=(0.65, -0.05, 0.75), p=(0, 1, 0), g='open', pole=(0.1, 0, 0))),
    'tip_hat_R': dict(R=dict(w=(-0.08, -0.19, 0.64), f=(0.25, -0.35, 0.9), p=(0.2, 0.9, 0.2), g='relax', pole=(0, 0, 0.1))),
    'clasp': dict(R=dict(w=(-0.08, -0.16, 0.10), f=(0.55, -0.2, -0.8), p=(0.2, 0.8, 0), g='relax'),
                    L=dict(w=(0.08, -0.16, 0.10), f=(-0.55, -0.2, -0.8), p=(-0.2, 0.8, 0), g='relax')),
    'think': dict(R=dict(w=(-0.06, -0.22, 0.52), f=(0.2, -0.2, 1), p=(0.3, 0.9, 0), g='fist'),
                  L=dict(w=(0.05, -0.20, 0.22), f=(-0.9, -0.1, 0.2), p=(0, 0.3, 1), g='relax')),
    'phone_R': dict(R=dict(w=(-0.10, -0.33, 0.30), f=(0.25, -0.2, 0.95), p=(0.15, -0.95, 0.1), g='relax')),
}
