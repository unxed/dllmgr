"""Run the real apply/undo scripts and legacy helpers with fake curl/Wine."""
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]


def pe(name=b"comctl32_v6.dll", tail=b"original"):
    data = bytearray(0x400)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 0x60)
    data[0x40:0x50] = b"Wine builtin DLL"
    data[0x60:0x64] = b"PE\0\0"
    struct.pack_into("<HH", data, 0x64, 0x14C, 1)
    struct.pack_into("<H", data, 0x74, 0xE0)
    struct.pack_into("<H", data, 0x78, 0x10B)
    struct.pack_into("<II", data, 0x78 + 96, 0x1000, 0x28)
    struct.pack_into("<8sIIII", data, 0x78 + 0xE0, b".edata", 0x100, 0x1000, 0x100, 0x200)
    struct.pack_into("<I", data, 0x20C, 0x1028)
    data[0x228:0x229 + len(name)] = name + b"\0"
    data[0x300:0x300 + len(tail)] = tail
    return bytes(data)


class ApplyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="dllmgr test ")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.prefix = self.root / "prefix"
        self.dest = self.prefix / "drive_c/windows/winsxs/x86_microsoft.windows.common-controls_6595b64144ccf1df_6.0_test/comctl32.dll"
        self.dest.parent.mkdir(parents=True)
        self.gdi = self.prefix / "drive_c/windows/syswow64/gdiplus.dll"
        self.gdi.parent.mkdir(parents=True)
        self.gdi_original = pe(name=b"gdiplus.dll", tail=b"original gdi")
        self.gdi.write_bytes(self.gdi_original)
        self.original = pe()
        self.dest.write_bytes(self.original)
        (self.prefix / "system.reg").write_text("#arch=win64\n")
        self.exe = self.prefix / "drive_c/Program Files/FastStone/FSViewer.exe"
        self.exe.parent.mkdir(parents=True)
        self.exe.write_bytes(pe() + b"Microsoft.Windows.Common-Controls")
        self.dll = self.root / "release.dll"
        self.dll.write_bytes(pe(tail=b"fixed"))
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
                        WINEPREFIX=str(self.prefix), FIW_WORK=str(self.root / "cache"),
                        LC_ALL="ru_RU.UTF-8", LANG="ru_RU.UTF-8", PYTHONUTF8="1",
                        TEST_ROOT=str(self.root))
        self.env.pop("FIW_WINE", None)
        if "FIW_TOOLS" not in self.env:
            raise RuntimeError("set FIW_TOOLS to an unmodified fix-it-in-wine/tools checkout")
        self.command("wine", '''import json, os, pathlib, sys
root = pathlib.Path(os.environ["TEST_ROOT"])
if sys.argv[1:] == ["--version"]:
    print("wine-11.0"); sys.exit(0)
registry = root / "registry.json"
values = json.loads(registry.read_text()) if registry.exists() else {}
name = sys.argv[sys.argv.index("/v") + 1]
value = values.get(name)
op = sys.argv[2]
if op == "query":
    output = "    " + name + "    REG_SZ    " + value + "\\r\\n" if value is not None else "reg: не удалось найти указанный ключ\\r\\n"
    rc = 0 if value is not None else 1
elif op == "add":
    if (os.environ.get("FAIL_NEXT_ADD") or os.environ.get("FAIL_GDI_ADD") and name == "gdiplus") and not (root / "add-failed").exists():
        (root / "add-failed").write_text("once")
        sys.stderr.buffer.write("Отказано в доступе".encode("cp866"))
        sys.exit(1)
    values[name] = sys.argv[sys.argv.index("/d") + 1]
    registry.write_text(json.dumps(values))
    output, rc = "Операция успешно завершена\\r\\n", 0
elif op == "delete":
    values.pop(name, None)
    if values: registry.write_text(json.dumps(values))
    elif registry.exists(): registry.unlink()
    output, rc = "Операция успешно завершена\\r\\n", 0
else:
    raise AssertionError(sys.argv)
sys.stdout.buffer.write(output.encode("cp866"))
sys.stderr.buffer.write("wine: /tmp/папка\\n".encode("utf-8"))
sys.exit(rc)
''')
        self.command("curl", '''import hashlib, os, pathlib, sys
root = pathlib.Path(os.environ["TEST_ROOT"])
name = sys.argv[-1].rsplit("/", 1)[-1]
if os.environ.get("CURL_FAIL") == ("sums" if name == "SHA256SUMS" else "dll"):
    sys.exit(22)
data = (root / "release.dll").read_bytes()
if name == "SHA256SUMS":
    digest = "0" * 64 if os.environ.get("BAD_SUM") else hashlib.sha256(data).hexdigest()
    data = (digest + "  comctl32_v6-wine-11.0-i386.dll\\n" + digest + "  gdiplus-wine-11.0-i386.dll\\n").encode()
pathlib.Path(sys.argv[sys.argv.index("-o") + 1]).write_bytes(data)
''')
        self.command("git", 'raise AssertionError("unexpected local build or tools checkout")\n')

    def command(self, name, body):
        path = self.bin / name
        path.write_text("#!" + sys.executable + "\n" + body)
        path.chmod(0o755)

    def run_script(self, name="apply", fix="winehq-59609", **env):
        return subprocess.run([str(SCRIPTS / (name + "-" + fix + ".sh"))], env=dict(self.env, **env),
                              capture_output=True, text=True, timeout=30)

    def test_russian_apply_and_separate_undo_restore_bytes_and_registry(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        state = json.loads((self.prefix / "fix-it-in-wine/state.json").read_text())
        self.assertEqual(len(state["entries"]), 1)
        self.assertEqual(json.loads((self.root / "registry.json").read_text())["comctl32"], "native,builtin")
        self.assertNotEqual(self.dest.read_bytes(), self.original)
        result = self.run_script("undo", CURL_FAIL="dll")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.dest.read_bytes(), self.original)
        self.assertFalse((self.root / "registry.json").exists())
        self.assertEqual(json.loads((self.prefix / "fix-it-in-wine/state.json").read_text())["entries"], [])

    def test_existing_registry_value_restored(self):
        (self.root / "registry.json").write_text(json.dumps({"comctl32": "builtin"}))
        self.assertEqual(self.run_script().returncode, 0)
        result = self.run_script("undo")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.root / "registry.json").read_text()), {"comctl32": "builtin"})

    def test_download_failures_do_not_build_or_change_prefix_or_cache(self):
        cached = self.root / "cache/release/winehq-59609/comctl32_v6-wine-11.0-i386.dll"
        cached.parent.mkdir(parents=True)
        cached.write_bytes(b"previous cached DLL")
        for failure in ("dll", "sums"):
            with self.subTest(failure=failure):
                result = self.run_script(CURL_FAIL=failure)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn("--build", result.stderr)
                self.assertEqual(self.dest.read_bytes(), self.original)
                self.assertEqual(cached.read_bytes(), b"previous cached DLL")
                self.assertFalse((self.prefix / "fix-it-in-wine").exists())

    def test_checksum_failure_does_not_change_prefix(self):
        result = self.run_script(BAD_SUM="1")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("checksum mismatch", result.stderr)
        self.assertEqual(self.dest.read_bytes(), self.original)
        self.assertFalse((self.prefix / "fix-it-in-wine").exists())

    def test_upgrade_to_combined_set_keeps_the_original_undo_baseline(self):
        (self.root / "registry.json").write_text(json.dumps({"comctl32": "builtin"}))
        self.assertEqual(self.run_script().returncode, 0)
        self.dll.write_bytes(pe(tail=b"combined fixes"))
        result = self.run_script(fix="faststone")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        state = json.loads((self.prefix / "fix-it-in-wine/state.json").read_text())
        self.assertEqual(state["entries"][0]["dllmgr_fix"], "faststone")
        self.assertEqual(state["entries"][0]["orig_sha256"], hashlib.sha256(self.original).hexdigest())
        self.assertEqual(state["entries"][0]["reg_before"], "builtin")
        self.assertNotEqual(self.run_script("undo").returncode, 0)
        result = self.run_script("undo", fix="faststone")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.dest.read_bytes(), self.original)
        self.assertEqual(self.gdi.read_bytes(), self.gdi_original)
        self.assertEqual(json.loads((self.root / "registry.json").read_text()), {"comctl32": "builtin"})

    def test_failed_switch_restores_the_installed_fix_and_state(self):
        self.assertEqual(self.run_script().returncode, 0)
        installed = self.dest.read_bytes()
        old_state = json.loads((self.prefix / "fix-it-in-wine/state.json").read_text())
        self.dll.write_bytes(pe(tail=b"combined fixes"))
        result = self.run_script(fix="faststone", FAIL_NEXT_ADD="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.dest.read_bytes(), installed)
        self.assertEqual(json.loads((self.prefix / "fix-it-in-wine/state.json").read_text()), old_state)
        self.assertEqual(json.loads((self.root / "registry.json").read_text())["comctl32"], "native,builtin")

    def test_second_module_failure_rolls_back_first_module_and_registry(self):
        self.assertEqual(self.run_script().returncode, 0)
        before = self.dest.read_bytes()
        state = (self.prefix / "fix-it-in-wine/state.json").read_bytes()
        self.dll.write_bytes(pe(tail=b"combined"))
        result = self.run_script(fix="faststone", FAIL_GDI_ADD="1")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.dest.read_bytes(), before)
        self.assertEqual(self.gdi.read_bytes(), self.gdi_original)
        self.assertEqual(json.loads((self.prefix / "fix-it-in-wine/state.json").read_bytes()), json.loads(state))
        self.assertEqual(json.loads((self.root / "registry.json").read_text()), {"comctl32": "native,builtin"})

    def test_switching_from_bundle_to_single_fix_removes_unused_module(self):
        result = self.run_script(fix="faststone")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotEqual(self.gdi.read_bytes(), self.gdi_original)
        self.dll.write_bytes(pe(tail=b"single fix"))
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.gdi.read_bytes(), self.gdi_original)
        self.assertEqual(json.loads((self.root / "registry.json").read_text()), {"comctl32": "native,builtin"})
        result = self.run_script("undo")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.dest.read_bytes(), self.original)
        self.assertFalse((self.root / "registry.json").exists())

    def test_reapplying_the_same_set_is_idempotent(self):
        self.assertEqual(self.run_script().returncode, 0)
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("already enabled", result.stdout)


if __name__ == "__main__":
    unittest.main()
