'''
The units of what is made for a game: one number of a level, a terrain, a prop or a kit is a metre.

`export_mesh` starts from millimetres.  The helpers that write game files (`export_terrain_chunks`, `export_scatter`, `Kit.export`) tell it that one number is a metre
(`model_unit="m"`), and -- in a file that has no unit of its own (.obj .stl .ply .off) -- that the file is in metres too, so the numbers of the model are the numbers of the file.
Anything can be given instead: `export_scatter(forest, "out/", model_unit="cm")`.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
'''

__all__ = []


def export_options(ext, options):
    ''' The options of an `export_mesh` call, with the unit of a game model set unless they say otherwise '''
    out = dict(options)
    unit = out.setdefault('model_unit', 'm')
    if str(ext).lower().lstrip('.') in ('stl', 'obj', 'ply', 'off') and unit in ('mm', 'cm', 'm', 'in'):
        out.setdefault('units', unit)
    return out
