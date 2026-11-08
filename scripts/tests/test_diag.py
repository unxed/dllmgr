import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("diag", Path(__file__).resolve().parent.parent / "diag.py")
diag = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diag)


class RegValueTest(unittest.TestCase):
    def test_reads_value_from_wine_reg_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = Path(tmp) / "system.reg"
            reg.write_text('WINE REGISTRY Version 2\n\n'
                           '[System\\\\ControlSet001\\\\Hardware Profiles\\\\Current\\\\Software\\\\Fonts] 1794159923\n'
                           '#time=1dc6f\n"LogPixels"=dword:000000c0\n\n'
                           '[Other] 1\n"LogPixels"=dword:00000060\n')
            key = 'System\\ControlSet001\\Hardware Profiles\\Current\\Software\\Fonts'
            self.assertEqual(diag.reg_value(reg, key, 'LogPixels'), 'dword:000000c0')
            self.assertIsNone(diag.reg_value(reg, 'Missing\\Key', 'LogPixels'))
            self.assertIsNone(diag.reg_value(Path(tmp) / 'absent.reg', key, 'LogPixels'))


if __name__ == "__main__":
    unittest.main()
