'''
A 2D shape from points or from a closed curve: `profile`.

    a = point(0, 0, 0)
    b = point(40, 0, 0)
    c = point(40, 20, 0)
    d = point(0, 20, 0, smooth=True)
    tile = profile([a, b, c, d])                # the face the points enclose; hard edges unless a point says smooth=True
    round = profile([a, b, c, d], smooth=True)   # ...or every point a spline, but where a point says smooth=False
    outline = spline([a, b, c, d], closed=True)
    tile = profile(outline)                     # the same, from a curve
    body = extrude(tile, 0, 5)                 # a solid: the face pulled 5 along its normal

The points are ordinary points (`point(x, y, z)`, dragged with their gizmo): any number of them, joined in the order they are given and closed (the last to
the first).  The shape lies in the PLANE through the first three points (the first that is not on a line with the first two); every other point is
projected onto that plane, so a profile is made whatever the points are.  A tuple of three numbers stands for a point too.

Each point is a corner (a hard edge: straight to its neighbours) or a spline point (the outline is a smooth curve through it) -- see `spline`, which makes the
outline.  `smooth=` of the profile says which a point is that does not say itself (False, a hard edge, by default); `point(..., smooth=True)` says it for
that point -- FielDev toggles it when you double-click the point.  The ROTATION of a spline point -- its gizmo's rotate numbers, which a point has no other use
for -- turns the direction in which the outline leaves it.

A profile is drawn from the numbers its points have, natively, while you drag them.  Its field (for `extrude`, `offset` ...) is plain math, made
when the script runs: the signed distance to the outline -- the distance to the nearest edge, with the side taken from that nearest edge or corner alone, so
the renderer drops the edges that are far from where it looks.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import ctypes
import functools
import math

from fieldev.ffi import lib
from fieldev.shape import Shape
from fieldev.stdlib import curves as C

__all__ = ['profile', 'Profile', 'extrude', 'path_extrude']


class Profile(Shape):
    ''' A 2D shape made of points (see `profile`).  .points are the points it was made from, .plane the plane it lies in -- (origin, u, v), three numbers each --
        .smooth the default of its points, .profile2d the same field in the coordinates of its plane (x along u, y along v) '''
    _kind = 'profile'
    _no_gizmo = True                # (no gizmo() line with numbers of its own: its points have them, and the viewport shares them -- View::groupGizmo -- to move, turn and scale it)
    _outline_gizmo = True           # (the model tree's gizmo button gives it a line without numbers, `x = gizmo(x, mode=...)`: when that shared gizmo is shown, off until said otherwise)

    def _remake(self, points, improper=False):
        ''' The same outline through other points (the images of its points in a symmetry: see symmetries.symmetry_images) -- the other way round for a mirror image, which turns
            the way round: reversed, it faces as this one does '''
        return profile(points[::-1] if improper else points, smooth=self.smooth, radius=getattr(self, 'radius', 0))

    def _display(self):
        # What the viewport draws is the face of the outline, made natively from the points' numbers: no field is needed for that, so none is made
        out = C.owned(Shape.wrap(1.0))
        for name, v in self.__dict__.items():
            if name != 'ptr':
                out.__dict__[name] = v
        out._kind = 'profile'
        out._profile_face = True
        return C.with_image_dots(self, out)


class SurfaceProfile(Shape):
    ''' A 2D shape made from a surface (see `profile`): the outline of the surface in its plane, holes included.  .plane the plane it lies in -- (origin, u, v), three
        numbers each, u x v the way the surface faces --, .profile2d the same field in the coordinates of that plane, .flat whether the surface is flat (it is projected
        onto the plane when it is not), .away how far the surface is from the plane at most, .loops the outline as [(polygon, hole)] with the points as (s, t) '''
    _kind = 'profile'
    _no_gizmo = True                # (it follows the part it was picked on)

    def _display(self):
        # Drawn from its field, as any 2D shape is, in its plane
        out = C.owned(self)
        for name, v in self.__dict__.items():
            if name != 'ptr':
                out.__dict__[name] = v
        out._kind = 'profile'
        out._flat2d = True
        o, u, v = self.plane
        out._flat_frame = tuple(tuple(Shape.wrap(float(c)) for c in axis) for axis in (o, u, v))
        return out


def _polygon_field(loop, frame, arcs=None):
    return C.owned(C.polygon_field(loop, frame, arcs))


def _from_surface(selection):
    ''' The 2D shape a surface picked on a part makes (see `profile`) '''
    from fieldev.stdlib import surface_profile
    plane, loops, flat, away = surface_profile.outline_of(selection)

    def field(frame):
        out = None
        for polygon, hole in loops:
            if hole:
                continue
            part = C.polygon_field(polygon, frame)
            out = part if out is None else out.min(part)
        for polygon, hole in loops:
            if hole:
                out = out.max(C.polygon_field(polygon, frame) * -1.0)          # (what is inside a hole is outside)
        return out

    made = C.owned(field(plane), SurfaceProfile)          # (the field is held for the whole call: see curves.owned)
    made.plane, made.profile2d, made.flat, made.away, made.loops = plane, C.owned(field(None)), flat, away, loops
    made.surface = selection
    o, u, v = plane
    made._outline_box = _box_of_points([tuple(o[k] + s * u[k] + t * v[k] for k in range(3)) for polygon, hole in loops if not hole for s, t in polygon])
    flat = [(s, t) for polygon, hole in loops if not hole for s, t in polygon]
    if flat:
        made._centre2d = (0.5 * (min(s for s, t in flat) + max(s for s, t in flat)), 0.5 * (min(t for s, t in flat) + max(t for s, t in flat)))
    made._no_handles = True                  # (no faces of its own to pull: it is made from the surface)
    if not flat:
        print('profile: the surface is not flat (it is up to %.3g mm from the plane through its middle): its outline is projected onto that plane, along the way it '
              'faces on average' % away)
    return made


def profile(source, smooth=False, radius=0):
    ''' The 2D shape the points of `source` enclose -- a list of points, or a curve -- as a closed outline through them in the order given, in the plane
        through the first three of them (the others are projected onto it).  `smooth` is what a point is that does not say (point(..., smooth=True) or
        smooth=False): False, a corner (a hard edge: the default), or True, a spline point.  A spline point leaves in the direction the rotation of its gizmo
        says (no rotation: from its neighbours).  A point can also be a ROUND corner, `point(..., radius=r)`: an exact arc of radius r, tangent to both edges, takes the place
        of the corner (the point stays where the two edges would meet; the scale of its gizmo multiplies the radius; where the arc would run into the next one or past the next
        point the radius is made smaller, and a square whose four corners ask for half its side is a circle).  `radius` is what a corner is that does not say, 0 (a hard
        corner) by default.  With fewer than three points, or all on a line, it is empty.

        `source` can also be a SURFACE picked on a part (`select_surface`): the 2D shape of its outline -- the outline of the face, holes included, in the plane
        of the face (exact for a flat face), or, for a surface that is not flat, of its projection onto the plane through its middle, along the way it faces on
        average.  It is made from the surface and moves with it: it has no points of its own to drag '''
    from fieldev.stdlib.selection import SurfaceSelection
    if isinstance(source, SurfaceSelection):
        return _from_surface(source)
    if isinstance(source, C.Curve):
        items = list(source.points)
        smooth = bool(smooth) or source.smooth          # (a curve that is a spline is a spline as the outline too)
    else:
        items = list(source)
    smooth = bool(smooth)
    if C.value_of(radius) < 0:
        raise ValueError('profile(..., radius=%g): a radius is not negative (0 is a hard corner)' % C.value_of(radius))
    ctrls = C.controls(items, rounds=True, radius_default=radius, smooth_default=smooth)
    C.mark(ctrls, smooth, 'profile')
    plane = C.plane_of(ctrls)
    if plane is None:
        out = C.owned(Shape.wrap(1e9), Profile)
        out.vertices, out._owners, out.plane, out.profile2d = [], [], None, out
    else:
        o, u, v = plane
        normal = C.cross(u, v)
        # (the rotation of a point of a profile is one angle, about the normal of its plane.)  The outline as it is drawn has every arc cut into pieces; the field is made on the
        # outline with every arc as its chord and the arcs themselves, which are exact
        verts, owners = C.trace(ctrls, smooth, True, normal=normal)
        rounded = [c for c in ctrls if c.rounded]
        if rounded:
            chord = C.trace(ctrls, smooth, True, normal=normal, arc_pieces=0)[0]
            arcs3 = C.fillets(ctrls, smooth, True, normal=normal)
        else:
            chord, arcs3 = verts, []
        loop = [(C.dot(C.sub(p, o), u), C.dot(C.sub(p, o), v)) for p in verts]
        loop_chord = [(C.dot(C.sub(p, o), u), C.dot(C.sub(p, o), v)) for p in chord]
        arcs_loop = [tuple((C.dot(C.sub(p, o), u), C.dot(C.sub(p, o), v)) for p in (a, b, c)) + (r,) for _i, a, b, c, r in arcs3]
        # The field is made in coordinates measured from the origin of space along u and v, not from the first point of the profile: the same shape, but a wall that stands at x = 12 is
        # `x - 12 = 0` there and `x = 12` here -- and the first one, turned by a gizmo or a symmetry, was meshed with teeth along its walls (a quarter turn of a solid made of it, the
        # kernel's mesher: +11 % of surface), the second is meshed exactly, as a box is
        from_origin = [(C.dot(p, u), C.dot(p, v)) for p in chord]
        arcs_origin = [tuple((C.dot(p, u), C.dot(p, v)) for p in (a, b, c)) + (r,) for _i, a, b, c, r in arcs3]
        field = _polygon_field(from_origin, ((0.0, 0.0, 0.0), u, v), arcs_origin)
        out = Profile(lib.libfive_tree_copy(field.ptr))
        out.plane = plane
        out.profile2d = _polygon_field(loop_chord, None, arcs_loop)
        out.vertices, out._owners = verts, owners
        out._outline_box = _box_of_points(verts)
        # (the middle of the box of the outline, in the plane's own coordinates: where a sweep puts the path -- through the middle of the profile, not through its first point)
        out._centre2d = (0.5 * (min(x for x, y in loop) + max(x for x, y in loop)), 0.5 * (min(y for x, y in loop) + max(y for x, y in loop)))
    out.points, out.smooth, out.radius = items, smooth, radius
    out._ctrls = ctrls
    C.viewport_data(out, ctrls, smooth, True)
    return out


profile._makes_no_gizmo = True
profile._makes_outline_gizmo = True


def _box_of_points(points):
    ''' The box that holds these points (3D numbers), or None when there are none '''
    pts = [tuple(float(c) for c in p) for p in points]
    if not pts:
        return None
    return tuple(min(p[k] for p in pts) for k in range(3)), tuple(max(p[k] for p in pts) for k in range(3))


def _linear(n, off):
    ''' The field n . (x, y, z) + off: a plane's distance, made of as few operations as it can be (no subtraction of a bare number: FielDev would offer that
        number as a handle) '''
    terms = None
    for axis, c in zip((Shape.X(), Shape.Y(), Shape.Z()), n):
        if abs(c) < 1e-15:
            continue
        t = axis * c
        terms = t if terms is None else terms + t
    if terms is None:
        return Shape.wrap(off)
    return terms + off if abs(off) > 1e-15 else terms


def extrude(shape, a, b):
    ''' A 2D shape pulled into a solid: the part of space between the distances `a` and `b` from its plane, along the plane's normal (the plane is
        z = 0 for the shapes that lie there -- a circle, a rectangle -- so that is zmin and zmax; the plane of a profile is the plane of its points,
        and the normal is the direction u x v of that plane).  `extrude(circle(5), 0, 10)` is a cylinder 10 tall '''
    shape = Shape.wrap(shape)
    plane = getattr(shape, 'plane', None)
    if plane is None:
        w = Shape.Z()
    else:
        o, u, v = plane
        n = C.cross(u, v)
        w = _linear(n, -C.dot(n, o))
    body = shape.max(Shape.wrap(a) - w).max(w - Shape.wrap(b))
    out = Shape(lib.libfive_tree_copy(body.ptr))
    # The box of the solid is known: the box of the outline of the face (what it is made from), carried along the normal from a to b.  It is not
    # searched for -- a search does not come to an end for a face with a curved outline -- so that the render region can hold the solid
    box = getattr(shape, '_outline_box', None)
    if box is not None and plane is not None:
        try:
            from fieldev.stdlib.handles import _var_numbers
            nums = _var_numbers([a, b])
        except Exception:
            nums = None
        if nums is not None:
            da, db = nums
            out._bounds = (tuple(box[0][k] + min(da * n[k], db * n[k]) for k in range(3)),
                           tuple(box[1][k] + max(da * n[k], db * n[k]) for k in range(3)))
    # A 2D shape that lies in the plane z = 0 (`plane` is None: a circle, a rectangle ...) has the box of its own outline (`_bounds`: its sides, the numbers of its handles, and of its gizmo when it
    # is placed); the box of its extrusion is that box carried along z from a to b.  Without it the box is searched for, and the search for a shape that a gizmo has placed does not come to an
    # end (the box touches the region it looks in): the render region did not grow for the extrusion and cut it off at its top -- a square of 5 extruded to 5 stood 1 high in the viewport
    if plane is None and getattr(out, '_bounds', None) is None:
        flat = getattr(shape, '_bounds', None)
        if flat and abs(float(flat[0][2])) < 1e-9 and abs(float(flat[1][2])) < 1e-9:
            try:
                from fieldev.stdlib.handles import _var_numbers
                nums = _var_numbers([a, b])
            except Exception:
                nums = None
            if nums is not None:
                out._bounds = ((float(flat[0][0]), float(flat[0][1]), min(nums)), (float(flat[1][0]), float(flat[1][1]), max(nums)))
                if getattr(shape, '_bounds_loose', False):
                    out._bounds_loose = True
    # A straight extrusion of a profile of points is a PRISM: the viewport draws it from the numbers of the points and of a and b at every render -- as it draws the face of
    # the profile -- so that it follows a point while the point is dragged, with no script run and no field meshed.  `_prism_guard` are the numbers (var()s) that must still
    # be what they were for the shape to be nothing but that prism: handles() and gizmo() add theirs (a pulled face, a placed shape make it something else)
    if getattr(shape, '_ctrl_pos', None) and plane is not None and getattr(shape, '_profile_face', None) is None and isinstance(shape, Profile):
        out._prism_pos = shape._ctrl_pos
        out._prism_rot = shape._ctrl_rot
        out._prism_flag = shape._ctrl_flag
        out._prism_scale = shape._ctrl_scale
        out._prism_radius = shape._ctrl_radius
        out._prism_default = shape._ctrl_default
        out._prism_a = Shape.wrap(a)
        out._prism_b = Shape.wrap(b)
        out._prism_guard = []
    # The handles of the extrusion of a shape that lies in a plane of its own (a profile of points) are its two ENDS -- a and b, the faces parallel to the shape: pulled, they are how long the
    # extrusion is -- and nothing else: what the tree of constants of such a field happens to hold (the numbers of its polygon, a plane through the origin) are not numbers anyone pulls.  Its
    # walls are the sides of the profile: pulled, they move the two points they are between (the viewport does that, from the points' own numbers), and the extrusion is made again of the
    # profile it was made of -- still the profile's, so it follows the points, and stays a prism that is drawn from their numbers while a or b is dragged
    if plane is not None and getattr(shape, '_ctrl_pos', None):
        try:
            from fieldev.stdlib.handles import _var_numbers
            ends = _var_numbers([a, b])
        except Exception:
            ends = None
        if ends is not None:
            out._handle_params = [float(x) for x in ends]
            out._handle_rebuild = lambda v: extrude(shape, v[0], v[1])
    # A 2D shape that is made of numbers of its own (a rectangle's four sides, a circle's centre and radius, a polygon's sides) hands them on: the handles of its extrusion are those numbers, and then a and
    # b -- the sides of the 2D shape pulled as they are on the shape itself, and the two end faces for the length --, whatever the shape is, and the extrusion is made again of the shape made again of them
    # (what the kernel found to expose in the extrusion's tree was most of them for most shapes and none of them for a rectangle)
    params = getattr(shape, '_handle_params', None)
    rebuild = getattr(shape, '_handle_rebuild', None)
    if plane is None and params is not None and rebuild is not None and getattr(out, '_handle_params', None) is None:
        try:
            from fieldev.stdlib.handles import _var_numbers
            ends = _var_numbers([a, b])
        except Exception:
            ends = None
        if ends is not None:
            count = len(params)
            out._handle_params = [float(x) for x in params] + [float(x) for x in ends]
            out._handle_rebuild = lambda v: extrude(rebuild(list(v[:count])), v[count], v[count + 1])
    # A 2D shape that has numbers of its own already -- a handles() and a gizmo() line, written when it was selected -- is placed by them: they are in the field of its extrusion, and the sides of the
    # extrusion are pulled by the handles (a pull never changes a gizmo's numbers).  What they do not reach are the two ENDS, a and b: those are the numbers of the extrusion, handles(extrusion, [a, b]),
    # made again of the shape as it is (the same 2D shape, with its numbers)
    if plane is None and getattr(out, '_handle_params', None) is None and _has_handles_of_its_own(shape):
        try:
            from fieldev.stdlib.handles import _var_numbers
            ends = _var_numbers([a, b])
        except Exception:
            ends = None
        if ends is not None:
            out._handle_params = [float(x) for x in ends]
            out._handle_rebuild = lambda v: extrude(shape, v[0], v[1])
            out._handles_ends_only = True
    return out


def _has_handles_of_its_own(shape):
    ''' Whether a 2D shape was given numbers to pull its sides by (handles()): the shape that handles() made, or the one that gizmo() placed after that '''
    for _ in range(8):
        if shape is None:
            return False
        if getattr(shape, '_pivot_shape', None) is not None:
            return True
        shape = getattr(shape, '_placed_from', None)
    return False


def _profile_at(profile, a, b, size=None, centre=None, grow=None):
    ''' The 2D shape as a field of two coordinates a and b (fields): where its own plane's origin is the point of the path and a, b run along its own two axes
        -- x and y for a shape in the plane z = 0, u and v for a profile.  `size` (a field, or None): how many times as big it is there -- the shape
        is looked at from 1 / size as far, and the distance it says is made as many times as long, so that it is still a distance.  `grow` (a number, with `size`): the outline is moved out by
        (size - 1) times it instead -- in where size is below 1 --, the section grown or thinned by an offset, not scaled (see `path_extrude(sizing='offset')`) '''
    profile = Shape.wrap(profile)
    inner = getattr(profile, 'profile2d', None)
    base = inner if inner is not None else profile
    # A profile is carried by the MIDDLE of its outline (the box of it), so that the path runs through the middle of what is swept, not along its first point; the
    # thickness of a point scales the profile about that middle too
    # (`centre`: the middle of the box of a shape in the plane z = 0 that is not a profile -- see path_extrude)
    cx, cy = centre if centre is not None else getattr(profile, '_centre2d', (0.0, 0.0))
    if size is None:
        return base.remap(a + cx if cx else a, b + cy if cy else b, Shape.wrap(0))
    if grow is not None:
        return base.remap(a + cx if cx else a, b + cy if cy else b, Shape.wrap(0)) - (size - 1.0) * grow
    return base.remap(a / size + cx if cx else a / size, b / size + cy if cy else b / size, Shape.wrap(0)) * size


def _transported(p0, p1, t0, t1, n0):
    ''' The normal at the next vertex, carried along from this one without turning about the path (the double reflection of Wang et al.): the places of
        the two vertices, their tangents, and the normal here '''
    v1 = C.sub(p1, p0)
    c1 = C.dot(v1, v1) + 1e-300
    rl = C.sub(n0, C.mul(v1, C.dot(v1, n0) * 2 / c1))
    tl = C.sub(t0, C.mul(v1, C.dot(v1, t0) * 2 / c1))
    v2 = C.sub(t1, tl)
    c2 = C.dot(v2, v2) + 1e-300
    return C.sub(rl, C.mul(v2, C.dot(v2, rl) * 2 / c2))


def _turned(v, t, cs, sn):
    ''' The vector `v` turned about the unit vector `t` by the angle whose cosine and sine are given (Rodrigues) '''
    return C.add(C.add(C.mul(v, cs), C.mul(C.cross(t, v), sn)), C.mul(t, C.dot(t, v) * (1.0 - cs)))


def _across_frame(bu, bv, t):
    ''' The two axes of a profile (`bu`, `bv`) turned the least that puts its plane across the direction `t`: (u, v) -- the same two when it is across already --, or None when the plane holds
        the direction (|n . t| below 0.1: nothing could be swept, the caller turns it another way) '''
    n = C.unit(C.cross(bu, bv))
    d = C.dot(n, t)
    if abs(d) < 0.1:
        return None
    if abs(d) >= 1.0 - 1e-9:
        return bu, bv
    target = t if d > 0 else C.mul(t, -1.0)
    axis = C.cross(n, target)
    s = math.sqrt(C.dot(axis, axis))
    axis = C.mul(axis, 1.0 / s)
    c = abs(d)

    def turn(v):
        return C.add(C.add(C.mul(v, c), C.mul(C.cross(axis, v), s)), C.mul(axis, C.dot(axis, v) * (1.0 - c)))
    return turn(bu), turn(bv)


@functools.lru_cache(maxsize=64)
def _inscribed_of(pts):
    n = len(pts)
    if n < 3:
        return 0.0, (0.0, 0.0)
    lox, hix = min(p[0] for p in pts), max(p[0] for p in pts)
    loy, hiy = min(p[1] for p in pts), max(p[1] for p in pts)

    def depth(x, y):
        inside = False
        best = 1e300
        for i in range(n):
            ax, ay = pts[i]
            bx, by = pts[(i + 1) % n]
            if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
                inside = not inside
            dx, dy = bx - ax, by - ay
            l2 = dx * dx + dy * dy
            t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / l2)) if l2 > 0 else 0.0
            px, py = ax + t * dx - x, ay + t * dy - y
            d2 = px * px + py * py
            if d2 < best:
                best = d2
        d = math.sqrt(best)
        return d if inside else -d
    bx, by = 0.5 * (lox + hix), 0.5 * (loy + hiy)
    bd = depth(bx, by)
    cells = 24
    sx, sy = (hix - lox) / cells, (hiy - loy) / cells
    for i in range(cells):
        for j in range(cells):
            x, y = lox + (i + 0.5) * sx, loy + (j + 0.5) * sy
            d = depth(x, y)
            if d > bd:
                bd, bx, by = d, x, y
    wx, wy = sx, sy
    for _ in range(6):
        cx, cy = bx, by
        for i in range(-2, 3):
            for j in range(-2, 3):
                x, y = cx + i * wx * 0.5, cy + j * wy * 0.5
                d = depth(x, y)
                if d > bd:
                    bd, bx, by = d, x, y
        wx *= 0.5
        wy *= 0.5
    return (bd, (bx, by)) if bd > 0 else (0.0, (0.0, 0.0))


def _inscribed(points):
    ''' The widest circle that fits inside the closed outline `points` [(x, y)]: (its radius, its middle) -- found on a grid over the box of the outline, then narrowed in on (the viewport's
        Shape::sweepMesh does the same on the same outline, so that the field and the picture offset by the same amount); (0, ...) for an outline that holds none '''
    return _inscribed_of(tuple((round(float(x), 9), round(float(y), 9)) for x, y in points))


def path_extrude(profile, path, twist=0, ends=None, sizing='scale', across=False):
    ''' A 2D shape swept along a curve: the `profile` -- its own axes across the curve (x and y for a shape in the plane z = 0, the two axes of the plane of a profile) -- carried
        along `path`, turning with it, without twisting about it unless the points of the curve say so.
        THE 2D SHAPE IS WHERE THE SWEEP STARTS: the curve says how it travels, not where from -- the whole sweep is moved so that the first point of the curve is the middle of
        the shape (the middle of the box of its outline), and its first ring is the shape itself, in its own plane at whatever angle the curve leaves it (the sweep is slanted
        when it is oblique; a shape whose plane holds the direction of the curve is turned across it), so that the shape you edit is the base of what it is swept into.  A circle
        or a rectangle is such a shape as a profile is.  The path is DRAWN where the sweep goes -- through the middle of its cross-section, from the middle of the shape, its
        points with it -- whatever its own numbers say; only its shape matters, and the first point of it is the middle of the shape:
        the ROTATION of a point (its gizmo's rotate numbers) twists the profile about the curve there, and the twist runs between the points as a
        smooth change.  `twist` (degrees) turns the whole profile about the curve besides.  The ends are cut square.  A curve with corners is swept
        with mitered joints.  `path_extrude(circle(2), spline([a, b, c]))` is a bent tube; `extrude` is the straight case.  `path` may be a list of points:
        the spline through them.
        ends     (round at the start, round at the end): an end that is True is a DOME instead of the flat face of the profile -- past the end of the path the profile shrinks along a
                 quarter of a circle (its size at a distance d from the end is the size there times sqrt(1 - (d / reach)^2), `reach` as long as the profile is wide), so that the end is the
                 profile's own shape closing, as long as the middle of its box is inside it or the shape can be seen from there (round, convex and star-like sections: a plus, a triangle; not a U or an L,
                 whose notch the dome covers).  The viewport builds the same dome from rings (Shape::sweepMesh).
        sizing   what the thickness of a point (its scale) does to the section: 'scale' (the default) multiplies the whole section about the middle of its box; 'offset' moves its outline in or out by
                 (scale - 1) times the radius of the widest circle the section holds -- so a thinner section of ANY shape (a U, an L) stays inside a thicker one, and the radius of that circle is
                 exactly the scale -- and the round ends close along the same offset (the section eroded along a quarter of a circle).  Where an offset folds (a notch narrower than the push, an arm
                 thinner than the pull) the field fills it in or lets it vanish, and the viewport holds the outline on the middle line of it
        across   True: the first section is turned the least that puts it across the path, so that both ends of an open sweep are square to it (an armature is made so); False: the section stays
                 in its own plane -- the shape you edit is the base of the sweep -- and is cut slanted when the path leaves it at an angle '''
    ends = (False, False) if ends is None else (bool(ends[0]), bool(ends[1]))
    if sizing not in ('scale', 'offset'):
        raise ValueError("path_extrude: sizing is 'scale' or 'offset', not %r" % (sizing,))
    if isinstance(path, (list, tuple)):
        from fieldev.stdlib.curves import spline
        path = spline(path)
    if not isinstance(path, C.Curve):
        raise TypeError('path_extrude(profile, path): the path is a curve (polyline([points]), spline([points])), or a list of points')
    V = list(path.vertices)
    owners = list(path._owners)
    n = len(V)
    if n < 2:
        return C.owned(Shape.wrap(1e9))
    # A sweep is a field of one piece for each piece of the path, each carrying the whole profile: a path of hundreds of pieces is a field that takes the renderer
    # minutes.  A path that long is thinned -- every point that was made stays (the corners and the places the twist and the thickness are given), the pieces of the
    # curves between them are made fewer -- so that the sweep can be drawn
    limit = 160
    if n > limit + 1:
        every = -(-n // limit)
        keep = [j for j in range(n) if j % every == 0 or owners[j][1] == 0.0 or j == n - 1]
        V = [V[j] for j in keep]
        owners = [owners[j] for j in keep]
        n = len(V)
    # The 2D shape is where the sweep STARTS (the path says how it travels): the sweep is moved so that the first point of the path is the middle of the shape -- the middle of
    # the box of its outline -- and (below) its first ring is the shape, so that the shape being edited is the base of what it is swept into.  A profile has its own plane; a
    # shape in the plane z = 0 (a circle, a rectangle, whatever a gizmo or handles() has made of one) has the plane z = 0, its axes x and y
    base_plane = None
    centre2d = (0.0, 0.0)
    ring = None                 # (the outline in numbers, from the middle of the box of it: the box of the sweep, and what the viewport draws a sweep of points from)
    primitive_ring = None       # (the same, as expressions of the numbers of a primitive: what the viewport draws a sweep of a primitive from)
    box_ring = None             # (the four corners of the box of a shape that has no outline to give, from the middle of it)
    if isinstance(profile, (Profile, SurfaceProfile)) and getattr(profile, 'plane', None) is not None:
        base_plane = profile.plane
        centre2d = getattr(profile, '_centre2d', (0.0, 0.0))
    elif not isinstance(profile, (Profile, SurfaceProfile)):
        outline = None
        make = getattr(profile, '_ring_points', None) if getattr(path, '_ctrl_pos', None) else None
        if make is not None:
            try:
                points = make()
                if points:
                    expressions = [(Shape.wrap(x), Shape.wrap(y)) for x, y in points]
                    numbers = [(C.value_of(x), C.value_of(y)) for x, y in expressions]
                    if all(math.isfinite(v) for xy in numbers for v in xy):
                        primitive_ring, outline = expressions, numbers
            except Exception:
                primitive_ring = outline = None
        if outline is None:
            try:
                (bx0, by0, bz0), (bx1, by1, bz1) = profile._bounds
                if all(math.isfinite(v) for v in (bx0, by0, bz0, bx1, by1, bz1)) and abs(bz0) < 1e-9 and abs(bz1) < 1e-9:
                    outline = [(bx0, by0), (bx1, by0), (bx1, by1), (bx0, by1)]
            except Exception:
                outline = None
        if outline:
            centre2d = (0.5 * (min(x for x, y in outline) + max(x for x, y in outline)), 0.5 * (min(y for x, y in outline) + max(y for x, y in outline)))
            base_plane = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
            relative = [(x - centre2d[0], y - centre2d[1]) for x, y in outline]
            if primitive_ring is not None:
                ring = relative
            else:
                box_ring = relative
    if base_plane is not None:
        bo, bu, bv = base_plane
        bx, by = centre2d
        middle = tuple(bo[k] + bx * bu[k] + by * bv[k] for k in range(3))
        shift = C.sub(middle, V[0])
        # The path is drawn where the sweep goes (see Curve._display and points.displayed): moved by the same amount, with its points, so that it runs through the middle of the
        # cross-section at all times -- the numbers in the script are not changed
        path._weld_shift = tuple(shift)
        for p in path.points:
            try:
                p._weld_shift = tuple(shift)
            except AttributeError:
                pass
        V = [C.add(p, shift) for p in V]
    closed = path.closed
    pieces = n if closed else n - 1
    T = [C.unit(C.sub(V[(k + 1) % n], V[k])) for k in range(pieces)]

    def tangent_at(k):
        # the vertex's own direction: along the one piece at the end of an open path, between the two pieces elsewhere (a closed path wraps)
        if closed:
            return C.unit(C.add(T[k - 1], T[k]))
        if k == 0:
            return T[0]
        if k == n - 1:
            return T[pieces - 1]
        return C.unit(C.add(T[k - 1], T[k]))

    # The frames.  A PROFILE is carried along the path as it is -- its two axes u and v, turned with the path (each next frame carried along without turning about the path:
    # the double reflection of Wang et al.) -- so that the first ring is the profile itself, at whatever angle the path leaves it.  A profile whose plane holds the direction of
    # the path (nothing could be swept) and every other profile start across the path: from the axis it is least along (so a path that starts up the z axis has the profile's
    # x along x and y along y)
    U = [None] * pieces
    W = [None] * pieces
    if base_plane is not None:
        bu, bv = base_plane[1], base_plane[2]
        turned_first = _across_frame(bu, bv, T[0]) if across else None
        if turned_first is not None:
            U[0], W[0] = turned_first
        elif abs(C.dot(C.unit(C.cross(bu, bv)), T[0])) >= 0.1:
            U[0], W[0] = bu, bv
    if U[0] is None:
        first = None
        if base_plane is not None:
            # (the profile's own axis u, across the path -- v when the path leaves along u)
            for across in (base_plane[1], base_plane[2]):
                candidate = C.sub(across, C.mul(T[0], C.dot(across, T[0])))
                if C.dot(candidate, candidate) > 1e-12:
                    first = C.unit(candidate)
                    break
        if first is None:
            axis = min(range(3), key=lambda i: abs(T[0][i]))
            ref = tuple(1.0 if i == axis else 0.0 for i in range(3))
            first = C.unit(C.add(C.mul(T[0], -C.dot(ref, T[0])), ref))
        U[0], W[0] = first, C.cross(T[0], first)
    for k in range(pieces - 1):
        U[k + 1] = C.unit(_transported(V[k], V[k + 1], T[k], T[k + 1], U[k]))
        W[k + 1] = C.unit(_transported(V[k], V[k + 1], T[k], T[k + 1], W[k]))
    # the frame the twist is measured in, across the path: u across it (v when u lies along it) -- u itself when the profile is across the path
    N, B = [], []
    for k in range(pieces):
        across = C.sub(U[k], C.mul(T[k], C.dot(U[k], T[k])))
        if C.dot(across, across) < 1e-12:
            across = C.sub(W[k], C.mul(T[k], C.dot(W[k], T[k])))
        N.append(C.unit(across))
        B.append(C.cross(T[k], N[k]))
    # the twist: a point's rotation turns its normal about the path; between the points the angle runs along the line
    ctrls = path._ctrls
    angle_of = {}
    for i, c in enumerate(ctrls):
        if not c.turned:
            continue
        vertex = next((j for j, o in enumerate(owners) if o[0] == i and o[1] == 0.0), None)
        if vertex is None:
            continue
        k = min(vertex, pieces - 1)
        nr = C.rotated(N[k], c.rot)
        angle_of[i] = math.atan2(C.dot(nr, B[k]), C.dot(nr, N[k]))

    def roll_at(j):
        i, t = owners[j]
        a0 = angle_of.get(i, 0.0)
        i1 = (i + 1) % len(ctrls)
        a1 = angle_of.get(i1, 0.0) if (closed or i + 1 < len(ctrls)) else a0
        return a0 * (1 - t) + a1 * t

    total = math.radians(C.value_of(twist))
    # the scale of a point is how thick the profile is there; between the points it runs along the line, as the twist does
    sizes = [c.scale for c in ctrls]

    def size_at(j):
        i, t = owners[j]
        s0 = sizes[i]
        i1 = (i + 1) % len(ctrls)
        s1 = sizes[i1] if (closed or i + 1 < len(ctrls)) else s0
        return max(s0 * (1 - t) + s1 * t, 1e-3)

    # The profile as the rings of the sweep have it: the outline of a profile, from the middle of it (the extent of the rings is the box of the sweep)
    if isinstance(profile, Profile) and getattr(profile, '_ctrl_pos', None) and getattr(path, '_ctrl_pos', None) and getattr(profile, 'plane', None) is not None:
        po, pu, pv = profile.plane
        cx, cy = centre2d
        ring = [(C.dot(C.sub(p, po), pu) - cx, C.dot(C.sub(p, po), pv) - cy) for p in profile.vertices]
    # The box of the sweep.  A profile that is not drawn from numbers (an offset of a circle, a profile of a path that is not made of points ...) is meshed from its field, and the
    # field of a sweep has no box that can be found in the time there is: the box the profile was told (its `_bounds`) carried along the path is one that holds the sweep, so
    # that the render region grows to hold it -- the region of the scene is not a place the sweep is cut off at
    if box_ring is None:
        box_ring = ring
    if box_ring is None:
        try:
            (bx0, by0, _bz0), (bx1, by1, _bz1) = profile._bounds
            if all(math.isfinite(v) for v in (bx0, by0, bx1, by1)):
                box_ring = [(bx0, by0), (bx1, by0), (bx1, by1), (bx0, by1)]
        except Exception:
            box_ring = None
    # The radius of the widest circle the section holds: what an offset is measured by (`sizing='offset'`), and how far a round end reaches in
    inner = _inscribed(ring or box_ring)[0] if (ring or box_ring) else 0.0
    grow = inner if (sizing == 'offset' and inner > 1e-9) else None
    lo = [1e300] * 3
    hi = [-1e300] * 3
    best = None
    for k in range(pieces):
        j = (k + 1) % n
        phi = (roll_at(k) + roll_at(j)) * 0.5 + total
        cs, sn = math.cos(phi), math.sin(phi)
        nk, bk = _turned(U[k], T[k], cs, sn), _turned(W[k], T[k], cs, sn)
        # (where a point is on the profile's plane, seen along the path: its coordinates a and b along the two axes of the profile -- the way they are when the profile is
        # across the path, and slanted when the path leaves the profile at an angle)
        det = C.dot(nk, C.cross(bk, T[k]))
        ra, rb = C.mul(C.cross(bk, T[k]), 1.0 / det), C.mul(C.cross(T[k], nk), 1.0 / det)
        a = _linear(ra, -C.dot(ra, V[k]))
        b = _linear(rb, -C.dot(rb, V[k]))
        s0, s1 = size_at(k), size_at(j)
        if box_ring:
            for end, sz in ((k, s0), (j, s1)):
                # (an offset section is the outline as it is, pushed out by at most (scale - 1) * the radius of the widest circle it holds)
                push = 0.0 if grow is None else max(sz - 1.0, 0.0) * grow
                for px, py in box_ring:
                    for axis in range(3):
                        x = V[end][axis] + (sz if grow is None else 1.0) * (px * nk[axis] + py * bk[axis])
                        lo[axis] = min(lo[axis], x - push)
                        hi[axis] = max(hi[axis], x + push)
        size = None
        if abs(s0 - 1) > 1e-9 or abs(s1 - 1) > 1e-9:
            # (thicker or thinner here: the size runs along the piece from one end to the other)
            span = math.sqrt(C.dot(C.sub(V[j], V[k]), C.sub(V[j], V[k]))) + 1e-300
            slope = (s1 - s0) / span
            size = _linear(C.mul(T[k], slope), s0 - C.dot(T[k], V[k]) * slope).max(1e-3)
        f = _profile_at(profile, a, b, size, centre2d, grow)
        # the piece ends at the planes that bisect the corners (square at the ends of an open path), a hair past them, so that two pieces overlap there and
        # the joint is inside, not a plane where the field is zero
        mk, mj = tangent_at(k), tangent_at(j)
        if base_plane is not None and not closed and (k == 0 or k == pieces - 1):
            # (the ends of the sweep of a profile are the profile -- the one that was drawn at the start, its copy at the end -- not cut square across the path)
            flat = C.cross(nk, bk)
            side = 1.0 if C.dot(flat, T[k]) >= 0 else -1.0
            if k == 0:
                mk = C.mul(flat, side)
            if k == pieces - 1:
                mj = C.mul(flat, side)
        start = _linear(C.mul(mk, -1.0), C.dot(mk, V[k]) - 1e-3)
        stop = _linear(mj, -C.dot(mj, V[j]) - 1e-3)
        body = f.max(start).max(stop)
        best = body if best is None else best.min(body)
    # Round ends: past the end of an open path the cross-section shrinks along a quarter of a circle, so that the end is a dome of the cross-section itself and not a ball that its shape
    # clashes with.  It is one more piece of the sweep: the profile in the frame of the end piece (the ring's own plane, which is across the path unless the path leaves the profile at an
    # angle), at the size that runs down to nothing at the tip, between the plane of the end and the tip
    dome_ring = ring or box_ring
    if not closed and dome_ring and best is not None and any(ends):
        reach0 = sum(math.hypot(x, y) for x, y in dome_ring) / len(dome_ring)
        for at_start in (True, False):
            if not ends[0 if at_start else 1]:
                continue
            k = 0 if at_start else pieces - 1
            j = (k + 1) % n
            phi = (roll_at(k) + roll_at(j)) * 0.5 + total
            cs, sn = math.cos(phi), math.sin(phi)
            nk, bk = _turned(U[k], T[k], cs, sn), _turned(W[k], T[k], cs, sn)
            flat = C.cross(nk, bk)
            side = 1.0 if C.dot(flat, T[k]) >= 0 else -1.0
            axis = C.mul(flat, -side if at_start else side)             # (out of the sweep)
            end_at = V[0] if at_start else V[n - 1]
            size0 = size_at(0 if at_start else n - 1)
            d = _linear(axis, -C.dot(axis, end_at))                     # (how far past the plane of the end)
            a = _linear(nk, -C.dot(nk, end_at))
            b = _linear(bk, -C.dot(bk, end_at))
            start = _linear(C.mul(axis, -1.0), C.dot(axis, end_at) - 1e-3)
            if grow is None:
                # (the section shrinking along a quarter of a circle, about the middle of its box)
                reach = max(reach0 * size0, 1e-6)
                size = ((1.0 - (d * (1.0 / reach)).square()).max(1e-6).sqrt() * size0).max(1e-3)
                f = _profile_at(profile, a, b, size, centre2d)
            else:
                # (the section of the node, eroded: its outline moved in along a quarter of a circle until the widest circle it holds is gone -- every section of the dome lies inside the one below it)
                reach = max(inner * size0, 1e-6)
                closing = (d.square() * -1.0 + reach * reach).max(1e-9).sqrt()
                f = _profile_at(profile, a, b, None, centre2d) - (size0 - 1.0) * grow + (closing * -1.0 + reach)
            best = best.min(f.max(start).max(d - reach))
            for axis_i in range(3):
                lo[axis_i] = min(lo[axis_i], end_at[axis_i] + axis[axis_i] * reach)
                hi[axis_i] = max(hi[axis_i], end_at[axis_i] + axis[axis_i] * reach)
    out = Shape(lib.libfive_tree_copy(best.ptr))
    out._sweep_inner = float(inner)         # (the radius of the widest circle the section holds: what the ring of a node is measured by when the sweep is offset)
    if box_ring:
        # (the box of the rings: one that holds the sweep, not its exact extent)
        pad = 0.02 * max(hi[a] - lo[a] for a in range(3)) + 1e-3
        out._bounds = (tuple(lo[a] - pad for a in range(3)), tuple(hi[a] + pad for a in range(3)))
        out._bounds_loose = True
    if ring:
        # A sweep of a profile is drawn natively from the numbers of the points of the profile and of the path (as a straight extrusion is: see `extrude`), so it
        # follows a point while the point is dragged and nothing is meshed.  Its field (above) is for what is made *of* it -- and it is not searched for or counted
        # for handles: it is a field of thousands of terms
        out._kind = 'solid'
        out._no_handles = True
        if primitive_ring is not None:
            # (the outline of a primitive: corners in the plane z = 0, its axes x and y -- the sweep starts at it, as at a profile)
            zero = Shape.wrap(0.0)
            out._sweep_ppos = [(x, y, zero) for x, y in primitive_ring]
            out._sweep_prot = [None] * len(primitive_ring)
            out._sweep_pflag = [0] * len(primitive_ring)
            out._sweep_pscale = [None] * len(primitive_ring)
            out._sweep_pradius = [None] * len(primitive_ring)
            out._sweep_pdefault = False
            out._sweep_free = True
            # (numbers that must stay what they are for the outline to be the shape's: a gizmo's turn about x or y, its move along z -- see handles.gizmo)
            out._sweep_guard = list(getattr(profile, '_ring_guard', []))
        else:
            out._sweep_ppos, out._sweep_prot = profile._ctrl_pos, profile._ctrl_rot
            out._sweep_pflag, out._sweep_pscale, out._sweep_pdefault = profile._ctrl_flag, profile._ctrl_scale, profile._ctrl_default
            out._sweep_pradius = profile._ctrl_radius
        out._sweep_qpos, out._sweep_qrot = path._ctrl_pos, path._ctrl_rot
        out._sweep_qflag, out._sweep_qscale, out._sweep_qdefault = path._ctrl_flag, path._ctrl_scale, path._ctrl_default
        out._sweep_qclosed = bool(path.closed)
        out._sweep_twist = Shape.wrap(twist)
        out._sweep_round = ends
        out._sweep_offset = grow is not None
        out._sweep_across = bool(across)
        out._drawn_key = _sweep_key          # (what tells whether two sweeps are the same shape without meshing either: see symmetries.symmetry_images, distinct=True)
    return out


def _sweep_key(s):
    ''' What a sweep is drawn from, as a key: two sweeps with the same key are the same shape -- the same outline carried along the same path, the same thickness and twist --
        so that the images of a sweep that are the sweep itself (a tube along a path that lies in a plane of the symmetry is its own image in it) are told without sampling its
        field, which is thousands of terms.  None for a sweep that is not drawn from such numbers (its gizmo turns or scales it).  The outline is the same from whichever of its points
        it starts and whichever way round it goes '''
    def num(v):
        return C.value_of(v) if isinstance(v, Shape) else float(v)

    def q(v):
        return int(round(num(v) * 1e5))                 # (a hundredth of a micrometre: numbers that agree to that are the same)
    try:
        move = (0.0, 0.0, 0.0)
        place = getattr(s, '_sweep_place', None)
        if place is not None:
            _about, mv, rot, scale = place
            if any(abs(num(v)) > 1e-9 for v in rot) or any(abs(num(v) - 1.0) > 1e-9 for v in scale):
                return None
            move = tuple(num(v) for v in mv)

        def points(ppos, prot, pflag, pscale):
            return [(tuple(q(num(p[i]) + move[i]) for i in range(3)), () if r is None else tuple(q(c) for c in r), int(f), () if sc is None else (q(sc),))
                    for p, r, f, sc in zip(ppos, prot, pflag, pscale)]
        ring = points(s._sweep_ppos, s._sweep_prot, s._sweep_pflag, s._sweep_pscale)
        path = points(s._sweep_qpos, s._sweep_qrot, s._sweep_qflag, s._sweep_qscale)
        n = len(ring)
        outline = min(tuple(run[i:] + run[:i]) for run in (ring, ring[::-1]) for i in range(max(n, 1)))
        return ('sweep', outline, tuple(path), bool(s._sweep_qclosed), q(s._sweep_twist), bool(getattr(s, '_sweep_free', False)),
                bool(s._sweep_pdefault), bool(s._sweep_qdefault), tuple(bool(v) for v in getattr(s, '_sweep_round', ())),
                bool(getattr(s, '_sweep_offset', False)), bool(getattr(s, '_sweep_across', False)))
    except (AttributeError, TypeError, ValueError):
        return None

# What these take (see fieldev.kinds.takes): a 2D shape pulled into a solid; a 2D shape, and the curve it is swept along or the points of one
from fieldev.kinds import takes as _declare
extrude._takes = _declare({'profile'}, [{'profile'}])
path_extrude._takes = _declare({'profile', 'curve', 'point'}, [{'profile'}, {'curve', 'point'}])
