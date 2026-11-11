"""Exercise the generated shell command without GitHub or a Wine prefix."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = "https://github.com/unxed/dllmgr"


class ShareTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="dllmgr share ")
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.home = root / "home"
        self.home.mkdir()
        self.checkout = root / "checkout"
        self.checkout.mkdir()
        self.env = {
            **os.environ,
            "HOME": str(self.home),
            "GIT_CONFIG_GLOBAL": str(root / "gitconfig"),
            "GIT_CONFIG_NOSYSTEM": "1",
            "WINEPREFIX": str(root / "Wine prefix"),
            "XDG_DATA_HOME": str(self.home / ".local" / "share"),
        }
        self.git("init", "-q")
        self.git("config", "user.name", "dllmgr test")
        self.git("config", "user.email", "dllmgr@example.invalid")
        self.git("config", "--global", f"url.{self.checkout.as_uri()}.insteadOf", UPSTREAM + ".git")
        shutil.copy2(ROOT / "install.sh", self.checkout)
        (self.checkout / "scripts").mkdir()
        shutil.copy2(ROOT / "scripts" / "share-recipe.py", self.checkout / "scripts")
        shutil.copy2(ROOT / "scripts" / "catalog_fixes.py", self.checkout / "scripts")
        shutil.copy2(ROOT / "scripts" / "install-version.sh", self.checkout / "scripts")
        shutil.copytree(ROOT / "catalog", self.checkout / "catalog")
        (self.checkout / "patches").mkdir()
        (self.checkout / "patches" / "test.patch").touch()
        self.runtime = self.checkout / "dllmgr"
        self.runtime.write_text(
            '#!/bin/sh\n'
            'root=$(dirname "$(readlink -f -- "$0")")\n'
            'if [ "$1" = share ]; then\n'
            '    shift; exec python3 "$root/scripts/share-recipe.py" "$@"\n'
            'fi\n'
            '[ "$1 $2" = "fix faststone" ] || exit 2\n'
            'printf "using %s\\n" "$WINEPREFIX"\n'
        )
        self.runtime.chmod(0o755)
        self.commit("initial")
        self.launcher = self.home / ".local" / "bin" / "dllmgr"

    def command(self, *args, check=True):
        return subprocess.run(
            args, cwd=self.checkout, env=self.env, text=True, capture_output=True, check=check
        )

    def git(self, *args):
        return self.command("git", *args).stdout.strip()

    def commit(self, message):
        self.git("add", ".")
        self.git("commit", "-qm", message)

    def test_generated_command_installs_the_pinned_commit_and_applies_recipe(self):
        revision = self.git("rev-parse", "HEAD")
        result = self.command(self.runtime, "share", "faststone-all")
        url, installer = result.stdout.splitlines()
        self.assertEqual(url, f"{UPSTREAM}/blob/{revision}/catalog/bundles/faststone-all.md")
        self.assertIn(revision, installer)

        # Advance the source checkout to prove the command uses the old pin.
        self.runtime.write_text(self.runtime.read_text() + "# new revision\n")
        self.commit("new version")

        applied = self.command("sh", "-c", installer)
        self.assertIn(f"using {self.env['WINEPREFIX']}", applied.stdout)
        self.assertEqual(self.launcher.resolve().parent.name, revision)
        entry = (self.home / ".local" / "share" / "applications" / "dllmgr-fix.desktop").read_text()
        self.assertIn(f'Exec="{self.launcher}" fix --pause\n', entry)
        self.assertIn("Terminal=true\n", entry)
        self.assertEqual(self.command(self.launcher, "share", "--command", "faststone").stdout.strip(), installer)

        self.command("bash", self.checkout / "install.sh")
        updated = self.git("rev-parse", "HEAD")
        self.assertEqual(self.launcher.resolve().parent.name, updated)
        self.assertIn(updated, self.command(self.launcher, "share", "--command", "faststone").stdout)

    def test_existing_unmanaged_command_is_preserved(self):
        self.launcher.parent.mkdir(parents=True)
        self.launcher.write_text("existing file\n")
        result = self.command("bash", self.checkout / "install.sh", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not managed", result.stderr)
        self.assertEqual(self.launcher.read_text(), "existing file\n")

    def test_unknown_recipe_produces_no_install_command(self):
        result = self.command(self.runtime, "share", "winehq-59609", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
