# Handoff: FastStone work, from the cloud session to a local agent

Date: 2026-11-06. Written for the agent that continues on the owner's own
computer. The cloud session had GitHub Actions (Windows runner, headless Wine
under Xvfb) but no real desktop, no real mouse and no browser. Everything
below marked **LOCAL** needs the owner's machine.

## Where things are

- Branch `fix/faststone-v2`, pull request https://github.com/unxed/dllmgr/pull/15
  into `main` (supersedes the closed PR 12).
- Recipe `catalog/bundles/faststone-all.md`: five fixes, prebuilt in the
  prerelease https://github.com/unxed/dllmgr/releases/tag/faststone-v2.
- Status table of every known symptom: `docs/faststone.md`, section
  "Status with recipe faststone-v2". Per-fix evidence: `results` rows in
  `catalog/fixes/*.md`.
- Data model proposal: `docs/data-model.md` (D14), waiting for the owner after
  the architecture review below.
- Install on the owner's machine (also the acceptance test):
  `dllmgr share faststone` prints the link and the one-line installer;
  `dllmgr fix faststone`, `dllmgr uninstall faststone`.

## Verified in CI (FastStone 8.5 x86, Wine 11.0, x86_64, win64, 192 DPI)

| Fix | Result |
| --- | --- |
| winehq-48872 names | names shown; label width 0 → 276 px |
| dllmgr-14 LVIR_ICON cell | tiles, folder preview, `BMP` badges, selection inside frames; fixture `--check-icon-cell` fails on stock Wine, Windows v6 returns the whole 74 px cell |
| winehq-59251 wheel | 0/426/426/852 px for ½,½,1,2 detents; Windows 0/216/216/432 at 96 DPI; stock Wine 37 px per event |
| winehq-59609 positions | thumbnails in the fullscreen strip |
| winehq-48874 pencil | GDI+ probe fixed. Real Draw Board: Windows draws red, stock Wine black. The patched Draw Board run was not finished when the session ended: read `pencil_stroke_color` in the `faststone85-192-comparison` artifact (`patched/snapshots85/draw/observations.txt`) of the latest `faststone-research` run on this branch. Expected `ff0000`. |

Middle button (FS-middle-button): Wine matches Windows in CI (fullscreen →
browser). Not a Wine bug so far.

## Owner's answers (2026-11-06, evening)

- Fonts: `FontSmoothing` = 2, `FontSmoothingType` = 1 (standard, not
  ClearType), and the host's `fc-match Tahoma` returns **Noto Sans**. CI used
  winehq-stable, which ships Wine's own `tahoma.ttf`. Leading hypothesis:
  the owner's Wine build lacks Wine's Tahoma and falls back to Noto Sans with
  other metrics. Check first: `wine --version` and
  `find / -iname 'tahoma*.ttf'`, then run `tests/wine/font-probe.c` in the
  owner's prefix to see the face Wine actually selects.
- Fullscreen strip on the real desktop: it appears at the edge and stays
  under a still mouse (so the headless reveal problem is a harness
  artifact), but the wheel does not scroll it on stock Wine. That is the
  59251 horizontal case; verify it after installing faststone-v2.
- Timings: no notable difference between the first and second start, and the
  number of files does not matter much.

## LOCAL work: not reproducible in the cloud

1. **Acceptance of faststone-v2 on the owner's desktop.** Install with the
   one-liner, then check names, tiles, wheel speed at the owner's DPI and
   wheel settings, and pencil colour in Draw Board. Record results as
   `results` rows (environment from the owner's machine).
2. **FS-fonts.** The left-panel heading looked clean in CI (Wine's own Tahoma,
   antialiased). Collect on the owner's prefix:
   `wine reg query 'HKCU\Control Panel\Desktop' /v FontSmoothing`,
   `... /v FontSmoothingType`, `fc-match Tahoma`, plus a cropped screenshot.
   Compare with `tests/wine/font-probe.c` output. Do not change prefix-wide
   font settings without the owner's consent.
3. **FS-path** (folder-path field artifacts). Intermittent, never reproduced.
   Capture immediately with the preceding actions (scroll, folder change,
   resize, view switch Thumbnails → Details → List clears it).
4. **FS-draw-start / FS-start** (Draw Board ~5 s, startup 2–3 s on the
   owner's machine; ~1 s and 0.7 s in CI). Measure cold and warm on the real
   prefix with the same folder; then bounded traces (fonts, GDI+, modules).
5. **Fullscreen thumbnail strip reveal.** In the headless harness the strip
   is often not under the cursor after a pointer move, on Wine and with the
   newest harness even on Windows, so the test cannot tell a Wine bug from a
   harness artifact. Ask the owner whether the strip appears at the top edge,
   stays while the mouse rests on it, and scrolls with the wheel. Only treat it
   as a Wine bug with a real-desktop observation.

## Owner decisions in this session

- Recipes, fixes and evidence live in the dllmgr catalog (D11). Per-user
  install under `~/.local` (D15).
- WineHQ Bugzilla: the agent prepares texts, **the owner posts them**. A text
  may be prepared only after the gate in `docs/faststone.md` holds (a test
  reproducing the reported behavior fails on stock Wine and passes with only
  the change, plus a visual check in the real app). The fix file itself is the
  draft: Problem, Windows behavior, The fix in words, Results. Done for
  winehq-59251 and dllmgr-14; still to write for 48874, 48872, 59609.
- Showcase app for lunobot (https://github.com/unxed/lunobot/issues/323): not
  tax software and not defense; prefer electronic identification.
- KISS: the data model must be no more complex than OpenStreetMap's (a budget,
  not a template).

## Open threads

- Architecture and vision review: https://github.com/unxed/dllmgr/pull/16
  (into `fix/faststone-v2`) and https://github.com/unxed/fix-it-in-wine/pull/10.
  It adds `docs/vision.md` (the owner's text verbatim plus marked editorial
  notes), D16 clean-room rules (Wine gets text only; Windows only as a black
  box), D17 the four headings for every fix file, D18 `dllmgr fix` without an
  app name (scan the prefix, match, ask) and a desktop menu entry, D19 vendor
  kits (`docs/vendor-kits.md`). Questions for the owner: accept D17 and D19?
  Enable a vendor kit at install time or by a launcher at each start? May a
  Bugzilla report link to a clearly labeled AI-written patch in the catalog?
  The data model (D14) waits for the owner's review of this PR.
- fix-it-in-wine PRs: lessons from this session
  (https://github.com/unxed/fix-it-in-wine/pull/8), showcase scope
  (https://github.com/unxed/fix-it-in-wine/pull/9).
- dllmgr issues: https://github.com/unxed/dllmgr/issues/8 (FastStone symptoms),
  https://github.com/unxed/dllmgr/issues/13 (ReactOS, LiberNT, CusDeb OS),
  https://github.com/unxed/dllmgr/issues/14 (LVIR_ICON cell).
- lunobot plans: https://github.com/unxed/lunobot/issues/321 (take over
  FastStone), 322 (Far Manager 3), 323 (showcase).

## Traps met in this session

- `GetScrollInfo` on another process's window fails under Wine; the observer
  measures item 0 with `LVM_GETITEMRECT` in the target process instead.
- `SetCursorPos` may not produce mouse motion under Wine's X11 driver; the
  observer uses `SendInput` for strips and drawing.
- A push that touches `tests/wine/`, `patches/`, `scripts/`, `catalog/` or the
  workflow cancels the running `faststone-research` run on that branch.
- An apt mirror once stalled the build job for over 30 minutes; it now has a
  10-minute limit.
- Wine's `LISTVIEW_SCROLL_ICON_LINE_SIZE` (37) is half the default 74 px
  spacing; calibrate constants against Windows with the app's real sizes.
