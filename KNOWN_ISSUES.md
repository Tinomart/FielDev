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

- **The viewport shows the colour of a material, and nothing else of it.** `with_materials(model, [...])` shows each material's colour, as an engine shows it, with a key of their names; the roughness, metalness, glow,
  opacity, textures and everything else of a material are written when you export (`export_mesh`), and a colour that is a field is shown grey. Bake the textures and look at the `.glb` in a viewer or an engine for the rest. A model
  that is not given `with_materials` is drawn in neutral shading. The numbers of a material are linear, as glTF has them; a `"#3a6ea5"` is sRGB, as in a paint program, and is converted when the material is made, so it looks the same in
  the viewport and in an engine (the same colour typed as the numbers `(0.227, 0.431, 0.647)` is read as linear and looks lighter).
- **A reference image follows its handle when you let go, not while you drag.** Its handle is a point with a gizmo (the menu writes it); the picture is drawn from the numbers of the last run of the script, and the script runs again
  when the drag ends. Its `height`, `opacity` and `flip` are numbers in the script.
- **An armature is not literally `path_extrude` unless it is given a `profile`.** The default round armature is made of round cones along the curve (exact, and a dragged node moves it at once); `profile=` sweeps a 2D shape with `path_extrude`.
- **`uv_unwrap` is a pure-Python unwrap**: a mesh of tens of thousands of triangles takes tens of seconds to lay out (the conformal map of an island of more than 6000 triangles is replaced by a planar projection), and the
  packing is a few per cent looser than a dedicated packer's.
- **FielDev writes no animation and no morph targets**: it is a modelling program. A rigged glTF is the mesh in its bind pose with the skeleton and the skin weights.
