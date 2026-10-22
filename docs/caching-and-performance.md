# Caching and performance

A FielDev script runs again after every edit, and a few of its operations are expensive: reading a big mesh
file, meshing a shape, building a field. The caches make the second run cheap **without changing any
result**: every cache is keyed by *exactly what the result was built from*, never by a name or a printed
approximation, and a hit returns the very thing a miss built. Nothing is ever sampled onto a grid to save time.

- [What is cached](#what-is-cached)
- [How keys work](#how-keys-work)
- [Controlling the caches](#controlling-the-caches)
- [The field cache](#the-field-cache)
- [The render cache](#the-render-cache)
- [Editing while it runs](#editing-while-it-runs)
- [The model tree](#the-model-tree)
- [Resolution and quality](#resolution-and-quality)
- [Long renders](#long-renders)
- [Making things faster](#making-things-faster)

## What is cached

| What | Kept | Key |
|---|---|---|
| **Any field a script builds** (`name = <expression>`: an offset, a thickness field — [the field cache](#the-field-cache)) | in memory, and on disk when every part of the field can be saved | the statement's text, the exact content of every name it reads, the `var()` numbers, the code that builds it |
| **Shapes already meshed in the viewport** | in memory, for the session | the shape's expression (structural identity) and its colouring |
| **The finished mesh of a shape you asked for** ([render cache](#the-render-cache)) | on disk, in FielDev's cache folder | the shape's expression with the numbers it is drawn with, its colours, the render region, resolution and quality |
| **The model tree of a script** ([the model tree](#the-model-tree)) | on disk, in FielDev's cache folder (`scene-cache`) | the md5 of the script's text, and the program and library that made the tree |
| **Mesh imports** | in memory | path, size, modification time, units |
| **`mass_properties` / `volume_of`** | in memory | the shape, bounds and resolution |
| **Field queries** (`curvature_field`, data fields) | in memory | they remember their answer at every point they were asked about — the same values, exactly |

## How keys work

A shape's **content key** is a 128-bit structural hash of its expression: every operation, every constant
bit-for-bit, every joint, and for the shapes that carry data (imported meshes, data fields)
the key of that data. Two shapes built separately from the same expression have the same key; constants
differing in the seventh digit, another imported file, another data field all differ. A free variable
matches only itself, so a shape that holds one is not mistaken for another.

That is why an edit late in the script does not repeat the work above it: the field above the edited line
has the same key as before.

**A mesh import** is kept by the file's path, size and modification time; `rev=` (the **⟳ Reimport** button)
makes the script read the file again.

## Controlling the caches

```python
cache_info()        # {name: (entries, hits, misses)}
clear_caches()      # forget everything held in memory (to measure, or to free it)
```

Memory caches are bounded (least recently used goes first).

Developers writing their own expensive construction can use the same machinery from
`fieldev.stdlib.content_cache`: `@content_cached('name', limit=8)` on a function of shapes and numbers,
`shape_key(shape)`, `value_key(v)`, `problem_key(kind, **parts)`.

## The field cache

Every statement of the form `name = <expression>` whose value is a field is remembered, **by what it was made of**: its
text, the exact content of every name it reads (a field by the structural hash of its expression, a number by its bits,
lists, text, the library's own functions), the numbers of the script's `var()`s and the code that builds it (the library
and its Python files). There is nothing to switch on and no function to wrap: an exact offset or a
thickness field is cached because it is a field, not because somebody wrote a cache for it. Run the same
statement with the same inputs and the field is not built again: in the same session the very same field is handed back,
and in a later session (after closing and opening FielDev) it is read from a file. What the statement printed is printed
again. A hit returns exactly what a run builds; nothing is sampled onto a grid.

What is not kept this way:

- a statement that calls something that reads or writes a file (`import_...`, `load...`, `read...`, `open`, `save...`,
  `write...`, `export...`) or `var()`, `handles()`, `gizmo()` — a file may have changed (imports are kept by the file's path, size and time);
- a statement that reads a function or module of your own (it has no content to compare);
- a statement that took less than a quarter of a second (a file would be slower than the run).

A field is written to disk when **every part of it can be saved** (`libfive_tree_can_save`): operations, bodies, any
expression of them. A field with a part that cannot be saved (a mesh's distance field, a data field) is kept in memory for the session and is computed again in
the next one — the cache never writes a file it could not read back. The files are in `field-cache` beside the render
cache (`FIELDEV_FIELD_CACHE_DIR` moves them); the folder holds at most 3 GB, oldest first out.
**Settings → Clear the caches** deletes them together with the kept meshes of the render cache.

## The render cache

Meshing is the slow part of showing a big shape, and the viewport's memory of it ends with the session. So **every
shape keeps its finished mesh on disk** (in FielDev's cache folder, never in your project) once it has taken a while to
mesh (a sphere is not worth a file), and is shown from there at once the next time it is rendered — when you open the
script again, or after you changed it and changed it back. It is **on** unless you turn it off: the model tree's
**cache button** on every shape (a stack of disks; a menu entry in the right-click menu too) writes the line
`part = render_cache(part, False)` under the shape's definition; click it again (or delete the line) to have it on
again. `part = render_cache(part)` says the default aloud and keeps the mesh however quickly it was made.

The mesh is looked up by what the shape *is*: its expression with the numbers it is drawn with (a dragged `var()`
is another shape), what colours it, the render region, resolution and quality, and the mesh files it uses (their size
and time). When **anything about the math changes** the key is another one: the shape is meshed again, shown as
usual, and the new mesh is kept. The button shows what happened — blue: on, green: the mesh on screen was read from
the cache, amber: this shape cannot be kept (hover for why).

`render_cache_key(shape)` shows the key a shape is kept by (the same text in every run for the same math, another one when
anything about the math changes, `None` when the shape cannot be kept).

A shape can be kept when everything it is made of can be recognised from one run to the next: operations, numbers,
`var()`s, imported meshes, field-driven sizes. A shape that holds an oracle with no key of its own cannot (the amber
button says so). The folder holds at
most 4 GB (`FIELDEV_RENDER_CACHE_MB` changes that), oldest files first out; **Settings → Clear the caches**
deletes all of it (and the field cache's files). The mesher's output changes now and then; the cache then starts anew by a version number
(`kRenderCacheVersion`), not on every build.

## Editing while it runs

The script runs again after every edit, and an edit usually has nothing to do with most of the shapes. Three things keep
the work that does not need doing from being done:

- **A shape that did not change is not meshed again.** Its numbers (`var(...)`) are told apart by the statement they are
  written in and their place in it -- not by how many `var()`s come before them in the script. A new line above a shape, a
  comment, a number changed in another statement, another variable added: the shapes stay as they are, and a render that is
  going on goes on. (What does restart a render is what the render is made of: the shape's expression, its colours, the
  region, the resolution, the quality.)
- **Only the last of a row of edits runs.** The edits of a quick series (typing, several clicks in the model tree) each
  ask for a run of the script as it was then; a run that a newer edit has replaced is not made, and the one that is running
  is told to stop. A script that takes a minute to run does not run six times for six clicks.
- **An edit that does not touch the statement that runs does not stop it.** Showing or hiding a model above a long
  statement that is going, or writing anything below it, is put into the run as it goes: the calculation carries on (it
  can be minutes), and what you unhid is drawn at once. Only an edit of what that statement is made of -- a number in it or in a
  statement it uses, a line added above it -- stops it, and then at once.
- **A part of the script that is stopped half-way shows its last whole result.** The viewport keeps what it had until a run
  is done; an error in the middle of typing does not empty it.

Two more things hold while a long render is going on:

- **A long render is never stopped by a change that has nothing to do with it, and it does not hold the others up.** A render that
  is expected to be long (the next level has more than about 150 000 vertices) runs at a lower priority: it still uses every core that
  nothing else wants, but a small shape that was changed meanwhile is meshed first -- a tiny sphere next to a gyroid that takes half
  a minute was ready in a third of a second -- and a part that is hidden needs no render at all, so it is gone at once.
## The model tree

The model tree is **read from the script's text**, so it is there at once, whatever the script is doing (see *The model tree* in
the interface chapter). What only a run can tell it -- the exact kind of what a statement made, how far it reaches -- is **kept**:
after every run that worked, it is written to `scene-cache` in the cache folder (`FIELDEV_SCENE_CACHE_DIR` moves it; the sixty
newest are kept), by the md5 of the script's text and of the program and library that made it. Opening the same text again lays
that on the rows **at once**, and they can be clicked while the script runs for the first time. A script that was changed since, or
another version of FielDev, has no kept facts: the rows show a guess from the function names until the statements have run.

**The buttons of a row act at once.** The eye, the lock and the render cache write their lines into the script, and the tree
changes in the same moment -- every row is on the line the edit gave it, the clicked model shows its new state -- without
waiting for the script to run. Several clicks in a row are all made, one after the other, from the tree as it is, and answered by
one run of the last text. The tree then reads the text again, a moment later, and that is the tree that stays: a click made in
that moment follows when it is there. The gizmo button changes its icon at once but its lines are the run's to say: a
second click on it waits for the run. A model that is selected is made ready to be dragged (`handles`, `gizmo` calls) once the
run is done, not while clicks are being followed.

Building the tree is fast: 400 models take about 60 ms (the rows are made apart from the view and put into it once).

## Resolution and quality

The viewport meshes the script's shapes over `view.set_bounds(...)` at `view.set_resolution(...)`
(samples per mm) and `view.set_quality(...)` (1–10, mesh accuracy). The mesher splits the region in
halves until a cell is no larger than `1 / resolution`, so **the cost changes in steps** of four to six
times the vertices at every halving: doubling a resolution that just misses a halving costs nothing extra
until it crosses one. `roi_resolution` picks resolutions that are whole numbers of halvings.

- **Every model is meshed at a resolution of its own**, scaled from `view.set_resolution`: that number is for a model as big as
  the region; a model that is smaller gets finer in proportion to the square root of how many times smaller it is (at most 2000
  samples across it, never below the number you set), so a large and a small part render at the same time without the small one
  being a jumble of triangles. Raise `view.set_resolution` and every model gets finer. The quick first picture is sized by the model
  too, not by the region. Models that have a resolution of their own (an imported part's, a render hint) keep it.
- Too coarse: thin walls and small features vanish (a 0.6 mm wall wants 3 samples per mm or
  more).
- Too fine for the region: minutes of meshing (and gigabytes). Cancel with `Esc` and lower it.
- For imports, prefer `roi_resolution(model)` — every part gets its own resolution.
- `view.set_quality(8)` is a good default; lower numbers are faster and rougher.
- **One body that needs more (or less) than the scene**: `custom_resolution(body, 3)` meshes that body at 3 samples per mm
  whatever `set_resolution` says, so a fine part does not make the whole scene fine. It is a **property row under the
  variable** in the model tree (the number is a field of the tree, the bin takes the line away) and an entry of the right-click menu. It is the
  body's wherever the body is: a body that reaches out of the scene's region (the box of a body is sometimes an estimate) is drawn at its
  own resolution inside the region -- nothing outside the region is drawn, as for every shape. The finest a body can be drawn is
  2000 samples along its longest side; a number above that is not an error: the body is drawn at the finest there is, and the
  row shows what is used (`8 → 7.63`, in amber, with the reason in its tooltip).
## Long renders

- The status bar and the thin progress bar show what is meshing; the output pane shows the statement
  (`3/12`) and the progress of an operation inside it.
- `Esc` cancels a slow render.
- **Breakpoints** (`F9`) let you look at a half-built model while something later is slow.

## Making things faster

1. **Import once, tune later.** A big mesh import is the slowest step. Keep the `import_model` line
   unchanged while you work on what comes after it.
2. **Render only what you need.** Hide what you are not working on (the eye in the model tree), set the
   region with `view.set_bounds` around the part you are looking at.
3. **Coarse first.** Lower `view.set_resolution` and the quality while composing, raise them for the final
   picture or STL.
4. **Put expensive, rarely changed operations early** in the script, where caches keep them.
5. **Use the exact operations sparingly**: `offset_exact`, `round_edges`, `fillet` read the distance from the
   shape's own field with a few Newton steps, each a handful of calls of it (nothing is meshed), so a drawing
   of one costs several times the shape's own. Use them on the finished shape, not inside a loop.
