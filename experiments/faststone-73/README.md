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
