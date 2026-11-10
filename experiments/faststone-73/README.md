# #73: Association Settings button does nothing under `dllmgr run` (v20)

Cause: `dllmgr run` sets DLLMGR_TARGET_EXE, and for it the msimg32 proxy
(built without DLLMGR27_ACTIVE_IN_RUNTIME) returned from DllMain before the
ShellExecuteA hook was installed. The earlier stand check ran the proxy
without DLLMGR_TARGET_EXE, so it missed this.

Fix: install the hook before that early return (prefill.c), plus a source
order test (AssocHookOrderTest in scripts/tests/test_private_app.py).

Stand check (`t73b.sh`, rt-cur3, :96, the same env as `dllmgr run`):
F12, Associations tab (1661,609), Association Settings button (1387,812):
- v20 proxy: no command run;
- fixed proxy: DLLMGR73_ASSOC command runs (`touch OUT/hit` appears).

## 2026-11-10 19:20: runtime v21 candidate (CI run 42871864489), owner's path

`t73c.sh` on the owner's laptop stand (console agent, isolated HOME,
Xvfb + Muffin, Russian UI): `dllmgr run faststone` with the recipe installed
from the v21 package, F12, "Ассоциации" tab, "Настройки ассоциаций" button
-> dllmgr's zenity checklist "File types for FastStone" opens
(v21-button-dialog.png). No hand-set variables: everything comes from
`dllmgr run`.
