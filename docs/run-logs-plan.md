# Plan: always-on run logs and a one-command log bundle (#71, #76)

Owner, 2026-11-11: a crash such as #76 (page fault photoshop+0xb249ce
reading 0x76bb1800) must be catchable without preparation, and sending the
logs must be trivial: zip one folder, send it.

## Logging (on by default)

- `dllmgr run APP` (and the menu entries, which call it) writes one log per
  start to `~/.local/share/dllmgr/logs/APP/YYYY-MM-DD_HH-MM-SS.log`.
- Content, kept small:
  - `WINEDEBUG=+loaddll,+seh` (module load/unload, exceptions);
  - on a crash: winedbg's automatic backtrace and module list;
  - a last line with how the program ended: normal exit, crash
    (exception code, address, module+offset) or signal.
- Rotation: the last ~20 starts per application; older files are removed.
- Setting to turn it off: `dllmgr set APP logs=off` (default on; no app
  feature is switched off).
- Logs stay local; nothing is sent anywhere.

## Bundle for the owner

```sh
dllmgr logs APP
```

Writes `~/Downloads/dllmgr-logs-APP-DATE.zip` (or `~/Загрузки`, per XDG) with
the recent logs plus versions (dllmgr commit, runtime release, recipe/module
release, Wine prefix arch) and prints its path. Optional anonymising of the
user name in paths.
Manual alternative: zip `~/.local/share/dllmgr/logs/APP`.

## Why this catches #76

0x76bb1800 is a typical DLL address range: likely a read from a module that
was unloaded, or from data inside a DLL. `+loaddll` shows what was mapped at
0x76bb0000 and whether it was unloaded before the fault; the winedbg dump
gives the stack. Static disassembly of photoshop+0xb249ce shows whose
pointer is read (vtable, import table, callback).

Status: plan only, not implemented.
