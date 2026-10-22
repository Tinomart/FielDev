'''
Materials: a name, a colour, how it shines, how it is lit -- and where on the model it applies, as a field.

    skin = material("skin", color=(0.9, 0.72, 0.6), roughness=0.7)
    metal = material("metal", color="#9aa0aa", metallic=1.0, roughness=0.3, where=box((-40, -30, 100), (40, 30, 150)))
    glass = material("glass", color=(0.9, 0.95, 1.0), roughness=0.05, transmission=1.0, ior=1.5)
    gold = material_preset("gold")
    export_mesh(character, "hero.glb", materials=[skin, metal])

The materials of an export are LAYERS, painted in the order they are listed: each triangle takes the last material whose `where` is negative at the middle of the
triangle (inside the body or the field it names), so a material without a `where` -- the base -- goes first.  A triangle no material covers has none.  OBJ files
get a .mtl file next to them (`usemtl` for each group of triangles), glTF files a material for each and a primitive of the mesh for each.

`where` is any field: a body (the material is on what is inside it), or a field -- `100 - z_field()` is negative above z = 100.  The edge between two materials
runs along the triangles of the mesh: as fine as the resolution of the export -- unless the textures are baked (`textures=bake(...)` of export_mesh), which
asks the field at every texel of the texture: the edge is as fine as the texture is.

A colour, the roughness, the metalness, the glow and the opacity can be FIELDS instead of numbers -- a pattern, noise, a gradient -- when the textures are baked:

    wood = material("wood", color=(0.55 + 0.1 * noise, 0.35 + 0.1 * noise, 0.2), roughness=0.4 + 0.3 * noise)

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
'''
from fieldev.shape import Shape

__all__ = ['material', 'material_preset', 'material_presets', 'Material']


class Material:
    ''' A material for `export_mesh(..., materials=[...])`: see `material` '''

    def __init__(self, name, color, roughness, metallic, emissive, where, texture=None, opacity=1.0, alpha_mode=None, double_sided=False, ior=None, transmission=0.0,
                 clearcoat=0.0, clearcoat_roughness=0.0, sheen=None, emissive_strength=1.0, normal_texture=None, orm_texture=None, emissive_texture=None, normal_scale=1.0):
        self.name = name
        self.color = color
        self.roughness = roughness
        self.metallic = metallic
        self.emissive = emissive
        self.where = where
        self.texture = texture
        self.opacity = opacity
        self.alpha_mode = alpha_mode
        self.double_sided = double_sided
        self.ior = ior
        self.transmission = transmission
        self.clearcoat = clearcoat
        self.clearcoat_roughness = clearcoat_roughness
        self.sheen = sheen
        self.emissive_strength = emissive_strength
        self.normal_texture = normal_texture
        self.orm_texture = orm_texture
        self.emissive_texture = emissive_texture
        self.normal_scale = normal_scale

    def is_procedural(self):
        ''' True when a colour, the roughness, the metalness, the glow or the opacity is a field: the material can only be written with baked textures '''
        values = list(self.color) + [self.roughness, self.metallic, self.opacity] + (list(self.emissive) if self.emissive else [])
        return any(isinstance(v, Shape) for v in values)

    def blend_mode(self):
        ''' "OPAQUE", "MASK" or "BLEND": the alpha mode asked for, else BLEND when the material is see-through, else OPAQUE '''
        if self.alpha_mode:
            return self.alpha_mode
        return 'BLEND' if isinstance(self.opacity, Shape) or self.opacity < 1.0 else 'OPAQUE'

    def __repr__(self):
        def show(v):
            return '<field>' if isinstance(v, Shape) else '%.3g' % v
        return 'material(%r, color=(%s), roughness=%s, metallic=%s%s)' % (
            self.name, ', '.join(show(c) for c in self.color), show(self.roughness), show(self.metallic), ', where=...' if self.where is not None else '')


def _channel(v, what):
    if isinstance(v, Shape):
        return v
    try:
        return min(1.0, max(0.0, float(v)))
    except (TypeError, ValueError):
        raise ValueError('%s: a colour channel is a number from 0 to 1 or a field, not %r' % (what, v))


def _rgb(value, what):
    ''' (r, g, b), each a number from 0 to 1 or a field, from those or from a text like "#c8a064" '''
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
        r, g, b = tuple(value)
    except (TypeError, ValueError):
        raise ValueError('%s: a colour is (r, g, b) from 0 to 1 or "#rrggbb", not %r' % (what, value))
    return tuple(_channel(c, what) for c in (r, g, b))


def _unit(v, name, what):
    ''' A number from 0 to 1, or a field '''
    if isinstance(v, Shape):
        return v
    if not isinstance(v, (int, float)) or isinstance(v, bool) or not 0.0 <= v <= 1.0:
        raise ValueError('material %s: %s is a number from 0 to 1 (or a field), not %r' % (name, what, v))
    return float(v)


def _image(value, name, what):
    if value is not None and (not isinstance(value, str) or not value.strip() or any(c in value for c in ' \t\r\n')):
        raise ValueError('material %s: %s is the name of an image file without spaces ("skin.png"), not %r' % (name, what, value))
    return value


def material(name, color=(0.8, 0.8, 0.8), roughness=0.5, metallic=0.0, emissive=None, where=None, texture=None, opacity=1.0, alpha_mode=None, double_sided=False,
             ior=None, transmission=0.0, clearcoat=0.0, clearcoat_roughness=0.0, sheen=None, emissive_strength=1.0, normal_texture=None, orm_texture=None,
             emissive_texture=None, normal_scale=1.0):
    ''' A material of a mesh export (`export_mesh(part, "hero.glb", materials=[...])`).  The physically based one glTF has (metallic and roughness).

        name        what the file calls it (letters, digits, - and _)
        color       (r, g, b) from 0 to 1, or "#rrggbb"; each channel can be a field (baked into the textures)
        roughness   0 (a mirror) to 1 (chalk); a number or a field
        metallic    0 (a dielectric) to 1 (a metal); a number or a field
        emissive    (r, g, b) or "#rrggbb" for a surface that glows, or None
        emissive_strength   how many times brighter than 1 the glow is (a lamp): 1 by default
        where       a body or a field: the material is on the triangles whose middle is inside it (where its value is negative); with baked textures, on the texels.  None: everywhere
        opacity     1 (solid) to 0 (invisible); a number or a field.  Below 1 the material is blended
        alpha_mode  "OPAQUE", "MASK" (a cut-out: leaves, a fence) or "BLEND"; None: BLEND below an opacity of 1, else OPAQUE
        double_sided  both sides of a triangle are drawn and lit (a leaf, a flag, a sheet)
        ior         the index of refraction (1.5 is glass); None: glTF's 1.5
        transmission  1 for glass that light passes through, 0 for a solid
        clearcoat   0 to 1: a glossy layer on top (car paint, varnish); clearcoat_roughness: how rough that layer is
        sheen       (r, g, b) of the soft glow at grazing angles of cloth and velvet, or None
        normal_scale  how strong the baked or given normal map is: 1
        texture, normal_texture, orm_texture, emissive_texture   the file names of images you made yourself ("skin.png"): the colour, the normal map, the packed
                    occlusion (red) / roughness (green) / metallic (blue) map, and the glow.  Mapped with the UVs of the export (`export_mesh(..., uvs=...)`); the
                    images are not copied or checked: they are the names the file says.  `export_mesh(..., textures=bake(...))` makes them from the fields instead

        The materials of an export are layers: each triangle takes the LAST one that covers it, so the base material (no `where`) goes first. '''
    name = ''.join(c if (c.isalnum() or c in '_-') else '_' for c in str(name or ''))
    if not name:
        raise ValueError('material: a name is needed')
    if where is not None and not isinstance(where, Shape):
        raise TypeError('material %s: where is a body or a field, not %r' % (name, type(where).__name__))
    if alpha_mode is not None:
        alpha_mode = str(alpha_mode).strip().upper()
        if alpha_mode not in ('OPAQUE', 'MASK', 'BLEND'):
            raise ValueError('material %s: alpha_mode is "OPAQUE", "MASK" or "BLEND", not %r' % (name, alpha_mode))
    if ior is not None and (not isinstance(ior, (int, float)) or isinstance(ior, bool) or not 1.0 <= ior <= 4.0):
        raise ValueError('material %s: ior is a number from 1 to 4 (1.5 is glass, 1.33 water), not %r' % (name, ior))
    for what, v in (('transmission', transmission), ('clearcoat', clearcoat), ('clearcoat_roughness', clearcoat_roughness)):
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not 0.0 <= v <= 1.0:
            raise ValueError('material %s: %s is a number from 0 to 1, not %r' % (name, what, v))
    if not isinstance(emissive_strength, (int, float)) or isinstance(emissive_strength, bool) or not 0.0 <= emissive_strength <= 1000.0:
        raise ValueError('material %s: emissive_strength is a number from 0 to 1000, not %r' % (name, emissive_strength))
    if not isinstance(normal_scale, (int, float)) or isinstance(normal_scale, bool) or not 0.0 <= normal_scale <= 10.0:
        raise ValueError('material %s: normal_scale is a number from 0 to 10, not %r' % (name, normal_scale))
    return Material(name, _rgb(color, 'material %s' % name), _unit(roughness, name, 'roughness'), _unit(metallic, name, 'metallic'),
                    None if emissive is None else _rgb(emissive, 'material %s' % name), where, _image(texture, name, 'texture'),
                    _unit(opacity, name, 'opacity'), alpha_mode, bool(double_sided), None if ior is None else float(ior), float(transmission),
                    float(clearcoat), float(clearcoat_roughness), None if sheen is None else _rgb(sheen, 'material %s' % name), float(emissive_strength),
                    _image(normal_texture, name, 'normal_texture'), _image(orm_texture, name, 'orm_texture'), _image(emissive_texture, name, 'emissive_texture'),
                    float(normal_scale))


# What the common materials look like: the colour (linear, as glTF has it; for the metals it is the reflectance at normal incidence), the roughness, the metalness, and the rest
_PRESETS = {
    'gold': dict(color=(1.000, 0.766, 0.336), roughness=0.25, metallic=1.0),
    'silver': dict(color=(0.972, 0.960, 0.915), roughness=0.2, metallic=1.0),
    'copper': dict(color=(0.955, 0.638, 0.538), roughness=0.3, metallic=1.0),
    'brass': dict(color=(0.910, 0.778, 0.423), roughness=0.3, metallic=1.0),
    'iron': dict(color=(0.560, 0.570, 0.580), roughness=0.5, metallic=1.0),
    'steel': dict(color=(0.650, 0.660, 0.670), roughness=0.35, metallic=1.0),
    'aluminium': dict(color=(0.913, 0.922, 0.924), roughness=0.35, metallic=1.0),
    'chrome': dict(color=(0.550, 0.556, 0.554), roughness=0.05, metallic=1.0),
    'plastic': dict(color=(0.80, 0.10, 0.10), roughness=0.35, metallic=0.0, clearcoat=0.3),
    'rubber': dict(color=(0.04, 0.04, 0.04), roughness=0.9, metallic=0.0),
    'wood': dict(color=(0.45, 0.28, 0.14), roughness=0.65, metallic=0.0),
    'stone': dict(color=(0.42, 0.41, 0.39), roughness=0.85, metallic=0.0),
    'concrete': dict(color=(0.52, 0.52, 0.50), roughness=0.9, metallic=0.0),
    'brick': dict(color=(0.45, 0.17, 0.12), roughness=0.85, metallic=0.0),
    'ceramic': dict(color=(0.85, 0.85, 0.82), roughness=0.15, metallic=0.0, clearcoat=0.6, clearcoat_roughness=0.05),
    'skin': dict(color=(0.80, 0.55, 0.43), roughness=0.55, metallic=0.0, sheen=(0.15, 0.08, 0.06)),
    'leather': dict(color=(0.30, 0.17, 0.10), roughness=0.6, metallic=0.0, clearcoat=0.15, clearcoat_roughness=0.4),
    'cloth': dict(color=(0.35, 0.40, 0.55), roughness=0.95, metallic=0.0, sheen=(0.25, 0.25, 0.30), double_sided=True),
    'paper': dict(color=(0.90, 0.88, 0.82), roughness=0.9, metallic=0.0, double_sided=True),
    'bone': dict(color=(0.80, 0.76, 0.66), roughness=0.55, metallic=0.0),
    'glass': dict(color=(0.95, 0.98, 1.0), roughness=0.03, metallic=0.0, transmission=1.0, ior=1.5),
    'water': dict(color=(0.60, 0.80, 0.90), roughness=0.02, metallic=0.0, transmission=0.9, ior=1.33),
    'paint': dict(color=(0.20, 0.35, 0.70), roughness=0.4, metallic=0.0, clearcoat=0.8, clearcoat_roughness=0.08),
    'glow': dict(color=(0.05, 0.05, 0.05), roughness=0.5, metallic=0.0, emissive=(1.0, 0.85, 0.5), emissive_strength=4.0),
}


def material_presets():
    ''' The names `material_preset` knows '''
    return sorted(_PRESETS)


def material_preset(kind, name=None, **options):
    ''' A material that looks like a common thing: "gold", "silver", "copper", "brass", "iron", "steel", "aluminium", "chrome", "plastic", "rubber", "wood", "stone", "concrete",
        "brick", "ceramic", "skin", "leather", "cloth", "paper", "bone", "glass", "water", "paint", "glow" (see `material_presets()`).  `name` is what the file calls it (the
        kind by default); the other options are those of `material` and replace the preset's: `material_preset("plastic", color="#2060c0", where=body)` '''
    key = str(kind).strip().lower()
    if key not in _PRESETS:
        raise ValueError('material_preset: %r is not one of %s' % (kind, ', '.join(material_presets())))
    values = dict(_PRESETS[key])
    values.update(options)
    return material(name or key, **values)
