'''
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
'''
import ctypes
import os

from fieldes.ffi import lib, libfive_region_t, libfive_interval_t, libfive_mesh_import_info_t
from fieldes.shape import Shape
from fieldes.stdlib import mesh_import as _mesh
from fieldes.stdlib.content_cache import content_cached
from fieldes.stdlib.fields import _s, _shape_bounds, render_mesh, _vars_key

__all__ = ['import_model', 'tessellate']

_MESH = ('.stl', '.obj', '.ply', '.3mf', '.glb', '.gltf', '.fbx', '.off', '.dxf')
_MESH_LIST = ', '.join(_MESH)


def _kind_of(path):
    return 'mesh' if os.path.splitext(path)[1].lower() in _MESH else None


def _path_of(path, who):
    if not isinstance(path, (str, os.PathLike)):
        raise TypeError('{}: the first argument is the path of the file ({} is a {})'.format(
            who, path, type(path).__name__))
    path = os.fspath(path)
    if not os.path.exists(path):
        raise RuntimeError('{}({!r}): the file does not exist'.format(who, path))
    return os.path.abspath(path)


def import_model(path, units='mm', file_units=None, rev=None):
    ''' Imports a triangle mesh (.stl, .obj, .ply, .3mf, .glb, .gltf, .fbx, .off, .dxf) as a list of one
        (shape, (lower corner, upper corner)), the shape being the exact signed distance to its triangles:

            parts = import_model("rock.obj")
            part, bounds = parts[0]
            view.set_bounds(*roi(parts))

        units       the units of your script ('mm', 'cm', 'm', 'in'...)
        file_units  what the numbers of the file mean ('mm' if it does not say: STL, OBJ, PLY and OFF do not; 3MF, FBX and DXF
                    with $INSUNITS do, glTF is metres)
        rev         a number that is part of what an import is kept by: another one imports again ("Reimport" in FielDes) '''
    path = _path_of(path, 'import_model')
    if _kind_of(path) is None:
        raise ValueError('import_model({!r}): not a file it can read; use a mesh ({})'.format(path, _MESH_LIST))
    return [_import_mesh(path, units, file_units, rev)]


def tessellate(source, units='mm', file_units=None, rev=None, bounds=None, resolution=None):
    ''' The exact surface, as a distance field.  `source` is

        a file          a mesh file: what import_model() makes of it.  Returns [(shape, bounds)] as import_model() does
        a field         any shape: its surface is meshed (`resolution` samples per unit, default about 200 along its
                        longest side; `bounds` = ((x0, y0, z0), (x1, y1, z1)) if they cannot be found) and the result is
                        the exact signed distance to that mesh.  Booleans, blends and warps have fields that are only
                        roughly a distance; after this offsets and shells are uniform.  Returns a shape.  (A feature
                        thinner than the mesh cells falls between its samples: raise `resolution`)
        a list          of (shape, bounds) -- what import_model() returns -- or of shapes: each tessellated

        units, file_units, rev: see import_model() '''
    if isinstance(source, (str, os.PathLike)):
        path = _path_of(source, 'tessellate')
        kind = _kind_of(path)
        if kind is None:
            raise ValueError('tessellate({!r}): not a file it can read; use a mesh ({})'.format(path, _MESH_LIST))
        return [_import_mesh(path, units, file_units, rev)]
    if isinstance(source, (list, tuple)):
        if _is_part(source):                  # (one (shape, bounds))
            return (tessellate(source[0], bounds=source[1], resolution=resolution), source[1])
        return [tessellate(item, bounds=bounds, resolution=resolution) for item in source]
    shape = _s(source)
    if getattr(shape, '_tessellated_import', False):
        return shape                      # (it is the distance to its own triangles already)
    lo, hi = _shape_bounds(shape, bounds)
    size = max(hi[i] - lo[i] for i in range(3)) or 1.0
    res = float(resolution) if resolution else 200.0 / size
    return _tessellate_field(shape, tuple(lo), tuple(hi), res, _vars_key())


def _is_part(item):
    return (isinstance(item, (tuple, list)) and len(item) == 2 and isinstance(item[0], Shape)
            and isinstance(item[1], (tuple, list)) and len(item[1]) == 2)


@content_cached('tessellate', limit=8)
def _tessellate_field(shape, lo, hi, resolution, script_vars):
    ''' The signed distance to the mesh of a field's surface, '''
    size = max(hi[i] - lo[i] for i in range(3)) or 1.0
    pad = 0.03 * size
    region = libfive_region_t(*[libfive_interval_t(a - pad, b + pad) for a, b in zip(lo, hi)])
    mesh_p = render_mesh(shape, region, resolution)
    if not mesh_p:
        raise ValueError('tessellate: the shape could not be meshed')
    try:
        mesh = mesh_p[0]
        if mesh.tri_count == 0:
            raise ValueError('tessellate: the shape has no surface in its bounds')
        verts = ctypes.cast(mesh.verts, ctypes.POINTER(ctypes.c_float))
        tris = ctypes.cast(mesh.tris, ctypes.POINTER(ctypes.c_uint32))
        info = libfive_mesh_import_info_t()
        ptr = lib.libfive_mesh_from_arrays(verts, mesh.vert_count, tris, mesh.tri_count, 1.0, ctypes.byref(info))
    finally:
        lib.libfive_mesh_delete(mesh_p)
    if not ptr:
        raise ValueError('tessellate: ' + lib.libfive_import_mesh_last_message().decode('utf-8', 'replace'))
    out = Shape(ptr)
    out._bounds = (tuple(lo), tuple(hi))
    out._tessellated_import = True
    return out


def _import_mesh(path, units, file_units, rev):
    ''' (shape, bounds) of a mesh file '''
    return _mesh._import_mesh(path, units=units, file_units=file_units, rev=rev)
