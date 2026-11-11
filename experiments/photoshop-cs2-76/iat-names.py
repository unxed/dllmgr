#!/usr/bin/env python3
"""Print the imported function behind IAT slots of a PE32 file.
Usage: iat-names.py FILE.exe 0xVA [0xVA ...]   (no args after FILE: all slots)"""
import struct, sys
d = open(sys.argv[1], 'rb').read()
want = {int(a, 16) for a in sys.argv[2:]}
pe = struct.unpack_from('<I', d, 0x3c)[0]
nsec = struct.unpack_from('<H', d, pe + 6)[0]
osz = struct.unpack_from('<H', d, pe + 20)[0]
opt = pe + 24
base = struct.unpack_from('<I', d, opt + 28)[0]
secs = [struct.unpack_from('<8sIIII', d, opt + osz + i * 40) for i in range(nsec)]
def off(rva):
    for _n, vs, va, rs, ro in secs:
        if va <= rva < va + max(vs, rs):
            return rva - va + ro
    raise ValueError(hex(rva))
i = off(struct.unpack_from('<I', d, opt + 104)[0])
while True:
    ilt, _ts, _fc, name, iat = struct.unpack_from('<5I', d, i)
    i += 20
    if not name:
        break
    dll = d[off(name):].split(b'\0')[0].decode()
    t = ilt or iat
    k = 0
    while True:
        e = struct.unpack_from('<I', d, off(t) + 4 * k)[0]
        if not e:
            break
        va = base + iat + 4 * k
        if not want or va in want:
            fn = ('#%d' % (e & 0xffff)) if e & 0x80000000 else d[off(e) + 2:].split(b'\0')[0].decode()
            print(hex(va), dll, fn)
        k += 1
# delay imports (directory 13): attrs, name, hmod, IAT, INT, ... ; attrs bit 0 = RVAs
j = struct.unpack_from('<I', d, opt + 96 + 13 * 8)[0]
if j:
    j = off(j)
    while True:
        attrs, name, _hm, iat, intt = struct.unpack_from('<5I', d, j)
        j += 32
        if not name:
            break
        rv = (lambda x: x) if attrs & 1 else (lambda x: x - base)
        dll = d[off(rv(name)):].split(b'\0')[0].decode()
        k = 0
        while True:
            e = struct.unpack_from('<I', d, off(rv(intt)) + 4 * k)[0]
            if not e:
                break
            va = base + rv(iat) + 4 * k
            if not want or va in want:
                fn = ('#%d' % (e & 0xffff)) if e & 0x80000000 else d[off(rv(e)) + 2:].split(b'\0')[0].decode()
                print(hex(va), dll, '(delay)', fn)
            k += 1
