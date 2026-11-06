# Wine source patches

These diffs modify Wine, whose relevant modules are licensed under
LGPL-2.1-or-later. The repository's BSD license for the manager does not
relicense Wine code or the resulting DLLs.

Apply each complete diff to the exact Wine source version recorded by the
build. Compose the selected patches in one source tree before building shared
modules. The research workflow starts from Wine 11.0 commit
`db11d0fe6a169c457e23d007e20404643d067aa8` and records the source revision and
patch list with the output.

- `winehq-59609.patch`: the reporter's item-position fix, also packaged by the
  original fix-it-in-wine showcase.
- `winehq-48872.patch`: candidate public API geometry correction for empty icon
  labels. Related MR 10093 prompted the empty-selection painting regression
  check; this patch keeps painting metrics unchanged.
- `winehq-48874.patch`: candidate GDI+ ROP2 correction for colored pencil strokes
  on 24-bit DIBs.
- `winehq-59251.patch`: candidate horizontal icon-list wheel handling; separate
  from the thumbnail-drawing coordinate correction.

Candidate status and before/after/undo evidence are described in
[the FastStone audit](../docs/faststone.md). A patch applying or compiling does
not establish that it fixes the application.
