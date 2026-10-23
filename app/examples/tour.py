# The guided tour's model
from fieldev import *

view.set_bounds([-35, -25, -8], [35, 25, 30], auto_scale=True)
view.set_resolution(4)
view.set_quality(8)

tile = box((-30, -20, 0), (30, 20, var(6)))
doorway = cylinder(var(5), 40, (0, 0, -10))
wall = difference(tile, doorway)
wall
