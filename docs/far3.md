# Far Manager 3 under Wine: plan

Status: plan, 2026-11-06. Written so that a smaller model (Sonnet) can pick up
any step. Work in small atomic commits; push each one; KISS; fail fast.
Lunobot tracking issue: https://github.com/unxed/lunobot/issues/322.

## Why Far3, and who works on it

Far Manager 3 is a console file manager. It needs no fonts, no GPU, no X11
and no real mouse, so a headless cloud runner reproduces what a user sees.
Rule (D21): when a GUI task (FastStone and similar) is blocked on the owner's
desktop, cloud sessions work on Far3 instead.

Far3 is open source (BSD). Use the official portable x64 and x86 builds from
https://github.com/FarGroup/FarManager/releases; record version and SHA256
like the FastStone profile. f4 (https://github.com/unxed/f4) is the owner's
own clone; it is not the target here.

## Goal 1: start fast

Far is an everyday tool: startup time is a feature. Target: a warm start of
`far.exe` to a usable panel in well under a second, close to Windows.

Measure before changing anything (report median of 10 runs, cold and warm):

1. Time from exec to first panel output, in three setups:
   - Wine console on the Unix terminal (`wine far.exe` from a TTY or `script`
     pseudo-terminal) — the main case;
   - `wineconsole` (conhost window) for comparison;
   - Windows runner (`windows-latest`) as the reference.
2. Split the time: wineserver start, prefix initialization (`wineboot`), DLL
   loading (`WINEDEBUG=+loaddll` once, never while timing), Far's own init.

Startup levers to test one at a time (keep each only with numbers):

- A persistent wineserver (`wineserver -p`) so warm starts skip it.
- No graphics: `WINEDLLOVERRIDES` disabling the display driver for the Far
  process (e.g. `winex11.drv,winewayland.drv=d`) and no `DISPLAY`; check Far
  still works on the Unix console backend.
- No Mono/Gecko prompts or loads: `mscoree,mshtml=d` in the prefix used for
  Far; a dedicated minimal prefix created once.
- `WINEDEBUG=-all`.
- Which DLLs Far imports (static check) versus what Wine loads anyway; any
  avoidable load is a candidate fix.

Each lever that helps becomes either a recipe setting (dllmgr) or a Wine
fix in the catalog, with `results` rows (environment + before/after times).

## Goal 2: fix the console bugs

Audit WineHQ Bugzilla first (read every comment): quick search
https://bugs.winehq.org/buglist.cgi?quicksearch=far%20manager returns many
unrelated hits (Far Cry, window managers). Known title matches: 50606 (TTY
resize), 51650 (console support), 59724 (console colors), 59130 (startup
hang). Read linked console bugs too. Separate the Unix-terminal backend from
the conhost window.

Per bug, same pipeline as FastStone:
1. A console reproducer (C, mingw) that fails on stock Wine and passes on
   Windows; console output is plain text, so checks are exact.
2. A fix, a catalog entry `catalog/fixes/winehq-N.md` with the four headings
   (Problem, Windows behavior, The fix in words, Results) and `results` rows.
3. A composed recipe `catalog/bundles/far3-all.md` with a measured profile.
Most console code lives in Unix-side or core parts (conhost, kernelbase,
ntdll); check D-rules on what can be replaced before planning an install.

## Ideas for later (not planned work)

- **winescape in Far3.** Support https://github.com/unxed/winescape so Far
  under Wine calls native host APIs and looks and works like a native app.
  Open question first: do the trampolines out of Wine cost time per call? If
  they slow down hot paths (directory listing, console output), the idea
  fails. Benchmark: N calls through the trampoline versus the Win32 path
  versus native, per operation, on directory listings of 10k files. If slow,
  look for speedups on the Wine side (batching, a cheaper transition), in
  dllmgr (a patched module that takes the fast path), or in Marwin
  (https://github.com/unxed/Marwin), which has no Wine layer to cross.
- **Marwin as a Far3 target.** The same catalog and checks serve Marwin (D7);
  compare Far3 startup under Marwin and Wine once Marwin runs it.

## How to hand over

Update this file's status line and add a dated "Next step" line at the end
whenever a session stops, with the last measured numbers.

Next step: Goal 1, measurement 1 on a CI runner (Linux, Wine 11.0 from
winehq-stable, and windows-latest), portable Far3 x64 latest stable.
