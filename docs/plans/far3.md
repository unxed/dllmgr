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

## FAR-2 console bugs (far3.md Goal 2)

Executing agent: Bugzilla audit + a console reproducer per bug (plain text
output, exact comparison with the Windows runner). Escalate to Opus: any fix
in conhost/kernelbase/ntdll Unix side and its delivery (private runtime
optional overlay groups exist since 029685b; new groups need a design).
