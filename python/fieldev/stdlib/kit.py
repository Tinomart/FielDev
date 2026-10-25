'''
Modular kits: pieces that fit on a grid, and levels built from them.

A modular kit is a handful of pieces -- a floor tile, a wall, a wall with a door, a corner -- each exactly one grid cell wide, made once and set out as many times as a level
needs.  What can go wrong is the seam: a piece that is a hair too wide, a wall that does not meet its neighbour.  Here every piece is a field cut to its cell, so it ends exactly
on the cell's faces, and `seam(a, b)` checks it by asking both fields what is solid on the face they share.

    walls = kit(cell=(4, 4, 3), wall=0.3, floor=0.25)           # a cell is 4 x 4 x 3; the floor is 0.25 thick
    walls.pieces()                                               # {"floor": ..., "wall": ..., "wall_door": ..., "wall_window": ..., "corner": ..., "pillar": ...}
    house = walls.build(["#####",
                         "#####",
                         "##  #"], edges={(2, 2, 0): "door"})  # a floor plan: '#' is a cell that is inside; walls stand on every edge that has outside beyond it
    walls.export(house, "kit/")                                  # each piece once, and the list of where each one stands -- what an engine builds a level from

The cell of a piece has its south-west floor corner at the origin: a piece covers x from 0 to the cell's width, y from 0 to its depth, z from 0 to its height.  Walls are made
standing along the south edge (the front); `turn` 1, 2, 3 turns a piece a quarter, a half, three quarters about the middle of its cell (counter-clockwise from above), which puts
a wall on the east, north, west edge.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import json
import math
import os

from fieldev.shape import Shape
from fieldev.stdlib.gameunits import export_options
from fieldev.stdlib.fields import union_all, evaluate
from fieldev.stdlib.shapes import box, _bounded
from fieldev.stdlib.transforms import move, rotate_z
from fieldev.stdlib.level import doorway, window_opening

__all__ = ['kit', 'Kit']

_RISES = ((0, 1), (-1, 0), (0, -1), (1, 0))         # (the way stairs rise for 0, 1, 2, 3 quarter turns: north, west, south, east)
_DIRS = ((0, -1), (1, 0), (0, 1), (-1, 0))          # (the neighbour a wall faces away to: south, east, north, west)


def _cell(cell):
    if isinstance(cell, (int, float)):
        cell = (cell, cell, cell)
    try:
        sx, sy, sz = (float(c) for c in cell)
    except (TypeError, ValueError):
        raise ValueError('kit: cell is (width, depth, height)')
    if min(sx, sy, sz) <= 0:
        raise ValueError('kit: the cell has a size above zero')
    return sx, sy, sz


def kit(cell=(4.0, 4.0, 3.0), wall=0.3, floor=0.25, door=(1.4, 2.3), window=(1.2, 1.1, 1.0)):
    ''' A kit with this cell (width, depth, height), walls `wall` thick, floors and ceilings `floor` thick, doors (width, height) and windows (width, height, sill height above the
        floor).  A cell that is as wide as it is deep can be turned; one that is not can only be turned a half '''
    return Kit(_cell(cell), float(wall), float(floor), tuple(float(d) for d in door), tuple(float(w) for w in window))


class Kit:
    ''' See the top of this file '''

    def __init__(self, cell, wall, floor, door, window):
        self.cell = cell
        self.wall = wall
        self.floor = floor
        self.door = door
        self.window = window
        sx, sy, sz = cell
        if wall * 2 >= min(sx, sy) or floor * 2 >= sz:
            raise ValueError('kit: the walls and floors are thicker than the cell can hold')
        if door[0] >= sx - 2 * wall or door[1] >= sz - floor:
            raise ValueError('kit: the door does not fit in the wall of a cell')
        if window[0] >= sx - 2 * wall or window[2] + window[1] >= sz - floor:
            raise ValueError('kit: the window does not fit in the wall of a cell')

    # ---- the pieces: each in its own cell, ending exactly on its faces

    def _in_cell(self, body, top=None):
        sx, sy, sz = self.cell
        sz = sz if top is None else float(top)             # (stairs reach the top of the floor above, which is the next cell's)
        clipped = body.max(box((0.0, 0.0, 0.0), (sx, sy, sz)))
        _bounded(clipped, [0.0, 0.0, 0.0], [sx, sy, sz])
        return clipped

    def floor_tile(self):
        ''' A floor: the whole cell, `floor` thick '''
        sx, sy, sz = self.cell
        return self._in_cell(box((0.0, 0.0, 0.0), (sx, sy, self.floor)))

    def ceiling_tile(self):
        ''' A ceiling: the whole cell, `floor` thick, at the top of it '''
        sx, sy, sz = self.cell
        return self._in_cell(box((0.0, 0.0, sz - self.floor), (sx, sy, sz)))

    def wall_piece(self, opening=None, trim=(False, False)):
        ''' A wall along the south edge of the cell, from the floor to the ceiling.  `opening`: None, "door", "window" or "arch" (a door with a round top), in the middle of it.
            `trim`: (start, end) -- the end of the wall that is cut back by the thickness of a wall, where a wall that stands across it owns the corner '''
        sx, sy, sz = self.cell
        w = self.wall
        body = box((w if trim[0] else 0.0, 0.0, 0.0), (sx - w if trim[1] else sx, w, sz))
        mid = sx / 2.0
        if opening in ('door', 'arch'):
            body = body.max(-doorway((mid, w / 2.0, self.floor), width=self.door[0], height=self.door[1], depth=4.0 * w, axis='y', arch=(opening == 'arch')))
        elif opening == 'window':
            body = body.max(-window_opening((mid, w / 2.0, self.floor), width=self.window[0], height=self.window[1], sill=self.window[2], depth=4.0 * w, axis='y'))
        elif opening is not None:
            raise ValueError('wall_piece: opening is None, "door", "window" or "arch", not %r' % (opening,))
        return self._in_cell(body)

    def corner_piece(self):
        ''' A corner: the south wall, and the west wall from where the south wall ends to the north edge of the cell '''
        sx, sy, sz = self.cell
        w = self.wall
        return self._in_cell(box((0.0, 0.0, 0.0), (sx, w, sz)).min(box((0.0, w, 0.0), (w, sy, sz))))

    def pillar_piece(self):
        ''' A post in the south-west corner of the cell, a wall's thickness square: it closes the corner where two walls meet at a point '''
        sx, sy, sz = self.cell
        return self._in_cell(box((0.0, 0.0, 0.0), (self.wall, self.wall, sz)))

    def stairs_piece(self, steps=12):
        ''' Stairs up the cell from the south edge to the north, as high as the cell is (to the top of the floor above): `steps` solid steps '''
        sx, sy, sz = self.cell
        rise = sz / steps
        run = sy / steps
        y = Shape.Y()
        blocks = [box((0.0, k * run, 0.0), (sx, (k + 1) * run, self.floor + rise * (k + 1))) for k in range(int(steps))]
        return self._in_cell(union_all(blocks), self.cell[2] + self.floor)

    def pieces(self):
        ''' Every piece of the kit by its name: floor, ceiling, wall, wall_door, wall_arch, wall_window, corner, pillar, stairs '''
        return {'floor': self.floor_tile(), 'ceiling': self.ceiling_tile(), 'wall': self.wall_piece(), 'wall_door': self.wall_piece('door'),
                'wall_arch': self.wall_piece('arch'), 'wall_window': self.wall_piece('window'), 'corner': self.corner_piece(), 'pillar': self.pillar_piece(),
                'stairs': self.stairs_piece()}

    # ---- setting them out

    def place(self, piece, i, j, k=0, turn=0):
        ''' `piece` in the cell (i, j) of level k: turned `turn` quarter turns about the middle of its cell, then moved to the cell '''
        sx, sy, sz = self.cell
        if turn % 4 and abs(sx - sy) > 1e-9 and turn % 2:
            raise ValueError('place: a cell that is not square can only be turned a half')
        out = piece
        if turn % 4:
            out = rotate_z(out, math.radians(90.0 * (turn % 4)), (sx / 2.0, sy / 2.0, 0.0))
        return move(out, (i * sx, j * sy, k * sz))

    def build(self, plan, edges=None, levels=1, ceiling=True, stairs=None):
        ''' The level of a floor plan: `plan` is a list of strings, the first the northmost; any character but a space is a cell that is inside.  A floor on every cell; a wall on
            every edge that has outside (or the edge of the plan) beyond it; a post at every corner that two walls meet at a point.  `edges` changes an edge: {(i, j, side): kind} --
            the cell (i, j) counted from the south-west, `side` 0 south, 1 east, 2 north, 3 west, `kind` "door", "arch", "window", "wall" (a wall where there is none, between two
            cells that are inside) or None (no wall).  `levels`: stacked this many times; `ceiling`: a ceiling on the top one.  `stairs`: {(i, j, k): turn} -- a stairs piece in the cell (i, j) of level k, rising towards north, west, south
            or east for `turn` 0, 1, 2, 3, with the floor above it left out; it leads up into the next cell in that direction, which has to be inside the plan, and `levels` has to be at
            least k + 2.  The body has `_placements`: what stands where '''
        rows = [r for r in plan]
        height = len(rows)
        inside = set()
        for r, line in enumerate(rows):
            for i, ch in enumerate(line):
                if ch != ' ':
                    inside.add((i, height - 1 - r))
        if not inside:
            raise ValueError('build: the plan has no cell inside')
        edges = dict(edges or {})
        stairs = {tuple(int(c) for c in cell): int(turn) % 4 for cell, turn in dict(stairs or {}).items()}
        for (i, j, k), turn in stairs.items():
            di, dj = _RISES[turn]
            if (i, j) not in inside:
                raise ValueError('build: the stairs at %r are not in a cell that is inside the plan' % ((i, j, k),))
            if not 0 <= k < int(levels) - 1:
                raise ValueError('build: the stairs at %r lead up to a level that is not built (levels=%d)' % ((i, j, k), int(levels)))
            if (i + di, j + dj) not in inside:
                raise ValueError('build: the stairs at %r end at a cell that is not inside the plan' % ((i, j, k),))
        holes = {(i, j, k + 1) for (i, j, k) in stairs}             # (the floor above stairs is left out)
        pieces = self.pieces()
        placements = []

        def has_wall(i, j, side):
            kind = edges.get((i, j, side), '?')
            di, dj = _DIRS[side]
            # (the same edge seen from the cell on its other side)
            if kind == '?':
                kind = edges.get((i + di, j + dj, (side + 2) % 4), '?')
            if kind != '?':
                return kind
            return 'wall' if (i + di, j + dj) not in inside else None

        for (i, j) in sorted(inside):
            walls = {side: has_wall(i, j, side) for side in range(4)}
            for k in range(int(levels)):
                if (i, j, k) not in holes:
                    placements.append(('floor', i, j, k, 0))
                if (i, j, k) in stairs:
                    placements.append(('stairs', i, j, k, stairs[(i, j, k)]))
                if ceiling and k == int(levels) - 1:
                    placements.append(('ceiling', i, j, k, 0))
                for side in range(4):
                    kind = walls[side]
                    if kind is None:
                        continue
                    di, dj = _DIRS[side]
                    if edges.get((i + di, j + dj, (side + 2) % 4), '?') != '?' and (i + di, j + dj) in inside and (i, j) > (i + di, j + dj):
                        continue                     # (a wall between two cells that are inside is made once)
                    name = 'wall' if kind == 'wall' else 'wall_' + kind
                    if side in (1, 3):
                        # (the walls that run north-south give the corners to the ones that run east-west)
                        start_wall, end_wall = (walls[0], walls[2]) if side == 1 else (walls[2], walls[0])
                        trim = (start_wall is not None, end_wall is not None)
                        if trim != (False, False):
                            name = ('wall_trim' + ('_' + kind if kind != 'wall' else '')) + ('_s' if trim[0] else '') + ('_e' if trim[1] else '')
                            if name not in pieces:
                                pieces[name] = self.wall_piece(None if kind == 'wall' else kind, trim)
                    placements.append((name, i, j, k, side))
                # (a corner where two walls only touch: the cell is inside, the two neighbours are inside, the one between them is not)
                for corner in range(4):
                    a, b = _DIRS[corner], _DIRS[(corner + 3) % 4]
                    side_a, side_b = (i + a[0], j + a[1]), (i + b[0], j + b[1])
                    diagonal = (i + a[0] + b[0], j + a[1] + b[1])
                    if side_a in inside and side_b in inside and diagonal not in inside:
                        placements.append(('pillar', i, j, k, corner))
        self._pieces_made = pieces
        parts = [self.place(pieces[name], i, j, k, turn) for name, i, j, k, turn in placements]
        body = union_all(parts) if len(parts) > 1 else parts[0]
        sx, sy, sz = self.cell
        lo = [min(i for _, i, _, _, _ in placements) * sx, min(j for _, _, j, _, _ in placements) * sy, 0.0]
        hi = [(max(i for _, i, _, _, _ in placements) + 1) * sx, (max(j for _, _, j, _, _ in placements) + 1) * sy, int(levels) * sz]
        _bounded(body, lo, hi)
        body._placements = [{'piece': n, 'cell': [i, j, k], 'turn': t} for n, i, j, k, t in placements]
        body._kit = self
        body._kit_pieces = pieces               # (the pieces of this build: another build with the same kit does not change what `export` writes for this one)
        return body

    # ---- checking and exporting

    def seam(self, a, b, axis='x', samples=24):
        ''' Whether piece `a`, standing in a cell, meets piece `b` in the next cell along `axis` ("x", "y" or "z"): both are asked, on a grid of `samples` x `samples` points just
            inside the face they share, whether it is solid there.  Returns {"ok", "mismatch" (the fraction of points that differ), "points"} '''
        sx, sy, sz = self.cell
        n = int(samples)
        eps = 1e-3 * min(sx, sy, sz)
        extent = {'x': (sy, sz), 'y': (sx, sz), 'z': (sx, sy)}[axis]
        size = {'x': sx, 'y': sy, 'z': sz}[axis]
        grid = [((p + 0.5) / n * extent[0], (q + 0.5) / n * extent[1]) for p in range(n) for q in range(n)]

        def at(depth):
            if axis == 'x':
                return [(depth, u, v) for u, v in grid]
            if axis == 'y':
                return [(u, depth, v) for u, v in grid]
            return [(u, v, depth) for u, v in grid]

        solid_a = [value < 0 for value in evaluate(a, at(size - eps))]
        solid_b = [value < 0 for value in evaluate(b, at(eps))]
        wrong = sum(1 for p, q in zip(solid_a, solid_b) if p != q)
        return {'ok': wrong == 0, 'mismatch': wrong / float(len(grid)), 'points': len(grid)}

    def check(self, samples=24):
        ''' Every piece against every piece along x and y where they meet side by side: the walls (south walls side by side), the floors and the ceilings.  A list of what does not meet;
            empty when the kit is sound '''
        pieces = self.pieces()
        along_x = [n for n in pieces if n in ('floor', 'ceiling', 'wall', 'wall_door', 'wall_arch', 'wall_window')]
        problems = []
        for a in along_x:
            for b in along_x:
                same = a.split('_')[0] == b.split('_')[0] or {a.split('_')[0], b.split('_')[0]} <= {'wall'}
                if not same:
                    continue
                for axis in ('x',) if a.startswith('wall') else ('x', 'y'):
                    report = self.seam(pieces[a], pieces[b], axis, samples)
                    if not report['ok']:
                        problems.append((a, b, axis, report['mismatch']))
        return problems

    def export(self, built, folder, ext='glb', **options):
        ''' Writes the pieces that `built` (from `build`) uses, once each, as `folder/piece.glb`, and `folder/kit.json`: the size of the cell and, for every piece that stands in the
            level, its name, its cell (i, j, k) and its turn in quarter turns.  The other options are those of `export_mesh`.  Returns the paths '''
        from fieldev.stdlib.exporting import export_mesh
        placements = getattr(built, '_placements', None)
        if placements is None:
            raise TypeError('export: the first argument is the body that build(...) made')
        os.makedirs(os.fspath(folder), exist_ok=True)
        sx, sy, sz = self.cell
        made = getattr(built, '_kit_pieces', None) or getattr(self, '_pieces_made', None) or self.pieces()
        paths = []
        for name in sorted({p['piece'] for p in placements}):
            path = os.path.join(os.fspath(folder), '%s.%s' % (name, ext))
            lo, hi = getattr(made[name], '_bounds', None) or ((0.0, 0.0, 0.0), (sx, sy, sz))             # (the stairs are a floor's thickness higher than the cell)
            export_mesh(made[name], path, bounds=(tuple(lo), tuple(hi)), **export_options(ext, options))
            paths.append(path)
        index = os.path.join(os.fspath(folder), 'kit.json')
        with open(index, 'w') as f:
            json.dump({'cell': [sx, sy, sz], 'meshes': [os.path.basename(p) for p in paths], 'turn': 'quarter turns counter-clockwise about the middle of the cell, seen from above',
                       'placements': placements}, f, indent=1)
        return paths + [index]
