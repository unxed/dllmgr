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
