'''
Collision meshes: the same field, asked for fewer triangles.

A body that is a field has no "low-poly version" to model by hand or to decimate afterwards: meshing the field again, coarser, gives a rougher copy of the same surface, and the
copy stays where the surface is.  `export_collision` writes that copy beside the model, named the way you choose:

    export_collision(rock, "out/rock.glb", triangles=300)                      # out/rock_collision.glb
    export_collision(rock, "out/rock.glb", triangles=300, naming="godot")      # out/rock-colonly.glb, and its node in the file is called "rock-colonly"

A game engine decides by the name what a mesh is for.  "godot" is the suffix its importer takes for a mesh that is a collision shape and nothing else; it looks at the name of the
node, which the helper sets to the same name (`name=` changes it).  None of this was tried in an engine.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import os

from fieldev.stdlib.gameunits import export_options

__all__ = ['export_collision']

_SUFFIX = {'suffix': '_collision', 'godot': '-colonly'}


def export_collision(part, path, triangles=300, naming='suffix', **options):
    ''' Writes a collision mesh of `part` of at most `triangles` triangles beside `path` and returns its path.  naming: "suffix" (`name_collision.ext`) or "godot" (`name-colonly.ext`).
        The other options are those of `export_mesh` (units, up, bounds, resolution ...); one number is a metre unless `model_unit` says otherwise '''
    from fieldev.stdlib.exporting import export_mesh
    if naming not in _SUFFIX:
        raise ValueError('export_collision: naming is %s, not %r' % (' or '.join(repr(n) for n in _SUFFIX), naming))
    if 'max_triangles' in options:
        raise TypeError('export_collision: the budget is `triangles`, not max_triangles')
    if int(triangles) < 4:
        raise ValueError('export_collision: a budget of %r triangles -- a closed surface has at least four' % (triangles,))
    folder, file = os.path.split(os.fspath(path))
    base, ext = os.path.splitext(file)
    stem = base + _SUFFIX[naming]
    options.setdefault('name', stem)
    return export_mesh(part, os.path.join(folder, stem + ext), max_triangles=int(triangles), **export_options(ext, options))
