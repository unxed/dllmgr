"""`dllmgr upgrade` plans and outcomes on fake prefixes (no Wine, no network)."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import upgrade  # noqa: E402

private_app = upgrade.private_app
PIN = json.loads((SCRIPTS / 'private-runtime.json').read_text())
MODULES = upgrade.catalog_fixes.release('faststone', 'wine-11.0')
NOW, OLD = 'b' * 40, 'a' * 40
REAPPLY = upgrade.reapply
PROCESS_PREFIX = upgrade.process_prefix


class UpgradeTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='dllmgr-upgrade-test-')
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        env = patch.dict(os.environ, HOME=str(self.root / 'home'), XDG_STATE_HOME=str(self.root / 'state'))
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop('WINEPREFIX', None)
        self.prefix = self.make_prefix('prefix')
        self.running = {}
        for name, value in [('dllmgr_revision', lambda: NOW),
                            ('running_on', lambda exe: self.running.get(exe, []))]:
            p = patch.object(private_app, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.where = {}
        p = patch.object(upgrade, 'process_prefix', lambda pid: self.where.get(pid))
        p.start()
        self.addCleanup(p.stop)
        self.calls = []
        self.results = {}
        p = patch.object(upgrade, 'reapply', self.fake_reapply)
        p.start()
        self.addCleanup(p.stop)
        self.stamp()

    def stamp(self, age=0):
        path = self.root / 'state/dllmgr/last-update.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(dict(time=int(time.time()) - age, revision=NOW)))

    def make_prefix(self, name):
        prefix = self.root / name
        (prefix / 'drive_c').mkdir(parents=True)
        (prefix / 'dosdevices').mkdir()
        (prefix / 'dosdevices/c:').symlink_to('../drive_c')
        (prefix / 'system.reg').write_text('WINE REGISTRY Version 2\n#arch=win64\n')
        return prefix.resolve()

    def add(self, app, exe_name, prefix=None, **fields):
        prefix = prefix or self.prefix
        exe = prefix / 'drive_c/app' / app / exe_name
        exe.parent.mkdir(parents=True, exist_ok=True)
        exe.write_bytes(b'MZ')
        target = 'C:\\app\\' + app + '\\' + exe_name
        ident = private_app.app_id(target, app)
        state = dict(schema=1, phase='installed', id=ident, prefix=str(prefix), exe=str(exe), target=target,
                     exe_sha256='e' * 64, fix='faststone' if app == 'faststone' else app,
                     release=MODULES if app == 'faststone' else None, generation='0' * 64,
                     files={}, runtime='/r', base='/opt/wine-stable', package_sha256=PIN['sha256'],
                     desktops=[], runtime_release=PIN['release'], dllmgr_revision=NOW)
        if app != 'faststone':
            state['app'] = app
        state.update(fields)
        path = prefix / '.dllmgr/apps' / (ident + '.json')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state))
        return path

    def fake_reapply(self, app, prefix, state):
        self.calls.append(app)
        code = self.results.get(app, 0)
        if code == 0:  # what private-app.py install leaves behind
            path = prefix / '.dllmgr/apps' / (state['id'] + '.json')
            path.write_text(json.dumps(dict(state, package_sha256=PIN['sha256'], runtime_release=PIN['release'],
                                            release=MODULES if app == 'faststone' else None,
                                            dllmgr_revision=NOW, phase='installed')))
        return code

    def run_upgrade(self, *argv, answer=None):
        out = io.StringIO()
        stdin = io.StringIO(answer) if answer is not None else io.StringIO('')
        with contextlib.redirect_stdout(out), patch('sys.stdin', stdin):
            code = upgrade.main(['--prefix', str(self.prefix), *argv])
        return code, out.getvalue()

    def test_up_to_date_apps_are_left_alone(self):
        self.add('faststone', 'FSViewer.exe')
        self.add('photoshop-cs2', 'Photoshop.exe')
        code, out = self.run_upgrade('--yes')
        self.assertEqual(code, 0)
        self.assertEqual(self.calls, [])
        self.assertIn('0 to upgrade, 2 up to date, 0 held back.', out)
        self.assertNotIn('Note:', out)

    def test_plan_lists_each_change_and_dry_run_changes_nothing(self):
        self.add('faststone', 'FSViewer.exe', release='faststone-v1')
        self.add('photoshop-cs2', 'Photoshop.exe', package_sha256='1' * 64,
                 runtime_release='app-isolation-wine-11.0-v22')
        del_rev = self.add('photoshop-cs2', 'Photoshop2.exe')
        state = json.loads(del_rev.read_text())
        del state['dllmgr_revision']
        del_rev.write_text(json.dumps(state))
        code, out = self.run_upgrade('--dry-run')
        self.assertEqual(code, 0)
        self.assertEqual(self.calls, [])
        self.assertIn('modules faststone-v1 -> ' + MODULES, out)
        self.assertIn('runtime app-isolation-wine-11.0-v22 (sha256 111111111111) -> ' + PIN['release'] +
                      ' (sha256 ' + PIN['sha256'][:12] + ')', out)
        self.assertIn('dllmgr unknown (fixed by an older dllmgr) -> bbbbbbb', out)
        self.assertIn('3 to upgrade, 0 up to date', out)

    def test_yes_reapplies_and_one_failure_does_not_stop_the_others(self):
        self.add('faststone', 'FSViewer.exe', dllmgr_revision=OLD)
        self.add('photoshop-cs2', 'Photoshop.exe', dllmgr_revision=OLD)
        self.results['faststone'] = 1
        code, out = self.run_upgrade('--yes')
        self.assertEqual(code, 1)
        self.assertEqual(self.calls, ['faststone', 'photoshop-cs2'])
        self.assertIn('faststone: upgrade failed (exit 1); its previous fix stays in place', out)
        self.assertIn('Upgraded: photoshop-cs2; failed: faststone in ' + str(self.prefix), out)
        code, out = self.run_upgrade('--dry-run')
        self.assertIn('1 to upgrade, 1 up to date', out)

    def test_answer_decides(self):
        self.add('photoshop-cs2', 'Photoshop.exe', dllmgr_revision=OLD)
        for answer in ('n\n', ''):  # "no" and end of input
            code, out = self.run_upgrade(answer=answer)
            self.assertEqual((code, self.calls), (0, []))
            self.assertIn('Nothing changed.', out)
        code, out = self.run_upgrade(answer='y\n')
        self.assertEqual(self.calls, ['photoshop-cs2'])
        self.assertIn('✓ Upgraded: photoshop-cs2', out)

    def test_running_and_local_package_apps_are_held_back(self):
        self.add('photoshop-cs2', 'Photoshop.exe', dllmgr_revision=OLD)
        self.add('faststone', 'FSViewer.exe', package_sha256='1' * 64, runtime_release='local package /x.zip')
        self.running['Photoshop.exe'] = [(4242, 'private runtime'), (4343, 'private runtime')]
        self.where = {4242: self.prefix, 4343: self.root / 'elsewhere'}
        code, out = self.run_upgrade('--yes')
        self.assertEqual((code, self.calls), (0, []))
        self.assertIn('held back: running (pid 4242); close it', out)
        self.assertIn('held back: installed from a local runtime package', out)
        self.assertIn('0 to upgrade, 0 up to date, 2 held back.', out)

    def test_default_and_several_prefixes(self):
        second = self.make_prefix('second')
        self.add('photoshop-cs2', 'Photoshop.exe', prefix=second, dllmgr_revision=OLD)
        out = io.StringIO()
        with contextlib.redirect_stdout(out), patch.dict(os.environ, WINEPREFIX=str(second)):
            self.assertEqual(upgrade.main(['--dry-run']), 0)
        self.assertIn('Prefix ' + str(second), out.getvalue())
        code, out = self.run_upgrade('--prefix', str(second), '--yes')
        self.assertIn('no apps fixed by dllmgr here', out)
        self.assertEqual(self.calls, ['photoshop-cs2'])
        code, out = self.run_upgrade('--prefix', str(self.root / 'missing'))
        self.assertEqual(code, 1)
        self.assertIn('not a Wine prefix', out)

    def test_the_same_app_running_in_another_prefix_does_not_hold_back(self):
        self.add('photoshop-cs2', 'Photoshop.exe', dllmgr_revision=OLD)
        self.running['Photoshop.exe'] = [(4343, 'private runtime')]
        self.where = {4343: self.root / 'elsewhere'}
        code, out = self.run_upgrade('--yes')
        self.assertEqual(self.calls, ['photoshop-cs2'])

    def test_process_prefix_reads_wineprefix_or_home(self):
        proc = self.root / 'proc'
        for pid, env in [(1, b'HOME=/h\0WINEPREFIX=/p/x\0'), (2, b'HOME=/h\0'), (3, b'')]:
            (proc / str(pid)).mkdir(parents=True)
            (proc / str(pid) / 'environ').write_bytes(env)
        self.assertEqual(PROCESS_PREFIX(1, proc), Path('/p/x'))
        self.assertEqual(PROCESS_PREFIX(2, proc), Path('/h/.wine'))
        self.assertIsNone(PROCESS_PREFIX(3, proc))
        self.assertIsNone(PROCESS_PREFIX(4, proc))

    def test_unreadable_journal_is_reported(self):
        path = self.add('faststone', 'FSViewer.exe')
        path.write_text('{broken')
        code, out = self.run_upgrade('--yes')
        self.assertEqual(code, 1)
        self.assertIn('unreadable', out)

    def test_stale_or_missing_update_is_noted(self):
        self.stamp(age=10 * 86400)
        self.assertIn('10 days ago', self.run_upgrade('--dry-run')[1])
        (self.root / 'state/dllmgr/last-update.json').unlink()
        self.assertIn('has not been run here', self.run_upgrade('--dry-run')[1])

    def test_reapply_runs_fix_with_the_recorded_installation(self):
        path = self.add('faststone', 'FSViewer.exe', fix='winehq-59609', base='/opt/other-wine')
        state = json.loads(path.read_text())
        with patch.object(upgrade.subprocess, 'run') as run:
            run.return_value.returncode = 0
            REAPPLY('faststone', self.prefix, state)  # the real one, not the fake
        command = run.call_args[0][0]
        self.assertEqual(command[1:], [str(SCRIPTS / 'private-app.py'), 'install', '--app', 'faststone',
                                       '--prefix', str(self.prefix), '--exe', state['exe'],
                                       '--fix', 'winehq-59609', '--base-wine', '/opt/other-wine'])


if __name__ == '__main__':
    unittest.main()
