# Making game assets: terrain, levels, props, kits

FielDev models with **fields**: a shape is a number at every point of space, negative inside. For game assets that has consequences nothing else gives you:

* **No grid, no stitching.** A terrain is one field. A chunk cut from it meets the next chunk exactly, because both are cut from the same numbers.
* **Walls are what is left round empty space.** You say where the rooms and corridors are; the walls have the same thickness everywhere, two rooms that touch share a wall, and a corridor that runs into a room opens into it.
* **Everything blends.** A road keeps its width over any hill, a river bank slopes into the ground, a hill joins the plain. They are sums of fields: they cannot leave a crack.
* **Materials are fields too.** Grass where the ground is flat, rock where it is steep, snow high up, bark below the crown: a material is *where* a field is negative, and it goes to the exported file.
* **Solids, not surfaces.** Caves, arches and overhangs are boolean cuts of the same body. A heightmap cannot have them.

All of these live in the library (`from fieldev import *`) and work like any other model: they are shown, moved, cut and exported.

**Units.** These helpers are written for a model in **metres**: one number is one metre (a door is 1.2 wide, a room 12 long). Set the view's bounds and resolution to match: `view.set_bounds([-60, -60, -20], [60, 60, 30])`, `view.set_resolution(1)` (samples per number). An export is told so with `export_mesh(model, "wall.glb", model_unit="m")`: a 4-metre wall is then 4 metres in the glTF (`model_unit` is "mm" by default; "cm" and "in" are possible too).

## Where each is in the right-click menu

Everything on this page is in the right-click menu; an entry writes the call into the script, with every argument written at a value that shows something, to be edited there.

| What | Where | Writes |
|---|---|---|
| `terrain`, `water`, `room`, `corridor`, `doorway`, `window_opening`, `pillar`, `staircase`, `wall_segment` | *Parametric shapes ▸ Game*, on empty space or on a model | the shape at the place of the click (a room and a corridor are `build_level(room(...))` and `build_level(corridor(...))`, a body each) |
| `rock`, `tree`, `crate`, `barrel` | *Parametric shapes ▸ Game* | the prop, `placed` at the click |
| `kit`, `floor_tile`, `ceiling_tile`, `wall_piece`, `corner_piece`, `pillar_piece`, `stairs_piece` | *Parametric shapes ▸ Game* | the whole kit built from a plan (`edges`, `levels`, `ceiling` and `stairs` are written, for you to fill), or one piece of it |
| `kit_check` | *Parametric shapes ▸ Game* | the check of a kit: whether its pieces meet where they stand side by side; the answer is printed below the editor |
| the edits of a ground: `terrain_raised`, `terrain_flattened`, `terrain_road`, `terrain_river`, `terrain_river_water`, `terrain_cave`, `terrain_add`, `terrain_cut`, `terrain_textured`, `terrain_steep_places`, `terrain_chunk`, `terrain_chunks` (all the squares, a list of bodies), `terrain_height_field` (the height as a field of its own) | right-click a terrain, *Operations ▸ Terrain* | `terrain_raised(ground, center=..., radius=..., ...)`: the function form of `ground.raised(...)`, and so on; the ground stays a terrain, so the edits chain. `terrain_add` and `terrain_cut` take a second model, selected with the ground |
| the numbers of a ground: `terrain_walkable_fraction`, `terrain_height_at`, `terrain_slope_at` | *Operations ▸ Terrain* | the number, which is printed below the editor too |
| `placed`, `merge`, `scatter_prop` | *Operations ▸ Props* | `placed(prop, ...)`; `merge([a, b, ...])` of the models selected; `scatter_prop([props], ground, ...)`: select the prop (or several, for variants) and the terrain, in any order |
| `join_levels` | *Operations ▸ Level* | `join_levels([room, corridor, ...])`: the rooms and corridors selected made one level, so that the wall between them is open where a corridor ends in a room. A doorway or a window is taken out of a wall with *Combining ▸ difference*; a pillar or a staircase is added with *Combining ▸ union* |
| `covered`, `with_materials` | *Operations ▸ Materials* | snow, moss or dust as geometry; a material for the model |
| materials by drag and drop | *View ▸ Materials* | see below |

A terrain edit is offered for a terrain only (in the menu of any other model the whole *Terrain* group is left out): a ground that was given its colours (`textured`, `steep_places`) is a plain body, so make the edits first and dress it last. Not in the menu under a name of their own are `.material_layers()` (a list of materials: `terrain_textured` and `terrain_steep_places` take its colours as arguments and dress the ground with them) and a kit's `place`, `seam` and `pieces` (`place` is *Moving ▸ move* and *rotate_z* on a piece, `seam` is what `kit_check` runs, `pieces` are the six piece entries of *Game*).

## Materials: drag and drop

`View > Materials` opens the card of materials: a swatch for each preset of the library (`material_presets()`: gold, stone, wood, glass ...), drawn as a ball in its colour, shine and roughness.

* **Drag a swatch onto a model** in the viewport -- or onto its row in the model tree -- and let go: the model gets that material. A line is written under the model's definition,

      rock = with_materials(rock, material_preset("stone"))

  the same way a gizmo or a lock takes a model again, so there is still one model, shown once.
* **Drop another one** on the same model: the material in that line is replaced, not nested.
* **Click a swatch** to give the material to every model that is selected.
* Dropping on a point's dot does nothing; dropping on empty space does nothing.  The tree shows the model twice afterwards -- its first statement dimmed, and the line that takes it again --, as it does for any variable that is made again.

The materials of a model shown with `with_materials` are exported with it (`export_mesh` writes them into .glb, .gltf, .obj + .mtl). A material of your own is `material("name", color="#rrggbb", roughness=..., where=field)`; a `where` makes it a layer over a place.

## Terrain

    ground = terrain(size=(240, 240), height=14, scale=60, seed=3)        # hills, from noise
    ground = ground.raised((30, -20), radius=28, height=16)                # a hill there
    ground = ground.flattened((-50, 40), radius=14)                        # a place to build on
    ground = ground.road([(-110, -80), (-40, -20), (30, 10), (110, 60)], width=6)
    ground = ground.river([(-100, 100), (0, 20), (90, -90)], width=8, depth=3)
    ground = ground.cave([(60, -60, 4), (80, -30, 6), (100, 0, 8)], radius=5)
    shown = ground.textured(snow_line=26, beach=1.5)

| | |
|---|---|
| `terrain(size, height, scale, seed, base, center, roughness, ridges, plains, level)` | A solid slab whose top is hills of noise. `ridges` (0 to 1) makes mountains, `plains` fills the valleys. |
| `.raised(center, radius, height, falloff)` | A hill (a pit when `height` is negative). Falloff `'smooth'`, `'dome'` or `'cone'`. |
| `.flattened(center, radius, level, blend)` | A flat place, joined to the ground over `blend`. |
| `.road(path, width, blend, depth, smooth)` | A flat road along the path; the places are `(x, y)` or `(x, y, z)`, a place with no z is as high as the ground is there. |
| `.river(path, width, depth, blend, smooth)` | A channel with sloping banks. |
| `.river_water(freeboard)` | The water of the rivers made so far, as a body of its own in the water material: it fills each channel from the bed up to `freeboard` below the ground the river was cut into, following the river downhill. Where a river runs across a steep slope the water spills to the low side. |
| `.steep_places(max_angle)`, `.walkable_fraction(max_angle, samples)` | The ground in its materials with red where it is steeper than `max_angle` degrees (a check to look at while modelling), and the share of the ground that is not. |
| `.cave(path, radius, blend)`, `.add(shape, blend)`, `.cut(shape, blend)` | 3D changes of the solid. |
| `.height_at(x, y)`, `.slope_at(x, y)` | Numbers, for standing things on the ground. |
| `.chunk(ix, iy, size)`, `.chunks(size)` | A square of the ground, or all of them, cut from its one field: squares that touch meet exactly. |
| `.textured(...)`, `.material_layers(...)` | Grass, rock (steeper than `rock_angle`, and the walls of caves), snow (above `snow_line`), sand (below `beach`), and a road and a river bed wherever `.road` and `.river` were made. |
| `water(size, level, depth)` | A slab of water. |

Every method returns a new terrain; the old one is untouched. Rivers and roads go over each other in the order you call them.

## Levels

    hall = room((0, 0, 0), (12, 8, 3.5))
    cell = room((16, 1, 0), (22, 7, 3.5))
    link = corridor([(10, 4, 0), (19, 4, 0)], width=2.4, height=2.8)          # from inside the hall to inside the cell
    gate = doorway((-0.2, 4, 0), width=1.6, height=2.4, axis="x", arch=True)
    look = window_opening((6, 8.2, 0), width=1.4, height=1.2, sill=1.0, axis="y")
    keep = build_level([hall, cell, link], openings=[gate, look],
                       solids=[staircase((2, 1, 0), (2, 6, 1.5), width=1.6, steps=8), pillar((9, 2), radius=0.35, height=3.5, capital=0.3)])

`room` and `corridor` are the **empty** space; walls (`wall`, 0.4 by default), floor and ceiling are what `build_level` leaves round them. A corridor's places have a z (the height of its floor): two different heights make a ramp. A corridor ends where its last place is, so put the first and the last inside the rooms it joins. `doorway` and `window_opening` are cutters (`depth` must reach through the wall); `staircase`, `pillar` and `wall_segment` are solids.

## Props

    stone = rock(size=1.4, seed=7)               # flat underneath, standing on z = 0
    pine = tree(height=9, kind="pine", seed=2)  # "round", "pine", "bush"
    row = merge([placed(stone, (0, 0, 0)), placed(pine, (6, 0, 0), turn=30, scale=1.2), placed(crate(1.0), (10, 0, 0)), placed(barrel(), (12, 0, 0))])
    forest = scatter(lambda s: tree(height=8, seed=s), 120, ground=ground, min_distance=5, max_slope=28, variants=3)

A prop is a body shown in its materials (bark and leaves are two). `placed` scales, turns (degrees about z) and moves it with its materials; `merge` joins several into one body. `scatter` stands props on the ground where it is flat enough (`max_slope`, degrees) and a rule allows (`where`: a field that is negative where props may stand, or a function of x, y, z), at least `min_distance` apart.
## Snow, moss and dust as geometry

    snowy = covered(rock(1.4, seed=7), depth=0.12, angle=55)                        # snow on every surface that faces up, thinning out where it would slide off
    mossy = covered(crate(1.0), depth=0.04, angle=70, name="moss", color="#4f7a34")

`covered` adds a layer of `depth` to every surface of a model that faces `direction` (up by default) to within `angle` degrees -- thickest where it faces straight at it, thinning to nothing at the angle -- and gives it a material of its own (`name`, `color`) that lies only on the cover, so an exported file has it as a layer. It is arithmetic on the field of the model, which is differenced on both sides along each axis to find which way its surface faces: it works on anything with a field (a prop, a kit piece, a level), the cover is geometry that an engine sees in the silhouette, and a `covered` prop can still be `placed`, `merge`d and `scatter`ed. The right-click menu of a model has it too, under *Materials*. The field is evaluated seven times as often, so a model that is slow to mesh is slower with a cover.

## Modular kits

    walls = kit(cell=(4, 4, 3), wall=0.3, floor=0.25)
    walls.check()                                   # [] when every piece meets its neighbours
    house = walls.build(["#####",
                         "#####",
                         "##  #"], edges={(2, 2, 2): "door", (1, 0, 0): "window"})

The cell of a piece has its south-west floor corner at the origin. `wall_piece` stands on the south edge; `turn` quarter turns (counter-clockwise from above) put it on the east, north, west edge. A plan is a list of strings, the first the northmost; a cell is inside unless it is a space. Walls stand on every edge with outside beyond it; `edges` changes an edge: `{(i, j, side): kind}` with `side` 0 south, 1 east, 2 north, 3 west and `kind` "door", "arch", "window", "wall" or `None`. `stairs={(i, j, k): turn}` puts a stairs piece in the cell (i, j) of level k, rising towards north, west, south or east for `turn` 0, 1, 2, 3, and leaves out the floor above it; it leads up into the next cell in that direction, which has to be inside the plan, and `levels` has to be at least k + 2.

Every piece is cut to its cell, so it ends exactly on the cell's faces. `seam(a, b, axis)` asks both fields, on a grid just inside the face they share, what is solid, and `check()` does it for the whole kit. Walls that run north-south give the corner squares to the ones that run east-west, and a post (`pillar_piece`) closes a corner where two walls would only touch at a point, so no volume is made twice.

## Where the fields are, and where a mesh is made

Everything in this list is built as fields (arithmetic on x, y and z) and is meshed only to be shown, or to be written to a file:

| | The field |
|---|---|
| Terrain | A height `h(x, y)` and the solid `z < h`. Hills, roads, rivers and flat places are sums, blends and `smoothstep`s of fields of x and y; a cave or a pit is a boolean on the solid. |
| Roads and rivers | The distance from a path, as a field, blended into the height. The water of a river is the body between its bed and a level that follows the path. |
| Materials | Every layer is a `where` field: the slope (from the gradient of the height), the height, the distance to a path or to a body. `steep_places` is one more layer. |
| `covered` | The field of the model, less `depth` times a weight made from the field's own gradient (which way the surface faces). |
| Levels | The space inside is a field; the walls are that field grown by the wall thickness, and the space is subtracted again. |
| Kit pieces | Each piece is a field clipped to its cell; `seam` asks two fields whether they are solid on the face they share. |
| Props | Noise, ellipsoids and blended unions; the rules of `scatter` (`where`, the slope) are fields. |
| Chunks | The one field of the ground, cut by a box. |

A mesh is made by `export_mesh`, and by the viewport to show a model: nothing of the field is left in an exported file. Nothing else is made here -- what an engine does with a model (levels of detail, collision, streaming, instances) is the engine's job, not this program's.

## What is not here yet

* The kit's seam check covers plain walls, floors and ceilings, not stairs.
* The right-click menus were dumped and every entry's text was run in the virtual display; the menu of the model-tree row of a terrain has the *Terrain* group and the menu of the row of a box does not (`treecontext`, `popup dump`). Nothing was seen in a real window.
* Anything seen in a real window or on Windows: all of this was run only in a virtual display on a Linux machine.
