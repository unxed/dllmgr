import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "prefill_proxy", Path(__file__).resolve().parent.parent / "prefill-proxy.py")
pp = importlib.util.module_from_spec(spec)
sys.modules["prefill_proxy"] = pp
spec.loader.exec_module(pp)


class FakeRegistry:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def get(self, key, name):
        return self.values.get((key, name))

    def set(self, key, name, value):
        self.values[(key, name)] = value

    def delete(self, key, name):
        self.values.pop((key, name), None)


class PrefillProxyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.prefix = root / "prefix"
        (self.prefix).mkdir()
        (self.prefix / "system.reg").write_text("")
        self.app = root / "app"
        self.app.mkdir()
        self.exe = self.app / "Photoshop.exe"
        self.exe.write_bytes(b"MZexe")
        self.dll = root / "version.dll"
        self.dll.write_bytes(b"MZproxy")
        self.key = pp.key_for(self.exe)

    def tearDown(self):
        self.tmp.cleanup()

    def test_apply_status_undo_restores_absent_override(self):
        reg = FakeRegistry()
        self.assertEqual(pp.apply(self.prefix, self.exe, "version", self.dll, reg), "installed")
        self.assertEqual((self.app / "version.dll").read_bytes(), b"MZproxy")
        self.assertEqual(reg.get(self.key, "version"), "native,builtin")
        self.assertIn("AppDefaults\\Photoshop.exe\\DllOverrides", self.key)
        pp.check(self.prefix, self.exe, reg)
        self.assertEqual(pp.apply(self.prefix, self.exe, "version", self.dll, reg), "already installed")
        pp.undo(self.prefix, self.exe, reg)
        self.assertFalse((self.app / "version.dll").exists())
        self.assertIsNone(reg.get(self.key, "version"))
        with self.assertRaises(pp.Error):
            pp.load(self.prefix, self.exe)

    def test_undo_restores_previous_override(self):
        reg = FakeRegistry({(self.key, "version"): "builtin"})
        pp.apply(self.prefix, self.exe, "version", self.dll, reg)
        pp.undo(self.prefix, self.exe, reg)
        self.assertEqual(reg.get(self.key, "version"), "builtin")

    def test_refuses_unmanaged_existing_dll_and_non_pe(self):
        reg = FakeRegistry()
        (self.app / "version.dll").write_bytes(b"MZsomeone else's")
        with self.assertRaisesRegex(pp.Error, "not managed"):
            pp.apply(self.prefix, self.exe, "version", self.dll, reg)
        (self.app / "version.dll").unlink()
        bad = self.dll.with_name("bad.dll")
        bad.write_bytes(b"ELF")
        with self.assertRaisesRegex(pp.Error, "PE DLL"):
            pp.apply(self.prefix, self.exe, "version", bad, reg)
        self.assertEqual(reg.values, {})

    def test_tampering_is_detected_and_not_deleted(self):
        reg = FakeRegistry()
        pp.apply(self.prefix, self.exe, "version", self.dll, reg)
        (self.app / "version.dll").write_bytes(b"MZchanged")
        with self.assertRaisesRegex(pp.Error, "changed"):
            pp.check(self.prefix, self.exe, reg)
        with self.assertRaisesRegex(pp.Error, "changed outside"):
            pp.undo(self.prefix, self.exe, reg)
        self.assertTrue((self.app / "version.dll").exists())

    def test_override_change_is_detected(self):
        reg = FakeRegistry()
        pp.apply(self.prefix, self.exe, "version", self.dll, reg)
        reg.set(self.key, "version", "builtin")
        with self.assertRaisesRegex(pp.Error, "override changed"):
            pp.check(self.prefix, self.exe, reg)

    def test_companion_installed_checked_and_removed(self):
        reg = FakeRegistry()
        line = '"Z:\\opt\\dllmgr\\dllmgr" run faststone --'
        self.assertEqual(pp.apply(self.prefix, self.exe, "version", self.dll, reg, line), "installed")
        extra = self.app / "version.dllmgr"
        self.assertEqual(extra.read_text(), line + "\n")
        pp.check(self.prefix, self.exe, reg)
        self.assertEqual(pp.apply(self.prefix, self.exe, "version", self.dll, reg, line), "already installed")
        with self.assertRaisesRegex(pp.Error, "Another"):
            pp.apply(self.prefix, self.exe, "version", self.dll, reg, line + " x")
        extra.write_text("changed\n")
        with self.assertRaisesRegex(pp.Error, "companion changed"):
            pp.check(self.prefix, self.exe, reg)
        with self.assertRaisesRegex(pp.Error, "companion was changed"):
            pp.undo(self.prefix, self.exe, reg)
        extra.write_text(line + "\n")
        pp.undo(self.prefix, self.exe, reg)
        self.assertFalse(extra.exists())
        self.assertFalse((self.app / "version.dll").exists())

    def test_companion_refuses_bad_line_and_foreign_file(self):
        reg = FakeRegistry()
        with self.assertRaisesRegex(pp.Error, "one line"):
            pp.apply(self.prefix, self.exe, "version", self.dll, reg, "dllmgr run")
        (self.app / "version.dllmgr").write_text("someone else's\n")
        with self.assertRaisesRegex(pp.Error, "not managed"):
            pp.apply(self.prefix, self.exe, "version", self.dll, reg, '"Z:\\x" run')
        self.assertFalse((self.app / "version.dll").exists())
        self.assertEqual(reg.values, {})

    def test_registry_survives_non_utf8_reg_output(self):
        fake = Path(self.tmp.name) / "fake-wine"
        # reg.exe on a Russian locale: cp866 error text, exit 1 for a missing value
        fake.write_bytes(b"#!/bin/sh\nprintf '\\216\\350\\250\\241\\255\\240\\357 \\255\\245\\342\\n' >&2\n"
                         b"printf 'x\\255y\\n'\nexit 1\n")
        fake.chmod(0o755)
        reg = pp.Registry(self.prefix, str(fake))
        self.assertIsNone(reg.get(self.key, "version"))


if __name__ == "__main__":
    unittest.main()
