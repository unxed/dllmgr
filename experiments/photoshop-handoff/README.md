# Preserved Photoshop / TopPlan investigation sources

Owner requested all unfinished work saved to GitHub before further research.
These are exact source snapshots transferred from the wine bugzilla chat's
local photoshop-cs2 stand on2026-11-08, not production helpers or a delivered fix.
See docs/photoshop-handoff.md, issues31/34/35/36 and the original stand's STATE.md.

- headless.py: original session runner. Paths are relative to the original
  stand, the existing test prefix and unpacked Xvfb. Reconfigure deliberately;
  do not run the archived copy blindly. Before any launch, verify an unused
  display and a disposable prefix, not the active desktop/default prefix.
- windows.c: current public-API enumeration/click/close/resize source. Original
  executable variants are not bundled. Window IDs are transient; establish
  ownership in your own invisible session before invoking a mutating command.
- sizehook.c / hookhost.c: current32-bit before/after public message observer.
  They do not fix the dialog. Original hardcoded log path is preserved; adapt
  deliberately for a new stand. The host requires a live owned GUI HWND and
  keeps hooks alive while running. Build/usage validation is recorded in the
  transferred session, not repeated or newly claimed by this archival commit.
- sizehook110.log: original message-only trace, no document/prefix contents.
- source-sha256.json: hashes of the exact transferred sources/trace.
- fix-it-in-wine-catalog-format1.patch: owner-applied patch already also present
  in unxed/fix-it-in-wine#13. This snapshot does not mean upstream merge.
- topplan-cdx-pages.json: archived official-page CDX candidates, not verified
  downloadable installer binaries or a completed TopPlan retest.

Do not upload proprietary installers, test-prefix files, registry/trial state
or uninspected personal screenshots. The synthetic public-API sources, diagnostic
trace and actionable continuation are the work products preserved here.
