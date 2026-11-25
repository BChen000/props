"""Builds and runs the two C path tracers.

boxtrace.c   scenes made of boxes (axis-aligned or rotated about z) + the floor plane
meshtrace.c  triangle meshes with a BVH, clear glass walls, and an `env` mode that lights marble positions

Both write a 2x-supersampled G-buffer the compositor paints marbles on:
  <prefix>_D.f32 key light, _A.f32 sky/bounce light, _O.f32 reflections+fog, _Z.f32 depth, _N.f32 normals,
  _I.u8 object ids, _preview.ppm; meshtrace also writes the front glass layer _GA/_GC/_GZ.f32.
"""
import hashlib
import os
import subprocess

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CFLAGS = ["-O3", "-march=native", "-fopenmp"]


def build(name, outdir):
    """Compiles HERE/<name>.c into outdir/<name> unless an up-to-date binary is there."""
    src = os.path.join(HERE, name + ".c")
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, name)
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(src):
        subprocess.run(["gcc", *CFLAGS, "-o", out, src, "-lm"], check=True)
    return out


def file_hash(*paths):
    h = hashlib.sha256()
    for p in paths:
        with open(p, "rb") as f:
            h.update(f.read())
    return h.hexdigest()[:16]


def render_static(binary, scene_txt, prefix, log=None, deps=()):
    """Renders the G-buffer once per scene (scene file + deps such as a mesh file); skips if already rendered.
    The tracer runs in the scene file's folder, so a mesh path in the scene file can be relative to it."""
    stamp = prefix + "_scene.sha"
    want = file_hash(scene_txt, *deps)
    if os.path.exists(stamp) and open(stamp).read().strip() == want and os.path.exists(prefix + "_I.u8"):
        return False
    with open(log or os.devnull, "w") as lf:
        subprocess.run([os.path.abspath(binary), os.path.abspath(scene_txt), os.path.abspath(prefix)], check=True,
                       stdout=lf, stderr=subprocess.STDOUT, cwd=os.path.dirname(os.path.abspath(scene_txt)))
    with open(stamp, "w") as f:
        f.write(want)
    return True


def env_query(binary, scene_txt, points, workdir):
    """meshtrace env mode: per point -> [light visibility, 6x3 ambient cube, gap below, shadow reach] (21 floats)."""
    os.makedirs(workdir, exist_ok=True)
    pin = os.path.join(workdir, "env_pts.f32")
    pout = os.path.join(workdir, "env_out.f32")
    np.asarray(points, np.float32).tofile(pin)
    subprocess.run([os.path.abspath(binary), os.path.abspath(scene_txt), "env", os.path.abspath(pin),
                    os.path.abspath(pout)], check=True, cwd=os.path.dirname(os.path.abspath(scene_txt)))
    return np.fromfile(pout, np.float32).reshape(len(points), 21)
