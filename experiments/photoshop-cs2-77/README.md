# #77: activation dialog headings

The headings ("Activate with My Serial Number", "Try Adobe Photoshop - N
days left") are drawn with the raster font "System" bold, h=16 (Wine:
vgasys.fon, +font trace, ~22000 selections). Windows draws them the same
way: monochrome raster System (windows-96dpi-activation.png,
windows-heading-x5.png from CI run 42846015037, 96 DPI). So Wine matches
Windows; on the owner's screen the 2x pixel doubling (scaling=exact) and the
125 % panel make the raster font look worse than at 96 DPI.
Going beyond Windows (owner's choice): an opt-in setting that substitutes a
TrueType face for "System" in this application (like DLLMGR66_TAHOMA), so
it is smoothed at HiDPI; it changes the metrics of every System-font text in
Photoshop, so it needs a check of clipping in dialogs.

## 2026-11-10: stand check of patches/dllmgr-77.patch (DLLMGR77_SYSTEM)

Stand: owner's laptop, Xvfb 3072x1728 / 192 DPI + Muffin, rt-exp (Wine 11.0 +
our patches, new WoW64), DLLMGR52_TEXT=gray DLLMGR52_GAMMA=2.2, one fresh
copy of a prefix per run. Note: the never-started prefix-clean (reinstalled
19:47) shows no activation dialog at all on this stand: Photoshop starts
straight into the "program error" box (F26 area, other agent), also with
LC_ALL=C.UTF-8 and with Gecko installed. So the check used copies of the
older prefix-auto, whose trial is over (F25): same dialog, variant
"Activation Required" / "Need an Adobe Photoshop serial number?", headings
drawn with the same "System" bold h=16.

Files (crops of the dialog, X-screen pixels, plus `-as-seen` = scripts/as-seen.py):
t77-base.png (no env), t77-tahoma.png (DLLMGR77_SYSTEM=Tahoma),
t77-tahoma-smooth.png (plus DLLMGR66_SMOOTH_TAHOMA=1),
t77-side-by-side-as-seen.png (same order), t77-headings.png (both headings,
three rows each, same order).

Results:
- DLLMGR77_SYSTEM=Tahoma alone: the substitution works (+font:
  `dllmgr77: System -> L"Tahoma"`, `Chosen: L"Tahoma Bold"`, ppem 13), but
  the headings come out NOT smoothed and look thin/regular: pure black
  pixels, no grey. Cause: #66 (`dllmgr66_tahoma_strike`, freetype.c) forces
  GGO_BITMAP for Wine's Tahoma Bold at sizes that have a hand-drawn strike;
  tahomabd.ttf has EBLC strikes at ppem 9-13, 15, 16, so ppem 13 uses the
  strike. Not what #77 wants.
- With DLLMGR66_SMOOTH_TAHOMA=1 added: headings are smoothed Tahoma Bold, as
  intended. Ink widths (X pixels): "Activation Required" 250 (System) -> 258,
  "Need an Adobe Photoshop serial number?" 542 -> 546. Both panels have
  hundreds of pixels of room: no clipping, no overlap; vertical position
  unchanged. Nothing else in the dialog changed (diff is limited to the
  heading lines; body text, buttons and links are identical).
- Next: make the #77 substitution skip the #66 strike rule for the
  substituted face (DLLMGR66_SMOOTH_TAHOMA smooths all Tahoma in Photoshop,
  too broad), re-run; check the "Try Adobe Photoshop - N days left" variant
  once a prefix shows it again; other System-font dialogs not checked.
