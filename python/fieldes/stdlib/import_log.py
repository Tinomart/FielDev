'''
What every import leaves behind: a log of the imports made in this session (the model tree lists an import's parts from it), the
units an importer can scale to, the stand-in for a part that could not be imported, and roi() / roi_resolution(), the region and the
resolution to view what was imported.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import math
import os

from fieldes.shape import Shape

__all__ = [
    'FailedPart',
    'roi',
    'roi_resolution',
]

class FailedPart(object):
    ''' Stands in for a part that could not be imported. Its bounds are still real, so the tuple can still be
        unpacked and inspected, but ANY attempt to actually use it as a
        Shape (meshing it, combining it with other shapes, even just
        printing its value) raises immediately with the specific reason,
        instead of silently substituting Oracle or approximate geometry. '''
    __slots__ = ('error',)

    def __init__(self, error):
        self.error = error

    def _raise(self):
        raise RuntimeError('this part could not be imported: {}'.format(self.error))

    def __getattr__(self, name):
        if name.startswith('_'):
            # (the library asks every part for its private notes -- _bounds, _step_ref, _fit_marker -- and
            # an absent one is None: only using the part as a shape is an error)
            raise AttributeError(name)
        self._raise()

    def __repr__(self):
        self._raise()

    def __bool__(self):
        self._raise()
    __nonzero__ = __bool__


_UNITS_MM = {'mm': 1.0, 'cm': 10.0, 'dm': 100.0, 'm': 1000.0, 'in': 25.4,
             'inch': 25.4, 'ft': 304.8}


def _target_mm(units):
    if units in (None, 'file'):
        return None
    try:
        return _UNITS_MM[str(units).lower()]
    except KeyError:
        raise ValueError('unknown units {!r}; use one of {} or "file"'.format(
            units, ', '.join(sorted(_UNITS_MM))))


# Every import made in this process: absolute path -> summary.  FielDes's
# scene panel reads this to list an import's parts (with their bounds and
# failure reasons) without importing the file a second time.
_import_log = {}


def _log_import(path, kind, parts, unit_mm, units, names=None):
    entries = []
    for i, (shape, (lo, hi)) in enumerate(parts):
        failed = isinstance(shape, FailedPart)
        entries.append({'index': i, 'ok': not failed,
                        'error': shape.error if failed else None,
                        # (a body the file lists and gives no surface: nothing to import, which the tree shows quietly)
                        'empty': bool(failed and 'has no surface to tessellate' in (shape.error or '')),
                        'name': (names[i] if names and i < len(names) else '') or '',
                        'bounds': [list(lo), list(hi)]})
        if not failed:
            try:
                shape._bounds = (tuple(lo), tuple(hi))
            except AttributeError:
                pass
    _import_log[os.path.normcase(os.path.abspath(path))] = {
        'kind': kind, 'path': os.path.abspath(path), 'unit_mm': unit_mm,
        'units': units, 'parts': entries}


def _bounds_of(item):
    ''' Bounds boxes found in an import result / part / bounds / Shape  '''
    def is_vec(v):
        return isinstance(v, (tuple, list)) and len(v) == 3 and \
            all(isinstance(c, (int, float)) for c in v)
    if isinstance(item, (tuple, list)):
        if len(item) == 2 and is_vec(item[0]) and is_vec(item[1]):
            return [item]                                   # a bounds pair
        if len(item) == 2 and isinstance(item[1], (tuple, list)) and \
                len(item[1]) == 2 and is_vec(item[1][0]):
            return [item[1]]                                # (shape, bounds)
        out = []
        for sub in item:                                    # a parts list
            out.extend(_bounds_of(sub))
        return out
    b = getattr(item, '_bounds', None) if isinstance(item, Shape) else None
    return [b] if b else []


def roi(*items, pad=0.1):
    ''' Region of interest covering the given imported models, for
        view.set_bounds(*roi(...)).  Accepts whatever the importers
        return: a parts list, one (shape, bounds) part, a bounds pair, or
        an imported Shape.  Each side is padded by `pad` times the box size.
        Returns (xyz_min, xyz_max). '''
    boxes = []
    for it in items:
        boxes.extend(_bounds_of(it))
    if not boxes:
        raise ValueError('roi(): no bounds found in the given items')
    lo = [min(b[0][i] for b in boxes) for i in range(3)]
    hi = [max(b[1][i] for b in boxes) for i in range(3)]
    size = [hi[i] - lo[i] for i in range(3)]
    ref = max(size) or 1.0
    p = [pad * max(size[i], 0.05 * ref) for i in range(3)]
    return (tuple(lo[i] - p[i] for i in range(3)),
            tuple(hi[i] + p[i] for i in range(3)))


def roi_resolution(*items, cells=150):
    ''' A render resolution (voxels per unit) for the given models, view.set_resolution(roi_resolution(...)): `cells`
        voxels across the region roi(...) covers, rounded to two significant digits. '''
    lo, hi = roi(*items, pad=0.0)
    span = max(hi[i] - lo[i] for i in range(3)) or 1.0
    r = cells / span
    return round(r, 1 - int(math.floor(math.log10(abs(r)))))


# What the transforms and the handles carry from a shape to the shape made of it: what the importer, roi() and the viewport read
# off a part (its box, its colouring, its name)
_CARRIED = ('_color_field', '_color_range', '_color_label', '_color_map', '_part_name', '_bounds', '_kind', 'xyz',
            '_point_pos', 'size')
