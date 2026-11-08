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
