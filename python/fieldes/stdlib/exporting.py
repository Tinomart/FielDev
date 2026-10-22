'''
Exporting: a body as a mesh file, a field sampled on a grid.

    export_mesh(part, "part.stl")                   .stl .obj .ply .3mf .glb .gltf .fbx .off .dxf  (see meshfiles.py)
    export_field(field, "noise.vti")                any field sampled on a regular grid: .vti (VTK image data), .csv

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import ctypes
import math
import os
from array import array

from fieldes.ffi import lib, libfive_interval_t, libfive_region_t
from fieldes.shape import Shape
from fieldes.stdlib import meshfiles

__all__ = ['export_mesh', 'export_field']


def _host(name, default=None):
    ''' A setting of the application (the scene's region, resolution, quality), or `default` outside it '''
    try:
        import _fieldes_host as host
        value = getattr(host, name, None)
        return default if value is None else value
    except ImportError:
        return default


def _body_of(x, what):
    ''' The shape an export is about: a shape, or what has one (a callable `shape`, a field it stands for) '''
    if isinstance(x, Shape):
        return x
    shape = getattr(x, 'shape', None)
    if isinstance(shape, Shape):
        return shape
    if callable(shape):
        made = shape()
        if isinstance(made, Shape):
            return made
    as_field = getattr(type(x), '_as_field', None)
    if as_field is not None:
        made = x._as_field()
        if isinstance(made, Shape):
            return made
    raise TypeError('{}: a body (a shape) is exported, not {!r}'.format(what, type(x).__name__))


# ---------------------------------------------------------------------------
# Meshes

def _surface_arrays(shape, bounds, resolution):
    from fieldes.stdlib.fields import _shape_bounds, render_mesh
    lo, hi = _shape_bounds(shape, bounds)
    if resolution is None:
        resolution = _host('__resolution', None)
        if resolution is None:
            size = max(h - l for l, h in zip(lo, hi))
            resolution = max(0.5, min(20.0, 200.0 / max(size, 1e-9)))
    if bounds is None:
        # (the extent of a body is the box its faces lie on: a region that ends exactly on a face has no face inside it -- one cell more all round)
        pad = max(1.0 / resolution, 0.005 * max(h - l for l, h in zip(lo, hi)))
        lo, hi = tuple(l - pad for l in lo), tuple(h + pad for h in hi)
    region = libfive_region_t(*[libfive_interval_t(a, b) for a, b in zip(lo, hi)])
    mesh_p = render_mesh(shape, region, resolution)
    if not mesh_p:
        raise RuntimeError('nothing to export: the shape has no surface inside the region {} .. {}'.format(tuple(lo), tuple(hi)))
    try:
        mesh = mesh_p[0]
        nv, nt = mesh.vert_count, mesh.tri_count
        if not nt:
            raise RuntimeError('nothing to export: the shape has no surface inside the region {} .. {}'.format(tuple(lo), tuple(hi)))
        xyz = array('f')
        xyz.frombytes(ctypes.string_at(ctypes.cast(mesh.verts, ctypes.c_void_p).value, nv * 12))
        tri = array('I')
        tri.frombytes(ctypes.string_at(ctypes.cast(mesh.tris, ctypes.c_void_p).value, nt * 12))
    finally:
        lib.libfive_mesh_delete(mesh_p)
    return xyz, tri


def export_mesh(part, path, bounds=None, resolution=None, name=None, ascii=False):
    ''' Writes the surface of a body as a triangle mesh file, in the format of the file's extension:

            .stl (binary; ascii=True for text), .obj, .ply, .3mf, .glb, .gltf, .fbx (Autodesk FBX, ASCII 7.4: see fbx.py), .off, .dxf (3DFACE)

        part        a body (a shape, or a list of them)
        path        the file to write (a folder that is not there is made)
        bounds      ((x0, y0, z0), (x1, y1, z1)) the region meshed; the body's own extent when it is not given
        resolution  samples per mm of the mesh (the scene's resolution when it is not given: the one of the viewport)
        name        the object's name inside the file (the file's name)
        ascii       STL as text, not binary

        Millimetres in every format that has no unit; the ones that state their unit (3MF, FBX, DXF) say millimetres (a glTF is in metres, Y up, as
        glTF is).  Returns the path. '''
    path = os.fspath(path)
    ext = os.path.splitext(path)[1].lower()
    if ext not in meshfiles.MESH_WRITE_FORMATS:
        raise ValueError('export_mesh({!r}): the mesh formats are {}'.format(path, ', '.join(meshfiles.MESH_WRITE_FORMATS)))
    parts = list(part) if isinstance(part, (list, tuple)) else [part]
    xyz, tri = array('f'), array('I')
    for p in parts:
        body = _body_of(p, 'export_mesh')
        x, t = _surface_arrays(body, bounds, resolution)
        base = len(xyz) // 3
        xyz.extend(x)
        tri.extend(base + i for i in t)
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    meshfiles.write_mesh(path, xyz, tri, name=name, ascii=ascii)
    return path


def _eval_at(shape, xyz, count):
    ''' A field's value at `count` points (flat x, y, z floats) '''
    pts = (ctypes.c_float * (3 * count))(*xyz) if not isinstance(xyz, ctypes.Array) else xyz
    out = (ctypes.c_float * count)()
    known = None
    try:
        from fieldes.app_support import _var_values
        known = _var_values()
    except Exception:
        known = None
    if known is not None and hasattr(lib, 'libfive_tree_eval_points_vars'):
        lib.libfive_tree_eval_points_vars(shape.ptr, pts, count, out, known[0], known[1], known[2])
    else:
        lib.libfive_tree_eval_points(shape.ptr, pts, count, out)
    return list(out)


def export_field(field, path, bounds=None, resolution=None, name='field'):
    ''' Samples a field -- anything that is a Shape -- on a regular grid and writes it:

            .vti   VTK image data (ParaView ...): the values as point data
            .csv   x, y, z, value for every grid point

        bounds      ((x0, y0, z0), (x1, y1, z1)): the box sampled (the extent of the shape that has one: field.bounds, else this is needed)
        resolution  samples per mm (the scene's resolution by default, limited to 2 million points)

        A field is not a mesh: this is the sampling of it that other programs work with, at the resolution asked for.  Returns the path. '''
    from fieldes.stdlib.fields import _shape_bounds
    path = os.fspath(path)
    ext = os.path.splitext(path)[1].lower()
    if ext not in ('.vti', '.csv'):
        raise ValueError('export_field({!r}): the field formats are .vti and .csv'.format(path))
    field = _body_of(field, 'export_field') if not isinstance(field, Shape) else field
    lo, hi = _shape_bounds(field, bounds)
    if resolution is None:
        resolution = _host('__resolution', None) or 2.0
    dims = [max(2, int(math.ceil((hi[i] - lo[i]) * resolution)) + 1) for i in range(3)]
    while dims[0] * dims[1] * dims[2] > 2000000:
        dims = [max(2, int(d * 0.9)) for d in dims]
    step = [(hi[i] - lo[i]) / (dims[i] - 1) for i in range(3)]
    n = dims[0] * dims[1] * dims[2]
    pts = (ctypes.c_float * (3 * n))()
    k = 0
    for iz in range(dims[2]):
        for iy in range(dims[1]):
            for ix in range(dims[0]):
                pts[k], pts[k + 1], pts[k + 2] = lo[0] + ix * step[0], lo[1] + iy * step[1], lo[2] + iz * step[2]
                k += 3
    values = _eval_at(field, pts, n)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    if ext == '.csv':
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write('x,y,z,%s\n' % name)
            for i in range(n):
                f.write('%.7g,%.7g,%.7g,%.7g\n' % (pts[3 * i], pts[3 * i + 1], pts[3 * i + 2], values[i]))
    else:
        with open(path, 'w', encoding='ascii') as f:
            f.write('<?xml version="1.0"?>\n<VTKFile type="ImageData" version="0.1" byte_order="LittleEndian">\n'
                    '<ImageData WholeExtent="0 %d 0 %d 0 %d" Origin="%.9g %.9g %.9g" Spacing="%.9g %.9g %.9g">\n'
                    '<Piece Extent="0 %d 0 %d 0 %d">\n<PointData Scalars="%s">\n<DataArray type="Float32" Name="%s" format="ascii">\n'
                    % (dims[0] - 1, dims[1] - 1, dims[2] - 1, lo[0], lo[1], lo[2], step[0], step[1], step[2],
                       dims[0] - 1, dims[1] - 1, dims[2] - 1, name, name))
            f.write(' '.join('%.7g' % v for v in values))
            f.write('\n</DataArray>\n</PointData>\n</Piece>\n</ImageData>\n</VTKFile>\n')
    return path
