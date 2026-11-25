import os
import bpy, math, json, sys
import numpy as np
from mathutils import Vector, Matrix, Quaternion, Euler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blib, feathers
from blib import Rig, creature_rot
from chick import toe_meshes

PAL = {
    'adult': dict(lion=(0.62, 0.44, 0.23), belly=(0.80, 0.66, 0.45), neck=(0.55, 0.36, 0.15), head=(0.86, 0.82, 0.71),
                  pale=(0.86, 0.80, 0.66), dark=(0.17, 0.11, 0.07), wing_tube=(0.30, 0.21, 0.12),
                  prim=((0.30, 0.22, 0.15), (0.075, 0.058, 0.045)), sec=((0.30, 0.22, 0.15), (0.11, 0.085, 0.065)),
                  tert=((0.38, 0.28, 0.17), (0.20, 0.15, 0.10)), gcov=((0.40, 0.28, 0.15), (0.26, 0.18, 0.10)),
                  mcov=((0.52, 0.36, 0.18), (0.38, 0.26, 0.13)), under=((0.46, 0.36, 0.25), (0.32, 0.24, 0.16)),
                  scap=((0.46, 0.33, 0.17), (0.32, 0.22, 0.12)), edge=(0.62, 0.46, 0.24),
                  iris=((0.78, 0.50, 0.12), (0.50, 0.26, 0.05)), beak=((0.92, 0.74, 0.22), (0.86, 0.62, 0.17), (0.36, 0.27, 0.16))),
    'juvenile': dict(lion=(0.60, 0.43, 0.24), belly=(0.78, 0.66, 0.48), neck=(0.42, 0.29, 0.15), head=(0.50, 0.37, 0.22),
                     pale=(0.72, 0.62, 0.46), dark=(0.11, 0.075, 0.05), wing_tube=(0.26, 0.18, 0.11),
                     prim=((0.80, 0.77, 0.70), (0.08, 0.06, 0.05)), sec=((0.80, 0.77, 0.70), (0.10, 0.08, 0.06)),
                     tert=((0.36, 0.26, 0.16), (0.18, 0.13, 0.09)), gcov=((0.34, 0.24, 0.14), (0.22, 0.15, 0.09)),
                     mcov=((0.40, 0.28, 0.15), (0.28, 0.19, 0.10)), under=((0.70, 0.66, 0.58), (0.40, 0.32, 0.24)),
                     scap=((0.38, 0.27, 0.15), (0.26, 0.18, 0.11)), edge=(0.55, 0.42, 0.25),
                     iris=((0.66, 0.42, 0.12), (0.40, 0.22, 0.06)), beak=((0.88, 0.70, 0.24), (0.55, 0.45, 0.30), (0.12, 0.11, 0.10))),
}


def lin(c):
    return tuple(float(x) ** 2.2 for x in c)


def mat_body(name):
    m, nt = blib.new_mat(name)
    ca = nt.node('ShaderNodeVertexColor', layer_name='col')
    uvm = nt.node('ShaderNodeUVMap', uv_map='mask')
    sep = nt.node('ShaderNodeSeparateXYZ'); nt.link(uvm.outputs[0], sep.inputs[0])
    ra = nt.node('ShaderNodeUVMap', uv_map='rest_xy'); rb = nt.node('ShaderNodeUVMap', uv_map='rest_z')
    sa = nt.node('ShaderNodeSeparateXYZ'); sb = nt.node('ShaderNodeSeparateXYZ')
    nt.link(ra.outputs[0], sa.inputs[0]); nt.link(rb.outputs[0], sb.inputs[0])
    rest = nt.node('ShaderNodeCombineXYZ')
    nt.link(sa.outputs[0], rest.inputs[0]); nt.link(sa.outputs[1], rest.inputs[1]); nt.link(sb.outputs[0], rest.inputs[2])
    # fur streaks: stretched along body (y)
    mpf = nt.node('ShaderNodeMapping'); mpf.inputs['Scale'].default_value = (170.0, 22.0, 170.0)
    nt.link(rest.outputs[0], mpf.inputs['Vector'])
    nf = nt.node('ShaderNodeTexNoise', i_Scale=1.0, i_Detail=6.0, i_Roughness=0.7)
    nt.link(mpf.outputs[0], nf.inputs['Vector'])
    # feathers: small overlapping cells
    mpv = nt.node('ShaderNodeMapping'); mpv.inputs['Scale'].default_value = (1.0, 0.38, 1.0)
    nt.link(rest.outputs[0], mpv.inputs['Vector'])
    vf = nt.node('ShaderNodeTexVoronoi', feature='SMOOTH_F1', i_Scale=72.0)
    nt.link(mpv.outputs[0], vf.inputs['Vector'])
    mps = nt.node('ShaderNodeMapping'); mps.inputs['Scale'].default_value = (420.0, 70.0, 420.0)
    nt.link(rest.outputs[0], mps.inputs['Vector'])
    ns = nt.node('ShaderNodeTexNoise', i_Scale=1.0, i_Detail=4.0, i_Roughness=0.6)
    nt.link(mps.outputs[0], ns.inputs['Vector'])
    ve = nt.node('ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE', i_Scale=72.0)
    nt.link(mpv.outputs[0], ve.inputs['Vector'])
    vs0 = nt.node('ShaderNodeMath', operation='MULTIPLY_ADD')
    vs0.inputs[1].default_value = 0.35
    nt.link(ve.outputs['Distance'], vs0.inputs[0]); nt.link(vf.outputs['Distance'], vs0.inputs[2])
    vsum = nt.node('ShaderNodeMath', operation='MULTIPLY_ADD')
    vsum.inputs[1].default_value = 0.45
    nt.link(ns.outputs[0], vsum.inputs[0]); nt.link(vs0.outputs[0], vsum.inputs[2])
    mixh = nt.node('ShaderNodeMix', data_type='FLOAT')
    nt.link(sep.outputs[0], mixh.inputs['Factor'])
    nt.link(nf.outputs[0], mixh.inputs['A']); nt.link(vsum.outputs[0], mixh.inputs['B'])
    bump = nt.node('ShaderNodeBump', i_Strength=0.8, i_Distance=0.006)
    nt.link(mixh.outputs['Result'], bump.inputs['Height'])
    # colour variation from feathers
    fr0 = nt.node('ShaderNodeMapRange', i_From_Min=0.0, i_From_Max=0.7, i_To_Min=1.10, i_To_Max=0.80)
    nt.link(vf.outputs['Distance'], fr0.inputs['Value'])
    fe = nt.node('ShaderNodeMapRange', i_From_Min=0.0, i_From_Max=0.14, i_To_Min=0.93, i_To_Max=1.0)
    nt.link(ve.outputs['Distance'], fe.inputs['Value'])
    fr1 = nt.node('ShaderNodeMath', operation='MULTIPLY')
    nt.link(fr0.outputs[0], fr1.inputs[0]); nt.link(fe.outputs[0], fr1.inputs[1])
    fst = nt.node('ShaderNodeMapRange', i_From_Min=0.3, i_From_Max=0.7, i_To_Min=0.84, i_To_Max=1.12)
    nt.link(ns.outputs[0], fst.inputs['Value'])
    fr = nt.node('ShaderNodeMath', operation='MULTIPLY')
    nt.link(fr1.outputs[0], fr.inputs[0]); nt.link(fst.outputs[0], fr.inputs[1])
    ffr = nt.node('ShaderNodeMapRange', i_From_Min=0.3, i_From_Max=0.7, i_To_Min=0.80, i_To_Max=1.12)
    nt.link(nf.outputs[0], ffr.inputs['Value'])
    one = nt.node('ShaderNodeMix', data_type='FLOAT')
    nt.link(ffr.outputs[0], one.inputs['A'])
    nt.link(sep.outputs[0], one.inputs['Factor']); nt.link(fr.outputs[0], one.inputs['B'])
    cc = nt.node('ShaderNodeCombineColor')
    for i in range(3):
        nt.link(one.outputs['Result'], cc.inputs[i])
    mul = nt.node('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY')
    mul.inputs['Factor'].default_value = 1.0
    nt.link(ca.outputs['Color'], mul.inputs['A']); nt.link(cc.outputs[0], mul.inputs['B'])
    if 'shaderB' in sys.argv:
        mpv.inputs['Scale'].default_value = (1.0, 0.55, 1.0)
        vf.inputs['Scale'].default_value = 58.0
        vs0.inputs[1].default_value = 0.0
        vsum.inputs[1].default_value = 0.0
        bump.inputs['Strength'].default_value = 0.75; bump.inputs['Distance'].default_value = 0.005
        fr0.inputs['To Min'].default_value = 1.12; fr0.inputs['To Max'].default_value = 0.72
        fe.inputs['To Min'].default_value = 1.0; fe.inputs['To Max'].default_value = 1.0
        fst.inputs['To Min'].default_value = 1.0; fst.inputs['To Max'].default_value = 1.0
    p = blib.principled(nt, rough=0.72, spec=0.35, sheen=0.25, sheen_r=0.45)
    p.inputs['Sheen Tint'].default_value = (0.9, 0.75, 0.55, 1)
    nt.link(mul.outputs['Result'], p.inputs['Base Color'])
    nt.link(bump.outputs[0], p.inputs['Normal'])
    nt.link(p.outputs[0], nt.out.inputs[0])
    return m


def mat_tuft_hair(name, col):
    m, nt = blib.new_mat(name)
    d = nt.node('ShaderNodeBsdfDiffuse'); d.inputs[0].default_value = blib.rgb(col)
    nt.link(d.outputs[0], nt.out.inputs[0])
    return m


class Griffin:
    def __init__(self, name='adult', variant='adult', coll=None, scale=1.0, tuft_hair=True):
        pal = PAL[variant]
        self.pal = pal
        self.name = name
        blib.ensure_assets('adult')
        D = np.load(blib.ASSETS + 'adult_body.npz')
        R = json.load(open(blib.ASSETS + 'adult_rig.json'))
        acc = R['acc']
        bones = [list(b) for b in R['bones']]
        bb = Vector(acc['beak']['base']); bd = Vector(acc['beak']['dir'])
        for b in bones:
            if b[0] == 'jaw':
                b[1] = tuple(bb - bd * 0.03 + Vector((0, 0, -0.01)))
                b[2] = tuple(bb + bd * 0.12 + Vector((0, 0, -0.03)))
        names = [b[0] for b in bones]
        self.arm = blib.build_armature(name + '_rig', bones, coll)
        v, f = D['v'], D['f']
        fe = D['feath']; gold = D['gold']; pale = D['pale']; dark = D['dark']; belly = D['belly']; var = D['var']
        c = lambda k: np.array(lin(pal[k]))[None, :]
        fur = c('lion') * (1 - belly[:, None]) + c('belly') * belly[:, None]
        fea = c('neck') * (1 - gold[:, None]) + c('head') * gold[:, None]
        fea = fea * (1 - 0.5 * pale[:, None]) + c('pale') * 0.5 * pale[:, None]
        col = fur * (1 - fe[:, None]) + fea * fe[:, None]
        col = col * (1 - dark[:, None]) + c('dark') * dark[:, None]
        col = col * var[:, None]
        self.body = blib.mesh_obj(name + '_body', v, f, coll=coll)
        me = self.body.data
        blib.set_color_attr(me, 'col', col)
        blib.set_uv(me, 'mask', np.stack([fe, dark], 1))
        blib.set_uv(me, 'rest_xy', v[:, :2])
        blib.set_uv(me, 'rest_z', np.stack([v[:, 2], np.zeros(len(v))], 1))
        blib.bind(self.body, self.arm, D['W'], names)
        self.m_body = mat_body(name + '_bodymat')
        me.materials.append(self.m_body)
        if tuft_hair:
            self.m_tuft = mat_tuft_hair(name + '_tuft', lin(pal['dark']))
            me.materials.append(self.m_tuft)
            TP = [float(x) for x in os.environ.get('TUFT', '0.5,0.9,-0.3,300,0.0022,0.75,8').split(',')]
            blib.add_weight_group(self.body, 'tuft', np.clip((dark - TP[5]) / (1.0 - TP[5]) * 1.25, 0, 1))
            mod = self.body.modifiers.new('tuft', 'PARTICLE_SYSTEM')
            st = mod.particle_system.settings
            st.type = 'HAIR'; st.count = int(TP[3]); st.hair_length = 0.26; st.hair_step = 6; st.render_step = 3
            st.use_advanced_hair = True
            st.normal_factor = 0.06 * TP[0]
            st.object_align_factor = (0.0, 0.25 * TP[0], -0.05 * TP[0])
            st.material = 2; st.child_type = 'INTERPOLATED'; st.rendered_child_count = int(TP[6]); st.child_percent = 1
            st.clump_factor = TP[1]; st.clump_shape = TP[2]; st.roughness_2 = 0.008; st.roughness_endpoint = 0.012
            st.root_radius = 1.0; st.tip_radius = 0.05; st.radius_scale = TP[4]
            st.use_even_distribution = True
            mod.particle_system.vertex_group_density = 'tuft'
        self.tubes = {}
        for side in ('L', 'R'):
            T = np.load(blib.ASSETS + f'adult_wingtube_{side}.npz')
            tb = blib.mesh_obj(f'{name}_wingtube_{side}', T['v'], T['f'], coll=coll)
            tcol = np.tile(np.array(lin(pal['wing_tube']))[None, :], (len(T['v']), 1))
            blib.set_color_attr(tb.data, 'col', tcol)
            blib.set_uv(tb.data, 'mask', np.stack([np.ones(len(T['v'])), np.zeros(len(T['v']))], 1))
            blib.set_uv(tb.data, 'rest_xy', T['v'][:, :2])
            blib.set_uv(tb.data, 'rest_z', np.stack([T['v'][:, 2], np.zeros(len(T['v']))], 1))
            blib.bind(tb, self.arm, T['W'], names)
            tb.data.materials.append(self.m_body)
            self.tubes[side] = tb
        bpy.context.view_layer.update()
        self.rig = Rig(self.arm)
        # eyes, lids
        ir = pal['iris']
        self.m_eye = blib.mat_eye(name + '_eye', lin(ir[0]), lin(ir[1]), p=0.09, i=0.34, ring=(0.02, 0.01, 0.004))
        self.lids = {}
        self.eyes = {}
        for side in ('L', 'R'):
            e = acc['eye_' + side]
            eo = blib.sphere_mesh(f'{name}_eye_{side}', e['center'], e['radius'], e['dir'])
            blib.assign(eo, self.m_eye)
            blib.parent_to_bone(eo, self.arm, 'head')
            self.eyes[side] = eo
            for up in (True, False):
                lo, frame = blib.lid_mesh(f'{name}_lid_{side}_{"u" if up else "l"}', (0, 0, 0), e['radius'] * 1.08, (0, 0, 1), upper=up)
                x, y, z = blib.frame_from_dir(e['dir'])
                M = Matrix((x, y, z)).transposed().to_4x4(); M.translation = Vector(e['center'])
                lo.matrix_world = M
                lo.data.materials.append(self.m_body)
                lc = np.tile(np.array(lin(pal['head'] if variant == 'adult' else pal['neck']))[None, :], (len(lo.data.vertices), 1)) * 0.8
                blib.set_color_attr(lo.data, 'col', lc)
                blib.parent_to_bone(lo, self.arm, 'head')
                lo.rotation_mode = 'QUATERNION'
                self.lids[(side, up)] = (lo, lo.matrix_basis.copy())
        bk = pal['beak']
        self.m_beak = blib.mat_beak(name + '_beak', lin(bk[0]), lin(bk[1]), lin(bk[2]), rough=0.28)
        self.beak = blib.beak_mesh(name + '_beak_u', bb, bd, L=0.215, W=0.056, H=0.095, hook=0.95)
        blib.assign(self.beak, self.m_beak)
        blib.parent_to_bone(self.beak, self.arm, 'head')
        self.jaw = blib.beak_mesh(name + '_beak_l', bb + Vector((0, 0, -0.004)), bd, L=0.205, W=0.052, H=0.09, lower=True)
        blib.assign(self.jaw, self.m_beak)
        blib.parent_to_bone(self.jaw, self.arm, 'jaw')
        # front talons
        self.m_toe = blib.mat_toes(name + '_toes', lin((0.86, 0.66, 0.22)))
        self.m_claw = blib.mat_claw(name + '_claw')
        self.toes = {}
        for side, sx in (('L', 1), ('R', -1)):
            cc = acc['foot_' + side]['center']
            yl = [(sx * -24, 0.040, 0.0090), (0, 0.046, 0.0096), (sx * 24, 0.040, 0.0090), (sx * -165, 0.030, 0.0094)]
            parts = toe_meshes(f'{name}_{side}', cc, yl, scale=3.6, mat_toe=self.m_toe, mat_claw=self.m_claw, coll=coll)
            lst = []
            for tob, cl, pivot, axis in parts:
                blib.parent_to_bone(tob, self.arm, 'f_foot_' + side)
                blib.parent_to_bone(cl, self.arm, 'f_foot_' + side)
                lst.append((tob, cl, pivot, axis, tob.matrix_basis.copy(), cl.matrix_basis.copy()))
            self.toes[side] = lst
        self.build_wings(variant, coll)
        self.objects = [o for o in bpy.data.objects if o.name.startswith(name + '_')]
        if scale != 1.0:
            self.arm.scale = (scale, scale, scale)

    def build_wings(self, variant, coll):
        pal = self.pal
        mats = {}
        for key, trans in (('prim', 0.14), ('sec', 0.12), ('tert', 0.08), ('gcov', 0.05), ('mcov', 0.0), ('under', 0.05), ('scap', 0.0)):
            edge = lin(pal['edge']) if key in ('gcov', 'mcov', 'scap', 'tert') else None
            mats[key] = feathers.mat_feather(f'{self.name}_f_{key}', lin(pal[key][0]), lin(pal[key][1]), trans=trans, edge_col=edge, rachis_col=lin((0.55, 0.48, 0.40)))
        self.feathers = []
        bones = self.arm.data.bones
        for side, s in (('L', 1), ('R', -1)):
            def seg(bn):
                b = bones[f'{bn}_{side}']
                return Vector(b.head_local), Vector(b.tail_local)
            Z = Vector((0, 0, 1))

            def place(bn, t, theta, length, width, key, up=0.0, back=0.0, emarg=0.0, asym=0.2, curve=0.10, bend=0.05, fold_theta=None, tilt=0.0):
                a, b = seg(bn)
                bd = (b - a).normalized()
                k = (Z.cross(bd) * s).normalized()
                p = a + (b - a) * t + k * back + Z * up
                d = (bd * math.cos(math.radians(theta)) + k * math.sin(math.radians(theta))).normalized()
                n = (Z + d.cross(Z).normalized() * 0.0 + k * tilt).normalized()
                ls = 1.0 if key == 'scap' else (1.5 if key in ('prim', 'sec', 'tert') else 1.38)
                geom = feathers.feather_geom(length * ls, width * 1.3, curve=curve, bend=bend, asym=asym, emarg=emarg, asym_side=-1 if s > 0 else 1)
                M = feathers.frame_matrix(p, d, n)
                ob = feathers.make_feather_object(f'{self.name}_{key}_{side}_{len(self.feathers)}', geom, mats[key], M, coll)
                parent = f'{bn}_{side}'
                blib.parent_to_bone(ob, self.arm, parent)
                axis = bd.cross(k).normalized()
                self.feathers.append(dict(ob=ob, B0=ob.matrix_basis.copy(), pivot=p.copy(), axis=axis, bone=parent,
                                          theta=theta, fold_theta=fold_theta if fold_theta is not None else theta, key=key, side=side))
                return ob
            # primaries on hand (outermost first)
            P_len = [0.60, 0.70, 0.77, 0.80, 0.79, 0.75, 0.71, 0.67, 0.63, 0.59]
            P_ang = [6, 12, 19, 27, 36, 45, 54, 63, 72, 80]
            for i in range(10):
                t = 1.0 - i * 0.092
                place('w_hand', t, P_ang[i], P_len[i] * 1.02, 0.15 if i > 3 else 0.13, 'prim', up=-0.004 * i * 0.2,
                      back=0.01, emarg=0.38 if i < 4 else 0.0, asym=0.45 if i < 4 else 0.25, fold_theta=4 + i * 1.5, bend=0.05)
            # secondaries on forearm
            for i in range(13):
                t = 1.0 - i / 12.0
                place('w_fore', t, 88 + i * 1.6, 0.58 - 0.004 * i, 0.155, 'sec', up=-0.002, back=0.01, asym=0.15,
                      fold_theta=165, bend=0.04)
            # tertials on humerus
            for i in range(5):
                t = 1.0 - i * 0.12
                place('w_hum', t, 104 + i * 6, 0.52 - 0.035 * i, 0.16, 'tert', up=0.004, back=0.01, asym=0.1, fold_theta=12, bend=0.03)
            # greater coverts (secondary + primary coverts)
            for i in range(14):
                t = 1.0 - i / 13.0
                place('w_fore', t, 95 + i * 1.2, 0.30, 0.12, 'gcov', up=0.018, back=0.02, asym=0.1, fold_theta=165, bend=0.03)
            for i in range(8):
                t = 0.95 - i * 0.11
                place('w_hand', t, 20 + i * 7, 0.26, 0.10, 'gcov', up=0.018, back=0.02, asym=0.2, fold_theta=6 + i, bend=0.03)
            # median + lesser coverts
            for bn, n_, ln_, w_, up_ in (('w_fore', 12, 0.17, 0.085, 0.032), ('w_hum', 7, 0.17, 0.085, 0.032), ('w_hand', 5, 0.14, 0.07, 0.03)):
                for i in range(n_):
                    t = 1.0 - i / max(1, n_ - 1) * 0.95
                    ang = 100 if bn != 'w_hand' else 40
                    place(bn, t, ang, ln_, w_, 'mcov', up=up_, back=0.0, asym=0.0, fold_theta=165 if bn == 'w_fore' else 12, bend=0.02, curve=0.15)
            for bn, n_ in (('w_fore', 16), ('w_hum', 9), ('w_hand', 6)):
                for i in range(n_):
                    t = 1.0 - i / max(1, n_ - 1) * 0.97
                    ang = 108 if bn != 'w_hand' else 50
                    place(bn, t, ang, 0.11, 0.06, 'mcov', up=0.045, back=-0.02, asym=0.0, fold_theta=165 if bn == 'w_fore' else 12, bend=0.01, curve=0.2)
            # under-wing coverts
            for bn, n_ in (('w_fore', 12), ('w_hum', 6)):
                for i in range(n_):
                    t = 1.0 - i / max(1, n_ - 1) * 0.95
                    place(bn, t, 100, 0.27, 0.12, 'under', up=-0.03, back=0.0, asym=0.0, fold_theta=165 if bn == 'w_fore' else 12, bend=-0.02, curve=-0.1)
            # scapulars over the wing root
            for i in range(6):
                t = 0.05 + i * 0.09
                place('w_hum', t, 118 - i * 3, 0.44 - 0.02 * i, 0.15, 'scap', up=0.075 - 0.004 * i, back=-0.02, asym=0.0, fold_theta=20, bend=0.02, curve=0.12)

    def key_feathers(self, frame, fold, spread_extra=None):
        """fold: dict side->0..1"""
        for fd in self.feathers:
            fl = fold[fd['side']] if isinstance(fold, dict) else fold
            dth = (fd['fold_theta'] - fd['theta']) * fl
            if spread_extra and fd['key'] == 'prim':
                dth += spread_extra.get(fd['side'], 0.0)
            bone = self.arm.data.bones[fd['bone']]
            BT = bone.matrix_local.copy(); BT.translation = bone.tail_local
            Rm = Matrix.Translation(fd['pivot']) @ Matrix.Rotation(math.radians(dth), 4, fd['axis']) @ Matrix.Translation(-fd['pivot'])
            ob = fd['ob']
            ob.matrix_basis = BT.inverted() @ Rm @ BT @ fd['B0']
            ob.keyframe_insert('location', frame=frame)
            ob.keyframe_insert('rotation_euler', frame=frame)

    def key_lids(self, frame, closed):
        for (side, up), (lo, B0) in self.lids.items():
            ang = (1.0 - closed) * (math.radians(70) if up else math.radians(-60))
            lo.matrix_basis = B0 @ Matrix.Rotation(-ang, 4, 'X')
            lo.keyframe_insert('location', frame=frame)
            lo.keyframe_insert('rotation_quaternion', frame=frame)

    def key_toes(self, frame, curl):
        for side, lst in self.toes.items():
            cval = curl[side] if isinstance(curl, dict) else curl
            bone = self.arm.data.bones['f_foot_' + side]
            BT = bone.matrix_local.copy(); BT.translation = bone.tail_local
            for k, (tob, cl, pivot, axis, B0, C0) in enumerate(lst):
                a = -cval * (0.8 if k == 3 else 1.0)
                Rm = Matrix.Translation(pivot) @ Matrix.Rotation(a, 4, Vector(axis)) @ Matrix.Translation(-pivot)
                for ob, B in ((tob, B0), (cl, C0)):
                    ob.matrix_basis = BT.inverted() @ Rm @ BT @ B
                    ob.keyframe_insert('location', frame=frame)
                    ob.keyframe_insert('rotation_euler', frame=frame)
