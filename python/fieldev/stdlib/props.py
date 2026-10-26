'''
Props: rocks, trees, bushes, crates and barrels -- made by number, varied by seed, and set out over the ground by a field's rules.

    stone = rock(size=1.4, seed=7)                         # a boulder, flat underneath, standing on z = 0
    pine = tree(height=9, kind="pine", seed=2)            # "round", "pine" or "bush"
    box_ = crate(size=0.9)
    keg = barrel(radius=0.4, height=1.0)

Every prop is a body shown in its own materials (see `with_materials`), standing with its foot on z = 0, so `placed(prop, (x, y, z), turn=30, scale=1.2)` puts it somewhere and
`merge([a, b, c])` makes one body of several -- the materials go with them, each material one layer over all the places it is on.

    forest = scatter(lambda s: tree(height=8, seed=s), 120, ((-90, -90), (90, 90)), ground=ground, min_distance=5, max_slope=28)

`scatter` stands props on the ground, wherever it is flat enough and the rules allow (`where`: a field that is negative where props may be, or a function of (x, y, z)), each a
variant of a few (`variants`), turned and scaled a little.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import copy
import math
import random

from fieldev.shape import Shape
from fieldev.stdlib.fields import noise_field, smooth_union, union_all
from fieldev.stdlib.materials import material, material_preset, with_materials
from fieldev.stdlib.shapes import box, sphere, cylinder, cone, rounded_box
from fieldev.stdlib.surfaces import ellipsoid
from fieldev.stdlib.characters import round_cone
from fieldev.stdlib.transforms import move, rotate_z, scale_xyz

__all__ = ['rock', 'tree', 'crate', 'barrel', 'placed', 'merge', 'scatter']


def _prop(body, layers, grow=0.0):
    ''' `body` shown in the materials `layers`, remembering both (and `grow`, how far inside the body a point of its surface counts as being) so that it can be placed and merged '''
    shown = with_materials(body, layers)
    shown._parts = (body, layers, float(grow))
    return shown


def rock(size=1.0, seed=1, roughness=0.35, flat=0.75, crag=0.0, color=None):
    ''' A boulder about `size` across (a radius), flat underneath so that it sits on z = 0.  `roughness`: how lumpy (0 to 1); `flat`: how low it is against its width; `crag`: 0 to 1,
        sharp ridges over the lumps; `color`: "#rrggbb" instead of stone grey.  Another `seed`, another rock '''
    rng = random.Random(seed)
    r = float(size)
    sx, sy = r * rng.uniform(0.85, 1.15), r * rng.uniform(0.8, 1.1)
    sz = r * float(flat) * rng.uniform(0.85, 1.1)
    body = ellipsoid((sx, sy, sz)) - noise_field(r * 0.9, 3, seed, gain=0.55, amplitude=1.5 * float(roughness) * r)
    if crag:
        body = body - noise_field(r * 0.55, 2, seed + 5, kind='ridged', amplitude=0.25 * float(crag) * r)
    cut = 0.55 * sz
    body = move(body.max(-Shape.Z() - cut), (0.0, 0.0, cut))
    layers = [material_preset('stone', color=color) if color else material_preset('stone')]
    return _prop(body, layers, 0.04 * r)


def tree(height=6.0, trunk=0.25, crown=2.2, seed=1, kind='round'):
    ''' A tree `height` tall with a trunk of radius `trunk` and a crown of radius about `crown`.  kind: "round" (leafy balls on a leaning trunk), "pine" (stacked cones) or
        "bush" (no trunk to speak of: a low crown).  The bark and the leaves are two materials '''
    if kind not in ('round', 'pine', 'bush'):
        raise ValueError('tree: kind is "round", "pine" or "bush", not %r' % (kind,))
    rng = random.Random(seed)
    h, c = float(height), float(crown)
    lean = (rng.uniform(-0.3, 0.3) * 0.2 * h, rng.uniform(-0.3, 0.3) * 0.2 * h)
    if kind == 'bush':
        h = max(c * 1.4, 0.6)
        top = (0.0, 0.0, 0.3 * h)
        stem = round_cone((0.0, 0.0, trunk), top, trunk * 1.1, trunk * 0.8)
        balls = [sphere(c * rng.uniform(0.55, 0.8), center=(rng.uniform(-0.7, 0.7) * c, rng.uniform(-0.7, 0.7) * c, 0.55 * c + rng.uniform(0.0, 0.3) * c)) for _ in range(5)]
        leaves = union_all(balls, blend=0.3 * c) - noise_field(0.4 * c, 2, seed + 3, amplitude=0.3 * c)
    elif kind == 'round':
        top = (lean[0], lean[1], 0.64 * h)
        stem = round_cone((0.0, 0.0, trunk * 1.2), top, trunk * 1.2, trunk * 0.55)
        centre = (top[0], top[1], 0.72 * h)
        balls = [sphere(c * rng.uniform(0.62, 0.85), center=(centre[0] + rng.uniform(-0.6, 0.6) * c, centre[1] + rng.uniform(-0.6, 0.6) * c, centre[2] + rng.uniform(-0.3, 0.5) * c))
                 for _ in range(6)]
        leaves = union_all(balls, blend=0.35 * c) - noise_field(0.45 * c, 2, seed + 3, amplitude=0.35 * c)
    else:
        top = (lean[0] * 0.5, lean[1] * 0.5, 0.9 * h)
        stem = round_cone((0.0, 0.0, trunk * 1.2), top, trunk * 1.2, trunk * 0.4)
        tiers = 4
        cones = [cone(c * (1.0 - 0.2 * i), 0.4 * h, base=(lean[0] * 0.3 * i / tiers, lean[1] * 0.3 * i / tiers, h * (0.2 + 0.16 * i))) for i in range(tiers)]
        leaves = union_all(cones, blend=0.05 * c)
    body = smooth_union(stem, leaves, 0.1 * c)
    grown = leaves - 0.25 * min(c, 1.0)               # (the surface of the union that is the leaves' lies inside them, grown a little)
    layers = [material_preset('wood', name='bark', color='#5a3d27'), material('leaves', color='#3c7a2c' if kind != 'pine' else '#2f5f35', roughness=0.85, where=grown)]
    return _prop(body, layers, 0.04 * h)


def crate(size=1.0, plank=0.12, depth=0.04):
    ''' A wooden crate `size` on a side, standing on z = 0 with its middle on the origin: a frame of boards `plank` wide (a fraction of the size) and panels sunk `depth` into it '''
    s = float(size)
    h = s / 2.0
    body = rounded_box((-h, -h, 0.0), (h, h, s), 0.06)
    fw, d = float(plank) * s, float(depth) * s
    cuts = [box((h - d, -h + fw, fw), (h + 1.0, h - fw, s - fw)), box((-h - 1.0, -h + fw, fw), (-h + d, h - fw, s - fw)),
            box((-h + fw, h - d, fw), (h - fw, h + 1.0, s - fw)), box((-h + fw, -h - 1.0, fw), (h - fw, -h + d, s - fw)),
            box((-h + fw, -h + fw, s - d), (h - fw, h - fw, s + 1.0))]
    for cut in cuts:
        body = body.max(-cut)
    return _prop(body, [material_preset('wood', name='crate_wood', color='#8a6236')], 0.03 * s)


def barrel(radius=0.4, height=1.0, bulge=0.12, hoops=2):
    ''' A barrel standing on z = 0, `bulge` wider in the middle than at the ends, with `hoops` iron bands '''
    r0, hh = float(radius), float(height)
    z = Shape.Z()
    t = (z * (1.0 / hh) - 0.5) * 2.0
    r_here = r0 * (1.0 + float(bulge) * (1.0 - t.square()))
    r = (Shape.X().square() + Shape.Y().square()).sqrt()
    staves = (r - r_here).max(-z).max(z - hh)
    bands = None
    for k in range(int(hoops)):
        zc = hh * (0.2 + 0.6 * k / max(int(hoops) - 1, 1)) if hoops > 1 else hh * 0.5
        band = (r - (r_here + 0.03 * r0)).max((z - zc).abs() - 0.05 * hh)
        bands = band if bands is None else bands.min(band)
    body = staves if bands is None else staves.min(bands)
    layers = [material_preset('wood', name='staves', color='#7a5230')]
    if bands is not None:
        layers.append(material_preset('iron', name='bands', where=bands - 0.02 * r0))
    return _prop(body, layers, 0.03 * hh)


def placed(prop, position=(0.0, 0.0, 0.0), turn=0.0, scale=1.0):
    ''' `prop` scaled (about its foot), turned `turn` degrees about z and moved to `position`: the materials go with it '''
    where = list(getattr(position, 'xyz', position))
    position = tuple(float(c) for c in where) + (0.0,) * (3 - len(where))

    def transform(field):
        out = field
        if scale != 1.0:
            out = scale_xyz(out, (scale, scale, scale))
        if turn:
            out = rotate_z(out, math.radians(float(turn)))
        return move(out, position)

    parts = getattr(prop, '_parts', None)
    if parts is None:
        return transform(prop)
    body, layers, grow = parts
    moved = []
    for m in layers:
        one = copy.copy(m)
        if m.where is not None:
            one.where = transform(m.where)
        moved.append(one)
    return _prop(transform(body), moved, grow * float(scale))


def merge(props, blend=0.0):
    ''' Several props as one body.  A material that two of them have is one layer, on the places of all of them '''
    bodies, layers = [], []
    by_name = {}
    for p in props:
        parts = getattr(p, '_parts', None)
        body, own, grow = parts if parts is not None else (p, [], 0.0)
        bodies.append(body)
        for m in own:
            if m.where is None and len(props) > 1:
                m = copy.copy(m)
                m.where = body - grow             # (a material that covers the whole of one prop covers its body, not everything: the others have theirs)
            if m.name in by_name:
                known = by_name[m.name]
                known.where = None if (known.where is None or m.where is None) else known.where.min(m.where)
            else:
                known = copy.copy(m)
                by_name[m.name] = known
                layers.append(known)
    out = union_all(bodies, blend) if len(bodies) > 1 else bodies[0]
    if not layers:
        return out
    layers.sort(key=lambda m: (m.where is not None, bool(getattr(m, '_cover', False))))           # (the ones that are everywhere go first, the covers of `covered` last: the rest are painted over them)
    return _prop(out, layers)


def scatter(make, count, area=None, ground=None, seed=1, min_distance=0.0, max_slope=40.0, where=None, scale=(0.85, 1.2), turn=True, variants=3, sink=0.0, blend=0.0):
    ''' `count` props over `area` ((x0, y0), (x1, y1): the ground's own when not given), each made by `make(seed)` -- `variants` different ones, each placed many times --, standing on
        `ground` (a `terrain(...)`: at its height, only where it is not steeper than `max_slope` degrees) at least `min_distance` apart, turned about z and scaled by a number in `scale`.
        `where`: a field that is negative where props may stand, or a function (x, y, z) -> True / False.  `sink`: how far they sink into the ground.  Fewer than `count` are made when
        the area has no room for more.  The result is one prop '''
    rng = random.Random(seed)
    if area is None:
        if ground is None:
            raise ValueError('scatter: give an area ((x0, y0), (x1, y1)) or a ground')
        cx, cy, sx, sy = ground._box
        area = ((cx - sx / 2.0, cy - sy / 2.0), (cx + sx / 2.0, cy + sy / 2.0))
    (x0, y0), (x1, y1) = area
    bases = [make(int(seed) * 1000 + k) for k in range(max(1, int(variants)))]
    spots = []
    tries = 0
    while len(spots) < int(count) and tries < int(count) * 60:
        tries += 1
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        z = ground.height_at(x, y) if ground is not None else 0.0
        if ground is not None and ground.slope_at(x, y) > float(max_slope):
            continue
        if where is not None:
            ok = (float(where(x, y, z)) < 0.0) if isinstance(where, Shape) else bool(where(x, y, z))
            if not ok:
                continue
        if min_distance and any((x - px) ** 2 + (y - py) ** 2 < float(min_distance) ** 2 for px, py, _ in spots):
            continue
        spots.append((x, y, z))
    items = []
    for x, y, z in spots:
        k = rng.randrange(len(bases))
        s = rng.uniform(float(scale[0]), float(scale[1]))
        t = rng.uniform(0.0, 360.0) if turn else 0.0
        items.append(placed(bases[k], (x, y, z - float(sink) * s), t, s))
    if not items:
        raise ValueError('scatter: no place was found for a prop (the area, the slope or the rule leave none)')
    out = merge(items, blend)
    return out
