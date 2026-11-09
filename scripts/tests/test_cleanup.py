import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location("cleanup", Path(__file__).resolve().parents[1] / "cleanup.py")
cleanup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup)


class CleanupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {"HOME": str(self.home), "WINEPREFIX": str(self.home / ".wine")}, clear=False)
        self.env.start()
        os.environ.pop("XDG_DATA_HOME", None)
        # default prefix with Photoshop + avif, a second prefix under Games with FastStone, one unrelated prefix
        self.wine = self.prefix(".wine")
        (self.wine / ".dllmgr/apps").mkdir(parents=True)
        (self.wine / ".dllmgr/apps/photoshop-cs2-0123456789abcdef0123.json").write_text(json.dumps({"exe": "/x/Photoshop.exe"}))
        (self.wine / ".dllmgr/avif-codec.json").write_text("{}")
        (self.wine / "drive_c/dllmgr").mkdir(parents=True)
        self.games = self.prefix("Games/fs")
        (self.games / ".dllmgr/apps").mkdir(parents=True)
        (self.games / ".dllmgr/apps/faststone-0123456789abcdef0123.json").write_text(json.dumps({"exe": "/y/FSViewer.exe"}))
        self.other = self.prefix("Games/other")
        nested = self.wine / "drive_c/users/u/inner"  # never walked into
        (nested / ".dllmgr").mkdir(parents=True)
        (nested / "system.reg").write_text("")
        share = self.home / ".local/share"
        (share / "dllmgr/runtimes/abc").mkdir(parents=True)
        (share / "applications").mkdir(parents=True)
        (share / "applications/dllmgr-fix.desktop").write_text("")
        (share / "applications/other.desktop").write_text("")
        (self.home / ".cache/fix-it-in-wine").mkdir(parents=True)
        lib = self.home / ".local/lib/dllmgr/" / ("a" * 40)
        lib.mkdir(parents=True)
        (lib / "dllmgr").write_text("")
        (self.home / ".local/bin").mkdir(parents=True)
        (self.home / ".local/bin/dllmgr").symlink_to(lib / "dllmgr")
        self.calls = []

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def prefix(self, rel):
        p = self.home / rel
        p.mkdir(parents=True)
        (p / "system.reg").write_text("")
        return p

    def fake_run(self, ok=True):
        def run(cmd, env=None):
            self.calls.append((cmd[2] if cmd[1] == "unfix" else "prefill", cmd[3] if cmd[1] == "unfix" else None, env["WINEPREFIX"]))
            if ok:  # the real unfix removes the recipe's state
                prefix = Path(env["WINEPREFIX"])
                for path in (prefix / ".dllmgr/apps").glob(cmd[2] + "-*.json") if cmd[1] == "unfix" else ():
                    path.unlink()
                if cmd[1] == "unfix" and cmd[2] == "faststone-avif":
                    (prefix / ".dllmgr/avif-codec.json").unlink()
            return mock.Mock(returncode=0 if ok else 1)
        return run

    def run_cleanup(self, *argv, ok=True):
        with mock.patch.object(cleanup.subprocess, "run", side_effect=self.fake_run(ok)), \
             mock.patch("sys.stdout", new_callable=io.StringIO):
            return cleanup.main(list(argv))

    def test_prefix_from_a_routed_launcher_outside_home(self):
        with tempfile.TemporaryDirectory() as far:
            far = Path(far)
            (far / "system.reg").write_text("")
            (self.home / ".local/share/applications/dllmgr-faststone-x.desktop").write_text(
                '[Desktop Entry]\nExec="/h/dllmgr" "run" "faststone" "--prefix" "%s" "--exe" "/f.exe" -- %%F\n' % far)
            self.assertIn(far.resolve(), {p.resolve() for p in cleanup.find_prefixes([])})

    def test_finds_prefixes_with_state_but_not_inside_prefixes(self):
        found = {p.resolve() for p in cleanup.find_prefixes([])}
        self.assertEqual(found, {self.wine.resolve(), self.games.resolve()})

    def test_everything(self):
        self.assertEqual(self.run_cleanup("--yes"), 0)
        self.assertEqual(sorted(c[0] for c in self.calls), ["faststone", "faststone-avif", "photoshop-cs2"])
        for gone in (self.wine / ".dllmgr", self.wine / "drive_c/dllmgr", self.games / ".dllmgr",
                     self.home / ".local/share/dllmgr", self.home / ".cache/fix-it-in-wine",
                     self.home / ".local/share/applications/dllmgr-fix.desktop", self.home / ".local/lib/dllmgr"):
            self.assertFalse(gone.exists(), gone)
        self.assertFalse((self.home / ".local/bin/dllmgr").is_symlink())
        self.assertTrue((self.home / ".local/share/applications/other.desktop").exists())
        self.assertTrue((self.wine / "system.reg").exists())

    def test_one_fix_keeps_the_rest_and_the_runtime_while_used(self):
        self.assertEqual(self.run_cleanup("photoshop-cs2", "--yes"), 0)
        self.assertEqual([c[0] for c in self.calls], ["photoshop-cs2"])
        self.assertTrue((self.home / ".local/share/dllmgr/runtimes").exists())  # FastStone still uses it
        self.assertTrue((self.wine / ".dllmgr/avif-codec.json").exists())
        self.calls.clear()
        self.assertEqual(self.run_cleanup("faststone", "--yes"), 0)
        self.assertFalse((self.home / ".local/share/dllmgr/runtimes").exists())  # last app recipe gone
        self.assertTrue((self.home / ".local/lib/dllmgr").exists())

    def test_failed_unfix_removes_nothing_else(self):
        self.assertEqual(self.run_cleanup("--yes", ok=False), 1)
        self.assertTrue((self.home / ".local/lib/dllmgr").exists())
        self.assertTrue((self.wine / ".dllmgr").exists())

    def test_dry_run_changes_nothing(self):
        self.assertEqual(self.run_cleanup("--dry-run"), 0)
        self.assertEqual(self.calls, [])
        self.assertTrue((self.home / ".local/lib/dllmgr").exists())
        self.assertTrue((self.wine / ".dllmgr/apps").exists())

    def test_asks_first(self):
        with mock.patch("builtins.input", return_value="n"):
            self.assertEqual(self.run_cleanup(), 1)
        self.assertEqual(self.calls, [])
        self.assertTrue((self.home / ".local/lib/dllmgr").exists())


if __name__ == "__main__":
    unittest.main()
