# FastStone task cards

Context: docs/handoff.md, docs/faststone.md, issues #8 #21-#23 #27-#30.

## FS-1 (#27) fixes on every launch path

Decided design (docs/tasks/27-every-launch-path.md), do it in this order:
1. Backstop: ship the msimg32 prefill proxy (patches/dllmgr-27, `build.sh
   msimg32`) inside the next runtime package (CI build, file
   `i386-windows/dllmgr-27-msimg32.dll` listed in the manifest) and make
   `dllmgr fix faststone` install it with scripts/prefill-proxy.py for the
   target exe. Test: stock `wine FSViewer.exe IMAGE` -> no white phase
   (tests/wine/first-open-x.sh, Metacity, 3 runs).
2. Trampoline (escalate the details to Opus before coding): the proxy, when
   FSViewer runs under stock Wine without DLLMGR_TARGET_EXE, re-executes the
   same command line through the private runtime launcher and exits. Proven:
   CreateProcessW starts native ELF (tests/wine/spawn-unix.c). Open
   questions to answer with measurements, not guesses: FastStone single
   instance behaviour, how args/cwd/env pass, recursion guard.
Stop and ask if: the runtime package needs a format change beyond adding a
file (that is a private_runtime.py manifest change: claim scripts/ files).
Owner verification is the acceptance: ask them to launch the way they
normally do (menu/file manager) and send `dllmgr diag`.

## FS-2..: issues #21 #22 #23 #28 #29

Follow docs/handoff.md per issue. Rules from this session that apply:
judge by X pixels; Metacity for flicker; DPI-unaware coordinates; owner tests
on their laptop with `dllmgr diag` attached to every report.
