# Triangle meshes: export a part as STL, read it back in.
#
# import_model() turns an STL / OBJ / PLY / 3MF / glTF file into a field: the exact signed distance to
# its triangles (the mesh is cleaned first, holes are closed smoothly).  So a mesh from anywhere
# is a shape like any other: cut it, blend it, mirror it.  Here a part built from primitives
# is exported with save_stl and read back.
#
import os
from fieldev import *

lo, hi = (-30, -30, -5), (30, 30, 35)
view.set_bounds(lo, hi)
view.set_resolution(2)
view.set_quality(8)

part = difference(cylinder(25, 30, (0, 0, 0)), sphere(18, (0, 0, 30)))

os.makedirs("meshes", exist_ok=True)
path = "meshes/part.stl"
if not os.path.exists(path):
    part.save_stl(path, lo, hi, resolution=2)       # STL carries no units: millimetres

mesh, (mlo, mhi) = import_model(path, file_units="mm")[0]
mesh
print("mesh size (mm):", [round(h - l, 1) for l, h in zip(mlo, mhi)])
