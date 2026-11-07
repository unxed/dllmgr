#!/usr/bin/env python3
"""Package an AVIF CI artifact, preserving all dependency notices."""
import argparse
import hashlib
from pathlib import Path
import zipfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('artifact', type=Path)
parser.add_argument('output', type=Path)
args = parser.parse_args()
artifact = args.artifact.resolve()
for line in (artifact/'SHA256SUMS.txt').read_text(encoding='utf-8-sig').splitlines():
    digest, name = line.split(None, 1)
    path = artifact/name.replace('\\', '/')
    if not path.resolve().is_relative_to(artifact):
        raise SystemExit('Invalid artifact path')
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise SystemExit('Artifact checksum mismatch: '+name)
if 'Failures: 0' not in (artifact/'test-results.txt').read_text(encoding='utf-8-sig'):
    raise SystemExit('Expected successful WIC self-test evidence')
files = {str(p.relative_to(artifact)).replace('\\', '/'): p.read_bytes()
         for p in sorted(artifact.rglob('*')) if p.is_file()}
license_files = ['NOTICE.md'] + sorted(name for name in files if name.startswith('licenses/'))
notices = []
for name in license_files:
    notices.append(('\n===== '+name+' =====\n').encode()+files[name]+b'\n')
files['THIRD-PARTY-NOTICES.txt'] = b''.join(notices)
files.pop('SHA256SUMS.txt')
files['SHA256SUMS.txt'] = ''.join(hashlib.sha256(data).hexdigest()+'  '+name+'\n'
                                for name, data in sorted(files.items())).encode()
args.output.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(args.output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    for name, data in sorted(files.items()):
        info = zipfile.ZipInfo(name, date_time=(2026, 11, 7, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        archive.writestr(info, data)
print(hashlib.sha256(args.output.read_bytes()).hexdigest()+'  '+args.output.name)
