"""Find recipe programs in a prefix and offer their recipes, without Wine."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("detect_apps", SCRIPTS / "detect-apps.py")
detect_apps = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(detect_apps)


def bundle(*rows):
    return {"kind": "bundle", "id": "app-all", "application": "app",
            "programs": ["App.exe"], "fixes": ["winehq-1"], "profiles": list(rows)}


def row(content, wine="wine-11.0", prefix_arch="win64"):
    return {"exe_sha256": hashlib.sha256(content).hexdigest(), "wine": wine,
            "host_arch": platform.machine(), "prefix_arch": prefix_arch, "release": "app-v1"}


class DetectTest(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory(prefix="dllmgr detect ")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.prefix = self.root / "prefix"
        (self.prefix / "drive_c").mkdir(parents=True)
        (self.prefix / "system.reg").write_text("WINE REGISTRY Version 2\n#arch=win64\n")

    def program(self, relative, content):
        path = self.prefix / "drive_c" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def test_a_measured_build_on_a_measured_system_is_ready(self):
        exe = self.program("Program Files/App/APP.EXE", b"v1")
        report, ready = detect_apps.detect([bundle(row(b"v1"))], self.prefix, "wine-11.0")
        self.assertEqual(ready, {"app"})
        self.assertEqual(report, [("app", "ready", exe, None)])

    def test_the_reason_names_the_key_that_differs(self):
        self.program("App/App.exe", b"v1")
        report, ready = detect_apps.detect([bundle(row(b"v1"))], self.prefix, "wine-9.0")
        self.assertEqual(ready, set())
        self.assertIn("wine: verified on wine-11.0, this system has wine-9.0", report[0][3])

    def test_an_unknown_build_is_reported_but_not_ready(self):
        self.program("App/App.exe", b"v2")
        report, ready = detect_apps.detect([bundle(row(b"v1"))], self.prefix, "wine-11.0")
        self.assertEqual(ready, set())
        self.assertEqual(report[0][1], "unverified")
        self.assertIn("no verified row", report[0][3])

    def test_copies_sharing_an_exe_name_must_match_the_same_row(self):
        self.program("A/App.exe", b"v1")
        self.program("B/App.exe", b"v2")
        report, ready = detect_apps.detect([bundle(row(b"v1"))], self.prefix, "wine-11.0")
        self.assertEqual(ready, set())
        self.assertEqual(report[-1][1], "blocked")

    def test_an_explicit_portable_copy_is_checked_too(self):
        portable = self.root / "portable" / "App.exe"
        portable.parent.mkdir()
        portable.write_bytes(b"v1")
        report, ready = detect_apps.detect([bundle(row(b"v1"))], self.prefix, "wine-11.0", [portable])
        self.assertEqual(ready, {"app"})
        self.assertEqual(report[0][2], portable)

    def test_bundles_without_an_application_are_ignored(self):
        self.program("App/App.exe", b"v1")
        draft = dict(bundle(row(b"v1")), application=None)
        self.assertEqual(detect_apps.detect([draft], self.prefix, "wine-11.0"), ([], set()))


class FixPrefixTest(unittest.TestCase):
    """`dllmgr fix` without an application, with stub wine and stub recipe runner."""

    def setUp(self):
        temp = TemporaryDirectory(prefix="dllmgr fix ")
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.tree = root / "dllmgr"
        (self.tree / "scripts").mkdir(parents=True)
        (self.tree / "catalog").mkdir()
        for name in ("fix-prefix.sh", "detect-apps.py", "catalog_fixes.py"):
            shutil.copy2(SCRIPTS / name, self.tree / "scripts")
        index = {"format": 1, "entries": [bundle(row(b"v1"))]}
        (self.tree / "catalog" / "index.json").write_text(json.dumps(index))
        self.calls = root / "calls"
        runner = self.tree / "dllmgr"
        runner.write_text(f'#!/bin/sh\nprintf "%s\\n" "$*" >> "{self.calls}"\n')
        runner.chmod(0o755)
        wine = root / "wine"
        wine.write_text("#!/bin/sh\necho 'wine-11.0 (test)'\n")
        wine.chmod(0o755)
        self.prefix = root / "prefix"
        self.exe = self.prefix / "drive_c" / "App" / "App.exe"
        self.exe.parent.mkdir(parents=True)
        self.exe.write_bytes(b"v1")
        (self.prefix / "system.reg").write_text("#arch=win64\n")
        self.env = {**os.environ, "FIW_WINE": str(wine), "WINEPREFIX": str(self.prefix)}

    def fix(self, *args, env=None):
        return subprocess.run(["bash", str(self.tree / "scripts" / "fix-prefix.sh"), *args],
                              env=env or self.env, stdin=subprocess.DEVNULL, text=True, capture_output=True)

    def applied(self):
        return self.calls.read_text().splitlines() if self.calls.exists() else []

    def test_yes_applies_each_ready_recipe(self):
        result = self.fix("--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.applied(), ["fix app"])
        self.assertIn("Verified recipes: app", result.stdout)

    def test_without_a_terminal_or_yes_nothing_is_applied(self):
        result = self.fix()
        self.assertEqual(result.returncode, 1)
        self.assertIn("dllmgr fix app", result.stderr)
        self.assertEqual(self.applied(), [])

    def test_dry_run_only_reports(self):
        result = self.fix("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.applied(), [])

    def test_an_exe_inside_drive_c_selects_its_prefix(self):
        env = {key: value for key, value in self.env.items() if key != "WINEPREFIX"}
        result = self.fix("--yes", "--exe", str(self.exe), env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(str(self.prefix), result.stdout)
        self.assertEqual(self.applied(), [f"fix app --exe {self.exe}"])

    def test_nothing_matching_is_a_failure_with_a_reason(self):
        self.exe.write_bytes(b"v2")
        result = self.fix("--yes")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Nothing to fix", result.stdout)
        self.assertIn("no verified row", result.stderr)
        self.assertEqual(self.applied(), [])


if __name__ == "__main__":
    unittest.main()
