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
