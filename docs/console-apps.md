# Far Manager 3 and hiew under Wine

Owner additions, 2026-11-07. This is a documented backlog; do not start hiew
or terminal-protocol implementation during the active FastStone work.
Project tracking: https://github.com/unxed/dllmgr/issues/18.
Far3's existing standing Lunobot assignment is
https://github.com/unxed/lunobot/issues/322. Its detailed plan is [far3.md](far3.md).

## Application coverage

Bring both official Far Manager 3 and hiew to Windows-equivalent behavior
through Wine fixes delivered by dllmgr. Keep a feature matrix, individual
reproducers/fixes, composed application selections and complete rollback.
Do not patch the applications to conceal Wine defects. Distinguish the Unix
terminal backend from wineconsole/conhost, Wine versions and x86/x64 builds.
Headless console checks do not prove physical keyboard, clipboard or mouse parity.

hiew's initial report is
[WineHQ 57281: hiew32demo.exe rendering problems](https://bugs.winehq.org/show_bug.cgi?id=57281).
It reports Wine 9.0 and reproduces with the official demo from
https://hiew.ru/files/hiew32demo.zip:

```sh
wine hiew32demo.exe hiew32demo.exe
```

Compare against Windows and wineconsole: the reporter says wineconsole renders
correctly. Attachment 77236 is the incorrect-rendering reference. Pin the demo
version/hash and recheck current Wine before deciding whether a fix is needed.
Use a synthetic binary as the ordinary fixture. Keep hiew separate from the
owner's other editor/disassembler projects.

## Advanced terminal keyboard input

[WineHQ 57078](https://bugs.winehq.org/show_bug.cgi?id=57078) originally requests
the kitty keyboard protocol because combinations such as Ctrl+Enter, used by
Far, are not expressible through the usual terminal input. Comment 1 also
requests win32 input mode.

Owner priority: implement at least one advanced protocol for Wine's Unix
console path, starting with **win32-input-mode**, as specified in
[Improved keyboard handling in ConPTY](https://github.com/microsoft/terminal/blob/main/doc/specs/%234999%20-%20Improved%20keyboard%20handling%20in%20Conpty.md).
Keep kitty as a related alternative, not a prerequisite for the first step.
The future acceptance matrix must include modifiers, Ctrl+Enter, key down/up,
repeat events, Unicode, negotiated enable/disable behavior, escape-sequence
fragmentation and restoration of the terminal when the application exits.
Verify against a compatible terminal and actual Far3/hiew interactions.

## Clipboard and longer-term extensions

- Add **OSC52 clipboard write** support for copying from the Wine console
  application to the host clipboard. Clipboard read/query is outside this
  request. Define behavior when the host terminal lacks support or has limits;
  test Unicode, large payloads and error/fallback behavior.
- Ideally implement relevant **far2l terminal extensions** afterwards. Inventory
  the documented capabilities before choosing a subset; do not claim protocol
  support from an untested subset. Preserve a safe fallback on other terminals.

Routes for the Unix side to evaluate first: https://github.com/unxed/winescape
and https://git.howett.net/DHowett/WinUnixPtyBridge (Dustin Howett, Microsoft
terminal team, a for-fun project); see docs/plans/far3.md.

Most affected Wine console code is core or Unix-backed. These changes need a
supported patch/runtime mechanism; they cannot be installed as ordinary native
DLL overrides. All new scope above is plan only until scheduled. Wine receives
owner-posted words-only reports; code and exact-SHA CI evidence stay in dllmgr.

## Route comparison (Opus, 2026-11-09)

Read from the sources (winescape 8d2826b, WinUnixPtyBridge b866e0a, Wine 11.0).

| | Wine's own conhost.exe (patch) | winescape | WinUnixPtyBridge |
|---|---|---|---|
| What it is | PE program; in Unix mode it parses terminal input escapes itself (programs/conhost/conhost.c `tty_input` -> `process_input_escape`) and writes VT output with WriteFile; raw tty mode is set by wineserver (server/console.c tcsetattr) | CC0 library: raw POSIX syscalls from PE code (Go/C), self-tested `Available()`, Linux and FreeBSD only; has tcgetattr/MakeRaw/winsize/poll/pty/spawn | 6 tiny exports (openpt, read/write, resize, vfork+execve) in a winelib ELF `.dll.so` placed next to Microsoft's conhost under Wine |
| Direction | Unix terminal <- Windows console app (Far) | any; app-side escape hatch | Windows terminal UI -> Unix shell child (pty master on the Windows side): the opposite of what Far needs |
| win32-input-mode / kitty keys | extend the escape parser + send the enable sequence; no Unix access needed | not needed for this; would only replace I/O Wine already does | no |
| OSC52 | output bytes from conhost | not needed | no |
| Delivery | conhost.exe is a builtin PE program loaded from the runtime's lib dir: a new private-runtime optional group (`x86_64-windows/conhost.exe` (+ i386 if used)), no prefix change | compiled into the program that uses it (f4); Far is not ours to rebuild | build per Wine version with winegcc (Wine ABI), hardcoded zsh and HOME |
| Licence | LGPL (Wine) | CC0 | none stated (all rights reserved): not redistributable |

Decision (owner, 2026-11-09: accepted): win32-input-mode first as a patch to
Wine's PE conhost, delivered through the private runtime (new optional group;
design in the same style as OPTIONAL_GROUPS), and posted to WineHQ in words.
winescape stays the tool for programs we build ourselves (f4) and for a
measured need the handle layer cannot meet (none known for Far). Do not use
WinUnixPtyBridge: wrong direction and no licence; its only lesson is that a
winelib DLL next to a PE exe is a working escape hatch.
Open before coding: does Far started as `wine far.exe` in a terminal really
run under conhost in Unix mode in our stand (`--unix` in its command line),
and which keys Far misses today (acceptance matrix above).
