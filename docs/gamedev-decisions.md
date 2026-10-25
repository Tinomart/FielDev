# Game development in FielDev: what was decided, what was tried, what is open

Written overnight, while nobody could be asked. Every decision below was made by me, with the alternative that was not taken, so that it can be changed in one place. Nothing here has been seen in a real window or on Windows: the application ran in a virtual display on a Linux machine, with software rendering, and the pictures and logs of those runs are the only evidence.

## What exists

| | Where | Seen in the virtual display |
|---|---|---|
| Materials card, drag and drop of a material onto a model (viewport and model tree), click to give it to the selection | `View > Materials`; `app/src/materialspanel.cpp`, `view.cpp`, `scenetree.cpp` | yes: the card with 24 swatches; drops on shapes and on rows; a click on a swatch with a shape selected; a second drop replaces the material |
| A click on a node of an armature puts the armature mode back on | `app/src/view.cpp` | the log says so; the node-test pictures show no model (see below) |
| Closing the window while a heavy model meshes no longer waits for the whole render | `~Shape` | example 33 exited in 86 s where it was killed at 140 s |
| Terrain, levels, props, modular kits, their exports | `python/fieldev/stdlib/{terrain,level,props,kit,gameunits}.py`, `docs/gamedev.md` | the level by 16 point checks, the kit by its seam check, all of them by pictures of the four new examples |
| The unit of a model: `export_mesh(..., model_unit="m")` | `exporting.py` | a crate of size 1 is 1.0 in a glTF with it, 0.001 without |
| Game entries in the right-click menu | `menu_catalog.py` | the menu dump lists them under *Parametric shapes > Game* |
| Examples 42 to 45 | `examples/` | opened and drawn |

## Decisions

**1. The material of a model is a line in the script, `rock = with_materials(rock, material_preset("stone"))`.** The script stays the truth, a dropped material is undoable like every edit, a second drop edits that line. Not taken: a `material=` argument on every primitive (touches every primitive and every menu entry); a dropdown in the tree row (hides the material from the script); a new variable for each drop (what the *Materials* entry of the menu does: it leaves the original model shown under the new one, and the picker then finds the original, so a second drop would not replace). **Open:** the tree shows such a model twice, the first row dimmed. Gizmo, lock and handles statements are folded into their model's row; `with_materials` could be, but about ten places of the tree code list the statements that belong to a model (delete, copy, drag, move), and I did not touch them without being able to see the result. Your call.

**2. A click on a node of an armature, without moving it, puts the armature mode back on, going on from that node.** You said selecting a point of an armature "does not go back into armature mode, like it is supposed to anymore". The history of the code has no earlier place that did this (only the menu entries *New armature* and *Add nodes from here*, and the tour, start the mode), so this is my reading of it. A drag still moves the node; Shift and Ctrl clicks still select several; `Esc` or a right click ends the mode. The risk: selecting a node to look at it now puts you in a mode where the next click on empty space puts a node down. If that is wrong, the change is the one block in `View::mousePressEvent` and `mouseReleaseEvent` marked `m_armNodePress`.

**3. The helpers think in metres.** One number is one metre; the helpers that write files tell `export_mesh` so. Not taken: millimetres everywhere (what the library did: a 4-metre wall is 4 numbers and then 0.004 in a glTF); a project-wide unit setting (right, but bigger: it touches the viewport's scale bar, the bounds, the resolution). `export_mesh(..., model_unit=...)` is new and optional; every existing call is unchanged.

**4. Terrain is a solid slab under a height field, not a heightmap and not a free 3D field.** A road, a river, a flat place and a hill are things you do to a *height*, so the ground keeps its height field; caves and arches are things you do to the *solid*, so it is also a body that boolean cuts can change. Chunks are cut from the one field, so neighbours fit exactly. Slope for the rock material is read from the height field by differences over half a unit. Not done: erosion, terraces, texture splat maps, per-chunk level of detail with skirts, a river that carries water (only the bed is carved and coloured; `water(...)` is a flat slab).

**5. Levels are the space inside, not the walls.** `room` and `corridor` are empty space, `build_level` grows them by the wall thickness and subtracts the space again. Walls are of equal thickness by construction, rooms that touch share a wall, a corridor that ends inside a room opens into it. Not done: helpers for storeys, an L-shaped room (use two rooms that overlap), door frames, lights, a navigation mesh.

**6. A prop is a body shown with its materials, and it remembers its parts.** `placed`, `merge` and `scatter` use that to keep the materials with the body they belong to; a material that two props share becomes one layer. `scatter` also keeps the places (`_instances`) and the few variants (`_variants`), and `export_scatter` writes the variants once with a JSON list of places: how an engine wants a forest. Not taken: one big merged mesh as the only output.

**7. A kit is a grid of cells; its pieces end exactly on the cell's faces.** The cell's south-west floor corner is the origin; a wall stands on the south edge; `turn` quarter turns put it on the other edges. Walls that run east and west own the corner squares; those that run north and south are cut back by a wall thickness at an end where a perpendicular wall stands; a post closes a corner where two walls would only touch at a point. `check()` asks pairs of pieces what is solid on the face they share. Not done: stairs in the plan builder, an inner-corner piece of its own, diagonal walls, cells that are not square (only a half turn is allowed for them).

**8. The Game entries are under *Parametric shapes*, not under *Primitives*.** The *Primitives* menu is the list of the most basic shapes; a rock or a tree is not basic. A section of their own like *Characters* would need more application code.

## What I could not check

* **Anything on a real screen.** The software renderer in the virtual display shows the shapes; it says nothing about speed on a graphics card, or about how a drag feels. The card of materials is about 390 pixels high with all 24 swatches: on a small window it covers a lot of the viewport (it can be collapsed and dragged like the other cards).
* **The armature-mode pictures.** In those test runs the viewport shows no model (the nodes lie off the visible part): the evidence is the log, which says the mode went on, anchored at the node, after a click and not after a drag.
* **A real drag from a swatch.** The drop was tested with the events a drop makes (enter, move, drop) sent to the viewport and to the tree, and the click on a swatch with the real button; the Qt drag that starts from a swatch (`QDrag`) needs a mouse that a test cannot press here.
* **Heavy examples.** Examples 33, 38 and 40 (armature figures that check their own exports) do not finish their script within 100 seconds in the virtual display; the build from before the speed fix (6751b1d) is no faster (at 100 s example 40 is at step 26 of 79 there and 29 of 79 in the current build), so it is not something that changed.  The other 42 examples run to their end without a Python error (39 within 100 s, the rest within 40).
* **Windows.** The zip was rebuilt for the first commit of the night (flicker and the rest); a second rebuild, with the game-development work, is the last step of the night (see the last commits).
* **The library, beyond the examples.** 49 checks of the parts that no example runs -- `add`, `cut`, `chunks` (the squares hold their middle and meet exactly), a corridor ramp, stairs down, `wall_segment`, `merge` of plain bodies, the rules of `scatter` (a field and a function), a kit of two levels, the units of an export, `export_terrain_chunks`, `export_scatter` -- pass.  One failed at first because the test looked at the edge between two squares, and passes with the middle.
* **The speed of the bigger examples.** Example 45 opens in about 12 seconds to the first picture here; how long the finest mesh takes is not measured.

## What I would do next, in this order

1. Fold the material statement into its model's row in the tree (decision 1), so a model is one row.
2. A project unit (decision 3) and a polygon budget per prop and per chunk in the export, so a level can be checked against a number.
3. Level of detail for terrain chunks, and a river with water.
4. Stairs and storeys in the kit's plan builder; an inner-corner piece.
5. Scatter rules from fields in the interface: drag a field onto a scatter to say where props may stand.
