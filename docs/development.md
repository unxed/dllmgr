# Development policy: RUP principles and immediate delivery

Owner decision, 2026-11-08. dllmgr follows RUP principles: iterative,
incremental development driven by the user's needs, early work on the main
risks, and feedback from each working increment. This is a practical working
rule, not a requirement to add process paperwork.

**Deliver immediately.** Make small, atomic, reversible changes. As soon as a
useful increment works, commit it, push it to `main`, and give it to the user
for testing. On the owner's machine, install the delivered fix within the
existing task authorization. Do not accumulate finished changes locally, on
unmerged branches, or behind a larger unfinished feature.

The normal loop is:

1. Choose the smallest useful change addressing the user's current problem.
2. Implement it and run the minimal relevant check against a known regression.
3. Immediately commit and push that increment to `main`, and deliver it to the
   user. State what is available now and how to use or undo it.
4. Continue broader CI, additional environments and edge cases after delivery;
   run them in parallel where possible. Report their actual status honestly.
5. Use user feedback and test results for the next small atomic increment.

Do not hold a working fix for exhaustive testing, perfect architecture,
cosmetic polish, unrelated cleanup, or completion of every item in a test
matrix. Those are subsequent increments. A failed later check calls for a
prompt small correction, not another pile of unpublished changes.

Immediate delivery does not mean claiming unverified behavior is proven or
replacing shared system files despite a known isolation defect. Keep each
increment's scope clear, retain rollback, preserve already working applications,
and disclose limitations. When one experiment is blocked, deliver the
independent completed work and continue another useful task.

**Priority: working software in the user's hands, then refinement from real
feedback. Avoid perfectionism and accumulated changes.**
