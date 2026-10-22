'''
Reference images: a picture standing in the 3D view, to model over.

    front = reference_image("hero_front.png", plane="front", height=180)                 # a drawing of the character seen from the front, 180 mm high
    side = reference_image("hero_side.png", plane="right", height=180, center=(0, 0, 90), opacity=0.4)
    spine = limb([(0, 0, 92), (0, 0, 106), (0, 0, 128)], radii=[13, 11, 15], name="spine")      # the nodes are placed over the pictures

A reference image is not part of the model: it is drawn in the viewport, in the plane it is given, and nothing is exported of it.  The camera is free -- orbit, zoom, look at
the pictures from any side -- and the nodes of a limb are placed over the picture, one after another, with the work plane (Shift+W) faced to the picture, or the pictures
are the planes the nodes are dragged in.  The picture is set by numbers in the script: where its middle is (`center`), how tall it is (`height`: the width follows the picture's
shape), how strong it is (`opacity`), whether it is turned over (`flip`) and whether it is shown (`visible`).

The planes are the standard views of the viewport, so a picture reads the right way round in the view of its name: the model's z is up and its front is toward -y (the Front view
looks at it from -y, and a glTF made of it faces +z, the way a game engine wants a character):

    front   the picture's right is +x, its up is +z   (seen from -y: the Front view)
    back    -x, +z   (seen from +y)
    right   +y, +z   (seen from +x)
    left    -y, +z   (seen from -x)
    top     +x, +y   (seen from +z)
    bottom  +x, -y   (seen from -z)

or `plane=((ux, uy, uz), (vx, vy, vz))`: the two directions of the picture's right and up, any plane through `center`.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import math
import os

from fieldev.shape import Shape
from fieldev.stdlib import curves as C

__all__ = ['reference_image', 'ReferenceImage']


def _scalar(v):
    ''' A number, or a `var()` (an expression of them) of the script -- its value now: the number can be dragged in the viewport or in the model tree, and the picture follows it '''
    if isinstance(v, Shape):
        return C.value_of(v)
    return v

_PLANES = {
    'front': ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    'back': ((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    'right': ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    'left': ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
    'top': ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
    'bottom': ((1.0, 0.0, 0.0), (0.0, -1.0, 0.0)),
}

try:
    import _fieldev_host as _host              # (provided by the application: it reads the list after the script has run)
except ImportError:
    _host = None
    recorded = []                              # (outside the application, the images of the last script are here)


class ReferenceImage:
    ''' A picture standing in the view: see `reference_image` '''

    def __init__(self, path, center, u, v, height, opacity, flip, visible, scale=1.0):
        self.scale = scale
        self.path = path
        self.center = center
        self.u = u
        self.v = v
        self.height = height
        self.opacity = opacity
        self.flip = flip
        self.visible = visible

    def __repr__(self):
        return 'reference_image(%r, center=(%.4g, %.4g, %.4g), height=%g)' % ((os.path.basename(self.path),) + tuple(self.center) + (self.height,))


def _unit(vector, what):
    try:
        x, y, z = (float(c) for c in vector)
    except (TypeError, ValueError):
        raise ValueError('reference_image: %s is (x, y, z), not %r' % (what, vector))
    length = math.sqrt(x * x + y * y + z * z)
    if length < 1e-12:
        raise ValueError('reference_image: %s is not a direction' % what)
    return (x / length, y / length, z / length)


def reference_image(path, plane='front', height=None, center=(0, 0, 0), opacity=0.5, flip=False, visible=True):
    ''' A picture to model over, standing in the viewport (see the top of this file).

        path     the image file (PNG, JPG, BMP ...); a relative path is from the folder the program was started in
        plane    "front", "back", "right", "left", "top" or "bottom" (see above), or ((ux, uy, uz), (vx, vy, vz)): the directions of the picture's right and up
        height   how tall the picture is, in mm along its up (None: as tall as the render region is along it); the width follows the shape of the picture; `var(180)` for a number to drag
        center   where the middle of the picture is: (x, y, z), or a point -- a point with a gizmo is the picture's handle: drag the point and the picture goes with it, scale
                 its ring and the picture is that much larger (the script runs again when it is let go)
        opacity  0 (not seen) to 1 (solid): 0.5 by default, so that what is modelled shows through
        flip     the picture turned over left to right (a drawing of the other side)
        visible  False: not shown (the line stays in the script) '''
    if not isinstance(path, str) or not path.strip():
        raise ValueError('reference_image: the file name of an image, not %r' % (path,))
    if isinstance(plane, str):
        if plane.strip().lower() not in _PLANES:
            raise ValueError('reference_image: plane is %s, or ((ux, uy, uz), (vx, vy, vz)) -- not %r' % (', '.join('"%s"' % p for p in _PLANES), plane))
        u, v = _PLANES[plane.strip().lower()]
    else:
        try:
            u, v = plane
        except (TypeError, ValueError):
            raise ValueError('reference_image: plane is a name, or ((ux, uy, uz), (vx, vy, vz)), not %r' % (plane,))
        u, v = _unit(u, 'the right of the picture'), _unit(v, 'the up of the picture')
        d = u[0] * v[0] + u[1] * v[1] + u[2] * v[2]
        v = _unit((v[0] - d * u[0], v[1] - d * u[1], v[2] - d * u[2]), 'the up of the picture (it is along its right)')
    height = None if height is None else _scalar(height)
    opacity = _scalar(opacity)
    if height is not None and not (isinstance(height, (int, float)) and not isinstance(height, bool) and height > 0):
        raise ValueError('reference_image: height is a number of mm above 0, not %r' % (height,))
    if not isinstance(opacity, (int, float)) or isinstance(opacity, bool) or not 0.0 <= opacity <= 1.0:
        raise ValueError('reference_image: opacity is a number from 0 to 1, not %r' % (opacity,))
    try:
        anchor = C.Control(center)
        middle = tuple(float(c) for c in anchor.pos)
    except TypeError:
        raise ValueError('reference_image: center is a point or (x, y, z), not %r' % (center,))
    # (a point with a gizmo is the picture's handle: its place is the middle of the picture and the scale of its gizmo -- the ring -- is how large the picture is, times `height`)
    scale = 1.0 if anchor.scale_expr is None else max(1e-6, float(C.value_of(anchor.scale_expr)))
    image = ReferenceImage(os.path.abspath(path), middle, u, v, 0.0 if height is None else float(height), float(opacity), bool(flip), bool(visible), scale)
    entry = (image.path, image.center, image.u, image.v, image.height, image.opacity, image.flip, image.visible, image.scale)
    if _host is not None:
        try:
            getattr(_host, '__references').append(entry)
        except AttributeError:
            setattr(_host, '__references', [entry])
    else:
        recorded.append(entry)
    return image
