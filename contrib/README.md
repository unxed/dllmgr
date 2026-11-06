# Proposed fix-it-in-wine fix

`fix-it-in-wine-codepage.patch` applies to `unxed/fix-it-in-wine` main at
`0b37d498ef4fd4b1077421af62974a9b3587e80a`:

```sh
git apply /path/to/fix-it-in-wine-codepage.patch
```

It decodes redirected Wine registry output with the locale's OEM code page
(the table and Unix selection algorithm from `unxed/localecp`), preserves
UTF-8 Unix diagnostics, and reads the previous registry value before replacing
the DLL. The locale table retains its BSD license in `tools/localecp.LICENSE`.
`FIW_WINE_ENCODING` can specify a frontend's output encoding explicitly.

dllmgr's `apply-scripts` CI checks its scripts against both the unchanged
helper and this patched helper, and runs the patched helper's test suite.
The runtime adapter in dllmgr works before the upstream patch is applied.
