# Meshes

FielDes models with fields, and moves between fields and triangle meshes in both directions.

- [Importing meshes](#importing-meshes)
- [Exporting and importing meshes](#exporting-and-importing-meshes)
- [Fields on a grid](#fields-on-a-grid)
- [Getting a mesh in a script](#getting-a-mesh-in-a-script)
- [Round trip](#round-trip)

## Importing meshes

**File → Import model…** (`Ctrl+I`) or drop a file on the window. FielDes writes

```python
# Imported model: bracket.stl
bracket = import_model(r"C:\models\bracket.stl", file_units="mm")
bracket_0 = bracket[0][0]
bracket_0
view.set_bounds(*roi(bracket), auto_scale=True)
view.set_resolution(roi_resolution(bracket))
view.set_quality(8)
```

`import_model(path, units='mm', file_units=None, rev=None)` is the importer: it reads **STL** (binary or ASCII), **OBJ**, **PLY**
(ASCII or binary), **3MF**, **glTF** (`.glb`, `.gltf`), **FBX** (binary or ASCII), **OFF** and **DXF** (`3DFACE` entities
and polyface meshes). The mesh becomes an **exact signed distance
field** (negative inside), so it works with everything else: CSG with other shapes, `offset`, `shell`,
blends, transforms.

Before that the triangles are cleaned: duplicate vertices welded, degenerate triangles dropped, windings made
consistent, inside-out shells flipped. A mesh **with holes** still imports: near a hole, inside and outside
come from the generalised winding number, which closes it with a smooth membrane. The winding number also
decides wherever the nearest feature of the mesh has no clear side -- a sliver folded back over its neighbour or a
knife edge, as a dual-contouring mesher leaves along sharp edges -- so a mesh exported from a part reads back with
the part's inside and outside.

**Units.** STL, OBJ, PLY and OFF carry none: they are read as millimetres unless you say
`file_units='m'` (or `'in'`, `'cm'`). 3MF, FBX (its unit scale) and DXF (`$INSUNITS`, when the file has it) state their unit, and glTF is always in
metres; that is used unless `file_units=` overrides it. glTF's and FBX's Y-up axes become Z-up (an FBX that says Z up is left as it is). `units=` is the
unit of the script (`'mm'`).

**Model tree flags.** An **amber** row means the mesh is open or looks suspiciously small for its units: hover
it for the details. `mesh_info(path)` returns the summary of the last import (triangle count, whether it
is watertight, …) as a dict.

The result is [cached](caching-and-performance.md) by the file's path, size and modification time; `rev=`
makes the script re-read a file that changed on disk.

## Exporting and importing meshes

- **File → Export mesh…** (`F7`, `Ctrl+Alt+E`) writes the shapes shown in the viewport as one mesh, in the format of the file's extension.
- **Right-click a model → Export → Mesh** writes that one model (the file is asked for, and written in the background).
- From a script:

```python
export_mesh(part, "part.stl")                              # the extent of the part, the scene's resolution
export_mesh(part, "part.glb", bounds=(lo, hi), resolution=4)
export_mesh([a, b], "assembly.fbx")                        # several bodies, one file
export_mesh(part, "hero.obj", units="m", up="y")           # metres, Y up (see below)
export_mesh(part, "hero.glb", max_triangles=3000)          # the finest mesh within a budget of triangles
export_mesh(part, "hero.glb", symmetric="x")               # exactly symmetric across x = 0
```

`bounds` is the region meshed (`((x0, y0, z0), (x1, y1, z1))`; a body that knows its extent needs none), `resolution` is samples per mm (larger is
finer and slower; the scene's resolution when not given). The older `part.save_stl(path, lo, hi, resolution, quality)` still works.

| Format | Extension | Written as | Read |
|---|---|---|---|
| STL | `.stl` | binary (`ascii=True` for text), millimetres and Z up unless `units=` / `up=` say otherwise | yes |
| Wavefront OBJ | `.obj` | text, millimetres and Z up unless `units=` / `up=` say otherwise | yes |
| Stanford PLY | `.ply` | binary little endian, millimetres and Z up unless `units=` / `up=` say otherwise | yes |
| 3D Manufacturing Format | `.3mf` | states its unit: millimetre | yes |
| glTF 2.0 | `.glb`, `.gltf` | metres, Y up (the numbers are turned into them) | yes |
| **Autodesk FBX** | `.fbx` | ASCII 7.4, Z up, unit scale 0.1 cm (= 1 mm) | yes (binary and ASCII) |
| OFF | `.off` | text, millimetres and Z up unless `units=` / `up=` say otherwise | yes |
| DXF | `.dxf` | `3DFACE` entities, `$INSUNITS` 4 (millimetres) | yes (`3DFACE`, polyface meshes) |

### Units, axes, a budget of triangles, symmetry

Four options of `export_mesh` are for what a game engine asks of a mesh. (`examples/32_game_export.py` uses each, reads the files back and prints a
line that starts with `ok` or `FAIL` for everything it checks.)

- **`units="mm" | "cm" | "m" | "in"`** is the unit of the numbers in the file, for the formats that have none (STL, OBJ, PLY, OFF; the OBJ and the PLY
  say it in a comment). The model itself is in millimetres. 3MF, FBX, DXF and glTF state their own unit and axes, so `units=` and `up=` for them are an
  error (the value the format has anyway is accepted).
- **`up="z" | "y"`**: the axis that is up in the file. `"y"` turns the model about the X axis, `(x, y, z)` becomes `(x, z, -y)`: it is turned, not mirrored,
  so the triangles keep their sides and the volume is the same.
- **`max_triangles=N`** is a ceiling: the mesh is made at the resolution asked for, and while it has more than N triangles the resolution is lowered
  (the triangles of a surface grow with its square) until the finest mesh that fits is found. It is not a decimation -- the mesh stays an even one of
  its own resolution -- and a mesh that is within the budget is left as it is.
- **`symmetric="x" | "y" | "z"`** (or `("x", 12.5)` for a plane at that position; `"-x"` keeps the other side): the half on the larger-coordinate side is
  the model. It is meshed with a margin across the plane, cut exactly at it, and its mirror image is added: the triangles are cut with one shared
  vertex for each edge that crosses, the vertices on the plane belong to both halves, and the mirrored half is turned over. The result is symmetric to
  the last bit, closed wherever the mesh was closed, and the two halves are joined with no seam. The vertices within a quarter of a cell of the plane
  are put on it. Model the half you want and the mirror does the rest; the body does not have to be symmetric itself.

### Materials and vertex colours

```python
skin = material("skin", color=(0.93, 0.74, 0.62), roughness=0.7)                 # the base: everywhere
metal = material("metal", color="#9aa0aa", metallic=1.0, roughness=0.3, where=box((-45, -30, 100), (45, 30, 150)))
export_mesh(hero, "hero.glb", materials=[skin, metal], colors=(0.8, 0.8, 1 - z_field() / 200))
```

- **`material(name, color, roughness, metallic, emissive, where)`** says what a surface is made of and where. `color` is `(r, g, b)` from 0 to 1 or `"#rrggbb"`;
  `where` is a body (the material is on what is inside it) or any field (where it is negative: `100 - z_field()` is negative above z = 100), or nothing
  for everywhere.
- **The materials of an export are layers**, painted in the order they are listed: each triangle takes the last material whose `where` is negative at the
  middle of the triangle, so the base material, with no `where`, goes first. A triangle that no material covers has none. The edge between two materials
  follows the triangles of the mesh, as fine as the resolution of the export.
- **`materials=[...]`** is written in **OBJ** (`usemtl` for each group of triangles, and a `.mtl` file beside the OBJ with the colour, the shininess and the
  physically based `Pr` roughness and `Pm` metalness that Blender and the engines read) and **glTF** (`.glb`, `.gltf`: a material with its
  `pbrMetallicRoughness` for each, and one primitive of the mesh for each). The other formats have no materials: asking for them is an error.
- **`colors=(r, g, b)`**, each a number or a field from 0 to 1, is evaluated at every vertex: vertex colours in **OBJ** (`v x y z r g b`), **PLY**
  (`red`, `green`, `blue`) and **glTF** (`COLOR_0`).

[`examples/34_materials.py`](../examples/34_materials.py) writes all of it for a figure, reads the files back and checks that each material is where it says.

### Texture coordinates (UVs)

```python
skin = material("skin", color=(0.93, 0.74, 0.62), texture="skin.png")           # the image is a file name: it is not copied
export_mesh(hero, "hero.glb", uvs="box", materials=[skin])                       # the texture fits each side of the model once
export_mesh(wall, "wall.obj", uvs=("box", 500))                                  # one repeat of the texture for every 500 mm of the model
```

- **`uvs="box"`** is the box projection: each triangle is projected along the axis its normal is mostly along (+x, -x, +y, -y, +z, -z), seen from outside, so a
  texture reads the same way on every side and is not mirrored on the back ones. A vertex that is in triangles of different projections is made again for each
  of them -- that is the seam of the texture -- and the vertices that are not on a seam are shared. A triangle that faces right is never turned over in the
  texture.
- **The size of the texture.** `uvs="box"` puts the texture once over each side: u and v start at 0 on each side and the largest side of the model is 1.
  `uvs=("box", 500)` is *world-scaled*: one repeat of the texture for every 500 mm of the model, with one origin, so the texture goes on from one surface to
  the next (walls, floors and rocks of a game world that share a texture).
- **Where it is written.** OBJ (`vt`, and the faces say `v/vt`), PLY (`s` and `t`), glTF (`TEXCOORD_0`; v is down from the top of the image there, as glTF has
  it). The other formats have no texture coordinates: asking for them is an error.
- **`material(..., texture="skin.png")`** names the image that is the colour of the material: `map_Kd` in the `.mtl`, the `baseColorTexture` of the material
  in glTF (with the file name as the URI of an image). The image itself is yours to put beside the mesh.

[`examples/35_uvs.py`](../examples/35_uvs.py) checks it by reading the files back: the areas in the texture against the areas in space, the seams, the tiling.

**FBX is a proprietary format** of Autodesk, whose SDK is available under its own licence and whose files have no published specification. FielDes
reads and writes FBX **without the Autodesk SDK**, from the structure of the files as the community documents it (the node tree, the property types,
the objects and their connections), and handles **meshes only**: geometry, the transform of the models that hold it, the scene's unit and up axis -- no
materials, animation, skins or cameras. Because the format is not specified, another program may read less of what FielDes writes than FielDes reads of
its own files: STL, OBJ, PLY, 3MF and glTF are the safer ways to hand a model on. DXF is the same: only meshes made of faces.

When no `bounds` is given a body is meshed in its own extent plus one cell all round (a face that lies exactly on the edge of the region meshed is not found by it).

## Fields on a grid

```python
export_field(swell, "swell.vti", bounds=((0, 0, 0), (60, 20, 10)), resolution=1)   # VTK image data
export_field(swell, "swell.csv", bounds=(lo, hi))                                                 # x, y, z, value
```

A field is not a mesh: this samples it on a regular grid (at most two million points) for programs that read grids, at the resolution you ask for.

## Getting a mesh in a script

`verts, tris = shape.get_mesh(lo, hi, resolution)` returns the vertices (`(x, y, z)`) and triangles (index
triples) of a shape as lists, for scripts that post-process the geometry (`algorithm='simplex'` or `'hybrid'`
are slower but more robust on awkward fields).

## Round trip

`examples/12_mesh_export_and_import.py` writes a cup as an STL file and reads it back with
`import_model`.
