import bpy, sys, math, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ep_paths
import numpy as np
from mathutils import Vector, Matrix, Euler, Quaternion
import blib, anim, drv, far, env
from anim import ease, lerp, wob, keyed, obj_matrix, key_object

SUN_COL = (1.0, 0.78, 0.55)


def base_scene(sun_elev=15.0, sun_rot=70.0, sun_strength=3.8, sky_strength=0.22, clouds=True):
    sc = blib.reset()
    F = far.build_far(sun_elev=sun_elev, sun_rot=sun_rot, sun_strength=sun_strength, sky_strength=sky_strength,
                      clouds=clouds, sun_color=SUN_COL)
    sc.frame_start = 1
    return sc, F


def look(cam, frame, loc, target, roll=0.0):
    d = Vector(target) - Vector(loc)
    q = d.to_track_quat('-Z', 'Y')
    if roll:
        q = q @ Quaternion((0, 0, 1), math.radians(roll))
    cam.rotation_mode = 'QUATERNION'
    cam.location = loc
    cam.rotation_quaternion = q
    cam.keyframe_insert('location', frame=frame)
    cam.keyframe_insert('rotation_quaternion', frame=frame)


def plate_camera(name, loc, target, lens, roll=0.0):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens; cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36.0; cd.clip_end = 80000; cd.clip_start = 0.5
    ob = bpy.data.objects.new(name, cd)
    blib.link(ob)
    d = Vector(target) - Vector(loc)
    q = d.to_track_quat('-Z', 'Y')
    if roll:
        q = q @ Quaternion((0, 0, 1), math.radians(roll))
    ob.rotation_mode = 'QUATERNION'
    ob.location = loc; ob.rotation_quaternion = q
    return ob


def creature_objects(prefix):
    return [o for o in bpy.data.objects if o.name.startswith(prefix)]


def flight_key(g, f, t, pos, yaw, pitch=0.0, roll=0.0, scale=1.0, **kw):
    rots, fold, bob = anim.flight_rots(t, **kw)
    M = obj_matrix(pos, yaw=yaw, pitch=pitch, roll=roll, scale=scale)
    key_object(g.arm, f, M)
    anim.pose_creature(g.rig, f, M, rots, root_off=Vector((0, 0, bob)))
    g.key_feathers(f, fold)
    return M
