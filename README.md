# dllmgr private Wine runtimes

Packages built by CI (`.github/workflows/app-isolation.yml` on main) and
published here by the cloud agent, because release creation through the API
is refused for both the agent and the workflow token (docs/sandbox-findings.md
F20). dllmgr pins each package by commit and SHA256 in
`scripts/private-runtime.json`; nothing here is ever rewritten.

Each directory: `wine-11.0-app-isolation.zip` (the overlay), `SHA256SUMS`,
`SOURCE.txt` (upstream Wine commit and the patches, which are inside the zip;
complete source: Wine at that commit plus those patches from this repository).
