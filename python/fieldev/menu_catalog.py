'''
What the viewport's context menus create: the library's primitives and basic operations.

Right-clicking empty space in the viewport offers Primitives -- New 3D shape / 2D shape / 1D shape / point / surface / field, the most basic of each (BASIC), placed where the
cursor is -- Parametric shapes (the rest of the shapes the library can make with no argument, by kind) and Operations (the operations); right-clicking a body offers the same, with that body passed in.  The
menus are built from the two lists below, and the call each entry writes into the script comes from its template,
so this file is the one place that says what the menus offer.

A template is a Python format string.  For a primitive: {x} {y} {z} is the place (the point of the cursor's ray
that is closest to the origin, rounded), {s} the size (about a hundred pixels on screen, a round number), {h} half
of it, {xm} {xp} {ym} {yp} {zm} {zp} the place minus and plus half the size.  For an operation: {body} is the model
it works on, {other} the other models (for the operations that combine models: one name, or several separated by
commas, as when several models are selected -- union, difference, intersection and exclude take any number: for exclude the
first is the shape and the others are the regions locked in it), {others} the same with a comma before it, or nothing when there
are none (surface_from_bodies: the surface of one model, or where the others meet it), {s} the size, {t} a tenth of it.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import inspect
import json
import math

from fieldev.i18n import tr

# What a template may put ABOVE the line it writes (a function the call uses, for the user to write their own logic in): the
# text before this line is written above the assignment, the text after it is the call.  {var} is the variable the model gets.
PRELUDE = '\n#@@#\n'

_LOW_LEVEL_FIELD = '''def {var}_logic(x, y, z):
    # Your own field: x, y and z are the coordinates (fields). Return the value you want at that point.
    # Write the math with + - * / **, x.sqrt() x.square() x.abs() x.sin() x.cos(), a.max(b) a.min(b); a number is a constant field.
    return ((x - {x}).square() + (y - {y}).square() + (z - {z}).square()).sqrt() - {h}     # (here: the distance from a point, less {h})
#@@#
low_level_field({var}_logic)'''

_LOW_LEVEL_BODY = '''def {var}_logic(x, y, z):
    # Your own body: x, y and z are the coordinates (fields). Return a number that is negative inside the body, zero on its
    # surface and positive outside -- ideally the distance to the surface. Math: + - * / **, x.sqrt() x.square() x.abs() x.sin()
    # x.cos(), a.max(b) a.min(b), maximum(a, b, c) minimum(a, b, c).
    return ((x - {x}).square() + (y - {y}).square() + (z - {z}).square()).sqrt() - {h}     # (here: a ball of radius {h})
#@@#
low_level_body({var}_logic)'''

# What the menu says of an entry when the mouse rests on it
HINTS = {
    'instance': tr('A linked copy of the selected model: the same shape, following every change of it, that can only be moved and rotated (Ctrl+D)'),
}

# A profile or a curve made from the menu: its points are made with it (each a model of its own, drawn as a dot, with the gizmo that moves and
# rotates it), in the horizontal plane at the place of the click
def _gizmoed_point(name, x, y, z, shown=True, corner=False, size=None):
    ''' The statements of a point that is a model of its own, with its gizmo (so that it can be dragged).  `shown` False: the line that shows the point where it is is left out
        (the points of the profile of an armature are shown by the clone of it at the armature's first node, not at the origin).  `corner`: the point says `smooth=False` (a node in the middle of
        an armature is a corner: only its ends are spline points); `size`: the text of its scale (1 when not given) '''
    scale = '1' if size is None else size
    return ('%s = point(%s, %s, %s%s)\n%s = gizmo(\n    %s,\n    move=(var(0), var(0), var(0)),\n    rotate=(var(0), var(0), var(0)),\n'
            '    scale=(var(%s), var(%s), var(%s)),\n)\n%s' % (name, x, y, z, ', smooth=False' if corner else '', name, name, scale, scale, scale,
                                                                  ('%s\n' % name) if shown else ''))


def _points(*places, base='{var}', shown=True, corners=(), size=None):
    ''' The points a profile or a line made from the menu is made of: each a model of its own, with its gizmo (so that it can be dragged, and the face or the line
        with all of them), written above the call.  `places` are the (x, y, z) texts of the template; `corners` the numbers (from 0) of the points that are corners; `size` the text of their scale '''
    out = []
    for k, (x, y, z) in enumerate(places, 1):
        out.append(_gizmoed_point('%s_p%d' % (base, k), x, y, z, shown, (k - 1) in corners, size))
    return ''.join(out), ', '.join('%s_p%d' % (base, k) for k in range(1, len(places) + 1))


_PROFILE_POINTS, _PROFILE_LIST = _points(('{xm}', '{ym}', '{z}'), ('{xp}', '{ym}', '{z}'), ('{xp}', '{yp}', '{z}'), ('{xm}', '{yp}', '{z}'))
_PROFILE = _PROFILE_POINTS + '#@@#\nprofile([' + _PROFILE_LIST + '])'

_LINE_POINTS, _LINE_LIST = _points(('{xm}', '{y}', '{z}'), ('{x}', '{yp}', '{z}'), ('{xp}', '{y}', '{z}'))
_POLYLINE = _LINE_POINTS + '#@@#\npolyline([' + _LINE_LIST + '])'
_SPLINE = _LINE_POINTS + '#@@#\nspline([' + _LINE_LIST + '])'
_CHAIN = _LINE_POINTS + '#@@#\nchain([' + _LINE_LIST + '], radii={q})'
# The cross-section of an armature made from the menu: a profile of four points -- a square whose corners are spline points, nearly a circle of the radius {q} -- in the plane z = 0 at the
# origin, written above the armature: each point a model of its own with its gizmo, none drawn there.  The armature is swept along its nodes from it (swap it by dropping another profile on it
# in the model tree); the clone of it shown at the first node, written under the armature's line, has the dots of its points
_CUT_POINTS, _CUT_LIST = _points(('{qa}', '{qa}', '0'), ('{qn}', '{qa}', '0'), ('{qn}', '{qn}', '0'), ('{qa}', '{qn}', '0'), base='{var}_cut', shown=False)
_CUT = _CUT_POINTS + '{var}_cut = profile([' + _CUT_LIST + '], smooth=True)\n'
_FACE = '\n#@@@#\n{var}_face = cut_face({var})\n{var}_face'
_ARMATURE = _LINE_POINTS + _CUT + '#@@#\narmature([' + _LINE_LIST + '], profile={var}_cut, sizes=[' + ', '.join(['var(1)'] * (_LINE_LIST.count(',') + 1)) + '], name="{var}")' + _FACE


# The loops of new feature models: half a face drawn on the front view, as (x, y, z) in halves of the size from the place -- an outline from the chin to the top of the head (open, its ends
# on the plane of the mirror), an eye (a ring), a mouth (open, the end on the plane is where it is mirrored) and a nose (open, both ends on the plane, a ridge in front of the face)
_HALF_FACE = {
    'o': (False, [(0.0, 0.1, -1.0), (0.55, 0.1, -0.8), (0.85, 0.1, -0.2), (0.8, 0.1, 0.5), (0.45, 0.1, 0.95), (0.0, 0.1, 1.05)]),
    'e': (True, [(0.4 + 0.2 * math.cos(math.radians(60.0 * i)), 0.0, 0.25 + 0.12 * math.sin(math.radians(60.0 * i))) for i in range(6)]),
    'm': (False, [(0.0, 0.0, -0.45), (0.2, 0.0, -0.5), (0.4, 0.0, -0.42)]),
    'n': (False, [(0.0, -0.25, 0.1), (0.12, -0.15, -0.15), (0.0, -0.2, -0.3)]),
}


def _feature_model_text():
    ''' Feature models made from the menu: half a face (see _HALF_FACE), mirrored across the plane through the place -- each point a model of its own with its gizmo, and the call through
        the loops with every choice written out, to change in the script.  The places of the points are worked out in `_values` (f<loop><point>x, y, z) '''
    texts, loops = [], []
    for key, (closed, rows) in _HALF_FACE.items():
        places = [('{f%s%dx}' % (key, i), '{f%s%dy}' % (key, i), '{f%s%dz}' % (key, i)) for i in range(len(rows))]
        pts, listing = _points(*places, base='{var}_%s' % key)
        texts.append(pts)
        loops.append('feature([' + listing + ']' + (', closed=True' if closed else '') + ')')
    return ''.join(texts) + ('#@@#\nfeature_model([' + ', '.join(loops) + '], view="front", mirror=("x", {x}), snap=0, openings=True, trim=True, fill_holes=8, back=False, thickness={t}, '
                             'name="{var}")')


_FEATURE_MODEL = _feature_model_text()

# What an entry can be made OF the models selected, as DATA -- the entries that are made of what is selected, each with the words for its tooltip and the WAYS it is made, tried
# in the order they are listed: (the kinds of model it is made of, the least and the most of them (None: any number), the call it is written as -- `{names}` is those models in
# the order they were selected, `{name}` the first).  A way is taken when the selection has the right number of models of its kinds and none of the kinds of the ways before it;
# with none of them selected the entry is made from its own template (new points to drag).  The menu, its tooltips and the call are all read from this: a function the library
# can make of a kind of model is one more row here, and nothing else in the menus names it
FROM_SELECTION = {
    'profile': (tr('A 2D shape from points or from a surface.  With points selected: made from them, in the order you selected them.  With a surface selected: its '
                  'outline (a flat face exactly; a surface that is not flat is projected onto a plane).  With none: four new points to drag.  '
                  'Press its edge and drag to pull a point out of it; double-click a point to make it a corner or a spline point'),
               [({'point'}, 3, None, 'profile([{names}])'), ({'curve'}, 1, None, 'profile({name})'), ({'surface'}, 1, None, 'profile({name})')]),
    'polyline': (tr('A set of lines through points.  With points selected: made from them, in the order you selected them.  With none: three new points to '
                    'drag.  Press the line and drag to pull a point out of it; double-click a point to make it a corner or a spline point'),
                 [({'point'}, 2, None, 'polyline([{names}])')]),
    'spline': (tr('A smooth curve through points.  With points selected: made from them, in the order you selected them.  With none: three new points to '
                  'drag.  Press the curve and drag to pull a point out of it; double-click a point to make it a corner or a spline point'),
               [({'point'}, 2, None, 'spline([{names}])')]),
    'chain': (tr('An armature through points: a round cone between each two, thick where the point is big.  With points selected: made from them, in the order you selected them.  '
                 'With none: three new points to drag.  The size of a point -- the gold ring of its gizmo -- is how thick the armature is there'),
              [({'point'}, 1, None, 'chain([{names}], radii=3)')]),
    'armature': (tr('A part of a character: a smooth path through points, thick where its size is big (a path extrude), and the joints of its skeleton.  With points selected: made '
                'from them, in the order you selected them.  With none: three new points to drag.  The circle round a point is how thick the armature is there (drag it, or Shift + wheel over the point); the gold ring of its gizmo is how strongly the path leaves it; '
                'click a point in the middle of an armature and place a node to branch from it'),
             [({'point'}, 1, None, 'armature([{names}], radii=3)')]),
}

# (function, group, template)
PRIMITIVES = [
    ('sphere', '3D', 'sphere({h}, ({x}, {y}, {z}))'),
    ('box', '3D', 'box(({xm}, {ym}, {zm}), ({xp}, {yp}, {zp}))'),
    ('rounded_box', '3D', 'rounded_box(({xm}, {ym}, {zm}), ({xp}, {yp}, {zp}), {r})'),
    ('cylinder', '3D', 'cylinder({h}, {s}, ({x}, {y}, {zm}))'),
    ('cone', '3D', 'cone({h}, {s}, ({x}, {y}, {zm}))'),
    ('torus', '3D', 'torus({h}, {q}, ({x}, {y}, {z}))'),
    ('pyramid', '3D', 'pyramid(({xm}, {ym}), ({xp}, {yp}), {zm}, {s})'),
    ('prism', '3D', 'prism(({xm}, {ym}), ({xp}, {ym}), ({x}, {yp}), {zm}, {zp})'),
    ('half_space', '3D', 'half_space((0, 0, 1), ({x}, {y}, {z}))'),
    ('chain', '3D', _CHAIN),
    ('armature', 'Character', _ARMATURE),
    ('feature_model', 'Character', _FEATURE_MODEL),
    ('low_level_body', '3D', _LOW_LEVEL_BODY),
    ('circle', '2D', 'circle({h}, ({x}, {y}))'),
    ('rectangle', '2D', 'rectangle(({xm}, {ym}), ({xp}, {yp}))'),
    ('rounded_rectangle', '2D', 'rounded_rectangle(({xm}, {ym}), ({xp}, {yp}), {r})'),
    ('ring', '2D', 'ring({h}, {q}, ({x}, {y}))'),
    ('polygon', '2D', 'polygon({h}, {n}, ({x}, {y}))'),
    ('triangle', '2D', 'triangle(({xm}, {ym}), ({xp}, {ym}), ({x}, {yp}))'),
    ('profile', '2D', _PROFILE),
    ('polyline', '1D', _POLYLINE),
    ('spline', '1D', _SPLINE),
    ('point', 'Points', 'point({x}, {y}, {z})'),
    ('symmetry_planes', 'Symmetry', 'symmetry_planes(planes=1, kind=\'axis\', centre=({x}, {y}, {z}), axis=(0, 0, 1))'),
    ('plane', 'Surfaces', 'plane(({x}, {y}, {z}), (0, 0, 1))'),
    ('sphere_surface', 'Surfaces', 'sphere_surface({h}, ({x}, {y}, {z}))'),
    ('cylinder_surface', 'Surfaces', "cylinder_surface({h}, 'z', ({x}, {y}, 0))"),
    ('wave_surface', 'Surfaces', 'wave_surface({q}, {s}, "x", {z})'),
    ('distance_to_point', 'Fields', 'distance_to_point(({x}, {y}, {z}))'),
    ('radial_field', 'Fields', "radial_field(({x}, {y}, {z}), 'z')"),
    ('z_field', 'Fields', 'z_field()'),
    ('noise_field', 'Fields', 'noise_field({s}, {n})'),
    ('wave', 'Fields', "wave('x', {s}, {t})"),
    ('low_level_field', 'Fields', _LOW_LEVEL_FIELD),
    # What a game is made of (see docs/gamedev.md): the ground, a room, a kit, a rock, a tree, a crate, a barrel -- made where the menu is; the numbers are for the user to say
    ('terrain', 'Game', 'terrain(size=({s}, {s}), height={t}, scale={h}, center=({x}, {y}))'),
    ('room', 'Game', 'build_level(room(({xm}, {ym}, {z}), ({xp}, {yp}, {zp})))'),
    ('kit', 'Game', 'kit(({h}, {h}, {h})).build(["###", "###"])'),
    ('rock', 'Game', 'placed(rock({h}), ({x}, {y}, {z}))'),
    ('tree', 'Game', 'placed(tree({s}, {q}, {h}), ({x}, {y}, {z}))'),
    ('crate', 'Game', 'placed(crate({h}), ({x}, {y}, {z}))'),
    ('barrel', 'Game', 'placed(barrel({q}, {h}), ({x}, {y}, {z}))'),
]

# The PRIMITIVES -- the most basic, low-level representation of each kind of thing: a sphere, a box, a cylinder, a cone, a torus, a pyramid and a prism for 3D; a circle, a rectangle, a triangle,
# and a polygon for 2D (a profile, a 2D shape made of points, is a Parametric shape); a polyline and a spline for 1D; a point; a plane, a sphere surface and a cylinder surface; a distance, a radial, a z and a noise field.  The menus show these under
# Primitives, apart.  Everything else the library can make with no argument -- a rounded box, a ring, a wave, noise, your own low-level logic, a custom block -- is not a primitive, however
# little it needs: it is a Parametric shape
BASIC = frozenset((
    'sphere', 'box', 'cylinder', 'cone', 'torus', 'pyramid', 'prism',
    'circle', 'rectangle', 'triangle', 'polygon',
    'polyline', 'spline',
    'point',
    'symmetry_planes',
    'plane', 'sphere_surface', 'cylinder_surface',
    'distance_to_point', 'radial_field', 'z_field', 'noise_field',
))

# The number of an operation's call that a FIELD takes the place of when one is selected with the body -- `offset(tile, swell)`
# -- the way a field dropped on the call in the model tree does it (every size, radius, thickness of the library takes a field)
FIELD_SLOTS = {n: 't' for n in ('offset', 'shell', 'solidify', 'shell_inside', 'shell_outside', 'shell_centered', 'offset_exact',
                                'shell_exact', 'smooth', 'round_edges', 'fill_corners')}

# The values the templates of an entry are filled with where the menu has nothing better than a default: a number, a text, or '$key' (what the menu
# works out for the place and the size of the model).  Nothing is asked: what an entry writes is in the script, in front of the user, to be edited
# there -- every argument of the call, the defaults too (see fieldev.completion)
PARAMS = {
    'offset': {'t': '$t'},
    'offset_exact': {'t': '$t'},
    'solidify': {'t': '$t'},
    'shell': {'t': '$t'},
    'shell_inside': {'t': '$t'},
    'shell_outside': {'t': '$t'},
    'shell_centered': {'t': '$t'},
    'shell_exact': {'t': '$t'},
    'smooth': {'t': '$t', 'n': 3},
    'round_edges': {'t': '$t'},
    'fill_corners': {'t': '$t'},
    'move': {'dx': '$s', 'dy': 0, 'dz': 0},
    'rotate_z': {'angle': 45},
    'scale_xyz': {'sx': 1.5, 'sy': 1.5, 'sz': 1.5},
    'array_x': {'n': 3, 's': '$s'},
    'array_xy': {'nx': 3, 'ny': 3, 'dx': '$s', 'dy': '$s'},
    'array_polar_z': {'n': 6},
    'rounded_box': {'r': 0.3},
    'rounded_rectangle': {'r': 0.3},
    'polygon': {'n': 6},
    'noise_field': {'n': 3},
    'smooth_union': {'t': '$t'},
    'smooth_difference': {'t': '$t'},
    'smooth_intersection': {'t': '$t'},
    'bevel_union': {'t': '$t'},
    'rotate_x': {'angle': 45},
    'rotate_y': {'angle': 45},
    'array_polar': {'n': 6},
    'array_xyz': {'nx': 3, 'ny': 3, 'nz': 3, 'dx': '$s', 'dy': '$s', 'dz': '$s'},
    'twist_z': {'tw': 2},
}


def _fmt(v):
    ''' A number as it is written in a script: whole numbers without decimals, the others in their shortest form '''
    v = float(v)
    return str(int(v)) if v == int(v) and abs(v) < 1e12 else ('%.8g' % v)


def _default_text(d, values):
    if isinstance(d, str):
        return values[d[1:]] if d.startswith('$') else d
    return _fmt(d)


def _apply_params(name, values):
    ''' The values of the entry that the menu fills in itself: its defaults '''
    for k, d in PARAMS.get(name, {}).items():
        values[k] = _default_text(d, values)
    angle = values.get('angle')
    if angle is not None:
        values['angle_rad'] = _fmt(round(math.radians(float(angle)), 6))
    return values


# What a group of primitives makes (the kind: see fieldev.kinds), for the icon beside each entry
GROUP_KINDS = {'1D': 'curve', '3D': 'solid', '2D': 'profile', 'Points': 'point', 'Surfaces': 'surface', 'Fields': 'field', 'Symmetry': 'symmetry', 'Character': 'solid'}
# (function, group, template, takes a second model: True = needs one, 'optional' = takes the other selected models if there are any)
OPERATIONS = [
    ('offset', 'Grow and hollow', 'offset({body}, {t})', 'optional'),
    ('shell', 'Grow and hollow', 'shell({body}, {t})', 'optional'),
    ('solidify', 'Grow and hollow', 'solidify({body}, {t})', 'optional'),
    ('shell_inside', 'Grow and hollow', 'shell_inside({body}, {t})', 'optional'),
    ('shell_outside', 'Grow and hollow', 'shell_outside({body}, {t})', 'optional'),
    ('shell_centered', 'Grow and hollow', 'shell_centered({body}, {t})', 'optional'),
    ('offset_exact', 'Grow and hollow', 'offset_exact({body}, {t})', 'optional'),
    ('shell_exact', 'Grow and hollow', 'shell_exact({body}, {t})', 'optional'),
    # A texture on the surface of a body: a surface that is selected with it (or a field, or a body) is where it goes
    ('texture', 'Texturing', 'texture({body})', 'optional'),
    ('smooth', 'Round and bevel', 'smooth({body}, {t}, {n})', 'optional'),
    ('round_edges', 'Round and bevel', 'round_edges({body}, {t})', 'optional'),
    ('fill_corners', 'Round and bevel', 'fill_corners({body}, {t})', 'optional'),
    ('move', 'Moving', 'move({body}, ({dx}, {dy}, {dz}))', False),
    ('rotate_z', 'Moving', 'rotate_z({body}, {angle_rad})', False),
    ('scale_xyz', 'Moving', 'scale_xyz({body}, ({sx}, {sy}, {sz}))', False),
    ('reflect_x', 'Moving', 'reflect_x({body})', False),
    ('symmetric_x', 'Moving', 'symmetric_x({body})', False),
    ('symmetric_y', 'Moving', 'symmetric_y({body})', False),
    ('symmetric_z', 'Moving', 'symmetric_z({body})', False),
    # A linked copy (Ctrl+D): the model itself, placed where its own gizmo says -- written with the model held by reference (`# shadow:`)
    ('instance', 'Repeating', 'instance({body})', False),
    ('array_x', 'Repeating', 'array_x({body}, {n}, {s})', False),
    ('array_xy', 'Repeating', 'array_xy({body}, {nx}, {ny}, ({dx}, {dy}))', False),
    ('array_polar_z', 'Repeating', 'array_polar_z({body}, {n})', False),
    # Extruding: a 2D shape pulled into a solid, straight or along a curve (a curve, or points that make one)
    ('extrude', 'Extruding', 'extrude({body}, 0, {s})', False),
    ('path_extrude', 'Extruding', 'path_extrude({body}, {other})', True),
    ('union', 'Combining', 'union({body}, {other})', True),
    ('difference', 'Combining', 'difference({body}, {other})', True),
    ('intersection', 'Combining', 'intersection({body}, {other})', True),
    # A surface chosen by bodies: the first selected model's surface where the others meet it; one model alone: all of its surface
    # ('optional': the others are not needed, but taken when several models are selected: {others} is ", a, b" or nothing)
    ('surface_from_bodies', 'Surfaces', 'surface_from_bodies({body}{others})', 'optional'),
    # Arithmetic on fields (a number is a field too; of a body they work on its values, which makes a field)
    ('add_fields', 'Field math', 'add_fields({body}, {other})', True),
    ('subtract_fields', 'Field math', 'subtract_fields({body}, {other})', True),
    ('multiply_fields', 'Field math', 'multiply_fields({body}, {other})', True),
    ('divide_fields', 'Field math', 'divide_fields({body}, {other})', True),
    ('power_field', 'Field math', 'power_field({body}, {other})', True),
    ('min_fields', 'Field math', 'min_fields({body}, {other})', True),
    ('max_fields', 'Field math', 'max_fields({body}, {other})', True),
    ('abs_field', 'Field math', 'abs_field({body})', False),
    ('negate_field', 'Field math', 'negate_field({body})', False),
    ('sqrt_field', 'Field math', 'sqrt_field({body})', False),
    ('square_field', 'Field math', 'square_field({body})', False),
    ('field_from_body', 'Field math', 'field_from_body({body})', False),
    ('body_from_field', 'Field math', 'body_from_field({body})', False),
    # Importing: the surface of any model as the exact distance to its meshed surface (a file is imported from the menu of
    # empty space, Import model...)
    ('tessellate', 'Importing', 'tessellate({body})', False),
    # Measuring: both are in the first menu of a body (QUICK), not under a group
    ('center', 'Measuring', 'center({body})', False),
    ('bounding_box', 'Measuring', 'bounding_box({body})', False),
    # A field made of a point: how far each place is from it (in the first menu of a point, and only there)
    ('distance_to_point', 'Fields', 'distance_to_point({body})', False),
    # More ways to put models together (a blend where they meet: smooth, or cut at 45 degrees), to turn, mirror, repeat and deform them, and to paint them
    ('smooth_union', 'Combining', 'smooth_union({body}, {other}, {t})', True),
    ('smooth_difference', 'Combining', 'smooth_difference({body}, {other}, {t})', True),
    ('smooth_intersection', 'Combining', 'smooth_intersection({body}, {other}, {t})', True),
    ('bevel_union', 'Combining', 'bevel_union({body}, {other}, {t})', True),
    ('morph', 'Combining', 'morph({body}, {other}, 0.5)', True),
    ('rotate_x', 'Moving', 'rotate_x({body}, {angle_rad})', False),
    ('rotate_y', 'Moving', 'rotate_y({body}, {angle_rad})', False),
    ('reflect_y', 'Moving', 'reflect_y({body})', False),
    ('reflect_z', 'Moving', 'reflect_z({body})', False),
    ('array_polar', 'Repeating', 'array_polar({body}, {n})', False),
    ('array_xyz', 'Repeating', 'array_xyz({body}, {nx}, {ny}, {nz}, ({dx}, {dy}, {dz}))', False),
    ('twist_z', 'Bend and twist', 'twist_z({body}, {tw})', False),
    ('bend_z', 'Bend and twist', 'bend_z({body}, {s})', False),
    ('taper_xy_z', 'Bend and twist', 'taper_xy_z({body}, ({x}, {y}, {zm}), {s}, 0.5)', False),
    ('shear_x_y', 'Bend and twist', 'shear_x_y({body}, ({x}, {ym}), {s}, {t})', False),
    # The colours a body is shown and exported with (the presets: see material_presets(); a material of your own is `material(...)`)
    ('with_materials', 'Materials', 'with_materials({body}, material_preset("{preset}"))', False),
    # Snow, moss or dust laid on every surface of the body that faces up, as geometry (see fieldev.stdlib.finish)
    ('covered', 'Materials', 'covered({body}, depth={t}, angle=50)', False),
    # The cross-section of an armature, at its first node (made with every armature the menu makes: here for one that was written by hand)
    ('cut_face', 'Character', 'cut_face({body})', False),
    # A character: the armatures selected are joined into one body (the other half a mirror image), and are the skeleton of it
    ('character', 'Character', 'character([{body}{others}], blend="auto", symmetric="x")', 'optional'),
    ('skeleton_of', 'Character', 'skeleton_of([{body}{others}], mirror="x")', 'optional'),
]


# (operations that are in the first menu of a body, not under a group: used all the time)
QUICK = ('center', 'bounding_box', 'distance_to_point')

# The "Python" menu: the most basic features of the language as blocks of plain code, written at the top level of the script, at the insertion point of the model tree (not
# made into a model: no `name = ...`, no display line).  The code is edited in the code editor; the tree shows the blocks and what is in them.  A body of `pass` is where the
# code of the block goes.  (name, label, what it is, the code)
PYTHON = [
    ('variable', 'variable', tr('A name for a number, a text or any value: it is used by its name further down'), 'value = 10'),
    ('if', 'if', tr('Runs the code under it only when the condition is true'), 'if value > 5:\n    pass'),
    ('if_else', 'if / else', tr('One code when the condition is true, another when it is not'), 'if value > 5:\n    pass\nelse:\n    pass'),
    ('for_range', 'for loop (a count)', tr('Runs the code under it once for each number 0, 1, 2 ... up to the count'), 'for i in range(5):\n    pass'),
    ('for_each', 'for loop (a list)', tr('Runs the code under it once for each item of a list'), 'for item in [1, 2, 3]:\n    pass'),
    ('while', 'while loop', tr('Runs the code under it again and again while the condition is true'), 'count = 0\nwhile count < 5:\n    count += 1'),
    ('function', 'function (def)', tr('Code with a name that takes values and gives one back: it is called by its name'), 'def my_function(x):\n    return x'),
    ('class', 'class', tr('A kind of object of your own, with functions of its own'), 'class MyClass:\n    def __init__(self):\n        pass'),
    ('list', 'list', tr('Several values under one name: values[0] is the first'), 'values = [1, 2, 3]'),
    ('list_comprehension', 'list from a loop', tr('A list made by a loop, in one line'), 'squares = [i * i for i in range(5)]'),
    ('dictionary', 'dictionary', tr('Values found by a name: settings["size"]'), 'settings = {"size": 10}'),
    ('try', 'try / except', tr('Runs the code, and another code when it fails'), 'try:\n    pass\nexcept Exception as error:\n    print(error)'),
    ('with', 'with (a file)', tr('Opens a file for the code under it, and closes it after'), 'with open("file.txt") as f:\n    text = f.read()'),
    ('import', 'import', tr('Brings in a module of Python: math, random ...'), 'import math'),
    ('print', 'print', tr('Writes a value to the message pane of the script'), 'print("hello")'),
]


def _blocks():
    ''' The custom blocks the menus offer (see fieldev.blocks): [{name, doc, operation, primitive}] '''
    try:
        from fieldev import blocks
        return [b for b in blocks.info() if b['operation'] or b['primitive']]
    except Exception:
        return []


# What a game engine asks of an asset -- units, the up axis, a budget of triangles, UV maps, baked textures, a skeleton, the pivot -- is the arguments of `export_mesh`.  These
# entries of the Export menu of a model write the call into the script, with the choices written out for the user to change and run (key, group in the menu, label, tooltip, the call;
# `{var}` is the model)
EXPORTS = [
    ('game', '', tr('Game-ready glTF'),
     tr('A .glb with its origin at the feet, UV islands packed into the texture, smooth normals and a budget of 8000 triangles: export_mesh(model, "model.glb", ...)'),
     'export_mesh({var}, "{var}.glb", max_triangles=8000, pivot="base", uvs=uv_unwrap(), normals=True)'),
    ('engine_obj', '', tr('OBJ in metres, Y up'),
     tr('A file as most engines read it: metres, and Y up (the model is turned, not mirrored)'),
     'export_mesh({var}, "{var}.obj", units="m", up="y")'),
    ('mirror', '', tr('Exactly symmetric mesh'),
     tr('The half on the +x side is the model; the other half is its exact mirror image'),
     'export_mesh({var}, "{var}.glb", symmetric="x")'),
    ('rigged', '', tr('With a skeleton'),
     tr('A rigged glTF: the joints of skeleton_of([...]) -- put the armatures in -- and the weights that move each vertex'),
     'export_mesh({var}, "{var}.glb", pivot="base", skeleton=skeleton_of([...]))'),
    ('textures', '', tr('Baked textures'),
     tr('The colour, normal map and occlusion / roughness / metalness pictures, made from the fields of the model at every texel of its UV map'),
     'export_mesh({var}, "{var}.glb", uvs=uv_unwrap(), textures=bake(size=1024))'),
    ('uv_box', tr('UV map'), tr('Box projection'),
     tr('Each triangle is projected along the axis its normal is mostly along, seen from outside; a picture of the UV map is written beside the file to check it'),
     'export_mesh({var}, "{var}.glb", uvs=uv_box(), uv_layout="{var}_uvs.png")'),
    ('uv_planar', tr('UV map'), tr('Planar (floor, wall, relief)'),
     tr('One projection along an axis for the whole surface'),
     'export_mesh({var}, "{var}.glb", uvs=uv_planar("z"), uv_layout="{var}_uvs.png")'),
    ('uv_cylinder', tr('UV map'), tr('Cylinder'),
     tr('u is the angle round an axis through the middle of the model, v the height along it'),
     'export_mesh({var}, "{var}.glb", uvs=uv_cylinder("z"), uv_layout="{var}_uvs.png")'),
    ('uv_sphere', tr('UV map'), tr('Sphere'),
     tr('u is the longitude and v the latitude about the middle of the model: the map a globe is drawn on'),
     'export_mesh({var}, "{var}.glb", uvs=uv_sphere("z"), uv_layout="{var}_uvs.png")'),
    ('uv_unwrap', tr('UV map'), tr('Unwrapped atlas'),
     tr('The surface cut into islands, laid flat and packed into the square of the texture'),
     'export_mesh({var}, "{var}.glb", uvs=uv_unwrap(), uv_layout="{var}_uvs.png")'),
    ('uv_armature', tr('UV map'), tr('By armature part'),
     tr('For a character: each armature laid out as a tube, each piece of feature models flat as it was drawn'),
     'export_mesh({var}, "{var}.glb", uvs=uv_armature(), uv_layout="{var}_uvs.png")'),
]


def _export_text(r):
    ''' The call of an export for a game engine, written into the script: `name` is `export_game|<entry>|<model>` '''
    _, key, var = r['name'].split('|', 2)
    for k, _group, _label, _doc, code in EXPORTS:
        if k == key:
            return code.replace('{var}', var)
    raise ValueError(tr('the export menu has no entry called %s') % key)


def catalog():
    ''' The lists as JSON for the menus: {"primitives": [{name, group, type}], "operations": [{name, group, other}]}; the custom
        blocks are in them too (group "Custom blocks", type "block") '''
    from fieldev.kinds import describe
    from fieldev import user_primitives
    blocks = _blocks()
    basic = user_primitives.basic(BASIC)             # (what the user chose to show under Primitives: BASIC less what was taken out, and what was put in)
    given = user_primitives.labels()                 # (and the names the user gave the shapes of the library: the menus show those)
    return json.dumps({
        'kinds': describe(),
        'primitives': [dict({'name': n, 'group': g, 'type': GROUP_KINDS.get(g, 'solid'), 'with_bodies': n in FROM_SELECTION, 'primitive': n in basic,
                             'from_selection': n in FROM_SELECTION},
                            **({'label': given[n]} if n in given else {}),
                            **({'doc': FROM_SELECTION[n][0]} if n in FROM_SELECTION else {}),
                            # (a 2D shape that is written with an x and a y only lies in the plane z = 0: the place it is made at is where the ray under the cursor meets that plane)
                            **({'flat': True} if g == '2D' and '{z}' not in t else {}))
                       for n, g, t in PRIMITIVES]
                      + user_primitives.catalog_entries()                # (the primitives of the user's own: a model of a script, kept in a file of theirs)
                      + [{'name': b['name'], 'group': 'Custom blocks', 'type': 'block', 'doc': b['doc']}
                         for b in blocks if b['primitive']],
        # (`other`: takes the other selected models; `needs_other`: is not offered without a second model)
        'operations': [dict({'name': n, 'group': g, 'other': bool(o), 'needs_other': o is True, 'quick': n in QUICK},
                            **({'hint': HINTS[n]} if n in HINTS else {}))
                       for n, g, _, o in OPERATIONS]
                      + [{'name': b['name'], 'group': 'Custom blocks', 'other': False, 'type': 'block', 'doc': b['doc']}
                         for b in blocks if b['operation']],
        'python': [{'name': n, 'label': l, 'doc': d} for n, l, d, _code in PYTHON],
        'export': [{'name': k, 'group': g, 'label': l, 'doc': d} for k, g, l, d, _code in EXPORTS],
    })




def _others(r):
    ''' The other selected models as [{name, type, role, cls}] (the request's `others`; the names of `other` when there are none) '''
    others = r.get('others')
    if others is None:
        others = [{'name': n.strip()} for n in (r.get('other') or '').split(',') if n.strip()]
    return others


# ---- What an entry of a menu takes, and whether the models selected are that.
#
# Every model is classified once (_tag): by its kind.  An entry says which of those it
# takes: a list of SIGNATURES -- the tags it accepts, and the tags it must be given at least one of.  A selection fits an entry when all of
# its models are accepted by ONE signature and the signature's needs are met; an entry it does not fit is greyed out in the menu (nothing is
# said: it is not offered).  A model of no known kind (not run yet) fits anything, and so does an entry that declares nothing (a custom block).
from fieldev.kinds import SHAPES as _SHAPES                                                       # (what a geometric operation works on)
def _parameters_of(name):
    ''' The names of the parameters of the library's function `name`, in order ([] when there is none of that name) '''
    try:
        import fieldev
        return list(inspect.signature(getattr(fieldev, name)).parameters)
    except Exception:
        return []


def _takes(name):
    ''' What the operation `name` takes, as SIGNATURES (the kinds it accepts together, and the kinds it must be given at least one of): what the library function says of itself
        (`fn._takes`, see fieldev.kinds.takes -- no list of them is kept here), and None for a function that says nothing: it takes any shape '''
    try:
        import fieldev
        declared = getattr(getattr(fieldev, name, None), '_takes', None)
    except Exception:
        declared = None
    return declared or None


def _tag(m):
    ''' What a selected model is, for what an entry takes: its kind -- solid, profile, field, surface, point, import --
        None when it is not known (a model that has not run) '''
    return m.get('type') or None


def _selection_fits(kind, name, models):
    ''' Whether the models selected (each {type, role, cls}) are what the entry takes (see above) '''
    if kind == 'primitive':
        signatures = None
    else:
        group = next((g for n, g, _, _ in OPERATIONS if n == name), None)
        signatures = _takes(name) or ([(_SHAPES, [])] if group else None)
    tags = [t for t in map(_tag, models) if t]
    if not signatures or not tags:
        return True
    return any(all(t in accepts for t in tags) and all(any(t in need for t in tags) for need in needs) for accepts, needs in signatures)


# What a New entry makes, for whether it fits the models selected.  A SHAPE -- a 3D shape, a 2D shape, a 1D shape, a point, a surface, a field -- is a PLACEMENT: it is made wherever the menu
# is, so it is valid for any selection (a line or a profile is made of the points, curve or surface that are selected when they fit, and of new points when not).  Everything else is valid
# only when some function that says what it takes (see fieldev.kinds.takes) takes the selection together with it.  Nothing here names an entry
_PLACEMENT_KINDS = frozenset(('solid', 'profile', 'curve', 'point', 'surface', 'field'))


def _primitive_fits(name, models):
    ''' Whether the New entry `name` is valid for the models selected (each {type, role, cls}); anything is valid for none '''
    if not models:
        return True
    group = next((g for n, g, _t in PRIMITIVES if n == name), None)
    kind = GROUP_KINDS.get(group, 'solid')
    if kind in _PLACEMENT_KINDS:
        return True             # (placed anywhere -- a line or a profile too: made of the points, curve or surface selected when they fit (see FROM_SELECTION), of new points when not)
    # (something to be given to another function: the kind of what it makes, as a selected model of it would be)
    made = {'type': kind}
    users = [n for n, g, _t, _o in OPERATIONS if _takes(n)]
    return any(_selection_fits('operation', n, list(models) + [made]) for n in users)


def _from_selection(name, models, values):
    ''' The call of a New entry that is made of the models selected (the ways it is made are data: see FROM_SELECTION) -- the points a profile or a curve goes through (in the
        order they were selected), a curve or a surface a profile is the outline of -- or None when what is selected is not what the entry takes (it is made from its own
        template then, with new points) '''
    ways = FROM_SELECTION.get(name, (None, []))[1]
    present = {m.get('type') for m in models}
    earlier = set()
    for kinds, least, most, template in ways:
        mine = [m['name'] for m in models if m.get('type') in kinds]
        if not earlier & present and len(mine) >= least and (most is None or len(mine) <= most):
            return template.format(names=', '.join(mine), name=mine[0])
        earlier |= kinds
    return None


def _own_point_names(shape_name):
    ''' The names of the points the model `shape_name` is made of (the corners of a profile): the variables of the last run that hold those very points '''
    try:
        from fieldev import runner
        names = runner.last_globals
        mine = {id(p) for p in (getattr(names.get(shape_name), 'points', None) or [])}
        return {n for n, value in names.items() if id(value) in mine}
    except Exception:
        return set()


def _build_operation(name, v, others):
    ''' The text of an operation that is given the models selected with the body (see OPERATIONS: 'optional'), or None when they say
        nothing it can use -- the template is written then '''
    body = v['body']
    if name == 'texture':
        # (a surface, a field or a body that is selected with the body is where the texture goes)
        regions = [o['name'] for o in others if o.get('type') in ('surface', 'field', 'solid', 'profile')]
        if regions:
            return 'texture(%s, region=%s)' % (body, regions[0])
    if name == 'path_extrude':
        # (the 2D shape and the path, whichever was selected first; points make a curve of their own, which is shown and edited like any other)
        models = [dict(v.get('body_info') or {}, name=body)] + list(others)
        profile = next((m['name'] for m in models if m.get('type') == 'profile'), None)
        path = next((m['name'] for m in models if m.get('type') == 'curve'), None)
        # (the points a 2D shape is made of are not points of the path: selecting a profile together with the points along its path must not put the profile's own
        # corners into the path -- a path that goes round the profile's outline too is a sweep of dozens of pieces)
        own = _own_point_names(profile)
        points = [m['name'] for m in models if m.get('type') == 'point' and m['name'] not in own]
        if profile and path:
            return 'path_extrude(%s, %s)' % (profile, path)
        if profile and len(points) >= 2:
            var = v.get('var') or 'path_extrude_1'
            return '%s_path = spline([%s])\n%s_path%spath_extrude(%s, %s_path)' % (var, ', '.join(points), var, PRELUDE, profile, var)
    slot = FIELD_SLOTS.get(name)
    if slot:
        fields = [o['name'] for o in others if o.get('type') == 'field']
        if not fields:
            return None
        for n, _, template, _ in OPERATIONS:
            if n == name:
                return template.format(**dict(v, **{slot: fields[0]}))
        return None
    return None


def _num(v):
    ''' A number as it is written in a script: at most four decimals, no trailing zeros '''
    s = ('%.4f' % v).rstrip('0').rstrip('.')
    return '0' if s in ('', '-0') else s


def _nice(v):
    ''' The round number (1, 2 or 5 times a power of ten) nearest to v on a logarithmic scale '''
    if not v > 0:
        return 10.0
    e = math.floor(math.log10(v))
    f = v / 10 ** e
    best = min((1.0, 2.0, 5.0, 10.0), key=lambda c: abs(math.log(f / c)))
    return best * 10 ** e


def _step(s):
    ''' The grid a place snaps to: the largest 1, 2 or 5 times a power of ten that is at most a twentieth of the size '''
    target = s / 20.0
    e = math.floor(math.log10(target))
    for c in (5.0, 2.0, 1.0):
        if c * 10 ** e <= target * 1.0000001:
            return c * 10 ** e
    return 10 ** e


def _stroke_text(name, places, smooth, r):
    ''' A profile, a polyline or a spline of the points `places` (3-tuples of numbers as texts): the points, each a model of its own with its gizmo, written above the call.  While
        the symmetry is on (`r['symmetry']`) the images of the points are made too, each following the point it is the image of (`symmetry_image`), and the shapes through them:
        the stroke itself and its images, those that meet where they cross a plane joined into one outline '''
    from fieldev import symmetry_creation as sym
    elements = sym.elements_of(r.get('symmetry'))
    points, listing = _points(*places)
    smooth_arg = ', smooth=True' if name == 'profile' and smooth else ''
    if not elements:
        return points + '#@@#\n' + '%s([%s]%s)' % (name, listing, smooth_arg)
    positions = [tuple(float(c) for c in p) for p in places]
    step = float((r.get('plane') or {}).get('step') or 0.0)
    tol = max(1e-4, 1e-3 * step)
    r['_symmetric'] = True
    symmetry_var = (r.get('symmetry') or {}).get('var') or 'symmetry_1'
    whole = sym.simple_images(positions, elements, tol)
    if whole is not None:
        # The images are strokes that touch nothing: each is the image of the stroke, like the image of any model, `{var}_m1 = symmetry_image({var}, symmetry_1, 1)`, written under the
        # stroke (so that whatever is done to the stroke -- a point dragged, pulled out of an edge, deleted -- is done to its images)
        text = points + '#@@#\n' + '%s([%s]%s)' % (name, listing, smooth_arg)
        for k, el in enumerate(whole, 1):
            text += (sym.POST if k == 1 else '') + sym.image_statement('{var}', '{var}_m%d' % k, el, symmetry_var)
        return text
    made, shapes = sym.stroke_structure(positions, elements, name, name == 'profile', tol)
    n = len(places)
    # (the image points, each held to the point it is the image of)
    images = ''
    symmetry_var = (r.get('symmetry') or {}).get('var') or 'symmetry_1'
    for i, e, k in made:
        images += sym.image_statement('{var}_p%d' % (i + 1), '{var}_p%d_m%d' % (i + 1, e + 1), elements[e], symmetry_var)

    def names(nodes):
        return ', '.join(sym.point_name('{var}', k, n, made) for k in nodes)

    def call(shape_name, nodes):
        if shape_name == 'profile' and smooth:
            return 'profile(\n    [%s],\n    smooth=True,\n)' % names(nodes)
        return '%s([%s])' % (shape_name, names(nodes))

    # (the first shape is the model itself; the others are each a shape of its own beside it, named `var_m1`, `var_m2` ...)
    extra = ''
    for k, (shape_name, nodes) in enumerate(shapes[1:], 1):
        extra += '{var}_m%d = %s\n{var}_m%d\n' % (k, call(shape_name, nodes), k)
    first_name, first_nodes = shapes[0]
    return points + images + extra + '#@@#\n' + call(first_name, first_nodes)


def _plane_template(name, r):
    ''' A profile or a line made on the work plane (`r['plane']`: origin, u, v, and the step of its grid, 0 for none): its points are laid out in the plane's own axes
        round the place of the click -- the corners of a square for a profile -- not in the horizontal plane, and on the grid when the plane snaps '''
    plane = r['plane']
    u = tuple(float(c) for c in plane['u'])
    v = tuple(float(c) for c in plane['v'])
    centre = tuple(float(r.get(k, 0.0)) for k in ('x', 'y', 'z'))
    h = _nice(float(r.get('scale', 10.0))) / 2.0
    step = float(plane.get('step') or 0.0)
    if step > 0:
        h = max(step, round(h / step) * step)               # (the points are on the grid too)

    def at(a, b):
        return tuple(_num(c + a * x + b * y) for c, x, y in zip(centre, u, v))

    places = [at(-h, -h), at(h, -h), at(h, h), at(-h, h)] if name == 'profile' else [at(-h, 0.0), at(0.0, h), at(h, 0.0)]
    return _stroke_text(name, places, False, r)


def _placed_template(name, r):
    ''' A profile, a polyline or a spline put down on the work plane: the points the user clicked, each a model of its own with its gizmo, and the call through them.
        A profile of a spline (`smooth`) has spline points '''
    places = [tuple(_num(float(c)) for c in p) for p in r['points']]
    if name == 'armature':
        return _armature_text(places, r.get('scale'), size=r.get('size'))
    return _stroke_text(name, places, r.get('smooth'), r)


def _armature_text(places, scale=None, size=None):
    ''' An armature put down in the viewport, node after node: the nodes, each a model of its own with its gizmo (so that it can be dragged), and the call through them with `sizes`, a var() for each node: how
        thick the armature is there (the circle round the node in the viewport).  The thickness is a sixth of the longest stretch between two nodes, a round number: an armature of a drawing is about that thick.  The first and the
        last node are spline points (round ends), every one in the middle is a corner.  `size`: the size of the nodes put down '''
    pts = [tuple(float(c) for c in p) for p in places]
    # (one node has no stretch to measure: the size of the place it is put at, a fifth of it)
    reach = max((math.dist(a, b) for a, b in zip(pts, pts[1:])), default=(scale or 10.0) * 1.2)
    points, listing = _points(*places, corners=set(range(1, len(places) - 1)))
    # (the cross-section of the armature: the square with spline points, whose radius is a sixth of the longest stretch, written above it as a profile of its own, and its clone under the armature)
    q = _nice(reach / 6.0)
    width = 0.75 * q
    plus, minus = _num(width), _num(-width)
    cut_points, cut_list = _points((plus, plus, '0'), (minus, plus, '0'), (minus, minus, '0'), (plus, minus, '0'), base='{var}_cut', shown=False)
    each = _num(float(size)) if size is not None else '1'
    entries = [each] * len(places)
    sizes = ', '.join('var(%s)' % e for e in entries)
    return points + cut_points + '{var}_cut = profile([%s], smooth=True)\n' % cut_list + '#@@#\n' + 'armature([%s], profile={var}_cut, sizes=[%s], name="{var}")' % (listing, sizes) + _FACE


def _symmetry_template(r, values):
    ''' A symmetry made from the menu: the mirror the viewport has -- `r['symdef']`: planes, kind, centre, axis, first (from the planes of a model, or the card) -- or a mirror
        at the place of the click: on the work plane while its view is open (its axis the plane's normal, its first plane along the plane's u), else the plane x = 0 through it '''
    d = r.get('symdef')
    if d:
        planes, kind, centre, axis, first = d['planes'], d['kind'], d['centre'], d['axis'], d['first']
    elif r.get('plane'):
        plane = r['plane']
        u, v = [float(c) for c in plane['u']], [float(c) for c in plane['v']]
        centre = [r.get('x', 0.0), r.get('y', 0.0), r.get('z', 0.0)]
        planes, kind = 1, 'axis'
        axis = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
        first = u
    else:
        planes, kind = 1, 'axis'
        centre = [r.get('x', 0.0), r.get('y', 0.0), r.get('z', 0.0)]
        axis, first = [0, 0, 1], [0, 1, 0]

    def vec(v):
        return '(%s)' % ', '.join(_num(float(c)) for c in v)
    if kind == 'turn':
        return "symmetry_planes(copies=%d, kind='turn', centre=%s, axis=%s, first=%s)" % (int(planes), vec(centre), vec(axis), vec(first))
    return 'symmetry_planes(planes=%d, kind=%r, centre=%s, axis=%s, first=%s)' % (int(planes), kind, vec(centre), vec(axis), vec(first))


def _default_stroke_template(name, values, r):
    ''' The profile, polyline or spline of the menu with a symmetry on: the places of its points, from the template's own numbers '''
    if name == 'profile':
        places = [(values['xm'], values['ym'], values['z']), (values['xp'], values['ym'], values['z']), (values['xp'], values['yp'], values['z']),
                  (values['xm'], values['yp'], values['z'])]
    else:
        places = [(values['xm'], values['y'], values['z']), (values['x'], values['yp'], values['z']), (values['xp'], values['y'], values['z'])]
    return _stroke_text(name, places, False, r)


def _material_preset_name(r):
    ''' The preset the Materials entry writes: the one the request names (a swatch of the materials card dropped on a model), else plastic '''
    from fieldev.stdlib.materials import material_presets
    name = str(r.get('preset') or 'plastic').strip().lower()
    if name not in material_presets():
        raise ValueError(tr('there is no material called %s') % name)
    return name


def _values(r):
    ''' What the templates are filled from: the place, the size, the models, and the boxes and numbers worked out from them '''
    name = r['name']
    s = _nice(float(r.get('scale', 10.0)))
    step = _step(s)

    if name == 'point':
        step = s / 1000.0                   # (a point is where the cursor is, to a thousandth of the span of a hundred pixels: not rounded to a grid of the view)

    def snap(v):
        return round(float(v) / step) * step

    if r.get('plane'):
        # (made on the work plane: the place is where its grid says, in the plane's axes -- rounding each of the world's coordinates would take it off the plane)
        x, y, z = (float(r.get(k, 0.0)) for k in ('x', 'y', 'z'))
    else:
        x, y, z = snap(r.get('x', 0.0)), snap(r.get('y', 0.0)), snap(r.get('z', 0.0))
    h = s / 2.0
    values = {
        'x': _num(x), 'y': _num(y), 'z': _num(z), 's': _num(s), 'h': _num(h), 't': _num(s / 10.0), 'q': _num(s / 6.0),
        'qa': _num(0.75 * s / 6.0), 'qn': _num(-0.75 * s / 6.0),
        'xm': _num(x - h), 'xp': _num(x + h), 'ym': _num(y - h), 'yp': _num(y + h), 'zm': _num(z - h), 'zp': _num(z + h),
        'body': r.get('body', ''), 'other': r.get('other', ''), 'var': r.get('var') or (name + '_1'),
    }
    # the loops of new feature models: half a face at the place (see _HALF_FACE)
    for key, (_closed, rows) in _HALF_FACE.items():
        for i, (dx, dy, dz) in enumerate(rows):
            values['f%s%dx' % (key, i)] = _num(x + dx * h)
            values['f%s%dy' % (key, i)] = _num(y + dy * h)
            values['f%s%dz' % (key, i)] = _num(z + dz * h)
    values['others'] = ', ' + values['other'] if values['other'] else ''       # (for a call that may have no other model)
    values['preset'] = _material_preset_name(r)
    values['body_info'] = r.get('body_info')
    return values


def _images_after(r, head, expression):
    ''' The images a model made with the symmetry on has, written under it (see symmetry_creation): the models a menu entry places -- a shape, a point, a surface, a field -- and
        not what it is made of other models (an operation), a profile or a line (their points have the images: see _stroke_text) '''
    if r.get('_symmetric') or not (r.get('symmetry') or {}).get('elements') or not (r.get('symmetry') or {}).get('var'):
        return ''
    from fieldev import symmetry_creation as sym
    if r['kind'] == 'operation':
        return _operation_images(r)
    if r['kind'] != 'primitive':
        return ''
    for n, group, _ in PRIMITIVES:
        if n == r['name']:
            if group not in _PLACED_GROUPS or n in ('profile', 'polyline', 'spline', 'symmetry_planes', 'armature', 'feature_model'):
                return ''
            break
    else:
        return ''
    if r.get('body') or r.get('other') or r.get('points'):
        return ''
    text = sym.post_for(r.get('var') or (r['name'] + '_1'), expression, r, head)
    return sym.POST + text if text else ''


# The operations whose result is a body or a 2D shape of the model they are made for: with the symmetry on they are given their images too (`path_extrude(circle, curve)` is one
# tube; its images are the others)
_IMAGED_GROUPS = ('Grow and hollow', 'Texturing', 'Round and bevel', 'Moving', 'Bend and twist', 'Repeating', 'Extruding', 'Combining')


def _operation_images(r):
    ''' The images of what an operation made with the symmetry on: `x_images = symmetry_images(x, symmetry, distinct=True)` -- the images that are not the model itself or another
        image (they cannot be told here, where the models are only names: the run tells them).  Not for what is made of the images of a model (they are the images already), nor
        for what is not a body or a 2D shape (a field, a surface) '''
    from fieldev import symmetry_creation as sym
    for n, group, _template, _other in OPERATIONS:
        if n == r['name']:
            if group not in _IMAGED_GROUPS or n == 'instance':
                return ''
            break
    else:
        return ''
    # (what is selected: the first model and the others -- a path_extrude is made of a 2D shape and a curve, whichever was selected first)
    models = [dict(r.get('body_info') or {}, name=r.get('body') or '')] + list(_others(r))
    if not any(m.get('type') in ('solid', 'profile') for m in models) or any(m.get('symmetry_image') for m in models):
        return ''
    return sym.POST + sym.images_line(r.get('var') or (r['name'] + '_1'), r['symmetry']['var'], ', distinct=True')


def call(request):
    ''' The text of the call a menu entry writes, complete and laid out (fieldev.completion: what the call needs and was not given is a
        placeholder, every other argument is written with its default, one argument to a line when it does not fit).  `request` is JSON:
        {kind: 'primitive' | 'operation', name, x, y, z (the place), scale (mm spanned by about a hundred pixels there), body, other (names
        or expressions of the models), var (the name the model will get), indent (how far the statement is indented) } '''
    r = json.loads(request) if isinstance(request, str) else request
    if r.get('kind') == 'python':
        # (a picture to trace, from the Character menu: the name is `reference_image|<plane>|<file>`, the call is written at the insertion point)
        if r['name'].startswith('reference_image|'):
            return _reference_text(r)
        # (the export of a model for a game engine, from its Export menu: the name is `export_game|<entry>|<model>`)
        if r['name'].startswith('export_game|'):
            return _export_text(r)
        # (a block of plain Python: its code as it is -- no model is made of it)
        for n, _label, _doc, code in PYTHON:
            if n == r['name']:
                return code
        raise ValueError(tr('the Python menu has no block called %s') % r['name'])
    if r.get('kind') == 'primitive':
        # (a primitive of the user's own: the statements it is made of and its model, written again with names the script has not got)
        from fieldev import user_primitives
        mine = user_primitives.find(r['name'])
        if mine is not None:
            return user_primitives.insert_text(mine, r.get('var') or (r['name'] + '_1'), r.get('source') or '')
    text = _call(r)
    head, marker, expression = text.rpartition(PRELUDE)
    from fieldev import completion
    indent = int(r.get('indent', 0))
    column = indent + len(r.get('var') or (r['name'] + '_1')) + 3          # (the statement is `var = call`)
    if _makes_up_nothing(r):
        # (an entry that had no model to build from was written from its template: it keeps the models and drops what the template built)
        expression = completion.without_made_up_values(expression, structure=bool(r.get('_templated')))
    expression = completion.complete_call(expression, column, indent)
    return head + marker + expression + _images_after(r, head, expression)


KEEPS_ITS_TEMPLATE = ('extrude', 'with_materials')

# (the shapes of the first groups are made where the user clicks, as big as the view shows: the place and the size are what the click says.
# Everything else a menu writes is made of models and calls: the numbers in them are for the user to say)
_PLACED_GROUPS = ('1D', '3D', '2D', 'Points', 'Surfaces', 'Fields', 'Symmetry', 'Character', 'Game')


def _reference_text(r):
    ''' The call that puts a picture behind the model to trace it: `reference_image("file", plane="front", height=...)`.  `name` is `reference_image|<plane>|<file>`; the picture is as
        tall as about six hundred pixels of the view show, a round number (it is made to the size of the character in the script: change `height`) '''
    _, plane, path = r['name'].split('|', 2)
    if plane not in ('front', 'back', 'right', 'left', 'top', 'bottom'):
        raise ValueError(tr('a reference image lies in the front, back, right, left, top or bottom plane, not %s') % plane)
    quoted = '"' + path.replace('\\', '/').replace('"', '\\"') + '"'
    size = _nice(float(r.get('scale', 10.0)) * 6.0)
    # (a picture of the sides stands on the ground, like the character: its middle is half its height up; a top or a bottom picture is round the origin)
    middle = _num(size / 2.0) if plane in ('front', 'back', 'right', 'left') else '0'
    # (the middle of the picture is a point with a gizmo, the picture's handle: drag the point to move the picture, scale its ring to make it larger)
    name = r.get('var') or 'reference_image_1'
    at = name + '_at'
    return ('%s = point(0, 0, %s)\n%s = gizmo(\n    %s,\n    move=(var(0), var(0), var(0)),\n    rotate=(var(0), var(0), var(0)),\n    scale=(var(1), var(1), var(1)),\n)\n%s\n'
            '%s = reference_image(%s, plane="%s", height=%s, center=%s, opacity=0.5)'
            % (at, middle, at, at, at, name, quoted, plane, _num(size), at))


def _makes_up_nothing(r):
    ''' Whether the entry writes no number or text of its own: every operation (an extrusion keeps the length it writes) '''
    if r['kind'] == 'operation':
        return r['name'] not in KEEPS_ITS_TEMPLATE
    if r['kind'] == 'primitive':
        for n, group, _ in PRIMITIVES:
            if n == r['name']:
                return group not in _PLACED_GROUPS
    return False


def _call(r):
    kind, name = r['kind'], r['name']
    values = _apply_params(name, _values(r))
    others = _others(r)
    selected = ([dict(r.get('body_info') or {}, name=r['body'])] if r.get('body') else []) + list(others)
    if kind == 'operation' and not _selection_fits(
            kind, name, ([r['body_info']] if r.get('body') and r.get('body_info') else []) + list(others)):
        # (the menu greys the entry out for such a selection, so this is not reached from it)
        raise ValueError('%s does not take what is selected' % name)
    if kind == 'primitive' and r.get('check') and not _primitive_fits(name, selected):
        # (asked whether the entry is valid for this selection, by a menu on a model: the entry is made of what is selected or has a use for it, or it is not valid)
        raise ValueError('%s does not fit what is selected' % name)
    if kind == 'primitive' and name in FROM_SELECTION and selected:
        built = _from_selection(name, selected, values)
        if built:
            return built
    if kind == 'operation' and values['body'] and (r.get('others') is not None or r.get('body_info')):
        built = _build_operation(name, values, others)
        if built:
            return built
    if kind == 'primitive' and r.get('points') and name in ('profile', 'polyline', 'spline', 'armature'):
        r['_templated'] = True
        return _placed_template(name, r).format(**values)
    if kind == 'primitive' and name == 'symmetry_planes':
        r['_templated'] = True
        return _symmetry_template(r, values)
    if kind == 'primitive' and r.get('plane') and name in ('profile', 'polyline', 'spline'):
        r['_templated'] = True
        return _plane_template(name, r).format(**values)
    if kind == 'primitive':
        for n, _, template in PRIMITIVES:
            if n == name:
                r['_templated'] = True
                if name in ('profile', 'polyline', 'spline') and (r.get('symmetry') or {}).get('elements'):
                    return _default_stroke_template(name, values, r).format(**values)
                return template.format(**values)
    elif kind == 'operation':
        for n, _, template, _ in OPERATIONS:
            if n == name:
                # (nothing to work on, or no second model: a placeholder stands there -- the run stops before the statement until a
                # model is put in its place)
                if not values['body']:
                    values = dict(values, body='...')
                if '{other}' in template and not values['other']:
                    values = dict(values, other='...')
                # (written from its template with no model to build it of: what the template made up -- a list, a call -- is for the user to say.  With the model it is made of, the
                # list of models (`character([arm, leg])`) is what the entry is)
                r['_templated'] = not r.get('body')
                return template.format(**values)
    for b in _blocks():                 # (a custom block: its call, with its other arguments left to their defaults)
        if b['name'] == name and kind == 'primitive' and b['primitive']:
            return name + '()'
        if b['name'] == name and kind == 'operation' and b['operation']:
            return '%s(%s)' % (name, values['body'] or '...')
    raise ValueError(tr('the menu has no %s called %s') % (kind, name))
