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
| 4 | WineHQ 57513 (comment) | PuTTY IME: needs IBus + us,ru + UTF-8; result notify not forwarded to the IME UI window | to write after the bisect | due |
| 5 | WineHQ (new bug, duplicate search first) | inverting (XOR) pixels of colour cursors become transparent in the Xcursor path | to write after a Windows probe | candidate |
| 6 | WineHQ (new bug, duplicate search first) | #43 part 1: caption-less owned popups shown without activation are override-redirect, so a splash stays on top of everything when the busy app's main window is minimized (not a Mint bug: Muffin hides managed transients correctly) | to write after a Windows parity check (ghosted app, owned popup) | candidate |
| 11 | WineHQ (new bugs, one per case, duplicate search first) | HiDPI with fractional scaling (X11 screen at 2x, panel at 1.25x via xrandr; the owner's Cinnamon setup): collect every case where Wine output degrades after the downscale (thin lines, 1-px text detail, cursor sizes, DPI it reports) | to write per case after stand checks with scripts/as-seen.py | candidate |
| 12 | WineHQ 60746 (posted by the owner 2026-11-10) | #36 shape mask: a region span inside one byte of the 1-bit mask vanishes or shifts (set_surface_shape_rect, AND instead of AND NOT); stray pixels next to the Photoshop splash feather | docs/bugzilla/dllmgr-36-shape.txt (posted). Master check 2026-11-10: wine-11.21 (2af4506cc3) dce.c still has `l_mask & r_mask`, so still present by code; run on a master build still to do | posted, retest |

| 13 | WineHQ 60741 (comment) | Dmitry: "should be fixed by aac722e8", please use wine.git. aac722e8 changes only Cyrillic outline advances of Tahoma Bold; Latin advances and bitmap strikes byte-identical, the reported places are Latin | docs/bugzilla/dllmgr-66-comment2.txt (draft; post after a run on master) | due |

## Posted (for cross links)

- WineHQ 60743 (owner, 2026-11-10): #44 cursors of DPI-unaware applications not scaled (docs/bugzilla/dllmgr-44.txt).
- WineHQ 34134 (comment, owner, 2026-11-10): #35 Windows behaves the same (docs/bugzilla/wine-34134-comment.txt).

- WineHQ 60737 (owner, 2026-11-09): #46 halftone stretch of the dirty part only (docs/bugzilla/dllmgr-46.txt).
- WineHQ 60739 (owner, 2026-11-10): #65 desktop.ini lookups on every bind (docs/bugzilla/dllmgr-65.txt).
- WineHQ 60741 (owner, 2026-11-10): #66 Tahoma strikes placement, simulated italic, Shemanarev's approach (docs/bugzilla/dllmgr-66.txt) + comment with the Photoshop CS2 places (dllmgr-66-comment1.txt).

- WineHQ 58413 (comment, owner, 2026-11-09): #43 focus stealing mechanism and fix.
- WineHQ 60721 (comment, owner, 2026-11-09): the exposure fix and its results
  (docs/bugzilla/winehq-60721-fix.txt).

- WineHQ 60726: #38 SetWindowFeedbackSetting / GetWindowFeedbackSetting.
- WineHQ 60727: F13/F14 nested MsiInstallProduct breaks the outer custom
  action (docs/bugzilla/f13-msi-nested-install-binding.txt).
- Older ones: docs/bugzilla/submissions.json.
