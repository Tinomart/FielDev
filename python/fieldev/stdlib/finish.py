'''
Finishing: what weather and time do to a thing that is already modelled -- as geometry, not as a picture on it.

A cover of snow, moss, dust or sand that lies on every surface that faces up -- thickest where the surface faces straight up, thinning to nothing at the angle where it would slide
off -- is a line of arithmetic on the field of the thing:

    snowy = covered(rock(1.4, seed=7), depth=0.12, angle=55)                          # snow on a rock
    mossy = covered(crate(1.0), depth=0.04, angle=70, name="moss", color="#4f7a34")   # moss on a crate

It works on anything that has a field -- a prop, a piece of a kit, a level -- and, because the cover is geometry, an engine sees it in the silhouette and in the shadows.  The cover is
also a material (`name`, `color`) that is only where the cover is, so an exported file has it as a layer of its own.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import math

from fieldev.shape import Shape
from fieldev.stdlib.fields import find_extent, smoothstep
from fieldev.stdlib.materials import material
from fieldev.stdlib.props import _prop

__all__ = ['covered']


def covered(model, depth=0.1, direction=(0.0, 0.0, 1.0), angle=50.0, name='snow', color='#eef3f7', roughness=0.75, soft=0.15):
    ''' `model` with a cover of `depth` on every surface that faces `direction` (up by default) to within `angle` degrees.  The cover is thickest where the surface faces straight at
        the direction and thins to nothing at `angle` (over a band of `soft`, as a share of the cosine); it has a material of its own, `name` in `color`, that lies only on the
        cover.  The model's own materials stay, so the result can be shown, exported, `placed`, `merge`d and `scatter`ed like the model.

        The field of the model is differenced on both sides along every axis to find which way its surface faces (six more evaluations of it for every one of the result), so a model
        that is slow to mesh is slower with a cover.  A model whose field is not a distance (its gradient is not of length 1) gets a cover of the same depth: the length of the gradient is
        divided out '''
    from fieldev.stdlib.shapes import _bounded
    d = [float(c) for c in getattr(direction, 'xyz', direction)]
    if len(d) != 3 or math.sqrt(sum(c * c for c in d)) < 1e-12:
        raise ValueError('covered: direction is a direction (x, y, z), not %r' % (direction,))
    norm = math.sqrt(sum(c * c for c in d))
    d = [c / norm for c in d]
    depth = float(depth)
    if not depth > 0.0:
        raise ValueError('covered: depth is above zero, not %r' % (depth,))
    if not 0.0 < float(angle) < 180.0:
        raise ValueError('covered: angle is between 0 and 180 degrees, not %r' % (angle,))
    parts = getattr(model, '_parts', None)
    if parts is not None:
        body, layers, grow = parts
        layers = list(layers)
    else:
        body, layers, grow = model, list(getattr(model, '_materials', None) or []), 0.0
    if any(m.name == name for m in layers):
        raise ValueError('covered: the model has a material called %r already -- give the cover another name' % (name,))
    e = max(depth * 0.5, 1e-4)
    x, y, z = Shape.X(), Shape.Y(), Shape.Z()
    gx = body(x + e, y, z) - body(x - e, y, z)
    gy = body(x, y + e, z) - body(x, y - e, z)
    gz = body(x, y, z + e) - body(x, y, z - e)
    length = (gx.square() + gy.square() + gz.square()).sqrt().max(1e-9)             # (twice `e` times the length of the gradient)
    facing = (gx * d[0] + gy * d[1] + gz * d[2]) / length                            # (the cosine of the angle between the surface's normal and the direction)
    edge = math.cos(math.radians(float(angle)))
    weight = smoothstep(facing, max(edge - float(soft), -1.0), min(edge + float(soft), 1.0))
    grad = length * (0.5 / e)                                                        # (the length of the gradient of the field: 1 where it is a distance)
    out = body - weight * grad * depth
    box = getattr(body, '_bounds', None)
    if not box:
        box = find_extent(body)             # (searched here, once, for the body: the search an export makes of the result -- seven times the field -- runs out of its budget)
    if box:
        lo, hi = box
        _bounded(out, [float(c) - depth for c in lo], [float(c) + depth for c in hi])
    cover = material(name, color=color, roughness=float(roughness), where=(grad * (0.15 * depth) - body).max(body - grad * (1.25 * depth)))      # (below zero only where the result's surface is outside the model by more than a sliver and by not more than the cover is thick: nowhere else, so that a merged prop beside it is not painted)
    cover._cover = True                     # (`merge` puts a cover after the materials of the props it joins, whatever their order: the cover is on top of them)
    return _prop(out, layers + [cover], grow)
