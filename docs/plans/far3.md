# Far Manager 3 task cards

The detailed plan is docs/far3.md (already written for Sonnet); backlog in
docs/console-apps.md. Cards here only add execution guidance.

## FAR-1 Goal 1 measurement (next step in far3.md)

- Run in CI (Linux winehq-stable 11.0 and windows-latest); use `script -qc`
  for a pseudo-terminal; time "exec -> first panel output" by waiting for a
  fixed string of the panel frame in the pty stream (not by sleep).
- 10 cold + 10 warm runs, report medians; one +loaddll run separately.
- Change one lever at a time (far3.md list); keep a lever only with numbers.
Done when: a results table in far3.md with both platforms.
Stop and ask if: Far needs a display to start at all (record and ask).

## Unix-side console: two existing routes (owner, 2026-11-08)

- https://github.com/unxed/winescape — owner's project: a Windows program
  under Wine calls native host APIs (escape hatch out of Wine).
- https://git.howett.net/DHowett/WinUnixPtyBridge — Dustin Howett (Microsoft
  terminal team, written for fun): bridges Windows console/ConPTY semantics
  to a Unix pty.
Before designing any conhost/Unix-console change (win32-input-mode, OSC52,
kitty keys), compare both: features already there, per-app installation
(private runtime overlay vs PE side), licence, per-call overhead (far3.md
benchmark). Record the comparison in docs/console-apps.md; choose with the
owner.

## FAR-2 console bugs (far3.md Goal 2)

Executing agent: Bugzilla audit + a console reproducer per bug (plain text
output, exact comparison with the Windows runner). Escalate to Opus: any fix
in conhost/kernelbase/ntdll Unix side and its delivery (private runtime
optional overlay groups exist since 029685b; new groups need a design).
