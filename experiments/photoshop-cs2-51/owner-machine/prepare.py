"""Relocate only the disposable prefix's dllmgr metadata before recipe setup."""
import hashlib
import json
import os
from pathlib import Path

root = Path('/tmp/opencode/opencode-owner-51a7')
prefix = root / 'prefix'
source = str(Path.home() / '.wine')
assert prefix.is_dir() and not prefix.is_symlink()
for path in (prefix / '.dllmgr/apps').glob('*.json'):
    state = json.loads(path.read_text())
    state['exe'] = state['exe'].replace(source, str(prefix), 1)
    state['prefix'] = str(prefix)
    # Never route or rewrite the owner's actual desktop entries.
    state['desktops'] = []
    path.write_text(json.dumps(state, indent=2) + '\n')
for path in list((prefix / '.dllmgr/prefill').glob('*.json')):
    state = json.loads(path.read_text())
    for key in ('exe', 'target'):
        state[key] = state[key].replace(source, str(prefix), 1)
    relocated = path.parent / (hashlib.sha256(state['exe'].encode()).hexdigest()[:16] + '.json')
    relocated.write_text(json.dumps(state, indent=2) + '\n')
    if relocated != path:
        path.unlink()
# Personal-folder symlinks must not allow app writes outside the copy.
for path in (prefix / 'drive_c/users').rglob('*'):
    if path.is_symlink() and os.readlink(path).startswith('/home/unxed/'):
        path.unlink()
        path.mkdir()
data = root / 'data'
(data / 'dllmgr').mkdir(parents=True, exist_ok=True)
(data / 'dllmgr/runtimes').symlink_to(Path.home() / '.local/share/dllmgr/runtimes')
# Historical owner logs are not evidence of this experiment.
for name in ('launch.log', 'trampoline-run.log'):
    (prefix / '.dllmgr' / name).unlink(missing_ok=True)
print('Copy metadata relocated; desktop output isolated; historical launch logs removed.')
