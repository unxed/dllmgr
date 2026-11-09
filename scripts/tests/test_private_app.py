"""Synthetic tests for private Wine runtime assembly and app launch isolation."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import zipfile

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import private_runtime

SPEC = importlib.util.spec_from_file_location("private_app", SCRIPTS / "private-app.py")
private_app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(private_app)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def make_pe(name=b"comctl32_v6.dll", tail=b"payload"):
    """Small synthetic PE containing Wine's builtin mark and one export name."""
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


def make_runtime_package(path, payloads=None, manifest_overrides=None, extra_members=None):
    payloads = payloads or {
        "bin/wine": b"private wine launcher",
        "i386-windows/ntdll.dll": b"private i386 ntdll",
        "x86_64-windows/ntdll.dll": b"private x64 ntdll",
        "x86_64-unix/ntdll.so": b"private unix ntdll",
    }
    files = {name: sha(data) for name, data in payloads.items()}
    manifest = {
        "schema": 1,
        "wine_commit": private_runtime.WINE_COMMIT,
        "wine_version": "wine-11.0",
        "files": files,
        "base_files": {name: "0" * 64 for name in private_runtime.OVERLAY.values()},
    }
    if manifest_overrides:
        manifest.update(manifest_overrides)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        for name, data in payloads.items():
            archive.writestr(name, data)
        for name, data in (extra_members or {}).items():
            archive.writestr(name, data)
    return manifest, payloads


class PrivateRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="dllmgr-private-runtime-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.package = self.root / "runtime.zip"
        self.base = self.root / "base-wine"
        self.base.mkdir()

    def test_rejects_archive_traversal(self):
        make_runtime_package(self.package, extra_members={"../escape": b"outside"})
        with self.assertRaisesRegex(private_runtime.Error, "Unsafe runtime archive member"):
            private_runtime.package_manifest(self.package)
        self.assertFalse((self.root.parent / "escape").exists())

    def test_rejects_manifest_mismatch_and_wrong_runtime(self):
        make_runtime_package(self.package, manifest_overrides={"wine_commit": "0" * 40})
        with self.assertRaisesRegex(private_runtime.Error, "Unsupported private runtime"):
            private_runtime.package_manifest(self.package)

        make_runtime_package(self.package, manifest_overrides={"files": {"bin/wine": "0" * 64}})
        with self.assertRaisesRegex(private_runtime.Error, "Incomplete runtime manifest"):
            private_runtime.package_manifest(self.package)

    def test_rejects_base_fingerprint_mismatch(self):
        manifest, _ = make_runtime_package(self.package)
        for name in private_runtime.OVERLAY.values():
            path = self.base / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"base " + name.encode())
            manifest["base_files"][name] = sha(path.read_bytes())
        private_runtime.verify_base(self.base, manifest)
        changed = self.base / "lib/wine/x86_64-windows/ntdll.dll"
        changed.write_bytes(b"changed base runtime")
        with self.assertRaisesRegex(private_runtime.Error, "Unsupported or changed base Wine"):
            private_runtime.verify_base(self.base, manifest)

    def test_optional_overlay_group_is_all_or_none(self):
        payloads = {
            "bin/wine": b"w", "i386-windows/ntdll.dll": b"a", "x86_64-windows/ntdll.dll": b"b",
            "x86_64-unix/ntdll.so": b"c", "x86_64-unix/win32u.so": b"only one of the pair",
        }
        make_runtime_package(self.package, payloads=payloads)
        with self.assertRaisesRegex(private_runtime.Error, "Partial optional overlay group"):
            private_runtime.package_manifest(self.package)

    def test_optional_overlay_group_is_fingerprinted_and_installed(self):
        base_files = {
            "bin/wine": b"stock wine", "lib/wine/i386-windows/ntdll.dll": b"stock i386",
            "lib/wine/x86_64-windows/ntdll.dll": b"stock x64", "lib/wine/x86_64-unix/ntdll.so": b"stock unix",
            "lib/wine/x86_64-unix/win32u.so": b"stock win32u", "lib/wine/x86_64-unix/winex11.so": b"stock x11",
            "lib/wine/x86_64-unix/winewayland.so": b"untouched",
        }
        for name, data in base_files.items():
            (self.base / name).parent.mkdir(parents=True, exist_ok=True)
            (self.base / name).write_bytes(data)
        payloads = {
            "bin/wine": b"overlay wine", "i386-windows/ntdll.dll": b"overlay i386",
            "x86_64-windows/ntdll.dll": b"overlay x64", "x86_64-unix/ntdll.so": b"overlay unix",
            "x86_64-unix/win32u.so": b"patched win32u", "x86_64-unix/winex11.so": b"patched winex11",
        }
        overlay = dict(private_runtime.OVERLAY, **private_runtime.OPTIONAL_GROUPS[0])
        fingerprint = {dest: sha(base_files[dest]) for dest in overlay.values()}
        # Without the optional files fingerprinted the base check must fail.
        partial = {dest: sha(base_files[dest]) for dest in private_runtime.OVERLAY.values()}
        make_runtime_package(self.package, payloads=payloads, manifest_overrides={"base_files": partial})
        with self.assertRaisesRegex(private_runtime.Error, "incomplete base-Wine fingerprint"):
            private_runtime.assemble(self.package, self.base, self.root / "cache")
        make_runtime_package(self.package, payloads=payloads, manifest_overrides={"base_files": fingerprint})
        runtime = private_runtime.assemble(self.package, self.base, self.root / "cache2")
        for source, dest in overlay.items():
            self.assertEqual((runtime / dest).read_bytes(), payloads[source], dest)
            self.assertFalse((runtime / dest).is_symlink(), dest)
        self.assertEqual((runtime / "lib/wine/x86_64-unix/winewayland.so").read_bytes(), b"untouched")
        for name, data in base_files.items():
            self.assertEqual((self.base / name).read_bytes(), data, name)  # base never written
        private_runtime.verify(runtime, private_runtime.digest(self.package), self.base.resolve())
        (runtime / "lib/wine/x86_64-unix/winex11.so").write_bytes(b"tampered")
        with self.assertRaisesRegex(private_runtime.Error, "Private runtime changed"):
            private_runtime.verify(runtime, private_runtime.digest(self.package), self.base.resolve())

    def test_assembler_unlinks_overlay_symlinks_before_writing(self):
        external = self.root / "external"
        external.mkdir()
        targets = {
            "wine": external / "wine",
            "i386_ntdll": external / "i386-ntdll.dll",
            "unix_ntdll": external / "ntdll.so",
        }
        contents = {
            "wine": b"stock base wine",
            "i386_ntdll": b"stock base i386 ntdll",
            "unix_ntdll": b"stock base unix ntdll",
        }
        for key, path in targets.items():
            path.write_bytes(contents[key])

        (self.base / "bin").mkdir(parents=True)
        (self.base / "bin/wine").symlink_to(targets["wine"])
        i386 = self.base / "lib/wine/i386-windows"
        i386.mkdir(parents=True)
        (i386 / "ntdll.dll").symlink_to(targets["i386_ntdll"])
        x64 = self.base / "lib/wine/x86_64-windows"
        x64.mkdir(parents=True)
        (x64 / "ntdll.dll").write_bytes(b"stock base x64 ntdll")
        unix = self.base / "lib/wine/x86_64-unix"
        unix.mkdir(parents=True)
        (unix / "ntdll.so").symlink_to(targets["unix_ntdll"])

        package_files = {
            "bin/wine": b"overlay wine",
            "i386-windows/ntdll.dll": b"overlay i386 ntdll",
            "x86_64-windows/ntdll.dll": b"overlay x64 ntdll",
            "x86_64-unix/ntdll.so": b"overlay unix ntdll",
        }
        manifest, _ = make_runtime_package(self.package, payloads=package_files)
        for dest, source in private_runtime.OVERLAY.items():
            manifest["base_files"][source] = sha((self.base / source).read_bytes())
        # Rewrite the manifest with the real base fingerprints.
        with zipfile.ZipFile(self.package, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", json.dumps(manifest))
            for name, data in package_files.items():
                archive.writestr(name, data)

        runtime = private_runtime.assemble(self.package, self.base, self.root / "cache")
        for source, dest in private_runtime.OVERLAY.items():
            installed = runtime / dest
            self.assertFalse(installed.is_symlink(), dest)
            self.assertEqual(installed.read_bytes(), package_files[source])
        for key, path in targets.items():
            self.assertEqual(path.read_bytes(), contents[key], key)


class FakeRegistry:
    def __init__(self):
        self.values = {}

    def get(self, key, name):
        return self.values.get((key, name))

    def set(self, key, name, value):
        self.values[(key, name)] = value

    def delete(self, key, name):
        self.values.pop((key, name), None)


class PrivateAppTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="dllmgr-private-app-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.prefix = self.root / "prefix"
        self.drive_c = self.prefix / "drive_c"
        self.exe = self.drive_c / "Program Files/FastStone/FSViewer.exe"
        self.exe.parent.mkdir(parents=True)
        self.exe_bytes = b"synthetic verified FastStone executable"
        self.exe.write_bytes(self.exe_bytes)
        (self.prefix / "system.reg").write_text("WINE REGISTRY Version 2\n#arch=win64\n")
        dosdevices = self.prefix / "dosdevices"
        dosdevices.mkdir()
        (dosdevices / "c:").symlink_to(self.drive_c)
        self.base = self.root / "base-wine"
        (self.base / "bin").mkdir(parents=True)
        (self.base / "bin/wine").write_bytes(b"wine-11.0")
        for directory, arch in [('system32', 'x86_64'), ('syswow64', 'i386')]:
            data = ('stock ntdll ' + arch).encode()
            for path in [self.drive_c / 'windows' / directory / 'ntdll.dll',
                         self.base / 'lib/wine' / (arch + '-windows') / 'ntdll.dll']:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
        inf = self.base / 'share/wine/wine.inf'
        inf.parent.mkdir(parents=True)
        inf.write_text('stock Wine setup data')
        (self.prefix / '.update-timestamp').write_text(str(int(inf.stat().st_mtime)))
        self.runtime = self.root / "private-runtime"
        self.package = self.root / "runtime.zip"
        self.package.write_bytes(b"test package fingerprint")
        self.payloads = {
            "comctl32.dll": b"private patched comctl32 payload",
            "gdiplus.dll": b"private patched gdiplus payload",
        }
        self.original_exe_sha = private_app.EXE_SHA
        private_app.EXE_SHA = sha(self.exe_bytes)
        self.addCleanup(setattr, private_app, "EXE_SHA", self.original_exe_sha)
        self.data_home = self.root / "xdg-data"
        self.data_home.mkdir()
        self.old_env = os.environ.copy()

    def install(self, payloads=None, desktop_entry=None):
        args = SimpleNamespace(
            exe=self.exe,
            base_wine=self.base,
            runtime_package=self.package,
            fix="faststone",
            desktop_entry=[desktop_entry] if desktop_entry else [],
        )
        payloads = payloads or self.payloads
        with patch.object(private_app.platform, "machine", return_value="x86_64"), \
             patch.object(private_app.subprocess, "check_output", return_value="wine-11.0\n"), \
             patch.object(private_app, "runtime_package", return_value=self.package), \
             patch.object(private_app, "assemble", return_value=self.runtime), \
             patch.object(private_app, "modules", return_value=("faststone-v2", payloads)), \
             patch.dict(os.environ, {"XDG_DATA_HOME": str(self.data_home)}, clear=False):
            private_app.install(args, self.prefix.resolve())
        return args

    def state(self):
        state_dir = self.prefix / private_app.STATE
        paths = list(state_dir.glob("faststone-*.json"))
        self.assertEqual(len(paths), 1)
        return paths[0], json.loads(paths[0].read_text())

    def test_install_uses_exact_target_and_does_not_write_shared_prefix_dlls(self):
        windows = self.drive_c / "windows"
        windows.mkdir(exist_ok=True)
        shared = windows / "syswow64/gdiplus.dll"
        shared.parent.mkdir(parents=True, exist_ok=True)
        shared.write_bytes(b"stock shared gdiplus")
        system_before = (self.prefix / "system.reg").read_bytes()
        shared_before = shared.read_bytes()
        custom_desktop = self.data_home / "applications/custom-faststone.desktop"
        custom_desktop.parent.mkdir(parents=True)
        custom_desktop.write_text("before desktop entry\n")

        self.install(desktop_entry=custom_desktop)

        state_path, state = self.state()
        target = r"C:\Program Files\FastStone\FSViewer.exe"
        self.assertEqual(state["target"], target)
        self.assertEqual(state["exe"], str(self.exe.resolve()))
        self.assertEqual(state["exe_sha256"], sha(self.exe_bytes))
        self.assertEqual(shared.read_bytes(), shared_before)
        self.assertEqual((self.prefix / "system.reg").read_bytes(), system_before)
        self.assertFalse((self.prefix / "user.reg").exists())
        self.assertFalse((self.prefix / "fix-it-in-wine").exists())
        self.assertFalse((self.exe.parent / "comctl32.dll").exists())
        self.assertFalse((self.exe.parent / "gdiplus.dll").exists())
        desktop_text = custom_desktop.read_text()
        self.assertIn("Name=FastStone Image Viewer (dllmgr)", desktop_text)
        self.assertEqual(desktop_text.count('"run" "faststone"'), 1)
        installed = self.prefix / "drive_c/dllmgr/apps" / state["id"] / state["generation"]
        self.assertEqual({p.name for p in installed.iterdir()}, set(self.payloads))
        self.assertEqual(state_path.parent, self.prefix / private_app.STATE)

    def test_run_execs_exact_executable_and_private_dll_paths(self):
        self.install(payloads={"comctl32.dll": self.payloads["comctl32.dll"]})
        state_path, state = self.state()
        app_args = [r"C:\Images\image with spaces.png", "--view"]
        args = SimpleNamespace(exe=self.exe, app_args=app_args)
        captures = {}

        def capture_exec(path, argv, env):
            captures.update(path=path, argv=argv, env=env)

        with patch.object(private_app, "verify") as verify, \
             patch.object(private_app.os, "chdir") as chdir, \
             patch.object(private_app.os, "execve", side_effect=capture_exec), \
             patch.dict(os.environ, {
                 "DLLMGR_TARGET_EXE": "inherited-target",
                 "DLLMGR_COMCTL32": "inherited-comctl",
                 "WINEPREFIX": "inherited-prefix",
                 "WINELOADER": "inherited-loader",
                 "WINESERVER": "inherited-server",
             }, clear=False):
            private_app.launch(args, self.prefix.resolve())

        target = r"C:\Program Files\FastStone\FSViewer.exe"
        self.assertEqual(captures["path"], self.runtime / "bin/wine")
        self.assertEqual(captures["argv"], [str(self.runtime / "bin/wine"), target, *app_args])
        self.assertEqual(captures["env"]["WINEPREFIX"], str(self.prefix.resolve()))
        self.assertEqual(captures["env"]["WINEARCH"], "wow64")
        self.assertEqual(captures["env"]["WINELOADER"], str(self.runtime / "bin/wine"))
        self.assertEqual(captures["env"]["WINESERVER"], str(self.runtime / "bin/wineserver"))
        self.assertEqual(captures["env"]["DLLMGR_TARGET_EXE"], target)
        module_path = self.prefix / "drive_c/dllmgr/apps" / state["id"] / state["generation"] / "comctl32.dll"
        expected_module_path = "C:\\dllmgr\\apps\\" + state["id"] + "\\" + state["generation"] + "\\comctl32.dll"
        self.assertEqual(captures["env"]["DLLMGR_COMCTL32"], expected_module_path)
        self.assertNotIn("DLLMGR_GDIPLUS", captures["env"])
        self.assertEqual(module_path.read_bytes(), self.payloads["comctl32.dll"])
        chdir.assert_called_once_with(self.exe.parent)
        verify.assert_called_once_with(self.runtime, state["package_sha256"], Path(state["base"]))
        self.assertTrue(state_path.is_file())

    def test_tampered_private_module_blocks_status_and_uninstall_without_deleting_state(self):
        self.install()
        state_path, state = self.state()
        directory = self.prefix / "drive_c/dllmgr/apps" / state["id"] / state["generation"]
        module = directory / "gdiplus.dll"
        module.write_bytes(b"tampered")

        with self.assertRaisesRegex(private_app.Error, "Private DLL changed: gdiplus.dll"):
            private_app.checked_files(self.prefix, state)
        with self.assertRaisesRegex(private_app.Error, "Private DLL changed: gdiplus.dll"):
            private_app.uninstall(SimpleNamespace(fix="faststone", exe=self.exe), self.prefix.resolve())
        self.assertTrue(state_path.is_file())
        self.assertTrue(module.is_file())

    def test_uninstall_restores_prior_desktop_and_removes_owned_private_files(self):
        desktop = self.data_home / "applications/custom-faststone.desktop"
        desktop.parent.mkdir(parents=True)
        desktop.write_bytes(b"preexisting desktop\r\n")
        self.install(desktop_entry=desktop)
        _, state = self.state()
        directory = self.prefix / "drive_c/dllmgr/apps" / state["id"] / state["generation"]

        private_app.uninstall(SimpleNamespace(fix="faststone", exe=self.exe), self.prefix.resolve())

        self.assertFalse((self.prefix / private_app.STATE / (state["id"] + ".json")).exists())
        self.assertFalse(directory.exists())
        self.assertEqual(desktop.read_bytes(), b"preexisting desktop\r\n")
        default_desktop = self.data_home / "applications" / ("dllmgr-" + state["id"] + ".desktop")
        self.assertFalse(default_desktop.exists())

    def test_install_records_and_prints_versions(self):
        import contextlib, io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.install()
        _, state = self.state()
        self.assertEqual(state["runtime_release"], "local package " + str(self.package))
        self.assertIn("Versions: dllmgr ", out.getvalue())
        self.assertIn("modules faststone-v2", out.getvalue())

    def test_trampoline_uses_upgrade_stable_launcher_of_installed_copy(self):
        lib = self.root / "home/.local/lib/dllmgr"
        version = lib / ("a" * 40)
        (version / "scripts").mkdir(parents=True)
        (version / "dllmgr").write_text("#!/bin/sh\n")
        (version / ".dllmgr-revision").write_text("a" * 40 + "\n")
        link = self.root / "home/.local/bin/dllmgr"
        link.parent.mkdir(parents=True)
        link.symlink_to(version / "dllmgr")
        (self.prefix / "dosdevices/z:").symlink_to("/")
        with patch.object(private_app, "HERE", version / "scripts"), \
             patch.object(private_app.Path, "home", return_value=self.root / "home"):
            line = private_app.trampoline_line(self.prefix.resolve(), self.exe.resolve())
            self.assertEqual(private_app.dllmgr_version(), "aaaaaaa (installed)")
        self.assertTrue(line.startswith('"Z:' + str(link.parent).replace("/", "\\") + '\\dllmgr" run'), line)

    def trampoline_install(self, registry):
        import zipfile
        with zipfile.ZipFile(self.package, "w") as archive:
            archive.writestr(private_app.TRAMPOLINE_MEMBER, b"MZ trampoline proxy")
        (self.prefix / "dosdevices/z:").symlink_to("/")
        with patch.object(private_app, "trampoline_registry", return_value=registry):
            self.install()

    def test_trampoline_installed_with_companion_and_removed_on_uninstall(self):
        registry = FakeRegistry()
        self.trampoline_install(registry)
        proxy = self.exe.parent / "msimg32.dll"
        companion = self.exe.parent / "msimg32.dllmgr"
        self.assertEqual(proxy.read_bytes(), b"MZ trampoline proxy")
        line = companion.read_text()
        self.assertTrue(line.startswith('"Z:\\'), line)
        self.assertIn('\\dllmgr" run faststone --prefix "' + str(self.prefix.resolve()) + '" --exe "', line)
        self.assertTrue(line.endswith(str(self.exe.resolve()) + '" --\n'), line)
        key = "HKCU\\Software\\Wine\\AppDefaults\\FSViewer.exe\\DllOverrides"
        self.assertEqual(registry.values, {(key, "msimg32"): "native,builtin"})
        with patch.object(private_app, "trampoline_registry", return_value=registry):
            self.assertEqual(private_app.trampoline_status(self.prefix.resolve(), self.exe.resolve(), self.base), "ok")
            private_app.uninstall(SimpleNamespace(fix="faststone", exe=self.exe), self.prefix.resolve())
            self.assertEqual(private_app.trampoline_status(self.prefix.resolve(), self.exe.resolve(), self.base), "absent")
        self.assertFalse(proxy.exists())
        self.assertFalse(companion.exists())
        self.assertEqual(registry.values, {})

    def test_trampoline_reinstall_is_idempotent_and_foreign_proxy_is_kept(self):
        registry = FakeRegistry()
        self.trampoline_install(registry)
        with patch.object(private_app, "trampoline_registry", return_value=registry):
            self.install()
        self.assertTrue((self.exe.parent / "msimg32.dllmgr").exists())
        with patch.object(private_app, "trampoline_registry", return_value=registry):
            private_app.uninstall(SimpleNamespace(fix="faststone", exe=self.exe), self.prefix.resolve())
        (self.exe.parent / "msimg32.dll").write_bytes(b"MZ the user's own")
        with patch.object(private_app, "trampoline_registry", return_value=registry):
            self.install()
        self.assertEqual((self.exe.parent / "msimg32.dll").read_bytes(), b"MZ the user's own")
        self.assertFalse((self.exe.parent / "msimg32.dllmgr").exists())
        self.assertEqual(registry.values, {})

    def test_photoshop_profile_runtime_and_version_proxy_without_private_dlls(self):
        import zipfile
        ps = self.drive_c / "Program Files (x86)/Adobe/Adobe Photoshop CS2/Photoshop.exe"
        ps.parent.mkdir(parents=True)
        ps.write_bytes(b"synthetic verified Photoshop CS2")
        with zipfile.ZipFile(self.package, "w") as archive:
            archive.writestr("dllmgr-27/version.dll", b"MZ photoshop proxy")
            archive.writestr("dllmgr-27/msimg32.dll", b"MZ faststone proxy")
        (self.prefix / "dosdevices/z:").symlink_to("/")
        registry = FakeRegistry()
        args = SimpleNamespace(app="photoshop-cs2", exe=ps, base_wine=self.base, runtime_package=self.package,
                               fix="photoshop-cs2", desktop_entry=[], app_args=["C:\\a.psd"])
        with patch.dict(private_app.PROFILES["photoshop-cs2"], {"sha": (sha(ps.read_bytes()),)}), \
             patch.object(private_app, "trampoline_registry", return_value=registry), \
             patch.object(private_app.platform, "machine", return_value="x86_64"), \
             patch.object(private_app.subprocess, "check_output", return_value="wine-11.0\n"), \
             patch.object(private_app, "assemble", return_value=self.runtime), \
             patch.object(private_app, "modules", side_effect=AssertionError("no private DLLs for Photoshop")), \
             patch.dict(os.environ, {"XDG_DATA_HOME": str(self.data_home)}, clear=False):
            private_app.install(args, self.prefix.resolve())
            paths = list((self.prefix / private_app.STATE).glob("photoshop-cs2-*.json"))
            self.assertEqual(len(paths), 1)
            state = json.loads(paths[0].read_text())
            self.assertEqual((state["app"], state["files"], state["release"]), ("photoshop-cs2", {}, None))
            self.assertIsNone(private_app.checked_files(self.prefix, state))
            self.assertFalse((self.prefix / "drive_c/dllmgr/apps" / state["id"]).exists())
            self.assertEqual((ps.parent / "version.dll").read_bytes(), b"MZ photoshop proxy")
            self.assertIn(' run photoshop-cs2 --prefix "', (ps.parent / "version.dllmgr").read_text())
            self.assertFalse((ps.parent / "msimg32.dll").exists())
            key = "HKCU\\Software\\Wine\\AppDefaults\\Photoshop.exe\\DllOverrides"
            self.assertEqual(registry.values, {(key, "version"): "native,builtin"})
            desktop = self.data_home / "applications" / ("dllmgr-" + state["id"] + ".desktop")
            text = desktop.read_text()
            self.assertIn("Name=Adobe Photoshop CS2 (dllmgr)", text)
            self.assertIn('"run" "photoshop-cs2"', text)
            with self.assertRaises(private_app.Error):
                private_app.read_state(self.prefix.resolve())  # FastStone profile untouched
            captures = {}
            with patch.object(private_app, "verify"), patch.object(private_app.os, "chdir"), \
                 patch.object(private_app.os, "execve", side_effect=lambda p, a, e: captures.update(argv=a, env=e)):
                private_app.launch(args, self.prefix.resolve())
            self.assertEqual(captures["argv"][1], "C:\\Program Files (x86)\\Adobe\\Adobe Photoshop CS2\\Photoshop.exe")
            self.assertEqual(captures["env"]["DLLMGR_TARGET_EXE"], captures["argv"][1])
            self.assertNotIn("DLLMGR_COMCTL32", captures["env"])
            private_app.uninstall(args, self.prefix.resolve())
        self.assertFalse(paths[0].exists())
        self.assertFalse((ps.parent / "version.dll").exists())
        self.assertFalse((ps.parent / "version.dllmgr").exists())
        self.assertFalse(desktop.exists())
        self.assertEqual(registry.values, {})

    def test_running_on_tells_runtime_from_system_wine(self):
        proc = self.root / "proc"
        for pid, exe, lib in ((11, b"C:\\x\\Photoshop.exe\0", "/home/u/.local/share/dllmgr/runtimes/ab/lib/wine/x86_64-unix/winex11.so"),
                              (12, b"Z:\\y\\Photoshop.exe\0", "/opt/wine-stable/lib/wine/x86_64-unix/winex11.so"),
                              (13, b"python3 private-app.py run photoshop-cs2 Photoshop.exe\0", None)):
            (proc / str(pid)).mkdir(parents=True)
            (proc / str(pid) / "cmdline").write_bytes(exe)
            (proc / str(pid) / "maps").write_text("" if lib is None else "7f00-7f01 r-xp 0 00:00 1  " + lib + "\n")
        (proc / "self").mkdir()
        self.assertEqual(sorted(private_app.running_on("photoshop.exe", proc)),
                         [(11, "private runtime"), (12, "system Wine")])

    def test_routing_preserves_hidden_mime_entry_metadata(self):
        original = b'[Desktop Entry]\nName=Existing handler\nNoDisplay=true\nIcon=existing-icon\nExec=old-wine %f\n'
        desired = private_app.desktop_content(self.prefix, self.exe)
        routed = private_app.routed_desktop(original, desired)
        self.assertIn(b'NoDisplay=true\n', routed)
        self.assertIn(b'Icon=existing-icon\n', routed)
        self.assertIn(b'Name=Existing handler\n', routed)
        self.assertNotIn(b'Exec=old-wine', routed)
        self.assertEqual(routed.count(b'Exec='), 1)
        self.assertIn(b' -- %F', routed)

    def test_outdated_prefix_is_rejected_before_private_launch(self):
        private_app.verify_prefix(self.prefix, self.base)
        (self.prefix / '.update-timestamp').write_text('0')
        with self.assertRaisesRegex(private_app.Error, 'stock-Wine update'):
            private_app.verify_prefix(self.prefix, self.base)

    def test_interrupted_launcher_update_rolls_back_on_recovery(self):
        self.install()
        state_path, state = self.state()
        entry = state["desktops"][0]
        desktop = Path(entry["path"])
        before = desktop.read_bytes()
        changed = b"interrupted new desktop content\n"
        pending = dict(state, phase="pending", transaction=dict(previous=state,
            desktops=[dict(path=str(desktop), before_hex=before.hex(), after_sha256=sha(changed))]))
        private_app.save(state_path, pending)
        desktop.write_bytes(changed)
        private_app.recover(self.prefix.resolve(), state_path)
        self.assertEqual(desktop.read_bytes(), before)
        self.assertEqual(json.loads(state_path.read_text()), state)

    def test_recovery_does_not_overwrite_external_launcher_edit(self):
        self.install()
        state_path, state = self.state()
        desktop = Path(state["desktops"][0]["path"])
        before = desktop.read_bytes()
        pending = dict(state, phase="pending", transaction=dict(previous=state,
            desktops=[dict(path=str(desktop), before_hex=before.hex(), after_sha256=sha(b"candidate"))]))
        private_app.save(state_path, pending)
        desktop.write_bytes(b"external edit")
        with self.assertRaisesRegex(private_app.Error, "changed outside dllmgr"):
            private_app.recover(self.prefix.resolve(), state_path)
        self.assertEqual(desktop.read_bytes(), b"external edit")
        self.assertEqual(json.loads(state_path.read_text())["phase"], "pending")

    def test_modules_builds_only_selected_partial_recipe(self):
        raw = make_pe()
        name = "comctl32_v6-wine-11.0-i386.dll"

        def fake_download(url, dest, checksum=None, label=None):
            if dest.name == "SHA256SUMS":
                dest.write_text(sha(raw) + "  " + name + "\n")
            else:
                dest.write_bytes(raw)
            self.assertIn("/releases/download/winehq-59609-v2/", url)

        entry = {"kind": "fix", "id": "winehq-59609", "dlls": ["comctl32"],
                 "binaries": "https://github.com/unxed/dllmgr/releases/tag/winehq-59609-v2"}
        with patch.object(private_app.catalog_fixes, "resolve", return_value=["winehq-59609"]), \
             patch.object(private_app.catalog_fixes, "load_index", return_value=[entry]), \
             patch.object(private_app, "download", side_effect=fake_download):
            release, payloads = private_app.modules("winehq-59609", self.root)

        self.assertEqual(release, "winehq-59609-v2")
        self.assertEqual(set(payloads), {"comctl32.dll"})
        self.assertEqual(payloads["comctl32.dll"][0x40:0x60], bytes(32))
        self.assertFalse((self.root / "gdiplus-wine-11.0-i386.dll").exists())


class LaunchLogTest(unittest.TestCase):
    def test_keeps_the_last_twenty_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp)
            for i in range(25):
                private_app.launch_log(prefix, "run photoshop-cs2: step %d" % i)
            lines = (prefix / private_app.LAUNCH_LOG).read_text().splitlines()
            self.assertEqual(len(lines), 20)
            self.assertTrue(lines[-1].endswith("run photoshop-cs2: step 24"))
            self.assertIn(" pid %d " % os.getpid(), lines[0])

    def test_unwritable_prefix_is_ignored(self):
        private_app.launch_log(Path("/nonexistent/prefix"), "run faststone: started")


if __name__ == "__main__":
    unittest.main()
