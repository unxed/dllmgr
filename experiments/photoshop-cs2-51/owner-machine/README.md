# #51: owner-machine investigation

## 2026-11-10 — preflight blocked

Agent: `opencode-owner-51a7`.

Task: `docs/tasks/51-local-agent.md`. Read AGENTS.md, the multi-agent
protocol, console-agent instructions, task-card index and Photoshop handoff.
Claimed issue #51 before investigating.

Read-only prerequisite check:

```sh
command -v Xvfb muffin xdotool wmctrl dllmgr wine wineserver
```

Output (no path was returned for `Xvfb`):

```text
/usr/bin/muffin
/usr/bin/xdotool
/usr/bin/wmctrl
/home/unxed/.local/bin/dllmgr
/usr/bin/wine
/usr/bin/wineserver
```

The source prefix occupies 2.6 GiB; the filesystem containing
`/tmp/opencode` has approximately 23 GiB available. No environment variable
values or credentials were collected.

Stopped at the task's explicit Xvfb prerequisite. No prefix was copied or
changed, no Wine process was started, and no desktop windows were opened.
There is no disposable prefix to remove. Steps 1–4 have **not** been run;
there are no new launch logs and no reproduction or cause established.

Next: owner installs Xvfb (`sudo apt install xvfb`), then resume step 1
using an agent-owned disposable copy and `scripts/sandbox-stand.sh session`
with a free private display and Muffin. Never use the owner's desktop or
run against the original `~/.wine`.

## Resumed after Xvfb installation — reproduced

All Wine executions used the disposable copy
`/tmp/opencode/opencode-owner-51a7/prefix`, Xvfb `:151`, Muffin and
`scripts/sandbox-stand.sh session`. The source `~/.wine` was read only to
copy it. No far2l reproduction was needed: a direct plain launch reproduces.
Installed dllmgr: `719ddb2`; CI-built runtime: v11, package SHA256
`8ef0d5ae10a37aaae5aa80f11d079dc682a4d58e49bf361aac0d4495979ae091`.
No locally built proxy was substituted.

### Setup and commands

```sh
mkdir -p /tmp/opencode/opencode-owner-51a7
cp -a ~/.wine /tmp/opencode/opencode-owner-51a7/prefix
python3 experiments/photoshop-cs2-51/owner-machine/prepare.py
env STAND_DIR=/tmp/opencode/opencode-owner-51a7 STAND_DISPLAY=:151 \
  STAND_WM=muffin WINEPREFIX=/tmp/opencode/opencode-owner-51a7/prefix \
  sh scripts/sandbox-stand.sh session \
  sh experiments/photoshop-cs2-51/owner-machine/step1.sh
```

`prepare.py` relocates copied dllmgr ownership metadata, clears its desktop
ownership list, replaces personal-folder symlinks inside the copy with empty
directories, and isolates generated desktop entries with `XDG_DATA_HOME`.
The existing installed runtime cache is reused, not rebuilt. The trampoline
companion is checked to point at the **copy** before launching Photoshop.
Historical logs copied from the owner prefix are removed before the test.

An initial setup-only invocation stopped because `wineserver -k` returned 1
with no server running. Recipe setup had succeeded; no Photoshop launch had
occurred. `step1.sh` now tolerates that cleanup status. This was a harness
error, not a Photoshop result.

For steps 2–4, use the same `env ... sh scripts/sandbox-stand.sh session`
wrapper, with command
`python3 experiments/photoshop-cs2-51/owner-machine/observe.py` and
`STEP=step2`, `STEP=step3`, or `STEP=step4` added to `env`.
Each invocation is a separate session; teardown kills only the copy's server.
`collect.py` retains the relevant text evidence in `results/`.

### Results

1. **Plain launch:** after 45 s, status reports a Photoshop PID on system
   Wine. The private runtime ends with code **0 after 0.3 s**. Its stderr
   has only the attempt header. See `results/step1/`.
2. **Stock debug:** `DLLMGR27_DEBUG=1`, stderr and window-list polling at
   0.2 s intervals. A Photoshop window is listed at **2.079 s**;
   `trampoline armed` arrives at **2.519 s**. The stock side closes
   `PS3.0.5WIN` handle `0x90` at **3.079 s**, starts the launcher at
   **3.389 s**, then falls back at **18.431 s**. Thus a window already
   exists when the trampoline is armed; the v11 mutex close does happen.
   See `results/step2/`.
3. **Manual private launch beside stock:** stock starts with
   `DLLMGR27_NO_TRAMPOLINE=1`; its main titled window is listed from
   **2.802 s**, and the private command runs after 45 s.
   `WINEDEBUG=+loaddll,+process dllmgr run ...` returns **1 in 1.419 s**
   (not the trampoline's exit-0 result). It loads and unloads Photoshop.dll,
   PSViews.dll and PSArt.dll, without loading VERSION.dll. These are two
   different startup contexts; do not equate their exit codes.
   See `results/step3/private.log`.
4. **Actual trampoline with filtered relay:** the task's RelayInclude is
   set only in the copied registry, then the normal stock start runs with
   `DLLMGR27_DEBUG=1 WINEDEBUG=+relay,+loaddll`. Filtered kernel32/user32
   implementations are Wine **builtin** DLLs (provenance retained in the
   log); no native Microsoft component is relay-traced or disassembled.
   Stock again closes its mutex, but the private instance executes:

   ```text
   CreateMutexW(..., "PS3.0.5WIN") -> handle 0x98
   load Photoshop.dll, PSViews.dll, PSArt.dll
   FindWindowW("Photoshop", NULL) -> HWND 0x10068
   unload Photoshop.dll, PSViews.dll, PSArt.dll
   ExitProcess(0)
   ```

   No VERSION.dll load occurs. The stock process had already created its
   Photoshop-class window and remains waiting until fallback. This directly
   reproduces the owner's clean early exit, rather than a DLL-load failure.
   See `results/step4/`.

### Established cause and limits

The v11 handover leaves the stock Photoshop window alive. The private
Photoshop's single-instance startup finds a Photoshop-class HWND and exits
successfully before loading the signaling proxy. Closing the stock mutex
alone is insufficient on this installed copy. Far2l is not required to
trigger this failure; increasing the 15 s wait cannot make an already
exited private process signal.

The relay filter does **not** record GetLastError after CreateMutexW, so
the trace does not establish its last-error value or every internal branch.
The HWND is not independently mapped back to a PID with a Win32 helper;
the only Photoshop launched before the private attempt is the stock one.
The registered-versus-trial difference has not been isolated as a cause.
No fix was attempted: a safe way to avoid the surviving stock-window
single-instance check still needs a separately tested before/after change.
No upstream report is implied; this is dllmgr's handover behavior.

### Validation and cleanup

`git diff --check`, Python compilation of the three helpers, and `sh -n`
for step1.sh passed. Retained logs were checked for common token/key/password
markers; none were found. Environment differences contain names only.
After collection, the copy's wineserver was confirmed absent (`-k` returned
1); the exact disposable prefix directory above was removed. Xvfb/Muffin
were torn down by each session. The original prefix was never a run target.
