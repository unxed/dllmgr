# Wine Bugzilla audit: open bugs mentioning "photoshop" (#31)

Snapshot 2026-11-08 23:00 CET via REST `quicksearch=photoshop` (open statuses):
95 bugs, raw list in docs/bugzilla/photoshop-open-2026-11-08.json. First-pass
grouping by title only (Opus); **every row still needs the full bug read**
(description, all comments, attachments) before its verdict.

Groups: **A** CS2 named (in scope) · **B** version unclear, may apply to CS2 ·
**C** older than CS2 (PhotoDeluxe, PS 6/7, CS): check the symptom in CS2 only if
cheap · **D** later versions (CS3+, CC, Elements, other Adobe apps): skip with
version recorded · **E** not a Photoshop bug (word only in comments) or needs
hardware: skip with reason.

Verdict values: `reproduces` / `not reproduced (setup)` / `skipped: later version X`
/ `skipped: not Photoshop` / `skipped: needs hardware` / `insufficient data`.

| G | Bug | Status | Title | Notes | Verdict |
|---|---|---|---|---|---|
| A | [9623](https://bugs.winehq.org/show_bug.cgi?id=9623) | NEW | Adobe Photoshop CS2 crashes without Times.TTF from corefonts (PS 7 affected somewhat, too) |  |  |
| A | [9802](https://bugs.winehq.org/show_bug.cgi?id=9802) | REOPENED | ImageReady CS and CS2 crash on startup |  |  |
| A | [11412](https://bugs.winehq.org/show_bug.cgi?id=11412) | NEEDINFO | Adobe Photoshop CS2: splash screen z-order problem | checked 2026-11-08: submenu above Tools, palettes covered (Metacity c25; Muffin+Alt+Tab experiments/ps11412) |  |
| A | [19343](https://bugs.winehq.org/show_bug.cgi?id=19343) | NEW | Adobe Photoshop CS2: Edit controls have wrong names (appinstall) |  |  |
| A | [19344](https://bugs.winehq.org/show_bug.cgi?id=19344) | NEW | Adobe Photoshop CS2: Some files missing on installation (appinstall) |  |  |
| A | [33906](https://bugs.winehq.org/show_bug.cgi?id=33906) | NEW | Minimising Photoshop CS2 and restore it doesn't restore the draws | checked 2026-11-08: 3 minimize/restore cycles OK (c9); other WMs/workspaces open |  |
| A | [38244](https://bugs.winehq.org/show_bug.cgi?id=38244) | UNCONFIRMED | Photoshop CS2: Crash at Open file window with choosing multiple files to load |  |  |
| A | [53571](https://bugs.winehq.org/show_bug.cgi?id=53571) | UNCONFIRMED | PhotoshopCS2 Installer custom action page fault | likely = sandbox finding F14 (msiexec 0x6a6 after final dialog) |  |
| A | [55934](https://bugs.winehq.org/show_bug.cgi?id=55934) | UNCONFIRMED | Photoshop CS2 crashes after opening the program - the first time it was working, now it is not anymo |  |  |
| B | [19328](https://bugs.winehq.org/show_bug.cgi?id=19328) | NEW | Shortcuts designed to go to All Users\Start Menu\Programs are instead going to User\Start Menu\Progr |  |  |
| B | [25709](https://bugs.winehq.org/show_bug.cgi?id=25709) | NEW | Some apps doesn't recieve focus in Virtual Desktop Mode |  |  |
| B | [25912](https://bugs.winehq.org/show_bug.cgi?id=25912) | NEW | Multiple applications (Google SketchUp 7/8, Photoshop CS6, Mol) don't display the last drawn frame p |  |  |
| B | [41595](https://bugs.winehq.org/show_bug.cgi?id=41595) | UNCONFIRMED | Photoshop Palettes Remain Above All X11 Windows | same symptom as owner report 34136; not seen on Metacity/Muffin (experiments/ps11412) |  |
| B | [47012](https://bugs.winehq.org/show_bug.cgi?id=47012) | UNCONFIRMED | Photoshop Installer crashes after showing blank window |  |  |
| B | [48439](https://bugs.winehq.org/show_bug.cgi?id=48439) | UNCONFIRMED | Tool selection bug in adobe Photoshop on Linux mint |  |  |
| B | [57715](https://bugs.winehq.org/show_bug.cgi?id=57715) | UNCONFIRMED | Adobe Illustrator CS6 (16): Splash and About windows render white instead of transparent with Wine 1 | Illustrator CS6 white splash: same mechanism as #36 (own-window compose over 0xff surface); note only |  |
| B | [59188](https://bugs.winehq.org/show_bug.cgi?id=59188) | UNCONFIRMED | wayland: Photoshop menu is overlapped by canvas (wrong z-order) | Wayland driver only; owner uses X11 -> record, check only if a Wayland stand exists |  |
| C | [3739](https://bugs.winehq.org/show_bug.cgi?id=3739) | NEW | No windows redraw or repaint in Adobe PhotoDeluxe Home Edition |  |  |
| C | [10814](https://bugs.winehq.org/show_bug.cgi?id=10814) | NEW | Adobe Photoshop 7 main tool window disappears |  |  |
| C | [12007](https://bugs.winehq.org/show_bug.cgi?id=12007) | STAGED | Adobe Photoshop 7.0 Dragging Layers between Images dont work |  |  |
| C | [15932](https://bugs.winehq.org/show_bug.cgi?id=15932) | NEW | Adobe Photoshop 7, CS3 can't load images from URLs |  |  |
| C | [16417](https://bugs.winehq.org/show_bug.cgi?id=16417) | NEW | Scanning with Photoshop CS does give an error | scanner hardware needed (Photoshop CS) |  |
| C | [51997](https://bugs.winehq.org/show_bug.cgi?id=51997) | UNCONFIRMED | photoshop 6.0 will not launch |  |  |
| C | [54426](https://bugs.winehq.org/show_bug.cgi?id=54426) | NEEDINFO | Adobe Photoshop 6.0 and 7.0 main window hangs and always stayed on top |  |  |
| D | [15572](https://bugs.winehq.org/show_bug.cgi?id=15572) | NEEDINFO | Adobe Photoshop CS3 and InDesign CS3 have z-order problems and general painting glitches |  |  |
| D | [15583](https://bugs.winehq.org/show_bug.cgi?id=15583) | NEW | Adobe Photoshop, Dreamweaver CS3 Installer look really bad |  |  |
| D | [15590](https://bugs.winehq.org/show_bug.cgi?id=15590) | NEW | Photoshop CS3 installation fails due to Bonjour Service startup error |  |  |
| D | [20877](https://bugs.winehq.org/show_bug.cgi?id=20877) | NEW | Adobe Bridge cs4 hardware rendering not working |  |  |
| D | [21017](https://bugs.winehq.org/show_bug.cgi?id=21017) | NEW | Adobe Premiere Pro CS4 won't start |  |  |
| D | [23898](https://bugs.winehq.org/show_bug.cgi?id=23898) | NEW | Adobe Photoshop CS5 tool windows stay visible after switching to another program |  |  |
| D | [35805](https://bugs.winehq.org/show_bug.cgi?id=35805) | NEW | "Open file..." box doesn't display image preview in Photoshop CS6 |  |  |
| D | [37928](https://bugs.winehq.org/show_bug.cgi?id=37928) | UNCONFIRMED | Photoshop CS6: Mini-bridge panel does not show directory entries in alphabetical order |  |  |
| D | [37929](https://bugs.winehq.org/show_bug.cgi?id=37929) | UNCONFIRMED | Photoshop CS6: save for web dialog ( and others ) blur when tooltips are expected to appear |  |  |
| D | [38065](https://bugs.winehq.org/show_bug.cgi?id=38065) | UNCONFIRMED | Adobe Photoshop CS3 broken appearance |  |  |
| D | [38105](https://bugs.winehq.org/show_bug.cgi?id=38105) | UNCONFIRMED | Missing window control mechanisms (min/max/expand) and dragging ability while application is in unma |  |  |
| D | [38512](https://bugs.winehq.org/show_bug.cgi?id=38512) | UNCONFIRMED | winetricks fontsmooth-rgb partially smooth fonts in Photoshop CS6 |  |  |
| D | [39085](https://bugs.winehq.org/show_bug.cgi?id=39085) | UNCONFIRMED | Fireworks CS6 window stays on top of other windows |  |  |
| D | [39087](https://bugs.winehq.org/show_bug.cgi?id=39087) | UNCONFIRMED | Photoshop CS6 won't save on a gvfs mounted share |  |  |
| D | [39325](https://bugs.winehq.org/show_bug.cgi?id=39325) | UNCONFIRMED | PhotoShop CC 2014: Names in font dropdown list go blank after scroll down from top. |  |  |
| D | [39326](https://bugs.winehq.org/show_bug.cgi?id=39326) | UNCONFIRMED | PhotoShop CC 2014: Keyboard Shortcut list blank after scrolling down |  |  |
| D | [39327](https://bugs.winehq.org/show_bug.cgi?id=39327) | UNCONFIRMED | PhotoShop CC 2014: Names in layers window go blank after scroll down |  |  |
| D | [39328](https://bugs.winehq.org/show_bug.cgi?id=39328) | UNCONFIRMED | PhotoShop CC 2014: Top tool bar has blank spaces occasionally |  |  |
| D | [39329](https://bugs.winehq.org/show_bug.cgi?id=39329) | UNCONFIRMED | PhotoShop CC 2014: Pen tool ALT function not working when drawing shap |  |  |
| D | [39330](https://bugs.winehq.org/show_bug.cgi?id=39330) | UNCONFIRMED | PhotoShop CC 2014: Preferences window sub-section titles not displaying |  |  |
| D | [39476](https://bugs.winehq.org/show_bug.cgi?id=39476) | UNCONFIRMED | Photoshop CS6: dragging a layer does not make it transparent |  |  |
| D | [39929](https://bugs.winehq.org/show_bug.cgi?id=39929) | UNCONFIRMED | Photoshop CC 2015 doesn't run if it is not cleaned up "SLCache" |  |  |
| D | [41980](https://bugs.winehq.org/show_bug.cgi?id=41980) | UNCONFIRMED | Photoshop CS5 loading problem |  |  |
| D | [42034](https://bugs.winehq.org/show_bug.cgi?id=42034) | NEW | Photoshop CC 2015: Incorrect/Missing texts with builtin gdiplus when using custom theme |  |  |
| D | [42981](https://bugs.winehq.org/show_bug.cgi?id=42981) | NEW | Photoshop CS6, Illustrator CS6 - pressing down when a menu is open switches to the next menu |  |  |
| D | [43693](https://bugs.winehq.org/show_bug.cgi?id=43693) | UNCONFIRMED | Photoshop CS6, clicking on mini-bridge thumbnail crashes bridge with backtrace (JPG files only) |  |  |
| D | [43908](https://bugs.winehq.org/show_bug.cgi?id=43908) | NEEDINFO | Photoshop Elements 11: Crashes when opening a previously created Photoshop document (PSD) file. |  |  |
| D | [44806](https://bugs.winehq.org/show_bug.cgi?id=44806) | UNCONFIRMED | Photoshop CS6: active preference category background color is too dark |  |  |
| D | [44807](https://bugs.winehq.org/show_bug.cgi?id=44807) | UNCONFIRMED | Photoshop CS6 - dragging a guide generates a position indicator with transparent foreground color |  |  |
| D | [45348](https://bugs.winehq.org/show_bug.cgi?id=45348) | NEEDINFO | Photoshop CS6 doesn't recognize images copied to clipboard by Chromium |  |  |
| D | [46096](https://bugs.winehq.org/show_bug.cgi?id=46096) | UNCONFIRMED | Adobe Photoshop CS4 Installer hangs |  |  |
| D | [47329](https://bugs.winehq.org/show_bug.cgi?id=47329) | UNCONFIRMED | Adobe CC setup program looks broken |  |  |
| D | [48435](https://bugs.winehq.org/show_bug.cgi?id=48435) | UNCONFIRMED | Photoshop Cs3 Page fault while loading |  |  |
| D | [49031](https://bugs.winehq.org/show_bug.cgi?id=49031) | UNCONFIRMED | Photoshop Elements 2020 - Installer hangs with blank screen |  |  |
| D | [50012](https://bugs.winehq.org/show_bug.cgi?id=50012) | UNCONFIRMED | Installer failed to initialize for Photoshop CS6 installer |  |  |
| D | [50817](https://bugs.winehq.org/show_bug.cgi?id=50817) | UNCONFIRMED | Photoshop CC (all versions) reset windows position when click on them |  |  |
| D | [50990](https://bugs.winehq.org/show_bug.cgi?id=50990) | NEW | Photoshop CC 2021 fails to start |  |  |
| D | [50999](https://bugs.winehq.org/show_bug.cgi?id=50999) | NEW | Adobe Creative Cloud can't be installed |  |  |
| D | [51132](https://bugs.winehq.org/show_bug.cgi?id=51132) | NEEDINFO | Adobe Photoshop CS6 crashes on start |  |  |
| D | [51606](https://bugs.winehq.org/show_bug.cgi?id=51606) | UNCONFIRMED | Adobe Creative Cloud and apps like Photoshop CC need a browser to login |  |  |
| D | [53805](https://bugs.winehq.org/show_bug.cgi?id=53805) | NEEDINFO | Photoshop CS6 crashes |  |  |
| D | [54963](https://bugs.winehq.org/show_bug.cgi?id=54963) | UNCONFIRMED | Adobe Lightroom needs Windows.Storage.Streams.InMemoryRandomAccessStream |  |  |
| D | [56146](https://bugs.winehq.org/show_bug.cgi?id=56146) | UNCONFIRMED | Adobe Photoshop CC 2017: "About" window dismisses right after appearing |  |  |
| D | [56148](https://bugs.winehq.org/show_bug.cgi?id=56148) | UNCONFIRMED | Adobe Photoshop CC 2017: Camera Raw losing focus after tooltip appearing, all buttons gray out |  |  |
| D | [56170](https://bugs.winehq.org/show_bug.cgi?id=56170) | UNCONFIRMED | Photoshop CC 2021 - Bug "enregistrer sous" |  |  |
| D | [57053](https://bugs.winehq.org/show_bug.cgi?id=57053) | UNCONFIRMED | Photoshop CS6: Toggling Fullscreen breaks the UI |  |  |
| D | [57546](https://bugs.winehq.org/show_bug.cgi?id=57546) | UNCONFIRMED | photoshop 2023 sign in  success, but not respone from browser |  |  |
| D | [58913](https://bugs.winehq.org/show_bug.cgi?id=58913) | UNCONFIRMED | Photoshop CC interface is broken on recent wine dev |  |  |
| D | [59296](https://bugs.winehq.org/show_bug.cgi?id=59296) | UNCONFIRMED | Adobe InDesign CS5.5 crashes on start |  |  |
| D | [60026](https://bugs.winehq.org/show_bug.cgi?id=60026) | UNCONFIRMED | Adobe Photoshop Camera Raw AI-Denoiser issue |  |  |
| D | [60082](https://bugs.winehq.org/show_bug.cgi?id=60082) | UNCONFIRMED | Adobe Elements 2023 aborts or hangs during startup and sign in |  |  |
| E | [3952](https://bugs.winehq.org/show_bug.cgi?id=3952) | NEW | GameGuard does not work in several applications |  |  |
| E | [6394](https://bugs.winehq.org/show_bug.cgi?id=6394) | NEW | the tooltip is not going away in rapget |  |  |
| E | [6508](https://bugs.winehq.org/show_bug.cgi?id=6508) | NEW | wine cannot compile with icc |  |  |
| E | [8051](https://bugs.winehq.org/show_bug.cgi?id=8051) | STAGED | The Sims 2 demo needs support for software vertex processing |  |  |
| E | [11846](https://bugs.winehq.org/show_bug.cgi?id=11846) | STAGED | tablet pressure sensitivity not working in Sai and many other key graphic applications | tablet hardware needed |  |
| E | [12464](https://bugs.winehq.org/show_bug.cgi?id=12464) | NEW | ShellExecute does not integrate well with external handlers |  |  |
| E | [18517](https://bugs.winehq.org/show_bug.cgi?id=18517) | STAGED | Tablet pen pressure or eraser (wacom tablet) are not working in Photoshop CS 4/5 | tablet hardware needed |  |
| E | [23158](https://bugs.winehq.org/show_bug.cgi?id=23158) | NEW | Enhance appdb search filters to allow searching for regressions |  |  |
| E | [30615](https://bugs.winehq.org/show_bug.cgi?id=30615) | NEW | Adobe Audition CS6 (5.0) shows distorted mixer user interface |  |  |
| E | [32900](https://bugs.winehq.org/show_bug.cgi?id=32900) | UNCONFIRMED | The Bat 5.2.2 - keyboard keys stick |  |  |
| E | [39547](https://bugs.winehq.org/show_bug.cgi?id=39547) | NEW | OllyDbg 2.x tooltips steal focus from their parent window |  |  |
| E | [41062](https://bugs.winehq.org/show_bug.cgi?id=41062) | UNCONFIRMED | Evernote 6.1.x: search box loses focus due to tooltips |  |  |
| E | [44931](https://bugs.winehq.org/show_bug.cgi?id=44931) | STAGED | Macromedia Director Player 5.0/6.0 based games fail to run: "This program requires at least 3MB of f |  |  |
| E | [45277](https://bugs.winehq.org/show_bug.cgi?id=45277) | NEW | Multiple applications need Vulkan child window rendering (DxO PhotoLab, Affinity Photo, Google Earth |  |  |
| E | [50865](https://bugs.winehq.org/show_bug.cgi?id=50865) | UNCONFIRMED | Map editor of Heroes of Might and Magic 5 completely not working |  |  |
| E | [51581](https://bugs.winehq.org/show_bug.cgi?id=51581) | UNCONFIRMED | OleView crashes with unimplemented function acledit.dll.SedDiscretionaryAclEditor |  |  |
| E | [51949](https://bugs.winehq.org/show_bug.cgi?id=51949) | NEW | cardfile: black boxes for windows |  |  |
| E | [56608](https://bugs.winehq.org/show_bug.cgi?id=56608) | UNCONFIRMED | Tablet pen pressure no longer working | tablet hardware needed |  |
| E | [57184](https://bugs.winehq.org/show_bug.cgi?id=57184) | NEEDINFO | DirectX9 not working properly with OpenGL. |  |  |
| E | [57224](https://bugs.winehq.org/show_bug.cgi?id=57224) | UNCONFIRMED | Strange Behavior with >64 Processing Cores |  |  |

Rough volume: A 9 (2 partly done), B 8, C 7, D ~51, E 20. Real work
(reproduce + fix) is expected only in A and some of B; D/E are reading-only.

## Work order for real work (Opus, 2026-11-08, from descriptions + last comments)

Ranked by harm: data loss > blocks work > affects many users > cosmetic.
Each item still starts with the full-bug read of card PS-0.

1. **38244** CS2 crashes in the Open dialog when several JPEG files are
   selected (page fault; last asked to retest on Wine 5.6). A crash while
   opening files can lose unsaved work in other documents. Retest on 11.0
   with synthetic JPEGs (multi-select in the OS dialog).
2. **9623** "Could not complete ... because a system font was not found"
   without Times New Roman (corefonts); blocks operations for every user
   without corefonts. Check the fresh stand prefix (no corefonts); the fix is
   likely a font substitute/alias recipe (cf. FastStone font work), not a
   Wine core change.
3. **9802** ImageReady CS2 (bundled) crashes on startup (C++ exception after
   WM_MOUSEACTIVATE, still valid on Wine 4.12). Blocks a whole bundled app.
4. **55934** CS2 crash on later starts after it once worked (vague; asked to
   upgrade). Retest: start/quit CS2 several times, lock/unlock is not
   reproducible headless; likely `insufficient data`.
5. **25912** (SketchUp/Photoshop CS6) window content one input event behind
   (expose not triggered). Generic winex11 paint lag; check whether CS2's
   canvas/palettes lag on the stand before investing.
6. Installer: **53571** custom-action page fault on the file-association page
   (bisected to a 2022 user32 commit; maybe already resolved) together with
   sandbox findings F14 (msiexec 0x6a6 after Finish) and F13 ("&Finish"
   labels). The installation still completes, so below the runtime crashes.
7. **47012** a Photoshop installer crashes after a blank window (version to
   determine; AppDB says copy an installed tree; 47015 has a workaround).
8. Cosmetic / low impact: **19344** a few files missing after install
   (install.adb, Notepad.LNK), **19328** shortcuts land in the user's Start
   Menu instead of All Users, **25709** focus in virtual-desktop mode,
   **19343** installer edit-control class names (automation only).
Already handled this round: 11412, 33906 (retested OK on Metacity/Muffin),
34133/#36 splash (fixed on stock Wine via prefill proxy), 34134/#35 (Adobe's
own resize; Windows CI pending). 48439 is CS6 (move to D).
