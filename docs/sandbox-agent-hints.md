# Hints for agents in the Claude cloud sandbox (token savers)

Read this first in a new session. Everything below was learned the hard way on
2026-11-08; details live in docs/sandbox-stand.md and docs/sandbox-findings.md.

## Start of session (about 5 tool calls)

1. Repo with push: request it through the session's GitHub app (`add_repo`,
   `access: push`); clone goes to `/home/claude/dllmgr`. Ask for push only
   when you will push; a push request made just to read an issue was denied.
   Never put a user-pasted token into git config or URLs.
2. Issues: `gh api repos/unxed/dllmgr/issues/N` and `.../comments --paginate`
   (REST only, GraphQL is blocked, so `gh issue view` fails).
3. Stand: `sh scripts/sandbox-stand.sh install`, then
   `sh scripts/sandbox-stand.sh session sh scripts/sandbox-stand.sh prefix`.
   Installer: `curl` the https Adobe URL in sandbox-stand.md into
   `/home/claude/work/photoshop-cs2/dl/` (345 MB, about 10 s).
4. CS2 trial: `sh scripts/sandbox-stand.sh session sh scripts/sandbox-install-cs2.sh`
   (unattended, a few minutes, verifies installer and Photoshop.exe SHA256).
   Do not redo it by screenshots.

## Working with GUI apps cheaply

- One experiment = one `sandbox-stand.sh session CMD` run. Long runs: start it
  with the shell tool's background mode, then wait with an `until ...; do
  sleep 1; done` loop or the Monitor tool. A bare `sleep N` before other
  commands is blocked by the harness.
- Detached processes (`&`, `setsid`, `nohup`) die minutes after your reply;
  background tasks of the shell tool survive between replies (about 2 h max).
- Text before pixels: `sh scripts/stand-shot.sh list` prints visible windows
  with geometry. Titles alone usually tell which dialog is up.
- Look at images only when needed, and small: `stand-shot.sh win NAME REGEX`
  captures one window's client area at 50%. Click with
  `xdotool windowactivate --sync ID mousemove --window ID X Y click 1`, where
  X,Y = coordinates in the 50% image times 2.
- Dialogs are painted late (CS2 Setup is flat white for seconds): wait until
  `import -window ID png:- | convert png:- -format %k info:` reports more than
  2 colours before clicking (see `painted` in sandbox-install-cs2.sh).
- Synthetic keys may be ignored by Photoshop's main window (F16): prefer
  mouse + menu mnemonics (File menu, then `x` to exit).
- Wine logs: run each app with stdout/stderr to its own file; grep for
  `Unhandled|err:` instead of reading the whole log. ALSA and `winebth`
  errors are sandbox noise.

## Rules that bind every session

- Push each finished small change to `main` immediately (development.md).
- Problems met on the way go to sandbox-findings.md and are fixed last.
- Accept EULAs or click anything with legal effect only with the owner's
  explicit yes (CS2 trial EULA: approved 2026-11-08, see #31).
- Never use the owner's desktop or default prefix; the sandbox is separate
  anyway, but keep using disposable prefixes per experiment.
