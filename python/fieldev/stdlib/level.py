'''
Levels: rooms, corridors, doorways and the walls round them, as fields.

You say where the EMPTY space is -- rooms and corridors, the way you would sketch a floor plan -- and the walls are what is left round it: a wall is the same thickness
everywhere, two rooms that touch share one wall, a corridor that runs into a room opens into it, and a doorway is a cutter that goes through whatever is there.  Nothing is
stitched: the shell is `grown space minus space`.

    hall = room((0, 0, 0), (12, 8, 3.5))
    cell = room((16, 1, 0), (22, 7, 3.5))
    link = corridor([(10, 4, 0), (19, 4, 0)], width=2.4, height=2.8)           # from inside the hall to inside the cell
    gate = doorway((0, 4, 0), width=1.6, height=2.4, axis="x", arch=True)      # in the west wall of the hall
    keep = build_level([hall, cell, link], openings=[gate], solids=[staircase((2, 1, 0), (2, 7, 3.0), width=1.6, steps=12)])

Everything is in the unit of the model (1 = a metre if you think in metres).  A wall's thickness is `wall` (0.4 by default), the floor's `floor` and the ceiling's `ceiling`.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import math

from fieldev.shape import Shape
from fieldev.stdlib.fields import union_all
from fieldev.stdlib.shapes import box, _bounded

__all__ = ['Space', 'room', 'corridor', 'doorway', 'window_opening', 'pillar', 'staircase', 'wall_segment', 'build_level']


class Space:
    ''' A place that is empty inside and has walls round it: `inside` is the empty body, `outside` the body grown by the walls; `bounds` the box of the walls '''

    def __init__(self, inside, outside, lo, hi):
        self.inside = inside
        self.outside = outside
        self.bounds = (tuple(lo), tuple(hi))


def _p3(p, what):
    p = list(getattr(p, 'xyz', p))
    if len(p) == 2:
        p.append(0.0)
    if len(p) != 3:
        raise ValueError('%s: a place is (x, y) or (x, y, z), not %r' % (what, p))
    return tuple(float(c) for c in p)


def room(a, b, wall=0.4, floor=None, ceiling=None):
    ''' A room: the empty box between the corners `a` and `b` (the floor is at the lower z, the ceiling at the higher), with walls `wall` thick, a floor `floor` thick (the wall's
        thickness by default) and a ceiling `ceiling` thick '''
    a, b = _p3(a, 'room'), _p3(b, 'room')
    lo = [min(a[i], b[i]) for i in range(3)]
    hi = [max(a[i], b[i]) for i in range(3)]
    wall = float(wall)
    floor = wall if floor is None else float(floor)
    ceiling = wall if ceiling is None else float(ceiling)
    big_lo = (lo[0] - wall, lo[1] - wall, lo[2] - floor)
    big_hi = (hi[0] + wall, hi[1] + wall, hi[2] + ceiling)
    return Space(box(lo, hi), box(big_lo, big_hi), big_lo, big_hi)


def _piece(a, b, width, below, above, start, end):
    ''' The straight piece of a corridor from `a` to `b` (x, y, z; z is the floor): `width` across, `below` under the floor and `above` over it, reaching `start` before `a` and
        `end` beyond `b`.  Its floor runs from the height of `a` to the height of `b`: a ramp when they differ '''
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    if length < 1e-9:
        raise ValueError('corridor: two places of the path are the same in x and y')
    ux, uy = dx / length, dy / length
    px, py = Shape.X() - a[0], Shape.Y() - a[1]
    u = px * ux + py * uy                           # (along the piece)
    v = px * (-uy) + py * ux                        # (across it)
    t = (u * (1.0 / length)).max(0.0).min(1.0)
    floor_z = a[2] + t * (b[2] - a[2])
    side = v.abs() - width / 2.0
    ends = (u - (length + end)).max(-u - start)
    return side.max(ends).max((floor_z - below) - Shape.Z()).max(Shape.Z() - (floor_z + above))


def corridor(points, width=2.0, height=2.6, wall=0.4, floor=None, ceiling=None):
    ''' A corridor along `points` (places (x, y, z): z is the height of its floor, so that two places at different heights make a ramp), `width` wide and `height` high inside.
        It ends where the last place is: put the first and the last inside the rooms it joins, and it opens into them '''
    pts = [_p3(p, 'corridor') for p in points]
    if len(pts) < 2:
        raise ValueError('corridor: two places at least')
    wall = float(wall)
    floor = wall if floor is None else float(floor)
    ceiling = wall if ceiling is None else float(ceiling)
    width, height = float(width), float(height)
    inside, outside = [], []
    n = len(pts) - 1
    for i in range(n):
        a, b = pts[i], pts[i + 1]
        first, last = i == 0, i == n - 1
        inside.append(_piece(a, b, width, 0.0, height, 0.0 if first else width / 2.0, 0.0 if last else width / 2.0))
        outside.append(_piece(a, b, width + 2.0 * wall, floor, height + ceiling, wall if first else width / 2.0 + wall, wall if last else width / 2.0 + wall))
    reach = width / 2.0 + wall
    lo = [min(p[0] for p in pts) - reach, min(p[1] for p in pts) - reach, min(p[2] for p in pts) - floor]
    hi = [max(p[0] for p in pts) + reach, max(p[1] for p in pts) + reach, max(p[2] for p in pts) + height + ceiling]
    inner, outer = union_all(inside), union_all(outside)
    _bounded(inner, lo, hi)
    _bounded(outer, lo, hi)
    return Space(inner, outer, lo, hi)


def _cut(position, width, height, depth, axis, arch):
    px, py, pz = _p3(position, 'opening')
    if axis not in ('x', 'y'):
        raise ValueError("opening: axis is 'x' or 'y' -- the way you go through it")
    half = depth / 2.0
    if axis == 'x':
        straight_hi = (px + half, py + width / 2.0, pz + height - (width / 2.0 if arch else 0.0))
        lo = (px - half, py - width / 2.0, pz)
        round_axis = lambda zc: ((Shape.Y() - py).square() + (Shape.Z() - zc).square()).sqrt() - width / 2.0
        along = (Shape.X() - px).abs() - half
    else:
        straight_hi = (px + width / 2.0, py + half, pz + height - (width / 2.0 if arch else 0.0))
        lo = (px - width / 2.0, py - half, pz)
        round_axis = lambda zc: ((Shape.X() - px).square() + (Shape.Z() - zc).square()).sqrt() - width / 2.0
        along = (Shape.Y() - py).abs() - half
    body = box(lo, straight_hi)
    if arch:
        top = round_axis(pz + height - width / 2.0).max(along)
        body = body.min(top)
    reach_lo = (px - max(half, width), py - max(half, width), pz)
    reach_hi = (px + max(half, width), py + max(half, width), pz + height)
    _bounded(body, list(reach_lo), list(reach_hi))
    return body


def doorway(position, width=1.2, height=2.2, depth=2.0, axis='x', arch=False):
    ''' A cutter for a door: where a wall is to be open.  `position` is the middle of the bottom of the opening, in the wall; `axis` the way you go through it ('x' or 'y');
        `depth` how far the cutter reaches (more than the wall is thick); `arch`: round at the top.  Pass it to `build_level(openings=[...])` '''
    return _cut(position, float(width), float(height), float(depth), axis, bool(arch))


def window_opening(position, width=1.2, height=1.0, sill=1.0, depth=2.0, axis='x', arch=False):
    ''' A cutter for a window: like `doorway`, `sill` above the place given (the floor) '''
    px, py, pz = _p3(position, 'window_opening')
    return _cut((px, py, pz + float(sill)), float(width), float(height), float(depth), axis, bool(arch))


def pillar(center, radius=0.4, height=3.0, base=0.0, square=False, capital=0.0):
    ''' A pillar standing at `center` (x, y) from the height `base`: round, or square when `square`; `capital`: how high a wider cap on top is '''
    from fieldev.stdlib.shapes import cylinder
    cx, cy = float(center[0]), float(center[1])
    r, h = float(radius), float(height)
    if square:
        body = box((cx - r, cy - r, base), (cx + r, cy + r, base + h))
        if capital:
            body = body.min(box((cx - 1.4 * r, cy - 1.4 * r, base + h - capital), (cx + 1.4 * r, cy + 1.4 * r, base + h)))
        return body
    body = cylinder(r, h, base=(cx, cy, float(base)))
    if capital:
        body = body.min(cylinder(1.4 * r, float(capital), base=(cx, cy, float(base) + h - float(capital))))
    return body


def staircase(start, end, width=1.5, steps=10, fill=None):
    ''' Stairs: solid steps from `start` (x, y, z: the bottom of the first riser) to `end` (the top of the last), `width` across, `steps` of them, up or down.  Every step is a block
        that stands on the lower of the two heights, sunk `fill` (0.2) into the floor so that no crack is left.  A solid: give it to `build_level(solids=[...])` '''
    a, b = _p3(start, 'staircase'), _p3(end, 'staircase')
    steps = int(steps)
    if steps < 1:
        raise ValueError('staircase: one step at least')
    rise = (b[2] - a[2]) / steps
    fill = 0.2 if fill is None else float(fill)
    bottom = min(a[2], b[2]) - fill
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    if length < 1e-9:
        raise ValueError('staircase: the two places are the same in x and y')
    ux, uy = dx / length, dy / length
    px, py = Shape.X() - a[0], Shape.Y() - a[1]
    u = px * ux + py * uy
    v = px * (-uy) + py * ux
    run = length / steps
    blocks = []
    for k in range(steps):
        top = a[2] + rise * (k + 1)
        blocks.append((u - (k + 1) * run).max(k * run - u).max(v.abs() - width / 2.0).max(Shape.Z() - top).max(bottom - Shape.Z()))
    out = union_all(blocks)
    _bounded(out, [min(a[0], b[0]) - width, min(a[1], b[1]) - width, bottom], [max(a[0], b[0]) + width, max(a[1], b[1]) + width, max(a[2], b[2])])
    return out


def wall_segment(a, b, thickness=0.4, height=3.0, base=0.0, openings=()):
    ''' A wall of its own (a fence, a ruin, a rampart) along the straight line from `a` to `b` (x, y), `thickness` thick and `height` high from `base`, with the cutters
        `openings` taken out of it '''
    a, b = _p3(a, 'wall_segment'), _p3(b, 'wall_segment')
    a, b = (a[0], a[1], float(base)), (b[0], b[1], float(base))
    body = _piece(a, b, float(thickness), 0.0, float(height), 0.0, 0.0)
    for cut in openings:
        body = body.max(-cut)
    reach = float(thickness)
    _bounded(body, [min(a[0], b[0]) - reach, min(a[1], b[1]) - reach, float(base)], [max(a[0], b[0]) + reach, max(a[1], b[1]) + reach, float(base) + float(height)])
    return body


def build_level(spaces, openings=(), solids=()):
    ''' The level: the walls, floors and ceilings round `spaces` (rooms and corridors), with the cutters `openings` (doorways, windows) taken out of them, and the `solids`
        (staircase, pillars, anything that stands in the empty space) added.  A body '''
    spaces = list(spaces) if isinstance(spaces, (list, tuple)) else [spaces]
    if not spaces or not all(isinstance(s, Space) for s in spaces):
        raise TypeError('build_level(spaces): spaces is a list of room(...) and corridor(...)')
    outer = union_all([s.outside for s in spaces])
    inner = union_all([s.inside for s in spaces] + [o for o in openings])
    shell = outer.max(-inner)
    parts = [shell] + [s for s in solids]
    out = union_all(parts) if len(parts) > 1 else shell
    lo = [min(s.bounds[0][i] for s in spaces) for i in range(3)]
    hi = [max(s.bounds[1][i] for s in spaces) for i in range(3)]
    _bounded(out, lo, hi)
    return out
