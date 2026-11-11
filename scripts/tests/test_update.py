"""`dllmgr update` against a fake GitHub (no network) in a temporary HOME."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import update  # noqa: E402

DLLMGR = '#!/bin/sh\necho "fake dllmgr {}"\n'


def blob(data):
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()


def tree(files):
    """A recursive git tree listing of {path: (mode, data)}."""
    entries, dirs = [], set()
    for path, (mode, data) in files.items():
        parts = path.split('/')
        dirs.update('/'.join(parts[:i]) for i in range(1, len(parts)))
        entries.append(dict(path=path, mode=mode, type='commit' if mode == '160000' else 'blob',
                            sha=blob(data) if mode != '160000' else 'c' * 40))
    entries += [dict(path=d, mode='040000', type='tree', sha='d' * 40) for d in dirs]
    return entries


def commit_files(name, runtime='app-isolation-wine-11.0-v23', modules='faststone-v5'):
    index = dict(format=1, entries=[dict(kind='bundle', id='faststone-all', application='faststone',
                                         fixes=[], profiles=[dict(wine='wine-11.0', release=modules)])])
    return {
        'dllmgr': ('100755', DLLMGR.format(name).encode()),
        'scripts/install-version.sh': ('100755', (SCRIPTS / 'install-version.sh').read_bytes()),
        'scripts/private-runtime.json': ('100644', json.dumps(dict(release=runtime, sha256=name[0] * 64)).encode()),
        'catalog/index.json': ('100644', json.dumps(index).encode()),
        'patches/dllmgr-1.patch': ('100644', b'patch\n'),
        'experiments/huge.mp4': ('100644', b'not installed'),
        'README.md': ('100644', b'not installed'),
    }


class FakeGitHub:
    def __init__(self):
        self.commits = {}  # sha -> (tree sha, files)
        self.tip = None
        self.urls = []
        self.tamper = None

    def add(self, sha, files, tip=True):
        self.commits[sha] = (sha[::-1], files)
        if tip:
            self.tip = sha

    def fetch(self, url, accept=None):
        self.urls.append(url)
        if url == update.API + '/commits/main' or url.startswith(update.API + '/commits/'):
            ref = url.rsplit('/', 1)[1]
            sha = self.tip if ref == 'main' else next(s for s in self.commits if s.startswith(ref))
            return json.dumps(dict(sha=sha, commit=dict(tree=dict(sha=self.commits[sha][0])))).encode()
        if url.startswith(update.API + '/git/trees/'):
            tree_sha = url.split('/git/trees/')[1].split('?')[0]
            files = next(f for t, f in self.commits.values() if t == tree_sha)
            return json.dumps(dict(sha=tree_sha, truncated=False, tree=tree(files))).encode()
        if url.startswith(update.API + '/compare/'):
            return json.dumps(dict(ahead_by=3, behind_by=0)).encode()
        if url.startswith(update.RAW + '/'):
            sha, path = url[len(update.RAW) + 1:].split('/', 1)
            data = self.commits[sha][1][path][1]
            return self.tamper if self.tamper and path == 'scripts/private-runtime.json' else data
        raise AssertionError('unexpected URL ' + url)


class UpdateTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='dllmgr-update-test-')
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name) / 'home'
        self.home.mkdir()
        env = patch.dict(os.environ, HOME=str(self.home), XDG_STATE_HOME=str(self.home / 'state'),
                         XDG_DATA_HOME=str(self.home / 'data'), TMPDIR=tmp.name)
        env.start()
        self.addCleanup(env.stop)
        self.github = FakeGitHub()
        fetch = patch.object(update, 'fetch', self.github.fetch)
        fetch.start()
        self.addCleanup(fetch.stop)
        self.old, self.new = 'a' * 40, 'b' * 40
        self.github.add(self.old, commit_files('a', 'app-isolation-wine-11.0-v22', 'faststone-v4'))

    def run_update(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = update.main(list(argv))
        return code, out.getvalue()

    def link(self):
        return self.home / '.local/bin/dllmgr'

    def test_fresh_install_takes_only_the_installed_directories(self):
        code, out = self.run_update()
        self.assertEqual(code, 0)
        root = self.home / '.local/lib/dllmgr' / self.old
        self.assertEqual(Path(os.readlink(self.link())), root / 'dllmgr')
        self.assertTrue(os.access(root / 'dllmgr', os.X_OK))
        self.assertFalse(os.access(root / 'patches/dllmgr-1.patch', os.X_OK))
        self.assertEqual((root / '.dllmgr-revision').read_text().strip(), self.old)
        self.assertFalse((root / 'experiments').exists())
        self.assertFalse((root / 'README.md').exists())
        self.assertIn('Wine runtime: app-isolation-wine-11.0-v22', out)
        self.assertEqual(json.loads(update.stamp_path().read_text())['revision'], self.old)
        self.assertTrue((self.home / 'data/applications/dllmgr-fix.desktop').is_file())

    def test_update_reports_changed_pins_keeps_old_and_rolls_back_offline(self):
        self.run_update()
        self.github.add(self.new, commit_files('b'))
        code, out = self.run_update()
        self.assertEqual(code, 0)
        self.assertIn('dllmgr aaaaaaa -> bbbbbbb (3 new commits)', out)
        self.assertIn('Wine runtime: app-isolation-wine-11.0-v22 (sha256 aaaaaaaaaaaa) -> '
                      'app-isolation-wine-11.0-v23 (sha256 bbbbbbbbbbbb)', out)
        self.assertIn('modules faststone: faststone-v4 -> faststone-v5', out)
        self.assertEqual(self.link().resolve().parent.name, self.new)
        self.assertTrue((self.home / '.local/lib/dllmgr' / self.old / 'dllmgr').is_file())

        self.github.urls.clear()
        code, out = self.run_update('--revision', self.old[:7])
        self.assertEqual(code, 0)
        self.assertEqual(self.link().resolve().parent.name, self.old)
        self.assertFalse([u for u in self.github.urls if u.startswith(update.RAW)])
        self.assertNotIn('/commits/', ''.join(self.github.urls))
        self.assertEqual(json.loads(update.stamp_path().read_text())['revision'], self.new)

    def test_up_to_date_downloads_nothing(self):
        self.run_update()
        self.github.urls.clear()
        code, out = self.run_update()
        self.assertEqual(code, 0)
        self.assertIn('up to date: aaaaaaa', out)
        self.assertEqual(self.github.urls, [update.API + '/commits/main'])

    def test_tampered_file_installs_nothing(self):
        self.run_update()
        self.github.add(self.new, commit_files('b'))
        self.github.tamper = b'{"release": "evil"}'
        with self.assertRaisesRegex(update.Error, 'Checksum mismatch: scripts/private-runtime.json'), \
                contextlib.redirect_stdout(io.StringIO()):
            update.main([])
        self.assertEqual(self.link().resolve().parent.name, self.old)
        self.assertFalse((self.home / '.local/lib/dllmgr' / self.new).exists())

    def test_links_and_submodules_are_refused(self):
        for mode in ('120000', '160000'):
            files = commit_files('b')
            files['scripts/link'] = (mode, b'../../etc/passwd')
            self.github.add(self.new, files)
            with self.assertRaisesRegex(update.Error, 'Unsupported entry'), contextlib.redirect_stdout(io.StringIO()):
                update.main([])
            self.assertFalse(self.link().exists())

    def test_unmanaged_command_is_preserved(self):
        self.link().parent.mkdir(parents=True)
        self.link().write_text('mine\n')
        with self.assertRaisesRegex(update.Error, 'not managed'):
            update.main([])
        self.assertEqual(self.link().read_text(), 'mine\n')

    def test_install_sh_and_update_share_the_layout(self):
        # install.sh's core is the same script; a version it installed is reused.
        self.run_update()
        self.github.add(self.new, commit_files('b'))
        shutil.copytree(self.home / '.local/lib/dllmgr' / self.old, self.home / '.local/lib/dllmgr' / self.new)
        (self.home / '.local/lib/dllmgr' / self.new / '.dllmgr-revision').write_text(self.new + '\n')
        self.github.urls.clear()
        code, out = self.run_update()
        self.assertEqual(code, 0)
        self.assertIn('no download', out)
        self.assertFalse([u for u in self.github.urls if u.startswith(update.RAW)])


if __name__ == '__main__':
    unittest.main()
