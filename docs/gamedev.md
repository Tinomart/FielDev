# Making game assets: terrain, levels, props, kits

FielDev models with **fields**: a shape is a number at every point of space, negative inside. For game assets that has consequences nothing else gives you:

* **No grid, no stitching.** A terrain is one field. A chunk cut from it meets the next chunk exactly, because both are cut from the same numbers.
* **Walls are what is left round empty space.** You say where the rooms and corridors are; the walls have the same thickness everywhere, two rooms that touch share a wall, and a corridor that runs into a room opens into it.
* **Everything blends.** A road keeps its width over any hill, a river bank slopes into the ground, a hill joins the plain. They are sums of fields: they cannot leave a crack.
* **Materials are fields too.** Grass where the ground is flat, rock where it is steep, snow high up, bark below the crown: a material is *where* a field is negative, and it goes to the exported file.
* **Solids, not surfaces.** Caves, arches and overhangs are boolean cuts of the same body. A heightmap cannot have them.

All of these live in the library (`from fieldev import *`) and work like any other model: they are shown, moved, cut and exported.

**Units.** These helpers are written for a model in **metres**: one number is one metre (a door is 1.2 wide, a room 12 long). Set the view's bounds and resolution to match: `view.set_bounds([-60, -60, -20], [60, 60, 30])`, `view.set_resolution(1)` (samples per number). The helpers that write game files (`export_terrain_chunks`, `export_scatter`, `Kit.export`) pass `model_unit="m"` to `export_mesh`, so a 4-metre wall is 4 metres in the glTF; give `model_unit="mm"` (or "cm") for another unit.

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
| `.chunk(ix, iy, size)`, `.chunks(size)` | A square of the world, or all of them. |
| `.textured(...)`, `.material_layers(...)` | Grass, rock (steeper than `rock_angle`, and the walls of caves), snow (above `snow_line`), sand (below `beach`), and a road and a river bed wherever `.road` and `.river` were made. |
| `water(size, level, depth)` | A slab of water. |
| `export_terrain_chunks(ground, folder, size, lods=None)` | One file per square, with materials. `lods=[4000, 1000, 250]` writes every square at three budgets of triangles (`name_ix_iy_lod0.glb` ...): the field is meshed again, coarser. |

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
    export_scatter(forest, "out/forest", name="tree")

A prop is a body shown in its materials (bark and leaves are two). `placed` scales, turns (degrees about z) and moves it with its materials; `merge` joins several into one body. `scatter` stands props on the ground where it is flat enough (`max_slope`, degrees) and a rule allows (`where`: a field that is negative where props may stand, or a function of x, y, z), at least `min_distance` apart. It remembers where each stands, so `export_scatter` writes the few meshes **once** and a `name_instances.json` (variant, position, turn, scale for each): what an engine wants for a forest.

## Modular kits

    walls = kit(cell=(4, 4, 3), wall=0.3, floor=0.25)
    walls.check()                                   # [] when every piece meets its neighbours
    house = walls.build(["#####",
                         "#####",
                         "##  #"], edges={(2, 2, 2): "door", (1, 0, 0): "window"})
    walls.export(house, "out/kit")                  # each piece once, and kit.json: which piece stands in which cell, turned how

The cell of a piece has its south-west floor corner at the origin. `wall_piece` stands on the south edge; `turn` quarter turns (counter-clockwise from above) put it on the east, north, west edge. A plan is a list of strings, the first the northmost; a cell is inside unless it is a space. Walls stand on every edge with outside beyond it; `edges` changes an edge: `{(i, j, side): kind}` with `side` 0 south, 1 east, 2 north, 3 west and `kind` "door", "arch", "window", "wall" or `None`.

Every piece is cut to its cell, so it ends exactly on the cell's faces. `seam(a, b, axis)` asks both fields, on a grid just inside the face they share, what is solid, and `check()` does it for the whole kit. Walls that run north-south give the corner squares to the ones that run east-west, and a post (`pillar_piece`) closes a corner where two walls would only touch at a point, so no volume is made twice.

## Collision meshes

    export_collision(rock, "out/rock.glb", triangles=300)                  # out/rock_collision.glb
    export_collision(rock, "out/rock.glb", triangles=300, naming="godot")  # out/rock-colonly.glb

A body that is a field has no low-poly version to model by hand: the field is meshed again with fewer triangles, and the rougher copy stays where the surface is. `naming` is the suffix an engine looks for (`"godot"`: `-colonly`, which its importer reads from the node name, so the node gets the same name); nothing here was tried in an engine. The same idea gives levels of detail: `export_lods(part, path, [8000, 2000, 500])`, and `lods=` of `export_terrain_chunks`.

## What is not here yet

* Pieces of a kit in the right-click menus beyond the first Game entries; the kit's seam check covers plain walls, floors and ceilings, not stairs.
* Level of detail by distance for terrain chunks (`export_mesh(..., max_triangles=...)` per chunk works).
* Anything seen in a real window or on Windows: all of this was run only in a virtual display on a Linux machine.
