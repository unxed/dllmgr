# #27 follow-up: fixes must work for every FastStone launch path

Owner, 2026-11-08 19:55: `dllmgr run faststone -- file` shows no flash (v2
runtime works), but normal launches (Wine menu, file-manager double click,
`wine FSViewer.exe`) bypass the private runtime, so the flash and **all**
private FastStone fixes are missing there. Goal ("apple way"): no special
command; whatever starts FSViewer.exe gets the fixes.

Ideas, in planned order (RUP):

1. Backstop for any launch path: install the prefill proxy
   (patches/dllmgr-27, msimg32 entry) with `dllmgr fix faststone` via
   scripts/prefill-proxy.py. Stock Wine then has no white flash (<=1 frame
   black). Open: delivery of the binary — private path refuses local builds
   (apply-faststone-fix.sh), so ship the proxy in the CI-built runtime
   package (needs a new release; see autonomy question below).
2. Auto-route launchers: at `fix` time find the Wine .desktop/MIME entries
   that lead to this exe and route them through the private runtime
   (reversible, like --desktop-entry). Caveat: Wine menu entries point at
   .lnk files and MIME entries at `wine start /ProgIDOpen <ProgID>`, so
   resolving them to the exe needs the .lnk target / HKCR open command.
3. Universal trampoline: the proxy, when loaded in FSViewer.exe under stock
   Wine (no DLLMGR_TARGET_EXE in env), relaunches the same command line
   through the private runtime and exits. **Feasibility proven 2026-11-08:**
   a Windows process under Wine 11.0 can start a native ELF binary with
   CreateProcessW (tests/wine/spawn-unix.c: `wine spawn-unix.exe
   'Z:\usr\bin\touch' FILE` -> "started, exit=0", file created; `cmd /c`
   refuses non-.exe names, CreateProcessW does not). Risks to handle:
   FastStone single-instance forwarding, double start cost, env/cwd/args
   passing, recursion guard (env var), prefix lock.

Autonomy (owner question): releases cannot be created from the cloud
session (HTTP 403 "not permitted for this session type"). Proposal waiting
for the owner's decision: a publish-runtime.yml workflow_dispatch (run id
-> verify SHA256SUMS -> gh release create with the Actions token) plus
standing permission to publish runtime releases after tests pass.

Also done in this session: progress bars for runtime download/copy/check
(843e466), `dllmgr diag` read-only report (d5feb3d).

## Trampoline design (Opus, 2026-11-08 23:40)

Measured facts:
- A Wine process can start a native ELF with CreateProcessW; the command line
  is split Windows-style (double quotes, not single).
- The native child inherits the Unix environment of the Wine process
  (WINEPREFIX, PATH, HOME, custom variables) and its Unix cwd.
- `private-app.py run` (= `dllmgr run faststone -- ARGS`) passes arguments
  that are not existing Unix files unchanged, so Windows paths from menu and
  MIME launchers (`Z:\...`, `C:\...`) reach FastStone as given; it then
  execve()s the private runtime with WINEPREFIX of the caller. The private
  runtime's wineserver is an unmodified copy of the base one (same protocol),
  so a stock-Wine process and a private-runtime process may share a prefix.

Design (implement in this order, each step tested):
1. Where: the proxy DLL already loaded into FastStone under any Wine
   (msimg32 for FastStone 8.5). Install it with `dllmgr fix faststone`
   (CI-built binary; FS-1 step 1).
2. When: only if `DLLMGR_TARGET_EXE` is absent (stock Wine, not the private
   runtime) and `DLLMGR_TRAMPOLINED` is absent (loop guard).
3. Not in DllMain (loader lock): DllMain only hooks the exe's first
   window-creating import (`CreateWindowExW`/`CreateWindowExA`, IAT slots
   matched by address as in prefill.c). On the first call, before any window
   exists: build the command `dllmgr run faststone -- <original args>` from
   GetCommandLineW (keep FastStone's own argument quoting), set
   DLLMGR_TRAMPOLINED=1 in the environment, CreateProcessW the launcher with
   the absolute Unix path written at install time into a companion file next
   to the proxy (`msimg32.dllmgr`, hash-checked by `status`), then
   ExitProcess(0) without returning to the app.
4. Fail-safe: if the companion file is missing, the launcher cannot be
   started, or the child exits non-zero within ~2 s, continue normally under
   stock Wine (the prefill backstop still removes the white flash). Never
   loop, never show a dialog.
5. Single instance: FastStone forwards a second start to the running
   instance. Test both orders: private running + stock launch (second start
   must reach the private instance), and nothing running.

Measured 2026-11-08 (stock Wine 11.0, Metacity, :96, tests in
/home/claude/work/tramp/single.sh): FastStone 8.5 is single-instance. Start A
(`a.jpg`, window after 8 s), then B (`b.jpg`): within 1 s the running window
shows `b.jpg - FastStone`, there is still exactly 1 FSViewer.exe process and
the second launcher has exited. So a trampolined start while a private
instance runs is forwarded there and exits; the trampoline must not treat a
quick exit 0 of the child as failure.

Remaining measurements before coding step 3: exit status
of `dllmgr run` while the target keeps running (execve: it is the target's
own lifetime, so step 4 must not wait for exit — only watch for an early
failure); cost of the extra start (time from double click to first image,
stock vs trampolined, Metacity, 5 runs each).

Measured 2026-11-08 (tests/wine/spawn-env.c, stock Wine 11.0, 64- and 32-bit
callers): CreateProcessW of a Unix program (ELF or `#!` script) succeeds and
the script runs with Windows-split arguments and the caller's cwd, but
1. `pi.hProcess` is not waitable (WaitForSingleObject -> WAIT_FAILED) and
   GetExitCodeProcess gives nothing: the caller cannot see the child's exit;
2. variables set with SetEnvironmentVariableW in the caller do NOT reach the
   Unix child (it gets the Unix environment the Wine process started with).

Design changes forced by this:
- Loop guard: not an env variable. The private runtime itself is the guard:
  `dllmgr run` sets DLLMGR_TARGET_EXE (Unix env, inherited by the private
  FSViewer.exe) and the proxy does nothing when it is set; `dllmgr run` never
  falls back to stock Wine, so there is no path back to the trampoline.
- Fail-safe: the stock process creates a named event, starts the launcher
  and waits up to DLLMGR27_TRAMP_WAIT ms (default 15000). The proxy inside
  the private FSViewer.exe (DLLMGR_TARGET_EXE set) opens that event in
  DllMain and sets it. Set -> the stock process ExitProcess(0)s (the private
  instance either shows the window or forwards to an already running one).
  Timeout or launcher not startable -> continue under stock Wine with the
  prefill backstop. One event name per prefix (`dllmgr27-trampoline`):
  two stock launches at the same second may both exit on one signal; both
  then end up forwarded to the private instance, which is the intent.
- When: per-thread WH_CBT hook, HCBT_CREATEWND of the first window in the
  process (before any window exists; no IAT matching needed).
