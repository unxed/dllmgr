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
    {"kind": "bundle", "id": "app-all", "application": "app", "fixes": ["winehq-1", "dllmgr-2"],
     "profiles": [{"wine": "wine-11.0", "release": "app-v3"}, {"wine": "wine-9.0"}]},
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

    def test_release_follows_the_profile_for_the_wine_tag(self):
        self.assertEqual(catalog_fixes.release("app", "wine-11.0", INDEX), "app-v3")
        with self.assertRaises(KeyError):
            catalog_fixes.release("app", "wine-9.0", INDEX)

    def test_fix_release_can_advance_without_replacing_old_release_bytes(self):
        entry = {"kind": "fix", "id": "dllmgr-2",
                 "binaries": "https://github.com/unxed/dllmgr/releases/tag/dllmgr-2-v2"}
        self.assertEqual(catalog_fixes.release("dllmgr-2", "wine-11.0", [entry]), "dllmgr-2-v2")
        self.assertEqual(catalog_fixes.release("winehq-1", "wine-11.0", INDEX), "winehq-1")
        entry["binaries"] = "https://example.com/dllmgr-2-v2"
        with self.assertRaisesRegex(ValueError, "unsupported binary release"):
            catalog_fixes.release("dllmgr-2", "wine-11.0", [entry])

    def test_real_catalog_lists_the_faststone_bundle(self):
        self.assertIn("winehq-59609", catalog_fixes.resolve("faststone"))


if __name__ == "__main__":
    unittest.main()
