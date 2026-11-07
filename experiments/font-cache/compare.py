#!/usr/bin/env python3
"""Require matching font enumeration/metrics between the two research runtimes."""
from pathlib import Path
import re
import sys
pattern = re.compile(r'mode=(\d+) round=(\d+) callbacks=(\d+).*checksum=([0-9a-f]+) errors=0')
def evidence(path):
    rows = [match.groups() for match in pattern.finditer(Path(path).read_text())]
    if len(rows) != 8:
        raise SystemExit('Missing/failed benchmark phases: '+path)
    return rows
if evidence(sys.argv[1]) != evidence(sys.argv[2]):
    raise SystemExit('Baseline and candidate font counts or text metrics differ')
print('All eight phases have equal enumeration counts and text-metric checksums.')
