'''
Materials: a name, a colour, how it shines -- and where on the model it applies, as a field.

    skin = material("skin", color=(0.9, 0.72, 0.6), roughness=0.7)
    metal = material("metal", color="#9aa0aa", metallic=1.0, roughness=0.3, where=box((-40, -30, 100), (40, 30, 150)))
    export_mesh(character, "hero.glb", materials=[skin, metal])

The materials of an export are LAYERS, painted in the order they are listed: each triangle takes the last material whose `where` is negative at the middle of the
triangle (inside the body or the field it names), so a material without a `where` -- the base -- goes first.  A triangle no material covers has none.  OBJ files
get a .mtl file next to them (`usemtl` for each group of triangles), glTF files a material for each and a primitive of the mesh for each.

`where` is any field: a body (the material is on what is inside it), or a field -- `100 - z_field()` is negative above z = 100.  The edge between two materials
runs along the triangles of the mesh: as fine as the resolution of the export.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
'''
from fieldes.shape import Shape

__all__ = ['material', 'Material']


class Material:
    ''' A material for `export_mesh(..., materials=[...])`: see `material` '''

    def __init__(self, name, color, roughness, metallic, emissive, where):
        self.name = name
        self.color = color
        self.roughness = roughness
        self.metallic = metallic
        self.emissive = emissive
        self.where = where

    def __repr__(self):
        return 'material(%r, color=(%.3g, %.3g, %.3g), roughness=%g, metallic=%g%s)' % (
            (self.name,) + tuple(self.color) + (self.roughness, self.metallic, ', where=...' if self.where is not None else ''))


def _rgb(value, what):
    ''' (r, g, b) as three numbers from 0 to 1, from those or from a text like "#c8a064" '''
    if isinstance(value, str):
        text = value.strip().lstrip('#')
        if len(text) == 3:
            text = ''.join(c * 2 for c in text)
        if len(text) != 6:
            raise ValueError('%s: a colour is (r, g, b) from 0 to 1 or "#rrggbb", not %r' % (what, value))
        try:
            return tuple(int(text[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
        except ValueError:
            raise ValueError('%s: a colour is (r, g, b) from 0 to 1 or "#rrggbb", not %r' % (what, value))
    try:
        r, g, b = (float(c) for c in value)
    except (TypeError, ValueError):
        raise ValueError('%s: a colour is (r, g, b) from 0 to 1 or "#rrggbb", not %r' % (what, value))
    return tuple(min(1.0, max(0.0, c)) for c in (r, g, b))


def material(name, color=(0.8, 0.8, 0.8), roughness=0.5, metallic=0.0, emissive=None, where=None):
    ''' A material of a mesh export (`export_mesh(part, "hero.glb", materials=[...])`).

        name       what the file calls it (letters, digits, - and _)
        color      (r, g, b) from 0 to 1, or "#rrggbb"
        roughness  0 (a mirror) to 1 (chalk)
        metallic   0 (a dielectric) to 1 (a metal)
        emissive   (r, g, b) or "#rrggbb" for a surface that glows, or None
        where      a body or a field: the material is on the triangles whose middle is inside it (where its value is negative).  None: everywhere

        The materials of an export are layers: each triangle takes the LAST one that covers it, so the base material (no `where`) goes first. '''
    name = ''.join(c if (c.isalnum() or c in '_-') else '_' for c in str(name or ''))
    if not name:
        raise ValueError('material: a name is needed')
    for what, v in (('roughness', roughness), ('metallic', metallic)):
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not 0.0 <= v <= 1.0:
            raise ValueError('material %s: %s is a number from 0 to 1, not %r' % (name, what, v))
    if where is not None and not isinstance(where, Shape):
        raise TypeError('material %s: where is a body or a field, not %r' % (name, type(where).__name__))
    return Material(name, _rgb(color, 'material %s' % name), float(roughness), float(metallic),
                    None if emissive is None else _rgb(emissive, 'material %s' % name), where)
