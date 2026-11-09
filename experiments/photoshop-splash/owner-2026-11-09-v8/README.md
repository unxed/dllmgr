Owner retest of runtime v8 (2026-11-09, Mint/Cinnamon, 192 DPI).

- Plain launch: on the system Wine (`dllmgr status`), so no runtime fixes: #51.
- `dllmgr run photoshop-cs2` (log: run-private-runtime.log, nothing unusual
  besides the known 60 s critical-section wait of 6e): cursors OK (#44), blur
  without leftovers (#46), menus without black (#45).
- About: no frame; partial halo at the feather and the top edge, frame
  flashes briefly on the runtime (#36 comment).
- Text: contrasty but badly shaped on the runtime, slightly blurry on the
  system Wine; Preferences without antialiasing: #52.
