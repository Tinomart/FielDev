# Architecture

FielDes has three layers, in three folders. Each can be used without the ones above it.

```
   app/        Qt application  (FielDes.exe)        GPL-2.0-or-later
     │  embeds Python, draws the viewport, edits the script
   python/     Python library  (import fieldes)     MPL-2.0
     │  Shape, the standard library, mesh import and export, fields, points, curves and profiles
   kernel/     C++ kernel      (fieldes.dll)        MPL-2.0
        expression trees, evaluators, meshing, mesh import, field oracles
```

- [The kernel](#the-kernel)
- [The Python library](#the-python-library)
- [The application](#the-application)
- [How a script becomes a picture](#how-a-script-becomes-a-picture)
- [Selecting a surface](#selecting-a-surface)
- [The render cache](#the-render-cache)
- [The field cache](#the-field-cache)
- [FielDes apps](#fieldes-apps)
- [Files FielDes writes](#files-fieldes-writes)
- [Environment variables](#environment-variables)
- [Origins and licences](#origins-and-licences)

## The kernel

`kernel/` is C++17, built as the shared library `fieldes.dll` (and a small `fieldes-stdlib.dll` of
C++-defined shapes). It descends from **libfive**, Matt Keeter's kernel for implicit modelling.

| Folder | Holds |
|---|---|
| `src/tree`, `include/libfive/tree` | The expression **tree**: immutable, hash-consed expressions of `x, y, z` and constants/variables; serialisation; the structural **content key** used by every cache; `expose` (the kernel call behind `handles()`: turns the numbers that place surfaces into variables) |
| `src/eval` | Evaluators for trees: point, array (SIMD), interval, derivative, and feature-aware evaluation; a **call** runs the field it calls on evaluators of that field's own (`Callee`, one per distinct called field, shared by every call site of a deck) |
| `src/render/brep` | The meshers: dual contouring, simplex and hybrid, with an octree/xtree that splits regions until a cell is 1/resolution. Where an oracle is on the tape (a mesh's distance costs about a microsecond a point) the dual contouring finds the surface along an edge by bisection (10 points) instead of 4 stages of 16 |
| `src/render/discrete` | Heightmaps and voxels |
| `src/oracle` | *Oracles*: nodes of a tree that are evaluated by code instead of by arithmetic (meshes, data fields, distances to points and curves), with per-point memoisation |
| `src/solve` | The small solver that turns a drag in the viewport into changes of `var()` numbers |
| `src/mesh_import` | STL/OBJ/PLY/3MF/glTF → cleaned triangles → exact signed-distance oracle (spatial search structure, generalised winding numbers) |
| `src/fields` | Field oracles: distances to points and curves, curvature, scattered data, noise; the flood fill of `select_surface` (`surface_select.cpp`) |
| `stdlib` | Shapes defined in C++ |

### The call node: a field asked at a computed point

`CALL` (opcode 33, `Tree::call`, `libfive_tree_call`, and `f(x', y', z')` in Python) is the value a field `f` has at the point `(x', y', z')`
computed from `x, y, z`. It is what `remap` means, evaluated in another way. A **remap** is a substitution: `flatten` expands it into a copy
of `f` for every place it is used, which is right when `f` is used once (every transform) and wrong for a field asked at a hundred places
(a smoothing, the images of a symmetry, a part that stands in many places, a probe along a line: a hundred copies of a big field are a hundred
times the nodes to build, optimise and hold). A **call** keeps `f` as it is: its `Deck` is compiled once into a `Callee` (shared through the
`CalleeRegistry` of the top-level deck, so a field called from many sites, or from inside another called field, is one), and the evaluators of
the caller run it on the arguments' values. `Tree::flatten(share, Calls::Inline)` expands calls like remaps (what the classic consumers get);
`Calls::Keep`, which `walk()`, `optimized()` and the `Deck` use, keeps them and flattens the called field once on its own.

Every evaluator knows it. The array evaluator runs the callee on the points; the derivative evaluator seeds the callee's x, y, z derivatives with
the arguments' (the chain rule), also when the derivatives are those with respect to the `var()`s (so dragging a handle works through a call);
the feature evaluator combines the callee's feature lists (sharp edges); the interval evaluator runs the callee over the box the arguments
reach and **shortens the callee's tape for that box** (`Tape::calls`, one per call site), so the renderer's pruning goes into a called field.
An oracle that is substituted (`flatten` of a remap over an oracle) is called, not rebuilt: there is no transformed oracle. `Tree::optimized()`
counts the ways to reach a node, including through the arguments of a call, before it decides to optimise a graph.

The C API is `kernel/include/libfive.h`; the Python library calls it through `ctypes`.

## The Python library

`python/fieldes/` — `from fieldes import *`.

| File | Holds |
|---|---|
| `ffi.py` | Loads `fieldes.dll` (found through `FIELDES_DIR`, next to the package, or on the path) and declares the C API |
| `shape.py` | `Shape`: the wrapper of a tree, operators, evaluation, `save_stl`, `get_mesh` |
| `view.py` | `view.set_bounds / set_resolution / set_quality` |
| `stdlib/shapes.py`, `csg.py`, `transforms.py`, `text.py`, `surfaces.py` | Primitives, booleans, transforms, lettering, closed-form surfaces |
| `stdlib/importing.py`, `mesh_import.py`, `import_log.py` | `import_model()` and `tessellate()`; reading triangle meshes into an exact distance field; the log of a session's imports, from which the model tree lists an import's parts |
| `stdlib/exporting.py`, `meshfiles.py`, `fbx.py` | `export_mesh()` and `export_field()`; the mesh-file writers, and the readers of the formats the library does not read itself (FBX, with no Autodesk code behind it) |
| `stdlib/distance_field.py` | Exact distances and rolling balls read from a field itself (nothing is meshed) |
| `stdlib/fields.py`, `regression.py` | Fields, regressions |
| `stdlib/fieldargs.py` | The helpers that let a function take a number *or a field* (`number_or_field`, `positive`, `present`, ...), and the decorators that mark what a function returns (`returns_field`, `returns_body`) |
| `stdlib/points.py` | `Point` and `Surface` (models of their own), `point()`, `plane()`, `sphere_surface()` ..., and `displayed()`: how a profile, a surface, a point and a field are drawn |
| `kinds.py` | What a model *is* (`kind_of`: solid, curve, profile, field, surface, point, points, import, symmetry, block) and the colour of each; the kernel's `libfive_tree_axes` tells a 2D shape from a 3D one |
| `blocks.py` | The custom blocks: the files of the blocks folder, hot reload by modification time, what the editor and the menus are told about them |
| `stdlib/curves.py`, `profile.py`, `surface_profile.py` | 1D shapes (a line or a spline through points); a 2D shape from points or a closed curve (`profile`), `extrude` and `path_extrude`; the outline of a surface for `profile(surface)` |
| `stdlib/instances.py`, `symmetries.py` | Linked copies (`instance`); symmetry (`symmetry_planes`, `symmetry_images`) |
| `stdlib/selection.py`, `measure.py`, `custom_resolution.py` | `select_surface()`; the box and the middle of a body; a resolution of its own for one body |
| `stdlib/handles.py` | `gizmo()`, `handles()`, `lock()` |
| `app.py`, `app_package.py`, `__main__.py` | FielDes apps: the `app.` inputs a script declares; reading the form out of the text of a script, bundling a `.fieldesapp`, opening one, checking the values, the command line (`run`, `export`, `info`, `--watch`); see [Apps](apps.md) |
| `stdlib/content_cache.py`, `stdlib/render_cache.py`, `field_cache.py` | Content-keyed caches, the render cache and the field cache (see below) |
| `app_support.py`, `run_progress.py`, `runner.py` | What the application needs from Python: running a script statement by statement (with the blocks injected into its namespace), evaluating displays, the model tree's description (`scene_json`: items with their `type`, `inputs`, `owner`, ...), reporting progress |
| `menu_catalog.py` | The one list of what the right-click menus offer (primitives by kind, operations, custom blocks) and the call each entry writes |
| `outline.py`, `made_from.py` | The model tree, read from the script's text; what a model was made from |
| `profile_edit.py`, `symmetry_creation.py`, `user_primitives.py` | What the viewport writes when a point is pulled out of an edge, or when something is made while a symmetry is selected; the primitives the menus offer, and your own |
| `completion.py`, `i18n.py` | Writing a call with every argument visible; the language of the words the Python side shows |

## The application

`app/` — Qt 5 (Fusion style with a custom stylesheet, `theme.cpp`), OpenGL for the viewport.

| File | Holds |
|---|---|
| `main.cpp`, `app.cpp`, `args.cpp` | Start-up, command line (`FielDes run|export|info ...` runs the apps' command line with no window: Python starts and `app_support.app_cli` does the work; a `.fieldesapp` as the first argument opens the app window) |
| `appwindow.cpp`, `fileassoc.cpp` | The app window (a form built from the manifest's inputs, Run / Stop, progress, log, outputs, watch; its own `Python::Interpreter` thread) and the `.fieldesapp` file type (HKCU registry keys on Windows, a MIME type and a desktop entry on Linux) |
| `window.cpp` | The main window: the top dock and its menus, import code generation, guide and dialogs, autosave, file watching |
| `editor.cpp`, `script.cpp`, `syntax.cpp`, `findbar.cpp`, `documentation.cpp` | The code editor and its helpers |
| `python/interpreter.cpp` | The embedded Python interpreter (host module `_fieldes_host`: `var()`, `view.set_*`, display callbacks) |
| `view.cpp`, `shape.cpp`, `camera.cpp`, `shader.cpp`, `gl/` | The viewport: meshes, picking, dragging, drawing |
| `scenetree.cpp` | The model tree: rows, nesting by the scene's `owner`, selection, every action as a script edit, drag and drop (`SceneTree`, `moveGroups`, `dropOnModel`) |
| `typeicons.cpp` | The icon and colour of each kind of model, shared by the tree and the menus |
| `section.cpp` | The section card: the plane evaluated exactly on all cores |
| `tutorial.cpp` | The guided tour |
| `workplane.cpp`, `symmetry.cpp`, `primitives_dialog.cpp` | The work plane, the symmetry and the *Manage primitives* dialog |
| `shortcuts.cpp`, `language.cpp`, `i18n.cpp` | The shortcuts and their rebinding; the language of the program, and of the words Qt itself shows |
| `theme.cpp`, `icons.cpp` | Colours and the drawn icons |
| `automation.cpp` | A scripted-GUI facility for testing (see below) |

The application finds its Python runtime in `runtime/python3` (the portable folder) or in a vcpkg
checkout, and the `fieldes` package by walking up from its own folder for `python/fieldes`.

## How a script becomes a picture

1. The editor's text is run **statement by statement** in the embedded interpreter. The interpreter records
   every top-level expression that evaluates to a shape (or a list of shapes), every assignment (for the model
   tree), the `view.set_*` calls, and the `var()` numbers with their positions in the text.
2. For each displayed shape the application builds a render job: the region, the resolution, the quality,
   the colouring field.
3. The viewport compares the new shapes with the ones it already has by **structural identity** of their
   expressions. Unchanged shapes keep their mesh; new ones are meshed on worker threads (progress is shown),
   a body with a resolution of its own (`custom_resolution`) in its own cube at that resolution.
4. Hover, drag and probing evaluate the **field itself** (not a mesh) at the point under the cursor; a drag
   is turned into changes of `var()` numbers by the solver and written back into the text.

## Selecting a surface

`select_surface()` (`stdlib/selection.py`) calls the kernel's `libfive_surface_select` (`selectSurfacePatch` in
`kernel/src/fields/surface_select.cpp`), which works from the field alone — its value and gradient, through its own
`Field` evaluator and `projectToSurface`; no mesh of the shape is made. The seed is carried
onto the surface (Newton along the gradient); from every sample the walk takes eight steps of one spacing in the tangent
plane, each carried back onto the surface, and keeps a step whose normal passes the angle test of mode `flat` (against the
seed's normal) or `smooth` (against the sample about 10 mm back along the walk, the angle allowed per 10 mm), that stays inside the radius, that was not carried more than
0.6 of a step to reach the surface (it is past an edge or a gap otherwise), and that is not within 0.7 of a step of a
sample already taken (a hash of cubes). A step is a front: all the candidates of a front are carried onto the surface in one
batch, on all the threads. The samples are the patch; `libfive_points_distance` makes them a field, the distance to the
nearest, with a kd-tree (`PointCloudOracle`: a point and a box of space are answered by the few samples near them, the
interval bound is the box-to-nearest-sample distance). The selection is that field less half of the thinnest layer the samples cover (no setting); `.patch` is it
less the cover of the samples (0.85 of a step), `.whole` is `|f|`, the shape's own value, and `patch - whole` is below 0
where the nearest point of the surface is in the patch, which is how a ribbing gets sides that run straight along the
normal.

## The render cache

The cache is **on by default**: a shape the script does not mention keeps its finished mesh when meshing took 0.4 s or more
(`Shape::m_cache_on` starts true; `m_cache_forced` is set by an explicit `render_cache(x)`, which keeps it however
quick). `render_cache(shape, False)` (`stdlib/render_cache.py`) puts the attribute `_render_cache = False` on a copy of the
shape, the opt-out; the interpreter (`recordShape`) hands it to `Shape::setRenderCache`. A shape with the cache on keeps its finished mesh
(`Shape::writeRenderCache`, `<cache dir>/render-cache/<sha1 of the key>.fdmesh`: header, box, the key itself, float
vertices, triangles and the colour values) and `Shape::renderMesh` looks the key up before it meshes, at the start of a
render and again when the key changes; a hit is the finished mesh whatever level asked for it. The key is
`libfive::treePersistentKey` of the tree (a free variable counts by its value in a snapshot of what the evaluators
hold, an oracle by `OracleClause::persistentKey()`, a hash of its data — an oracle with none
makes the shape un-keepable and the row's button amber) plus the colour field, the region, the resolution, the quality and the algorithm, and
`kRenderCacheVersion` (bumped when the mesher's output changes — not on every build). The tree's key is made of the tree
as the script built it (`Shape::built_tree`), not of the optimized one: the optimizer's output differs from run to
run in the order of operands. A mesh an oracle holds is keyed by the surface, not by the order the mesher wrote it
in (`meshContentKey`: each triangle from its smallest corner, the triangles sorted). `render_cache_key()` shows the key. When anything about the math
changes the key is another one: a miss, the usual progressive render, and the new mesh is kept. The folder is
limited to 4 GB (`FIELDES_RENDER_CACHE_MB`), oldest files first; `Settings → Clear the caches` empties it (and the field cache).
The model tree's cache button writes and deletes the opt-out line `x = render_cache(x, False)` under the shape's definition
(under its `handles()` and `gizmo()` calls) like every other button of the tree (`ScenePanel::toggleCache`; the script
parser records the line as `cache_off`, an explicit `render_cache(x)` as `cache`).

**Selecting several models.** The tree selects whole rows (`ExtendedSelection`: the view does Ctrl and Shift itself; an event
filter on its viewport notes the modifiers of a click for `onItemClicked`, which then leaves the editor and the camera alone).
`ScenePanel` keeps the order the rows were selected in (`m_selectOrder`, kept across `rebuild()`, which restores every selected
row): the first selected model is what a *difference* subtracts from. `selectedModels()` turns the rows into models (a variable
or an expression displayed on its own, with the text that names it and the line after which a statement using it goes) and
`operandsFor(line)` says what a menu works on: the selected models when the one right-clicked is among two or more, else that
one; `createFromMenu` writes `union(a, b, c)`, `difference(a, b, c)` or `intersection(a, b, c)` (the library's variadic functions;
`other` is the list joined by commas) under the model defined last, and `combines(name)` asks the catalogue which operations
combine. In the viewport a Ctrl+click emits `shapeToggled`; a left press that pulls nothing starts a mouse state (`DRAG_RECT`; a click that does not move is a selection click, as before, a drag with Ctrl held adds) drawn by `paintOverlay` as a
thin outlined rectangle (Shift+left and the middle button start `DRAG_ROT`, the turntable), and on release `View::linesInside` projects every vertex of every displayed mesh with the camera and
keeps the shapes whose vertices all lie inside (`shapesRectSelected`). `View::mousePressEvent` takes the keyboard for the viewport
and the window gives it back to the viewport after every selection; `Editor::showScriptTab` switches tabs without taking the
keyboard and `Editor::onDragEnd` returns it to the script only if the script had it, so a click on a model never types the next key
into the code.

**The keys on a selection** (`ScenePanel::toggleSelected*`): each reads the state of every selected model and sets the target
`!all_on`, so a mixed selection first goes to *on* (`toggleSelectedVisible` through `visibilityEdit`, `toggleSelectedLock`
through `applyLock`, `toggleSelectedCache` through `applyCache`, `toggleSelectedEdit` through `applyModes`: the stored mode of
each model, gizmo or handles, which with several selected the tree's buttons show and the viewport does not use).
**The multi-select state** (two or more models selected) is not a mode: `View::mousePressEvent` starts no surface drag, and
`View::groupHandles` finds the shared gizmo -- all the selected shapes that have move numbers (`Shape::hasMoveVars`, in any mode)
-- at the middle of their pivots. `ScenePanel::prepareMultiSelect` (after the selection has settled, `m_prepareTimer`) writes
`x = gizmo(x, ..., mode=<its mode>)` for a selected model that has no numbers to move it by, never twice (the scene may be a run
behind the text: `m_editPending`, and a check of the text); `stripLocked` deselects the locked models of a selection of
several (`warnLockedMultiSelect`: the warning with a *do not show again* box in QSettings `hidden-messages/`, silent in
automation and after a run), `updateMultiNote` says what the state is under the tree. The shared gizmo's arrows and the centre dot (grip kind 3, also on every single gizmo) are `HandleGrip`s with `group` set,
and a drag changes the move number of every member at once (`handle_vars`: the id, the axis and the value when the drag began; the
dot adds the displacement of the cursor's ray on the plane through the pivot that faces the camera). A plain click on empty space
calls `ScenePanel::clearSelection`. A primitive made from the menu gets its calls once it exists (`m_selectNew`, `applyModes(...,
quiet)` from `setScene`).

**Lock.** `lock(x)` (in `stdlib/handles.py`) returns a copy of `x` with `_locked = True`; the interpreter reads it into
`Shape::setLocked`, which `hasGizmo()` (the gizmo) and `nativeDragOk()` (dragging a surface) respect. It is a call of its own,
recorded by the scene parser as `locked`, so toggling the way of editing (`gizmo()`'s mode, `gizmo` or `handles`) and the lock
never write each other's calls. `ScenePanel::applyModes` and `applyLock` build one edit for all the selected models.

The right-click in the viewport opens a menu (`View::showSurfaceMenu` on a model: Primitives, Parametric shapes, Operations (`View::fillOperationsMenu`), the quick operations, and Select Surface, which opens
`View::showSelectMenu`; `View::showEmptyMenu` on empty space: Primitives -- the basic 3D shape / 2D shape / 1D shape / point / surface / field, `menu_catalog.BASIC` --, Parametric shapes (the rest of the shapes) and Operations). Select emits `surfaceSelectRequested`;
`ScenePanel::addSurfaceSelection` writes the call into the script as an edit, so the selection is code like everything else (and selects the new model).
A `SurfaceSelection` displays itself through `_display()`: the part it was picked on, coloured by `patch - whole`
(zero or less where the vertex's nearest surface point is in the patch), with `_color_cutoff = 0`; the viewport gives `Shape` a
per-vertex `patch_value` and its fragment shader discards what is above zero, so only the patch is drawn, a hair towards the eye. The
other entries emit `createRequested`: `ScenePanel::createFromMenu` asks the interpreter for the call (`menu_call` in
`app_support.py`, from `fieldes/menu_catalog.py`, the one list of what the menus offer: the primitives with their placement
templates, the operations with the model passed in), writes `name = call` and a line showing it, and selects the new model once
the script has run. A primitive's place is the point of the ray under the cursor closest to the origin (`View::placeOnRay`),
its size about a hundred pixels (`View::scaleAt`). The `I` key (`ScenePanel::toggleIsolation`) hides all other models and shows
the selected one with the same edits as the tree's eyes, and remembers what was shown.
## The field cache

`python/fieldes/field_cache.py`, called by the runner (`_continue`) for every statement `name = <expression>` that is not a
call of a file reader (`import_*`, `load*`, `read*`, `open`, `save*`, `write*`, `export*`, `input`, `var`, `gizmo`, `handles`,
`render_cache`, `progress`). `lookup` makes the key — sha1 of the statement text, the content key of every name it reads
(`content_cache.value_key` / `shape_key`; a function or module without content makes the statement uncacheable), the
current `var()` numbers and the code identity (the kernel library's size and time, the library's Python files' sizes and
times) — and returns the kept `(Shape, printed text)`; `store` keeps a statement that took 0.25 s or more. The memory layer
holds the Shape itself; the disk layer holds `<key>.fdtree` (`libfive_tree_save`) and `<key>.fdfield` (JSON: the plain
Python attributes of the Shape and the text it printed) and is written only when `libfive_tree_can_save` says every oracle
in the tree installs a serializer (`OracleClause::install<T>(name)`; `libfive_tree_save` refuses an unsavable tree instead of
writing a file that cannot be read). No oracle installs a serializer today (the lattice's beams did, and went with the lattices), so a tree with an oracle in it -- a mesh's distance, a data field -- is not written to disk.
A new oracle type gets persistence by installing its serializer (`REGISTER_ORACLE_CLAUSE`) — nothing else changes. The folder is `field-cache/` beside
the render cache (`FIELDES_FIELD_CACHE_DIR`), 3 GB, oldest first.

## FielDes apps

An app is a script whose inputs are declared with `app.number(...)`, `app.file(...)`, ... (`python/fieldes/app.py`). The form is read from the
**text** of the script (`app_package.inputs_of`: every call `app.<kind>(...)` found in the syntax tree, its arguments plain values), so it exists before
the script has run; at run time the same functions return the value the person chose (`app.begin(values)` is what the host calls first) or, in the editor,
their defaults.

- **Bundling** (`app_package.build`): a zip with `manifest.json` (title, inputs, assets, blocks, files), `app.py`, `blocks/` (the custom blocks the script *calls*, and the ones those call:
  `blocks.info()` and the names of the calls in the syntax tree), and `files/` (the files named in `app.asset(...)`, the relative string literals that name a file next to the script,
  and the modules next to the script that it imports). It is unpacked once per version of the file (the folder name is a hash of its content) into the user's cache,
  `FIELDES_APPS_DIR` overrides it; the app runs with `files/` as its working folder and `blocks/` as its blocks folder.
- **The window** (`AppWindow`) is a process of its own: `Interpreter` is a singleton of the process (`g_interpreter`), so a preview from the editor is `FielDes <temp>.fieldesapp`, which watches
  its file and is read again when it is replaced. It asks Python through `Interpreter::callSupport` (`app_support.app_open / app_check / app_outputs / app_end`) and runs the script with
  `Interpreter::eval` like the editor does (`noteRequest()` first); Stop is `Interpreter::terminate()`. The progress bar reads `libfive::run_progress::current()`.
  `field_cache.py` never caches a statement that calls `app.` (its value is what a person chose).
- **The command line** (`app_package.main`): `execute()` runs the statements one after another with `var(x)` = `x`, as `scripts/run_example.py` does. `--watch` polls the modification times of the files.
- **File type**: `FileAssociation::registerForUser` (Windows: `HKCU\Software\Classes\.fieldesapp`, `FielDes.App`, the open command; Linux: `~/.local/share/mime/packages/application-x-fieldesapp.xml` and a desktop
  entry, `xdg-mime default`); the Windows installer (`installer/Setup.cs`), the Linux installer and the `.deb` do the same for their copy.
- **Testing**: `FIELDES_AUTOMATION` works in the app window too, with `appset <key> <value>`, `apprun`, `appstop`, `appwatch on|off`, `appwait <seconds>` and `appdump <file>`; the editor has
  `exportappto <file>` and `previewapp`.

## Files FielDes writes

| File | Where | Holds |
|---|---|---|
| `field-cache/<key>.fdtree`, `.fdfield` | FielDes's cache folder (beside the render cache) | the field cache; safe to delete (Settings → Clear the caches) |
| autosave | the script's own file, every 5 s once it has a name | your script |
| settings | the usual per-user location (`QSettings`: `FielDes`) | window, splitter, recent files, shortcuts, and per app (`apps/<id>/...`) the values last chosen |
| `apps/<name>-<hash>/` | the user's cache folder (`%LOCALAPPDATA%\FielDes\FielDes\apps`, `~/.cache/FielDes/apps`) | an unpacked `.fieldesapp`; safe to delete |

Nothing else is written outside the folders you choose (meshes exported by the script, STLs).

## Environment variables

| | |
|---|---|
| `FIELDES_DIR` | folder holding `fieldes.dll` (for the Python library without the application) |
| `FIELDES_AUTOMATION` | path of a command file: run a scripted GUI session (developer facility, `automation.hpp`) |
| `FIELDES_TIMING` | print timing lines to stderr |
| `FIELDES_APPS_DIR` | folder the apps are unpacked into (default: the user's cache) |
| `FIELDES_FIELD_CACHE_DIR` | folder of the field cache (default: `field-cache` beside the render cache) |
| `FIELDES_SCENE_CACHE_DIR` | folder of the kept model trees (default: `scene-cache` beside the render cache) |
| `FIELDES_SHAPE_LOG`, `FIELDES_TREE_LOG` | files the tests read: per run, how many viewport shapes were kept / new (`View::setShapes`); and the model tree's rebuild phases, the edits it followed and their times (developer) |
| `FIELDES_NO_EXACT_OFFSETS` | thicken, shell and offset an imported part with its own field instead of its exact distance |

## Origins and licences

FielDes stands on **libfive** (Matt Keeter, [github.com/libfive/libfive](https://github.com/libfive/libfive)).
From libfive come: the expression tree and evaluators, the dual-contouring/simplex mesher, the Python
bindings' shape and the GUI ("Studio") from which `app/` derives. Everything FielDes adds — mesh
import, fields, curves and profiles, symmetries, the model tree, the section card, handles, the new theme —
is in the same files and folders under
the same licences: `kernel/` and `python/` are MPL-2.0; `app/` is GPL-2.0-or-later. See
[NOTICE](../NOTICE.md) for third-party components.
