import hashlib
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "select-faststone.py"
SPEC = importlib.util.spec_from_file_location("select_faststone", SCRIPT)
selector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(selector)


class FastStoneProfileTest(unittest.TestCase):
    def test_exact_application_and_platform_required_for_a_shared_override(self):
        with TemporaryDirectory() as tmp, patch.object(selector.platform, "machine", return_value="x86_64"):
            prefix = Path(tmp)
            exe = prefix / "drive_c" / "Portable" / "FSViewer.exe"
            exe.parent.mkdir(parents=True)
            exe.write_bytes(b"verified")
            (prefix / "system.reg").write_text("WINE REGISTRY Version 2\n#arch=win64\n")
            catalog = [{
                "id": "faststone-all", "programs": ["FSViewer.exe"],
                "profiles": [{
                    "wine": "wine-11.0", "host_arch": "x86_64", "prefix_arch": "win64",
                    "exe_sha256": hashlib.sha256(b"verified").hexdigest(),
                }],
            }]
            self.assertEqual(selector.select(catalog, prefix, "wine-11.0", None), exe)
            with self.assertRaisesRegex(ValueError, "no verified"):
                selector.select(catalog, prefix, "wine-11.17", None)
            (exe.parent.parent / "FSVIEWER.EXE").write_bytes(b"different version")
            with self.assertRaisesRegex(ValueError, "not a verified FastStone build"):
                selector.select(catalog, prefix, "wine-11.0", exe)
