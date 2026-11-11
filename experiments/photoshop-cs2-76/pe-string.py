#!/usr/bin/env python3
"""Print string-table resources (RT_STRING) of a PE file by id.
Usage: pe-string.py FILE ID [ID ...]   (ids decimal or 0x hex)"""
import struct, sys
d = open(sys.argv[1], 'rb').read()
pe = struct.unpack_from('<I', d, 0x3c)[0]
nsec = struct.unpack_from('<H', d, pe + 6)[0]
osz = struct.unpack_from('<H', d, pe + 20)[0]
opt = pe + 24
secs = [struct.unpack_from('<8sIIII', d, opt + osz + i * 40) for i in range(nsec)]
def off(rva):
    for _n, vs, va, rs, ro in secs:
        if va <= rva < va + max(vs, rs):
            return rva - va + ro
    raise ValueError(hex(rva))
root = off(struct.unpack_from('<I', d, opt + 96 + 2 * 8)[0])
def entries(o):
    nn, ni = struct.unpack_from('<HH', d, o + 12)
    for k in range(nn + ni):
        name, ptr = struct.unpack_from('<II', d, o + 16 + 8 * k)
        yield name, ptr
def find(o, ident):
    for name, ptr in entries(o):
        if not name & 0x80000000 and name == ident:
            return ptr
for ident in (int(a, 0) for a in sys.argv[2:]):
    t = find(root, 6)
    blk = find(root + (t & 0x7fffffff), (ident >> 4) + 1)
    if blk is None:
        print(hex(ident), 'not found'); continue
    for _lang, leaf in entries(root + (blk & 0x7fffffff)):
        rva, size = struct.unpack_from('<II', d, root + leaf)
        p = off(rva)
        for i in range(ident & 15):
            p += 2 + 2 * struct.unpack_from('<H', d, p)[0]
        n = struct.unpack_from('<H', d, p)[0]
        print(hex(ident), repr(d[p + 2:p + 2 + 2 * n].decode('utf-16-le')))
        break
