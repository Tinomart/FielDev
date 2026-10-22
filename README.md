<p align="center">
  <img src="app/deploy/icon/fieldes.png" width="96" alt="FielDes">
</p>

# FielDes

**Field-driven modelling.** A scriptable modelling workbench in which every shape and every design parameter is a *field* — a value at
every point in space — so that **anything can drive anything**: a point you drag moves a whole swelling of a plate, a noise field roughens a
rock, a ramp over the distance to an anchor sets the radius of a blend.

> **This repository is FielDev**, a fork of FielDes that is being trimmed for **modelling for game development**: the world of a game
> from primitives, its characters from points. What is here is the modelling core. The engineering side of FielDes (finite-element
> analysis, flow, topology optimisation, lattices, STEP/CAD import, manufacturing checks) has been taken out, and the game outputs
> (symmetrical meshing, materials and shaders, textures and UVs, bone mapping) are not built yet. The product still carries the name
> FielDes everywhere (the name, the `fieldes` package, the environment variables); renaming it is the last step of the trim.

Wherever a number goes in FielDes, **a field goes**: `offset(part, 1.0)` grows a part by a millimetre everywhere;
`offset(part, ramp(distance_to_point(anchor), (0, 60), (4.0, 0.3)))` grows it by 4 mm near the anchor and 0.3 mm far from
it. The two are written alike, and the field is evaluated exactly where it is needed — never sampled onto a grid.

FielDes models with implicit functions (signed distance fields), reads triangle meshes as exact distance fields, writes meshes out,
and keeps the script and the viewport in step: every button in the viewport edits the script, and every edit of the script re-renders
the viewport. **A mesh is only ever the output**: the field is the model.

## The idea

- **The script is the model.** What you see is what a Python script says. Every drag and every button in the viewport is an
  edit of that script — readable, undoable, shareable.
- **Everything is a field.** Shapes, distances, ramps, noise: numbers at every point,
  combined with ordinary arithmetic. Any of them can stand where a number stands.
- **Direct manipulation, written down.** Pull a surface or a gizmo: the numbers in the script change. Edit a number: the
  viewport follows.
- **Your own building blocks.** A function in a file of the blocks folder is there in every script, with completion, call
  tips and a place in the menus.

New here? A welcome card offers a **guided tour** the first time FielDes starts (**Help → Guided tour** any time after): short cards over the
program itself that point at what they talk about and let you try it. The [tutorial](docs/tutorial.md) is the written version.
**File → Open example file** has 19 scripts (`00_START_HERE.py` says where everything is); the [examples README](examples/README.md) lists them.

## What it does

| | |
|---|---|
| **Fields everywhere** | Every size, radius, thickness, spacing and blend of every function takes a field instead of a number. [How it works](docs/fields.md#fields-everywhere) |
| **A typed, nested model tree** | Every kind of thing — 3D shape, 2D shape, curve, field, surface, point, point set, imported mesh, symmetry, custom block — has its own colour and icon. The models an operation is made of are its children, **and nesting always edits the call**: drag a row onto an operation to make it an input, out of one to take it out, between its children to reorder them; a model used twice has a half-transparent **shadow** row at its other use; `Ctrl`+drag adds a reference without moving the model. [The tree](docs/interface.md#the-model-tree) |
| **Make things from the context menu** | Right-click empty space, a model or a row of the model tree: the menu makes a shape, a point, a surface or a field, or adds an operation (offsets, moving, **field math**, ...) to the model you clicked, and writes the script where you clicked. *low_level_field* and *low_level_body* write a function of x, y and z for you to put your own logic in. [The menus](docs/interface.md#right-click-anywhere) |
| **Your own primitives** | *Primitives → Manage primitives…* chooses which shapes the menus offer as primitives, under their kind, adds a model of your own to the list, and renames any of them. [Your own primitives](docs/interface.md#your-own-primitives) |
| **Fields you can see** | A field is not a body, so it is not drawn: it is **an icon in the viewport with its name over it**, where the object it was made from is (an eye in the tree shows or hides it). Click the icon -- or select the field in the tree -- and its **field viewer** opens: a disc of the field, coloured by its value at every point, with a radius slider and arrows to move it. Arithmetic works on fields as it does on numbers (`a * b`, `2 ** a`, ...), and `field_from_body(body)` turns a body into a field you may multiply freely. |
| **Custom blocks** | A few lines in a file of the blocks folder make a function that is in every script — completion, call tips, menu entries, hot reload. [Custom blocks](docs/blocks.md) |
| **Apps for everyone else** | A script declares its inputs (`app.number`, `app.file`, `app.save_as`, ...) and is exported as **one `.fieldesapp` file**; whoever double-clicks it sees **a form, a Run button, a log and the files that were made** — no editor, no code. It runs without a window too (`FielDes run tool.fieldesapp --Radius 7`) and, with Watch, runs again by itself when an input file changes. [Apps](docs/apps.md) |
| **Model with fields** | Primitives, CSG, smooth and chamfered booleans, offsets, shells, twists, bends, repeats, extrusions, revolves, helical and parametric surfaces — all of them fields, composable with ordinary arithmetic. |
| **Edit by dragging** | A gizmo (`gizmo()`: move, rotate, scale), handles on the surfaces of a shape (`handles()`), and `var()` numbers — what you drag is written back into the script. Every primitive (box, sphere, cylinder, cone, torus, pyramid, prism, rounded box, and the flat circle, rectangle, ring, polygon and triangle) has handles that move the face you pull and no other. |
| **Python, as it is** | The script is plain Python and the model tree shows it: an `if`, a loop, `with`, `try`, a function or a class is a row, with the variables and statements in it under it (locked there: the code is edited in the editor), and a block moves by drag. What you add from the tree goes to the **insertion point** -- click between two rows -- which follows the text cursor of the editor. `Ctrl+E` extrudes the selected 2D shape. [Python in the tree](docs/interface.md#python-in-the-tree) |
| **Shapes from points** | Points are models of their own. A **profile** is the 2D shape a closed outline through points encloses (corners, spline points with `smooth=True`, or round corners with `radius=`: an exact arc takes the place of the corner); `extrude` pulls it into a solid and `path_extrude` sweeps it along a `spline` (the scale of a point is how thick the sweep is there). Press an edge and drag to pull a point out of it; double-click a point to switch it between a corner, a spline point and a round corner. A **work plane** (`Shift+W`) is a grid to draw lines, splines and points on, in any plane. [Profiles](docs/profiles.md) |
| **Copies and linked copies** | `Shift+D` copies a model. `Ctrl+D` **links** it: `bolt_2 = instance(bolt)` is the bolt itself, follows every change of it and can only be moved and rotated; the bolt is held by a shadow reference and keeps its own row. [Copies](docs/handles.md#copies-shiftd-and-ctrld) |
| **Texture, noise, symmetry** | `texture(body, 'grit' / 'stipple' / 'leather' / 'ribs' / 'dimples' / 'knurl', ...)` lays a pattern of small bumps and pits over a body, or over a region of it; five kinds of noise (perlin, billow, ridged, cellular, cracks) are fields that can drive anything; a symmetry is a model of the script, and whatever you make is made at its images too. |
| **Inspect** | A section card that cuts the model and paints a field on the plane; curvature and depth fields; hover probing; legends. |
| **Characters from points** | `chain([points], radii)` makes a limb of round cones between joints; the size of a point -- the ring of its gizmo -- is how thick the limb is there; blend limbs into a body and mirror the other half. [Characters](docs/characters.md) |
| **Meshes in and out** | `import_model()` reads STL, OBJ, PLY, 3MF, glTF, FBX, OFF and DXF as exact distance fields (a mesh with holes imports too); `export_mesh` writes the same formats; `export_field` samples any field on a grid (VTK, CSV). [Meshes](docs/meshes.md) |
| **Fast to work in** | Content-addressed caches (imports, exact distances), a render cache for finished meshes, per-statement progress, breakpoints, go to definition into any library or module file (opened in a tab), hot reload of imported files and blocks, cancel for slow renders. |

## Quick start

1. FielDev has **no release and no installer yet**: build it from source with `scripts/build-linux.sh` or `scripts/build-windows.ps1`
   (see [Building](docs/building.md)). There is no macOS version.

   FielDes speaks English, Spanish, French, German, Japanese, Chinese and Russian (the language of the system by default; **Settings → Language**).
2. Open a script from `examples/` (every one runs as it is and makes its own geometry), or write one: `import_model("rock.obj")` brings in a mesh.
3. Right-click empty space to make a shape; click a row in the model tree and drag the gizmo; open the section card
   (`Shift+X`); hover the model.
4. `Shift+F1` opens the guide with every feature and shortcut; `F1` the shape reference.

The smallest script:

```python
from fieldes import *

view.set_bounds([-35, -25, -8], [35, 25, 30], auto_scale=True)    # the region the viewport meshes
view.set_resolution(6)                           # samples per mm
view.set_quality(8)

plate   = box((-30, -20, 0), (30, 20, var(6)))        # var(...): a number you can drag in the viewport
anchor  = point(20, 10, 6)                                    # a point is a model, and a value where a coordinate goes
swell   = ramp(distance_to_point(anchor), (0, 45), (3.0, 0.5))   # 3 mm at the anchor, 0.5 mm 45 mm away: a field
offset(plate, swell)                                          # a field where a number goes
```

The last expression is what is shown; assign other shapes to names and they appear in the model tree.

## Examples

**Every example runs as it is** and makes its own geometry from primitives, fields and points; none needs a model file. Open one with
**File → Open example file**, or run it without the application with `python scripts/run_example.py examples/04_handles.py`.

| Example | Shows |
|---|---|
| [`00_START_HERE.py`](examples/00_START_HERE.py) | Where everything is: the examples by subject |
| [`04_handles.py`](examples/04_handles.py) | The gizmo (its click / never / always modes), dragging surfaces, and the lock |
| [`12_mesh_export_and_import.py`](examples/12_mesh_export_and_import.py) | STL out and back in |
| [`18_fields_everywhere.py`](examples/18_fields_everywhere.py) | A plate grown by a field, a blend whose radius varies, a smoothing whose radius varies — driven from a point |
| [`20_custom_blocks.py`](examples/20_custom_blocks.py) | Your own blocks: `perforate` with a field radius, `bracket` |
| [`21_low_level.py`](examples/21_low_level.py) | Low-level fields, as in libfive's Scheme `define-shape` / `remap-shape`: a cube from six plane distances, a twist by a remap, a ball and a torus from their formulas, a gyroid |
| [`22_export_files.py`](examples/22_export_files.py) | Exporting: every mesh format |
| [`26_profiles_and_sweeps.py`](examples/26_profiles_and_sweeps.py) | Shapes made of points: a profile, an extrusion, a line and a sweep |
| [`27_copies_and_linked_copies.py`](examples/27_copies_and_linked_copies.py) | Two kinds of duplicate: a copy, and a linked copy that follows its original |
| [`28_profile_on_a_plane.py`](examples/28_profile_on_a_plane.py) | A profile in a plane of its own: the work plane |
| [`29_symmetry.py`](examples/29_symmetry.py) | A symmetry as a model of the script: a round table with three curved legs, one of them drawn |
| [`30_noise_kinds.py`](examples/30_noise_kinds.py) | Noise, one of every kind, and what scale, octaves, stretch and warp do to it |
| [`31_texture.py`](examples/31_texture.py) | A pattern of small bumps and pits laid over the surface of a body: grit, stipple, leather, ribs, dimples, knurl |
| [`32_game_export.py`](examples/32_game_export.py) | Exporting for a game engine: the unit and the up axis, a budget of triangles, a mesh that is exactly symmetric — each checked by reading the files back |
| [`33_character.py`](examples/33_character.py) | A character from points: limbs that taper between joints (`chain`, `round_cone`), blended into one body, the other half made by a mirror |
| [`34_materials.py`](examples/34_materials.py) | Materials by region (a body or a field) and vertex colours from fields, written as OBJ + MTL, glTF and PLY — each checked by reading the files back |
| [`35_uvs.py`](examples/35_uvs.py) | Texture coordinates by the box projection, fitted or world-scaled, with the seams made, and the image of a material — OBJ, glTF and PLY, checked by reading them back |
| [`36_skeleton.py`](examples/36_skeleton.py) | A skeleton of joints (`joint`, `mirror_joints`) and the skin weights of the mesh, written as a rigged glTF — nodes, inverse bind matrices, `JOINTS_0` and `WEIGHTS_0`, checked by reading the file back |
| [`37_pivot_and_lods.py`](examples/37_pivot_and_lods.py) | Where the origin of an asset is (`pivot="base"`: standing on the ground) and levels of detail with a budget of triangles each (`export_lods`) — checked by reading the files back |

## Documentation

| | |
|---|---|
| [Tutorial](docs/tutorial.md) | The idea, the window, the controls that matter, in a short walk |
| [Getting started](docs/getting-started.md) | Install, first script, a tour of the window |
| [The interface](docs/interface.md) | Top bar, editor, viewport, the typed and nested model tree, drag and drop, section card, shortcuts |
| [Scripting](docs/scripting.md) | Shapes, fields, `var()`, view settings, what gets displayed |
| [Fields and regressions](docs/fields.md) | **Fields everywhere**, points and surfaces, distance fields, maps, `fit()`, coloring |
| [Custom blocks](docs/blocks.md) | Your own functions, in every script |
| [Apps](docs/apps.md) | A script as a program for other people: inputs, the form, `.fieldesapp`, `FielDes run`, watch |
| [Handles](docs/handles.md) | The gizmo, the handles on the surfaces, `gizmo()` and `handles()` |
| [The symmetry](docs/interface.md#the-symmetry) | A symmetry is a model of the script -- mirror planes through a centre (`symmetry_planes`); select it and everything you make is made at its images too (`symmetry_images`: all the images of a model are one model), which follow both the model and the symmetry; `Shift+S` |
| [Profiles, lines and extrusions](docs/profiles.md) | Shapes made of points: `profile`, `polyline`, `spline`, `extrude`, `path_extrude`; pull a point out of an edge, double-click a point for a spline, rotate and scale a point to shape the curve and the sweep |
| [Selecting surfaces](docs/selecting-surfaces.md) | Right-click a face: a flood-filled surface as a field, to work on one part of a body |
| [Meshes](docs/meshes.md) | Mesh import and export, with the units, up axis, triangle budget and exact symmetry a game engine asks for |
| [Characters](docs/characters.md) | Limbs and bodies made of points: `chain`, `round_cone`, a mirror for the other half |
| [Caching and performance](docs/caching-and-performance.md) | What is cached, resolution and quality, long renders |
| [Troubleshooting](docs/troubleshooting.md) | Empty viewport, slow renders, import errors |
| [Library reference](docs/reference.md) | Every function and class, from its docstring |
| [Architecture](docs/architecture.md) | How the kernel, the Python library and the application fit together |
| [Building from source](docs/building.md) | Building on Windows (MSVC and vcpkg) and on Linux |

## Known limitations

What is a rough edge rather than a limit of the design is in [KNOWN_ISSUES.md](KNOWN_ISSUES.md); **Help ▸ Report a bug** opens a new issue with your version and system filled in.

- **A mesh is an output.** Every shape is a field; an imported mesh becomes an exact distance field, and a mesh is made from a field when you export or
  look at it. There is no mode that edits the triangles of a mesh.
- **Units:** STL/OBJ/PLY/OFF carry none and are assumed to be millimetres (`file_units=`); 3MF, FBX and DXF say what they are, and glTF is always in metres.
- **Windows and Linux** are the platforms the build scripts know; the program has been built in a Linux cloud container but not looked at in a window there. There is no macOS version.

## Project layout

```
kernel/       the C++ kernel: field evaluation, meshing, mesh import  (fieldes.dll)
python/       the Python library  (import fieldes)
app/          the Qt application  (FielDes.exe)
blocks/       the custom blocks folder: sample blocks, and where yours go
examples/     example scripts
tests/        what checks the work: tests/verification/00_START_HERE.py is the file to open (the walkthroughs)
docs/         documentation
scripts/      build scripts, headless runner, reference generator
installer/    the Windows setup program
```

## Credits and licence

FielDes was created by its author ([Tinomart](https://github.com/Tinomart)) **with the help of Claude Code**
(Anthropic's AI coding assistant): the author set the direction and the design, tested the result and decided what
stays; much of the code was written together with Claude Code.

FielDes stands on **libfive** by Matt Keeter ([github.com/libfive/libfive](https://github.com/libfive/libfive)):
its kernel (`kernel/`, namespace `libfive`) and Python bindings (`python/`) are under the
**Mozilla Public License 2.0** (`LICENSE-MPL-2.0`), and the application (`app/`) derives from its
**Studio** GUI and is under the **GNU General Public License, version 2 or later** (`LICENSE-GPL-2.0`).
Files added for FielDes carry the licence of the part they belong to. See [`NOTICE.md`](NOTICE.md) for the
list of third-party components (Qt, Eigen, Boost, Manifold, libpng, Python, the Inconsolata font).
