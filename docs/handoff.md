# Handoff: FastStone work

Before continuing, follow [the development policy](development.md): small atomic
RUP increments, immediate push to `main` and delivery to the user; extended
checks and refinement come afterward. Do not accumulate completed changes.

## Current unfinished-work queue (2026-11-08)

This entry point supersedes older checkpoint instructions below. Follow
[the immediate-delivery policy](development.md); do not accumulate finished
work while broadening tests. The current app-private installation is documented
in [app-isolation.md](app-isolation.md), delivered on main in `6d21cb1`.
Shared system/SxS DLL apply must stay disabled for product use. The resolved
Photoshop incident (#25) covered only the self-extractor initial window; the
new CS2 trial compatibility audit is tracked separately in #31.

- [#21](https://github.com/unxed/dllmgr/issues/21): the original dropdown
  appearance correction and second-click close repaint are delivered and
  installed privately in **faststone-v4** (54ff7f3; catalog identity correction
  961c36d). Exact owner sequence fails on v3 and passes with the new DLL
  isolated/composed at96/192DPI in CI42499612512; the exact installed DLLs
  also pass headlessly on this laptop at192DPI. No user window was restarted;
  next managed launch gets v4. Owner visual acceptance remains pending.
  [Wine60720](https://bugs.winehq.org/show_bug.cgi?id=60720#c0) is posted.
  Separate severe intermittent path-row corruption remains unreproduced.
  See experiments/path-dropdown/owner-close-2026-11-08/.
  Its old research shared installer must not be reused.
- [#22](https://github.com/unxed/dllmgr/issues/22): startup/Draw latency. The
  font-cache enlargement was rejected after actual-app A/B; branch
  `research/faststone-font-cache` at `643b39a` preserves the negative result.
- [#23](https://github.com/unxed/dllmgr/issues/23): one composed selection with
  explicit distinction between private DLLs and prefix-wide font/WIC assets.
- [#27](https://github.com/unxed/dllmgr/issues/27): first-open full white-screen
  flash: reproduced image→white→image with a synthetic JPEG; the white
  interval was 251 ms. Probe and timeline: `experiments/first-open/`. Cause and
  fix remain open. Words-only Wine60721 is posted (docs/bugzilla/submissions.json). All further GUI tests must use a separate headless display
  and disposable prefix or hosted CI; no test windows on the owner's desktop.
- [#28](https://github.com/unxed/dllmgr/issues/28): accepted font .009 final
  polish (capital В); preserve the accepted improvements and rejected fixtures.
- [#29](https://github.com/unxed/dllmgr/issues/29): remaining middle-button/mode,
  Crop and historical redraw audit; physical-pointer slowness unreproduced now.
- [#30](https://github.com/unxed/dllmgr/issues/30): reconcile Wine report ledger,
  historical docs and supplied upstream patches. The unfinished local draft is
  remotely recoverable from [the source checkpoint](checkpoints/README.md).
- [#19](https://github.com/unxed/dllmgr/issues/19): vtui TUI first, goWidgets GUI
  later; planning only, do not implement until the owner activates the work.
- [#18](https://github.com/unxed/dllmgr/issues/18): Far3/hiew and terminal
  protocols. Far3's standing Lunobot assignment remains `unxed/lunobot#322`;
  the added hiew/protocol scope is recorded only for now.

- [#36](https://github.com/unxed/dllmgr/issues/36): Photoshop CS2 splash
  background transparency, reported by the owner; start with existing Wine
  #34133/#10091 and the other Photoshop session's saved evidence. Keep separate
  from FastStone's white flash and coordinate with #31/#35.

The merged Photoshop/TopPlan chat handoff is in [photoshop-handoff.md](photoshop-handoff.md),
including published Wine comment URLs, the preserved invisible test stand,
remaining #34/#35/#36 work and the owner-applied fix-it-in-wine#13 patch.

Broader recorded project tasks: [#31](https://github.com/unxed/dllmgr/issues/31)
(Photoshop CS2 compatibility audit and composed recipe),
[#32](https://github.com/unxed/dllmgr/issues/32) (quick winetricks-style recipes),
and [#33](https://github.com/unxed/dllmgr/issues/33) (future HTTP Range/package
indexes, implement only when a practical task needs it). These have their own
requirements and handoffs; they do not replace the current FastStone work.

Parent [#8](https://github.com/unxed/dllmgr/issues/8) is the authoritative
remaining-work index. Completed #25 must not be mistaken for an unresolved
Photoshop installation task; historical notes below are evidence, not current
instructions to restore the unsafe shared-file method.

## Emergency continuation checkpoint (2026-11-08, owner quota limit)

Everything useful from this session is pushed to main; no research job remains
running. Last successful research run42501854290 atf682c3b9b99c5f373d76425593a1fca4e5c1fb5a.

- Installed **faststone-v4** close repaint passes the exact stationary second-click
  sequence on the hidden laptop stand. All1825 files from the shared DLL/font/WIC
  baseline remain byte-identical, verified again after v4. Evidence:
  experiments/path-dropdown/owner-close-2026-11-08/v4-shared-integrity.json.
- Wine60720 and60721 are published, words only; exact URLs/times in
  docs/bugzilla/submissions.json. Already-published font c15/c16 were recovered,
  not reposted. Historical prepared reports are now individually readable.
- White flash remains **unfixed**. The improved centre-first observer gets
  241–242 Windows samples instead of44, with no sampled flash; Wine192DPI still
  reproduces it. DPI/resolution differ and this is not exhaustive frame capture.
- Same-size positioning plus a corner paint does not reproduce the white flash
  in the minimal popup; Windows retains yellow, Wine stays black. This is a
  negative diagnostic result, not a solution. Next inspect what marks the real
  new fullscreen surface entirely dirty before its first flush.
- Source is work/wine-11.0 atdb11d0fe6a169c457e23d007e20404643d067aa8.
  Diagnostic trace: work/local-first-open-headless/gdi-trace/trace.txt,
  interval.txt and observations.txt. Own hidden Xvfb:93 and Metacity remain
  available; verify ownership before reuse. Disposable prefix:
  work/avif-wine-validation/prefix. Never use the user's desktop for tests.
- Current checkout work/dllmgr-private, branch fix/app-isolation, pushes HEAD
  directly to origin/main. The old work/dllmgr22-file WIP is exactly preserved
  by checkpoint991a22b; do not reset or merge it wholesale. Its current tree
  ef50b39e56c838239bc53470c758dab0091f7183 matches the saved patch. The only
  untracked images/ in the current checkout contains166 synthetic files,
  byte-identical to tests/wine/make-images.py output, not unpublished source.
- Other-repo changes remain supplied patches for the owner, not silently applied.
  No delegation or automation was started. Current queue remains issues8/21/22/
  23/27/28/29/30; Photoshop/TopPlan handoff is linked above.

## Latest local checkpoint (2026-11-07)

Saved on GitHub at the owner's request on **2026-11-07**. Detailed attempts,
including failures, are in `experiments/local-validation/README.md` and
`experiments/tahoma-bold/README.md`; start there before repeating experiments.

- **AVIF / Wine 60703:** the native x86 WIC decoder passes Windows CI
  [42402910201](https://github.com/unxed/dllmgr/actions/runs/42402910201) at
  72310aced08b695d7750dabbba7af49b834a734d. The exact DLL also displays the
  reported 626x417 file and generated 320x192 image in actual FastStone on this
  laptop (fullscreen, thumbnail, preview). See docs/avif.md for experimental
  install/undo, prefix-wide 32-bit WIC scope and deliberate format limits.
  Release winehq-60703-v1 is published. The owner's CLI is updated to 108641a
  and the codec is now installed in the default prefix; status and a subsequent
  WIC sample decode pass. A one-off post-install registry-export timeout was
  followed by successful read-only query/export/status; no server was killed.
  FastStone must be restarted to discover the newly installed decoder.
- **Isolated GDI+ discrepancy resolved:** an old KnownDLL image survived the
  disk/registry change in the same wineserver. A new server gives stock black
  versus GDI+-only red (3642 pixels), with native GDI+ / builtin comctl32
  loading confirmed. Full bundle, registry, managed state and settings restored.
  See experiments/local-validation; no server was killed.
- **Font .009:** the owner says nearly ideal; capital В seems a little
  heavier than its neighbors (its original bold outline is untouched).
  .007 had filled counters; .008 fixed those but had a thin Ы stem and merged
  ы parts. .009 normalizes source winding before offsetting and preserves
  horizontal component gaps. All 66 glyphs pass counter/component checks;
  .007/.008 fail the expanded regression guard. Actual Wine GDI and FastStone
  panel checks pass. Install/undo and source packaging: docs/fonts.md.
  The reversible manager also passed an apply/status/undo cycle on the real
  prefix. Experimental candidates are not silently added to faststone-v2.
- Far3/hiew backlog is visible in dllmgr issue 18 and docs/console-apps.md;
  the new terminal-protocol scope is documentation only for now. Far3's
  existing Lunobot assignment remains issue 322. Do not start hiew/protocols
  while continuing this FastStone session.

- Deep research run **42278157255** at `255f086` completed successfully.
  The patched real Draw Board stroke is red (`ff0000`, 3642 pixels);
  native module loads and byte-exact DLL undo both passed. The earlier
  five-minute failure was two APT timeouts before the application started.
  Commit `2db204d` preserves download/setup failure evidence and passed
  catalog/apply-scripts CI. See `docs/ci-timing.md`.
- The installed `faststone-v2` recipe also draws red on the owner's laptop:
  FastStone 8.5 x86, Wine 11.0, win64 prefix, 192 DPI, synthetic white image.
  Startup mapping/first WM_NULL reply: **1462/1473 ms**. Draw Board first
  open: **6108/6457 ms**; second open: **6329/6342 ms**. These are window
  readiness proxies, not a claim that all pixels are painted. Traced runs
  are kept separate from timing evidence.
- Localized Draw Board uses `TDrawBoard.UnicodeClass`; the observer must
  accept that suffix and fail on missing windows. Foreground checks prevent
  shortcut injection into an unrelated application.
- Font workaround is **not accepted or installed permanently**. Emboldening
  66 Cyrillic glyphs fixes mixed weight, but the owner still sees uneven
  positioning. A higher `head.fontRevision` makes a temporary prefix font
  take precedence; removing it restores the original. Hinting investigation
  continues. Preserve original advances and unrelated outlines.
- CLI presentation passed 38 script tests and was installed locally at
  `bc1dbd9`: concise progress/result, `--verbose` for details, `NO_COLOR`.
  D22 records the vtui TUI as a future plan only. Far3 was assigned to
  Lunobot in issue 322; this session continues FastStone.
- The owner is away. Continue independent work and collect any questions
  for one later batch. Physical mouse speed and final visual font acceptance
  still need the owner; no synthetic motion proves physical mouse behavior.

## Cloud sessions

If this session runs in the cloud and the next FastStone step needs the
owner's desktop, switch to Far Manager 3: `docs/far3.md` (D21).

## First steps for the next session

Read the latest checkpoint above, then validate any newer commits:

1. `go test ./...`, `FIW_TOOLS=<fix-it-in-wine>/tools python3 -m unittest
   discover -s scripts/tests`, `go run ./cmd/dllmgr-catalog check catalog`.
2. Read the latest `faststone-research` and `apply-scripts` runs on `main`
   (use fix-it-in-wine `tools/ci_wait.py`); fix what fails.
   Normal job durations and the fail-fast limits (timeouts, bounded apt
   installs, diagnostics on failure) are in `docs/ci-timing.md`; the CI
   changes were merged untested.
3. Pencil with the fix passed both CI and the local desktop. Evidence is in
   `faststone85-192-comparison/patched/snapshots85/draw/observations.txt`;
   expected `ff0000` (3642 pixels). Avoid repeating the deep run unless a
   relevant change requires it.
4. Owner's acceptance so far (https://github.com/unxed/dllmgr/issues/8#issuecomment-6693158826):
   tiles fit (dllmgr-14) and the fullscreen strip scrolls (59251) on the
  owner's desktop. Still to check visually there: names and wheel speed
   in the browser grid.

Date: 2026-11-06. Written for the agent that continues on the owner's own
computer. The cloud session had GitHub Actions (Windows runner, headless Wine
under Xvfb) but no real desktop, no real mouse and no browser. Everything
below marked **LOCAL** needs the owner's machine.

## Where things are

- Work is merged into `main`; PRs 15 and 17 are closed.
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
| winehq-48874 pencil | GDI+ probe fixed. Real Draw Board: Windows draws red, stock Wine black; patched Wine draws red in CI and on the owner's laptop (`ff0000`, 3642 pixels). |

Middle button (FS-middle-button): Wine matches Windows in CI (fullscreen →
browser). Not a Wine bug so far.

## Owner's answers (2026-11-06, evening)

- Fonts: `FontSmoothing` = 2, `FontSmoothingType` = 1 (standard, not
  ClearType), and the host's `fc-match Tahoma` returns **Noto Sans**. CI used
  winehq-stable, which ships Wine's own `tahoma.ttf`. Ruled out later: the owner's Wine is winehq-stable with
  `/opt/wine-stable/share/wine/fonts/tahoma.ttf`, the same as CI. Remaining
  differences to test: `FontSmoothingType` 1 (grayscale) versus the CI
  prefix's value, and hinting. A cropped screenshot of the poor text is the
  next input. Check first: `wine --version` and
  `find / -iname 'tahoma*.ttf'`, then run `tests/wine/font-probe.c` in the
  owner's prefix to see the face Wine actually selects.
- Fullscreen strip on the real desktop: it appears at the edge and stays
  under a still mouse (so the headless reveal problem is a harness
  artifact), but the wheel does not scroll it on stock Wine. That is the
  59251 horizontal case; verify it after installing faststone-v2.
- Timings: no notable difference between the first and second start, and the
  number of files does not matter much.

## FS-fonts: cause found; FS-cursor: new

- FS-fonts: Wine 11.0's own `fonts/tahomabd.ttf` draws Cyrillic letters that
  have no Latin look-alike (Ф й л д ш у П в т з м ы к …) with the regular
  outlines, only wider; а с о р е are real bold. Reproduction:
  `docs/img/tahomabd-cyrillic.png`; details in
  https://github.com/unxed/dllmgr/issues/8#issuecomment-6693207972.
  Existing Wine bug: https://bugs.winehq.org/show_bug.cgi?id=26037 ("Tahoma
  Bold is not bold", NEW since 2011; Latin was later reported fixed). A
  words-only follow-up draft is in `docs/bugzilla/winehq-26037.md`; the owner
  posts it. Workaround plan (needs FontForge, which the cloud sandbox could
  not install): embolden the affected Cyrillic glyphs in Wine's
  `fonts/tahomabd.sfd` while keeping their advance widths, rebuild the font,
  ship it as a catalog variant; first test locally whether a `tahomabd.ttf`
  in the prefix's `windows/Fonts` overrides Wine's own for "Tahoma" bold.
  Add a check that renders Cyrillic bold text and compares ink with Latin.
- FS-cursor (new, owner): the pointer moves very slowly over the FastStone
  window; the owner suspects HiDPI. Measure pointer motion over FastStone and
  over another Wine window at 96 and 192 DPI first.

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
