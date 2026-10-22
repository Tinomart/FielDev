'''
glTF 2.0 files (.glb, .gltf): the writer behind export_mesh for them.  Metres, Y up: the numbers (millimetres, Z up) are turned into them as (x, z, -y) / 1000.

What a file can hold, all of it from the model:

    the mesh              POSITION, NORMAL (the exact normals of the field), TANGENT (for the normal map), COLOR_0, TEXCOORD_0 and TEXCOORD_1 (v down, as glTF has it)
    the materials         the metallic-roughness model, the colour / normal / occlusion-roughness-metalness / emissive pictures (a .glb has the baked ones inside), alpha mode,
                          double sided, and the extensions KHR_materials_emissive_strength, _transmission, _ior, _clearcoat and _sheen
    a skeleton            the joints as nodes, the skin, JOINTS_0 / WEIGHTS_0 (and _1: up to eight joints a vertex)

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import base64
import json
import os
import struct
from array import array

__all__ = ['write_glb', 'write_gltf', 'gltf_document']

_FLOAT, _UBYTE, _USHORT, _UINT = 5126, 5121, 5123, 5125
_ARRAY, _ELEMENTS = 34962, 34963


def _clean_name(name):
    name = ''.join(c if (c.isalnum() or c in '_-') else '_' for c in str(name or 'fieldev'))
    return name or 'mesh'


def _little(values):
    ''' The bytes of an array of numbers, little endian '''
    values = array(values.typecode, values)
    if struct.pack('=I', 1) != struct.pack('<I', 1):
        values.byteswap()
    return values.tobytes()


def _point(p):
    ''' A place of the model (mm, Z up) as glTF has it: metres, Y up (x, z, -y) '''
    return (p[0] * 0.001, p[2] * 0.001, -p[1] * 0.001)


def _turn(v):
    ''' A direction of the model as glTF has it: (x, z, -y) '''
    return (v[0], v[2], -v[1])


class _Buffer:
    ''' The one binary buffer of the file, and the buffer views and accessors that cut it up '''

    def __init__(self):
        self.data = bytearray()
        self.views = []
        self.accessors = []

    def view(self, payload, target=None):
        self.data += b'\0' * (-len(self.data) % 4)
        entry = {'buffer': 0, 'byteOffset': len(self.data), 'byteLength': len(payload)}
        if target is not None:
            entry['target'] = target
        self.data += payload
        self.views.append(entry)
        return len(self.views) - 1

    def accessor(self, values, component, kind, count, target=None, bounds=None, normalized=False):
        entry = {'bufferView': self.view(_little(values), target), 'componentType': component, 'count': count, 'type': kind}
        if bounds is not None:
            entry['min'], entry['max'] = bounds
        if normalized:
            entry['normalized'] = True
        self.accessors.append(entry)
        return len(self.accessors) - 1


def _by_material(tri, tri_material):
    ''' The triangles of each material: [(the number of the material, its triangles as flat corners)], in the order of the materials; the ones that no material covers
        (-1) first.  With no materials, all of them in one '''
    if tri_material is None:
        return [(-1, tri)]
    groups = {}
    for t in range(len(tri) // 3):
        groups.setdefault(tri_material[t], array('I')).extend(tri[3 * t:3 * t + 3])
    return [(k, groups[k]) for k in sorted(groups)]


def _materials_and_textures(materials, extra, embed, buf):
    ''' The glTF materials, images and textures.  `extra['baked']` is {the map: the file name} of the pictures baked for the export (their bytes are in `extra['images']`);
        a map that is baked replaces the number (or the field) of the material for that property '''
    baked = extra.get('baked') or {}
    images, textures, made = [], [], []
    texcoord = extra.get('texcoord', 0)

    def texture(name, data=None):
        ''' The index of the texture of an image: a file by its name (uri), or the baked picture inside the file '''
        for k, image in enumerate(images):
            if image['name'] == name:
                return k
        if data is not None and embed:
            images.append({'name': name, 'mimeType': 'image/png', 'bufferView': buf.view(data)})
        else:
            images.append({'name': name, 'uri': name})
        textures.append({'source': len(images) - 1, 'sampler': 0})
        return len(textures) - 1

    def baked_texture(kind):
        return texture(baked[kind], extra['images'].get(baked[kind])) if kind in baked else None

    for m in materials:
        pbr = {}
        color_index = baked_texture('color')
        user = m.texture
        if color_index is not None:
            pbr['baseColorFactor'] = [1.0, 1.0, 1.0, 1.0]
            pbr['baseColorTexture'] = {'index': color_index, 'texCoord': texcoord}
        else:
            alpha = 1.0 if hasattr(m.opacity, 'ptr') else m.opacity
            pbr['baseColorFactor'] = [m.color[0], m.color[1], m.color[2], alpha]
            if user:
                pbr['baseColorTexture'] = {'index': texture(user), 'texCoord': extra.get('texcoord', 0)}
        mr = 'orm' if 'orm' in baked else ('mr' if 'mr' in baked else None)
        if mr is not None:
            pbr['metallicFactor'], pbr['roughnessFactor'] = 1.0, 1.0
            pbr['metallicRoughnessTexture'] = {'index': baked_texture(mr), 'texCoord': texcoord}
        else:
            pbr['metallicFactor'], pbr['roughnessFactor'] = m.metallic, m.roughness
            if m.orm_texture:
                pbr['metallicRoughnessTexture'] = {'index': texture(m.orm_texture), 'texCoord': extra.get('texcoord', 0)}
        out = {'name': m.name, 'pbrMetallicRoughness': pbr}
        normal = baked_texture('normal')
        if normal is not None:
            out['normalTexture'] = {'index': normal, 'texCoord': texcoord, 'scale': m.normal_scale}
        elif m.normal_texture:
            out['normalTexture'] = {'index': texture(m.normal_texture), 'texCoord': extra.get('texcoord', 0), 'scale': m.normal_scale}
        occlusion = baked_texture('orm') if 'orm' in baked else baked_texture('occlusion')
        if occlusion is not None:
            out['occlusionTexture'] = {'index': occlusion, 'texCoord': texcoord}
        elif m.orm_texture:
            out['occlusionTexture'] = {'index': texture(m.orm_texture), 'texCoord': extra.get('texcoord', 0)}
        glow = baked_texture('emissive')
        if glow is not None:
            out['emissiveFactor'] = [1.0, 1.0, 1.0]
            out['emissiveTexture'] = {'index': glow, 'texCoord': texcoord}
        else:
            if m.emissive:
                out['emissiveFactor'] = list(m.emissive)
            if m.emissive_texture:
                out['emissiveFactor'] = out.get('emissiveFactor', [1.0, 1.0, 1.0])
                out['emissiveTexture'] = {'index': texture(m.emissive_texture), 'texCoord': extra.get('texcoord', 0)}
        mode = m.blend_mode()
        if mode != 'OPAQUE':
            out['alphaMode'] = mode
            if mode == 'MASK':
                out['alphaCutoff'] = 0.5
        if m.double_sided:
            out['doubleSided'] = True
        ext = {}
        if (m.emissive or glow is not None) and m.emissive_strength != 1.0:
            ext['KHR_materials_emissive_strength'] = {'emissiveStrength': m.emissive_strength}
        if m.transmission > 0.0:
            ext['KHR_materials_transmission'] = {'transmissionFactor': m.transmission}
        if m.ior is not None:
            ext['KHR_materials_ior'] = {'ior': m.ior}
        if m.clearcoat > 0.0:
            ext['KHR_materials_clearcoat'] = {'clearcoatFactor': m.clearcoat, 'clearcoatRoughnessFactor': m.clearcoat_roughness}
        if m.sheen is not None:
            ext['KHR_materials_sheen'] = {'sheenColorFactor': list(m.sheen), 'sheenRoughnessFactor': 0.5}
        if ext:
            out['extensions'] = ext
        made.append(out)
    return made, images, textures


def gltf_document(xyz, tri, name, materials=None, tri_material=None, colors=None, uvs=None, skin=None, extra=None, embed=True):
    ''' (the glTF document, its binary buffer).

        xyz, tri       the mesh (mm, Z up) as flat arrays
        materials      the list of materials (the baked pictures are wired to them), tri_material the number of the material of each triangle
        colors, uvs    COLOR_0, and TEXCOORD_0 (u, v of every vertex, v up)
        skin           (the joints, the joint numbers of every vertex, their weights, how many a vertex has: 4 or 8) or None
        extra          a dict: normals (3 floats a vertex), tangents (4), uvs2 (TEXCOORD_1), baked ({map: file name}), images ({file name: the bytes}), texcoord (the UV set of the
                       baked pictures)
        embed          the baked pictures go inside the buffer (a .glb); False: the file names are uris '''
    extra = extra or {}
    nv = len(xyz) // 3
    buf = _Buffer()
    pos = array('f')
    for i in range(0, len(xyz), 3):
        pos.extend(_point((xyz[i], xyz[i + 1], xyz[i + 2])))
    lo = [min(pos[i::3]) for i in range(3)] if len(pos) else [0.0] * 3
    hi = [max(pos[i::3]) for i in range(3)] if len(pos) else [0.0] * 3
    attributes = {'POSITION': buf.accessor(pos, _FLOAT, 'VEC3', nv, _ARRAY, (lo, hi))}
    normals = extra.get('normals')
    if normals is not None:
        turned = array('f')
        for i in range(0, len(normals), 3):
            turned.extend(_turn((normals[i], normals[i + 1], normals[i + 2])))
        attributes['NORMAL'] = buf.accessor(turned, _FLOAT, 'VEC3', nv, _ARRAY)
    tangents = extra.get('tangents')
    if tangents is not None:
        turned = array('f')
        for i in range(0, len(tangents), 4):
            turned.extend(_turn((tangents[i], tangents[i + 1], tangents[i + 2])) + (tangents[i + 3],))
        attributes['TANGENT'] = buf.accessor(turned, _FLOAT, 'VEC4', nv, _ARRAY)
    if colors is not None:
        attributes['COLOR_0'] = buf.accessor(array('f', colors), _FLOAT, 'VEC3', nv, _ARRAY)
    for key, set_uvs in (('TEXCOORD_0', uvs), ('TEXCOORD_1', extra.get('uvs2'))):
        if set_uvs is not None:
            flipped = array('f', set_uvs)
            flipped[1::2] = array('f', [1.0 - v for v in set_uvs[1::2]])          # (glTF has v down from the top of the image)
            attributes[key] = buf.accessor(flipped, _FLOAT, 'VEC2', nv, _ARRAY)
    if skin is not None:
        joints, ids, weights, influences = skin
        # (the joints a vertex has are in sets of four -- JOINTS_0 / WEIGHTS_0, then _1 -- and what a set has no joint for is 0: one to four joints are one set, five to eight two)
        for k in range((influences + 3) // 4):
            set_ids, set_weights = array('B', [0]) * (4 * nv), array('f', [0.0]) * (4 * nv)
            for c in range(4):
                slot = 4 * k + c
                if slot < influences:
                    set_ids[c::4] = ids[slot::influences]
                    set_weights[c::4] = weights[slot::influences]
            attributes['JOINTS_%d' % k] = buf.accessor(set_ids, _UBYTE, 'VEC4', nv, _ARRAY)
            attributes['WEIGHTS_%d' % k] = buf.accessor(set_weights, _FLOAT, 'VEC4', nv, _ARRAY)
    primitives = []
    for k, group in _by_material(tri, tri_material):
        primitive = {'attributes': dict(attributes), 'indices': buf.accessor(group, _UINT, 'SCALAR', len(group), _ELEMENTS), 'mode': 4}
        if k >= 0:
            primitive['material'] = k
        primitives.append(primitive)
    mesh = {'name': _clean_name(name), 'primitives': primitives}
    nodes = [{'mesh': 0, 'name': _clean_name(name)}]
    scene = [0]
    skins = None
    if skin is not None:
        # The joints are nodes with no turn, each a translation from its parent: the pose of the mesh is the bind pose, and the inverse bind matrix of a joint is the
        # translation back from where it is
        where = {j.name: _point(j.position) for j in joints}
        node_of = {j.name: k + 1 for k, j in enumerate(joints)}
        matrices = array('f')
        for j in joints:
            here = where[j.name]
            origin = where[j.parent] if j.parent is not None else (0.0, 0.0, 0.0)
            node = {'name': j.name, 'translation': [here[c] - origin[c] for c in range(3)]}
            children = [node_of[c.name] for c in joints if c.parent == j.name]
            if children:
                node['children'] = children
            nodes.append(node)
            matrices.extend((1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, -here[0], -here[1], -here[2], 1.0))
        root = next(k + 1 for k, j in enumerate(joints) if j.parent is None)
        nodes[0]['skin'] = 0
        scene.append(root)
        skins = [{'inverseBindMatrices': buf.accessor(matrices, _FLOAT, 'MAT4', len(joints)), 'joints': list(range(1, len(joints) + 1)), 'skeleton': root}]
    doc = {
        'asset': {'version': '2.0', 'generator': 'FielDev'},
        'scene': 0,
        'scenes': [{'nodes': scene}],
        'nodes': nodes,
        'meshes': [mesh],
    }
    if skins:
        doc['skins'] = skins
    used = []
    if materials:
        made, images, textures = _materials_and_textures(materials, extra, embed, buf)
        doc['materials'] = made
        if textures:
            doc['images'] = [{k: v for k, v in image.items() if k != 'name'} for image in images]
            doc['textures'] = textures
            doc['samplers'] = [{'magFilter': 9729, 'minFilter': 9987, 'wrapS': 10497, 'wrapT': 10497}]
        for m in made:
            for key in m.get('extensions', {}):
                if key not in used:
                    used.append(key)
    if used:
        doc['extensionsUsed'] = used
    doc['accessors'] = buf.accessors
    doc['bufferViews'] = buf.views
    doc['buffers'] = [{'byteLength': len(buf.data)}]
    return doc, bytes(buf.data)


def write_glb(path, xyz, tri, name='fieldev', materials=None, tri_material=None, colors=None, uvs=None, skin=None, extra=None):
    doc, binary = gltf_document(xyz, tri, name, materials, tri_material, colors, uvs, skin, extra, True)
    text = json.dumps(doc, separators=(',', ':')).encode('utf-8')
    text += b' ' * (-len(text) % 4)
    binary += b'\0' * (-len(binary) % 4)
    total = 12 + 8 + len(text) + 8 + len(binary)
    with open(path, 'wb') as f:
        f.write(struct.pack('<4sII', b'glTF', 2, total))
        f.write(struct.pack('<I4s', len(text), b'JSON'))
        f.write(text)
        f.write(struct.pack('<I4s', len(binary), b'BIN\0'))
        f.write(binary)


def write_gltf(path, xyz, tri, name='fieldev', materials=None, tri_material=None, colors=None, uvs=None, skin=None, extra=None):
    ''' The .gltf with its buffer inside; the baked pictures are the files beside it (their names are the uris) '''
    doc, binary = gltf_document(xyz, tri, name, materials, tri_material, colors, uvs, skin, extra, False)
    doc['buffers'][0]['uri'] = 'data:application/octet-stream;base64,' + base64.b64encode(binary).decode('ascii')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(doc, f, separators=(',', ':'))
