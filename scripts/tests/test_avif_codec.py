import importlib.util
import json
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest

SPEC = importlib.util.spec_from_file_location('avif_manager', Path(__file__).parents[1]/'avif-codec.py')
m = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(m)


class Registry:
    def __init__(self):
        self.keys = {}; self.installs = 0; self.fail = False
    def exists(self, key): return key in self.keys
    def snapshot(self, key): return self.keys.get(key)
    def install(self):
        self.installs += 1
        for i, key in enumerate(m.ROOTS):
            self.keys[key] = 'hash-'+str(i)
            if self.fail: raise m.Error('injected import failure')
    def remove(self):
        for key in m.ROOTS: self.keys.pop(key, None)


class AvifTransactionTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.prefix = Path(self.temp.name); self.reg = Registry()
        data = bytearray(128); data[:2] = b'MZ'; struct.pack_into('<I', data, 60, 64)
        data[64:68] = b'PE\0\0'; struct.pack_into('<H', data, 68, 0x14c)
        self.dll = self.prefix/'source.dll'; self.dll.write_bytes(data)
        self.dll.with_name(m.NOTICES.name).write_text('Test-only license notices.\n')
    def install(self): return m.apply(self.prefix, self.dll, self.reg)
    def test_install_is_idempotent_and_undo_restores_absence(self):
        self.assertEqual(self.install(), 'installed')
        self.assertEqual(self.install(), 'already installed')
        self.assertEqual(self.reg.installs, 1)
        m.undo(self.prefix, self.reg)
        self.assertEqual(self.reg.keys, {})
        self.assertFalse((self.prefix/m.DLL).exists())
        self.assertFalse((self.prefix/m.STATE).exists())
        self.assertFalse((self.prefix/m.NOTICES).exists())
    def test_partial_registry_failure_rolls_back_files_state_and_keys(self):
        self.reg.fail = True
        with self.assertRaisesRegex(m.Error, 'injected'): self.install()
        self.assertEqual(self.reg.keys, {})
        self.assertFalse((self.prefix/m.DLL).exists())
        self.assertFalse((self.prefix/m.STATE).exists())
    def test_existing_machine_or_user_registration_is_not_overwritten(self):
        key = m.ROOTS[0].replace('HKLM\\Software\\Classes', 'HKCR', 1)
        self.reg.keys[key] = 'other-owner'
        with self.assertRaisesRegex(m.Error, 'already exists'): self.install()
        self.assertEqual(self.reg.keys, {key: 'other-owner'})
        self.assertFalse((self.prefix/m.STATE).exists())
    def test_changed_registry_prevents_uninstall(self):
        self.install(); self.reg.keys[m.ROOTS[0]] = 'external-change'
        before = dict(self.reg.keys)
        with self.assertRaisesRegex(m.Error, 'registration changed'): m.undo(self.prefix, self.reg)
        self.assertEqual(self.reg.keys, before)
        self.assertTrue((self.prefix/m.DLL).exists())
    def test_changed_dll_prevents_uninstall(self):
        self.install(); (self.prefix/m.DLL).write_bytes(b'external-change')
        with self.assertRaisesRegex(m.Error, 'DLL changed'): m.undo(self.prefix, self.reg)
        self.assertEqual((self.prefix/m.DLL).read_bytes(), b'external-change')
        self.assertTrue(self.reg.keys)
    def test_changed_notices_prevent_uninstall(self):
        self.install(); (self.prefix/m.NOTICES).write_text('external change')
        with self.assertRaisesRegex(m.Error, 'notices changed'): m.undo(self.prefix, self.reg)
        self.assertTrue((self.prefix/m.DLL).exists())
        self.assertTrue(self.reg.keys)
    def test_missing_notices_do_not_install(self):
        self.dll.with_name(m.NOTICES.name).unlink()
        with self.assertRaises(FileNotFoundError): self.install()
        self.assertFalse((self.prefix/m.STATE).exists())
        self.assertFalse(self.reg.keys)
    def test_pending_install_can_be_recovered(self):
        self.install(); state_path = self.prefix/m.STATE
        state = json.loads(state_path.read_text()); state['phase'] = 'pending'
        state_path.write_text(json.dumps(state)); self.reg.keys.pop(m.ROOTS[1])
        m.undo(self.prefix, self.reg)
        self.assertFalse(state_path.exists()); self.assertEqual(self.reg.keys, {})
    def test_invalid_pe_does_not_change_anything(self):
        self.dll.write_bytes(b'not a PE')
        with self.assertRaisesRegex(m.Error, 'x86 PE'): self.install()
        self.assertFalse((self.prefix/m.STATE).exists()); self.assertEqual(self.reg.keys, {})


if __name__ == '__main__': unittest.main()
