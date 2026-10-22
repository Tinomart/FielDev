'''
PNG files: the writer behind the baked textures, and a reader for checking them.

    write_png("skin.png", 256, 256, pixels, channels=3)     8 bits a channel: 1 (grey), 2 (grey, alpha), 3 (RGB) or 4 (RGBA); the rows from the top
    width, height, channels, pixels = read_png("skin.png")  8-bit, not interlaced: what write_png writes, and what the common tools save

`pixels` is `bytes` (or a bytearray): `width * height * channels` of them.  Nothing but the standard library (zlib) is used.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import os
import struct
import zlib

__all__ = ['write_png', 'read_png']

_SIGNATURE = b'\x89PNG\r\n\x1a\n'
_COLOR_TYPE = {1: 0, 2: 4, 3: 2, 4: 6}              # (channels -> the PNG colour type: grey, grey + alpha, RGB, RGBA)
_CHANNELS = {0: 1, 4: 2, 2: 3, 6: 4}


def _chunk(kind, data):
    body = kind + data
    return struct.pack('>I', len(data)) + body + struct.pack('>I', zlib.crc32(body) & 0xffffffff)


def png_bytes(width, height, pixels, channels=3, level=6):
    ''' The bytes of a PNG file '''
    if channels not in _COLOR_TYPE:
        raise ValueError('a PNG has 1, 2, 3 or 4 channels, not {!r}'.format(channels))
    if width < 1 or height < 1:
        raise ValueError('a PNG is at least one pixel across, not {} x {}'.format(width, height))
    stride = width * channels
    if len(pixels) != stride * height:
        raise ValueError('a {} x {} PNG with {} channels has {} bytes, not {}'.format(width, height, channels, stride * height, len(pixels)))
    pixels = bytes(pixels)
    rows = [b'\x00' + pixels[y * stride:(y + 1) * stride] for y in range(height)]
    header = struct.pack('>IIBBBBB', width, height, 8, _COLOR_TYPE[channels], 0, 0, 0)
    return _SIGNATURE + _chunk(b'IHDR', header) + _chunk(b'IDAT', zlib.compress(b''.join(rows), level)) + _chunk(b'IEND', b'')


def write_png(path, width, height, pixels, channels=3):
    ''' Writes `pixels` (8 bits a channel, the rows from the top) as a PNG file; a folder that is not there is made.  Returns the path '''
    path = os.fspath(path)
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    with open(path, 'wb') as f:
        f.write(png_bytes(width, height, pixels, channels))
    return path


def read_png(path):
    ''' (width, height, channels, pixels) of an 8-bit PNG that is not interlaced (grey, grey + alpha, RGB or RGBA) '''
    with open(os.fspath(path), 'rb') as f:
        data = f.read()
    if data[:8] != _SIGNATURE:
        raise ValueError('{}: not a PNG file'.format(path))
    pos, header, idat = 8, None, []
    while pos + 8 <= len(data):
        size, kind = struct.unpack_from('>I4s', data, pos)
        body = data[pos + 8:pos + 8 + size]
        if kind == b'IHDR':
            header = struct.unpack('>IIBBBBB', body)
        elif kind == b'IDAT':
            idat.append(body)
        elif kind == b'IEND':
            break
        pos += 12 + size
    if header is None:
        raise ValueError('{}: a PNG file with no header'.format(path))
    width, height, depth, color, _, _, interlace = header
    if depth != 8 or interlace or color not in _CHANNELS:
        raise ValueError('{}: only 8-bit PNGs that are not interlaced and have no palette are read'.format(path))
    channels = _CHANNELS[color]
    stride = width * channels
    raw = zlib.decompress(b''.join(idat))
    out = bytearray(stride * height)
    previous = bytearray(stride)
    at = 0
    for y in range(height):
        kind = raw[at]
        row = bytearray(raw[at + 1:at + 1 + stride])
        at += 1 + stride
        if kind == 1:                                   # (Sub)
            for i in range(channels, stride):
                row[i] = (row[i] + row[i - channels]) & 255
        elif kind == 2:                                 # (Up)
            for i in range(stride):
                row[i] = (row[i] + previous[i]) & 255
        elif kind == 3:                                 # (Average)
            for i in range(stride):
                left = row[i - channels] if i >= channels else 0
                row[i] = (row[i] + ((left + previous[i]) >> 1)) & 255
        elif kind == 4:                                 # (Paeth)
            for i in range(stride):
                a = row[i - channels] if i >= channels else 0
                b = previous[i]
                c = previous[i - channels] if i >= channels else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                row[i] = (row[i] + (a if pa <= pb and pa <= pc else (b if pb <= pc else c))) & 255
        elif kind != 0:
            raise ValueError('{}: a PNG row with the filter {}'.format(path, kind))
        out[y * stride:(y + 1) * stride] = row
        previous = row
    return width, height, channels, bytes(out)
