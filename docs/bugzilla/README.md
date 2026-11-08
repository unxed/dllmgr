# WineHQ feedback

Before preparing feedback, check `submissions.json` and read the entire live
ticket. Existing reports receive a follow-up; search for duplicates before
creating a new report. Handle one report at a time.
Also audit local fix records with only a dllmgr issue: covering the existing
Wine numbers does not complete reporting while a verified local fix still
needs its own upstream report. Track each such pending new report explicitly;
its `bug_url` remains null until publication is verified.

Write the text in English and plain text, without Markdown. Describe measured
behavior, environment and verification; keep unsupported conclusions out.
The verification gate in `docs/faststone.md` still applies. The owner may post the text or explicitly authorize the agent to submit it.
On2026-11-08 the owner explicitly authorized posting the remaining reports
through the authenticated WineHQ session. Never mark a prepared draft as posted. After publication, verify the
comment and record its exact URL and UTC timestamp in `submissions.json`.
Each record's `fix_record` points to the catalog fix or separate workaround
description; that description links back to this ledger and the published
comment. The problem overview is `docs/faststone.md#published-wine-feedback`.

## AI disclosure

Owner decision, 2026-11-07: do not add a statement that an agent wrote the
report unless Wine explicitly requires that disclosure. If such a requirement
is introduced or requested for the report, follow it and record its source.
Do not falsely claim human authorship or conceal provenance if asked directly.

Checked on 2026-11-07:

- https://gitlab.winehq.org/wine/wine/-/wikis/Clean-Room-Guidelines
- https://gitlab.winehq.org/wine/wine/-/wikis/Bugs

Neither checked page requires AI disclosure in bug-report prose. The clean-room
rule prohibits using an LLM to generate code for Wine; it does not impose a
disclosure footer on bug-report text. Our words-only, no-agent-code and
no-agent-code-links policy remains in force. The unconditional disclosure
sentence in the current fix-it-in-wine skill/template is a local instruction,
not a requirement found in these Wine rules. This owner decision overrides it
for dllmgr reports. A corresponding patch for that repository is in
`contrib/fix-it-in-wine-report-disclosure.patch`.
