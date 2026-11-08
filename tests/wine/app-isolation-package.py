#!/usr/bin/env python3
"""Package the tested overlay; complete modified Wine source ships separately."""
import hashlib
import json
from pathlib import Path
import zipfile

root = Path('out/isolation')
files = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
         for p in sorted(root.rglob('*')) if p.is_file()
         and p.name not in {'SHA256SUMS', 'manifest.json'}}
base = {}
for line in (root / 'BASE-SHA256SUMS').read_text().splitlines():
    digest, name = line.split(maxsplit=1)
    base[name] = digest
manifest = {'schema': 1, 'wine_commit': 'db11d0fe6a169c457e23d007e20404643d067aa8',
            'wine_version': 'wine-11.0', 'files': files, 'base_files': base}
(root / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
with zipfile.ZipFile('out/wine-11.0-app-isolation.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(root.rglob('*')):
        if path.is_file() and path.name != 'SHA256SUMS':
            archive.write(path, str(path.relative_to(root)))
