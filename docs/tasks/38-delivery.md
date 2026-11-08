# #38 delivery: SetWindowFeedbackSetting for users of stock Wine

State 2026-11-09 (Opus design, agent claude-cloud-ada0). The Wine-side fix
is patches/dllmgr-38.patch (user32, PE side), sent to WineHQ as bug 60726
in words. Users of stock Wine 11.0 / Bottles / the Adobe fork need it now,
without rebuilding Wine.

## Options (fix strategy ladder: workaround -> Wine constructor -> ReactOS)

A. **Import shim in a proxy DLL (recommended first).** The loader cannot
   find the two exports and puts the address of an aborting stub into the
   importing module's IAT; nothing calls it before the app opens an image.
   A proxy DLL that the app loads anyway (as patches/dllmgr-27 does with
   version.dll / msimg32.dll) walks, in its DllMain, every loaded module's
   import descriptors for `user32.dll`, finds the thunks named
   `SetWindowFeedbackSetting` / `GetWindowFeedbackSetting` (by name through
   OriginalFirstThunk; MSVC images have it) and writes its own
   implementations into those IAT slots. Modules loaded later are handled
   with LdrRegisterDllNotification (Wine implements it). The implementations
   follow the measured Windows semantics of the 19 cases (the same logic as
   the patch: per-window properties, validation, NULL-config reset, ancestor
   lookup, size query, last error untouched on success).
   Pros: any Wine version, Bottles, the fork; one small file next to
   Photoshop.exe plus an AppDefaults override, reversible with
   scripts/prefill-proxy.py. Cons: only works if a proxy-able DLL is loaded
   before the first call (practically always: DllMain runs before the exe's
   entry point).
B. **PE overlay in the private runtime (Wine constructor).** Add an optional
   group `{i386-windows,x86_64-windows}/user32.dll` to
   scripts/private_runtime.py; builtin DLLs load from the runtime's lib dir,
   so the prefix stays unchanged. Needs private-app.py generalised beyond
   FastStone (exe hash, profile per app) and a runtime release. Keep for
   when a fix needs real user32/win32u internals.

Decision: A now (fast user feedback, RUP), B only when a fix cannot be done
from outside the module.

## Unknowns (fail fast: ask, do not guess)

1. Which module of Photoshop 2024 imports the functions (Photoshop.exe or a
   DLL), and which of its imports can carry the proxy (version.dll,
   msimg32.dll, winmm.dll, ...). Needs `objdump -p` of the user's
   Photoshop.exe (we do not have Photoshop 2024). Until then the shim
   patches all loaded modules and later loads, so only the entry DLL is
   open.
2. Whether the fork's users run 64-bit Photoshop only (2024 is x86_64): the
   shim is built for x86_64 then; i686 build only if a 32-bit app needs it.

## Test plan (no Photoshop needed)

- tests/wine/feedback-setting.c already imports the functions statically
  and aborts on stock Wine. Variant: also import version.dll (call
  GetFileVersionInfoSizeW once) so a version.dll proxy is loaded first.
- Stock Wine 11.0 + proxy + `WINEDLLOVERRIDES=version=n,b`: all 19 cases
  print the Windows results (docs: tests/wine/feedback-get.c output from
  the windows-probes CI job). Without the override: abort (control).
- A module loaded with LoadLibrary after start that imports the functions:
  patched through the DLL notification.
