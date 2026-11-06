import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "catalog_fixes.py"
SPEC = importlib.util.spec_from_file_location("catalog_fixes", SCRIPT)
catalog_fixes = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(catalog_fixes)

INDEX = [
    {"kind": "fix", "id": "winehq-1"},
    {"kind": "fix", "id": "dllmgr-2"},
    {"kind": "bundle", "id": "app-all", "application": "app", "fixes": ["winehq-1", "dllmgr-2"]},
    {"kind": "bundle", "id": "draft-all", "fixes": ["winehq-1"]},
]


class CatalogFixesTest(unittest.TestCase):
    def test_application_and_bundle_ids_resolve_to_the_bundle_list(self):
        self.assertEqual(catalog_fixes.resolve("app", INDEX), ["winehq-1", "dllmgr-2"])
        self.assertEqual(catalog_fixes.resolve("app-all", INDEX), ["winehq-1", "dllmgr-2"])

    def test_a_fix_resolves_to_itself(self):
        self.assertEqual(catalog_fixes.resolve("dllmgr-2", INDEX), ["dllmgr-2"])

    def test_unknown_id_is_rejected(self):
        with self.assertRaises(KeyError):
            catalog_fixes.resolve("other", INDEX)

    def test_known_lists_only_installable_bundles(self):
        self.assertEqual(catalog_fixes.known(INDEX), {"app", "winehq-1", "dllmgr-2"})

    def test_real_catalog_lists_the_faststone_bundle(self):
        self.assertIn("winehq-59609", catalog_fixes.resolve("faststone"))


if __name__ == "__main__":
    unittest.main()
