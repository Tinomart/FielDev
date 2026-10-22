# Fields everywhere: wherever a number goes, a field goes.
#
# A field is a number at every point of space: a distance, a ramp, noise, a falloff from a point.  Every function of
# the library that takes a size, a thickness, a radius or a spacing takes a field in its place, and evaluates it where it
# needs it (nothing is sampled onto a grid).  Three bodies here, side by side, each driven by a field:
#
#   1. a plate grown by an amount that is 4 mm near an anchor point and 0.3 mm far from it   (offset)
#   2. a cylinder and a block joined by a blend that is sharp at one end and 8 mm round at the other   (smooth_union)
#   3. a dimpled block smoothed by 0.3 mm at one end and 6 mm at the other   (smooth)
#
# Change a number, or swap a field for another one (noise_field(...), distance_to_plane(...),
# depth_below(...) ...), and the body follows.
#
# To look at a field itself, turn on its eye in the model tree (swell, blend, softness): it becomes an icon in the viewport with
# its name over it, and a click on the icon opens the field viewer -- a disc through the field with a radius slider.
from fieldes import *

view.set_bounds([-10, -10, -10], [225, 55, 45], auto_scale=True)
view.set_resolution(4)
view.set_quality(8)

# 1. A plate, grown more near the anchor.  The anchor is a point: anything that wants a coordinate takes it.
plate = box((0, 0, 0), (60, 40, 6))
anchor = point(52, 8, 6)
anchor = gizmo(
    anchor,
    move=(var(0), var(-2.37372), var(0)),
    rotate=(var(0), var(0), var(0)),
    scale=(var(1), var(1), var(1)),
)
anchor
swell = ramp(distance_to_point(anchor), (0, 60), (4.0, 0.3))
grown = offset(plate, swell)
grown

# 2. The blend radius of a smooth union as a field of x: 0.5 mm at the left, 8 mm at the right.
post = cylinder(10, 30, (105, 20, 0))
block = box((80, 8, 0), (140, 32, 10))
blend = ramp(x_field(), (80, 140), (0.5, 8.0))
softness = ramp(x_field(), (160, 220), (0.3, 6.0))
joined = smooth_union(post, block, blend)
joined = handles(joined, [var(105.0), var(20.0), var(10.0), var(30.0), var(0.0), var(110.0), var(30.0), var(20.0), var(12.0), var(5.0), var(5.0), var(80.0), var(10.0)])
joined = gizmo(
    joined,
    move=(var(0), var(0), var(0)),
    rotate=(var(0), var(0), var(0)),
    scale=(var(1), var(1), var(1)),
)
joined
# 3. Smoothing whose radius is a field.  The dimples at the left keep their sharp rims; to the right they are washed out
#    more and more, until they are shallow hollows.
core = box((160, 0, 0), (220, 40, 30))
dimpled = difference(core, repeat(sphere(3.5, (0, 0, 30)), (9, 9, 0)))
soft = smooth(dimpled, softness, 2)
soft = gizmo(
    soft,
    move=(var(0), var(0), var(0)),
    rotate=(var(0), var(0), var(0)),
    scale=(var(1), var(1), var(1)),
)
soft

