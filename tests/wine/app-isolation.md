# Private Wine 11.0 loader experiment

This overlay is built from Wine commit db11d0fe6a169c457e23d007e20404643d067aa8,
plus the complete attached patch. It is for a private copy of the Wine runtime,
not installation over a system Wine or shared prefix DLL. Wine is licensed under
LGPL-2.1-or-later; the accompanying complete modified source archive includes
COPYING.LIB and original source notices. Reproduce with app-isolation-build.sh.

A launcher preserves the user UTF-8 locale (CI uses LC_ALL=C.UTF-8) and sets
these Windows paths, canonicalized by winepath -w:

- DLLMGR_TARGET_EXE: complete target EXE path, including its directory.
- DLLMGR_GDIPLUS: private, builtin-marker-cleared GDI+ DLL path.
- DLLMGR_COMCTL32: private, builtin-marker-cleared common-controls v6 DLL path.

Only bare gdiplus.dll and comctl32.dll requests from the exact target image are
redirected before SxS and KnownDLL resolution. Paths compare case-insensitively.
Explicit DLL paths use ordinary Wine behavior. No registry override is needed.
Missing, relative, or noncanonical selected DLL paths fail loading; there is no
fallback to a stock DLL for that selected request. Unrelated child images inherit
the variables but fail the exact-image match. Another EXE in the same folder or
the same EXE basename in another folder likewise uses ordinary loading.

The launcher must use this private runtime. Starting the application with plain
system wine bypasses the patch. This experiment establishes loader isolation;
it does not itself validate FastStone or Photoshop UI behavior.

The ZIP manifest records each payload SHA256 and the original packaged Wine
launcher/ntdll SHA256 values. The complete modified Wine source is a separate
.tar.xz; it is not installed into the runtime. The ZIP includes the build/check
scripts used by CI. The source tree has no build directory or .git metadata.

Runtime assembly copies /opt/wine-stable and overlays the three ntdll files under
lib/wine/{i386-windows,x86_64-windows,x86_64-unix}/. ZIP bin/wine is the Wine
`tools/wine/wine` launcher and is installed as runtime/bin/wine. The distinct
`loader/wine` binary belongs beside ntdll.so; the stock runtime copy already
contains this unmodified loader at lib/wine/x86_64-unix/wine.
