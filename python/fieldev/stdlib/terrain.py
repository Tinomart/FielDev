'''
Terrain: the ground as a field.

A heightmap is a picture of heights; a terrain here is a FIELD -- the ground is where z is below a height that is itself a field of x and y, and everything you do to it is
arithmetic on that field.  So:

  * there is no grid and no resolution: the same ground is meshed coarse for a preview and fine for an export;
  * a hill, a flat place to build on, a road, a river are smooth blends of fields: they cannot leave a crack, and a road keeps its width over any hill;
  * it is a solid, not a surface: caves, arches and overhangs are boolean cuts of the same body, which a heightmap cannot have;
  * the material of a place is a field too -- grass where the ground is flat, rock where it is steep, snow high up -- and goes to the exported file.

    ground = terrain(size=(240, 240), height=14, scale=60, seed=3)        # hills, from noise
    ground = ground.raised((30, -20), radius=28, height=16)                # a hill there
    ground = ground.flattened((-50, 40), radius=14)                        # a place to build on, as high as the ground is at its middle
    ground = ground.road([(-110, -80), (-40, -20), (30, 10), (110, 60)], width=6)
    ground = ground.river([(-100, 100), (0, 20), (90, -90)], width=8, depth=3)
    ground = ground.cave([(60, -60, 4), (80, -30, 6), (100, 0, 8)], radius=5)
    shown = ground.textured(snow_line=26, beach=1.5)                       # grass, rock, snow, sand: by the slope and the height

`ground.height_at(x, y)` is the height of the ground there (for standing a prop on it: see props.scatter).

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import math
import numbers

from fieldev.shape import Shape
from fieldev.stdlib.curves import owned
from fieldev.stdlib.fields import noise_field, smoothstep, smooth_union, smooth_difference, evaluate
from fieldev.stdlib.materials import material, material_preset, with_materials

__all__ = ['terrain', 'Terrain', 'water']


def _pair(v, what):
    if isinstance(v, numbers.Number):
        return float(v), float(v)
    try:
        a, b = v[0], v[1]
        return float(a), float(b)
    except (TypeError, IndexError, ValueError):
        raise ValueError('%s: two numbers (x, y), not %r' % (what, v))


def _flat_noise(scale, octaves, seed, gain, kind='perlin'):
    ''' Noise that only depends on x and y: a slice of the 3D noise at one height '''
    n = noise_field(scale, octaves, seed, gain=gain, kind=kind)
    return n.remap(Shape.X(), Shape.Y(), Shape.wrap(0.5 + 0.37 * seed))


def _height_range(h, cx, cy, sx, sy, n=17):
    points = [(cx - sx / 2.0 + sx * i / (n - 1.0), cy - sy / 2.0 + sy * j / (n - 1.0), 0.0) for i in range(n) for j in range(n)]
    values = evaluate(h, points)
    return min(values), max(values)


def _make(height, box, base, edits, features=(), rivers=()):
    ''' The Terrain with this height field, in this footprint (cx, cy, sx, sy), with the floor of its slab at `base` and the 3D changes `edits` made to it in order '''
    from fieldev.stdlib.shapes import _bounded
    cx, cy, sx, sy = box
    x, y, z = Shape.X(), Shape.Y(), Shape.Z()
    body = (z - height).max(base - z).max((x - cx).abs() - sx / 2.0).max((y - cy).abs() - sy / 2.0)
    for op, shape, blend in edits:
        body = smooth_union(body, shape, blend) if op == 'add' else smooth_difference(body, shape, blend)
    out = owned(body, Terrain)
    out._height = height
    out._box = box
    out._base = base
    out._edits = tuple(edits)
    out._features = tuple(features)
    out._rivers = tuple(rivers)
    low, high = _height_range(height, cx, cy, sx, sy)
    margin = 0.1 * (high - low) + 1.0
    _bounded(out, [cx - sx / 2.0, cy - sy / 2.0, min(base, low) - margin], [cx + sx / 2.0, cy + sy / 2.0, high + margin])
    return out


def terrain(size=(200.0, 200.0), height=10.0, scale=50.0, seed=1, base=None, center=(0.0, 0.0), roughness=0.5, ridges=0.0, plains=0.0, level=0.0):
    ''' A piece of ground: a solid slab whose top is hills made of noise.

        size        (x, y): how far it reaches across, centred on `center`
        height      about how high the hills rise above, and how deep the valleys sink below, `level`
        scale       the size of the largest hills (the next octaves are finer: `roughness` is how strong they are, 0 to 1)
        seed        another number, another landscape
        ridges      0 to 1: how much of the hills are sharp ridges (mountains) instead of round hills
        plains      0 to 1: how much the valleys are filled up to `level` (flat land between the hills)
        level       the height of the ground where the noise is zero
        base        the height of the flat bottom of the slab (below the lowest valley by default)

        The ground is a body: it can be moved, cut and exported like any other.  It also knows its height field -- `height_at`, `raised`, `flattened`, `road`, `river`, `cave`,
        `chunk` and `textured` are what you do with it. '''
    sx, sy = _pair(size, 'terrain: size')
    cx, cy = _pair(center, 'terrain: center')
    hills = _flat_noise(scale, 4, seed, roughness) * (3.0 * float(height))
    if ridges:
        ridge = _flat_noise(scale * 1.3, 4, seed + 7, roughness, kind='ridged') * float(height)
        hills = hills * (1.0 - float(ridges)) + ridge * float(ridges)
    if plains:
        hills = hills * (1.0 - float(plains)) + hills.max(0.0) * float(plains)
    h = hills + float(level)
    if base is None:
        base = float(level) - 2.0 * abs(float(height)) - 4.0
    return _make(h, (cx, cy, sx, sy), float(base), ())


def _catmull(points, per):
    ''' A smooth path through the points: Catmull-Rom pieces, `per` straight pieces to each '''
    if len(points) < 3 or per < 2:
        return list(points)
    out = []
    n = len(points)
    for i in range(n - 1):
        p0, p1, p2, p3 = points[max(i - 1, 0)], points[i], points[i + 1], points[min(i + 2, n - 1)]
        for k in range(per):
            t = k / float(per)
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2.0 * p1[a]) + (-p0[a] + p2[a]) * t + (2.0 * p0[a] - 5.0 * p1[a] + 4.0 * p2[a] - p3[a]) * t2 + (-p0[a] + 3.0 * p1[a] - 3.0 * p2[a] + p3[a]) * t3)
                            for a in range(3)))
    out.append(tuple(points[-1]))
    return out


def _path(nodes, ground, smooth):
    ''' The nodes of a path as (x, y, z): a node with no z is as high as the ground is there '''
    pts = []
    for p in nodes:
        p = list(getattr(p, 'xyz', p))
        if len(p) < 2:
            raise ValueError('a path is made of places (x, y) or (x, y, z), not %r' % (p,))
        x, y = float(p[0]), float(p[1])
        z = float(p[2]) if len(p) > 2 else (ground.height_at(x, y) if ground is not None else 0.0)
        pts.append((x, y, z))
    if len(pts) < 2:
        raise ValueError('a path needs at least two places')
    return _catmull(pts, 8) if smooth else pts


def _along(pts, with_point=False):
    ''' (the distance across the ground from the path, the height of the path nearest to it) as fields of x and y: the pieces of the path are straight, the height runs
        along each of them, and the nearest piece wins '''
    x, y = Shape.X(), Shape.Y()
    best_d = best_z = best_x = best_y = None
    for a, b in zip(pts, pts[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        l2 = dx * dx + dy * dy
        if l2 < 1e-12:
            continue
        px, py = x - a[0], y - a[1]
        t = ((px * dx + py * dy) * (1.0 / l2)).max(0.0).min(1.0)
        qx, qy = px - t * dx, py - t * dy
        d = (qx.square() + qy.square()).sqrt()
        z = a[2] + t * (b[2] - a[2])
        wx, wy = a[0] + t * dx, a[1] + t * dy                  # (the place of this piece that is nearest to (x, y))
        if best_d is None:
            best_d, best_z, best_x, best_y = d, z, wx, wy
        else:
            nearer = (-(d - best_d).compare(0.0)).max(0.0)       # (1 where this piece is nearer than the ones before it, else 0)
            best_z = best_z + (z - best_z) * nearer
            best_x = best_x + (wx - best_x) * nearer
            best_y = best_y + (wy - best_y) * nearer
            best_d = best_d.min(d)
    if best_d is None:
        raise ValueError('a path needs two places that are not the same')
    return (best_d, best_z, best_x, best_y) if with_point else (best_d, best_z)


class Terrain(Shape):
    ''' The ground (see the top of this file): a body that also knows its height field.  Every method that changes it gives a new Terrain; this one is left as it was '''
    _height = None
    _box = None
    _base = None
    _edits = ()
    _rivers = ()                    # (the rivers made: (distance from the path as a field, how far the channel reaches, the nearest place of the path as two fields, the ground before the channel, the depth) -- what river_water fills)
    _features = ()                  # (the roads and rivers made: (kind, distance from the path as a field, half the width) -- what the road and river materials are where)

    def _with_height(self, height, feature=None, river=None):
        return _make(height, self._box, self._base, self._edits, self._features + ((feature,) if feature else ()), self._rivers + ((river,) if river else ()))

    def _with_edit(self, op, shape, blend):
        return _make(self._height, self._box, self._base, self._edits + ((op, Shape.wrap(shape), float(blend)),), self._features, self._rivers)

    # ---- what the ground is like at a place

    def height_at(self, x, y):
        ''' The height of the ground at (x, y), a number (the height field: caves and cuts are not in it) '''
        return float(self._height(float(x), float(y), 0.0))

    def slope_at(self, x, y, step=0.5):
        ''' How steep the ground is at (x, y), in degrees (0 is flat) '''
        gx = (self.height_at(x + step, y) - self.height_at(x - step, y)) / (2.0 * step)
        gy = (self.height_at(x, y + step) - self.height_at(x, y - step)) / (2.0 * step)
        return math.degrees(math.atan(math.hypot(gx, gy)))

    def height_field(self):
        ''' The height of the ground as a field of x and y (it does not change with z): for your own arithmetic -- a material, a mask, a scatter '''
        return self._height

    # ---- shaping it

    def raised(self, center, radius, height, falloff='smooth'):
        ''' A hill (a pit when `height` is negative) of that height and radius at `center` (x, y).  falloff: 'smooth' (rounded top, flat foot), 'dome' (round), 'cone' '''
        cx, cy = _pair(center, 'raised: center')
        r = ((Shape.X() - cx).square() + (Shape.Y() - cy).square()).sqrt()
        if falloff == 'smooth':
            t = 1.0 - smoothstep(r, 0.0, float(radius))
        elif falloff == 'dome':
            t = (1.0 - (r * (1.0 / float(radius))).square()).max(0.0).sqrt()
        elif falloff == 'cone':
            t = (1.0 - r * (1.0 / float(radius))).max(0.0)
        else:
            raise ValueError("raised: falloff is 'smooth', 'dome' or 'cone', not %r" % (falloff,))
        return self._with_height(self._height + t * float(height))

    def flattened(self, center, radius, level=None, blend=None):
        ''' A flat place of that radius at `center`, at height `level` (as high as the ground is at its middle when not given), joined to the ground round it over `blend` '''
        cx, cy = _pair(center, 'flattened: center')
        level = self.height_at(cx, cy) if level is None else float(level)
        blend = 0.6 * float(radius) if blend is None else float(blend)
        r = ((Shape.X() - cx).square() + (Shape.Y() - cy).square()).sqrt()
        inside = 1.0 - smoothstep(r, float(radius), float(radius) + blend)
        return self._with_height(self._height + (level - self._height) * inside)

    def road(self, path, width=4.0, blend=None, depth=0.0, smooth=True):
        ''' A road along `path` (places (x, y), or (x, y, z) where the road is to be at a height): flat across, `width` wide, cut into the ground and filled up to it, and joined
            to the ground at its sides over `blend` (a road's width by default).  A place with no z is as high as the ground is there.  `depth`: sunk below that height.
            `smooth`: the path is a smooth curve through the places, not straight pieces '''
        pts = _path(path, self, smooth)
        dist, level = _along(pts)
        blend = float(width) if blend is None else float(blend)
        on_it = 1.0 - smoothstep(dist, float(width) / 2.0, float(width) / 2.0 + blend)
        return self._with_height(self._height + (level - float(depth) - self._height) * on_it, ('road', dist, float(width) / 2.0))

    def river(self, path, width=6.0, depth=2.0, blend=None, smooth=True):
        ''' A channel `depth` deep along `path` (places (x, y)), `width` across at its bottom, with banks that slope up to the ground over `blend` (its width by default) '''
        pts = _path(path, None, smooth)
        dist, _, px, py = _along(pts, True)
        blend = float(width) if blend is None else float(blend)
        bowl = 1.0 - smoothstep(dist, 0.0, float(width) / 2.0 + blend)
        return self._with_height(self._height - float(depth) * bowl, ('river', dist, float(width) / 2.0),
                                 (dist, float(width) / 2.0 + blend, px, py, self._height, float(depth)))

    def river_water(self, freeboard=0.4):
        ''' The water of the rivers made so far, as a body of its own in the water material: it fills each channel from the bed up to `freeboard` below the level the ground had at the
            middle of the channel before it was cut (at the nearest place of the river's path, so the water follows the river downhill), and ends where the bank rises above it.  It
            is a separate body, so that an engine can give it a water shader: export it beside the ground.  Where a river runs across a steep slope the water spills towards the
            low side as far as the channel reaches -- let a river run along the fall of the land, or over flat land '''
        from fieldev.stdlib.shapes import _bounded
        if not self._rivers:
            raise ValueError('river_water: this ground has no river -- make one with river(...) first')
        x, y, z = Shape.X(), Shape.Y(), Shape.Z()
        body = None
        for dist, reach, px, py, before, depth in self._rivers:
            surface = before(px, py, z) - float(freeboard)                  # (the ground at the nearest place of the path, as it was before the channel, less the freeboard)
            piece = (z - surface).max(self._height(x, y, z) - 0.1 - z).max(dist - reach)       # (a little under the bed, so that the two bodies do not share a face)
            body = piece if body is None else body.min(piece)
        lo, hi = self._bounds
        _bounded(body, list(lo), list(hi))
        return with_materials(body, material_preset('water'))

    def cave(self, path, radius=4.0, blend=2.0):
        ''' A tunnel of that radius along `path` (places (x, y, z): inside the ground, or coming out of it), blended into the ground over `blend`.  A cut of the solid: a heightmap
            cannot have one '''
        from fieldev.stdlib.characters import chain
        pts = [tuple(float(c) for c in getattr(p, 'xyz', p)) for p in path]
        if any(len(p) != 3 for p in pts):
            raise ValueError('cave: the path is made of places (x, y, z)')
        return self._with_edit('cut', chain(pts, radii=float(radius)), blend)

    def add(self, shape, blend=0.0):
        ''' Another body joined to the ground (a rock, a ruin ...), with a blend of `blend` where they meet '''
        return self._with_edit('add', shape, blend)

    def cut(self, shape, blend=0.0):
        ''' A body taken out of the ground (a pit, a cellar, a cave of your own), with a blend of `blend` along the cut '''
        return self._with_edit('cut', shape, blend)

    # ---- where a character can walk

    def _tangent(self, e=0.5):
        ''' The tangent of the angle of the ground, as a field (what `slope_at` gives in degrees: the same differences over `e` on each side) '''
        x, y, z = Shape.X(), Shape.Y(), Shape.Z()
        h = self._height
        gx = (h(x + e, y, z) - h(x - e, y, z)) * (0.5 / e)
        gy = (h(x, y + e, z) - h(x, y - e, z)) * (0.5 / e)
        return (gx.square() + gy.square()).sqrt()

    def steep_places(self, max_angle=35.0, color='#d9483b', **options):
        ''' The ground in the colours of `textured(**options)`, with `color` (red) wherever it is steeper than `max_angle` degrees: a check to look at while you model, for the places
            a character cannot walk up.  It is a layer like the others, so it is in the file if you export it '''
        layers = self.material_layers(**options)
        layers.append(material('too_steep', color=color, roughness=0.9, where=math.tan(math.radians(float(max_angle))) - self._tangent()))
        return with_materials(self, layers)

    def walkable_fraction(self, max_angle=35.0, samples=30):
        ''' How much of the ground, seen from above, is not steeper than `max_angle` degrees: a number from 0 to 1, from a grid of `samples` x `samples` places '''
        cx, cy, sx, sy = self._box
        n = int(samples)
        if n < 1:
            raise ValueError('walkable_fraction: samples is at least 1')
        ok = 0
        for i in range(n):
            for j in range(n):
                if self.slope_at(cx - sx / 2.0 + (i + 0.5) * sx / n, cy - sy / 2.0 + (j + 0.5) * sy / n) <= float(max_angle):
                    ok += 1
        return ok / float(n * n)

    # ---- what it is made of

    def material_layers(self, grass='#5f8f3c', rock='#7b776f', sand=None, snow=None, rock_angle=38.0, snow_line=None, beach=None, seed=1, road='#8b7b63', riverbed='#6e6552'):
        ''' The materials of the ground, as layers for `with_materials` and `export_mesh`: grass everywhere, `rock` where the ground is steeper than `rock_angle` degrees (and on the
            walls of caves), `snow` above `snow_line` where it is not too steep (with an edge that wanders), `sand` below `beach` where it is flat, `road` on the roads and `riverbed`
            in the rivers that were made (None leaves them out).  A colour is "#rrggbb" or (r, g, b);
            None leaves the layer out (`snow` and `sand` are made when `snow_line` and `beach` are given) '''
        e = 0.5
        x, y, z = Shape.X(), Shape.Y(), Shape.Z()
        h = self._height
        gx = (h(x + e, y, z) - h(x - e, y, z)) * (0.5 / e)
        gy = (h(x, y + e, z) - h(x, y - e, z)) * (0.5 / e)
        slope = (gx.square() + gy.square()).sqrt()                      # (the tangent of the angle of the ground)
        layers = [material('grass', color=grass, roughness=0.95)]
        if beach is not None:
            sand = sand or '#c9b27c'
            layers.append(material('sand', color=sand, roughness=0.9, where=(z - float(beach)).max(slope - math.tan(math.radians(25.0)))))
        kinds = {}
        for kind, dist, half in self._features:
            name, color = ('road', road) if kind == 'road' else ('riverbed', riverbed)
            if color is None:
                continue
            here = dist - half
            kinds[name] = (kinds[name][0], kinds[name][1].min(here)) if name in kinds else (color, here)
        for name, (color, where) in kinds.items():
            layers.append(material(name, color=color, roughness=0.95, where=where))
        steep = math.tan(math.radians(float(rock_angle))) - slope
        for op, shape, blend in self._edits:
            if op == 'cut':
                steep = steep.min(shape - 0.6)                        # (the walls of a cave are rock: the cut's field is zero on them)
        layers.append(material('rock', color=rock, roughness=0.9, where=steep))
        if snow_line is not None:
            snow = snow or '#eef3f7'
            fuzz = _flat_noise(6.0, 3, seed + 21, 0.5) * 9.0
            layers.append(material('snow', color=snow, roughness=0.7, where=(float(snow_line) + fuzz - z).max(slope - math.tan(math.radians(48.0)))))
        return layers

    def textured(self, **options):
        ''' The ground shown (and exported) in the colours of `material_layers(**options)` '''
        return with_materials(self, self.material_layers(**options))


def water(size=(200.0, 200.0), level=0.0, depth=3.0, center=(0.0, 0.0)):
    ''' A slab of water, `depth` deep, whose top is at `level`: the ground shows through where it is higher.  Shown with the water material '''
    from fieldev.stdlib.shapes import box
    sx, sy = _pair(size, 'water: size')
    cx, cy = _pair(center, 'water: center')
    slab = box((cx - sx / 2.0, cy - sy / 2.0, float(level) - float(depth)), (cx + sx / 2.0, cy + sy / 2.0, float(level)))
    return with_materials(slab, material_preset('water'))
