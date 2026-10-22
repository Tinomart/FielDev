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

- **The viewport shows no materials.** A material (its colour, a texture) is written when you export (`export_mesh`); the viewport draws every model in its own neutral shading. Bake the textures and look at the `.glb` in a viewer or an engine.
- **A reference image follows its handle when you let go, not while you drag.** Its handle is a point with a gizmo (the menu writes it); the picture is drawn from the numbers of the last run of the script, and the script runs again
  when the drag ends. Its `height`, `opacity` and `flip` are numbers in the script.
- **A limb is not literally `path_extrude` unless it is given a `profile`.** The default round limb is made of round cones along the curve (exact, and a dragged node moves it at once); `profile=` sweeps a 2D shape with `path_extrude`.
- **`uv_unwrap` is a pure-Python unwrap**: a mesh of tens of thousands of triangles takes tens of seconds to lay out (the conformal map of an island of more than 6000 triangles is replaced by a planar projection), and the
  packing is a few per cent looser than a dedicated packer's.
- **FielDev writes no animation and no morph targets**: it is a modelling program. A rigged glTF is the mesh in its bind pose with the skeleton and the skin weights.
