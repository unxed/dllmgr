#!/usr/bin/env python3
"""Summarise a dllmgr-sample-<pid>.txt (DLLMGR_SAMPLE=ms[,seconds] in the
dllmgr-27 proxy): Wine syscall stubs named from the win32u/ntdll exports.
usage: sample-report.py SAMPLES [WINE_LIB_DIR] [--from MS] [--to MS]"""
import argparse, bisect, collections, os
import pefile
ap = argparse.ArgumentParser()
ap.add_argument('samples'); ap.add_argument('libdir', nargs='?', default='/opt/wine-stable/lib/wine/i386-windows')
ap.add_argument('--from', dest='lo', type=int, default=0); ap.add_argument('--to', dest='hi', type=int, default=1 << 30)
a = ap.parse_args()
exports = {}
def name(frame):
    mod, _, off = frame.partition('+')
    if not off or mod.lower() not in ('win32u.dll', 'ntdll.dll'):
        return frame
    if mod not in exports:
        pe = pefile.PE(os.path.join(a.libdir, mod.lower()), fast_load=True)
        pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXPORT']])
        exports[mod] = sorted((e.address, (e.name or b'?').decode()) for e in pe.DIRECTORY_ENTRY_EXPORT.symbols)
    ex = exports[mod]; o = int(off, 16)
    i = bisect.bisect_right([x for x, _ in ex], o) - 1
    return mod + ':' + ex[i][1] if i >= 0 else frame
rows = [l.split() for l in open(a.samples) if l.strip()]
rows = [r for r in rows if a.lo <= int(r[0]) < a.hi]
top = collections.Counter(name(r[1]) for r in rows)
print('%d samples' % len(rows))
for f, c in top.most_common(20):
    print('%5d %5.1f%%  %s' % (c, 100.0 * c / len(rows), f))
