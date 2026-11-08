# Photoshop / TopPlan handoff from the wine bugzilla chat

Received2026-11-08. The owner consolidated that chat's work into the dllmgr chat;
the source chat stopped its own work. This does not pause dllmgr. Continue the
atomic FastStone work separately and do not duplicate published Wine comments.
All native testing must use an invisible display and a separate prefix.

## Published evidence and remaining work

- [#31](https://github.com/unxed/dllmgr/issues/31): CS2 audit parent. Includes
  the owner's old reports34133–34137 and their parent reports, even closed ones.
- [#36](https://github.com/unxed/dllmgr/issues/36), splash background: white
  rectangle confirmed on stock Wine11.0 both by the owner and on headless Xvfb.
  [Wine34133 c5](https://bugs.winehq.org/show_bug.cgi?id=34133#c5) is already
  published. Preserve WONTFIX; c3 discusses reading existing background pixels
  and10091. Windows/background comparison and a solution remain outstanding.
  ClientSideGraphics workaround has not been tested.
- [#35](https://github.com/unxed/dllmgr/issues/35), Open dialog: OS1192x1136 →
  Adobe1520x1136 → OS1520x1136 physical X11 client size at192DPI. DPI-unaware
  Win32 outer604x602 →768x602 →768x602. Same OS HWND persists. Published:
  [Wine34134 c5](https://bugs.winehq.org/show_bug.cgi?id=34134#c5). Hooks record
  a requested768x602; min-track140x34 does not establish a MemDialogSize cause.
  Next: publicly resize OS to604x602, trace a full OS→Adobe→OS cycle, compare
  Windows or a synthetic API case before choosing a fix. No correction exists.
- [Wine33906 c9](https://bugs.winehq.org/show_bug.cgi?id=33906#c9), parent34137:
  three main-window minimize/restore cycles preserved the image/document on
  stock11.0, Xvfb/Metacity without compositing,192DPI. Workspace/other-WM cases
  untested; do not close the entire report from this result.
- [Wine11412 c25](https://bugs.winehq.org/show_bug.cgi?id=11412#c25), parent
  34135/34136: tool submenu painted above Tools; activating a native test window
  through the WM covered Photoshop palettes on Metacity. Five Alt+Tab attempts
  did not switch focus and are not successful switch tests. Intermittent,
  splash and other-desktop scenarios remain unproven; status unchanged.
- [#34](https://github.com/unxed/dllmgr/issues/34), TopPlan13594: no installer,
  no retest, no new Wine comment. Official links contain literal *key* and403.
  Exact CDX page history exists in work/topplan/cdx-pages.json; next extract
  historical official hrefs from archived HTML and verify binary snapshots.
  Domain-CDX timeout and questionable wildcard queries do not prove absence.

Wine comments above contain text only. Any further Wine feedback must also have
no code, code attachments or code links, and must avoid duplicate reports.

## Local stand: preserve and revalidate before use

Disposable cloud-sandbox rebuild of the stand: docs/sandbox-stand.md.

Root: /home/unxed/Documents/Codex/2026-11-07/pfl. Research: work/photoshop-cs2/
and work/topplan/. The independent2.6GB prefix is work/photoshop-cs2/prefix110;
never substitute the normal ~/.wine for it. Photoshop EXE SHA256:
98c746a4707a875f8077d79550f7129b459ae784de05b05f349f89ddecf56d30.

The extracted work/headless/root/usr/bin/Xvfb can be reused read-only on a new
free display. Do not delete it: FastStone's own:93 uses it too. Photoshop's
transient codex-ps-investigation.service and:94 were stopped at handoff. Its
headless.py can restart an owned isolated session; recheck display/unit/process
ownership, never trust old PID/HWND values or kill shared Wine servers.

windows.c/windows2.exe/windows3.exe enumerate/control public APIs. sizehook.c,
sizehook.dll, hookhost.c/hookhost.exe observe public window-position messages,
not a fix; sizehook110.log records attempts. Reattach to fresh GUI IDs, keep the
host alive, and distinguish DPI-unaware logical from physical coordinates.
Welcome/trial dialogs and120s startup can delay readiness; failed shortcuts or
black transitional screenshots are not evidence of a successful scenario.

Use stock /opt/wine-stable for baselines. The source work/wine-wine-11.0 and
work/wine110-runtime include an earlier conhost60210 change; neither should be
mistaken for a pristine baseline. work/build110 lacks X/Wayland and is not a
ready32-bit CS2 DLL build. Extracted11.21 exists but CS2 has not been tested on it.

## Owner-applied cross-repository patch

[fix-it-in-wine#13](https://github.com/unxed/fix-it-in-wine/issues/13) contains
an unapplied catalog-format1 compatibility patch, with26 passing catalog tests
and a live current-index read. Local outputs/fix-it-in-wine-catalog-format1.patch
and work/catalog-fix/ preserve it. Do not claim merged or edit another shared
checkout; the owner applies changes to other unxed repositories.

## Separate cloud test environment

The reproducible Wine 11.0 / Xvfb cloud stand is documented in
[cloud-wine-sandbox.md](cloud-wine-sandbox.md), with pinned packages and setup
scripts in `tools/wine-sandbox/`. It does not contain the local trial prefix
or establish a Photoshop retest. The cloud host cannot run Linux i386 ELF
natively; use the documented full-system QEMU fallback for 32-bit Wine.

## Sandbox session checkpoint (2026-11-08 19:50, Claude cloud sandbox)

Start a new session with docs/sandbox-agent-hints.md (stand, CS2 install,
token-cheap GUI work). State on main:

- #27 FastStone first-open flash: fixed Wine-side by patches/winehq-60721.patch,
  delivered through private runtime v2 (scripts/private-runtime.json, release
  app-isolation-wine-11.0-v2). Owner test pending:
  `dllmgr uninstall faststone && dllmgr fix faststone`. PE-only fallback:
  patches/dllmgr-27 (msimg32 proxy, removes white, 15-28 ms black remains).
- #36 CS2 splash white rectangle: cause = Photoshop composes the splash over
  its own window's initial 0xff surface. Fixed on stock Wine by the same
  prefill code as a version.dll proxy (`patches/dllmgr-27/build.sh version`,
  install with scripts/prefill-proxy.py). experiments/photoshop-splash/.
  Open: faint 1 px line at the splash window edge (not compared with Windows).
- #35 / Wine 34134 Open dialog width: Adobe's versioncueui.dll itself resizes
  the OS dialog to the Adobe dialog rect; Wine just executes it. Needs one real
  Windows run to decide. experiments/ps35-open-dialog/.
- Findings to fix last: docs/sandbox-findings.md (F1-F19).
- Not yet touched in the sandbox: #11412 (submenu vs Tools palette, palettes
  above other apps), #34 TopPlan.
