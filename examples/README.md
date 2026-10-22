# Examples

Open one with **File → Open example file**, or run it without the application:
`python scripts/run_example.py examples/04_handles.py`. **Every example runs as it is** and makes its own geometry from
primitives, fields and points; the application switches to a script's folder when it opens it. Every one of them opens in under
two seconds, except `12` (mesh export and import), which writes a mesh and reads it back the first time it runs.

| Script | Part | Shows |
|---|---|---|
| `04_handles.py` | none (a small crate) | the gizmo (`gizmo()`: click / never / always), the handles on the surfaces (`handles()`), and the lock, of the model tree |
| `12_mesh_export_and_import.py` | none (a cup) | STL out with `save_stl` and back in with `import_model` |
| `18_fields_everywhere.py` | none | wherever a number goes, a field goes: a plate grown by a field (`offset`), a blend radius that varies (`smooth_union`), a smoothing radius that varies (`smooth`), driven from a `point` |
| `20_custom_blocks.py` | none | custom blocks (`blocks/sample_blocks.py`): `perforate` with a field radius, `bracket` |
| `21_low_level.py` | none | low-level fields, as in libfive's Scheme `define-shape` / `remap-shape`: a cube from six plane distances (`.max`), a twist by `.remap`, a ball and a torus from their formulas joined by a smooth minimum of your own, a gyroid cut to a cube; evaluating and printing a tree |
| `22_export_files.py` | none (a beam with a hole) | exporting: `export_mesh` in every format (STL, OBJ, PLY, 3MF, glTF, FBX, OFF, DXF); sections in the model tree |
| `26_profiles_and_sweeps.py` | none | points, a **profile** (corners and a spline point), `extrude`, a `spline` and `path_extrude` of a profile whose thickness follows the scale of a point: pull a point out of an edge, double-click a point, scale it with its ring |
| `27_copies_and_linked_copies.py` | none (a plate with lugs and bolts) | `Shift+D` (a copy) against `Ctrl+D` (a linked copy, `instance`): three bolts that follow the first one, a lug copied and changed on its own; shadows in the model tree |
| `28_profile_on_a_plane.py` | none | a profile in a tilted plane, `extrude` along the normal of its plane, a smooth badge on it, and how to draw on the plane with the **work plane** (`Shift+W`) |
| `29_symmetry.py` | none (a round table: a top, and one leg -- a profile swept along a spline) | a three-way **symmetry** (`symmetry_planes(kind='turn', copies=3)`: three turned copies, nothing mirrored -- any number up to 24, or planes): select it and everything you make is made at its images too; `symmetry_images(leg, mirror)` is the other legs **and their splines** as one model (the sweep and its path are mirrored together); dragging a dot of any leg's spline drags the original's point, changing the copies on the card redraws the legs; `Shift+S`, selecting the images brings back the mirror they were made in |
| `30_noise_kinds.py` | none (ten balls) | `noise_field`: the five kinds (`perlin`, `billow`, `ridged`, `cellular`, `cracks`), a stretch per axis, a `warp`, one octave against six, and a scale that is a field -- each ball is `ball - depth * noise`, so the relief is the noise |
| `31_texture.py` | none (twelve blocks) | `texture`: the six patterns (`grit`, `stipple`, `leather`, `ribs`, `dimples`, `knurl`), on the top face only (`select_surface`) or inside a body (`region`), `side='in'` / `'out'`, a pattern of your own, and a depth that is a field |

(Open each script: the comment at its top says what to look at.)
