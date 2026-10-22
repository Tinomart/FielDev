'''
Exporting: a body as a mesh file, a field sampled on a grid.

    export_mesh(part, "part.stl")                   .stl .obj .ply .3mf .glb .gltf .fbx .off .dxf  (see meshfiles.py)
    export_mesh(part, "hero.obj", units="m", up="y")    the unit and the up axis of the numbers in a file that has none of its own
    export_mesh(part, "hero.glb", max_triangles=3000)   the finest mesh that is within a budget of triangles
    export_mesh(part, "hero.glb", symmetric="x")        the x >= 0 half, cut exactly at x = 0, and its mirror image: symmetric to the last bit
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
from fieldes.stdlib.materials import Material

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

def _default_resolution(lo, hi, resolution):
    ''' The samples per mm of a mesh: the one asked for, else the scene's, else enough for about 200 samples across the body '''
    if resolution is None:
        resolution = _host('__resolution', None)
        if resolution is None:
            size = max(h - l for l, h in zip(lo, hi))
            resolution = max(0.5, min(20.0, 200.0 / max(size, 1e-9)))
    return resolution


def _surface_arrays(shape, bounds, resolution, half=None):
    ''' The surface of a body as flat vertices (x, y, z ... in mm) and triangles.  `half` = (axis, plane, sign): only the side of that plane which
        `sign` names (+1: the larger coordinates) is meshed, and its mirror image is made of it (see _mirrored) '''
    from fieldes.stdlib.fields import _shape_bounds, render_mesh
    lo, hi = _shape_bounds(shape, bounds)
    resolution = _default_resolution(lo, hi, resolution)
    if bounds is None:
        # (the extent of a body is the box its faces lie on: a region that ends exactly on a face has no face inside it -- one cell more all round)
        pad = max(1.0 / resolution, 0.005 * max(h - l for l, h in zip(lo, hi)))
        lo, hi = tuple(l - pad for l in lo), tuple(h + pad for h in hi)
    lo, hi = list(lo), list(hi)
    if half is not None:
        axis, plane, sign = half
        # (the region reaches two cells across the plane: the cut is made in the mesh, where the surface is, not at the edge of the region)
        if sign > 0:
            lo[axis] = max(lo[axis], plane - 2.0 / resolution)
        else:
            hi[axis] = min(hi[axis], plane + 2.0 / resolution)
        if not lo[axis] < hi[axis]:
            raise RuntimeError('nothing to export: the shape has nothing on the {} side of the plane {} = {}'.format('+' if sign > 0 else '-', 'xyz'[axis], plane))
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
    if half is not None:
        xyz, tri = _mirrored(xyz, tri, axis, plane, sign, 0.25 / resolution)
    return xyz, tri


def _mirrored(xyz, tri, axis, plane, sign, snap):
    ''' The part of a mesh on one side of a plane, cut at the plane, and its mirror image: a mesh that is symmetric to the last bit, and closed where
        the mesh was.  `sign` names the side kept (+1: the larger coordinates).  The vertices within `snap` of the plane are put on it; a triangle that
        crosses it is cut, and the point where an edge crosses is ONE vertex for the triangles on either side of the edge; the vertices on the plane are
        shared by the half and its image, so that the two are joined there. '''
    n = len(xyz) // 3
    height = [0.0] * n              # above the plane on the kept side (0: on it, negative: on the side that is dropped)
    for i in range(n):
        d = sign * (xyz[3 * i + axis] - plane)
        height[i] = 0.0 if abs(d) <= snap else d
    pts = []                        # the vertices kept (x, y, z)
    where = {}                      # vertex of the mesh -> its place in pts
    cut = {}                        # edge of the mesh -> the place in pts of the vertex where it crosses the plane
    flat = set()                    # the places in pts that are on the plane

    def keep(i):
        j = where.get(i)
        if j is None:
            j = where[i] = len(pts)
            p = [xyz[3 * i], xyz[3 * i + 1], xyz[3 * i + 2]]
            if height[i] == 0.0:
                p[axis] = plane
                flat.add(j)
            pts.append(p)
        return j

    def crossing(a, b):
        key = (a, b) if a < b else (b, a)
        j = cut.get(key)
        if j is None:
            ka, kb = key
            t = height[ka] / (height[ka] - height[kb])
            p = [xyz[3 * ka + c] + t * (xyz[3 * kb + c] - xyz[3 * ka + c]) for c in range(3)]
            p[axis] = plane
            j = cut[key] = len(pts)
            flat.add(j)
            pts.append(p)
        return j

    half = []
    for t in range(0, len(tri), 3):
        corners = (tri[t], tri[t + 1], tri[t + 2])
        hs = [height[c] for c in corners]
        if min(hs) >= 0.0:
            if max(hs) > 0.0:       # (a triangle lying in the plane is dropped: the two halves are joined along the edges of the ones that are kept)
                half.append(tuple(keep(c) for c in corners))
        elif max(hs) > 0.0:         # (it crosses the plane: what is on the kept side is a triangle or a quadrilateral)
            polygon = []
            for k in range(3):
                a, b = corners[k], corners[(k + 1) % 3]
                if height[a] >= 0.0:
                    polygon.append(keep(a))
                if height[a] * height[b] < 0.0:
                    polygon.append(crossing(a, b))
            for k in range(1, len(polygon) - 1):
                corner = (polygon[0], polygon[k], polygon[k + 1])
                if len(set(corner)) == 3:
                    half.append(corner)
    if not half:
        raise RuntimeError('nothing to export: the shape has no surface on the {} side of the plane'.format('+' if sign > 0 else '-'))
    out_xyz = array('f')
    for p in pts:
        out_xyz.extend(p)
    image = {}                      # the mirror image of a vertex (a vertex on the plane is its own)
    for j, p in enumerate(pts):
        if j in flat:
            image[j] = j
        else:
            image[j] = len(out_xyz) // 3
            out_xyz.extend(p[c] if c != axis else 2.0 * plane - p[c] for c in range(3))
    out_tri = array('I')
    for a, b, c in half:
        out_tri.extend((a, b, c))
    for a, b, c in half:
        out_tri.extend((image[a], image[c], image[b]))      # (turned over: it is seen from outside the other way round)
    return out_xyz, out_tri


def _meshes(bodies, bounds, resolutions, factor, half):
    ''' The surfaces of the bodies as one mesh, each at its own resolution times `factor` '''
    xyz, tri = array('f'), array('I')
    for body, res in zip(bodies, resolutions):
        x, t = _surface_arrays(body, bounds, res * factor, half)
        base = len(xyz) // 3
        xyz.extend(x)
        tri.extend(base + i for i in t)
    return xyz, tri


def _within_budget(bodies, bounds, resolutions, half, limit):
    ''' The finest mesh of at most `limit` triangles.  The mesh is made at the resolution asked for; when it has more triangles the resolution is lowered
        until it has not.  The triangles of a surface grow with the square of the resolution, so each try goes by the square root of the ratio, between the
        finest one that fitted and the coarsest one that did not.  A mesh already within the budget is left as it is. '''
    good = None                     # (factor, xyz, tri): the finest that fitted
    bad = None                      # the lowest factor that gave too many
    factor = 1.0
    for _ in range(10):
        try:
            xyz, tri = _meshes(bodies, bounds, resolutions, factor, half)
        except RuntimeError:        # (so coarse that no surface is left)
            if good is None:
                raise
            break
        count = len(tri) // 3
        if count <= limit:
            if good is None or factor > good[0]:
                good = (factor, xyz, tri)
            if factor >= 1.0 or count >= 0.85 * limit:
                break
        elif bad is None or factor < bad:
            bad = factor
        below = good[0] if good else 0.0
        above = bad if bad is not None else float('inf')
        if good and above - below < 0.01 * below:
            break
        factor = factor * math.sqrt(0.93 * limit / max(count, 1))
        if not below < factor < above:
            factor = 0.5 * (below + above)
    if good is None:
        raise RuntimeError('max_triangles={}: the coarsest mesh tried still has more triangles'.format(limit))
    return good[1], good[2]


# What a format with a unit and axes of its own says (unit, up axis); the others (STL, OBJ, PLY, OFF) say nothing, and the numbers are the exporter's to choose
UNITS = {'mm': 1.0, 'cm': 10.0, 'm': 1000.0, 'in': 25.4}      # (in millimetres)
_UNIT_NAMES = {'mm': 'millimetres', 'cm': 'centimetres', 'm': 'metres', 'in': 'inches'}
_OWN = {'.3mf': ('mm', 'z'), '.fbx': ('mm', 'z'), '.dxf': ('mm', 'z'), '.glb': ('m', 'y'), '.gltf': ('m', 'y')}


def _conventions(ext, units, up):
    ''' (unit, up axis) the numbers are written in: the ones asked for in a file that has none of its own (millimetres, Z up by default); in a format that
        states its own they are left as the writer takes them, and asking for another is an error '''
    for what, value, allowed in (('units', units, UNITS), ('up', up, ('y', 'z'))):
        if value is not None and value not in allowed:
            raise ValueError('export_mesh: {}={!r} -- one of {}'.format(what, value, ', '.join(allowed)))
    own = _OWN.get(ext)
    if own is None:
        return units or 'mm', up or 'z'
    for what, value, mine in (('units', units, own[0]), ('up', up, own[1])):
        if value is not None and value != mine:
            raise ValueError('export_mesh: a {} file has its own unit ({}) and up axis ({}), so {}={!r} does not apply; units= and up= are for .stl .obj .ply .off'
                             .format(ext, own[0], own[1], what, value))
    return 'mm', 'z'


def _convert(xyz, units, up):
    ''' The vertices (mm, Z up) in the unit and with the up axis asked for: Y up is a turn about X (x, z, -y), which keeps the triangles' sides '''
    k = 1.0 / UNITS[units]
    if k == 1.0 and up == 'z':
        return xyz
    out = array('f')
    if up == 'y':
        for i in range(0, len(xyz), 3):
            out.extend((xyz[i] * k, xyz[i + 2] * k, -xyz[i + 1] * k))
    else:
        out.extend(v * k for v in xyz)
    return out


_MATERIAL_FORMATS = ('.obj', '.glb', '.gltf')           # (the formats that carry materials: the OBJ with a .mtl file beside it)
_COLOR_FORMATS = ('.obj', '.ply', '.glb', '.gltf')      # (and vertex colours)


def _triangle_materials(xyz, tri, materials):
    ''' (the list of materials, the number of the material of each triangle: the last whose `where` is negative at the middle of the triangle, -1 for none) '''
    materials = list(materials) if isinstance(materials, (list, tuple)) else [materials]
    names = set()
    for m in materials:
        if not isinstance(m, Material):
            raise TypeError('export_mesh: materials is a list of material(...), not {!r}'.format(type(m).__name__))
        if m.name in names:
            raise ValueError('export_mesh: two materials are called {!r}'.format(m.name))
        names.add(m.name)
    nt = len(tri) // 3
    centres = array('f', [0.0]) * (3 * nt)
    for c in range(3):
        a, b, d = tri[0::3], tri[1::3], tri[2::3]
        centres[c::3] = array('f', [(xyz[3 * a[t] + c] + xyz[3 * b[t] + c] + xyz[3 * d[t] + c]) / 3.0 for t in range(nt)])
    chosen = array('i', [-1]) * nt
    for k, m in enumerate(materials):
        if m.where is None:
            chosen = array('i', [k]) * nt
        else:
            values = _eval_at(m.where, centres, nt)
            for t in range(nt):
                if values[t] < 0:
                    chosen[t] = k
    return materials, chosen


def _vertex_colors(xyz, colors):
    ''' r, g, b (0 to 1) of every vertex, flat: `colors` is three numbers or fields '''
    try:
        channels = list(colors)
    except TypeError:
        channels = []
    if len(channels) != 3:
        raise ValueError('export_mesh: colors is (r, g, b), each a number or a field from 0 to 1')
    nv = len(xyz) // 3
    out = array('f', [0.0]) * (3 * nv)
    for c, channel in enumerate(channels):
        values = _eval_at(channel, xyz, nv) if isinstance(channel, Shape) else [float(channel)] * nv
        out[c::3] = array('f', [min(1.0, max(0.0, v)) for v in values])
    return out


def _half_of(symmetric):
    ''' (axis, plane, sign) from "x", "-y", ("z", 12.5) ...: the axis the mirror is across, where it is, and which side is kept '''
    if symmetric is None or symmetric is False:
        return None
    plane = 0.0
    if isinstance(symmetric, (tuple, list)):
        if len(symmetric) != 2:
            raise ValueError('export_mesh: symmetric is an axis ("x", "y", "z", or "-x" to keep the negative side) or (axis, position)')
        symmetric, plane = symmetric
    text = str(symmetric).strip().lower()
    sign = -1 if text.startswith('-') else 1
    text = text.lstrip('+-')
    if text not in ('x', 'y', 'z'):
        raise ValueError('export_mesh: symmetric={!r} -- an axis: "x", "y" or "z" ("-x" keeps the negative side)'.format(symmetric))
    return 'xyz'.index(text), float(plane), sign


def export_mesh(part, path, bounds=None, resolution=None, name=None, ascii=False, units=None, up=None, max_triangles=None, symmetric=None, materials=None, colors=None):
    ''' Writes the surface of a body as a triangle mesh file, in the format of the file's extension:

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

        Millimetres and Z up in every format that has no unit or axis (see units, up); the ones that state their unit (3MF, FBX, DXF) say millimetres
        (a glTF is in metres, Y up, as glTF is), and units= or up= for them are an error.  Returns the path. '''
    path = os.fspath(path)
    ext = os.path.splitext(path)[1].lower()
    if ext not in meshfiles.MESH_WRITE_FORMATS:
        raise ValueError('export_mesh({!r}): the mesh formats are {}'.format(path, ', '.join(meshfiles.MESH_WRITE_FORMATS)))
    units, up = _conventions(ext, units, up)
    half = _half_of(symmetric)
    if materials and ext not in _MATERIAL_FORMATS:
        raise ValueError('export_mesh: materials are written in {} files, not {}'.format(', '.join(_MATERIAL_FORMATS), ext))
    if colors is not None and ext not in _COLOR_FORMATS:
        raise ValueError('export_mesh: vertex colours are written in {} files, not {}'.format(', '.join(_COLOR_FORMATS), ext))
    if max_triangles is not None and int(max_triangles) < 4:
        raise ValueError('export_mesh: max_triangles={!r} -- a closed surface has at least four'.format(max_triangles))
    from fieldes.stdlib.fields import _shape_bounds
    parts = list(part) if isinstance(part, (list, tuple)) else [part]
    bodies = [_body_of(p, 'export_mesh') for p in parts]
    resolutions = [_default_resolution(*_shape_bounds(body, bounds), resolution) for body in bodies]
    if max_triangles is None:
        xyz, tri = _meshes(bodies, bounds, resolutions, 1.0, half)
    else:
        xyz, tri = _within_budget(bodies, bounds, resolutions, half, max_triangles)
    # (the materials and the colours are asked of the fields where the model is: before the numbers are turned into another unit and another up axis)
    tri_material = None
    if materials:
        materials, tri_material = _triangle_materials(xyz, tri, materials)
    vertex_colors = _vertex_colors(xyz, colors) if colors is not None else None
    xyz = _convert(xyz, units, up)
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    note = '%s%s' % (_UNIT_NAMES[units], ', Y up' if up == 'y' else '')
    meshfiles.write_mesh(path, xyz, tri, name=name, ascii=ascii, note=note, materials=materials or None, tri_material=tri_material, colors=vertex_colors)
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
