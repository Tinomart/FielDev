# Sample custom blocks.  Every function in a file of this folder (whose name does not start with an underscore) is a block:
# it is there in every script, like a function of the library, with its call tip, completion and menus.  Write one with a
# few lines, save the file, and use it:
#
#     wall = windows(box((0, 0, 0), (60, 40, 6)), 2.5, 10)
#
# The whole library is at hand in a block file (no imports).  The first line of the docstring is what the call tip says.
# A block whose first argument is a model and has defaults for the others is in the right-click menu under
# "Operations > Custom blocks"; a block that needs no argument is under "Parametric shapes > New custom block".


def windows(body, radius=2.0, spacing=10.0):
    ''' Cuts a grid of round windows right through a wall, along z '''
    holes = repeat(cylinder(radius, 100000, (0, 0, -50000)), (spacing, spacing, 0))
    return difference(body, holes)


def rounded(body, radius=1.0):
    ''' Smooths every edge and bump of a body that is smaller than the radius '''
    return smooth(body, radius, 2)


def hollow(body, wall=2.0):
    ''' A body hollowed to a wall of the given thickness, empty inside '''
    return shell_inside(body, wall)


def stairs(steps=6, width=30.0, rise=3.0, run=5.0):
    ''' A flight of steps: each one a rise higher and a run further than the one before '''
    flight = box((0, 0, 0), (run, width, rise))
    for k in range(1, steps):
        flight = union(flight, box((k * run, 0, 0), ((k + 1) * run, width, (k + 1) * rise)))
    return flight
