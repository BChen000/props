from sc_common import *
from adult import Griffin


def head_world(g):
    bpy.context.view_layer.update()
    pb = g.arm.pose.bones['head']
    return g.arm.matrix_world @ pb.tail


def run_flight(NAME, N, F, cam, plate_cam, crop=False, spp=3, plate_res=(912, 1620), plate_spp=14, only=None, dynamic=None, step=1):
    far_objs = drv.far_objects(F)
    hide = [o for o in bpy.data.objects if o.type in ('MESH',) and o not in far_objs]
    if 'camonly' in sys.argv:
        import json
        sc = bpy.context.scene
        recs = {}
        for f in range(1, N + 1):
            sc.frame_set(f)
            recs[str(f)] = {'cam': drv.cam_record(cam)}
        json.dump({'res': list(drv.RES), 'frames': recs, 'plate': drv.cam_record(plate_cam), 'plate_res': list(plate_res)},
                  open(drv.shot_dir(NAME) + 'cams_dry.json', 'w'))
        return
    if 'quick' in sys.argv:
        sc = bpy.context.scene
        blib.render_settings(res=(360, 640), spp=4, transparent=False)
        os.makedirs(drv.SHOTS + NAME + '/quick', exist_ok=True)
        for f in [int(x) for x in sys.argv[sys.argv.index('quick') + 1].split(',')]:
            sc.frame_set(f); sc.render.filepath = drv.SHOTS + NAME + '/quick/%04d.png' % f
            bpy.ops.render.render(write_still=True)
        return
    if 'noplate' not in sys.argv:
        drv.render_plate(NAME, F, hide, cam=plate_cam, spp=plate_spp, res=plate_res)
        drv.save_plate_cam(NAME, plate_cam)
        if 'plateonly' in sys.argv:
            return
    drv.set_visible(far_objs, False)
    if 'test' in sys.argv:
        only = [int(x) for x in sys.argv[sys.argv.index('test') + 1].split(',')]
    drv.render_frames(NAME, 1, N, spp=spp, dynamic=dynamic, crop=crop, only=only, margin_px=40, step=step)
