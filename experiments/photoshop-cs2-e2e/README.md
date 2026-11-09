# End-to-end check of the released recipe (stand, owner's way of starting)

e2e.sh: installed recipe (`dllmgr fix photoshop-cs2`, pinned runtime), plain
`wine Photoshop.exe C:\t46.png` from the system Wine, Russian layout first
(ru,us), LC_ALL=C.UTF-8, preferences that used to trigger #62.

2026-11-09, runtime v10 (sha256 841a7a0e…), dllmgr 753c21b:
- handover: private runtime (`dllmgr status`: Running ... on the private
  runtime)                                                      #51
- document: open (no "hardware or system error")                #62
- ru Ctrl+N: New opened                                         #49
- splash: no halo (v10-splash-corner.png)                       #36
- text: default text=gray contrast=2.2, smoothed menus and palettes
  (v10-loaded.png)                                              #52 (a)
