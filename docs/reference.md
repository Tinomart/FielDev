# Library reference

Every public function and class of the FielDes library, generated from its docstrings
(`python scripts/gen_reference.py`).  `from fieldes import *` brings all of them in.

Contents: [Primitive shapes](#primitive-shapes) | [Combining shapes (CSG)](#combining-shapes-csg) | [Moving, rotating, scaling, deforming](#moving-rotating-scaling-deforming) | [Text](#text) | [Importing models](#importing-models) | [Triangle meshes](#triangle-meshes) | [Materials of an export](#materials-of-an-export) | [Skeletons of an export](#skeletons-of-an-export) | [Exporting files](#exporting-files) | [Handles: editing shapes by dragging](#handles-editing-shapes-by-dragging) | [Linked copies](#linked-copies) | [Symmetry](#symmetry) | [Points and surfaces](#points-and-surfaces) | [Lines and curves: 1D shapes made of points](#lines-and-curves-1d-shapes-made-of-points) | [Profiles and extrusions](#profiles-and-extrusions) | [Characters: limbs made of points](#characters-limbs-made-of-points) | [Measuring a body](#measuring-a-body) | [Fields](#fields) | [Regressions and data](#regressions-and-data) | [Surfaces and offsets](#surfaces-and-offsets) | [Selecting surfaces](#selecting-surfaces) | [Telling fields from numbers](#telling-fields-from-numbers) | [The shape class](#the-shape-class) | [Progress of a long step](#progress-of-a-long-step) | [Caching](#caching) | [Keeping rendered meshes (render cache)](#keeping-rendered-meshes-render-cache) | [A resolution of its own for one body](#a-resolution-of-its-own-for-one-body) | [FielDes apps: the inputs of a script](#fieldes-apps-the-inputs-of-a-script)

## Primitive shapes

Python library of FielDes, built on the libfive CAD kernel

Originally generated from the C++ standard library (kernel/stdlib/libfive_stdlib.h) by the libfive
project; the generator is not part of FielDes, so this file is now maintained by hand.

This is fieldes.stdlib.shapes

Every shape has ONE primitive, with that shape and nothing else: `box`, `cylinder`, `sphere`, ... (no centred or mitered or `_z` variants:
a shape that stands another way is turned with rotate_x / rotate_y / rotate_z, one that sits somewhere else is moved with move).
The 3D shapes stand along z, the 2D shapes lie in the plane z = 0.

### `array_polar(shape, n, center=(0, 0))`

Iterates a shape about an optional center position

### `array_polar_z(shape, n, center=(0, 0))`

Iterates a shape about an optional center position

### `array_x(shape, nx, dx)`

Iterates a part in a 1D array

### `array_xy(shape, nx, ny, delta)`

Iterates a part in a 2D array

### `array_xyz(shape, nx, ny, nz, delta)`

Iterates a part in a 3D array

### `box(a, b)`

A box between two opposite corners (a true distance outside it: an offset of it has rounded edges)

### `circle(r, center=(0, 0))`

A 2D circle with the given radius and optional center

### `cone(radius, height, base=(0, 0, 0))`

A cone with the given base radius and height, standing along z on the (optional) base position: the base is a disc of that radius at the base height and the apex stands
`height` above its centre.  It has two faces, the base and the side: its handles pull the base (it moves up or down) and the side (the cone grows or shrinks at the same slope, round
its base), and the axis stays where it is

### `cylinder(r, h, base=(0, 0, 0))`

A cylinder with the given radius and height, standing along z on the (optional) base position

### `emptiness()`

A value which is empty everywhere

### `half_space(norm, point=(0, 0, 0))`

A plane which divides the world into inside and outside, defined by its
normal and a single point on the plane

### `polygon(r, n, center=(0, 0))`

A polygon with center-to-vertex distance r and n sides.  Its handles pull a side each -- a side moves parallel to itself, the others stay -- and the gizmo's pivot is where the polygon was made, so a side pulled moves that side only, at any scale

### `prism(a, b, c, z0, z1)`

A triangular prism: the triangle of the three corners a, b, c (x, y) between the heights z0 and z1.  Its handles pull a face each -- the three sides and the two ends -- parallel to itself,
and the gizmo's pivot is where the prism was made, so a face pulled moves that face only, at any scale

### `pyramid(a, b, zmin, height)`

A pyramid defined by its base rectangle (the corners a and b), lower Z value, and height: its tip stands above the middle of the base.  It has five faces -- the base and four
slanted ones -- and its handles pull one each, parallel to itself (the slopes stay what they were made with)

### `rectangle(a, b)`

A rectangle between the corners a (the low one) and b (the high one) (a true distance outside it: an offset of it is a rounded rectangle).  Its four numbers are
its four sides, so the handles of a rectangle pull one side each

### `ring(ro, ri, center=(0, 0))`

A 2D ring with the given outer/inner radii and optional center

### `rounded_box(a, b, r)`

Rounded box with the given bounds.  The radius `r` is a fraction, 0 to 1, of half the shortest side of the box (r = 0.4 on a box 15 mm thick rounds its edges with a radius of 3 mm; 1 makes the
shortest side a half circle).  Its handles pull a side each -- a side moves, the others and the rounding stay -- and the gizmo's pivot is where the box was made, so a side pulled moves that side only, at any scale

### `rounded_rectangle(a, b, r)`

A rectangle with rounded corners of radius r, between the corners a (the low one) and b (the high one) (a true distance outside it).  The corners are tangent to the
sides whatever the numbers are: its handles pull a side each (the radius with them)

### `sphere(radius, center=(0, 0, 0))`

A sphere with the given radius and (optional) center

### `torus(ro, ri, center=(0, 0, 0))`

A torus lying round the z axis, with the given outer radius, inner radius, and (optional) center

### `triangle(a, b, c)`

A 2D triangle between three corners.  Its handles pull a side each: a side moves parallel to itself, and the gizmo's pivot is where the triangle was made, so a side pulled moves that side only, at any scale

## Combining shapes (CSG)

Python library of FielDes, built on the libfive CAD kernel

Originally generated from the C++ standard library (kernel/stdlib/libfive_stdlib.h) by the libfive
project; the generator is not part of FielDes, so this file is now maintained by hand.

This is fieldes.stdlib.csg

### `blend(a, b, m)`

Blends two shapes by the given amount using exponents,
with the blend term adjusted to produce results approximately
resembling blend_rough for values between 0 and 1.

### `blend_difference(a, b, m, o=0)`

Blends the subtraction of b, with optional offset o,
from a, with smoothness m

### `blend_expt(a, b, m)`

Blends two shapes by the given amount using exponents

### `blend_expt_unit(a, b, m)`

Blends two shapes by the given amount using exponents,
with the blend term adjusted to produce results approximately
resembling blend_rough for values between 0 and 1.

### `blend_rough(a, b, m)`

Blends two shapes by the given amount, using a fast-but-rough
CSG approximation that may not preserve gradients

### `clearance(a, b, offset)`

Expands shape b by the given offset then subtracts it from shape a

### `difference(a, b, *rest)`

Subtracts any number of shapes from the first argument

### `intersection(a, *args)`

Returns the intersection of two shapes

### `inverse(a)`

Returns a shape that's the inverse of the input shape

### `loft(a, b, zmin, zmax)`

Produces a blended loft between a (at zmin) and b (at zmax)
a and b should be 2D shapes (i.e. invariant along the z axis)

### `loft_between(a, b, lower, upper)`

Produces a blended loft between a (at lower.z) and b (at upper.z),
with XY coordinates remapped to slide between lower.xy and upper.xy.
a and b should be 2D shapes (i.e. invariant along the z axis)

### `morph(a, b, m)`

Morphs between two shapes.
m = 0 produces a, m = 1 produces b

### `offset(a, o)`

Expand or contract a given shape by an offset
Positive offsets expand the shape; negative offsets shrink it

### `shell(a, offset)`

Returns a shell of a shape with the given offset

### `union(a, *args, radius=0)`

The union of any number of shapes.  radius (mm, default 0: a sharp union) blends the surfaces where they meet
with a smooth transition of that radius, so parts that do not quite fit together are joined by a fillet --
a rib and a plate, a horn and a head.  It works on any field.
(A radius that is a field makes a blend that varies.)

## Moving, rotating, scaling, deforming

Python library of FielDes, built on the libfive CAD kernel

Originally generated from the C++ standard library (kernel/stdlib/libfive_stdlib.h) by the libfive
project; the generator is not part of FielDes, so this file is now maintained by hand.

This is fieldes.stdlib.transforms

### `attract(shape, locus, radius, exaggerate=1)`

Attracts the shape away from a point based upon a radius r,
with optional exaggeration

### `attract_x(shape, locus, radius, exaggerate=1)`

Attracts the shape away from a YZ plane based upon a radius r,
with optional exaggeration

### `attract_xy(shape, locus, radius, exaggerate=1)`

Attracts the shape away from line parallel to the Z axis,
with a particular radius and optional exaggeration

### `attract_xz(shape, locus, radius, exaggerate=1)`

Attracts the shape away from line parallel to the Y axis,
with a particular radius and optional exaggeration

### `attract_y(shape, locus, radius, exaggerate=1)`

Attracts the shape away from a XZ plane based upon a radius r,
with optional exaggeration

### `attract_yz(shape, locus, radius, exaggerate=1)`

Attracts the shape away from line parallel to the X axis,
with a particular radius and optional exaggeration

### `attract_z(shape, locus, radius, exaggerate=1)`

Attracts the shape away from a XY plane based upon a radius r,
with optional exaggeration

### `move(shape, v)`

Moves the given shape in 2D or 3D space

### `reflect_x(t, x0=0)`

Reflects a shape about the x origin or an optional offset

### `reflect_xy(t)`

Reflects a shape about the plane X=Y

### `reflect_xz(t)`

Reflects a shape about the plane X=Z

### `reflect_y(t, y0=0)`

Reflects a shape about the y origin or an optional offset

### `reflect_yz(t)`

Reflects a shape about the plane Y=Z

### `reflect_z(t, z0=0)`

Reflects a shape about the z origin or an optional offset

### `repel(shape, locus, radius, exaggerate=1)`

Repels the shape away from a point based upon a radius r,
with optional exaggeration

### `repel_x(shape, locus, radius, exaggerate=1)`

Repels the shape away from a YZ plane based upon a radius r,
with optional exaggeration

### `repel_xy(shape, locus, radius, exaggerate=1)`

Repels the shape away from line parallel to the Z axis,
with a particular radius and optional exaggeration

### `repel_xz(shape, locus, radius, exaggerate=1)`

Repels the shape away from line parallel to the Y axis,
with a particular radius and optional exaggeration

### `repel_y(shape, locus, radius, exaggerate=1)`

Repels the shape away from a XZ plane based upon a radius r,
with optional exaggeration

### `repel_yz(shape, locus, radius, exaggerate=1)`

Repels the shape away from line parallel to the X axis,
with a particular radius and optional exaggeration

### `repel_z(shape, locus, radius, exaggerate=1)`

Repels the shape away from a XY plane based upon a radius r,
with optional exaggeration

### `revolve_y(shape, x0=0)`

Revolves a 2D (XY) shape about a line parallel to the Y axis with the
given x value

### `rotate(t, angle, center=(0, 0, 0))`

Rotate the given shape by an angle in radians
The center of rotation is [0 0 0] or specified by the optional argument

### `rotate_x(t, angle, center=(0, 0, 0))`

Rotate the given shape by an angle in radians
The center of rotation is [0 0 0] or specified by the optional argument

### `rotate_y(t, angle, center=(0, 0, 0))`

Rotate the given shape by an angle in radians
The center of rotation is [0 0 0] or specified by the optional argument

### `rotate_z(t, angle, center=(0, 0, 0))`

Rotate the given shape by an angle in radians
The center of rotation is [0 0 0] or specified by the optional argument

### `scale_x(t, sx, x0=0)`

Scales a shape by sx on the x axis about 0 or an optional offset

### `scale_xyz(t, s, center=(0, 0, 0))`

Scales a shape on all three axes, about 0 or an optional offset

### `scale_y(t, sy, y0=0)`

Scales a shape by sx on the x axis about 0 or an optional offset

### `scale_z(t, sz, z0=0)`

Scales a shape by sx on the x axis about 0 or an optional offset

### `shear_x_y(t, base, height, offset, base_offset=0)`

Shears a shape on the x axis as a function of y
offset = base-offset at base.y
offset = offset = base.y + h

### `symmetric_x(t)`

Clips the given shape at the x origin, then duplicates the remaining
shape reflected on the other side of the origin

### `symmetric_y(t)`

Clips the given shape at the y origin, then duplicates the remaining
shape reflected on the other side of the origin

### `symmetric_z(t)`

Clips the given shape at the z origin, then duplicates the remaining
shape reflected on the other side of the origin

### `taper_x_y(shape, base, h, scale, base_scale=1)`

Tapers a shape along the x axis as a function of y
width = base-scale at base
width = scale at base + [0 h]

### `taper_xy_z(shape, base, height, scale, base_scale=1)`

Tapers a shape in the xy plane as a function of z
width = base-scale at base
width = scale at base + [0 0 height]

### `twirl_axis_x(shape, amount, radius, center=(0, 0, 0))`

Twirls the shape in the x axis about the line extending from the
(optional) center point

### `twirl_axis_y(shape, amount, radius, center=(0, 0, 0))`

Twirls the shape in the y axis about the line extending from the
(optional) center point

### `twirl_axis_z(shape, amount, radius, center=(0, 0, 0))`

Twirls the shape in the z axis about the line extending from the
(optional) center point

### `twirl_x(shape, amount, radius, center=(0, 0, 0))`

Twirls the shape in the x axis about the (optional) center point

### `twirl_y(shape, amount, radius, center=(0, 0, 0))`

Twirls the shape in the y axis about the (optional) center point

### `twirl_z(shape, amount, radius, center=(0, 0, 0))`

Twirls the shape in the z axis about the (optional) center point

## Text

Python library of FielDes, built on the libfive CAD kernel

Originally generated from the C++ standard library (kernel/stdlib/libfive_stdlib.h) by the libfive
project; the generator is not part of FielDes, so this file is now maintained by hand.

This is fieldes.stdlib.text

### `text(txt, pos=(0, 0))`

Returns the given text, rendered in a custom f-rep font
(with a character height of 1)

## Importing models

Importing a model: import_model() and tessellate().

    parts = import_model("rock.obj")               # a triangle mesh
    part, bounds = parts[0]
    view.set_bounds(*roi(parts))

import_model() is the one function to know.  It reads a triangle mesh (.stl, .obj, .ply, .3mf, .glb, .gltf, .fbx, .off, .dxf)
and returns a list of (shape, (lower corner, upper corner)) with one entry, placed where the file has it, in the units you ask for.
The shape is the exact signed distance to the mesh's triangles.

    tessellate(source)      the exact surface as a distance field -- of a mesh file, of ANY field (tessellate(shape): the
                            field's surface made a mesh and the exact distance to it, which makes offsets and shells
                            uniform), of a list of parts

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.

### `import_model(path, units='mm', file_units=None, rev=None)`

Imports a triangle mesh (.stl, .obj, .ply, .3mf, .glb, .gltf, .fbx, .off, .dxf) as a list of one
(shape, (lower corner, upper corner)), the shape being the exact signed distance to its triangles:

    parts = import_model("rock.obj")
    part, bounds = parts[0]
    view.set_bounds(*roi(parts))

units       the units of your script ('mm', 'cm', 'm', 'in'...)
file_units  what the numbers of the file mean ('mm' if it does not say: STL, OBJ, PLY and OFF do not; 3MF, FBX and DXF
            with $INSUNITS do, glTF is metres)
rev         a number that is part of what an import is kept by: another one imports again ("Reimport" in FielDes)

### `tessellate(source, units='mm', file_units=None, rev=None, bounds=None, resolution=None)`

The exact surface, as a distance field.  `source` is

a file          a mesh file: what import_model() makes of it.  Returns [(shape, bounds)] as import_model() does
a field         any shape: its surface is meshed (`resolution` samples per unit, default about 200 along its
                longest side; `bounds` = ((x0, y0, z0), (x1, y1, z1)) if they cannot be found) and the result is
                the exact signed distance to that mesh.  Booleans, blends and warps have fields that are only
                roughly a distance; after this offsets and shells are uniform.  Returns a shape.  (A feature
                thinner than the mesh cells falls between its samples: raise `resolution`)
a list          of (shape, bounds) -- what import_model() returns -- or of shapes: each tessellated

units, file_units, rev: see import_model()

## Triangle meshes

Triangle-mesh import (what import_model() does with a mesh file): STL (binary or ASCII), Wavefront OBJ, PLY
(ASCII or binary), 3MF, glTF (.glb / .gltf), Autodesk FBX (binary or ASCII: see fbx.py for what that means), OFF and DXF (3DFACE
and polyface meshes) files.

    parts = import_model(r"C:\models\bracket.stl")
    bracket, bounds = parts[0]
    view.set_bounds(*roi(parts))

The mesh becomes an exact signed distance field (negative inside), so it
works with everything else in fieldes.stdlib: union / difference with CSG
shapes, offset / shell / blend, transforms and so on.  Before that its
triangles are cleaned up (duplicate vertices welded, degenerate triangles
dropped, windings made consistent, inside-out shells flipped).  Meshes with
holes still import: near a hole, inside and outside come from the
generalised winding number, which closes it with a smooth membrane.

STL, OBJ and PLY files carry no units: pass file_units= to say what their
numbers mean (e.g. 'm' or 'in'; millimetres otherwise).  3MF files state
their unit and glTF is always in metres; that is used unless file_units=
overrides it.  glTF's Y-up axes are turned into FielDes's Z-up.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.

### `mesh_info(path)`

The summary of the last import of `path` in this session (triangle
count, whether it is watertight, ...) as a dict, or None.

## Materials of an export

Materials: a name, a colour, how it shines -- and where on the model it applies, as a field.

    skin = material("skin", color=(0.9, 0.72, 0.6), roughness=0.7)
    metal = material("metal", color="#9aa0aa", metallic=1.0, roughness=0.3, where=box((-40, -30, 100), (40, 30, 150)))
    export_mesh(character, "hero.glb", materials=[skin, metal])

The materials of an export are LAYERS, painted in the order they are listed: each triangle takes the last material whose `where` is negative at the middle of the
triangle (inside the body or the field it names), so a material without a `where` -- the base -- goes first.  A triangle no material covers has none.  OBJ files
get a .mtl file next to them (`usemtl` for each group of triangles), glTF files a material for each and a primitive of the mesh for each.

`where` is any field: a body (the material is on what is inside it), or a field -- `100 - z_field()` is negative above z = 100.  The edge between two materials
runs along the triangles of the mesh: as fine as the resolution of the export.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.

### `Material`

A material for `export_mesh(..., materials=[...])`: see `material`

### `material(name, color=(0.8, 0.8, 0.8), roughness=0.5, metallic=0.0, emissive=None, where=None, texture=None)`

A material of a mesh export (`export_mesh(part, "hero.glb", materials=[...])`).

name       what the file calls it (letters, digits, - and _)
color      (r, g, b) from 0 to 1, or "#rrggbb"
roughness  0 (a mirror) to 1 (chalk)
metallic   0 (a dielectric) to 1 (a metal)
emissive   (r, g, b) or "#rrggbb" for a surface that glows, or None
where      a body or a field: the material is on the triangles whose middle is inside it (where its value is negative).  None: everywhere
texture    the file name of an image (a path relative to the mesh file, "skin.png"): the colour of the surface, mapped with the UVs of the export
           (`export_mesh(..., uvs="box")`).  The image is not copied or checked: it is the name the file says

The materials of an export are layers: each triangle takes the LAST one that covers it, so the base material (no `where`) goes first.

## Skeletons of an export

Rigging: a skeleton of joints for the glTF that a game engine animates.

    hips = joint("hips", (0, 0, 92))
    spine = joint("spine", (0, 0, 128), parent="hips")
    shoulder = joint("shoulder.R", shoulder_point, parent="spine")           # a point works: its numbers at the time of the export
    elbow = joint("elbow.R", (31, 0, 113), parent="shoulder.R")
    bones = mirror_joints([hips, spine, shoulder, elbow])                    # every ".R" joint gets a ".L" one on the other side of x = 0
    export_mesh(figure, "hero.glb", skeleton=bones)

The joints are in the order they are given, every joint after its parent, and there is ONE root.  The export writes them as the nodes of the glTF, with the
skin (the inverse bind matrices) and, for every vertex, the four joints that move it and how much (JOINTS_0 and WEIGHTS_0): the weights come from the
distance of the vertex to the bones.  The bone of a joint is the segments from it to its children (and the joint itself): the geometry between the elbow and
the hand follows the elbow, as it does when the elbow is turned.  A vertex follows the nearest bone alone, and shares itself with the others that are about as near
-- within `skin_falloff` -- so that a joint bends smoothly.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.

### `Joint`

A joint of a skeleton: see `joint`

### `joint(name, position, parent=None, tip=None)`

A joint of a skeleton for `export_mesh(..., skeleton=[...])`.

name      what the file calls it (a text: "elbow.R"; each joint of a skeleton has its own)
position  where it is in the model: a point (the numbers it has when the file is written) or (x, y, z)
parent    the name of the joint it hangs from, a joint that was made before it; None for the root, which there is one of
tip       where the bone of a joint with no children ends -- the hand, the head, the toe: a point or (x, y, z).  Not given: the bone goes on in the
          direction of the one before it for half its length (the hand goes on past the wrist), so that the end of the body has a bone of its own

### `mirror_joints(joints, axis='x', plane=0.0, suffixes=('.R', '.L'))`

The joints and the mirror images of those whose name ends with `suffixes[0]`: across the plane `axis` = `plane` ("x", "y" or "z"), named with `suffixes[1]`
instead, hanging from the mirror image of their parent when it has one and from their parent otherwise.  The skeleton of a half of a body is the skeleton of all of it

## Exporting files

Exporting: a body as a mesh file, a field sampled on a grid.

    export_mesh(part, "part.stl")                   .stl .obj .ply .3mf .glb .gltf .fbx .off .dxf  (see meshfiles.py)
    export_mesh(part, "hero.obj", units="m", up="y")    the unit and the up axis of the numbers in a file that has none of its own
    export_mesh(part, "hero.glb", max_triangles=3000)   the finest mesh that is within a budget of triangles
    export_mesh(part, "hero.glb", symmetric="x")        the x >= 0 half, cut exactly at x = 0, and its mirror image: symmetric to the last bit
    export_field(field, "noise.vti")                any field sampled on a regular grid: .vti (VTK image data), .csv

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.

### `export_field(field, path, bounds=None, resolution=None, name='field')`

Samples a field -- anything that is a Shape -- on a regular grid and writes it:

    .vti   VTK image data (ParaView ...): the values as point data
    .csv   x, y, z, value for every grid point

bounds      ((x0, y0, z0), (x1, y1, z1)): the box sampled (the extent of the shape that has one: field.bounds, else this is needed)
resolution  samples per mm (the scene's resolution by default, limited to 2 million points)

A field is not a mesh: this is the sampling of it that other programs work with, at the resolution asked for.  Returns the path.

### `export_lods(part, path, triangles, **options)`

Writes levels of detail of a body, each a mesh of at most so many triangles (see `max_triangles` of export_mesh): `export_lods(hero, "hero.glb", [8000, 2000, 500])` writes
hero_lod0.glb with at most 8000 triangles, hero_lod1.glb with 2000 and hero_lod2.glb with 500.  `triangles` is the budgets, the finest first and each smaller than the
one before; None for a level with no budget.  The other options are those of export_mesh (units, up, symmetric, materials, skeleton, pivot ...), the same for every
level.  Returns the paths written

### `export_mesh(part, path, bounds=None, resolution=None, name=None, ascii=False, units=None, up=None, max_triangles=None, symmetric=None, materials=None, colors=None, uvs=None, skeleton=None, skin_falloff=None, pivot=None)`

Writes the surface of a body as a triangle mesh file, in the format of the file's extension:

    .stl (binary; ascii=True for text), .obj, .ply, .3mf, .glb, .gltf, .fbx (Autodesk FBX, ASCII 7.4: see fbx.py), .off, .dxf (3DFACE)

part        a body (a shape, or a list of them)
path        the file to write (a folder that is not there is made)
bounds      ((x0, y0, z0), (x1, y1, z1)) the region meshed; the body's own extent when it is not given
resolution  samples per mm of the mesh (the scene's resolution when it is not given: the one of the viewport)
name        the object's name inside the file (the file's name)
ascii       STL as text, not binary
units       the unit of the numbers in the file: "mm" (default), "cm", "m" or "in".  Only for .stl .obj .ply .off, which have no unit of their own
up          the axis that is up in the file: "z" (default: as modelled) or "y" (a game engine's; the model is turned, not mirrored).  Same four formats
max_triangles   a budget: the finest mesh of at most this many triangles (the resolution is lowered until it fits; a mesh within it is left as it is)
symmetric   "x", "y" or "z" (or ("x", 12.5): the plane at that position): the half on the larger-coordinate side ("-x": the smaller) is the
            model, cut exactly at the plane, and the other half is its mirror image -- exactly symmetric, and closed where the mesh was.
            The model is only as symmetric as the half you give it: the mesh does not have to be
materials   a list of `material(...)`s (see materials.py), painted in the order given: each triangle has the LAST one whose `where` field is negative at the
            middle of the triangle (a material with no `where` covers everything: it goes first).  .obj (a .mtl file is written beside it), .glb, .gltf
colors      (r, g, b), each a number or a field from 0 to 1, evaluated at every vertex: vertex colours.  .obj, .ply, .glb, .gltf
uvs         "box": texture coordinates by the box projection -- each triangle is projected along the axis its normal is mostly along, seen from outside, so a
            texture is not mirrored on the back faces; the vertices on a seam are made again for each side of it.  The texture fits each side once (the
            largest side of the model is 0 to 1), or ("box", 500) repeats it every 500 mm of the model, going on from one surface to the next (world-scaled
            tiling).  .obj (vt), .ply (s, t), .glb, .gltf (TEXCOORD_0).  The images are the `texture=` of the materials
skeleton    a list of `joint(...)`s (see rigging.py), one root, each after its parent: written as the nodes and the skin of a glTF, with the four joints that
            move each vertex and their weights (JOINTS_0, WEIGHTS_0) made from the distance of the vertex to the bones.  .glb, .gltf
skin_falloff  how far, in mm, a bone can be behind the nearest one and still move a vertex (the width of the blend at a joint); None: 4 % of the model
pivot       where the origin of the file is: "origin" (default: as modelled), "base" (the middle of the bottom of the model: a character stands on the ground, its feet
            at 0), "center" (the middle of its box), or a place (x, y, z) of the model.  The skeleton moves with it

Millimetres and Z up in every format that has no unit or axis (see units, up); the ones that state their unit (3MF, FBX, DXF) say millimetres
(a glTF is in metres, Y up, as glTF is), and units= or up= for them are an error.  Returns the path.

## Handles: editing shapes by dragging

Handles and the gizmo: edit a shape -- an imported part too -- by dragging in FielDes's viewport.

Two ways of editing by dragging work together, and the first has priority where they meet:

  the gizmo    the part's own move arrows, rotation rings and scale knobs: `gizmo()` writes, under the shape's
               definition,

                   part = gizmo(
                       part,
                       move=(var(0), var(0), var(0)),
                       rotate=(var(0), var(0), var(0)),
                       scale=(var(1), var(1), var(1)),
                   )

               so what the gizmo does is ordinary script text, like any dragged var().  The shape is `part`
               scaled about its centre, rotated (x, then y, then z; degrees) and moved.  When the gizmo is shown
               is the `mode` of that call (the model tree's gizmo button, key E, goes through them):

                   'click'   (the default) the gizmo is shown while the shape is selected, i.e. after you click it
                   'never'   it is never shown, so that it cannot get in the way
                   'always'  it is shown on the shape whether it is selected or not

  handles      the handles on the shape's own surfaces: hover a surface of the shape and drag it.  They are always
               there, whatever the mode of the gizmo.  Any shape with `var()` numbers has them; for a shape written
               with plain numbers -- a primitive, or a shape made of primitives --
               `handles()` makes the numbers that place its surfaces variables:

                   part = handles(part, [var(6), var(40)])

               One line, however many numbers (nobody edits them by hand: they are dragged).  Dragging a face changes
               the number of that face (a plane's position, a radius) in the script text; a round feature keeps its centre,
               a box keeps the face opposite the one dragged.  FielDes writes the call itself when you select the shape.

A lock button beside it (key R) is a separate switch: a locked shape cannot be dragged at all, neither by the
gizmo nor by its handles, and keeps its gizmo mode, which comes back when it is unlocked:

               part = lock(part)

Nothing is stored anywhere but in the script: delete the `handles(...)` and `gizmo(...)` calls of a part
(FielDes's Reimport does) and it is the file's version again; the `lock(...)` call only keeps it from being
dragged. 

### `forget_literals()`

A script was opened: the numbers the last run saw in the calls of the old one say nothing about this one

### `gizmo(shape, move=(0, 0, 0), rotate=(0, 0, 0), scale=(1, 1, 1), about=None, mode=None)`

Scales, rotates and moves a shape, with the gizmo FielDes shows on it.

scale: (x, y, z) factors about the shape's centre, `rotate`: (x, y, z)
rotations in degrees about the same centre (x first, then y, then z),
`move`: (x, y, z) translation.  Write the numbers as var(...) to drag
them: FielDes's model tree does that for you.
about: the centre (default: the middle of the shape's box)
mode: when FielDes shows the gizmo: 'click' (the default) while the shape is selected, 'never', or
'always'.  The shape's own surfaces (see handles()) can be dragged whatever the mode, and the gizmo has
priority where it is shown.
To make a shape undraggable, lock it: `shape = lock(shape)`.

### `handle_values(shape)`

The numbers handles() makes variables, in its order, as the text to write them as

### `handles(shape, values=None, **removed)`

A shape whose surfaces have handles: the numbers that place its
surfaces -- a plane's position, a radius, the faces of a box -- are
replaced by `values`, in the order of their appearance in the shape
(FielDes writes them as var(...) with the shape's own numbers, which
makes them draggable: hover a surface, drag it).  Orientations and the
placement of the whole part are not exposed, so a dragged face
moves and neither turns nor takes the rest of the part along.

With the shape's own numbers the result is the very same shape.  If the
shape has a different number of them (the part was changed in its
file) it raises ValueError: reimport the part.

(This is what expose() was called.  The gizmo -- the arrows, rings and knobs
that move, turn and scale a shape -- is gizmo(shape, move=..., rotate=..., scale=...).)

### `lock(shape)`

`shape`, locked: FielDes does not let it be dragged -- neither by the gizmo nor by its surfaces -- until the
line is deleted.  It is the shape itself in every other way (its bounds, handles, colours and exact regions
stay), and the way of editing it had (gizmo or handles) comes back when it is unlocked.

Write it under a shape's definition, with its gizmo() and handles() calls:

    part = lock(part)

(FielDes's model tree has a lock button on every model -- shapes, results, points -- and the key R toggles it.)

## Linked copies

Linked copies: `instance(shape)`.

A linked copy IS another shape -- the same field, so the same surfaces, sizes, colours and every other property -- and it follows it: change the original
(its numbers, its definition, anything it is made of) and the copy changes with it.  What a copy has of its own is only WHERE it is: its POSITION and its ROTATION are
its own, not the original's -- moving or turning the original does not move or turn the copy, and the other way round -- with its gizmo, `gizmo(copy, move=..., rotate=...)`.
Nothing else is its own: no scale knobs (a scale the original has is part of that shape, and the copy has it too).  Its surfaces CAN be dragged, as the original's can,
and they are linked: both are pulled by the numbers of the original's `handles(...)`, so dragging a surface of the copy moves the original's and every other copy's, and the
other way round.  (A copy that has a shape of its own is another thing: copy the model's statements instead -- Shift+D in FielDes.)

FielDes writes one with Ctrl+D (or Operations > Repeating > instance):

    plate_2 = instance(plate)  # shadow: plate
    plate_2 = gizmo(
        plate_2,
        move=(var(0), var(0), var(0)),
        rotate=(var(0), var(0), var(0)),
    )

The original is only REFERRED to: the mark `# shadow: plate` keeps it where it is in the model tree (a shadow of it is shown under the copy), whether it is
locked or not -- taking the original into the copy would move its row away and make the copy look like what the original is made of.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.

### `instance(shape)`

A linked copy of `shape`: the very same shape -- its surfaces, sizes, colours and properties are the original's, and change with it -- that can only be
moved and rotated, with its gizmo (`gizmo(copy, move=..., rotate=...)`).  It cannot be scaled: its shape is the original's -- and so are the numbers its
surfaces are pulled by, so dragging a surface of the copy or of the original moves both.  FielDes writes it with Ctrl+D, holding the original as a reference (`# shadow: original`: the original keeps its own row in the model tree,
locked or not).  A copy that has a shape of its own is a copy of the statements instead (Shift+D)

## Symmetry

Symmetry: `symmetry_planes(...)`, a model that is a set of mirror planes, and `symmetry_images(shape, symmetry)`, ALL the images of a shape in it, as one model.

    mirror = symmetry_planes()                        # one plane, through the origin, the plane x = 0: a mirror
    mirror = gizmo(mirror, move=(var(0), var(0), var(0)), rotate=(var(0), var(0), var(0)))        # moved and turned with its gizmo, like any model
    leg = cylinder(5, 30, (40, 22, 0))                # the one you edit
    leg_images = symmetry_images(leg, mirror)         # all its images, one model: the leg as it looks in the mirror, left to right

The leg is the only model with numbers: the images are not models of their own, they are what the symmetry makes of the leg, so a symmetry of two planes at right angles makes three
images (a turn of half a way round and two mirror images) in ONE model, and a cube's nine planes make forty-seven in one -- not forty-seven rows and forty-seven lines.

A symmetry is made of planes through one centre.  `kind` says how they are arranged round the axis (the line through the centre that all of them contain, or that is across the
plane of the last):

    'axis'      `planes` planes that all contain the axis, equally spaced (1: a mirror; 2: two at right angles; 3: 60 degrees apart ...)
    'across'    the same, and the plane across the axis (a part is mirrored top to bottom as well)
    'cube'      the nine planes of a cube whose axes are the three lines of the symmetry: three across them, six through its edges
    'turn'      no planes: `copies` copies of what is made, equally spaced round the axis, each the one before it turned by 360 / copies degrees (3: three legs 120 degrees
                apart; 5, 7 ...: any number, 1 to 24) -- the rotational symmetry of a three-legged table, a fan, a gear

Every plane makes an image of what is made while the symmetry is on, and so does every turn between them (two planes at right angles make a turn of half a way round); a 'turn'
symmetry has the turns only: the
images of a symmetry are numbered 1 .. symmetry_count(symmetry).  `symmetry_images(x, mirror)` is all of them (`only=(1, 3)` some of them), `symmetry_image(x, mirror, 2)` one.
The images FOLLOW what they are the images of and the symmetry: move the original and they move the way a mirror shows; move the symmetry (its gizmo) and every image of it moves
with it.  They have no numbers of their own: pulling one pulls the original.  FielDes writes the images of what you make while a symmetry is selected (Shift+S turns that on and off):
one model, `leg_images`, for a body, a 2D shape or a point (a body or a 2D shape: the union of its images; a point: a set of points); what is
made of other models -- a path_extrude, a union -- gets its images the same way (`distinct=True` leaves out those that would be the model itself or another image); a surface or a field
gets one model for each image, `symmetry_image`; so does a profile, a line or a spline: it is made of its points, which are the models, so each point has its images
(`symmetry_image(point, mirror, 3)`) and the stroke goes through them.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.

### `SymmetryPlanes`

A symmetry: mirror planes through a centre (see the top of this file).  In the model tree it is a model of its own kind; selected it has a gizmo that moves and turns it,
and the symmetry card; nothing is drawn of it but its planes

### `base_elements(definition)`

The images of a symmetry as plain matrices (rows), in the order they are numbered: every turn and mirror image but the identity, in the symmetry's own place -- before its
gizmo moved and turned it.  The same list, in the same order, that FielDes's viewport makes

### `symmetry_count(symmetry)`

How many images a symmetry makes of what is made with it: they are numbered 1 .. symmetry_count(symmetry) (see symmetry_image)

### `symmetry_image(shape, symmetry, index=1)`

The image of `shape` in the symmetry `symmetry`: `index` is the number of the image (1 .. symmetry_count(symmetry)).  It follows both: change the shape, or move the
symmetry, and the image changes with it.  It has no gizmo and no numbers of its own: pulling it pulls the shape.  FielDes writes it for everything that is made while the
symmetry is selected (Shift+S)

### `symmetry_images(shape, symmetry, only=None, distinct=False)`

ALL the images of `shape` in the symmetry `symmetry`, as ONE model -- or those numbered in `only`, `only=(1, 3)`; with `distinct=True` those that are neither the shape
itself nor another image (a tube along a path that lies in a plane of the symmetry has no image in that plane) -- so that what a symmetry of several planes makes of a leg
is one row of the model tree and one line of the script, not one for each image.  It is the union of the images for a body or a 2D shape (the shape
itself is not in it: it is its own model, the one you edit), and a set of points for a point.  The viewport draws each image as a shape of its own, meshed and moved on its
own (so that dragging the shape moves its images as it is dragged, with nothing meshed again), all of them one model of the tree: select it and all of them are selected.
It follows the shape and the symmetry as each image does (see symmetry_image) and has no numbers of its own: its gizmo is the shape's, drawn at the first image, and pulling
a surface of any of them pulls the shape.

What a shape was made from is mirrored TOGETHER with it: the profiles, the lines and the points of the models it was made from -- the profile and the path of a
`path_extrude`, the profile of an `extrude`, whatever the operation -- are drawn with each image, as a copy of the line or the outline and a dot for each point.  They are not
models -- there is no statement and no row of the model tree for them -- and the ones of the shape you made stay the only ones with numbers: press a dot of any image's and drag
it, and it is that point of the original that moves.

### `symmetry_planes(planes=1, kind='axis', centre=(0, 0, 0), axis=(0, 0, 1), first=None, copies=None)`

A symmetry: mirror planes through `centre`.  `kind` is 'axis' (`planes` planes that all contain the axis `axis`, equally spaced: one is a mirror), 'across' (and the plane
across the axis) or 'cube' (the nine planes of a cube).  `first` is a line in the first plane (across the axis; any when it is left out): with one plane the plane is the one
that holds the axis and `first`.  The default is the mirror x = 0.

`kind='turn'` has no planes: it is the rotational symmetry of `copies` copies equally spaced round the axis (`copies=3`: three legs 120 degrees apart; 5, 7 ... up to 24),
each the one before turned by 360 / copies degrees -- nothing is mirrored.

It is a model: selected in the model tree it has a gizmo -- moved, turned -- and everything made while it is selected is made with its images (see symmetry_image)

## Points and surfaces

Points and surfaces: models of their own kind, and how every kind is drawn.

    p = point(10, 0, 5)                    a point: drawn as a dot (the middle point of a gizmo); click it and its gizmo shows, and moves it
    s = plane((0, 0, 8), (0, 0, 1))        a surface: an open sheet, the zero set of a field, with no body behind it
    wavy = wave_surface(2, 10)             z = 2 sin(2 pi x / 10)

A point is usable where a field function takes a position (distance_to_point(p), attractor(p, ...)) and gives its
coordinates as p.xyz.  A surface is a field like any other (negative on one side, positive on the other), so it works
wherever a field does: thicken(s, 1) makes it a wall, texture(part, region=s) roughens the part there.

What is drawn for each kind of model (Shape._display calls displayed() below):
    a 3D shape                    as it is
    a 2D shape (no z)             its face in the z = 0 plane: flat, a sheet with no thickness (it has no height)
    a surface                     the sheet itself, with no thickness (the zero set of its field, meshed as it is)
    a point                       a dot, the middle point of a gizmo (click it to select the point: its gizmo shows)
    a field                       nothing in the viewport: selected in the model tree it is shown by the section viewer,
                                  which colours a plane through the render region by the field (move the plane to see
                                  the field in 3D)

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.

### `Point`

A point: p.xyz is its coordinates (numbers or fields).  The viewport draws it as **a dot** -- the middle point of a gizmo -- wherever it is;
click the dot to select it, and its full gizmo shows.  (As a field it is a tiny ball, which gives it a place for its gizmo and for the
bounds of what is made of it: nothing of the ball is painted.)

### `PointSet`

A set of points: what the images of a point under a symmetry make (symmetry_images).  FielDes draws
them, each as the dot of a gizmo (without the gizmo's handles: they are data, not something to drag).
.points     the points, (x, y, z) in mm
.spacing    the average distance between a point and its nearest neighbour that it was made for
.body       the body they were made in (None when they were not made in one)
len(points), iterating it, points[i] work as for a list; points.stats() says how the points really are

#### `PointSet.stats(self)`

How the points are: {count, mean, min, max} -- the distance from a point to its nearest neighbour (mm), on average, the
smallest and the largest of them

### `Surface`

An open surface: the zero set of a field, with no body behind it (negative on one side, positive on the other)

### `cylinder_surface(radius=5.0, axis='z', center=(0, 0, 0))`

The surface of an infinite cylinder along an axis: a surface, negative inside

### `displayed(shape)`

What FielDes draws for a shape (see the top of this file)

### `plane(point=(0, 0, 0), normal=(0, 0, 1))`

A plane through `point`, positive on the side `normal` points to: a surface

### `point(x=0.0, y=0.0, z=0.0, smooth=None, radius=None)`

A point at (x, y, z).  Its coordinates are numbers or fields.  It is drawn as a dot (the middle point of a gizmo): click it, and its gizmo shows.
In a `profile` or the path of a `path_extrude` it is a spline point when `smooth` is True (the curve goes smoothly through it, in the direction
its gizmo's rotation gives) and a corner when False; None (the default): what the profile says.  In a `profile` it can also be a ROUND corner, `radius=r`: an exact arc
of that radius, tangent to both edges, takes the place of the corner (the scale of its gizmo multiplies the radius; a spline point has no radius).  A double click on its
dot goes from a corner to a spline point to a round corner and back to a corner

### `sphere_surface(radius=10.0, center=(0, 0, 0))`

The surface of a sphere (without its inside): a surface, negative inside

### `surface(field)`

An open surface from any field: where the field is 0.  (A body's field as a surface is its skin.)

### `wave_surface(amplitude=2.0, period=10.0, axis='x', height=0.0)`

A wavy sheet z = height + amplitude sin(2 pi s / period) along an axis (s = x or y): a surface, positive above it

### `weld_shift_of(shape)`

The shift a point or a curve is DRAWN with: its own (path_extrude sets it on the path of a sweep and on its points), or -- for the image of such a point in a symmetry -- the
original's, taken through the turn or mirror the image is made by.  The image of a path is drawn where the image of its sweep is, as the path is where its sweep is.
None when it is drawn where it is

## Lines and curves: 1D shapes made of points

1D shapes: a line or a spline through points.

    a = point(0, 0, 0)
    b = point(20, 10, 0)
    c = point(40, 0, 5)
    lines = polyline([a, b, c])                 # straight pieces between the points: a hard corner at each
    smooth = spline([a, b, c])                  # a smooth curve through the points
    loop = spline([a, b, c], closed=True)       # joined from the last point back to the first

A curve is a model of its own kind (a 1D shape), made of points and drawn as a line.  It stands on its own, and anything that takes a curve takes it as it is:

    face = profile(loop)                         # the 2D shape a closed curve encloses (see profile)
    tube = offset(smooth, 1.5)                  # a 3D shape: the points at most 1.5 from the curve (a tube round it)
    beam = path_extrude(face, smooth)           # a 2D shape swept along it

As a field a curve is the distance to it (zero on it, positive everywhere else), so `offset`, `thicken` and the field functions work on it.

A polyline is made of corners and a spline of spline points -- but each POINT can say otherwise (`point(..., smooth=True)` or `smooth=False`; FielDes toggles
it when you double-click the point), so a spline can have a corner and a polyline a smooth stretch.  The ROTATION of a spline point -- the rotate numbers of
its gizmo, which a point has no other use for -- turns the direction in which the curve leaves it.  With no rotation the direction comes from the
neighbouring points (a Catmull-Rom spline); the rotation turns it about x, then y, then z (degrees), the way a gizmo turns a shape.  The same
numbers twist what `path_extrude` sweeps along the curve.

The line is made by the kernel from the numbers the points have when the script runs (and drawn from the numbers they have while you drag them).  Its field
is plain math: the least of the distances to its straight pieces, so the renderer drops the pieces that are far from where it looks.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.

### `Control`

One point of a curve or profile: where it is (three numbers; the expressions the script gave are kept for the viewport, which draws the line from them
while the point is dragged), what it says of itself (-1: what the shape says, 0: a corner, 1: a spline point) and its rotation

#### `Control.smooth(self, default)`

*(no description yet)*

### `Curve`

A 1D shape (see `polyline`, `spline`).  .points are the points it was made from, .smooth the default of its points, .closed whether it is joined at its
ends, .vertices the line it is drawn as (x, y, z)

### `add(a, b)`

*(no description yet)*

### `controls(points, rounds=False, radius_default=0.0, smooth_default=False)`

The controls of a curve (`rounds` False: a point that says it is round is a corner there) or of a profile (`rounds` True)

### `cross(a, b)`

*(no description yet)*

### `dot(a, b)`

*(no description yet)*

### `fillets(ctrls, default, closed, normal=None)`

The round corners of the line or face through the controls, made by the kernel: a list of (control, a, b, centre, radius) -- the arc runs from `a` to `b` (the short
way round) about `centre`, in the plane of the face; the radius is what the arc has been made with (smaller than the one asked for where it would run into the next
arc or past the next point)

### `mark(ctrls, default, kind)`

Tell each point what the curve or profile made of it: a corner or a spline point (the viewport draws the two differently, and the double click
changes it), and the default it follows

### `mul(a, k)`

*(no description yet)*

### `owned(shape, cls=<class 'fieldes.shape.Shape'>)`

A new `cls` that owns a copy of the tree of `shape`.  (`shape` is held for the whole call: a copy of `X(...).ptr` made inline would be made from a tree that
is already freed, the temporary having died as soon as its pointer was read)

### `plane_of(ctrls)`

(origin, u, v) of the plane through the first three points that are not on a line (numbers), or None

### `polygon_field(loop, frame, arcs=None)`

The signed distance to the polygon whose corners are `loop` (s, t) -- negative inside, in the plane of `frame` (origin, u, v: s and t are the
coordinates along u and v), or in x and y when there is none.  An exact distance, concave outlines too.

`arcs`: round corners, (a, b, centre, radius) in the same coordinates, each the short way round from a to b; `loop` then has the chord from a to b as an edge
in place of each of them (see `fillets`).  The distance is to the arc, exact (the chord is not an edge of the outline), and the side of the outline is that of the
polygon of the chords turned over inside every circular segment between a chord and its arc: a segment that bulges out of the polygon is added to it, one that bulges
into it is cut out.

Made the way a vector renderer measures a polygon, of two parts, both a plain `min` over small pieces so that the renderer drops the pieces that are far
from where it looks (a polygon of a hundred edges costs what the few pieces near the point cost):
- how far: the least of the distances to the edges;
- which side: the polygon is cut into triangles when the script runs, and a point is inside when it is inside one of them (a `min` over triangles of
  the `max` of three straight lines).  Across a cut a triangle goes a hair over, so that the cut itself is inside; the edges of the polygon are exact.
An outline that crosses itself cannot be cut: its side is then the winding of the outline round the point (the sum of the angles each edge is seen
under: a full turn inside, none outside)

### `polyline(points, closed=False)`

A set of lines: straight pieces through the points, in the order given, a corner at each (a point can say it is a spline point: `point(..., smooth=True)`),
joined from the last point back to the first when `closed`.  As a field it is the distance to the lines

### `polyline_field(vertices, closed)`

The distance to the straight pieces between the vertices (x, y, z): the least of the distances to the pieces, then one square root

### `rotated(t, rotation)`

The vector t turned the way the gizmo turns a shape: about x, then y, then z (degrees)

### `spline(points, closed=False)`

A smooth curve through the points, in the order given (a point can say it is a corner: `point(..., smooth=False)`), joined from the last point back to the first
when `closed`.  It leaves each point in the direction the rotation of its gizmo says (no rotation: from the neighbouring points).  As a field it is the
distance to the curve

### `sub(a, b)`

*(no description yet)*

### `trace(ctrls, default, closed, pieces=14, normal=None, arc_pieces=32)`

(the vertices of the line through the controls, as (x, y, z); for each the number of the control it is after and how far along towards the next it is)
-- made by the kernel.  `normal`: the normal of the plane of a face the points belong to -- the rotation of a point is then one angle about it, in
the plane (the z number of its rotation) -- or None for a line in space.  A round corner is its arc, `arc_pieces` to a quarter turn (0: only the two ends of
the arc: the chord, which is what the exact field of a face is made on, see `fillets`)

### `unit(a)`

*(no description yet)*

### `value_of(c)`

The number a coordinate has now: a number, or a field that is the same everywhere (a var(), an expression of var()s)

### `vec(v)`

*(no description yet)*

### `viewport_data(out, ctrls, default, closed)`

What the viewport draws the line or the face from while a point is dragged: the expressions of each point's place and rotation (their numbers move with
the script's var()s), and what each says of itself.  The line is made again from them at every frame, natively: no script is run

## Profiles and extrusions

A 2D shape from points or from a closed curve: `profile`.

    a = point(0, 0, 0)
    b = point(40, 0, 0)
    c = point(40, 20, 0)
    d = point(0, 20, 0, smooth=True)
    plate = profile([a, b, c, d])                # the face the points enclose; hard edges unless a point says smooth=True
    round = profile([a, b, c, d], smooth=True)   # ...or every point a spline, but where a point says smooth=False
    outline = spline([a, b, c, d], closed=True)
    plate = profile(outline)                     # the same, from a curve
    body = extrude(plate, 0, 5)                 # a solid: the face pulled 5 along its normal

The points are ordinary points (`point(x, y, z)`, dragged with their gizmo): any number of them, joined in the order they are given and closed (the last to
the first).  The shape lies in the PLANE through the first three points (the first that is not on a line with the first two); every other point is
projected onto that plane, so a profile is made whatever the points are.  A tuple of three numbers stands for a point too.

Each point is a corner (a hard edge: straight to its neighbours) or a spline point (the outline is a smooth curve through it) -- see `spline`, which makes the
outline.  `smooth=` of the profile says which a point is that does not say itself (False, a hard edge, by default); `point(..., smooth=True)` says it for
that point -- FielDes toggles it when you double-click the point.  The ROTATION of a spline point -- its gizmo's rotate numbers, which a point has no other use
for -- turns the direction in which the outline leaves it.

A profile is drawn from the numbers its points have, natively, while you drag them.  Its field (for `extrude`, `offset` ...) is plain math, made
when the script runs: the signed distance to the outline -- the distance to the nearest edge, with the side taken from that nearest edge or corner alone, so
the renderer drops the edges that are far from where it looks.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.

### `Profile`

A 2D shape made of points (see `profile`).  .points are the points it was made from, .plane the plane it lies in -- (origin, u, v), three numbers each --
.smooth the default of its points, .profile2d the same field in the coordinates of its plane (x along u, y along v)

### `SurfaceProfile`

A 2D shape made from a surface (see `profile`): the outline of the surface in its plane, holes included.  .plane the plane it lies in -- (origin, u, v), three
numbers each, u x v the way the surface faces --, .profile2d the same field in the coordinates of that plane, .flat whether the surface is flat (it is projected
onto the plane when it is not), .away how far the surface is from the plane at most, .loops the outline as [(polygon, hole)] with the points as (s, t)

### `extrude(shape, a, b)`

A 2D shape pulled into a solid: the part of space between the distances `a` and `b` from its plane, along the plane's normal (the plane is
z = 0 for the shapes that lie there -- a circle, a rectangle -- so that is zmin and zmax; the plane of a profile is the plane of its points,
and the normal is the direction u x v of that plane).  `extrude(circle(5), 0, 10)` is a cylinder 10 tall

### `path_extrude(profile, path, twist=0)`

A 2D shape swept along a curve: the `profile` -- its own axes across the curve (x and y for a shape in the plane z = 0, the two axes of the plane of a profile) -- carried
along `path`, turning with it, without twisting about it unless the points of the curve say so.
THE 2D SHAPE IS WHERE THE SWEEP STARTS: the curve says how it travels, not where from -- the whole sweep is moved so that the first point of the curve is the middle of
the shape (the middle of the box of its outline), and its first ring is the shape itself, in its own plane at whatever angle the curve leaves it (the sweep is slanted
when it is oblique; a shape whose plane holds the direction of the curve is turned across it), so that the shape you edit is the base of what it is swept into.  A circle
or a rectangle is such a shape as a profile is.  The path is DRAWN where the sweep goes -- through the middle of its cross-section, from the middle of the shape, its
points with it -- whatever its own numbers say; only its shape matters, and the first point of it is the middle of the shape:
the ROTATION of a point (its gizmo's rotate numbers) twists the profile about the curve there, and the twist runs between the points as a
smooth change.  `twist` (degrees) turns the whole profile about the curve besides.  The ends are cut square.  A curve with corners is swept
with mitered joints.  `path_extrude(circle(2), spline([a, b, c]))` is a bent tube; `extrude` is the straight case.  `path` may be a list of points:
the spline through them

### `profile(source, smooth=False, radius=0)`

The 2D shape the points of `source` enclose -- a list of points, or a curve -- as a closed outline through them in the order given, in the plane
through the first three of them (the others are projected onto it).  `smooth` is what a point is that does not say (point(..., smooth=True) or
smooth=False): False, a corner (a hard edge: the default), or True, a spline point.  A spline point leaves in the direction the rotation of its gizmo
says (no rotation: from its neighbours).  A point can also be a ROUND corner, `point(..., radius=r)`: an exact arc of radius r, tangent to both edges, takes the place
of the corner (the point stays where the two edges would meet; the scale of its gizmo multiplies the radius; where the arc would run into the next one or past the next
point the radius is made smaller, and a square whose four corners ask for half its side is a circle).  `radius` is what a corner is that does not say, 0 (a hard
corner) by default.  With fewer than three points, or all on a line, it is empty.

`source` can also be a SURFACE picked on a part (`select_surface`): the 2D shape of its outline -- the outline of the face, holes included, in the plane
of the face (exact for a flat face), or, for a surface that is not flat, of its projection onto the plane through its middle, along the way it faces on
average.  It is made from the surface and moves with it: it has no points of its own to drag

## Characters: limbs made of points

Characters: bodies made of points, in the spirit of a skeleton of round joints -- a few points, each with a size, and the flesh round them.

    shoulder = point(0, 0, 40)
    elbow = point(22, 0, 38)
    hand = point(40, 0, 30)
    arm = chain([shoulder, elbow, hand], radii=[7, 5, 4])      # a limb that tapers: a round cone from joint to joint
    leg = chain([point(0, 0, 0), point(0, 0, 25)], radii=[5, 7])
    body = smooth_union(arm, leg, 3)                           # limbs are joined with a blend, as everything else is

`round_cone(a, b, ra, rb)` is the segment: two balls and the taper between them.  `chain(points, radii, blend)` is a limb: a round cone between each two
points that follow each other.  The radius at a joint is the SIZE of its point -- the scale of its gizmo, the ring that is dragged to make the joint
thicker -- times `radii[i]` when radii are given, so a limb is shaped by dragging its points and the sizes of its points, in the viewport, as a spline is.

A joint is a ball, a segment is the surface between two balls with a radius that changes along it, and a chain is the union of its segments: a smooth
body wherever the radius changes gently, and balls at the joints however it changes.  The fields are plain math (no meshing step), so they are blended,
offset, shelled, textured and exported like every other model.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.

### `chain(points, radii=None, blend=0)`

A limb through points: a round cone (see `round_cone`) between each two points that follow each other, joined as one body.

    arm = chain([shoulder, elbow, hand], radii=[7, 5, 4])

points  the joints, in order: points (`point(x, y, z)`, dragged with their gizmos) or tuples of numbers.  One point is a ball
radii   the radius at each joint: a number for all of them, or one for each (numbers or fields).  The radius at a joint is that number TIMES the size of
        its point -- the scale of its gizmo (1 for a point that has none) -- so with no radii the size of a point is its radius, and the ring of its gizmo is the
        thickness of the limb there
blend   the radius of a smooth blend where the segments meet (0, the default: none; the joints are balls already, so a chain is smooth without it)

### `round_cone(a, b, ra, rb=None)`

Two balls, one of radius `ra` at `a` and one of radius `rb` at `b` (the same as `ra` when it is not given), and the surface between them whose radius
changes along the way from one to the other: a limb that tapers, a bone with its joints.  `a` and `b` are points, or tuples of numbers; the radii are
numbers, or fields (a radius that is thick here and thin there).  The cone is cut across by the ends: each ends in a ball, so that limbs that
meet at a joint are one smooth body there.  Where the radius changes fast over a short way the surface is steeper than the field is: a body, not a distance

## Measuring a body

Measuring a body: its box and its middle.

    box = bounding_box(part)          # the smallest box, aligned with the axes, that holds the part: a body of its own
    middle = center(part)             # the middle of that box: a point

Both are what a script needs all the time -- to put something in the middle of a part, to give a region to a condition, to size
a cell to a part, to place the next part against this one -- and both are in the right-click menu of a body.  They are made when
the script runs, from the extent the body has then (a body that is dragged, or has var() numbers, is measured again by the run it
causes), and the extent is the one the body knows exactly -- a box, an imported part -- or else the one found by searching its
field, which can be a little roomy for a body with soft edges.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.

### `bounding_box(body)`

The smallest box, aligned with the axes, that holds `body`: a body of its own (`box` between the body's lowest and highest
corner).  Use it as a region, as the space to lay something out in, or to read the size of a part:

    box = bounding_box(part)
    base = fixed(box)

It is measured when the script runs, from the extent the body knows exactly (a box, an imported part) or the one found by
searching its field.

### `center(body)`

The middle of `body`'s bounding box, as a point:

    middle = center(part)
    part = move(part, (-middle.x, -middle.y, -middle.z))        # the part about the origin

It is measured when the script runs, like bounding_box.

## Fields

Field-driven design tools: scalar fields (Shapes used as values rather than
as solids) and the operations that turn them into geometry.

Every Shape is a field -- a number at every point in space.  A
solid is the region where its field is negative; any other field (a
distance, a ramp, noise, a regression of measured data) can drive a
parameter such as a shell's thickness or an offset:

    from fieldes import *

    part  = sphere(30)
    up    = ramp(z_field(), (-30, 30), (0.5, 3.0))   # 0.5 mm at the bottom -> 3 mm at the top
    skin  = shell_inside(part, up)

Groups:
    coordinates        x_field(), y_field(), z_field(), radial_field(),
                       angle_field(), polar_field()
    distances          distance_to_point / _points / _line / _segment /
                       _polyline / _plane, distance_to_surface, depth_below,
                       signed_distance
    value maps         ramp, clamp, lerp, smoothstep, step_field, normalize,
                       remap_field, attractor, wave, sum_fields, mix
    geometry           thicken, shell_inside / _outside / _centered,
                       offset_by, smooth_union,
                       smooth_intersection, smooth_difference, chamfer_union,
                       union_all, intersection_all, repeat, repeat_polar,
                       mirror_x / _y / _z, twist_z, bend_z
    evaluation         evaluate, sample_grid, field_range, volume_of,
                       mass_properties
    exact distances    exact_distance, offset_exact, shell_exact,
                       round_edges, fillet
    of the surface     normal_field, gradient_field, gradient_magnitude,
                       curvature_field, colored
    data               field_from_points, field_from_csv, noise_field
    surface texture    texture

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.

### `abs_field(field)`

The absolute value of a field at every point

### `add_fields(*fields)`

The sum of fields (and numbers): a + b + ... at every point

### `angle_field(center=(0, 0, 0), axis='z')`

Angle around an axis through `center`, in radians (-pi..pi)

### `attractor(points, radius, falloff='smooth', strength=1.0)`

(`radius` and `strength` are numbers or fields.)  A field that is `strength` at the given points (or curves: pass a
distance field instead of points) and falls to 0 at `radius`.
falloff: 'linear', 'smooth' (smoothstep) or 'gauss'.

### `bend_z(shape, radius, center=(0, 0))`

Bends a shape lying along +x around the z axis: x becomes arc length
on a circle of the given radius

### `body_from_field(field, level=0.0)`

A BODY from a field: what is inside where the field is below `level` (0 by default), its surface where the field
equals `level` -- the other way of field_from_body().  The result is drawn and is a part like any other (it can be
offset, shelled, textured, exported).

    noise = noise_field(12, 3)                                  # a field: not drawn
    lumps = body_from_field(noise, 0.2)                         # the places where it is below 0.2: a body

The value of the body is the field's less `level`, so it is a true distance to its surface only where the field is
one (field_from_body of a body, a distance_to_point ...): the surface is exact, an offset of a body made from a
field that only roughly measures distance is about right, not exact.  `level` may be a field too.

### `chamfer_union(a, b, size)`

Union with a 45-degree chamfer of the given size where the shapes meet

### `clamp(field, lo, hi)`

Limits a field to [lo, hi]

### `colored(shape, field, range=None, label=None, colormap='turbo')`

`shape`, displayed in FielDes coloured by `field` (another Shape: a
distance, noise, a curvature) with a colour map; hovering the model shows the
value.  range=(lo, hi) fixes the colour scale (default: the field's
range on the part).  Anywhere else it is simply `shape`.

### `curvature_field(shape, step=None)`

Mean curvature (1/mm; positive where convex, e.g. 1/r on a sphere of
radius r).  step: finite-difference step in mm (default 0.05)

### `depth_below(shape)`

Depth below a shape's surface: 0 on the surface and outside, growing
towards its interior (e.g. the thickness of material above a point)

### `distance_to_line(point, direction)`

Distance to an infinite line through `point` along `direction`

### `distance_to_plane(point=(0, 0, 0), normal=(0, 0, 1))`

Signed distance to a plane: positive on the side the normal points to (the point's and the normal's
coordinates may be fields: a plane that moves or tilts from place to place)

### `distance_to_point(p)`

Euclidean distance to a point (its coordinates may be fields: a point that is where a field says)

### `distance_to_points(points)`

Distance to the nearest of several points

### `distance_to_polyline(points, closed=False)`

Distance to a polyline (a curve given by its points)

### `distance_to_segment(a, b)`

Distance to the line segment from a to b

### `distance_to_surface(shape)`

Unsigned distance to a shape's surface (the shape's field is used as
the distance, so this is exact for exact distance fields such as
spheres, boxes, imported meshes)

### `divide_fields(first, *others)`

The first field divided by the others: a / b / ... at every point (NaN where a divisor is zero)

### `evaluate(field, point_or_points)`

A field's value at a point, or a list of values at many points

### `exact_distance(shape, reach=None, bounds=None)`

The signed distance field of a shape (mm: negative inside, 0 on the surface, the distance to the surface outside), read from the shape's own field: nothing is
meshed.  Many shapes built with booleans, blends, imports or warps have fields that are only roughly a distance (the field of a box is the largest of the distances to
its planes: boxy mitres outside its edges), and offsets, shells, rounded edges and the depth below a surface mean a true one.  From each point the surface is found
by walking along the field's gradient (a few Newton steps, each a handful of calls of the field), and the distance is the length of that walk -- see distance_field.py.
It is exact for a field that is a distance already, for a sphere, a cylinder, a plane, and for the edge and the corner of a box; at an edge where faces meet at another
angle it is a little off (the walk goes from face to face and ends beside the nearest point).
reach: how far from the surface the distance is made, mm (default a quarter of the shape's size): beyond it the shape's own field stands, so that the walk is not made
(and not drawn) over the whole of space; an offset, a shell or a thickness asks for as much as it needs.  bounds: the box round the shape, when it cannot be found --
only its size is used (the step of the gradient).

### `field_from_body(body)`

The values of a body as a FIELD: the same number at every point as the body (its distance to its surface, negative
inside), but not a body -- it is not drawn, it is not a part, and it is free to be multiplied, divided or powered
and still be a valid field.  (A body itself always keeps its true scale: it is a distance, which a factor would
break.  Selecting the field shows it in the section viewer.)

### `field_from_csv(path, x='x', y='y', z='z', value='value', neighbours=8, power=2.0, delimiter=None, scale=1.0)`

A field from a CSV file of samples (e.g. heights, densities or
colours measured or exported elsewhere): columns by header name or index.
scale multiplies the coordinates (e.g. 1000 for metres -> mm).

### `field_from_points(points, values=None, neighbours=8, power=2.0)`

A field through scattered samples -- measured data, or values
exported from another program: at every point, the
inverse-distance-weighted average (weights 1 / distance^power) of the
nearest `neighbours` samples.  Handles hundreds of thousands of
samples.  points: [(x, y, z), ...] with values [v, ...], or
[(x, y, z, v), ...].  The field stays within the samples' range.

### `field_range(field, body=None, lower=None, upper=None, n=24)`

(min, max) of a field, sampled on a grid over a box (and only inside
`body` if given)

### `fillet(shape, radius, bounds=None)`

Fills every concave (inside) edge and corner of a shape with a
fillet of the given radius (a number or a field), and fills what is narrower than the ball: a ball of that radius rolls in the air, and the
shape is everything it cannot reach.  It is made from the shape's own field (see exact_distance and distance_field.py): the centres of the ball are where the field is
`radius`, and the surface of the result is `radius` from them.  Exact for the inside edge of two flat faces at any angle and for the corner of three
(the ball's centre is where the planes of the faces meet); a slot narrower than the ball is filled flush with its mouth, not left with the sag of the ball resting on its two edges.

### `find_extent(shape, budget=200000, resolution=2.0, half=1000000.0)`

The box ((x0, y0, z0), (x1, y1, z1)) round the inside of a shape, found by searching it with interval
arithmetic -- or None when it has no extent that can be found (it is empty, or open on a side, or the search
ran out of cells).  A shape with var() numbers is searched with the numbers they have in the script: inside
the application a var() is held by the program, and a search that did not know its number would read it as 0
(a box of size var(2) is no box at all).  The search takes a third of a second or more, and every select_surface of the same part
asks for it again on every run of the script: it is remembered by what the shape is (and the numbers it has)

### `gradient_field(shape)`

The gradient of a shape's field, as three fields (gx, gy, gz)

### `gradient_magnitude(shape)`

The length of a field's gradient: 1 for an exact distance field; far
from 1 where a field only roughly measures distance

### `intersection_all(shapes, blend=0)`

Intersection of many shapes (optionally blended)

### `lerp(a, b, t)`

Linear interpolation between two values or fields: a at t = 0, b at
t = 1 (t may itself be a field)

### `low_level_body(logic)`

A BODY from your own logic: `logic(x, y, z)` returns a number that is NEGATIVE inside the body, zero on its surface and
positive outside -- ideally the distance to the surface, so that offsets and shells come out right:

    def ball(x, y, z):
        return (x.square() + y.square() + z.square()).sqrt() - 20          # a ball of radius 20

    part = low_level_body(ball)

or `low_level_body(lambda x, y, z: maximum(x - 6, -6 - x, y - 6, -6 - y, z - 6, -6 - z))` for a cube of 12.  The body is
drawn and is a part like any other.  See low_level_field() for the operations; a field that is not a body is
low_level_field() (and body_from_field() makes a body of it).

### `low_level_field(logic)`

A FIELD from your own logic, in one line or a few: `logic` is a function of the coordinates -- it is called ONCE, with
x, y and z as fields (a function of x and y alone is a 2D field) -- and returns the value you want at that point:

    def ripple(x, y, z):
        distance = (x.square() + y.square()).sqrt()          # the distance from the z axis
        return (distance * 0.6).sin() * 3                    # a ring pattern, up to 3

    waves = low_level_field(ripple)

Write the math with + - * / **, the methods .sqrt() .square() .abs() .sin() .cos() .tan() .exp() .log(), a.max(b) and
a.min(b) (or maximum(a, b, c) and minimum(a, b, c)); a number is a constant field.  What you get is a field like any
other: it is not drawn (display it: its icon opens the field viewer), it goes wherever a number goes (`offset(part,
waves)`), a shell's thickness.  low_level_body() is the same for a body; body_from_field() makes a
body of a field.  In FielDes: right-click, Parametric shapes, New field, low_level_field, writes the function and the call for you.

### `mass_properties(shape, density=1.0, lower=None, upper=None, resolution=None)`

Volume, mass (density in g/cm^3 -> grams), centroid and bounding box
of a solid, by grid sampling.  Returns a dict.  The density is a number or a field (a material that is
denser here than there): the mass adds it up over the solid, and the
dict has the centre of mass as well as the centroid.

### `max_fields(*fields)`

The largest of the fields (and numbers) at every point

### `maximum(*terms)`

The largest of several fields, point by point (Python's own max cannot compare fields; `.max` of one takes one
other): maximum(x - 6, -6 - x, y - 6) is the intersection of three half-spaces.  See minimum().

### `min_fields(*fields)`

The smallest of the fields (and numbers) at every point

### `minimum(*terms)`

The smallest of several fields, point by point: minimum(a, b, c) is the union of three bodies.  See maximum().

### `mirror_x(shape, x=0.0)`

Mirror-symmetric copy: the half at x > x0 reflected onto the other

### `mirror_y(shape, y=0.0)`

Mirror-symmetric copy: the half at y > y0 reflected onto the other

### `mirror_z(shape, z=0.0)`

Mirror-symmetric copy: the half at z > z0 reflected onto the other

### `mix(a, b, t)`

Same as lerp()

### `multiply_fields(*fields)`

The product of fields (and numbers): a * b * ... at every point

### `negate_field(field)`

A field with its sign changed: -a at every point

### `noise_field(scale=10.0, octaves=4, seed=1, gain=0.5, lacunarity=2.0, amplitude=1.0, kind='perlin', warp=0.0)`

Smooth random variation, a field of values around zero (`scale`, `amplitude` and `warp` are numbers or fields).
`scale` is the size (mm) of the largest features -- or three sizes, `(x, y, z)`, to stretch the pattern along an axis: `(40, 4, 4)` is streaks along x --, each
octave adds detail `lacunarity` times finer and `gain` as strong; a different `seed` gives a different pattern.  `kind`:
  'perlin'    the classic: soft hills and hollows (Perlin's improved noise).  Four octaves stay mostly inside +-0.3 and rarely go past +-0.6, so
              `amplitude` is what sets how strong it is: 3 or so uses the range of -1 .. 1
  'billow'    puffy, rounded humps with creases where the noise passes through zero
  'ridged'    sharp ridges where the noise passes through zero (mountains, veins)
  'cellular'  Worley noise: the distance to the nearest of random points, low in the middle of a cell and high at its walls (bubbles, pits, scales)
  'cracks'    the distance from the walls between those cells, low along them (a web, a foam's walls, cracks): about -1 .. 1
`warp` pushes the coordinates about by three other noises, so the pattern bends (marble, flowing organic shapes); it is in feature sizes, 1 bends it a lot.
The billow, ridged and cellular kinds are laid over about -1 .. 1.  E.g. an organic surface texture:
part - 0.3 * noise_field(4)

### `normal_field(shape)`

The unit surface normal of a shape (pointing out of it), as three
fields (nx, ny, nz); defined everywhere, meaningful near the surface

### `normalize(field, lo, hi)`

Maps [lo, hi] to [0, 1] (clamped)

### `offset_by(shape, distance)`

Offsets a shape by a distance -- which may be a field, e.g. grow a
part by up to 2 mm with noise: offset_by(part, 2 * noise_field(10, 3))

### `offset_exact(shape, distance, bounds=None)`

A uniform offset of any shape: grows it by `distance` mm everywhere
(shrinks it for a negative distance), measured along true normals,
so edges and corners get round, not stretched.  The distance is a number or a field (an offset that
is more here than there).  The distance to the shape is read from its field (see exact_distance) as far out as the offset reaches.

### `polar_field(center=(0, 0, 0), axis='z')`

Angle from an axis through `center`, in radians (0..pi): 0 along the
axis, pi/2 at its equator (spherical coordinates)

### `power_field(base, *exponents)`

The first field to the power of the next: (a ** b) ** ... at every point (NaN where a negative value meets a
fractional power)

### `radial_field(center=(0, 0, 0), axis='z')`

Distance from an axis through `center` (cylindrical radius, mm); the centre's coordinates may be fields

### `ramp(field, input_range, output_range, clamped=True)`

Linear map of a field: input_range=(a, b) -> output_range=(va, vb); each end is a number or a field (a ramp
that starts and ends where other fields say).  Clamped by default (values beyond the input range hold the end
values), e.g. ramp(z_field(), (0, 50), (2, 0.5)) is 2 at z = 0,
falling to 0.5 at z = 50 and above.

### `remap_field(field, input_range, output_range, clamped=True)`

Same as ramp()

### `render_mesh(shape, region, res)`

The library's mesh of a shape over a region (a libfive_region_t) at `res` samples per mm: the
pointer libfive_tree_render_mesh gives (free it with libfive_mesh_delete), or None. A shape with
var()s is meshed with the numbers they have in the script.

### `repeat(shape, spacing, center=(0, 0, 0))`

Repeats a shape infinitely on a grid.  spacing: a number or (sx, sy,
sz), each a number or a field (the repeat is closer here and wider there); 0 along an axis leaves that axis alone.  The shape should fit
inside one grid cell centred on `center`.

### `repeat_polar(shape, count, center=(0, 0), axis='z')`

Repeats a shape `count` times around the z axis; the shape should
lie in the wedge around the +x direction

### `round_edges(shape, radius, bounds=None)`

Rounds every convex (outside) edge and corner of a shape with the
given radius (a number or a field), and removes what is thinner than the ball: a ball of that radius rolls in the material, and the shape is everything
it reaches.  It is made from the shape's own field (see exact_distance and distance_field.py): the centres of the ball are where the field is
`-radius`, and the surface of the result is `radius` from them.  Exact for the outside edge of two flat faces at any angle and for the corner of three
(the ball's centre is where the planes of the faces meet), for a cylinder and a sphere.

### `sample_grid(field, lower, upper, n=20)`

Values on an n x n x n grid of cell centres over a box (a flat list,
x fastest) together with the points

### `shell_centered(shape, thickness)`

A shell straddling the surface (half inside, half outside)

### `shell_exact(shape, thickness, side='inside', bounds=None)`

A hollow shell of uniform thickness (true distance), side = 'inside',
'outside' or 'center'.  The thickness is a number or a field.

### `shell_inside(shape, thickness)`

A hollow shell: the part of `shape` within `thickness` of its surface

### `shell_outside(shape, thickness)`

A skin grown outwards from the surface by `thickness`

### `signed_distance(shape)`

A shape's signed distance field (negative inside) -- the shape
itself, named for readability

### `smooth(shape, radius, steps=1)`

Smooths the surface of a body without thickening it: bumps, dents, ridges and stair-steps smaller than
about `radius` mm are smoothed away, edges and corners are eased, and a flat or gently curved face stays
where it is (unlike offset() or thicken(), which move or grow the surface).  The field of the body is
averaged over the points a `radius` away on all six sides -- the smoothing of a mesh's Laplacian, done on the
field -- and `steps` of those make the field of the smoothed body: more steps smooth further (the reach
grows as the square root of the number of steps).  The radius is a number or a field (smoothed more where
the field is large, not at all where it is 0).  Like any smoothing it eases convex features slightly
inwards and concave ones slightly outwards; the body as a whole does not grow.

The result is a field like any other, a weighted sum of copies of the body's own field moved by whole
radii (6 copies for one step, 19 for two, 44 for three, 85 for four; more steps than four are four at a
larger radius, which smooths as far), so nothing is measured or meshed here: the surface is found when it
is drawn, and the cost is that of the field times the copies.  The body's field should be about a
distance (the primitives and what is made of them are; a part that carries its exact distance is replaced by
it, as offset() does), because a field that rises faster smooths by as much more.

### `smooth_difference(a, b, radius)`

a minus b, with a rounded blend along the cut

### `smooth_intersection(a, b, radius)`

Intersection with a rounded blend

### `smooth_union(a, b, radius)`

Union with a rounded blend of the given radius where the shapes meet (a number, or a field: a blend that
is round here and sharp there)

### `smoothstep(field, edge0, edge1)`

0 below edge0, 1 above edge1, a smooth S-curve between

### `sqrt_field(field)`

The square root of a field at every point (NaN where it is negative)

### `square_field(field)`

A field times itself at every point

### `step_field(field, edge)`

0 below the edge, 1 above (a sharp step; see smoothstep)

### `subtract_fields(first, *others)`

The first field minus the others: a - b - ... at every point

### `sum_fields(*fields)`

Sum of several fields

### `texture(body, pattern='grit', depth=0.1, size=1.0, region=None, fade=None, seed=1, axis='z', radius=None, side='both')`

A texture on the surface of `body`: a pattern of small bumps and pits laid over it (sandpaper, a grip, a leather grain ...), on all of it or only where `region` says.
`pattern` is one of 'grit' (sandpaper, sandblast), 'stipple' (round pits), 'leather' (grooves between cells, with a fine grain), 'ribs' (grooves across `axis`),
'dimples' (a 3D egg carton) and 'knurl' (diamonds round `axis`; give the `radius` it goes round), or a field of your own, about -1 .. 1.
`size` is the grain or the pitch (mm) and `depth` the height from a pit to a bump (mm); `side` 'both' puts the bumps outside and the pits inside the surface,
'in' only cuts into it (the part stays inside its size), 'out' only adds to it.  `region`: a surface picked on the body (select_surface), or a body that holds the
places to texture; the texture fades out over `fade` mm (the size, by default) so that no step is left at its edge.  A texture is made of the field of the body: the
render has to be fine enough to show it -- a resolution of about four samples to the size.  E.g. a rough grip on the top face:
top = select_surface(part, seed=(0, 0, 10)); gripped = texture(part, 'grit', depth=0.2, size=0.6, region=top)

### `thicken(field, thickness)`

A solid wall of the given thickness centred on a field's zero
surface (e.g. a plane, a TPMS surface, a shape's skin); the
thickness may be a field

### `twist_z(shape, degrees_per_mm, center=(0, 0))`

Twists a shape about the z axis; the rate may be a field

### `union_all(shapes, blend=0)`

Union of many shapes (optionally blended)

### `volume_of(shape, lower=None, upper=None, resolution=None)`

Volume of a solid (mm^3), by sampling a grid over its bounds
(resolution: samples per mm; by default ~100 along the longest side)

### `wave(axis='x', period=10.0, amplitude=1.0, phase=0.0)`

A sine wave along an axis (or a field): amplitude * sin(2 pi s / period + phase)

### `x_field()`

The x coordinate as a field (mm)

### `y_field()`

The y coordinate as a field (mm)

### `z_field()`

The z coordinate as a field (mm)

## Regressions and data

Regressions: turn measured data into fields.

A regression is fitted to (x, y) data and can then be applied to numbers or
to any field -- typically a distance field -- to get a field that drives an
operation (a shell's thickness, an offset, a blend):

    from fieldes import *

    ball = sphere(30)
    # how far the surface swells at several heights
    swell_of_z = fit([(-30, 0.0), (-10, 1.5), (10, 2.5), (30, 0.5)], model='poly', degree=2)
    print(swell_of_z)                  # equation and goodness of fit (R^2)
    swell = swell_of_z(z_field())      # a field
    pear = offset_by(ball, swell)

Models (fit(..., model=...)):
    'linear'        a + b x
    'poly'          polynomial of the given degree (default 2)
    'exp'           a e^(b x)                 (y > 0)
    'exp_offset'    a e^(b x) + c
    'power'         a x^b                     (x > 0, y > 0)
    'log'           a + b ln x                (x > 0)
    'logistic'      c + L / (1 + e^(-k (x - x0)))
    'interp'        straight lines through the points
    'spline'        smooth natural cubic spline through the points
    'pchip'         smooth, shape-preserving cubic through the points
                    (no overshoot between points -- good for thicknesses)
    'auto'          the best of the parametric models (by corrected AIC)

By default a regression holds its end values outside the data range
(clamp=True), so a field never runs off to unphysical values; pass
clamp=False to extrapolate.

Also:
    fit_csv(path, x_column, y_column, ...)      fit data from a CSV file
    fit_field(points, values, degree)           3D polynomial field from
                                                scattered samples (x, y, z) -> v
    interpolate_field(points, values)           a field through scattered
                                                samples (radial basis functions)

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.

### `FieldFit`

A fitted 3D field: .field (the Shape), .r2, .rmse, and call it with a
point for its value.

### `Regression`

A fitted regression.  Call it on a number (-> number) or on a field
(-> field): reg(3.0), reg(depth_below(part)).

Attributes: model, params, r2 (coefficient of determination), rmse,
equation (text), domain (min and max x of the data), clamp.

#### `Regression.on(self, field)`

The regression applied to a field (same as calling it)

#### `Regression.residuals(self)`

The data's y minus the fitted curve at each x (what the fit leaves unexplained)

#### `Regression.table(self, n=11)`

(x, y) samples of the fitted curve across the data range

### `fit(x, y=None, model='poly', degree=2, clamp=True)`

Fits a regression to data and returns a Regression, which can be
called on numbers or fields.

Data: fit([(x0, y0), (x1, y1), ...]) or fit(xs, ys) or fit({x: y}).
model: 'linear', 'poly' (with degree), 'exp', 'exp_offset', 'power',
'log', 'logistic', 'interp', 'spline', 'pchip' or 'auto'.

### `fit_csv(path, x_column=0, y_column=1, model='poly', degree=2, clamp=True, delimiter=None)`

Fits a regression to two columns of a CSV file.  Columns are given
by index or by header name; rows that aren't numbers are skipped.

### `fit_field(points, values=None, degree=2)`

Least-squares polynomial field in x, y, z through scattered samples,
e.g. measured temperatures or loads at points -> a smooth field.
points: [(x, y, z), ...] with values [v, ...], or [(x, y, z, v), ...].
Returns a FieldFit; its .field is the Shape.

### `interpolate_field(points, values=None, smoothing=0.0, method='rbf', power=2.0)`

A field passing through scattered samples (x, y, z) -> v.
method='rbf': polyharmonic radial basis functions (smooth, exact at
the samples unless smoothing > 0; up to a few hundred points).
method='idw': inverse-distance weighting with the given power
(no solve; bounded by the sample values).

## Surfaces and offsets

Closed-form surfaces: cheap primitives beyond planes, spheres and cylinders.

Each is a handful of arithmetic operations, so it meshes as fast as any
other shape.  The general forms take coefficients; the named ones are for
modeling:

    quadric(coefficients, center, scale)        any surface of degree 2
    extruded_curve(coefficients, direction, origin, scale)
                                                a cubic curve swept straight
    revolved_curve(coefficients, axis, origin, scale)
                                                a cubic curve spun around an axis
    helical_curve(coefficients, lead, axis, origin, offset, scale)
                                                a cubic curve screwed along an axis
    helical_sweep(profile, lead, center)        a cross-section screwed along z:
                                                helical gears, twisted flutes
    helical_revolve(profile, lead, center)      an axial profile screwed around z:
                                                threads, springs, auger flights
    coil_spring(radius, wire_radius, lead, turns, center)
    ellipsoid(radii, center)
    elliptic_cylinder(a, b, center)             along z
    paraboloid(k, center)                       z >= k (x^2 + y^2), opening up
    hyperboloid(a, c, center)                   one sheet, along z
    wave_block(size, amplitude, period, center) a block with a wavy top

Coefficient orders (in coordinates w = (p - origin) / scale):
    quadric:  x^2 y^2 z^2 xy xz yz x y z 1
    curves:   u^3 u^2v uv^2 v^3 u^2 uv v^2 u v 1
      extruded_curve: u, v across the direction (see _frame)
      revolved_curve: u = distance from the axis, v = along the axis
      helical_curve: u, v across the axis, turning with the height
All three return scale * f(w): inside where negative.

### `coil_spring(radius, wire_radius, lead, turns, center=(0, 0, 0))`

A coil spring along z: `turns` turns of round wire (radius
`wire_radius`) around a coil of radius `radius`, rising `lead` per
turn, standing on `center`, its ends cut flat.

### `ellipsoid(radii, center=(0, 0, 0))`

An ellipsoid with semi-axes radii = (a, b, c) along x, y, z, numbers or fields
(distance-like near the surface; exact for a sphere)

### `elliptic_cylinder(a, b, center=(0, 0, 0))`

An infinite cylinder along z with an elliptic section (semi-axes a, b)

### `extruded_curve(coefficients, direction=(0, 0, 1), origin=(0, 0, 0), scale=1)`

A cubic curve g(u, v) = 0 in the plane across `direction`, swept
straight along it (u, v: along the two axes _frame picks)

### `helical_curve(coefficients, lead, axis=(0, 0, 1), origin=(0, 0, 0), offset=(0, 0), scale=1)`

A cubic curve g(u, v) = 0 in the plane across the axis (through
`origin`), turning as it advances along the axis -- one full turn per
`lead` (a negative lead turns the other way): the flank of a helical
gear or a worm, a thread, a coil.  u, v are measured from `offset` in the turned plane.

### `helical_revolve(profile, lead, center=(0, 0, 0))`

Like revolving a profile around the z axis (through `center`), but
advancing `lead` along it per turn (negative: left-handed): a
thread, a coil spring, an auger's flight.  The profile is a 2D shape
in the xy plane: x = distance from the axis, y = height; it must fit
within one lead of height (|y| < lead / 2), since the result repeats
every lead.  Unbounded along z -- cut it to length.

### `helical_sweep(profile, lead, center=(0, 0, 0))`

`profile` (a shape; its cross-section in the xy plane is what counts)
screwed along the z axis through `center`: turned by one full turn
per `lead` of height (negative: the other way).  A gear outline gives
a helical gear, a drill's outline its twisted flutes (for threads and
springs, whose profile is drawn through the axis: helical_revolve).
Unbounded along z -- cut it to length, e.g. with extrude.  Kept
close to a distance by dividing out the twist's stretching.

### `hyperboloid(a, c, center=(0, 0, 0))`

One-sheet hyperboloid along z: (x^2 + y^2) / a^2 - z^2 / c^2 = 1,
waist radius a (the inside is the part around the axis)

### `paraboloid(k, center=(0, 0, 0))`

The inside of z = k (x^2 + y^2) (opening up from its vertex at center)

### `quadric(coefficients, center=(0, 0, 0), scale=1)`

Any surface of degree 2: ellipsoids, elliptic / parabolic /
hyperbolic cylinders, cones, paraboloids, hyperboloids.
coefficients: x^2 y^2 z^2 xy xz yz x y z 1, in w = (p - center) / scale

### `revolved_curve(coefficients, axis=(0, 0, 1), origin=(0, 0, 0), scale=1)`

A cubic curve g(r, h) = 0 (r: distance from the axis, h: along it,
from `origin`) spun around the axis

### `wave_block(size, amplitude, period, center=(0, 0, 0))`

A block (size = (sx, sy, sz)) whose top is a wave:
z_top = sz / 2 + amplitude sin(2 pi x / period) sin(2 pi y / period)

## Selecting surfaces

Selecting a surface: the flood fill of a CAD program, as a field.

    from fieldes import *

    top = select_surface(part, seed=(12.5, 40.0, -3.0), angle=10)
    top                                       # displayed: the part's surface, only the patch of it, lit up

`select_surface` picks the patch of the part's surface around `seed` (a point on or near it) by walking over the
surface: from the seed, in small steps along it, as long as the surface stays within `angle` degrees -- with
mode='flat' (the default) of the way it faced at the seed (a flat face, or a gently curved one); with mode='smooth' the
surface may turn at most `angle` degrees within 10 mm of the walk -- a limit on how tightly it bends: a cylinder, a fillet or
a gently rounded skin is followed, a tight bend (the toe of a shoe, a small round) or a sharp edge stops it.  `radius` stops
it that far from the seed.

It is made from the part's FIELD alone -- its value and its gradient, which is the surface normal: a step is carried
onto the surface where the field is zero, and the angle is the angle of the gradients.  No mesh of the part is made or
read, so it does the same on any shape however it was made (a mesh, a CSG model), and a thin wall is no harder than a thick one: the walk
follows the surface, not the space, and finds no surface to step onto past an edge.

What comes back is a SURFACE -- the patch of the part's surface, nothing thicker -- as a field, like everything else here.
It is a region you can show on the part, combine with other shapes, or give to an operation that works on a part of a
surface (`texture(part, region=top)`).

In FielDes, right-click a surface in the viewport: the menu holds the mode, the angle and the radius, and
writes the `select_surface(...)` line into the script under the part, like everything else the program does.

`surface_from_bodies` picks a surface by other bodies instead of by a place: the surface of the FIRST body, where it meets the
bodies that follow.

    plate_holes = surface_from_bodies(plate, bolt_1, bolt_2)      # the walls of the holes the two bolts sit in
    skin = surface_from_bodies(plate)                             # no other body: the whole surface of the plate

It is a surface like the one `select_surface` makes -- a region of a surface --
and it too is made from the fields alone: the first body's surface is where its field is zero, and "meets" is a number, the
distance of that surface from the other bodies (their field), so no mesh is made and a body that is dragged or has var()
numbers moves the selection with it.  In FielDes: select several models in the model tree (Ctrl or Shift click), right-click
one, Operations > Surfaces > surface_from_bodies: the first selected is the body, the others are what it is met by.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.

### `BodiesSurface`

The surface of a body where it meets other bodies (see surface_from_bodies): a surface, with the attributes of a
SurfaceSelection (.shape the first body, .patch, .whole, .surface, .cover, .spacing) and .others (the bodies that
select it, a list: empty for the whole surface), .tolerance

### `SurfaceSelection`

A patch of a surface (see select_surface): a surface.
.shape (what it was picked on), .surface (the patch as a field: the height above it, zero on it), .seed, .angle, .mode, .samples (how many points of the surface the
walk took), .spacing (how far apart they are), .patch (the distance to the patch's surface, a field: zero on it,
to within `.cover`), .whole (the distance to the whole surface, a field: the shape's own value, |f|, which is the
distance where the shape's field is one -- as the field of an imported part or a mesh is; it equals .patch where the
nearest point of the surface is in the patch), .cover (how far the surface of the patch can be from a sample: the
patch and the whole differ by less than that where the nearest surface is in the patch)

### `select_surface(shape, seed, angle=15.0, mode='flat', radius=None, resolution=None, bounds=None)`

The patch of the surface of `shape` around the point `seed`, found by a flood fill over the surface made from the
shape's field (see the module): a surface.

seed        a point on (or near) the surface: (x, y, z)
angle       degrees: with mode='flat' how far from the way the seed's surface faces it may face, with
            mode='smooth' how much it may turn within 10 mm of the surface (how tightly it may bend)
mode        'flat' (a face, flat or gently curved) or 'smooth' (round faces: a bend tighter than `angle` per 10 mm
            stops it, and so does a sharp edge)
radius     mm: stop this far from the seed (default: no limit)
resolution  steps per mm along the surface (default: about 150 along the longest side, at least 0.1): a finer one
            follows smaller faces and places the edge of the patch more exactly, and costs more (the walk takes a
            sample for every step of the surface it reaches)
bounds      ((x0, y0, z0), (x1, y1, z1)) of the shape, if it cannot be found

Returns a SurfaceSelection: a shape (so it is shown, hidden, deleted like any), usable as a region:
texture(part, region=selection).

### `surface_from_bodies(body, *others, tolerance=None, bounds=None)`

The surface of `body` where it meets `others`, the bodies that follow: the parts of its surface that intersect them (that
touch them or run through them), as a surface.  With no other body, the whole surface of `body`.

    holes = surface_from_bodies(plate, bolt_1, bolt_2)   # the plate's surface where the bolts are
    skin = surface_from_bodies(plate)                    # all of it

body        the body whose surface is selected (a part, an imported part, any shape)
others      the bodies that choose where: a point of the surface of `body` is selected when it is inside one of
            them or within `tolerance` of one (several can be given, or a list)
tolerance   mm: how close a body must come to the surface to count as meeting it (default: half a percent of the
            size of `body`) -- bodies that touch at a face, or that sit in a hole with a little play, meet; a gap
            wider than this is a gap
bounds      ((x0, y0, z0), (x1, y1, z1)) of `body`, if it cannot be found

It is made from the fields alone, like everything: the surface of `body` is where its field is zero, and the distance of
a point from the others is their field.  No mesh is made, and a body that moves (a var() number, a drag) moves
the selection.  The selection is a thin layer along the surface, a hundredth of the body thick at most -- not a setting: a
surface has no thickness -- the way select_surface makes it.  The patch is cut by the others the way a box cuts
it: where one ends, the selection ends (it follows no face to its edges).  What comes back is a surface, shown
lit up on the body, and a region (`texture(part, region=selection)`).  If the bodies do not meet, nothing is selected (a note says so when their boxes do not
even touch).

## Telling fields from numbers

Numbers and fields in the same place.

Anything the library takes as a number takes a FIELD as well (a Shape: a value at every point of space -- a distance, a ramp
of one, noise ...), as in nTop.  A function that can do arithmetic with what it is given needs nothing;
the few places that must ask a question of a number (is it positive? is it zero?) use these.  A number stays a number, so
nothing is slower for a plain value; a field is worked with as the tree it is.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.

### `highest(*values)`

The largest of numbers and fields: a number when all are numbers, else a field

### `is_field(v)`

Whether v is a field (a Shape) and not a plain number

### `lowest(*values)`

The smallest of numbers and fields: a number when all are numbers, else a field

### `nonzero(v)`

v itself when it is a field or a nonzero number, else None -- for a size that "0" turns off

### `number_or_field(v, what='a value')`

v as a float, or kept as the field it is; anything else is a TypeError that says what was expected

### `positive(v)`

A number above zero -- or a field, which is not known to be anything else

### `present(v)`

A value was given and it is not zero (a field is taken to be something)

### `returns_body(fn)`

A function that makes a body out of what it is given, which may be a field: what it returns is not of the kind
'field' even when it was made from one (a wall round a sheet, a shell)

### `returns_field(fn)`

A function that makes a field (not a body): what it returns is of the kind 'field', which the model tree shows
with a field's icon, and displayed it has an icon in the viewport that opens the field viewer (a plane coloured by it)

## The shape class

Python library of FielDes, built on the libfive CAD kernel
Copyright (C) 2021  Matt Keeter

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.

### `Shape`

*(no description yet)*

#### `Shape.Shape(ptr)`

*(no description yet)*

#### `Shape.X()`

*(no description yet)*

#### `Shape.Y()`

*(no description yet)*

#### `Shape.Z()`

*(no description yet)*

#### `Shape.abs(self)`

*(no description yet)*

#### `Shape.acos(self)`

*(no description yet)*

#### `Shape.asin(self)`

*(no description yet)*

#### `Shape.atan(self)`

*(no description yet)*

#### `Shape.call(self, fn, *args, **kwargs)`

Calls the given function with self as the first argument.
This is convenient to chain transforms without deep call trees.

#### `Shape.cos(self)`

*(no description yet)*

#### `Shape.exp(self)`

*(no description yet)*

#### `Shape.get_mesh(self, xyz_min=(-10, -10, -10), xyz_max=(10, 10, 10), resolution=10, algorithm='dc')`

Converts this Shape into a mesh, and returns that mesh in
    the form of a face-vertex mesh.

Options are the same as in save_stl(). `algorithm` selects the
meshing algorithm: 'dc' (dual contouring, default, fastest),
'simplex', or 'hybrid'. The latter two are slower but more
robust for oracle shapes (an imported mesh's distance), where dual contouring
has been found to fragment meshes even when the underlying
field is provably correct at every queried point.

Returns:
verts - List of (x, y, z) vertices
tris - List of (a, b, c) indices into verts

#### `Shape.lock(self)`

*(no description yet)*

#### `Shape.log(self)`

*(no description yet)*

#### `Shape.new(op, *args)`

*(no description yet)*

#### `Shape.optimized(self)`

*(no description yet)*

#### `Shape.partial(self, axis, oracle_step=0.0, max_call_depth=1)`

The partial derivative of this field with respect to x (axis 0), y (1) or z (2), as a field of its own: the symbolic derivative, by
the rules of calculus -- not a difference of two calls, whose intervals over a cell of the renderer's are as many times too wide as
the cell is wider than the step (a field built from such a gradient makes the renderer refine a whole band round the surface).
A native field inside (a mesh's distance, noise) has no formula: with `oracle_step` above 0 its partial is the central difference over
that step; without it, None is returned.  None too for a field whose calls are nested deeper than `max_call_depth` (default 1: calls of plain
fields): the derivative of a call is three calls of partials, and costs several times what the field does for every level of nesting -- a
field made from the gradient of another, a Newton walk, the result of a remedy that was made from remedies.  Its gradient is read by differences.

#### `Shape.remap(self, x_, y_, z_)`

Performs the remapping f(x_, y_, z_)

#### `Shape.save_stl(self, filename, xyz_min=(-10, -10, -10), xyz_max=(10, 10, 10), resolution=10, quality=8)`

Converts this Shape into a mesh and saves it as an STL file.

xyz_min/max are three-element lists of corner positions
resolution is the reciprocal of minimum feature size
    (larger values = higher resolution = slower)
quality is the negative order of magnitude of maximum error

#### `Shape.sin(self)`

*(no description yet)*

#### `Shape.sqrt(self)`

*(no description yet)*

#### `Shape.square(self)`

*(no description yet)*

#### `Shape.tan(self)`

*(no description yet)*

#### `Shape.var()`

*(no description yet)*

#### `Shape.with_constant_vars(self)`

*(no description yet)*

#### `Shape.wrap(t)`

Ensures that the input argument is a Shape, converting constants

### `field_shape(ptr)`

A field made from the tree `ptr`: a FIELD, not a body -- a value at
every point of space, which is not drawn, is not a part, and has an icon (that opens the field viewer) when it is displayed

### `shape(f)`

Decorator which converts a target function into a Shape

## Progress of a long step

A script run's progress, for FielDes's progress bar (see run_progress.hpp).

The runner (runner.py) says which top-level statement runs; the operations
inside one count how far they are: top-level loops (the runner counts their
items), loading a cached import (its tree files), and progress() for your
own long computations.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.

### `begin(name, shown=None)`

shown: the name the bar shows (default: name)

### `counted(items, name='item')`

Yields items, counting them as the progress of the current step (or
of the operation it runs in); what runs for one item counts within
that item's share.  Items with no len(): counted, but how far
along isn't known.

### `end()`

*(no description yet)*

### `end_to(depth)`

Ends the operations begun deeper than depth (left open by a
progress() call, or by an error)

### `progress(fraction, text='')`

Says how far a long computation of yours is, 0..1, for the progress
bar (text: what it is doing).  Call it as often as you like, e.g.
progress(i / n, 'smoothing') in a loop; it counts within whatever
runs it (a loop's item, a step of the script).

### `report(fraction, detail='')`

*(no description yet)*

### `span(a, b)`

*(no description yet)*

### `task(name)`

with task('meshing'): ... report(f) ...  -- an operation that counts
how far it is, 0..1 (report(f)); one begun inside it counts within the share
span(a, b) gave it

## Caching

Content-keyed caches for the constructions that cost real time.

A script runs again on every edit.  Most of what it builds is a lazy expression
that costs nothing until it is evaluated, but a few constructions do real work
when they are called: meshing a shape and building the search structure of an
exact distance field, importing a mesh file, measuring
a volume.  Their results are remembered by *what they were built from* -- the
shape's expression (not its identity), the numbers, the file's path, size and
modification time -- so running the script again, or moving a slider that does
not touch them, asks nothing twice.  Change the shape, a number or the file and
the key differs: the new result is built and the old one stays until it is the
one used least.

    cache_info()      what is held: {name: (entries, hits, misses)}
    clear_caches()    forget everything (to measure, or to free the memory)

Nothing here approximates: a hit returns the very object a miss built.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.

### `Uncacheable`

A value with no content key

### `cache_for(name, limit=8)`

The named in-memory cache (made on first use) holding at most `limit` entries, least recently used out first

### `cache_info()`

What the content caches hold: {name: (entries, hits, misses)}

### `clear_caches()`

Forgets everything the content caches hold

### `content_cached(name, limit=8, copy_result=False)`

A decorator: the function's results are remembered by the content of its arguments.
copy_result: hand out a copy of a mutable result (a dict) each time

### `is_local(key)`

Whether a problem key holds a part that only this session can recognise (nothing is kept under it for another)

### `problem_key(kind, **parts)`

A key of a whole problem -- a computation made of several inputs: what it is made of, each part by its
content -- or None when some part has no content key (then nothing is remembered)

### `shape_key(shape)`

An exact key of a shape's expression: the same expression built again -- a script run again -- has
the same key, and a different one does not (a constant differing in the seventh digit, another
imported mesh, another data field: all different).  It is the library's structural hash of the
tree, not its printed text.  A var() of the script is its number there (the key is then the same in every
session, and another when the number is another); a tree with anything else no run could recognise -- a
variable of its own, an oracle with no key of its own -- gets a key that is good in this session only
('local': nothing is kept under it for another session).  (Raises Uncacheable when the library has no
such key.)

### `value_key(v)`

A hashable key for an argument, by its content: numbers (every bit), text, sequences, shapes (by
their expression), and the library's own small objects (by their
fields).  Raises Uncacheable for anything else

## Keeping rendered meshes (render cache)

The render cache: keep what FielDes meshes, so a shape that has not changed is on screen at once.

    part = difference(box((0, 0, 0), (40, 30, 10)), sphere(8))
    part                            # its mesh is kept: nothing to write
    part = render_cache(part, False)    # ... unless you opt out (the model tree's cache button writes this line)

Meshing is the slow part of showing a shape.  Every shape's finished mesh is saved (in FielDes's cache
folder, outside your project) once it has taken a while to make, and read back when the same shape is
shown again -- the next time you open the script, or after you changed the script and changed it back --
instead of being meshed again.  When anything about the math changes -- an operation, a number, a
var() you dragged, an imported file, the render region, the resolution -- the shape is not the same
one any more: it is meshed again, shown as usual, and the new mesh is kept.

It is ON unless you turn it off: click the cache button on a row of the model tree (or write
`part = render_cache(part, False)`) to turn it off for that shape; click again (or delete the line) for
the default.  `part = render_cache(part)` says the default aloud and keeps the mesh however quickly it was
made.  The line is the whole setting: it is saved with the script and nothing else about the script
changes.  The shape itself is not touched.

A shape is kept when everything it is made of can be recognised from one run to the next: nodes,
numbers, var()s, imported meshes and parts, fields.

The kept meshes are deleted oldest first when they fill more than 4 GB (the environment variable
FIELDES_RENDER_CACHE_MB sets that); Settings > Clear the caches deletes them all (and the files of the field cache).

Every field a script builds with `name = <expression>` is kept the same way -- by the statement's text, the exact
content of what it reads, the var() numbers and the code that builds it -- so a texture laid over a part is not laid
over again when the script is run again, also after FielDes was closed (when every part of the field can be saved).
FIELDES_FIELD_CACHE_DIR moves the files; the details are in caching-and-performance.md.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.

### `render_cache(shape, on=True)`

`shape`, with its finished mesh kept on disk: shown from there when the same shape is rendered
again (see the module).  Every shape is kept by default; `render_cache(shape, False)` opts it out, and
`render_cache(shape)` keeps it however quickly it was meshed.  Returns the shape itself in every
other way: it keeps its bounds, handles, colours and exact regions.

Write it as the last line of a shape's definition, after gizmo() and handles():

    part = render_cache(part)

(FielDes's model tree has a button for it on every shape.)

### `render_cache_key(shape)`

The key the render cache keeps `shape`'s mesh by, as text -- the same in every run of the program for the
same math, another one when anything about the math changes (an operation, a number, a var() with the
value it has now, an imported file) -- or None when the shape cannot be kept: it depends on something no
other run could recognise.  (The region, resolution and quality it is meshed at are
part of the key the application uses, which is made of this and them.)

## A resolution of its own for one body

A resolution of its own for one body.

The viewport meshes the whole scene at one resolution (view.set_resolution): fine enough for the finest thing in it, which is
more than the rest needs.  `custom_resolution(body, resolution)` gives ONE body a resolution of its own, in samples per mm,
whatever the scene's is: a part that is intricate is drawn fine and the rest of the scene stays coarse and quick -- or a part
that is big and plain is drawn coarser than the scene.

    from fieldes import *

    view.set_resolution(2)                        # the scene: 2 samples per mm
    gear = custom_resolution(gear, 8)             # ... except the gear, drawn at 8
    gear                                          # (it is shown by the line that names it, as always)

The body is meshed on its own, over a cube round it, at that resolution; the number is the resolution, not a scale of the scene's,
so it stays what it is when the scene's resolution is changed.  Nothing is drawn outside the region of the scene (view.set_bounds), as
for every shape: a body that reaches out of it is drawn at its own resolution inside it.  It changes how the body is DRAWN, not what it
is: a boolean or an export of it is the same.

The finest a body can be drawn is 2000 samples along its longest side (a longer one would be hundreds of millions of cells): a
resolution above that is not an error, the body is drawn at the finest there is, and the model tree's row says what is used
(`resolution 8 -> 7.6`).

In FielDes, right-click a body and choose "Custom resolution": the line is written under its definition, and the number is a field
under the body in the model tree (type in it; the bin takes the line away).

### `custom_resolution(shape, resolution, bounds=None)`

`shape` drawn at a resolution of its own: `resolution` samples per mm, whatever the scene's resolution is (see the module).

shape       a body
resolution  samples per mm (a number above 0); 2 draws features of half a millimetre, 10 of a tenth
bounds      ((x0, y0, z0), (x1, y1, z1)) of the body, if its extent cannot be found

Returns the body itself in every other way; only the way it is meshed for the viewport is changed.

## FielDes apps: the inputs of a script

FielDes apps: a script that people who never open the editor can run.

An engineer writes the script once and declares what the person who runs it may choose -- a radius, a model file, where to save the
result.  FielDes shows those inputs as a form (a window of its own, with a Run button, a log and the files that were made), so an
artist or a designer opens the app, fills in the form and presses Run.  The script is an ordinary FielDes script:

    from fieldes import *

    app.title('Rock maker', 'Roughens a model into a rock and saves it as a mesh')
    roughness = app.number('Roughness', 2, min=0, max=10, unit='mm')
    look = app.choice('Look', ['smooth', 'jagged'])
    model = app.file('Model', filter='Meshes (*.obj *.stl *.glb)')
    target = app.save_as('Export path', 'rock.glb')

    part = import_model(model)
    ...
    export_mesh(part, target)

In the editor the inputs are just their defaults: `app.number('Radius', 5)` is 5, so the script runs as it always did, and the script is
tried and changed there.  File > Export as app... bundles it with the custom blocks it uses and the files it needs into one
`.fieldesapp` file; opening that file (a double click) shows the form.  The same file runs without a window:

    FielDes run bracket.fieldesapp --Radius 7 --Material aluminium

Every input is written with a plain value -- a number, a text, a list -- at the top of the script, because the form is read from the
text of the script (it is there before the script has run).  The name of an input is what the form shows; `--Radius`, `--radius` and
`--RADIUS` are the same option, and so are `Model path`, `ModelPath` and `model_path`.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.

### `app.asset(path)`

A file that is bundled into the app: `model = import_model(app.asset('models/rock.obj'))`.  A relative path is read from
the folder of the script (and is the same inside the app); File > Export as app... copies the file in.  Returns the full path.

### `app.choice(name, options, default=None, help='')`

One of a few texts: `material = app.choice('Material', ['steel', 'aluminium'])`.  `default` is the first one when it is left out.

### `app.file(name, default='', filter='', help='')`

A file the person picks (it must exist when the app runs), returned as its full path:

    model = app.file('Model', filter='Meshes (*.obj *.stl *.glb);;All files (*)')

`default` can be a file that comes with the app, `app.asset('models/rock.obj')`.  The runner can run the app again by itself
when this file changes (Watch).

### `app.flag(name, default=False, help='')`

A yes / no choice (a check box).  On the command line: `--Hollow`, `--no-Hollow` or `--Hollow yes`.

### `app.folder(name, default='', help='')`

A folder the person picks (a relative path is made under the Documents folder), returned as its full path

### `app.in_app()`

True when the script is run as an app (by the app window or `FielDes run`), False in the editor.  Write files only when it is: an
edit of the script runs it again and again in the editor, and it should only show the result there:

    if app.in_app():
        export_mesh(part, target)

### `app.number(name, default=0, min=None, max=None, step=None, unit='', help='')`

A number the person chooses: a whole number when `default` is one (and min, max, step are), else a decimal.

    radius = app.number('Radius', 5, min=1, max=20, unit='mm')

`unit` is shown after the field, `help` under it.  A value outside min..max is refused before the script runs.

### `app.output(path, label='')`

A file the script makes that the runner lists under *Outputs* when it is there afterwards (a report, a drawing):

    report = app.output('report.txt')

A relative path means the Documents folder (or the folder the command was started in).  Returns the full path.

### `app.running()`

True when the person pressed Run (or the app runs from the command line): the work is to be done.  False while the script only makes the
picture of the app's viewport -- when the app is opened, an input changes, a model was dragged -- and in the editor.  Put what takes
long, and what writes files, under it:

    if app.running():
        export_mesh(part, target)

### `app.save_as(name, default='result', filter='', help='')`

Where the result is saved: a path the person can change, returned as a full path (a relative one means the Documents folder, or
the folder the command was started in).  The runner lists it under *Outputs* once the script has written it:

    export_mesh(part, app.save_as('Export path', 'bracket.stl'))

### `app.text(name, default='', help='')`

A text the person types (a name, a label to engrave).  Returns it as it is.

### `app.title(text, description='', version='')`

The name of the app, what it does, and its version: shown at the top of its window and in the list of recent apps.
Written once, with plain texts, at the top of the script.

### `app.viewport(models=None, *more, labels=True)`

The app window shows a viewport: a picture of what you give it, that the person can look around in and -- the models that are not
locked -- drag by their gizmo and their handles.  Write it as a statement of its own:

    app.viewport({'Bracket': part, 'Load point': pull}, support, load)

`models` is a dict of name -> model (the name is drawn over the model), or a list of
models (no names); the models after it (`more`) are shown without a name.  Whatever a model has numbers to drag -- `gizmo()`, `handles()`, `var()` -- the person can drag,
unless it is `lock()`ed: click a model to select it and its gizmo shows; there is no model tree and no menu.  A model that is dragged
writes its new numbers into the script the app runs, which runs again for the picture (with app.running() False), and the numbers are
there when Run is pressed.  A point is its dot: always drawn, click it to select it.  A **field** among them has an icon (with its name over it) at the place of the object it
was made from; click the icon and the field is shown on a disc, with a slider for its radius and arrows to move it.

It is a setting of the app: the editor draws nothing for it and the model tree has no row for it -- the models are in the tree as they are,
shown by their eyes; File > Preview as app shows the viewport.  `labels=False` leaves the names out.
