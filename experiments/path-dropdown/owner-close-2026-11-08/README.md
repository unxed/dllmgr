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
