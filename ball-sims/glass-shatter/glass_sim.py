import os, sys, time, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pybullet as p
import settings as C
import fracture as FR

ap = argparse.ArgumentParser()
ap.add_argument('--stage', type=int, required=True)
ap.add_argument('--frames', type=int, default=150)
ap.add_argument('--bx', type=float, default=0.02)
ap.add_argument('--by', type=float, default=-0.015)
ap.add_argument('--drop', type=float, default=-1.0)
ap.add_argument('--v0', type=float, default=0.0)
ap.add_argument('--keep', type=float, default=-1.0)
ap.add_argument('--seed', type=int, default=0)
ap.add_argument('--substeps', type=int, default=8)
ap.add_argument('--iters', type=int, default=30)
ap.add_argument('--out', default='')
a = ap.parse_args()

st = C.STAGES[a.stage]
rng = np.random.default_rng(100 + a.stage * 7 + a.seed)
p.connect(p.DIRECT)
p.setGravity(0, 0, -9.81)
dt = 1.0 / (C.FPS * a.substeps)
p.setPhysicsEngineParameter(fixedTimeStep=dt, numSolverIterations=a.iters, numSubSteps=0,
                            enableConeFriction=1, deterministicOverlappingPairs=1)
plane = p.createMultiBody(0, p.createCollisionShape(p.GEOM_PLANE))
p.changeDynamics(plane, -1, lateralFriction=0.6, restitution=0.1)
panes = []
for k in range(C.N_P):
    cs = p.createCollisionShape(p.GEOM_BOX, halfExtents=[C.HALF, C.HALF, C.T / 2])
    b = p.createMultiBody(0, cs, basePosition=[0, 0, C.pane_z(k)])
    p.changeDynamics(b, -1, lateralFriction=0.5, restitution=0.25)
    panes.append(b)
r = C.ball_r(st['kg'])
m_phys = float(np.clip(st['kg'], 2.0, 60.0))
drop = a.drop if a.drop > 0 else 1.15 + 1.6 * r
keep = a.keep if a.keep > 0 else [0.7, 0.7, 0.78, 0.82, 0.86, 0.9, 0.93][a.stage]
bz0 = C.pane_z(0) + C.T / 2 + drop
ball = p.createMultiBody(m_phys, p.createCollisionShape(p.GEOM_SPHERE, radius=r), basePosition=[a.bx, a.by, bz0])
p.changeDynamics(ball, -1, lateralFriction=0.45, restitution=0.32, rollingFriction=0.002, spinningFriction=0.002,
                 linearDamping=0.0, angularDamping=0.05)
p.resetBaseVelocity(ball, [0, 0, -a.v0])

shard_info = []
shard_bodies = []
intact = [True] * C.N_P
break_frames = [-1] * C.N_P
events = []


def do_break(k, frame):
    bpos, _ = p.getBasePositionAndOrientation(ball)
    bv, _ = p.getBaseVelocity(ball)
    speed = abs(bv[2])
    ic = (float(np.clip(bpos[0], -C.HALF + 0.05, C.HALF - 0.05)), float(np.clip(bpos[1], -C.HALF + 0.05, C.HALF - 0.05)))
    polys = FR.shatter(ic, half=C.HALF, seed=int(1000 * a.stage + 17 * k + a.seed), r0=0.02)
    p.removeBody(panes[k])
    intact[k] = False
    break_frames[k] = frame
    z = C.pane_z(k)
    for poly in polys:
        c, verts, faces, mats = FR.prism(poly, C.T, shrink=0.0007)
        area = abs(FR.poly_area(poly))
        mass = max(area * C.T * C.RHO_GLASS, 0.004)
        cs = p.createCollisionShape(p.GEOM_MESH, vertices=verts.tolist())
        body = p.createMultiBody(mass, cs, basePosition=[c[0], c[1], z])
        p.changeDynamics(body, -1, lateralFriction=0.55, restitution=0.12, collisionMargin=0.0006,
                         linearDamping=0.04, angularDamping=0.08)
        dxy = np.array([c[0] - ic[0], c[1] - ic[1]])
        d = np.linalg.norm(dxy) + 1e-6
        rad = dxy / d
        near = np.exp(-d / 0.16)
        vr = (0.35 + 0.30 * speed) * near * rng.uniform(0.5, 1.3)
        vz = -speed * 0.55 * np.exp(-d / max(0.08, r * 1.4)) + rng.uniform(-0.15, 0.25) * near
        lin = [rad[0] * vr, rad[1] * vr, vz]
        ang = (rng.normal(0, 1, 3) * (2 + 14 * near)).tolist()
        p.resetBaseVelocity(body, lin, ang)
        shard_bodies.append(body)
        shard_info.append(dict(pane=k, c=c.tolist(), verts=verts.tolist(), faces=faces, mats=mats, spawn=frame))
    p.resetBaseVelocity(ball, [bv[0] * 0.9, bv[1] * 0.9, bv[2] * keep], p.getBaseVelocity(ball)[1])
    events.append(dict(type='break', frame=frame, pane=k, speed=speed))


ball_pos, ball_quat, sh_pos, sh_quat = [], [], [], []
intact_log = []
t0 = time.time()
prev_v = np.array([0, 0, -a.v0])
for fr in range(a.frames):
    for sub in range(a.substeps):
        bpos, _ = p.getBasePositionAndOrientation(ball)
        nxt = next((k for k in range(C.N_P) if intact[k]), None)
        if nxt is not None and nxt < st['brk']:
            top = C.pane_z(nxt) + C.T / 2
            bvz = p.getBaseVelocity(ball)[0][2]
            near = bpos[2] - r <= top + 0.004 + (2 * C.T + 0.01 if nxt > 0 else 0.0)
            stalled = nxt > 0 and bvz > -0.35 and bpos[2] - r <= top + 0.12
            if (near or stalled) and abs(bpos[0]) < C.HALF + r and abs(bpos[1]) < C.HALF + r:
                do_break(nxt, fr)
        p.stepSimulation()
    bpos, bq = p.getBasePositionAndOrientation(ball)
    bv, _ = p.getBaseVelocity(ball)
    bv = np.array(bv)
    dv = bv - prev_v
    if np.linalg.norm(dv) > 0.9 and fr > 0:
        events.append(dict(type='ball_hit', frame=fr, dv=float(np.linalg.norm(dv)), z=float(bpos[2])))
    prev_v = bv
    ball_pos.append(bpos)
    ball_quat.append(bq)
    sp = np.zeros((len(shard_bodies), 3), np.float32)
    sq = np.zeros((len(shard_bodies), 4), np.float32)
    for i, b in enumerate(shard_bodies):
        pp, qq = p.getBasePositionAndOrientation(b)
        sp[i] = pp
        sq[i] = qq
    sh_pos.append(sp)
    sh_quat.append(sq)
    intact_log.append(list(intact))
    if fr % 15 == 0 or fr == a.frames - 1:
        print(f"frame {fr} t={time.time() - t0:.1f}s ball z {bpos[2]:.3f} shards {len(shard_bodies)}", flush=True)

N = len(shard_bodies)
P = np.full((a.frames, N, 3), np.nan, np.float32)
Q = np.zeros((a.frames, N, 4), np.float32)
Q[..., 3] = 1
for f in range(a.frames):
    n = len(sh_pos[f])
    P[f, :n] = sh_pos[f]
    Q[f, :n] = sh_quat[f]
os.makedirs(C.SIMS, exist_ok=True)
out = a.out or os.path.join(C.SIMS, f'stage{a.stage}.npz')
np.savez_compressed(out, ball_pos=np.array(ball_pos, np.float32), ball_quat=np.array(ball_quat, np.float32),
                    sh_pos=P, sh_quat=Q, intact=np.array(intact_log, bool), r=r,
                    shards=json.dumps(shard_info), events=json.dumps(events), break_frames=np.array(break_frames))
print('saved', out, 'shards', N, 'time', round(time.time() - t0, 1))
