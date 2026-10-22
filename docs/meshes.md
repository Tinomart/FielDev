# Meshes

FielDev models with fields, and moves between fields and triangle meshes in both directions.

- [Importing meshes](#importing-meshes)
- [Exporting and importing meshes](#exporting-and-importing-meshes)
- [Fields on a grid](#fields-on-a-grid)
- [Getting a mesh in a script](#getting-a-mesh-in-a-script)
- [Round trip](#round-trip)

## Importing meshes

**File → Import model…** (`Ctrl+I`) or drop a file on the window. FielDev writes

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
- **The whole PBR material.** `material(...)` also takes `opacity` (a number or a field) and `alpha_mode` (`"OPAQUE"`, `"MASK"` for leaves and fences, `"BLEND"`; blend by
  default below an opacity of 1), `double_sided`, `emissive_strength` (a lamp is brighter than 1), `ior` (1.5 is glass), `transmission` (1 for glass that light passes
  through), `clearcoat` and `clearcoat_roughness` (car paint, varnish), `sheen` (the soft glow of cloth), `normal_scale`, and the file names of images of your own for
  the colour, the normal map, the packed occlusion / roughness / metalness map and the glow (`texture`, `normal_texture`, `orm_texture`, `emissive_texture`). In
  glTF they are written as `pbrMetallicRoughness`, `normalTexture`, `occlusionTexture`, `emissiveTexture`, `alphaMode`, `doubleSided` and the extensions
  `KHR_materials_emissive_strength`, `_transmission`, `_ior`, `_clearcoat` and `_sheen`; in the OBJ's `.mtl` as `d`, `Ni`, `Ke`, `map_Kd`, `map_Bump`, `map_Ke`.
- **Presets.** `material_preset("gold")` is a material that looks like the thing: `gold`, `silver`, `copper`, `brass`, `iron`, `steel`, `aluminium`, `chrome`, `plastic`,
  `rubber`, `wood`, `stone`, `concrete`, `brick`, `ceramic`, `skin`, `leather`, `cloth`, `paper`, `bone`, `glass`, `water`, `paint`, `glow` (`material_presets()` lists
  them). The other options replace the preset's: `material_preset("plastic", color="#2060c0", where=body)`.
- **Fields instead of numbers.** The colour (each channel), the roughness, the metalness, the glow and the opacity can be fields -- noise, a gradient, a pattern. Such a
  material needs the textures baked (below): the picture is the field.
- **In the viewport.** `with_materials(hero, [skin, metal])` shows the model in the colours of its materials, with a key of their names at the right, and `export_mesh(hero, "hero.glb")` then writes the
  same materials without being told twice. The viewport shows each material's colour as an engine shows it (the numbers are linear; the screen gets them through the sRGB curve, so a `"#9aa0aa"` is lighter than in a
  paint program, here and in the engine); a place no material covers is a light grey; roughness, metalness, glow, opacity and textures are in the file, not in the viewport, and a colour that is a field is shown grey.

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

**More UV maps.** `uvs=` takes a text, a UV map made by a function, or a list of two (the second set is `TEXCOORD_1`, for a lightmap):

| | |
|---|---|
| `"box"`, `uv_box(size)` | the box projection above |
| `uv_planar("z", size)` | one projection along an axis for the whole surface (`"-z"` from below): a floor, a wall, a relief |
| `uv_cylinder("z", turns, size)` | u is the angle round the axis, v the height; the cap on the axis itself is stretched, as a cylinder map has it |
| `uv_sphere("z")` | longitude and latitude: the map a globe is drawn on |
| `"unwrap"`, `uv_unwrap(angle=60, margin=4, size=1024)` | the surface cut into **islands**, laid flat and packed into the square: a texture atlas |

`uv_unwrap` works in four steps. (1) The **islands** are grown from the largest triangle over the neighbours whose direction is within `angle` degrees of the
island's average; on a rough surface the directions are smoothed first (the rougher, the more) so that the islands follow the shape and not the bumps; the
ragged edges are made smooth, and the small islands that are left between the large are taken into the one they touch most. (2) Each island is laid flat by the
**conformal map** (least squares conformal maps: angles are kept, so a texture is not sheared) when it is a disc of at most 6000 triangles; else by projection
along its average direction. (3) Every island is scaled to the same density -- a texel is the same size everywhere on the model -- and turned to the angle where
its box is smallest. (4) The boxes are packed in the square, `margin` texels of a `size` x `size` texture apart (maximal rectangles, a quarter turn allowed), at the
largest scale where they fit. `uv_unwrap(...).report` says what it made: the islands, how many were laid flat conformally, how much of the square they cover, the
millimetres of a texel and the stretch. `export_mesh(..., uv_layout="layout.png")` writes a picture of the first map -- the islands and the edges of the
triangles -- to look at.

[`examples/38_uv_maps.py`](../examples/38_uv_maps.py) writes each map for a figure and a crate, reads the files back, and checks that the places are inside the square,
that no two islands overlap, that a texel is the same size everywhere, the repeat of the box and the seam of the cylinder.

### Baked textures

```python
export_mesh(rock, "rock.glb", max_triangles=3000, uvs=uv_unwrap(angle=45, size=1024), materials=[stone, moss, gold], textures=bake(size=1024))
```

A texture is a picture the surface is painted with. A mesh program paints it by hand; here the surface *is* a field, so the picture is asked of the field: every texel
is a place on the surface (the UV map says which place), and what is there is read from the model. `bake(size, maps, padding, occlusion_samples, occlusion_distance,
occlusion_strength, uv_set)` says which pictures and how fine; `export_mesh(..., textures=bake(...))` makes them, writes them beside the mesh
(`rock_color.png`, `rock_normal.png`, `rock_orm.png`, `rock_emissive.png`), wires them to the materials, and a `.glb` has them inside as well.

- **`color`** (sRGB) is the material of the place -- `where` is read **at the texel**, so the edge between two materials is as sharp as the picture, not as coarse as the
  triangles -- times the vertex colours (`colors=`). A material's colour can be a field.
- **`normal`** is the normal map: the exact normal of the field at the place, in the tangent space of the mesh (red right, green up, blue out). A coarse mesh
  (`max_triangles`) shaded with it looks like the fine surface: the detail of the field is in the picture, not in the triangles. The file has the exact vertex normals
  and the tangents (`NORMAL`, `TANGENT`).
- **`orm`** is occlusion (red), roughness (green), metalness (blue), one linear picture, which glTF and the engines read. `"mr"` is roughness and metalness only,
  `"occlusion"` the occlusion alone.
- **`emissive`** is the glow of the materials.
- **The occlusion** is the ambient occlusion of the field: rays go out over the hemisphere from every texel, and a ray is blocked where the field gets near zero
  again (cone tracing along the ray: exact for a field that is a distance, a good guess for one that is nearly). It is made from the field, so it has no triangles in it.
- **`padding`** grows each island by that many texels, so that a filter or a mip map does not take in the empty ground beside it.
- **Needs** `uvs=` with islands that do not overlap (`"unwrap"`); the pictures are for the first map (`uv_set=1`: the second). In **OBJ** the `.mtl` names the colour,
  the normal map and the glow; the packed picture is a file beside it, since an OBJ has no way to say which channel is the roughness.

[`examples/39_baked_textures.py`](../examples/39_baked_textures.py) bakes a rock with a moss layer and gold in its cracks, reads the pictures back and checks the colours,
the metalness, the roughness, the occlusion, that every normal is a unit vector, that a coarse sphere has far more in its normal map than a fine one, and what the glTF
says.

### Skeleton and skin weights (glTF)

```python
hips = joint("hips", (0, 0, 92))
spine = joint("spine", (0, 0, 106), parent="hips")
shoulder = joint("shoulder.R", shoulder_point, parent="spine")            # a point works: the numbers it has when the file is written
bones = mirror_joints([hips, spine, shoulder, joint("hand.R", (37, 8, 92), parent="shoulder.R")])   # a ".L" joint for every ".R" one
export_mesh(hero, "hero.glb", skeleton=bones)                              # skin_falloff=8 for a wider blend at the joints
```

- **`joint(name, position, parent, tip)`** is a joint: where it is (a point or `(x, y, z)`), and the name of the joint it hangs from. The joints of a skeleton
  are listed in order, every joint after its parent, and there is **one root**. A joint with no children has a bone to its `tip`, given or the bone before it
  gone on for half its length (the hand goes on past the wrist). **`mirror_joints(joints)`** adds a `.L` joint, across x = 0 (`axis=`, `plane=` and `suffixes=`
  change that), for every `.R` one.
- **What is written** (`.glb`, `.gltf` only): the joints as nodes of the glTF, each a translation from its parent in metres with Y up; the skin with the
  inverse bind matrices; and for every vertex the four joints that move it and their weights (`JOINTS_0`, `WEIGHTS_0`), each set adding up to 1.
- **The weights** come from the bones: a joint has a bone to each of its children (the geometry between the elbow and the hand follows the elbow, as it does when
  the elbow is turned). A vertex belongs to the **nearest bone**, and so to its joint; near the two ends of the bone it is shared with the joint beside it --
  the parent at the start, the child at the end -- half at the very joint, less and less over `skin_falloff` millimetres along the bone (4 % of the model by
  default), none beyond. A bone that is only *near* -- the other leg -- never moves a vertex.
- **A joint can own a place.** `joint(name, position, parent, tip, influence=body_or_field)`: where `influence` is negative the skin follows that joint alone, fading
  to the bones' weights over `skin_falloff` millimetres outside. The joints are layers, as materials are: the later one is on top. A jaw, a finger, a tail tip, a cape --
  anything the bones do not shape. The weights are *functions of the place* of a vertex, not of the triangles it is in, so they are as smooth as the model and the same
  on both sides of a seam.
- **`max_influences=4`** (1 to 8) is the most joints that move a vertex: the strongest are kept and the weights made to add up to 1. Above 4 the file has `JOINTS_1` and
  `WEIGHTS_1` as well.
- It can be written with the materials, the colours, the texture coordinates and the baked textures in the same file. A whole character -- limbs, body and skeleton
  from the same nodes -- is in [Characters](characters.md#armatures-limbs-a-character-a-skeleton).

### The origin of the asset, and levels of detail

```python
export_mesh(hero, "hero.glb", pivot="base")                      # the middle of the bottom of the model is the origin: the feet are at z = 0
export_mesh(hero, "hero.glb", pivot=(0, 0, 92))                  # a place of your own: here the hips
export_lods(hero, "hero.glb", [8000, 2000, 500])                 # hero_lod0.glb, hero_lod1.glb, hero_lod2.glb
```

- **`pivot=`** says where the origin of the file is: `"origin"` (the default: as modelled), `"base"` (the middle of the bottom of the model: a character or a prop
  that stands on the ground), `"center"` (the middle of its box), or a place `(x, y, z)` of the model. It is done last, so that the materials (`where`), the
  skin weights and the symmetry are made where the model is; the skeleton moves with it.
- **`export_lods(part, path, triangles, **options)`** writes a level of detail for each budget, `hero_lod0.glb` for the first: at most that many triangles
  (see `max_triangles`), the finest first and each smaller than the one before; `None` for a first level with no budget. The other options -- units, up
  axis, symmetry, materials, skeleton, pivot -- are the same for every level. It returns the paths. The levels are meshes of their own resolution, not decimations,
  so each is an even mesh of the same body.

[`examples/37_pivot_and_lods.py`](../examples/37_pivot_and_lods.py) writes them and reads them back: the box of each pivot, the skeleton that follows it, the
budgets of three levels.

[`examples/36_skeleton.py`](../examples/36_skeleton.py) reads the file back and checks the nodes and the hierarchy, the inverse bind matrices, that the tip of the
hand, the head, the forearms, the shin and the foot are moved by their joints, that no joint of the left half moves a vertex of the right, and the refusals.

**FBX is a proprietary format** of Autodesk, whose SDK is available under its own licence and whose files have no published specification. FielDev
reads and writes FBX **without the Autodesk SDK**, from the structure of the files as the community documents it (the node tree, the property types,
the objects and their connections), and handles **meshes only**: geometry, the transform of the models that hold it, the scene's unit and up axis -- no
materials, animation, skins or cameras. Because the format is not specified, another program may read less of what FielDev writes than FielDev reads of
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
