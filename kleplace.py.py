"""
KLEPlace - Place KiCad footprints based on KLE JSON output

License: IANAL but do whatever the fuck you want with this as long as you're not making money off the code itself.

You can use it to build keyboards to sell, just don't sell a KiCad plugin or anything.

No guarantees, etc. There are probably bugs here, but it works for my purposes.

How to use:
1. Put this script somewhere KiCad can load it. For me on macOS, this was ~/Library/Python/2.7/lib/python/site-packages/kleplace.py
2. Create your schematic, being sure to set the references for the switches. Use "SW_A0" for row A column 0
3. Assign your footprints, generate your netlist, open your PCB and import the netlist
4. Set up a KLE layout where the "legends" correspond to switch references. The script will add the "SW_" prefix by default.
5. Open the Python console in Pcbnew and enter:
    >>> import kleplace
    >>> kleplace.KLEPlace("<path to your KLE JSON>")
6. That's it! Your switch footprints should be laid out according to the KLE layout.

Known limitations:
* This doesn't handle non-rectangular keys at all. Sorry, ISO Gang.
"""

import json
import math

import pcbnew


GRID = 19.05 # mm per switch
MM = 10e5 # KiCad units per mm
OFFSET_X, OFFSET_Y = 2, 2 # how far from the top left of the page to place everything, in switch units


def KLEPlace(kle_path, ref_prefix='SW_'):
    with open(kle_path, 'r') as kle_file:
        keys = deserialize(json.load(kle_file))

    board = pcbnew.GetBoard()
    offset = vec(OFFSET_X, OFFSET_Y)

    for key in keys:
        module = board.FindModuleByReference(ref_prefix + key.ref)
        pos = vec(key.x, key.y)
        sizeOffset = vec(
            (key.w - 1) / 2.0 + 0.5, # offset switch positions based on their size
            (key.h - 1) / 2.0 + 0.5, # and offset all by 0.5 since KLE uses top-left corner and KiCad uses center for positioning
        )
        if key.r:
            rot = rotmat(-key.r)
            new = transform(pos, matmul(transmat(key.rx, key.ry), rot, transmat(-key.rx, -key.ry)))
            sizeOffset = transform(sizeOffset, rot)
            module.SetOrientation(-key.r * 10)

        pos = vecadd(pos, sizeOffset, offset)

        module.SetPosition(pcbnew.wxPoint(pos[0] * GRID * MM, pos[1] * GRID * MM))

    pcbnew.Refresh()


# Data model and deserialization

class Key(object):

    x = 0
    y = 0
    r = 0
    w = 1
    h = 1
    rx = 0
    ry = 0
    ref = ''

    def copy(self):
        new = Key()
        new.x, new.y = self.x, self.y
        new.w, new.h = self.w, self.h
        new.r, new.rx, new.ry = self.r, self.rx, self.ry
        new.ref = self.ref
        return new

    def __str__(self):
        return str(self.__dict__)

def deserialize(data):
    keys = []
    current = Key()

    for row in data:
        if not isinstance(row, list):
            continue

        current.x = 0

        for idx, cell in enumerate(row):
            if isinstance(cell, (str, unicode)):
                new = current.copy()

                new.ref = cell
                keys.append(new)

                current.x += current.w
                current.w, current.h = 1, 1
            if isinstance(cell, dict):
                if 'r' in cell:
                    if idx != 0:
                        raise Exception('"r" can only be used on the first key in a row')
                    current.r = cell['r']
                if 'rx' in cell:
                    if idx != 0:
                        raise Exception('"rx" can only be used on the first key in a row')
                    current.rx = cell['rx']
                    current.x = cell['rx']
                if 'ry' in cell:
                    if idx != 0:
                        raise Exception('"ry" can only be used on the first key in a row')
                    current.ry = cell['ry']
                    current.y = cell['ry']

                current.x += cell.get('x', 0)
                current.y += cell.get('y', 0)
                current.w = cell.get('w', current.w)
                current.h = cell.get('h', current.h)

        current.y += 1
        current.x = current.rx
    
    return keys


# Math utility functions

def matmul(X, *Ys):
    res = X
    for Y in Ys:
        res = [
            [
                sum(a*b for a,b in zip(X_row,Y_col))
                for Y_col in zip(*Y)
            ]
            for X_row in res
        ]
    return res

def vecadd(*vecs):
    return [sum(pos) for pos in zip(*vecs)]

def transform(v, A):
    return [
        sum(A[i][j] * v[j] for j in range(len(v)))
        for i in range(len(A))
    ]

def vec(x, y):
    return [x, y, 1]

def rotmat(theta):
    return [
        [math.cos(math.radians(theta)), math.sin(math.radians(theta)), 0],
        [-math.sin(math.radians(theta)), math.cos(math.radians(theta)), 0],
        [0, 0, 1],
    ]

def transmat(x, y):
    return [
        [1, 0, x],
        [0, 1, y],
        [0, 0, 1],
    ]