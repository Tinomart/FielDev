'''
Stitching loops: a surface stitched through loops of points, for the delicate parts of a character -- a face, an ear, a hand.

    outline = loop([point(0, 0, -10), point(7, 0, -5), point(8, 0, 4), point(0, 0, 10)])      # half of the face: an open path
    eye = ring((3, -0.4, 3), 1.3, 8)                                                          # a closed loop of 8 points
    nose = loop([point(0, -1.5, 1), point(0.8, -1.0, -1.5), point(0, -1.6, -2.5)])
    face = stitching_loops([outline, eye, nose], mirror="x", name="face")

STITCHING LOOPS make a surface through LOOPS of points.  A loop is a path of points, closed into a ring or open; every point you place is a vertex of the surface -- none is added, none is moved
-- and every edge of a loop is an edge of the surface, so the loops you draw are the edge loops of the face, wherever the points are dragged.  This is the method of Dust3D's stitching
loops, for modelling a part from the outlines of a reference picture: draw the outline of the face, of an eye, of the mouth, and the surface between them is made.

How the points are joined is decided in the plane of a VIEW (`view="front"`: the plane you look at the part in).  The points stay where they are in space -- each has its own depth --
so the view only decides what is joined to what, and the loops can be dragged in any view of the viewport.  Look at a face from the front, an ear from the side (`view="right"`), or
along any direction (`view=((0, 1, -1), (0, 0, 1))`: the direction you look along, and which way is up in the picture).

Nothing is automatic unless the arguments ask for it:

    stitching_loops(loops, view="front", mirror=None, snap=0, openings=True, trim=True, fill_holes=8, back=False, back_depth=1, back_sharpness=0, thickness=0.2, name=None)

        loops        the loops: `loop(...)`, `ring(...)`, a polyline or spline, a profile, or a plain list of points (an open loop)
        view         "front", "back", "left", "right", "top", "bottom", or (direction, up): the plane the points are joined in
        mirror       None: the loops are used as they are.  "x", "y" or "z" (the plane through the origin that the axis is the normal of), ("x", 2) (the plane x = 2) or (point, normal):
                     the loops are mirrored across that plane.  An open loop is half of a shape: with both its ends on the plane it becomes a ring (A-B-C-D-C'-B'), with one end on it a
                     path (A-B-C-D-C'-B'-A'), with neither it gets a mirror image of its own; a ring on one side of the plane gets a mirror image; what lies across the plane stays
        snap         how near the plane an end of an open loop may be to be put onto it (0: only the ends that are on it already)
        openings     a closed loop with nothing in it that lies inside another closed loop is an opening -- an eye, a nostril -- and not surface.  False: every loop is stitched across
        trim         drop the triangles that join the points of one loop alone and lie outside every closed loop (False: keep everything the triangulation makes)
        fill_holes   close the holes of this many edges or fewer (0: none).  An opening is not a hole
        back         True: close the outer boundary with rings that shrink to a point behind the surface, so that it is a solid.  back_depth is how deep that point is, as a share of the
                     mean radius of the outline, and back_sharpness (0 to 1) how much the rings keep the shape of the outline and do not follow the surface
        thickness    an open surface is a shell of this thickness (the surface is its middle); a closed one is a solid and has none
        name         what the UV map and the model tree call it

Each loop can say its own choice, and the surface's is then not used for it:

    loop(points, closed=False, mirror=None, opening=None)

        closed       True: a ring (the last point is joined to the first)
        mirror       None: as the surface says.  False: this loop is not mirrored.  True: across the plane of the surface.  Or a plane of its own
        opening      None: as `openings` says.  True: this closed loop is an opening, whatever is in it.  False: it is stitched across

`ring(center, radius, count, facing)` makes the points of a round loop.  The surface joins a character with the rest of the parts, as an armature does:

    hero = character([spine, arm, face], blend=2)

The UV map of the character (`uvs="armature"`, see uvmaps.py) unwraps stitching loops as they were drawn: flat, in the picture of its view, and the back, if it has one, as an island of its own.

The surface is a mesh, and the shape is the exact distance to that mesh.  It is made when the script runs: points dragged in the viewport change the surface when the script runs
again, and not while the drag is going on, as the sweep of an armature does.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import ctypes
import math

from fieldev.ffi import lib, libfive_mesh_import_info_t
from fieldev.kinds import takes as _declare
from fieldev.shape import Shape
from fieldev.stdlib import curves as C
from fieldev.stdlib import stitching as S
from fieldev.stdlib.content_cache import cache_for

__all__ = ['stitching_loops', 'loop', 'ring', 'Loop', 'StitchingLoops']

_MOST_NODES = 1500              # (the triangulation is made in plain Python: more nodes than this would take too long)
_cache = cache_for('stitching_loops', 8)


class Loop(list):
    ''' The points of a loop of stitching loops, and what the loop says of itself (see `loop`) '''

    def __init__(self, points=(), closed=False, mirror=None, opening=None):
        super().__init__(points)
        self.closed = bool(closed)
        self.mirror = mirror
        self.opening = opening

    def __repr__(self):
        return 'loop(%d points%s)' % (len(self), ', closed' if self.closed else '')


class StitchingLoops:
    ''' What stitching loops know of themselves, for the UV map and the model tree: its name, the surface that was stitched (a stitching.StitchedSurface: vertices, triangles, which loop and
        point each vertex comes from, the view) and the thickness of the shell it is made into '''

    def __init__(self, name, surface, loops, thickness):
        self.name = name
        self.surface = surface
        self.loops = loops
        self.thickness = thickness

    def __repr__(self):
        return 'stitching_loops(%r, %d loops, %d vertices, %d triangles)' % (self.name, self.loops, len(self.surface.vertices), len(self.surface.triangles))


def _is_node(item):
    if getattr(item, 'xyz', None) is not None:
        return True
    return isinstance(item, (tuple, list)) and len(item) in (2, 3) and all(isinstance(c, (int, float)) for c in item)


def _points_of(item, k):
    ''' (the points of a loop, whether the thing says it is closed -- or None) '''
    if isinstance(item, Loop):
        return list(item), item.closed
    points = getattr(item, 'points', None)
    if points is not None and getattr(item, '_kind', None) == 'profile':
        return list(points), True
    if points is not None and hasattr(item, 'closed'):
        return list(points), bool(item.closed)
    if isinstance(item, (list, tuple)):
        return list(item), None
    raise TypeError('stitching_loops: loop %d is loop(...), ring(...), a polyline, a spline, a profile or a list of points, not %r' % (k, type(item).__name__))


def loop(points, closed=None, mirror=None, opening=None):
    ''' A loop for stitching_loops: a path of points (`point(x, y, z)`, or tuples of numbers), with what it says of itself.

            eye = loop([point(2, -0.4, 3), point(3, -0.5, 3.6), point(4, -0.4, 3)], closed=True, opening=True)

        points   a list of points, or a polyline, a spline or a profile (their points are the nodes)
        closed   True: a ring, the last point joined to the first.  None: as the polyline, spline or profile says, and open for a list
        mirror   None: as the surface says.  False: this loop is not mirrored.  True: across the plane of the surface.  Or a plane of its own ("x", ("x", 2), (point, normal))
        opening  None: as the surface says (`openings`).  True: this closed loop is an opening, whatever is in it.  False: it is stitched across '''
    nodes, says = _points_of(points, 0)
    if closed is None:
        closed = bool(says)
    return Loop(nodes, closed, mirror, opening)


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def ring(center, radius, count=8, facing=(0, -1, 0), start=None):
    ''' A closed loop of round points, as tuples of numbers: `count` of them on a circle of `radius` (a number, or (wide, high) for an oval) round `center`, in the plane that `facing`
        is the normal of, the first at the direction `start` (default: up, +z; along x when the loop faces up or down).  The points follow each other counter-clockwise seen from
        where the loop faces.  The default faces -y, towards the viewer of the front view, with the first point up '''
    if not isinstance(count, int) or isinstance(count, bool) or count < 3:
        raise ValueError('ring: count is the number of points, 3 or more, not %r' % (count,))
    wide, high = (radius if isinstance(radius, (tuple, list)) and len(radius) == 2 else (radius, radius))
    n = math.sqrt(sum(float(c) ** 2 for c in facing))
    if n < 1e-12:
        raise ValueError('ring: facing is a direction, not (0, 0, 0)')
    f = tuple(float(c) / n for c in facing)
    up = tuple(float(c) for c in start) if start is not None else ((1.0, 0.0, 0.0) if abs(f[2]) > 0.9 else (0.0, 0.0, 1.0))
    along = _dot(up, f)
    u = _sub(up, tuple(c * along for c in f))                  # (the start direction, made to lie in the plane)
    lu = math.sqrt(_dot(u, u))
    if lu < 1e-12:
        raise ValueError('ring: start must not be along the way the loop faces')
    u = tuple(c / lu for c in u)
    v = _cross(f, u)
    out = []
    for k in range(count):
        t = 2.0 * math.pi * k / count
        a, b = math.cos(t) * high, math.sin(t) * wide
        out.append(tuple(float(center[i]) + u[i] * a + v[i] * b for i in range(3)))
    return Loop(out, closed=True)


def _surface_field(vertices, triangles):
    ''' The exact signed distance to a triangle mesh (see mesh_import), made once for the same mesh '''
    key = (tuple(vertices), tuple(triangles))
    hit, shape = _cache.get(key)
    if hit:
        return shape
    flat = [float(c) for v in vertices for c in v]
    ids = [int(i) for t in triangles for i in t]
    cx = (ctypes.c_float * len(flat))(*flat)
    ct = (ctypes.c_uint32 * len(ids))(*ids)
    info = libfive_mesh_import_info_t()
    ptr = lib.libfive_mesh_from_arrays(cx, len(vertices), ct, len(triangles), 1.0, ctypes.byref(info))
    if not ptr:
        raise ValueError('stitching_loops: ' + lib.libfive_import_mesh_last_message().decode('utf-8', 'replace'))
    shape = Shape(ptr)
    _cache.put(key, shape)
    return shape


def stitching_loops(loops, view='front', mirror=None, snap=0.0, openings=True, trim=True, fill_holes=8, back=False, back_depth=1.0, back_sharpness=0.0, thickness=0.2, name=None):
    ''' A surface stitched through loops of points -- see the top of this file for what each argument does.

            face = stitching_loops([outline, eye, mouth, nose], mirror="x", name="face")

        Returns a shape: the exact distance to the surface, made a shell of `thickness` when the surface is open and a solid when it is closed (`back=True`, with no opening left) '''
    if not isinstance(loops, (list, tuple)) or not loops:
        raise TypeError('stitching_loops(loops): a list of loops, each a list of points')
    records, positions = [], []
    for k, one in enumerate(loops):
        if _is_node(one):
            raise TypeError('stitching_loops: loops is a list of loops, each a list of points -- item %d is a point, not a loop' % k)
        points, says = _points_of(one, k)
        closed = bool(says)
        if len(points) < (3 if closed else 2):
            raise ValueError('stitching_loops: loop %d has %d points -- %s' % (k, len(points), 'a closed loop has 3 or more' if closed else 'a loop has 2 or more'))
        pos = [c.pos for c in C.controls(points)]
        positions.append(pos)
        records.append({'nodes': pos, 'closed': closed, 'mirror': getattr(one, 'mirror', None), 'opening': getattr(one, 'opening', None)})
    if sum(len(p) for p in positions) > _MOST_NODES:
        raise ValueError('stitching_loops: %d points are more than %d -- fewer points, or several sets of stitching loops' % (sum(len(p) for p in positions), _MOST_NODES))
    if not isinstance(thickness, (int, float)) or isinstance(thickness, bool) or not thickness > 0:
        raise ValueError('stitching_loops: thickness is a number above 0, not %r' % (thickness,))
    surface = S.stitch(records, view=view, mirror=mirror, snap=snap, openings=openings, trim=trim, fill_holes=fill_holes, back=back, back_depth=back_depth,
                       back_sharpness=back_sharpness)
    if surface.unforced:
        places = ', '.join('loop %d after its point %d' % (l, n) for l, n in surface.unforced[:4])
        raise ValueError('stitching_loops: the edges of loops cross in the %s view (%s) -- loops must not cross each other: move a point, or look at the part from another side (view=)'
                         % (view if isinstance(view, str) else 'chosen', places))
    if not surface.triangles:
        raise ValueError('stitching_loops: the loops make no surface -- a surface needs two loops to join, or a closed loop to fill (an opening has none)')
    label = str(name) if name else 'stitching_loops'
    field = _surface_field(surface.vertices, surface.triangles)
    out = field if surface.closed else field.abs() - 0.5 * float(thickness)
    # the box the shape fills, for the render region and the export: its vertices, and the thickness and a little more (a box that holds it, not its exact extent)
    flat_all = surface.vertices
    span = max(max(p[c] for p in flat_all) - min(p[c] for p in flat_all) for c in range(3))
    pad = 0.5 * float(thickness) + 0.05 * span + 1e-3
    out._bounds = (tuple(min(p[c] for p in flat_all) - pad for c in range(3)), tuple(max(p[c] for p in flat_all) + pad for c in range(3)))
    out._bounds_loose = True
    out._stitching_loops = StitchingLoops(label, surface, len(records), float(thickness))
    return out


# What the menus offer it for (see fieldev.kinds.takes): stitching loops are made of points
stitching_loops._takes = _declare({'point'}, [{'point'}])
