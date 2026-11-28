"""Build every mesh (the hooded man and the sets) into build/assets.npz. Needs bpy (Blender 5.3 as a Python module)."""
import paths  # noqa: F401  (sibling props on sys.path)
import os
import bpy
import meshkit
import build_man, build_sets, textures

HERE = os.path.dirname(os.path.abspath(__file__))
if __name__ == '__main__':
    bpy.ops.wm.read_factory_settings(use_empty=True)
    textures.build_all(os.path.join(HERE, 'build', 'tex'))
    build_man.build()
    build_sets.build()
    n = meshkit.save(os.path.join(HERE, 'build', 'assets.npz'))
    print(len(n), 'parts,', sum(n.values()), 'triangles')
