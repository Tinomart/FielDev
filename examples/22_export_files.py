# Exporting: a part as a mesh in every format.
#
# What to look at:
#   * the files, in the folder printed at the end (your temporary folder): the part as STL, OBJ, PLY, 3MF, glTF, FBX, OFF and DXF
#     (delete the folder to write them again);
#   * the model tree: **right-click a model, Export** writes one file at a time, with a dialog for where it goes;
#   * the script is divided into sections (`# SECTION ...`): rows of the model tree with an arrow to close them, and a fold in the code editor.
#     `beam` is made in the first section and used in the second: it stays where it is made.
#
# FBX is Autodesk's format, read and written here without Autodesk's SDK and for meshes only (docs/meshes.md says what that means).
import os
import tempfile
from fieldes import *

view.set_bounds((-5, -10, -10), (65, 30, 20), auto_scale=True)
view.set_resolution(2)
view.set_quality(8)

# SECTION The part
beam = difference(box((0, 0, 0), (60, 20, 10)), cylinder(3, 20, (30, 10, -5)))
beam

# SECTION The files
out = os.path.join(tempfile.gettempdir(), "fieldes-exports")
region = ((-1, -1, -1), (61, 21, 11))
for ext in (".stl", ".obj", ".ply", ".3mf", ".glb", ".fbx", ".off", ".dxf"):
    if not os.path.exists(os.path.join(out, "beam" + ext)):
        export_mesh(beam, os.path.join(out, "beam" + ext), bounds=region, resolution=2)
print("files written to", out)
print(sorted(f for f in os.listdir(out) if f.startswith("beam.")))
