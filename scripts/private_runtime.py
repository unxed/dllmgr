"""Verify and assemble an application-private Wine overlay. Never edits base Wine."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import zipfile

WINE_COMMIT = 'db11d0fe6a169c457e23d007e20404643d067aa8'
OVERLAY = {
    'bin/wine': 'bin/wine',
    'i386-windows/ntdll.dll': 'lib/wine/i386-windows/ntdll.dll',
    'x86_64-windows/ntdll.dll': 'lib/wine/x86_64-windows/ntdll.dll',
    'x86_64-unix/ntdll.so': 'lib/wine/x86_64-unix/ntdll.so',
}
# Optional overlays: Unix modules a package may additionally replace. Each group
# is all-or-none because its members share internal structures (win32u.so and
# winex11.so share struct window_surface, changed by patches/winehq-60721.patch).
OPTIONAL_GROUPS = (
    {
        'x86_64-unix/win32u.so': 'lib/wine/x86_64-unix/win32u.so',
        'x86_64-unix/winex11.so': 'lib/wine/x86_64-unix/winex11.so',
    },
    {   # #65: shell32 with the desktop.ini miss cache (patches/dllmgr-65.patch);
        # 32-bit only (Photoshop CS2), a 64-bit process keeps the base one
        'i386-windows/shell32.dll': 'lib/wine/i386-windows/shell32.dll',
    },
    {   # #74: sane.ds Unix side lists TWAIN sources from a device cache (patches/dllmgr-74-sane.patch)
        'x86_64-unix/sane.so': 'lib/wine/x86_64-unix/sane.so',
    },
    {   # #78: wineserver z-order rule for a non-topmost window put after a
        # topmost one (patches/dllmgr-78.patch); same protocol as the base
        'bin/wineserver': 'bin/wineserver',
    },
)
UNIX_MODES = {'bin/wine', 'x86_64-unix/ntdll.so', 'x86_64-unix/win32u.so', 'x86_64-unix/winex11.so', 'x86_64-unix/sane.so', 'bin/wineserver'}


class Error(RuntimeError):
    pass


def digest(path, progress=None):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
            if progress:
                progress.update(len(block))
    return h.hexdigest()


def _copy(src, dest, progress):
    """shutil.copy2 with progress (same bytes, mode and times)."""
    with open(src, 'rb') as fin, open(dest, 'wb') as fout:
        for block in iter(lambda: fin.read(1024 * 1024), b''):
            fout.write(block)
            progress.update(len(block))
    shutil.copystat(src, dest)


def valid_sha(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def overlay_for(manifest):
    """OVERLAY plus every optional group the package ships (validated in package_manifest)."""
    overlay = dict(OVERLAY)
    files = manifest.get('files', {})
    for group in OPTIONAL_GROUPS:
        if set(group) <= set(files):
            overlay.update(group)
    return overlay


def verify_base(base, manifest):
    expected = manifest.get('base_files')
    if not isinstance(expected, dict) or set(expected) != set(overlay_for(manifest).values()):
        raise Error('Runtime package has an incomplete base-Wine fingerprint')
    for name, checksum in expected.items():
        if not valid_sha(checksum) or digest(base / name) != checksum:
            raise Error('Unsupported or changed base Wine: ' + name)


def package_manifest(package):
    with zipfile.ZipFile(package) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or sum(i.file_size for i in archive.infolist()) > 150 * 1024 * 1024:
            raise Error('Invalid or oversized private-runtime package')
        for name in names:
            path = PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or str(path) != name:
                raise Error('Unsafe runtime archive member')
        manifest = json.loads(archive.read('manifest.json'))
        if manifest.get('schema') != 1 or manifest.get('wine_commit') != WINE_COMMIT or manifest.get('wine_version') != 'wine-11.0':
            raise Error('Unsupported private runtime')
        files = manifest.get('files', {})
        if not isinstance(files, dict) or set(files) != set(names) - {'manifest.json'} or not set(OVERLAY) <= set(files):
            raise Error('Incomplete runtime manifest')
        for group in OPTIONAL_GROUPS:
            if set(group) & set(files) and not set(group) <= set(files):
                raise Error('Partial optional overlay group: ' + ', '.join(sorted(set(group) - set(files))))
        for name, checksum in files.items():
            if not valid_sha(checksum) or hashlib.sha256(archive.read(name)).hexdigest() != checksum:
                raise Error('Runtime package checksum mismatch: ' + name)
    return manifest


def verify(runtime, package_sha, base, progress=None):
    state = json.loads((runtime / '.dllmgr-runtime.json').read_text())
    if state.get('package_sha256') != package_sha or state.get('base') != str(base):
        raise Error('Private runtime ownership record changed')
    manifest = state['manifest']
    verify_base(base, manifest)
    for name, checksum in state.get('copied_files', {}).items():
        path = runtime / name
        if path.is_symlink() or digest(path, progress) != checksum:
            raise Error('Private runtime changed: ' + name)
    for source, dest in overlay_for(manifest).items():
        path = runtime / dest
        if path.is_symlink() or digest(path) != manifest['files'][source]:
            raise Error('Private runtime changed: ' + dest)
    return runtime


def assemble(package, base, cache, progress=None):
    """progress: optional factory progress(label, total_bytes) -> object with
    update(n) and close() (scripts/ui.py Progress); None = silent."""
    base = base.resolve(strict=True)
    package_sha = digest(package)
    manifest = package_manifest(package)
    verify_base(base, manifest)
    # Include the base path: two equal installations may later be upgraded separately.
    key = hashlib.sha256((package_sha + str(base)).encode()).hexdigest()
    runtime = cache / key
    if runtime.exists():
        return verify(runtime, package_sha, base)
    cache.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.runtime-', dir=cache))
    try:
        # Unix modules must be real files: realpath(ntdll.so) determines Wine's
        # module directory. Large unchanged PE modules can be read-only links.
        copies = []
        for root, dirs, files in os.walk(base, followlinks=True):
            relative = Path(root).relative_to(base)
            target = stage / relative
            target.mkdir(parents=True, exist_ok=True)
            for name in files:
                src, dest = Path(root) / name, target / name
                if not src.is_file():
                    continue
                if relative.parts and (relative.parts[0] == 'bin' or relative.name.endswith('-unix')):
                    copies.append((src, dest))
                else:
                    dest.symlink_to(src.resolve())
        total = sum(src.stat().st_size for src, _ in copies)
        bar = progress(f'Building private runtime: copying {len(copies)} Wine Unix files from {base}', total) if progress else None
        for src, dest in copies:
            if bar:
                _copy(src, dest, bar)
            else:
                shutil.copy2(src, dest)
        if bar:
            bar.close()
        with zipfile.ZipFile(package) as archive:
            for source, dest in overlay_for(manifest).items():
                path = stage / dest
                path.unlink(missing_ok=True)  # Never write through a link into /opt.
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(archive.read(source))
                path.chmod(0o755 if source in UNIX_MODES else 0o644)
        files = [p for p in stage.rglob('*') if p.is_file() and not p.is_symlink()]
        bar = progress(f'Verifying private runtime: sha256 of {len(files)} files', 2 * sum(p.stat().st_size for p in files)) if progress else None
        copied = {str(p.relative_to(stage)): digest(p, bar) for p in files}
        (stage / '.dllmgr-runtime.json').write_text(json.dumps(dict(
            package_sha256=package_sha, base=str(base), manifest=manifest,
            copied_files=copied), sort_keys=True) + '\n')
        verify(stage, package_sha, base, bar)
        if bar:
            bar.close()
        stage.rename(runtime)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return runtime
