"""Retain relevant text evidence; no environment dumps or binary artifacts."""
from pathlib import Path
import re

root = Path('/tmp/opencode/opencode-owner-51a7')
dest = Path(__file__).resolve().parent / 'results'
for step in ('step1', 'step2', 'step3', 'step4'):
    source = root / step
    out = dest / step
    out.mkdir(parents=True, exist_ok=True)
    for name in ('fix.log', 'status.txt', 'launch.log', 'private-result.txt',
                 'windows-timed.log', 'windows.txt', 'start-time.txt'):
        path = source / name
        if path.exists():
            text = path.read_text(errors='replace')
            # Window-list hostnames are irrelevant to the investigation.
            if name.startswith('windows'):
                text = re.sub(r'(photoshop\.exe\.photoshop\.exe\s+)\S+', r'\1<host>', text)
            (out / name).write_text('\n'.join(line.rstrip() for line in text.splitlines()) + '\n')
    if (source / 'private.log').exists():
        (out / 'private.log').write_text((source / 'private.log').read_text(errors='replace'))
    path = source / 'stock-timed.log'
    if path.exists():
        lines = path.read_text(errors='replace').splitlines()
        selected = set()
        for i, line in enumerate(lines):
            if 'trampoline' in line or ('Call ' in line and any(
                    word in line for word in ('CreateMutexW', 'FindWindowW'))):
                selected.update(range(i, min(i + 2, len(lines))))
        (out / 'stock-excerpt.log').write_text('\n'.join(lines[i] for i in sorted(selected)) + '\n')
    path = source / 'trampoline-run.log'
    if path.exists():
        text = path.read_text(errors='replace')
        if step == 'step4':
            lines = text.splitlines()
            # Builtin provenance + the application startup/exit sequence.
            keep = [line for line in lines if 'build_module' in line or
                    '== attempt' in line or 'Call KERNEL32.CreateMutexW' in line or
                    'Ret  KERNEL32.CreateMutexW' in line or 'user32.FindWindowW(' in line or
                    'KERNEL32.ExitProcess(' in line or 'free_modref' in line]
            keep.append('Full source log VERSION.dll load count: ' + str(sum(
                'version.dll' in line.lower() and 'Loaded ' in line for line in lines)))
            text = '\n'.join(keep) + '\n'
        (out / 'trampoline-run.log').write_text(text)
