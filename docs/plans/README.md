# Task cards for executing agents (Sonnet-ready)

Written by Opus 2026-11-08. Cognitively hard parts (mechanism, measurement
traps, delivery design) are decided here; executing agents follow the cards,
measure, and **stop and ask** at the listed points instead of improvising.

Card format: Goal / Inputs / Steps / Done when / Stop and ask if / Traps.
Claim a card's issue first (docs/multi-agent-protocol.md). One card = one
claim. Escalate to the owner (or an Opus session) whenever a card says so,
or when a result contradicts the card's expectation twice.

Universal traps (learned the hard way, apply to every card):

- Judge on-screen pixels from the X server (tests/wine/xsample.c, `import`),
  never from Wine's GetPixel/screen DC (docs/sandbox-findings.md F18).
- Flicker/paint measurements need a non-compositing WM: STAND_WM=metacity.
  Muffin (the owner's Cinnamon) hides or invents phases (F17); a pass there
  proves nothing about the owner's laptop.
- Photoshop CS2 and FastStone are DPI-unaware; the stand runs 192 DPI, so
  window coordinates seen by the app are halved. Capture/draw code must work
  in physical pixels (patches/dllmgr-27/prefill.c).
- WineHQ stock packages use old WoW64 (32-bit apps load i386-unix/*.so); the
  dllmgr private runtime uses new WoW64 (x86_64-unix only). Rebuild for the
  layout you actually test.
- A gate is valid only if it fails on the known-bad variant. Before trusting
  a new test, make it fail once on purpose.
- Synthetic keys can be ignored by Photoshop's main window (F16): use mouse
  and menu mnemonics.
- Anything that launches the app must go through the same path the owner
  uses; `dllmgr run` vs plain `wine` give different results
  (docs/tasks/27-every-launch-path.md).

Plans: [photoshop-cs2.md](photoshop-cs2.md), [faststone.md](faststone.md),
[far3.md](far3.md), [putty.md](putty.md).
