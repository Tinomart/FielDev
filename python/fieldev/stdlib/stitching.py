'''
Stitching loops: a surface made of paths of points, in the way Dust3D makes one of the loops drawn over a reference image (its "Stitching Loop" mode, for faces).

The nodes of the loops are the vertices of the surface -- every point you place counts, none is added or moved (a closed back adds rings behind the surface) -- and the surface is
the triangulation of the nodes in the plane of a view, with every edge of a loop an edge of the triangulation:

  1. LOOPS.  A closed loop is a ring of nodes, an open loop a path.
  2. VIEW.  The nodes are projected into the plane of a view (front, side, top or any direction) and triangulated there: a Delaunay triangulation into which every loop edge is forced
     (by flipping the edges that cross it), so a loop stays an edge loop however its nodes are moved.  The vertices keep their 3D places -- the depth of a node is its own -- so the
     view only decides what is joined to what, and a surface can lie anywhere in space.
  3. MIRROR (only when asked for, for the feature or for single loops).  An open loop is half of a mirrored shape: with both ends on the plane it becomes the closed loop A-B-C-D-C'-B',
     with one end on it A-B-C-D-C'-B'-A', with neither it gets a mirror image of its own.  A closed loop on one side of the plane gets a mirror image.  Ends within `snap` of the
     plane are put onto it.
  4. WHAT IS SURFACE.  A triangle between nodes of different loops is surface.  One whose corners are all on one loop is surface only inside a closed loop (`trim`), and not inside
     an OPENING: a closed loop that is an opening has nothing inside it (an eye between its lids).  What is an opening is decided per loop, or automatically for a closed loop with
     nothing in it that lies inside another closed loop (a closed loop on its own is a patch of surface).
  5. SMALL HOLES, up to `fill_holes` edges, are closed by ear clipping (an opening is not a hole).
  6. A CLOSED BACK (optional): the outer boundary is closed with rings that shrink to an apex behind the surface.

Nothing here is automatic unless it is asked for: the mirror, the snap, the openings, the trimming, the holes and the back are arguments of `stitch` (see fieldev.stdlib.feature for
how they are given in a script), and the loops can override the ones that concern them.

The structure and the rules of 2, 4 and 5 are Dust3D's (dust3d/mesh/stitch_loop_mesh_builder.cc): this is a port of the method to Python, with the choices left to the user.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import math

__all__ = ['stitch', 'StitchedSurface', 'view_axes', 'mirror_plane']


class StitchedSurface:
    ''' The result of `stitch`.

        .vertices   (x, y, z) of every vertex
        .triangles  index triples, counter-clockwise seen from the view
        .sources    for each vertex (loop, node, mirrored): the loop it comes from (the index in the list given), the node of that loop, and whether it is the mirror image of that
                    node -- or None for a vertex of the closed back
        .back_from  the index of the first vertex of the closed back (len(vertices) without one)
        .view       (u, v, w): the unit vectors that run right and up in the view, and towards the viewer
        .closed     whether the surface has no open edge
        .openings   the indices of the loops that are openings (a loop made by a mirror counts under the loop it comes from)
        .unforced   [(loop, node)]: the loop edges that could not be made edges of the triangulation, because they cross other loops
        .mean_edge  the mean length of the edges of the loops, seen from the view '''

    def __init__(self, vertices, triangles, sources, back_from, view, closed, openings, unforced, mean_edge):
        self.vertices = vertices
        self.triangles = triangles
        self.sources = sources
        self.back_from = back_from
        self.view = view
        self.closed = closed
        self.openings = openings
        self.unforced = unforced
        self.mean_edge = mean_edge


# -- vectors ----------------------------------------------------------------------------------------------------------------------------

def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(a, what):
    n = math.sqrt(_dot(a, a))
    if not math.isfinite(n) or n < 1e-12:
        raise ValueError('%s is a direction, not %r' % (what, tuple(a)))
    return (a[0] / n, a[1] / n, a[2] / n)


def _vec3(value, what):
    try:
        out = tuple(float(c) for c in value)
    except (TypeError, ValueError):
        raise ValueError('%s is three numbers (x, y, z), not %r' % (what, value))
    if len(out) != 3:
        raise ValueError('%s is three numbers (x, y, z), not %r' % (what, value))
    return out


# The views, as the direction the viewer looks along and the direction that is up in the picture.  The front view looks along +y (the viewer stands at -y), x to the right, z up
_VIEWS = {'front': ((0, 1, 0), (0, 0, 1)), 'back': ((0, -1, 0), (0, 0, 1)),
          'right': ((-1, 0, 0), (0, 0, 1)), 'left': ((1, 0, 0), (0, 0, 1)),
          'top': ((0, 0, -1), (0, 1, 0)), 'bottom': ((0, 0, 1), (0, -1, 0))}


def view_axes(view='front'):
    ''' (u, v, w) of a view: right, up and towards the viewer, unit vectors.  `view` is a name ('front', 'back', 'left', 'right', 'top', 'bottom') or (direction, up): the direction the
        viewer looks along and the direction that is up in the picture (made square to the first) '''
    if isinstance(view, str):
        if view not in _VIEWS:
            raise ValueError('view is one of %s or (direction, up), not %r' % (', '.join(repr(k) for k in _VIEWS), view))
        look, up = _VIEWS[view]
    else:
        try:
            look, up = view
        except (TypeError, ValueError):
            raise ValueError("view is a name ('front', ...) or (direction, up), not %r" % (view,))
        look, up = _vec3(look, 'the viewing direction'), _vec3(up, 'the up direction')
    look = _unit(look, 'the viewing direction')
    side = _cross(look, up)
    if _dot(side, side) < 1e-18:
        raise ValueError('view: up must not be along the viewing direction')
    u = _unit(side, 'the direction to the right')
    w = (-look[0], -look[1], -look[2])
    v = _cross(w, u)
    return u, v, w


def mirror_plane(spec):
    ''' (point, unit normal) of a mirror plane given as 'x', 'y' or 'z' (the plane through the origin that the axis is the normal of), ('x', offset) (the plane x = offset) or
        (point, normal) '''
    if isinstance(spec, str):
        spec = (spec, 0.0)
    if isinstance(spec, (tuple, list)) and len(spec) == 2 and isinstance(spec[0], str):
        axis = spec[0].lower()
        if axis not in ('x', 'y', 'z'):
            raise ValueError("a mirror plane is 'x', 'y', 'z', ('x', offset) or (point, normal), not %r" % (spec,))
        try:
            offset = float(spec[1])
        except (TypeError, ValueError):
            raise ValueError('the offset of the mirror plane %r is a number' % (spec[0],))
        i = 'xyz'.index(axis)
        point = [0.0, 0.0, 0.0]
        point[i] = offset
        normal = [0.0, 0.0, 0.0]
        normal[i] = 1.0
        return tuple(point), tuple(normal)
    if isinstance(spec, (tuple, list)) and len(spec) == 2:
        return _vec3(spec[0], 'the point of the mirror plane'), _unit(_vec3(spec[1], 'the normal of the mirror plane'), 'the normal of the mirror plane')
    raise ValueError("a mirror plane is 'x', 'y', 'z', ('x', offset) or (point, normal), not %r" % (spec,))


def _image(p, plane):
    point, normal = plane
    d = _dot(_sub(p, point), normal)
    return [p[0] - 2.0 * d * normal[0], p[1] - 2.0 * d * normal[1], p[2] - 2.0 * d * normal[2]]


# -- a Delaunay triangulation of points in the plane, with edges that can be forced into it ---------------------------------------------------

def _orient(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


class _Triangulation:
    ''' A constrained Delaunay triangulation by Bowyer-Watson and edge flipping.  Small inputs only (the nodes of a stitched surface: hundreds), so everything is a plain scan '''

    def __init__(self, points):
        self.p = [(float(q[0]), float(q[1])) for q in points]
        self.n = len(self.p)
        self.tri = []
        self.forced = set()

    def triangulate(self):
        n = self.n
        if n < 3:
            return
        xs, ys = [q[0] for q in self.p], [q[1] for q in self.p]
        span = max(max(xs) - min(xs), max(ys) - min(ys), 1e-9)
        cx, cy = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
        # a triangle around everything, far enough not to bend the hull
        self.p += [(cx - 60.0 * span, cy - 40.0 * span), (cx + 60.0 * span, cy - 40.0 * span), (cx, cy + 70.0 * span)]
        self.tri = [(n, n + 1, n + 2)]
        for q in range(n):
            kept, removed, edges = [], [], set()
            for t in self.tri:
                if self._in_circle(t, self.p[q]):
                    removed.append(t)
                    for i in range(3):
                        edges.add((t[i], t[(i + 1) % 3]))
                else:
                    kept.append(t)
            for t in removed:
                for i in range(3):
                    a, b = t[i], t[(i + 1) % 3]
                    if (b, a) not in edges and _orient(self.p[a], self.p[b], self.p[q]) > 0:
                        kept.append((a, b, q))
            self.tri = kept

    def _in_circle(self, t, q):
        a, b, c = self.p[t[0]], self.p[t[1]], self.p[t[2]]
        ax, ay, bx, by, cx, cy = a[0] - q[0], a[1] - q[1], b[0] - q[0], b[1] - q[1], c[0] - q[0], c[1] - q[1]
        det = (ax * ax + ay * ay) * (bx * cy - cx * by) - (bx * bx + by * by) * (ax * cy - cx * ay) + (cx * cx + cy * cy) * (ax * by - bx * ay)
        return det > 0

    def _has_edge(self, a, b):
        for t in self.tri:
            for i in range(3):
                c, d = t[i], t[(i + 1) % 3]
                if (c == a and d == b) or (c == b and d == a):
                    return True
        return False

    def _crosses(self, a, b, c, d):
        ''' The open segments a-b and c-d cross at one interior point '''
        if a == c or a == d or b == c or b == d:
            return False
        p = self.p
        o1, o2 = _orient(p[a], p[b], p[c]), _orient(p[a], p[b], p[d])
        o3, o4 = _orient(p[c], p[d], p[a]), _orient(p[c], p[d], p[b])
        return ((o1 > 0 and o2 < 0) or (o1 < 0 and o2 > 0)) and ((o3 > 0 and o4 < 0) or (o3 < 0 and o4 > 0))

    def force_edge(self, a, b):
        ''' Make a-b an edge of the triangulation by flipping the edges that cross it.  False when that cannot be done (it crosses another forced edge, or passes through a point) '''
        if a == b or self._has_edge(a, b):
            self.forced.add((min(a, b), max(a, b)))
            return True
        crossing = []
        for t in self.tri:
            for i in range(3):
                c, d = t[i], t[(i + 1) % 3]
                if c < d and self._crosses(a, b, c, d):
                    crossing.append((c, d))
        stalled = 0
        p = self.p
        while crossing and stalled <= len(crossing):
            edge = crossing.pop(0)
            first = second = None
            apex_first = apex_second = 0
            for index, t in enumerate(self.tri):
                for i in range(3):
                    if t[i] == edge[0] and t[(i + 1) % 3] == edge[1]:
                        first, apex_first = index, t[(i + 2) % 3]
                    elif t[i] == edge[1] and t[(i + 1) % 3] == edge[0]:
                        second, apex_second = index, t[(i + 2) % 3]
            if first is None or second is None or edge in self.forced:
                return False
            # the two triangles on the edge make a quadrilateral: only a convex one can take its other diagonal
            if _orient(p[apex_first], p[edge[0]], p[apex_second]) <= 0 or _orient(p[apex_second], p[edge[1]], p[apex_first]) <= 0:
                crossing.append(edge)
                stalled += 1
                continue
            stalled = 0
            self.tri[first] = (apex_first, edge[0], apex_second)
            self.tri[second] = (apex_second, edge[1], apex_first)
            lower, upper = min(apex_first, apex_second), max(apex_first, apex_second)
            if self._crosses(a, b, lower, upper):
                crossing.append((lower, upper))
        if not self._has_edge(a, b):
            return False
        self.forced.add((min(a, b), max(a, b)))
        return True

    def triangles(self):
        ''' The triangles between the given points (none touching the surrounding triangle) '''
        return [t for t in self.tri if t[0] < self.n and t[1] < self.n and t[2] < self.n]


def _inside(polygon, x, y):
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        a, b = polygon[i], polygon[j]
        if (a[1] > y) != (b[1] > y) and x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]:
            inside = not inside
        j = i
    return inside


def _ear_clip(points):
    ''' The triangles (index triples, counter-clockwise) of a small simple polygon given counter-clockwise, by ear clipping '''
    index = list(range(len(points)))
    out = []
    guard = 0
    while len(index) > 3 and guard < 10000:
        guard += 1
        ear = None
        for k in range(len(index)):
            i0, i1, i2 = index[k - 1], index[k], index[(k + 1) % len(index)]
            a, b, c = points[i0], points[i1], points[i2]
            if _orient(a, b, c) <= 1e-18:
                continue
            blocked = False
            for other in index:
                if other in (i0, i1, i2):
                    continue
                q = points[other]
                if _orient(a, b, q) >= 0 and _orient(b, c, q) >= 0 and _orient(c, a, q) >= 0:
                    blocked = True
                    break
            if not blocked:
                ear = k
                break
        if ear is None:
            ear = 0
        out.append((index[ear - 1], index[ear], index[(ear + 1) % len(index)]))
        del index[ear]
    if len(index) == 3:
        out.append((index[0], index[1], index[2]))
    return out


# -- the surface ------------------------------------------------------------------------------------------------------------------------

def stitch(loops, view='front', mirror=None, snap=0.0, openings=True, trim=True, fill_holes=8, back=False, back_depth=1.0, back_sharpness=0.0):
    ''' The surface stitched through loops.

        loops       a list of dicts, one for each loop:
                      'nodes'    the nodes as (x, y, z)
                      'closed'   whether the loop is a ring
                      'mirror'   None: as the surface does; False: not mirrored; True: across the plane of the surface; or a plane of its own (see `mirror_plane`)
                      'opening'  None: as `openings` says; True: an opening; False: surface across
        view        what the nodes are projected into to be joined: 'front', 'back', 'left', 'right', 'top', 'bottom' or (direction, up) -- see `view_axes`
        mirror      the plane the loops are mirrored across (see `mirror_plane`), or None for no mirroring
        snap        how far from the mirror plane the end of an open loop may be to be put onto it (0: only those on it already)
        openings    whether a closed loop with nothing in it, inside another closed loop, is an opening; a loop's own 'opening' is what counts when it has one
        trim        drop the triangles that join the nodes of one loop outside every closed loop
        fill_holes  the most edges a hole may have to be closed (0: none)
        back, back_depth, back_sharpness   close the outer boundary with rings behind the surface: the depth of the apex as a share of the mean radius of the boundary, and 0 to 1 how
                    much the rings keep their shape and do not follow the surface

        Returns a StitchedSurface.  Raises ValueError for loops that give nothing to stitch '''
    u, v, w = view_axes(view)
    if len(loops) == 0:
        raise ValueError('stitch: no loops')
    if not isinstance(fill_holes, int) or isinstance(fill_holes, bool) or fill_holes < 0:
        raise ValueError('stitch: fill_holes is a number of edges, 0 or more, not %r' % (fill_holes,))
    snap = float(snap)
    if not snap >= 0.0:
        raise ValueError('stitch: snap is a distance, 0 or more, not %r' % (snap,))
    surface_plane = None if mirror is None or mirror is False else mirror_plane(mirror)

    def proj(p):
        return (_dot(p, u), _dot(p, v))

    work = []
    for index, loop in enumerate(loops):
        nodes = [list(_vec3(p, 'a node')) for p in loop['nodes']]
        closed = bool(loop.get('closed')) and len(nodes) >= 3
        want = loop.get('mirror')
        if want is None:
            plane = surface_plane
        elif want is False:
            plane = None
        elif want is True:
            if surface_plane is None:
                raise ValueError('stitch: loop %d is to be mirrored across the plane of the surface, which has none -- give a mirror plane' % index)
            plane = surface_plane
        else:
            plane = mirror_plane(want)
        work.append({'nodes': nodes, 'closed': closed, 'drawn_closed': closed, 'opening': loop.get('opening'), 'plane': plane, 'source': index,
                     'origin': [(i, False) for i in range(len(nodes))]})
    every = [p for loop in work for p in loop['nodes']]
    if not every:
        raise ValueError('stitch: the loops have no nodes')
    scale = max(max(p[c] for p in every) - min(p[c] for p in every) for c in range(3)) or 1.0
    exact = 1e-9 * scale
    # the mean edge length seen from the view
    total, count = 0.0, 0
    for loop in work:
        nodes = loop['nodes']
        for i in range(len(nodes) if loop['closed'] else len(nodes) - 1):
            a, b = proj(nodes[i]), proj(nodes[(i + 1) % len(nodes)])
            total += math.hypot(b[0] - a[0], b[1] - a[1])
            count += 1
    if count == 0:
        raise ValueError('stitch: every loop is a single point')
    mean_edge = total / count

    # the mirror
    def reflect(loop, indices):
        ''' The nodes of `loop` at `indices` mirrored, and the nodes they come from '''
        out, origin = [], []
        for i in indices:
            out.append(_image(loop['nodes'][i], loop['plane']))
            origin.append((loop['origin'][i][0], True))
        return out, origin

    for loop in list(work):
        plane = loop['plane']
        if plane is None or not loop['nodes']:
            continue
        nodes = loop['nodes']
        point, normal = plane
        reach = max(snap, exact)
        if not loop['closed']:
            for i in (0, len(nodes) - 1):
                d = _dot(_sub(nodes[i], point), normal)
                if abs(d) <= reach:
                    nodes[i] = [nodes[i][c] - d * normal[c] for c in range(3)]
        dist = [_dot(_sub(p, point), normal) for p in nodes]
        negative = any(d < -exact for d in dist)
        positive = any(d > exact for d in dist)
        if loop['closed']:
            if negative != positive:          # (on one side: its image is a loop of its own; across the plane or on it, it is its own image)
                image, origin = reflect(loop, range(len(nodes) - 1, -1, -1))
                work.append({'nodes': image, 'closed': True, 'drawn_closed': True, 'opening': loop['opening'], 'plane': None, 'source': loop['source'], 'origin': origin})
            continue
        if len(nodes) < 2:
            continue
        first = abs(dist[0]) <= reach
        last = abs(dist[-1]) <= reach
        if first and last:
            if len(nodes) >= 3:
                # A-B-C-D with both ends on the plane: the nodes between them mirrored back round to the start
                image, origin = reflect(loop, range(len(nodes) - 2, 0, -1))
                loop['nodes'] = nodes + image
                loop['origin'] = loop['origin'] + origin
                loop['closed'] = True
        elif first or last:
            if first:
                nodes.reverse()
                loop['origin'].reverse()
            # A-B-C-D(on the plane) -> A-B-C-D-C'-B'-A'
            image, origin = reflect(loop, range(len(nodes) - 2, -1, -1))
            loop['nodes'] = nodes + image
            loop['origin'] = loop['origin'] + origin
        elif negative != positive:
            image, origin = reflect(loop, range(len(nodes) - 1, -1, -1))
            work.append({'nodes': image, 'closed': False, 'drawn_closed': False, 'opening': loop['opening'], 'plane': None, 'source': loop['source'], 'origin': origin})

    # the vertices, and the triangulation with every loop edge in it
    vertices, sources, node_of, vertex_loop = [], [], [], []
    for li, loop in enumerate(work):
        node_of.append([])
        for ni, node in enumerate(loop['nodes']):
            node_of[li].append(len(vertices))
            vertices.append(tuple(node))
            sources.append((loop['source'], loop['origin'][ni][0], loop['origin'][ni][1]))
            vertex_loop.append(li)
    if len(vertices) < 3:
        raise ValueError('stitch: three nodes at least are needed')
    flat, seen = [], {}
    shift = max(1e-12, mean_edge * 1e-7)
    for i, p in enumerate(vertices):
        s, t = proj(p)
        key = (round(s, 9), round(t, 9))
        repeat = seen.get(key, 0)
        seen[key] = repeat + 1
        # (the places the triangulation works with are moved by a hair, each by its own amount, so that no four of them are on one circle and no three on one line: nodes on a grid,
        # or along the mirror plane, would otherwise make the tests that decide the triangulation come out as zero.  The vertices keep their places)
        jx = ((i * 0.7548776662466927) % 1.0 - 0.5) * shift
        jy = ((i * 0.5698402909980532) % 1.0 - 0.5) * shift
        flat.append((s + shift * repeat + jx, t + shift * 0.618 * repeat + jy))
    tri = _Triangulation(flat)
    tri.triangulate()
    unforced = []
    for li, loop in enumerate(work):
        nodes = loop['nodes']
        for ni in range(len(nodes) if loop['closed'] else len(nodes) - 1):
            if not tri.force_edge(node_of[li][ni], node_of[li][(ni + 1) % len(nodes)]):
                unforced.append((loop['source'], loop['origin'][ni][0]))

    # what is surface
    polygons = [[flat[x] for x in node_of[li]] if loop['closed'] else None for li, loop in enumerate(work)]
    is_opening = [False] * len(work)
    for li, loop in enumerate(work):
        if polygons[li] is None:
            continue
        if loop['opening'] is not None:
            is_opening[li] = bool(loop['opening'])
        elif openings and loop['drawn_closed']:
            # (a closed loop with nothing in it, inside another closed loop: an eye in a face.  A closed loop on its own is a patch of surface)
            empty = True
            enclosed = False
            for other in range(len(work)):
                if other == li:
                    continue
                if any(_inside(polygons[li], flat[x][0], flat[x][1]) for x in node_of[other]):
                    empty = False
                if polygons[other] is not None and all(_inside(polygons[other], flat[x][0], flat[x][1]) for x in node_of[li]):
                    enclosed = True
            is_opening[li] = empty and enclosed
    faces = []
    for t in tri.triangles():
        li = vertex_loop[t[0]]
        if li == vertex_loop[t[1]] and li == vertex_loop[t[2]]:
            x = (flat[t[0]][0] + flat[t[1]][0] + flat[t[2]][0]) / 3.0
            y = (flat[t[0]][1] + flat[t[1]][1] + flat[t[2]][1]) / 3.0
            if is_opening[li] and polygons[li] is not None and _inside(polygons[li], x, y):
                continue
            if trim and not any(p is not None and _inside(p, x, y) for p in polygons):
                continue
        faces.append(tuple(t))

    # small holes (not the openings: they are holes that were asked for)
    if fill_holes:
        rims = set()
        for li in range(len(work)):
            if is_opening[li]:
                ring = node_of[li]
                for i in range(len(ring)):
                    rims.add((ring[i], ring[(i + 1) % len(ring)]))
                    rims.add((ring[(i + 1) % len(ring)], ring[i]))
        _fill_holes(flat, faces, fill_holes, rims)

    back_from = len(vertices)
    if back:
        _close_back(vertices, sources, faces, float(back_depth), float(back_sharpness))
    edges = set()
    for f in faces:
        for i in range(3):
            edges.add((f[i], f[(i + 1) % 3]))
    closed = bool(faces) and all((b, a) in edges for (a, b) in edges)
    flags = sorted(set(loop['source'] for li, loop in enumerate(work) if is_opening[li]))
    return StitchedSurface(vertices, faces, sources, back_from, (u, v, w), closed, flags, unforced, mean_edge)


def _fill_holes(flat, faces, most, rims):
    ''' Close the holes of at most `most` edges in `faces` by ear clipping, but not those that have an edge in `rims`.  `flat` are the places of the vertices in the view '''
    used = set()
    for f in faces:
        for i in range(3):
            used.add((f[i], f[(i + 1) % 3]))
    boundary = {}
    for (a, b) in used:
        if (b, a) not in used:
            boundary.setdefault(a, []).append(b)
    visited = set()
    for start in sorted(boundary):
        for first in boundary[start]:
            if (start, first) in visited:
                continue
            hole, walked = [start], [(start, first)]
            cur, valid = first, True
            while cur != start:
                hole.append(cur)
                if len(hole) > most:
                    valid = False
                    break
                options = [c for c in boundary.get(cur, []) if (cur, c) not in visited and (cur, c) not in walked]
                if not options:
                    valid = False
                    break
                previous = hole[-2]
                incoming = math.atan2(flat[cur][1] - flat[previous][1], flat[cur][0] - flat[previous][0])
                best, least = None, 1e30
                for c in options:
                    outgoing = math.atan2(flat[c][1] - flat[cur][1], flat[c][0] - flat[cur][0])
                    turn = outgoing - incoming
                    while turn > math.pi:
                        turn -= 2.0 * math.pi
                    while turn < -math.pi:
                        turn += 2.0 * math.pi
                    if abs(turn) < least:
                        least, best = abs(turn), c
                walked.append((cur, best))
                cur = best
            for e in walked:
                visited.add(e)
            if not valid or len(hole) < 3:
                continue
            if any((hole[i], hole[(i + 1) % len(hole)]) in rims for i in range(len(hole))):
                continue
            pts = [flat[x] for x in hole]
            area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
            if area >= 0.0:
                continue                        # (the rim of a hole runs clockwise in the view, the outer boundary of the surface counter-clockwise: that one is not a hole)
            order = list(range(len(hole) - 1, -1, -1))
            for i0, i1, i2 in _ear_clip([pts[i] for i in order]):
                faces.append((hole[order[i0]], hole[order[i1]], hole[order[i2]]))


def _close_back(vertices, sources, faces, back_depth, back_sharpness):
    ''' Close the outermost boundary with rings that shrink to an apex behind the surface (Dust3D's `closeOuterBoundary`).  Changes `vertices`, `sources` and `faces` '''
    edges = set()
    for f in faces:
        for i in range(3):
            edges.add((f[i], f[(i + 1) % 3]))
    nxt = {}
    for (a, b) in edges:
        if (b, a) not in edges:
            nxt[a] = b
    if not nxt:
        return
    seen, found = set(), []
    for start in sorted(nxt):
        if start in seen:
            continue
        loop, cur = [], start
        while cur not in seen and cur in nxt:
            seen.add(cur)
            loop.append(cur)
            cur = nxt[cur]
        if len(loop) >= 3:
            found.append(loop)
    if not found:
        return

    def perimeter(loop):
        return sum(math.dist(vertices[loop[(i + 1) % len(loop)]], vertices[loop[i]]) for i in range(len(loop)))
    outer = max(found, key=perimeter)
    n = len(outer)
    centroid = [sum(vertices[x][c] for x in outer) / n for c in range(3)]
    # the normal of the boundary by Newell's method, turned round: the boundary runs counter-clockwise seen from the viewer, and the back is away from the viewer
    normal = [0.0, 0.0, 0.0]
    for i in range(n):
        p, q = vertices[outer[i]], vertices[outer[(i + 1) % n]]
        normal[0] += (p[1] - q[1]) * (p[2] + q[2])
        normal[1] += (p[2] - q[2]) * (p[0] + q[0])
        normal[2] += (p[0] - q[0]) * (p[1] + q[1])
    length = math.sqrt(sum(c * c for c in normal)) or 1.0
    normal = [-c / length for c in normal]
    radius = sum(math.dist(vertices[x], centroid) for x in outer) / n
    rings_count = max(4, n // 6)
    height = radius * back_depth
    sharp = max(0.0, min(1.0, back_sharpness))
    inner = set(outer)
    flow = []
    for x in outer:
        total, count = [0.0, 0.0, 0.0], 0
        for f in faces:
            if x in f:
                for y in f:
                    if y != x and y not in inner:
                        for c in range(3):
                            total[c] += vertices[y][c]
                        count += 1
        if count:
            d = [vertices[x][c] - total[c] / count for c in range(3)]
            l = math.sqrt(sum(c * c for c in d)) or 1.0
            flow.append([c / l for c in d])
        else:
            flow.append(list(normal))
    apex = [centroid[c] + normal[c] * height for c in range(3)]
    previous = list(outer)
    for k in range(1, rings_count + 1):
        t = k / float(rings_count)
        if k == rings_count:
            top = len(vertices)
            vertices.append(tuple(apex))
            sources.append(None)
            for i in range(n):
                faces.append((previous[i], top, previous[(i + 1) % n]))
            break
        scale = math.cos(t * math.pi / 2.0)
        offset = math.sin(t * math.pi / 2.0) * height
        ring = []
        for i in range(n):
            orig = vertices[outer[i]]
            kept = [centroid[c] + (orig[c] - centroid[c]) * scale + normal[c] * offset for c in range(3)]
            target = [orig[c] + flow[i][c] * radius * t for c in range(3)]
            follow = [target[c] * (1.0 - t * t) + apex[c] * (t * t) for c in range(3)]
            ring.append(len(vertices))
            vertices.append(tuple(kept[c] * sharp + follow[c] * (1.0 - sharp) for c in range(3)))
            sources.append(None)
        for i in range(n):
            p, q, r, s = previous[i], previous[(i + 1) % n], ring[(i + 1) % n], ring[i]
            faces.append((p, s, r))
            faces.append((p, r, q))
        previous = ring
