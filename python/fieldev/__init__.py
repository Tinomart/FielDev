'''
FielDev: field-driven design.

A script starts with

    from fieldev import *

which brings in everything the library offers (shapes, CSG, transforms, mesh
import and export, fields and regressions, points, profiles and sweeps, symmetry,
textures, ...) and `view`, the viewport settings of the application
(view.set_bounds, view.set_resolution, view.set_quality), and `app`, the inputs of a script that is run as an app
(app.number, app.file, app.save_as, ...; see fieldev.app).

The kernel this builds on is libfive by Matt Keeter (Mozilla Public License 2.0).
'''

import fieldev.shape
import fieldev.stdlib as _stdlib
from fieldev.stdlib import *
from fieldev.shape import Shape
from fieldev import view
from fieldev import app

__all__ = [n for n in dir(_stdlib) if not n.startswith('_')] + ['Shape', 'view', 'app']
