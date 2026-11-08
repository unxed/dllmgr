# Owner's exact close-button reproduction,2026-11-08

These are faithful button crops from the owner's four attached3072x1728
screenshots. Full desktop/photos/folder history are omitted. Crop coordinates
and source hashes are in sources.json.

1. ![Initially closed, gray button](1.png)
2. ![First click, dropdown open and button blue](2.png)
3. ![Second click, dropdown closed but button still blue](3.png)
4. ![Pointer moved, dropdown still closed and button gray](4.png)

**The reported bug is3→4, after the second click closes the popup.** The owner
is unsure what Windows should display while the list is open and does not ask
to change that without a comparison. The earlier stationary/motion experiment
kept the list open during movement, so it did not cover this exact sequence.

Next regression: open, release, close with a second click **without intervening
pointer movement**, release and dwell, then move inside/outside the button.
Avoid redundant activation or movement which could refresh the stale image.
Compare Windows and Wine, preserve the installed private recipe, and use only
an invisible display/disposable prefix or hosted CI.

## Reproduced on the invisible stand

The exact no-intervening-motion closing sequence reproduces on portable8.5,
private v3 modules and192DPI. Dropped/public pressed/list-visible all become0
but the button remains pixel-identical to its open/pressed appearance. After
moving outside it changes1216 pixels. See v3-before.txt and v3-before-pixels.json.
The expanded check fails on that v3 capture as required. Native module loading
was verified. The earlier test moved before closing and therefore masked it.

Source lead: the listbox's close path calls CBRollUp without requesting a button
redraw. For CBS_DROPDOWNLIST that path repaints only the text rectangle. The
candidate makes themed closing include the button; classic painting and public
state/input stay unchanged. Candidate source: ../close-repaint.patch. It is not
installed/published as a product fix yet. Manual path-dropdown workflow input
close_repaint_candidate=true builds/tests it isolated and composed at96/192DPI.

## Delivered close correction

`faststone-v4` / `dllmgr-21-v2` contain the exact binaries from successful
[CI42499612512](https://github.com/unxed/dllmgr/actions/runs/42499612512),
source2ea67cfd9ab437f19db760dd9808d98e62cc7384. Isolated and composed
comctl32 variants pass at96/192DPI, including native loading and byte-exact undo.

Installed privately on the owner's laptop, without restarting their open
FastStone. A separate disposable prefix on invisible Xvfb:93 then loaded copies
of the **installed generation's exact DLLs**, not a different candidate.
`v4-after.txt` and `v4-after-pixels.json` pass the same real-app gate at192DPI:
pressed→closed1216 pixels immediately; no change after stationary dwell or
inside movement. The148-pixel change on leaving/re-entering is the hover border.
The older v3 fails with0 pixels immediately and1216 only after movement.
`v4-*.png` contain synthetic button crops. Owner visual acceptance remains open.

Installed generation f8e2332674decdb2f1916d0c1a5fbe1707337919f4474f3ff0e5f8f592cd2385:
comctl32 SHA2568291684bf532ebf86c4899e578e2d1200fd46cfa13b6490f5da1c0d57d0b9394,
GDI+ SHA256a9baafe5a4de3b30e2288a60c59dc47760265d3d97195a829ed7217191414d67.

Wine words-only report: [60720](https://bugs.winehq.org/show_bug.cgi?id=60720#c0).
The catalog keeps its existing dllmgr-21 issue identity; the upstream link is
recorded in its prose and in the submissions ledger.
