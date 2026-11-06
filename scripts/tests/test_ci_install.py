"""Check installer failures without network access, sudo or package mutation."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / 'tests/wine/ci-install.sh'


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'dllmgr-ci-install').mkdir()
        self.env = dict(os.environ, PATH=str(self.root) + os.pathsep + os.environ['PATH'],
                        RUNNER_TEMP=str(self.root), INSTALL_TEST_ROOT=str(self.root))
        for name, body in {
            'sudo': 'exec "$@"',
            'dpkg': 'exit 0',
            'mkdir': 'exit 0',
            'tee': 'cat >/dev/null',
            'curl': 'exit 22',
            'apt-get': '''python3 - "$@" <<'ARGS'
import json, os, sys
from pathlib import Path
with (Path(os.environ['INSTALL_TEST_ROOT']) / 'calls').open('a') as out:
    out.write(json.dumps(sys.argv[1:])+'\\n')
ARGS
exit "${APT_RESULT:-0}"''',
        }.items():
            p = self.root / name
            p.write_text('#!/usr/bin/env bash\n' + body + '\n')
            p.chmod(0o755)

    def run_attempt(self, *args, **env):
        return subprocess.run(['bash', str(SCRIPT), '--attempt', *args],
                              env=dict(self.env, **env), capture_output=True, text=True, timeout=5)

    def calls(self):
        p = self.root / 'calls'
        return [json.loads(line) for line in p.read_text().splitlines()] if p.exists() else []

    def test_failed_repository_download_stops_before_apt(self):
        result = self.run_attempt('--winehq', 'winehq-stable')
        self.assertEqual(result.returncode, 22, result.stderr)
        self.assertEqual(self.calls(), [])

    def test_failed_index_update_stops_before_install(self):
        result = self.run_attempt('wine', APT_RESULT='100')
        self.assertEqual(result.returncode, 100, result.stderr)
        self.assertEqual(len(self.calls()), 1)
        self.assertIn('update', self.calls()[0])

    def test_package_arguments_are_literal_and_download_logging_is_enabled(self):
        value = 'package; touch ' + str(self.root / 'should-not-exist')
        result = subprocess.run(['bash', str(SCRIPT), '--install-recommends', value],
                                env=self.env, capture_output=True, text=True, timeout=5)
        self.assertFalse((self.root / 'should-not-exist').exists())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls()[1][-2:], ['--install-recommends', value])
        self.assertIn('-q', self.calls()[1])
        self.assertNotIn('-qq', self.calls()[1])


if __name__ == '__main__':
    unittest.main()
