# Vision

The owner's view of why dllmgr and fix-it-in-wine exist, and what they should
become. Recorded on 2026-11-06.

The owner's text is kept as written. Editorial notes by the agent are marked
**[Note N]** and listed after the text. They add sources or narrow a claim;
they do not change the author's words.

## The owner's text

### Original (Russian, verbatim)

> Поскольку Wine не берут код из LLM, скилл контрибьютит в Багзиллу словесное
> описание не только бага, но и того, как работает его фикс, и того, как эта
> логика тестировалась и с каким результатом. И ведёт свою базу фиксов
> параллельную, чтоб от апстрима не зависеть.
>
> И там тулза специально под это сделанная используется, dllmgr, это как
> playonlinux и прочие bottles, только с гранулярностью не до версии wine, а до
> DLL и конкретных заплаток. winetricks на стероидах, где вместо нативных либ -
> вайновские с ИИ фиксами (хочешь - бери бинарник, хочешь - словесное описание,
> и пусть агент у тебя прямо в коде вайна поправит и соберёт).

### English rendering

> Since Wine does not take code from LLMs **[Note 1]**, the skill contributes to
> Bugzilla **[Note 2]** a description in words not only of the bug, but also of
> how its fix works, and of how that logic was tested and with what result
> **[Note 3]**. And it keeps its own parallel database of fixes, so as not to
> depend on upstream.
>
> And it uses a tool made specially for this, dllmgr. It is like PlayOnLinux
> and the likes of Bottles, only the granularity is not a Wine version but a
> DLL and specific patches. winetricks on steroids, where instead of native
> libraries you get Wine's own, with AI fixes (take the binary if you want, or
> take the description in words and let your agent fix it right in the Wine
> code and build it **[Note 4]**).

### Why this revives the Wine ecosystem (the owner's points, translated)

1. **Fixes as text, not code.** A text description of a fix lets AI help in
   spite of Wine's restrictions. Code could probably be written from such
   descriptions even by models trained on deterministic data that surely
   contains no Microsoft code **[Note 5]**. Whether to do that is Wine's own
   decision. What matters is that we have our own way around it: the fixes.
2. **A much shorter feedback loop.** Today it is "a user reports a bug, it is
   fixed in 5 years, it reaches the user's distribution in 10, but the user
   has moved to a Mac" **[Note 6]**. Distributing fixes and fixed libraries
   separately solves this.
3. **No bottleneck of a few developers** (who know the code, are willing to
   build a huge C project, and so on). Agents do this work. It is relatively
   easy to formalize: API specifications exist; the original can be studied
   as a black box **[Note 7]** and compared with the reference on GitHub's
   Windows CI; no code is sent to Wine, so the clean room is kept.

### Vendor kits (the owner's new idea, translated)

Give software vendors tooling to make vendor kits. For example, FastStone's
developers could ship our fixed DLLs inside their own package, enabled by
default, so the program works out of the box everywhere. The plan is in
[vendor-kits.md](vendor-kits.md).

## Editorial notes

**[Note 1]** Confirmed. Wine's
[Clean Room Guidelines](https://gitlab.winehq.org/wine/wine/-/wikis/Clean-Room-Guidelines)
(read on 2026-11-06) say: "Don't use an LLM tool to generate code. There's no
guarantee that the training material of that LLM respects our Clean Room
Guidelines, or that its output is compatible with the LGPL." The rule is about
code. We found no published Wine rule about AI-written bug reports or
descriptions.

**[Note 2]** A goal, not yet a fact. As of 2026-11-06 the skill has posted
nothing to WineHQ Bugzilla. It prepares the text; a person approves every post.
Before anything is posted, it must pass the gate in
[faststone.md](faststone.md#gate-for-wine-bugzilla-reports-and-follow-ups): a
test that reproduces the reported behavior fails on stock Wine and passes with
only the proposed change, and the change is also checked by eye in the real
application.

**[Note 3]** The description says what Windows does (as measured by a test),
what to change in Wine's behavior, and how the change was checked. It is not
the patch retold line by line. Whether Wine developers act on a description
written with AI help is their decision. We label such text as AI-assisted.

**[Note 4]** "Build it" means one or a few DLLs, not all of Wine. In the
fix-it-in-wine check (its concept, §5.2) comctl32 and comctl32_v6 built in
39 seconds after configure. The code an agent writes this way is for the
user's own machine and our catalog. It is never sent to Wine.

**[Note 5]** The owner's hypothesis. Wine's guideline gives two reasons:
unknown training material, and unknown license compatibility of the output.
A model trained only on known-clean data addresses the first reason. It is not
clear that it addresses the second.

**[Note 6]** An illustration of the delay, not a measurement.

**[Note 7]** Edited. The owner's wording allowed studying the original in any
way. Under Wine's clean-room rules it may be studied **only as a black box**: test programs that call
the API and check the results, run on real Windows (for example GitHub's
Windows runners). Not allowed: disassembling Microsoft code, examining its
debug symbols, `+relay` traces of native Microsoft components, test programs
that dump internal tables, Microsoft source code (even "public" or leaked),
and ReactOS source code. Microsoft documentation is allowed, but a test
program is preferred.

## From vision to plan

| Piece | Where | Status |
| --- | --- | --- |
| Parallel fix database, keyed by bug | `catalog/fixes/`, D2, D14 | exists |
| Proof per fix: fails without, passes with, passes on Windows | `results` rows, [data-model.md](data-model.md) | exists for the FastStone fixes |
| Description in words, implementable without the patch | fix file prose, D17 | proposal |
| Clean-room rules for everything sent to Wine | D16 | decided by this text, pending review |
| Bugzilla posting gate | [faststone.md](faststone.md#gate-for-wine-bugzilla-reports-and-follow-ups) | documented; nothing posted yet |
| Binary or build from source | `release` in `when` rows; `--build` | exists for FastStone |
| One click for the user | `dllmgr fix` finds the apps in a prefix; a menu entry runs it; D18 | first step done |
| Vendor kits | [vendor-kits.md](vendor-kits.md), D19 | proposal |
| Short feedback loop for new Wine releases | CI re-runs the checks on each release; an upstream fix shows up as `without: pass` | planned |
| Other targets (ReactOS, LiberNT, CusDeb OS) | [issue 13](https://github.com/unxed/dllmgr/issues/13); environment key `target` | design input |
