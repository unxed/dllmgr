# Upstream outbox: what we still owe to WineHQ, Linux Mint and others

Owner, 2026-11-09: keep a ledger of everything that must be written
upstream; the owner posts in batches when he can. Add a row the moment a
report or comment becomes due; move it to "Posted" with the URL once the
owner (or an authorized agent) has published it. Texts: plain English, no
Markdown, no code, no links to code (docs/bugzilla/README.md). WineHQ
publication records: docs/bugzilla/submissions.json.

Rule: a bug that shows only with a Linux Mint component (Muffin, Cinnamon,
...) gets a Linux Mint report too (github.com/linuxmint/<component>/issues),
and both reports link to each other. Post order: the first report, then the
second one with the link, then add the back link to the first as a comment.

## Due (not posted)

| # | Where | What | Text | State |
|---|---|---|---|---|
| 7 | WineHQ (new bug, duplicate search first) | #46 DPI-scaled windows: halftone stretch of only the dirty part leaves the spread of XOR-drawn outlines on screen (816 -> 0 px with exact blocks at 2x) | docs/bugzilla/dllmgr-46.txt (prepared 2026-11-09; owner searches duplicates, Bugzilla is behind a bot check for agents) | posted: https://bugs.winehq.org/show_bug.cgi?id=60737 (owner, 2026-11-09) |
| 3 | WineHQ (new bug, duplicate search first) | #44 custom cursors of DPI-virtualized windows not scaled (32x32 at 200 %) | to write | due |
| 4 | WineHQ 57513 (comment) | PuTTY IME: needs IBus + us,ru + UTF-8; result notify not forwarded to the IME UI window | to write after the bisect | due |
| 5 | WineHQ (new bug, duplicate search first) | inverting (XOR) pixels of colour cursors become transparent in the Xcursor path | to write after a Windows probe | candidate |
| 6 | WineHQ (new bug, duplicate search first) | #43 part 1: caption-less owned popups shown without activation are override-redirect, so a splash stays on top of everything when the busy app's main window is minimized (not a Mint bug: Muffin hides managed transients correctly) | to write after a Windows parity check (ghosted app, owned popup) | candidate |
| 8 | WineHQ (new bug, duplicate search first) | #65 shell32 reads desktop.ini of every folder on each bind; each miss lists the directory on a case-sensitive FS: Photoshop CS2 start 29.6 -> 14.9 s with a 2 s miss cache | docs/bugzilla/dllmgr-65.txt (prepared 2026-11-10; owner posts) | posted: https://bugs.winehq.org/show_bug.cgi?id=60739 (owner, 2026-11-10) |
| 9 | WineHQ 34134 (comment on own report) | #35 Open dialog stays wide after Adobe -> OS: Windows does the same (CI run 42725940901: 592 -> 776 -> 776) | docs/bugzilla/wine-34134-comment.txt (prepared 2026-11-10; owner posts; status unchanged) | due |
| 10 | WineHQ (new bug, duplicate search first) | #66 Wine tahomabd.ttf strikes: wrong advances vs Windows (10 px: 40 of 94), "Op en"; simulated italic wider and smoothed | posted as WineHQ 60741 (2026-11-10); follow-up comment docs/bugzilla/dllmgr-66-comment1.txt (owner posts) | comment due |

## Posted (for cross links)

- WineHQ 58413 (comment, owner, 2026-11-09): #43 focus stealing mechanism and fix.
- WineHQ 60721 (comment, owner, 2026-11-09): the exposure fix and its results
  (docs/bugzilla/winehq-60721-fix.txt).

- WineHQ 60726: #38 SetWindowFeedbackSetting / GetWindowFeedbackSetting.
- WineHQ 60727: F13/F14 nested MsiInstallProduct breaks the outer custom
  action (docs/bugzilla/f13-msi-nested-install-binding.txt).
- Older ones: docs/bugzilla/submissions.json.
