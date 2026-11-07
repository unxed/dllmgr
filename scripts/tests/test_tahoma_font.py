import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('tahoma', Path(__file__).parents[1]/'tahoma-font.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class FontTransactionTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.prefix = Path(self.temp.name)/'prefix'
        self.prefix.mkdir()
        self.source = Path(self.temp.name)/'font.ttf'
        self.source.write_bytes(b'\0\1\0\0'+b'fixture-font')
        self.notices = Path(self.temp.name)/'notices.txt'
        self.notices.write_text('Fixture license notices')

    def apply(self):
        return m.apply(self.prefix, self.source, self.notices)

    def test_idempotent_apply_and_undo_preserve_other_fonts(self):
        other = self.prefix/m.FONT.parent/'tahomabd.ttf'
        other.parent.mkdir(parents=True)
        other.write_bytes(b'preexisting font')
        self.assertEqual(self.apply(), 'installed')
        self.assertEqual(self.apply(), 'already installed')
        m.undo(self.prefix)
        self.assertEqual(other.read_bytes(), b'preexisting font')
        self.assertFalse((self.prefix/m.FONT).exists())
        self.assertFalse((self.prefix/m.NOTICES).exists())
        self.assertFalse((self.prefix/m.STATE).exists())

    def test_refuses_existing_unmanaged_file(self):
        target = self.prefix/m.FONT
        target.parent.mkdir(parents=True)
        target.write_bytes(b'not ours')
        with self.assertRaisesRegex(m.Error, 'without managed state'):
            self.apply()
        self.assertEqual(target.read_bytes(), b'not ours')

    def test_external_change_prevents_undo(self):
        self.apply()
        (self.prefix/m.FONT).write_bytes(b'changed externally')
        with self.assertRaisesRegex(m.Error, 'changed outside'):
            m.undo(self.prefix)
        self.assertTrue((self.prefix/m.STATE).exists())
        self.assertTrue((self.prefix/m.NOTICES).exists())

    def test_partial_write_failure_restores_absence(self):
        real_atomic = m.atomic
        def fail_notices(path, data, mode=0o644):
            if path == self.prefix/m.NOTICES:
                raise OSError('injected disk failure')
            real_atomic(path, data, mode)
        with patch.object(m, 'atomic', side_effect=fail_notices):
            with self.assertRaisesRegex(OSError, 'injected disk failure'):
                self.apply()
        self.assertFalse((self.prefix/m.FONT).exists())
        self.assertFalse((self.prefix/m.NOTICES).exists())
        self.assertFalse((self.prefix/m.STATE).exists())

    def test_pending_partial_install_can_be_undone(self):
        self.apply()
        path = self.prefix/m.STATE
        state = json.loads(path.read_text())
        state['phase'] = 'pending'
        path.write_text(json.dumps(state))
        (self.prefix/m.NOTICES).unlink()
        m.undo(self.prefix)
        self.assertFalse(path.exists())
        self.assertFalse((self.prefix/m.FONT).exists())

    def test_tampered_state_cannot_remove_other_files(self):
        self.apply()
        path = self.prefix/m.STATE
        state = json.loads(path.read_text())
        state['files']['drive_c/other.ttf'] = 'not allowed'
        path.write_text(json.dumps(state))
        with self.assertRaisesRegex(m.Error, 'paths'):
            m.undo(self.prefix)
        self.assertTrue((self.prefix/m.FONT).exists())


if __name__ == '__main__':
    unittest.main()
