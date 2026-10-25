# Known issues

What you should know before you spend time on something. A problem that is not here: **Help ▸ Report a bug** opens a new issue with the version and your system filled in.
What a tool does and does not do (its scope, its accuracy, its cost) is in the guide, next to the tool: [docs/fields.md](docs/fields.md), [docs/interface.md](docs/interface.md);
the README has the design decisions (*Known limitations*).

## Platforms

- FielDev has **no release and no installer yet**: it is built from source with the scripts in `scripts/` (see [docs/building.md](docs/building.md)).
- **Windows** is the platform of the project it comes from. **Linux** builds with `scripts/build-linux.sh`; it has been built and looked at in a virtual display (Xvfb, software rendering) in a cloud container, where there is no
  physical screen: the window has not been looked at on a real display and a real graphics driver.
- There is **no macOS** build.

## Characters and textures

- **The round end of an armature does not follow a cross-section whose middle lies outside it.** The dome at a node that is a spline point is the cross-section shrinking toward the middle of its box, which keeps it inside
  round, convex and star-like sections (the default, a rectangle, a triangle, a hexagon, a plus: measured, nothing sticks out); a U or an L, whose box middle is in the notch, gets a dome that covers the notch (up to 3 mm out of a U
  20 mm wide). Give such a section a corner node (`point(..., smooth=False)`) for a flat end.
- **The viewport shows the colour of a material, and nothing else of it.** `with_materials(model, [...])` shows each material's colour, as an engine shows it, with a key of their names; the roughness, metalness, glow,
  opacity, textures and everything else of a material are written when you export (`export_mesh`), and a colour that is a field is shown grey. Bake the textures and look at the `.glb` in a viewer or an engine for the rest. A model
  that is not given `with_materials` is drawn in neutral shading. The numbers of a material are linear, as glTF has them; a `"#3a6ea5"` is sRGB, as in a paint program, and is converted when the material is made, so it looks the same in
  the viewport and in an engine (the same colour typed as the numbers `(0.227, 0.431, 0.647)` is read as linear and looks lighter).
- **A reference image follows its handle when you let go, not while you drag.** Its handle is a point with a gizmo (the menu writes it); the picture is drawn from the numbers of the last run of the script, and the script runs again
  when the drag ends. Its `height`, `opacity` and `flip` are numbers in the script.
- **A plain `path_extrude` has `sizes` but no circle in the viewport.** How thick a sweep is at a point is the number in `sizes` of the call (a var(): change it in the script). Only the nodes of an armature have the circle round them that is dragged and the Shift + wheel over the node that sets the same number. The scale of a point -- the gold ring of its gizmo -- is how strongly the curve leaves it, for both.
- **A feature model follows a dragged point when the script runs again, not during the drag.** Its surface is a mesh made of the points (every point a vertex, every loop an edge loop), so it changes when you let go of a point; an armature, which is a path extrude with a cross-section of its own, follows a dragged node at once.
- **A branch of an armature is drawn as a sweep that crosses its parent in the viewport; the blend is in the field.** `armature([a, b, [c, d], e])` joins the branch to the rest with a smooth union as wide as
  the branch is thick (what `character` and the export mesh), but the viewport draws every piece of an armature natively, ring by ring from the numbers of its nodes, and does not blend them: where a branch leaves its
  parent the two surfaces cross. A `character` of the armature, or the exported mesh, shows the blend.
- **`uv_unwrap` is a pure-Python unwrap**: a mesh of tens of thousands of triangles takes tens of seconds to lay out (the conformal map of an island of more than 6000 triangles is replaced by a planar projection), and the
  packing is a few per cent looser than a dedicated packer's.
- **FielDev writes no animation and no morph targets**: it is a modelling program. A rigged glTF is the mesh in its bind pose with the skeleton and the skin weights.

## Units

- **Lengths are called millimetres everywhere in the program, while the models of a game have the unit of their engine** (a metre in most). The scale bar, the resolution ("samples per mm"), the size of an imported model ("mm per unit") and the docs all say millimetres. A unit for the scene, and what an export does with it, is open.
