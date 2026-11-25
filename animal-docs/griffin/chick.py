import os
import bpy, math, json, sys
import numpy as np
from mathutils import Vector, Matrix, Quaternion, Euler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blib
from blib import Rig, creature_rot
from sdf import Prim, build_mesh, taubin

CREAM = (0.74, 0.66, 0.52)
TAWNY = (0.44, 0.24, 0.08)
DARK = (0.05, 0.03, 0.018)
SPOT = (0.22, 0.11, 0.04)


def toe_meshes(name, base_c, yaw_list, scale=1.0, mat_toe=None, mat_claw=None, coll=None, z_up=0.0):
    """returns list of (toe_ob, claw_ob, pivot, axis)"""
    out = []
    for k, (yaw, length, r0) in enumerate(yaw_list):
        d = Vector((math.sin(math.radians(yaw)), -math.cos(math.radians(yaw)), 0.0))
        b0 = Vector(base_c) + d * 0.010 * scale
        b1 = b0 + d * length * 0.55 * scale + Vector((0, 0, 0.002 * scale))
        b2 = b1 + d * length * 0.45 * scale + Vector((0, 0, -0.003 * scale))
        r1 = r0 * 0.9; r2 = r0 * 0.72
        prims = [Prim('cone', 't', k=0.004 * scale, a=tuple(b0), b=tuple(b1), r1=r0 * scale, r2=r1 * scale),
                 Prim('cone', 't', k=0.004 * scale, a=tuple(b1), b=tuple(b2), r1=r1 * scale, r2=r2 * scale),
                 Prim('sph', 't', k=0.003 * scale, c=tuple(b1 + Vector((0, 0, -0.002 * scale))), r=r1 * 1.08 * scale)]
        v, f = build_mesh(prims, h=0.0011 * scale, margin=0.004 * scale)
        v = taubin(v, f, iters=6)
        tob = blib.mesh_obj(f'{name}_toe{k}', v, f, coll=coll)
        if mat_toe:
            blib.assign(tob, mat_toe)
        # claw: curved cone
        cl = claw_mesh(f'{name}_claw{k}', b2 + d * r2 * 0.4 * scale, d, length=r0 * 1.9 * scale, rad=r2 * 0.78 * scale, coll=coll)
        if mat_claw:
            blib.assign(cl, mat_claw)
        axis = d.cross(Vector((0, 0, 1))).normalized()
        out.append((tob, cl, b0.copy(), axis))
    return out


def claw_mesh(name, base, d, length, rad, segs=12, ring=12, curve=0.9, coll=None):
    d = Vector(d).normalized()
    up = Vector((0, 0, 1))
    s = d.cross(up).normalized()
    u = s.cross(d).normalized()
    verts, uvs = [], []
    for i in range(segs + 1):
        t = i / segs
        ang = curve * t * 1.4
        c = Vector(base) + (d * math.sin(ang) + (-u) * (1 - math.cos(ang))) * (length / max(curve * 1.4, 1e-3))
        tang = (d * math.cos(ang) + (-u) * math.sin(ang)).normalized()
        nrm = tang.cross(s).normalized()
        r = rad * (1 - t) ** 0.9 + rad * 0.02
        for j in range(ring):
            a = 2 * math.pi * j / ring
            verts.append(c + (s * math.cos(a) * 0.8 + nrm * math.sin(a)) * r)
            uvs.append((t, j / ring))
    faces = []
    for i in range(segs):
        for j in range(ring):
            a = i * ring + j; b = i * ring + (j + 1) % ring
            faces.append((a, b, b + ring, a + ring))
    cap = len(verts); verts.append(Vector(base) - d * rad * 0.3); uvs.append((0, 0))
    for j in range(ring):
        faces.append(((j + 1) % ring, j, cap))
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    uvl = me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        for li, vi in zip(poly.loop_indices, poly.vertices):
            uvl.data[li].uv = uvs[vi]
    ob = bpy.data.objects.new(name, me)
    blib.link(ob, coll)
    return ob


class Chick:
    def __init__(self, name='chick', hair=True, hair_parents=4200, hair_children=6, coll=None, scale=1.0):
        blib.ensure_assets('chick')
        D = np.load(blib.ASSETS + 'chick_mesh.npz')
        R = json.load(open(blib.ASSETS + 'chick_rig.json'))
        acc = R['acc']
        bones = [list(b) for b in R['bones']]
        bb = Vector(acc['beak']['base']); bd = Vector(acc['beak']['dir'])
        for b in bones:
            if b[0] == 'jaw':
                b[1] = tuple(bb - bd * 0.010 + Vector((0, 0, -0.004)))
                b[2] = tuple(bb + bd * 0.03 + Vector((0, 0, -0.008)))
        self.name = name
        self.arm = blib.build_armature(name + '_rig', bones, coll)
        names = [b[0] for b in R['bones']]
        v = D['v']; f = D['f']
        self.body = blib.mesh_obj(name + '_body', v, f, coll=coll)
        me = self.body.data
        blib.set_uv(me, 'attr', np.stack([D['tawny'], D['dark']], 1))
        blib.set_uv(me, 'attr2', np.stack([D['spot'], D['var']], 1))
        me.uv_layers.active_index = 0
        blib.bind(self.body, self.arm, D['W'], names)
        self.m_skin = blib.mat_down_skin(name + '_skin', CREAM, TAWNY, DARK, SPOT)
        self.m_hair = blib.mat_down_hair(name + '_hair', CREAM, TAWNY, DARK, SPOT)
        me.materials.append(self.m_skin)
        me.materials.append(self.m_hair)
        if hair:
            blib.add_weight_group(self.body, 'hdens', D['hdens'])
            blib.add_weight_group(self.body, 'hlen', D['hlen'])
            mod = self.body.modifiers.new('down', 'PARTICLE_SYSTEM')
            ps = mod.particle_system
            st = ps.settings
            st.type = 'HAIR'
            st.count = hair_parents
            st.hair_length = 0.034
            st.hair_step = 5
            st.render_step = 3
            st.display_step = 2
            st.use_advanced_hair = False
            st.emit_from = 'FACE'
            st.use_even_distribution = True
            st.material = 2
            st.child_type = 'INTERPOLATED'
            st.rendered_child_count = hair_children
            st.child_percent = 1
            st.child_length = 1.0
            st.clump_factor = -0.35
            st.roughness_1 = 0.004
            st.roughness_1_size = 1.0
            st.roughness_2 = 0.010
            st.roughness_2_size = 1.0
            st.roughness_endpoint = 0.007
            st.kink = 'CURL'
            st.kink_amplitude = 0.0025
            st.kink_frequency = 2.2
            st.root_radius = 1.0
            st.tip_radius = 0.08
            st.radius_scale = 0.0013
            ps.vertex_group_density = 'hdens'
            ps.vertex_group_length = 'hlen'
            st.length_random = 0.25
            mod.show_viewport = True
        bpy.context.view_layer.update()
        self.rig = Rig(self.arm)
        # eyes
        self.m_eye = blib.mat_eye(name + '_eye', (0.07, 0.04, 0.022), (0.035, 0.02, 0.012), p=0.14, i=0.36, ring=(0.012, 0.008, 0.006))
        self.lids = {}
        self.eyes = {}
        self.m_lid = blib.mat_simple(name + '_lid', (0.62, 0.55, 0.43), rough=0.85, spec=0.3)
        for side in ('L', 'R'):
            e = acc['eye_' + side]
            eo = blib.sphere_mesh(f'{name}_eye_{side}', e['center'], e['radius'], e['dir'])
            blib.assign(eo, self.m_eye)
            blib.parent_to_bone(eo, self.arm, 'head')
            self.eyes[side] = eo
            for up in (True, False):
                lo, frame = blib.lid_mesh(f'{name}_lid_{side}_{"u" if up else "l"}', (0, 0, 0), e['radius'] * 1.07, (0, 0, 1), upper=up)
                x, y, z = blib.frame_from_dir(e['dir'])
                M = Matrix((x, y, z)).transposed().to_4x4()
                M.translation = Vector(e['center'])
                lo.matrix_world = M
                lo.data.materials.append(self.m_lid)
                blib.parent_to_bone(lo, self.arm, 'head')
                lo.rotation_mode = 'QUATERNION'
                self.lids[(side, up)] = (lo, lo.matrix_basis.copy())
        # beak
        self.m_beak = blib.mat_beak(name + '_beak', (0.75, 0.50, 0.10), (0.05, 0.045, 0.045), (0.01, 0.01, 0.012), rough=0.32)
        self.beak = blib.beak_mesh(name + '_beak_u', bb, bd, L=0.050, W=0.0175, H=0.025, hook=0.7)
        blib.assign(self.beak, self.m_beak)
        blib.parent_to_bone(self.beak, self.arm, 'head')
        self.jaw = blib.beak_mesh(name + '_beak_l', bb + Vector((0, 0, -0.001)), bd, L=0.048, W=0.0162, H=0.024, lower=True)
        blib.assign(self.jaw, self.m_beak)
        blib.parent_to_bone(self.jaw, self.arm, 'jaw')
        # front toes
        self.m_toe = blib.mat_toes(name + '_toes', (0.70, 0.48, 0.12))
        self.m_claw = blib.mat_claw(name + '_claw')
        self.toes = {}
        for side, sx in (('L', 1), ('R', -1)):
            c = acc['foot_' + side]['center']
            yl = [(sx * -26, 0.040, 0.0092), (0, 0.044, 0.0098), (sx * 24, 0.038, 0.0090), (sx * -160, 0.026, 0.0090)]
            parts = toe_meshes(f'{name}_{side}', c, yl, mat_toe=self.m_toe, mat_claw=self.m_claw)
            lst = []
            for tob, cl, pivot, axis in parts:
                blib.parent_to_bone(tob, self.arm, 'f_foot_' + side)
                blib.parent_to_bone(cl, self.arm, 'f_foot_' + side)
                lst.append((tob, cl, pivot, axis, tob.matrix_basis.copy(), cl.matrix_basis.copy()))
            self.toes[side] = lst
        # tiny wing feathers poking through the down
        import feathers as FE
        self.m_pin = FE.mat_feather(name + '_pin', (0.60, 0.52, 0.42), (0.045, 0.035, 0.028), trans=0.0, stripe=0.05)
        self.pins = []
        for side, sx in (('L', 1), ('R', -1)):
            b = self.arm.data.bones['wing_' + side]
            h, t = Vector(b.head_local), Vector(b.tail_local)
            for i in range(6):
                u = 0.35 + i * 0.12
                p = h + (t - h) * u + Vector((sx * 0.012, 0, -0.004))
                d = Vector((sx * 0.25, 1.0, -0.55 - 0.05 * i)).normalized()
                n = Vector((sx * 1.0, -0.1, 0.35)).normalized()
                geom = FE.feather_geom(0.040 + 0.006 * (i % 3), 0.013, curve=0.1, bend=0.05, asym=0.1, nx=6, ny=2)
                ob = FE.make_feather_object(f'{name}_pin_{side}{i}', geom, self.m_pin, FE.frame_matrix(p, d, n), coll)
                blib.parent_to_bone(ob, self.arm, 'wing_' + side)
                self.pins.append(ob)
        self.all_objects = [self.arm, self.body, self.beak, self.jaw] + list(self.eyes.values()) + [v[0] for v in self.lids.values()] + \
            [p[0] for s in self.toes.values() for p in s] + [p[1] for s in self.toes.values() for p in s] + self.pins
        if scale != 1.0:
            self.arm.scale = (scale, scale, scale)

    def key_lids(self, frame, closed):
        for (side, up), (lo, B0) in self.lids.items():
            ang = (1.0 - closed) * (math.radians(78) if up else math.radians(-62))
            lo.matrix_basis = B0 @ Matrix.Rotation(-ang, 4, 'X')
            lo.keyframe_insert('location', frame=frame)
            lo.keyframe_insert('rotation_quaternion', frame=frame)

    def key_toes(self, frame, curl):
        """curl in radians (positive = grip), per side dict or float"""
        for side, lst in self.toes.items():
            c = curl[side] if isinstance(curl, dict) else curl
            for k, (tob, cl, pivot, axis, B0, C0) in enumerate(lst):
                a = -c * (0.7 if k == 3 else 1.0)
                for ob, B in ((tob, B0), (cl, C0)):
                    ob.matrix_basis = _rot_about(B, pivot, axis, a, self, side)
                    ob.keyframe_insert('location', frame=frame)
                    ob.keyframe_insert('rotation_euler', frame=frame)


def _rot_about(B, pivot, axis, ang, chick, side):
    # object basis is expressed in bone-tail space; convert rotation defined in armature rest space
    bone = chick.arm.data.bones['f_foot_' + side]
    BT = bone.matrix_local.copy()
    BT.translation = bone.tail_local
    Rm = Matrix.Translation(pivot) @ Matrix.Rotation(ang, 4, Vector(axis)) @ Matrix.Translation(-pivot)
    return BT.inverted() @ Rm @ BT @ B
