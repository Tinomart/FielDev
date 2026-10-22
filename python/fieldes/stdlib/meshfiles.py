'''
Triangle-mesh files: the writers behind export_mesh() and the readers of the formats the library does not read itself.

    write_mesh(path, xyz, tri)      the format is the file's extension: .stl .obj .ply .3mf .glb .gltf .fbx .off .dxf

A mesh is two flat sequences: `xyz` (x0, y0, z0, x1, ...) in millimetres and `tri` (a0, b0, c0, a1, ...), the triangles' vertices as indices
into it, counter-clockwise seen from outside.  Each format is written as its own specification says, with no library behind it:

    .stl   binary (ascii=True: text)        millimetres by convention
    .obj   Wavefront                         millimetres by convention
    .ply   binary little endian              millimetres by convention
    .3mf   3D Manufacturing Format           states its unit (millimetre)
    .glb   glTF 2.0 binary, .gltf with its buffer inside  metres, Y up: the numbers are turned into them
    .fbx   Autodesk FBX 7.4 ASCII (fbx.py)  states its unit (centimetre scale 0.1) and its axes (Z up)
    .off   Object File Format               millimetres by convention
    .dxf   AutoCAD DXF, 3DFACE entities     states its unit ($INSUNITS 4: millimetres)

and read back by the importers: STL, OBJ, PLY, 3MF and glTF by mesh_import.py, OFF, DXF (3DFACE and polyface meshes) and FBX here and in fbx.py.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import base64
import json
import math
import os
import struct
import zipfile
import zlib
from array import array

__all__ = ['write_mesh', 'MESH_WRITE_FORMATS', 'MESH_READ_FORMATS']

# What can be written, and read (by extension)
MESH_WRITE_FORMATS = ('.stl', '.obj', '.ply', '.3mf', '.glb', '.gltf', '.fbx', '.off', '.dxf')
MESH_READ_FORMATS = ('.stl', '.obj', '.ply', '.3mf', '.glb', '.gltf', '.fbx', '.off', '.dxf')


def _clean_name(name):
    name = ''.join(c if (c.isalnum() or c in '_-') else '_' for c in str(name or 'fielDes'))
    return name or 'mesh'


def _bounds(xyz):
    n = len(xyz) // 3
    if not n:
        return (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)
    lo = [min(xyz[i::3]) for i in range(3)]
    hi = [max(xyz[i::3]) for i in range(3)]
    return lo, hi


def _num(v):
    ''' A number as short text that reads back as the same float32 '''
    return '%.9g' % v


# ---------------------------------------------------------------------------
# STL

def write_stl(path, xyz, tri, name='fieldes', ascii=False):
    n = len(tri) // 3
    if ascii:
        out = ['solid %s\n' % _clean_name(name)]
        for t in range(n):
            a, b, c = tri[3 * t] * 3, tri[3 * t + 1] * 3, tri[3 * t + 2] * 3
            p = (xyz[a], xyz[a + 1], xyz[a + 2]), (xyz[b], xyz[b + 1], xyz[b + 2]), (xyz[c], xyz[c + 1], xyz[c + 2])
            nx, ny, nz = _normal(*p)
            out.append(' facet normal %s %s %s\n  outer loop\n' % (_num(nx), _num(ny), _num(nz)))
            for q in p:
                out.append('   vertex %s %s %s\n' % (_num(q[0]), _num(q[1]), _num(q[2])))
            out.append('  endloop\n endfacet\n')
        out.append('endsolid %s\n' % _clean_name(name))
        with open(path, 'w', encoding='ascii') as f:
            f.write(''.join(out))
        return
    buf = bytearray(84 + 50 * n)
    struct.pack_into('<80sI', buf, 0, (b'FielDes ' + _clean_name(name).encode('ascii', 'replace'))[:80].ljust(80, b' '), n)
    pack = struct.Struct('<12fH').pack_into
    pos = 84
    for t in range(n):
        a, b, c = tri[3 * t] * 3, tri[3 * t + 1] * 3, tri[3 * t + 2] * 3
        p0, p1, p2 = (xyz[a], xyz[a + 1], xyz[a + 2]), (xyz[b], xyz[b + 1], xyz[b + 2]), (xyz[c], xyz[c + 1], xyz[c + 2])
        nx, ny, nz = _normal(p0, p1, p2)
        pack(buf, pos, nx, ny, nz, p0[0], p0[1], p0[2], p1[0], p1[1], p1[2], p2[0], p2[1], p2[2], 0)
        pos += 50
    with open(path, 'wb') as f:
        f.write(buf)


def _normal(p0, p1, p2):
    ux, uy, uz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
    vx, vy, vz = p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length < 1e-30:
        return 0.0, 0.0, 0.0
    return nx / length, ny / length, nz / length


def read_stl(path):
    ''' A binary or ASCII STL: (xyz, tri) with the vertices that share a place welded '''
    with open(path, 'rb') as f:
        data = f.read()
    corners = []
    if len(data) >= 84 and 84 + 50 * struct.unpack_from('<I', data, 80)[0] == len(data):
        n = struct.unpack_from('<I', data, 80)[0]
        unpack = struct.Struct('<12fH').unpack_from
        for t in range(n):
            v = unpack(data, 84 + 50 * t)
            corners.append((v[3], v[4], v[5]))
            corners.append((v[6], v[7], v[8]))
            corners.append((v[9], v[10], v[11]))
    else:
        for line in data.decode('ascii', 'replace').splitlines():
            w = line.split()
            if len(w) == 4 and w[0] == 'vertex':
                corners.append((float(w[1]), float(w[2]), float(w[3])))
        if len(corners) % 3:
            raise RuntimeError('not an STL file')
    xyz, tri, seen = array('f'), array('I'), {}
    for p in corners:
        k = seen.get(p)
        if k is None:
            k = seen[p] = len(xyz) // 3
            xyz.extend(p)
        tri.append(k)
    return xyz, tri


def convert_mesh(source, target):
    ''' A mesh file written in another format: `source` (an STL) read, `target` written in the format of its extension '''
    xyz, tri = read_stl(source)
    write_mesh(target, xyz, tri)
    return len(tri) // 3


# ---------------------------------------------------------------------------
# OBJ

def _write_mtl(path, materials):
    ''' The .mtl file of an OBJ: the colour (Kd), how it shines (Ns, Ks), the physically based roughness and metalness (Pr, Pm: the extension that Blender and the engines read) '''
    out = ['# FielDes materials\n']
    for m in materials:
        spec = 0.04 * (1.0 - m.metallic) + m.metallic
        out.append('\nnewmtl %s\nKd %s %s %s\nKs %s %s %s\nNs %s\nd 1\nillum 2\nPr %s\nPm %s\n' % (
            (m.name,) + tuple(_num(c) for c in m.color) + (_num(spec),) * 3 + (_num(max(1.0, (1.0 - m.roughness) ** 2 * 1000.0)), _num(m.roughness), _num(m.metallic))))
        if m.emissive:
            out.append('Ke %s %s %s\n' % tuple(_num(c) for c in m.emissive))
        if m.texture:
            out.append('map_Kd %s\n' % m.texture)
    with open(path, 'w', encoding='ascii') as f:
        f.write(''.join(out))


def write_obj(path, xyz, tri, name='fieldes', note='millimetres', materials=None, tri_material=None, colors=None, uvs=None):
    ''' materials: the list of the materials (a .mtl file is written beside the OBJ), tri_material: the number of the material of each triangle (-1: none),
        colors: r, g, b of each vertex (the "v x y z r g b" that Blender and MeshLab read), uvs: u, v of each vertex (the "vt" lines; v up, as OBJ has it) '''
    mtl = os.path.splitext(path)[0] + '.mtl'
    out = ['# FielDes (%s)\n' % note]
    if materials:
        out.append('mtllib %s\n' % os.path.basename(mtl))
    out.append('o %s\n' % _clean_name(name))
    for i in range(0, len(xyz), 3):
        line = 'v %s %s %s' % (_num(xyz[i]), _num(xyz[i + 1]), _num(xyz[i + 2]))
        if colors is not None:
            line += ' %s %s %s' % (_num(colors[i]), _num(colors[i + 1]), _num(colors[i + 2]))
        out.append(line + '\n')
    if uvs is not None:
        for i in range(0, len(uvs), 2):
            out.append('vt %s %s\n' % (_num(uvs[i]), _num(uvs[i + 1])))
    for k, group in _by_material(tri, tri_material if materials else None):
        if k >= 0:
            out.append('usemtl %s\n' % materials[k].name)
        for t in range(0, len(group), 3):
            a, b, c = group[t] + 1, group[t + 1] + 1, group[t + 2] + 1
            out.append(('f %d/%d %d/%d %d/%d\n' % (a, a, b, b, c, c)) if uvs is not None else ('f %d %d %d\n' % (a, b, c)))
    with open(path, 'w', encoding='ascii') as f:
        f.write(''.join(out))
    if materials:
        _write_mtl(mtl, materials)


# ---------------------------------------------------------------------------
# PLY

def write_ply(path, xyz, tri, name='fieldes', note='millimetres', colors=None, uvs=None):
    ''' colors: r, g, b (0 to 1) of each vertex, written as the uchar red, green, blue that every PLY reader knows; uvs: u, v of each vertex, as the float s and t '''
    nv, nt = len(xyz) // 3, len(tri) // 3
    head = ('ply\nformat binary_little_endian 1.0\ncomment FielDes (%s) %s\n'
            'element vertex %d\nproperty float x\nproperty float y\nproperty float z\n%s%s'
            'element face %d\nproperty list uchar int vertex_indices\nend_header\n'
            % (note, _clean_name(name), nv, 'property float s\nproperty float t\n' if uvs is not None else '',
               'property uchar red\nproperty uchar green\nproperty uchar blue\n' if colors is not None else '', nt)).encode('ascii')
    if colors is None and uvs is None:
        verts = _little(array('f', xyz))
    else:
        pack_vertex = struct.Struct('<3f' + ('2f' if uvs is not None else '') + ('3B' if colors is not None else '')).pack
        rows = []
        for i in range(nv):
            row = [xyz[3 * i], xyz[3 * i + 1], xyz[3 * i + 2]]
            if uvs is not None:
                row += [uvs[2 * i], uvs[2 * i + 1]]
            if colors is not None:
                row += [min(255, max(0, int(round(colors[3 * i + k] * 255)))) for k in range(3)]
            rows.append(pack_vertex(*row))
        verts = b''.join(rows)
    pack = struct.Struct('<B3i').pack
    faces = b''.join(pack(3, tri[t], tri[t + 1], tri[t + 2]) for t in range(0, len(tri), 3))
    with open(path, 'wb') as f:
        f.write(head)
        f.write(verts)
        f.write(faces)


# ---------------------------------------------------------------------------
# 3MF

def write_3mf(path, xyz, tri, name='fieldes'):
    verts = ''.join('<vertex x="%s" y="%s" z="%s"/>' % (_num(xyz[i]), _num(xyz[i + 1]), _num(xyz[i + 2])) for i in range(0, len(xyz), 3))
    tris = ''.join('<triangle v1="%d" v2="%d" v3="%d"/>' % (tri[t], tri[t + 1], tri[t + 2]) for t in range(0, len(tri), 3))
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             '<metadata name="Application">FielDes</metadata>'
             '<resources><object id="1" type="model" name="%s"><mesh><vertices>%s</vertices><triangles>%s</triangles></mesh></object></resources>'
             '<build><item objectid="1"/></build></model>' % (_clean_name(name), verts, tris))
    types = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', types)
        z.writestr('_rels/.rels', rels)
        z.writestr('3D/3dmodel.model', model)


def write_3mf_objects(path, objects):
    ''' A 3MF with several objects: [(name, xyz, tri, kind)] -- kind 'model' (a part), 'support' (a support that is not part of the print's shape) or 'other' (a volume that is not
        printed: a no-support region).  Each is an object of its own in the file and an item of the build, so that a slicer lists them apart '''
    resources, items = [], []
    for k, (name, xyz, tri, kind) in enumerate(objects, start=1):
        verts = ''.join('<vertex x="%s" y="%s" z="%s"/>' % (_num(xyz[i]), _num(xyz[i + 1]), _num(xyz[i + 2])) for i in range(0, len(xyz), 3))
        tris = ''.join('<triangle v1="%d" v2="%d" v3="%d"/>' % (tri[t], tri[t + 1], tri[t + 2]) for t in range(0, len(tri), 3))
        resources.append('<object id="%d" type="%s" name="%s"><mesh><vertices>%s</vertices><triangles>%s</triangles></mesh></object>' % (
            k, kind if kind in ('model', 'support', 'solidsupport', 'surface', 'other') else 'model', _clean_name(name), verts, tris))
        items.append('<item objectid="%d"/>' % k)
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             '<metadata name="Application">FielDes</metadata><resources>%s</resources><build>%s</build></model>' % (''.join(resources), ''.join(items)))
    types = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', types)
        z.writestr('_rels/.rels', rels)
        z.writestr('3D/3dmodel.model', model)


# ---------------------------------------------------------------------------
# glTF 2.0 (.glb, .gltf): metres, Y up

def _little(values):
    ''' The bytes of an array of numbers, little endian '''
    values = array(values.typecode, values)
    if struct.pack('=I', 1) != struct.pack('<I', 1):
        values.byteswap()
    return values.tobytes()


def _by_material(tri, tri_material):
    ''' The triangles of each material: [(the number of the material, its triangles as flat corners)], in the order of the materials; the ones that no material covers
        (-1) first.  With no materials, all of them in one '''
    if tri_material is None:
        return [(-1, tri)]
    groups = {}
    for t in range(len(tri) // 3):
        groups.setdefault(tri_material[t], array('I')).extend(tri[3 * t:3 * t + 3])
    return [(k, groups[k]) for k in sorted(groups)]


def _gltf_material(m, texture=None):
    ''' texture: the number of the glTF texture that is the colour map of the material, if it has one '''
    out = {'name': m.name, 'pbrMetallicRoughness': {'baseColorFactor': [m.color[0], m.color[1], m.color[2], 1.0],
                                                      'metallicFactor': m.metallic, 'roughnessFactor': m.roughness}}
    if texture is not None:
        out['pbrMetallicRoughness']['baseColorTexture'] = {'index': texture}
    if m.emissive:
        out['emissiveFactor'] = list(m.emissive)
    return out


def _gltf_document(xyz, tri, name, materials=None, tri_material=None, colors=None, uvs=None):
    ''' (the glTF document, its binary buffer).  The positions are in metres with Y up (x, z, -y: FielDes's Z up turned the way mesh_import turns glTF back); a primitive of
        the mesh for each material (the whole mesh in one when there are none), and the vertex colours as COLOR_0 '''
    pos = array('f')
    for i in range(0, len(xyz), 3):
        pos.extend((xyz[i] * 0.001, xyz[i + 2] * 0.001, -xyz[i + 1] * 0.001))
    lo = [min(pos[i::3]) for i in range(3)] if len(pos) else [0.0] * 3
    hi = [max(pos[i::3]) for i in range(3)] if len(pos) else [0.0] * 3
    nv = len(xyz) // 3
    binary = _little(pos)
    views = [{'buffer': 0, 'byteOffset': 0, 'byteLength': len(binary), 'target': 34962}]
    accessors = [{'bufferView': 0, 'componentType': 5126, 'count': nv, 'type': 'VEC3', 'min': lo, 'max': hi}]
    attributes = {'POSITION': 0}
    if colors is not None:
        data = _little(array('f', colors))
        views.append({'buffer': 0, 'byteOffset': len(binary), 'byteLength': len(data), 'target': 34962})
        accessors.append({'bufferView': len(views) - 1, 'componentType': 5126, 'count': nv, 'type': 'VEC3'})
        attributes['COLOR_0'] = len(accessors) - 1
        binary += data
    if uvs is not None:
        flipped = array('f', uvs)
        flipped[1::2] = array('f', [1.0 - v for v in uvs[1::2]])          # (glTF has v down from the top of the image)
        data = _little(flipped)
        views.append({'buffer': 0, 'byteOffset': len(binary), 'byteLength': len(data), 'target': 34962})
        accessors.append({'bufferView': len(views) - 1, 'componentType': 5126, 'count': nv, 'type': 'VEC2'})
        attributes['TEXCOORD_0'] = len(accessors) - 1
        binary += data
    primitives = []
    for k, group in _by_material(tri, tri_material):
        data = _little(group)
        views.append({'buffer': 0, 'byteOffset': len(binary), 'byteLength': len(data), 'target': 34963})
        accessors.append({'bufferView': len(views) - 1, 'componentType': 5125, 'count': len(group), 'type': 'SCALAR'})
        primitive = {'attributes': attributes, 'indices': len(accessors) - 1, 'mode': 4}
        if k >= 0:
            primitive['material'] = k
        primitives.append(primitive)
        binary += data
    doc = {
        'asset': {'version': '2.0', 'generator': 'FielDes'},
        'scene': 0,
        'scenes': [{'nodes': [0]}],
        'nodes': [{'mesh': 0, 'name': _clean_name(name)}],
        'meshes': [{'name': _clean_name(name), 'primitives': primitives}],
        'accessors': accessors,
        'bufferViews': views,
        'buffers': [{'byteLength': len(binary)}],
    }
    if materials:
        images, made = [], []
        for m in materials:
            if m.texture and m.texture not in images:
                images.append(m.texture)
            made.append(_gltf_material(m, images.index(m.texture) if m.texture else None))
        doc['materials'] = made
        if images:
            doc['images'] = [{'uri': uri} for uri in images]
            doc['textures'] = [{'source': k} for k in range(len(images))]
    return doc, binary


def write_glb(path, xyz, tri, name='fieldes', materials=None, tri_material=None, colors=None, uvs=None):
    doc, binary = _gltf_document(xyz, tri, name, materials, tri_material, colors, uvs)
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


def write_gltf(path, xyz, tri, name='fieldes', materials=None, tri_material=None, colors=None, uvs=None):
    doc, binary = _gltf_document(xyz, tri, name, materials, tri_material, colors, uvs)
    doc['buffers'][0]['uri'] = 'data:application/octet-stream;base64,' + base64.b64encode(binary).decode('ascii')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(doc, f, separators=(',', ':'))


# ---------------------------------------------------------------------------
# OFF

def write_off(path, xyz, tri, name='fieldes'):
    out = ['OFF\n', '%d %d 0\n' % (len(xyz) // 3, len(tri) // 3)]
    for i in range(0, len(xyz), 3):
        out.append('%s %s %s\n' % (_num(xyz[i]), _num(xyz[i + 1]), _num(xyz[i + 2])))
    for t in range(0, len(tri), 3):
        out.append('3 %d %d %d\n' % (tri[t], tri[t + 1], tri[t + 2]))
    with open(path, 'w', encoding='ascii') as f:
        f.write(''.join(out))


def read_off(path):
    ''' An Object File Format mesh (OFF; the counts on the header line or the next; a face line may carry colours after its indices): (xyz, tri) --
        polygons are fanned '''
    with open(path, 'r', encoding='ascii', errors='replace') as f:
        lines = [ln.split('#', 1)[0].strip() for ln in f]
    lines = [ln for ln in lines if ln]
    if not lines or not lines[0].upper().startswith(('OFF', 'COFF', 'NOFF')):
        raise RuntimeError('not an OFF file (it does not start with "OFF")')
    head = lines[0].split()
    if len(head) >= 3 and head[0].upper() == 'OFF':
        counts, at = head[1:3], 1
    else:
        counts, at = lines[1].split()[:2], 2
    nv, nf = int(counts[0]), int(counts[1])
    xyz = array('f')
    for ln in lines[at:at + nv]:
        w = ln.split()
        xyz.extend((float(w[0]), float(w[1]), float(w[2])))
    tri = array('I')
    for ln in lines[at + nv:at + nv + nf]:
        w = ln.split()
        k = int(w[0])
        poly = [int(x) for x in w[1:1 + k]]
        for j in range(1, k - 1):
            tri.extend((poly[0], poly[j], poly[j + 1]))
    return xyz, tri


# ---------------------------------------------------------------------------
# DXF

def write_dxf(path, xyz, tri, name='fieldes'):
    out = ['0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1015\n9\n$INSUNITS\n70\n4\n0\nENDSEC\n',
           '0\nSECTION\n2\nENTITIES\n']
    layer = _clean_name(name)
    for t in range(0, len(tri), 3):
        corners = []
        for k in range(3):
            i = tri[t + k] * 3
            corners.append((xyz[i], xyz[i + 1], xyz[i + 2]))
        out.append('0\n3DFACE\n8\n%s\n' % layer)
        for k, (x, y, z) in enumerate(corners + [corners[2]]):
            out.append('%d\n%s\n%d\n%s\n%d\n%s\n' % (10 + k, _num(x), 20 + k, _num(y), 30 + k, _num(z)))
    out.append('0\nENDSEC\n0\nEOF\n')
    with open(path, 'w', encoding='ascii') as f:
        f.write(''.join(out))


_DXF_UNITS_MM = {1: 25.4, 2: 304.8, 3: 1609344.0, 4: 1.0, 5: 10.0, 6: 1000.0, 7: 1e6, 8: 25.4e-6, 9: 0.0254, 10: 914.4,
                 13: 0.001, 14: 100.0, 15: 1e4, 16: 1e5}


def read_dxf(path):
    ''' A DXF mesh: its 3DFACE entities (a quad is two triangles) and polyface meshes (POLYLINE with VERTEX records, flags 64 and 128).
        Returns (xyz, tri, declared_mm): the unit the file says ($INSUNITS) in millimetres, or None '''
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        raw = f.read().splitlines()
    if len(raw) < 2:
        raise RuntimeError('not a DXF file')
    pairs = []
    for i in range(0, len(raw) - 1, 2):
        try:
            pairs.append((int(raw[i].strip()), raw[i + 1].strip()))
        except ValueError:
            raise RuntimeError('not an ASCII DXF file (a group code is not a number: binary DXF is not read)')
    xyz = array('f')
    tri = array('I')
    declared = None
    section = None
    entity = None
    data = {}
    poly = None                      # the polyface being read: [vertices, faces]

    def corner(k):
        return (float(data.get(10 + k, 0)), float(data.get(20 + k, 0)), float(data.get(30 + k, 0)))

    def finish(kind):
        nonlocal poly
        if kind == '3DFACE':
            c = [corner(k) for k in range(4)]
            base = len(xyz) // 3
            for p in c:
                xyz.extend(p)
            tri.extend((base, base + 1, base + 2))
            if c[3] != c[2]:
                tri.extend((base, base + 2, base + 3))
        elif kind == 'VERTEX' and poly is not None:
            flags = int(data.get(70, 0))
            if flags & 128 and not flags & 64:                       # a face: the corners are the numbers of its vertices
                idx = [int(data.get(c, 0)) for c in (71, 72, 73, 74)]
                idx = [abs(i) - 1 for i in idx if i != 0]
                poly[1].append(idx)
            else:
                poly[0].append(corner(0))
        elif kind == 'SEQEND' and poly is not None:
            base = len(xyz) // 3
            for p in poly[0]:
                xyz.extend(p)
            for idx in poly[1]:
                for j in range(1, len(idx) - 1):
                    tri.extend((base + idx[0], base + idx[j], base + idx[j + 1]))
            poly = None

    var = None
    for code, value in pairs:
        if code == 0:
            if entity is not None and section == 'ENTITIES':
                finish(entity)
            data = {}
            if value == 'SECTION':
                entity = None
                section = '?'
            elif value == 'ENDSEC':
                entity = None
                section = None
            elif value == 'POLYLINE' and section == 'ENTITIES':
                entity = 'POLYLINE'
                poly = [[], []]
            else:
                entity = value
            continue
        if code == 2 and section == '?':
            section = value
            continue
        if section == 'HEADER':
            if code == 9:
                var = value
            elif var == '$INSUNITS' and code == 70:
                declared = _DXF_UNITS_MM.get(int(value))
            continue
        if entity is not None:
            data[code] = value
    if entity is not None and section == 'ENTITIES':
        finish(entity)
    if not len(tri):
        raise RuntimeError('the DXF file has no 3DFACE or polyface mesh entities (only meshes made of faces are read)')
    return xyz, tri, declared


# ---------------------------------------------------------------------------

def write_mesh(path, xyz, tri, name=None, ascii=False, note='millimetres', materials=None, tri_material=None, colors=None, uvs=None):
    ''' Writes a mesh in the format of the file's extension (see the top of this file).  `note` is what the comment of an OBJ or a PLY says of the numbers
        ("millimetres", "metres, Y up"): the unit and the axes are the caller's to say in the formats that have none of their own '''
    path = os.fspath(path)
    ext = os.path.splitext(path)[1].lower()
    name = name or os.path.splitext(os.path.basename(path))[0]
    if len(tri) % 3 or len(xyz) % 3:
        raise ValueError('a mesh is flat lists of x, y, z and of triangle corners')
    if ext == '.stl':
        write_stl(path, xyz, tri, name, ascii)
    elif ext == '.obj':
        write_obj(path, xyz, tri, name, note, materials, tri_material, colors, uvs)
    elif ext == '.ply':
        write_ply(path, xyz, tri, name, note, colors, uvs)
    elif ext == '.3mf':
        write_3mf(path, xyz, tri, name)
    elif ext == '.glb':
        write_glb(path, xyz, tri, name, materials, tri_material, colors, uvs)
    elif ext == '.gltf':
        write_gltf(path, xyz, tri, name, materials, tri_material, colors, uvs)
    elif ext == '.off':
        write_off(path, xyz, tri, name)
    elif ext == '.dxf':
        write_dxf(path, xyz, tri, name)
    elif ext == '.fbx':
        from fieldes.stdlib import fbx
        fbx.write_fbx(path, xyz, tri, _clean_name(name))
    else:
        raise ValueError('cannot write {!r}: the mesh formats are {}'.format(ext, ', '.join(MESH_WRITE_FORMATS)))
    return path
