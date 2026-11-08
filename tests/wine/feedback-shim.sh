#!/bin/sh
# #38 shim check: stock Wine without the user32 exports + patches/dllmgr-38
# version.dll proxy must give the Windows results (fixtures/feedback-windows.txt,
# measured by the windows-probes CI job) for a statically importing exe, and
# patch a DLL loaded later. Needs a display (run in a stand session):
#   sh scripts/sandbox-stand.sh session sh tests/wine/feedback-shim.sh WINE_BIN
set -eu
wine=$1
here=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d)
sh "$here/../../patches/dllmgr-38/build.sh" x86_64 "$work/version.dll" >/dev/null
x86_64-w64-mingw32-gcc -O2 -Wall -DSTATIC_IMPORT -o "$work/feedback-static.exe" "$here/feedback-get.c" -lversion
x86_64-w64-mingw32-gcc -O2 -Wall -shared -DLATE_DLL -o "$work/feedback-late.dll" "$here/feedback-get.c"
cd "$work"
WINEDLLOVERRIDES=version=n,b timeout 60 "$wine" feedback-static.exe 2>/dev/null | tr -d "\r" >out.txt || :
rc=0
grep '^case=' out.txt | grep -v '^case=late' | diff "$here/fixtures/feedback-windows.txt" - >/dev/null || rc=1
grep -q '^case=late_set ret=1' out.txt || rc=1
grep -q '^case=late_get_after_set ret=1 .* value=1' out.txt || rc=1
echo "cases=$(grep -c '^case=' out.txt) verdict=$([ $rc = 0 ] && echo pass || echo FAIL)"
[ $rc = 0 ] || cat out.txt >&2
cd / && rm -rf "$work"
exit $rc
