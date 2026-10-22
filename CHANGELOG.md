# Changelog

FielDev is a fork of FielDes (a field-driven design workbench: a C++ kernel on libfive, a Python library and a Qt application), trimmed for **modelling for game development**.
What FielDes did before the fork is in the git history of this repository (this file used to hold it).

## 1.0.0 (not released)

### A Character section: limbs, a character, a skeleton, reference images
- **Right-click → Character** (between *Operations* and *Python*, in the menu of empty space and in the menu of a model): **Draw a limb**, **New limb**, **character**, **skeleton_of**, and **Reference image →** front, back,
  right, left, top, bottom.
- **Limb mode of the work plane** (a fourth button next to Line, Spline and Point): click the nodes of a limb one after another over a picture, `Enter` ends it, `Backspace` takes the last node back. Each node is a point with
  a gizmo -- the joint of the skeleton, its scale the thickness of the limb there -- and the limb is `limb([...], radii=..., name=...)`. The work plane is made from the view when the mode starts, so the first click lands on the picture
  you are looking at.
- **`limb`, `character`, `skeleton_of`** (`fieldev.stdlib.armature`): a limb is a swept cross-section along a smooth curve through its nodes, round (round cones, with the thickness following a smooth curve through the nodes'
  thicknesses) or any 2D shape by `path_extrude` (`profile=`, carried to its nodes); `character` joins limbs with a blend and mirrors the other half; `skeleton_of` makes a joint for every node, a limb that starts on a joint of another
  hangs from it.
- **Reference images** (`reference_image(path, plane=..., height=..., center=..., opacity=...)`): a picture standing in the scene behind the models, in the plane of a standard view (a picture reads the right way round in the
  view of its name; the character faces -y, as a glTF made of it faces +z), drawn with its own shader, in perspective -- the camera is free. A script that has nothing but pictures to look at is shown from its render region.
- `docs/interface.md` (*Reference images*, the work plane's Limb mode, the Character section), `docs/characters.md` (*Building a character in the viewport*), `examples/40_armature.py`.

### UV maps and textures baked from fields
- **UV maps** for `export_mesh(..., uvs=...)`: `uv_box`, `uv_planar`, `uv_cylinder`, `uv_sphere` and **`uv_unwrap`** -- the surface cut into islands where it turns (the cut follows the angle you give, on a smoothed normal), each laid flat
  by a conformal map (planar projection where that is not possible), scaled to one texel size, rotated to its smallest box and packed into the square; a second set (`TEXCOORD_1`) for a lightmap; the picture of the layout (`uv_layout=`).
  `examples/38_uv_maps.py`.
- **`bake(...)`** (`textures=`): every texel of a picture is a place on the surface, and what it is made of is read from the fields there -- the **colour** (materials by region, colours and values that are fields), the **normal map**
  (the exact normal of the field in the tangent space of the mesh: a coarse mesh shaded with it looks like the fine surface), **occlusion, roughness and metalness** (a soft ambient occlusion by tracing the field), with padding
  at the islands' edges. PNG files are written by the library itself (`fieldev.stdlib.pngfile`); a `.glb` carries the pictures inside it, an OBJ names them in its `.mtl`. `examples/39_baked_textures.py`.
- **Exact vertex normals** from the gradient of the field (`normals=`), tangents in the glTF, normals in the OBJ and the PLY.

### PBR materials
- `material(...)`: colour, roughness, metalness, opacity and emission, each a number **or a field**; alpha mode, double sidedness, IOR, transmission, clear coat, sheen, normal scale; `where=` for the region of a material;
  **24 presets** (`material_preset`, `material_presets`). Written as glTF materials with their extensions, and as OBJ + MTL.
- **`with_materials(model, [...])`**: the model shown in the viewport in the colours of its materials (the same layers an export paints, found at every vertex of the mesh; the edge between two is cut as sharp as the mesh is fine), with a
  key of their names; `export_mesh` writes the same materials when it is not given `materials=`. The roughness, metalness, glow, opacity and textures are only in the exported file.

### Rigging
- `joint`, `mirror_joints`, `skeleton_of`; skin weights by the nearest bone with a blend at the joints, **a joint that owns a place** (`influence=` a body or a field: the skin there follows it alone, fading outside it over
  `skin_falloff`), and up to **eight** joints a vertex (`max_influences`, `JOINTS_1` / `WEIGHTS_1`). A rigged glTF has the skin, the inverse bind matrices and the weights. The skeleton is the output of a model that is not animated:
  FielDev writes the bind pose; it has no animation and no morph targets.

### Exporting for a game engine
- `export_mesh`: the unit and the up axis (`units=`, `up=`), a budget of triangles (`max_triangles=`) and `export_lods`, a mesh that is exactly symmetric (`symmetric=`), the origin where the asset stands (`pivot="base"`), materials
  by region and vertex colours from fields; STL, OBJ, PLY, 3MF, glTF (`.glb`, `.gltf`), FBX, OFF and DXF.

### The product
- **Renamed from FielDes**, so that FielDev shares nothing with an installed FielDes: the application and organisation names, the `FIELDEV_*` environment variables, the Python package `fieldev`, the kernel libraries
  (`fieldev`, `fieldev-stdlib`), the `.fieldevapp` file type and the user-visible name. The licences stay: GPL 2 or later for the application, MPL 2.0 for libfive (`NOTICE.md`).
- **Taken out** (they are not what a game asset needs): the finite-element, thermal and flow solvers, topology optimisation, lattices, STEP / CAD import, manufacturing checks, and their menus, cards, glyphs and examples. The
  examples are rebuilt on primitives, fields and points.
