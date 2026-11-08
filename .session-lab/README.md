# Paused task35: unvalidated live Windows session draft

Agent: codex-debian-8c42. Owner requested pause before any dispatch. Do not merge this branch or start it automatically.

Goal: reuse task37 HTTPS command branches on a native Windows runner so installer/UIA diagnostics can be inspected before job completion. Main retains the batch ps35-windows workflow and all verified checkpoints. This branch only is an experimental alternative; no global execution policy.

Draft lab.py was ported locally from the previous Linux session transport: taskkill for owned children, PowerShell/UIA screenshots, Windows environment whitelist, UTF8 gh output. Only Python syntax was checked; Windows runtime behavior is UNTESTED. Workflow prepares cached source and runs inspection, then starts the bus. No workflow run exists for this draft.

Known unfinished details: PS35_KEEP_UI is passed but main measurement code does not yet implement it; do not assume failed automation retains its windows. Review cancellation/child cleanup, PowerShell output encoding and snapshot behavior before use. The parent batch run42534865330 was cancelled for the owner's pause; inspect its final artifact first. Never bypass trial expiry/activation or supply a serial; source must stay the pinned Wayback archive/cache.

Resume details are in main: experiments/ps35-open-dialog/windows-ci/PAUSED.md. Claim35 is released at pause; reacquire only after checking others. No WineHQ publication.
