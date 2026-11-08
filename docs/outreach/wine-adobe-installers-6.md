# Prepared reply: PhialsBasement/wine-adobe-installers#6 (not posted)

Target: https://github.com/PhialsBasement/wine-adobe-installers/issues/6
Status: prepared 2026-11-08 by Claude (dllmgr #38); the owner posts it.
After posting, record the comment URL here and in issue #38.

---

Hi! This looks fixed on our side, with a small Wine patch you can apply to
the fork.

**Cause.** Photoshop 2024 imports `SetWindowFeedbackSetting` from user32.
Wine's user32 does not export it (in 11.0 and in current master the spec line
is commented out), so the loader binds a stub that aborts the process the
first time it is called, which happens when an image is opened or created.
That is exactly the `Unimplemented function USER32.dll.SetWindowFeedbackSetting`
abort in the log above.

**Fix.** Implement `SetWindowFeedbackSetting` and `GetWindowFeedbackSetting`
in user32. They configure per-window touch/pen visual feedback; Wine draws no
such feedback, so the values are only stored and returned. We measured the
exact Windows behaviour on a Windows runner (argument validation, per-window
storage, reset with a NULL config, unset values, ancestor lookup, size query,
last-error handling: 19 cases) and the patched Wine prints identical results.

- Patch (against wine-11.0, applies to user32 only, PE side):
  https://github.com/unxed/dllmgr/blob/main/patches/dllmgr-38.patch
- Reproducer (static import like Photoshop; aborts on stock Wine, passes
  with the patch): https://github.com/unxed/dllmgr/blob/main/tests/wine/feedback-setting.c
- Windows reference probe: https://github.com/unxed/dllmgr/blob/main/tests/wine/feedback-get.c

**Install.** For this fork: apply the patch (`git apply dllmgr-38.patch`) and
rebuild; only `user32.dll` changes. We have not run Photoshop 2024 itself
(it needs a Creative Cloud login), so a confirmation from someone with the
original setup would be very welcome — if the next unimplemented function
shows up, please post the new log line.

The fix is part of dllmgr (https://github.com/unxed/dllmgr), a project that
collects verified Wine fixes per application; contributions welcome.
