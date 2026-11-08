# dllmgr-38: SetWindowFeedbackSetting shim for stock Wine

Photoshop 2024 aborts on `Unimplemented function USER32.dll.SetWindowFeedbackSetting`
(issue #38, PhialsBasement/wine-adobe-installers#6, WineHQ bug 60726). The
Wine-side fix is ../dllmgr-38.patch; this is the no-rebuild workaround for
users of stock Wine, Bottles or the Adobe fork (design:
docs/tasks/38-delivery.md).

`shim.c` is built as a version.dll proxy (`sh build.sh x86_64 out.dll`;
exports forward to kernelbase like patches/dllmgr-27/version.def). Put it
next to the exe with a load-order override for that exe
(`AppDefaults\Photoshop.exe\DllOverrides: version=native,builtin`, e.g. via
scripts/prefill-proxy.py). In DllMain it replaces the aborting stubs in the
import tables of all loaded modules, and of modules loaded later through
LdrRegisterDllNotification, with its own implementations of the measured
Windows semantics. If user32 exports the functions it does nothing.
`DLLMGR38_DEBUG=1` logs each patched slot, `DLLMGR38_OFF=1` disables it.

Verified 2026-11-09 on stock Wine 11.0 (sandbox stand): tests/wine/feedback-shim.sh
-> all 18 cases identical to Windows (tests/wine/fixtures/feedback-windows.txt),
a LoadLibrary'd DLL importing the function is patched too; without the shim
the same exe aborts with "Unimplemented function".

Open: which DLL Photoshop 2024 loads that can carry the proxy (version.dll is
assumed; `objdump -p Photoshop.exe | grep 'DLL Name'` from a user decides).
A Photoshop 2024 recipe (`dllmgr fix photoshop-2024`) comes after that.
