#!/bin/sh
# Kill leftover Wine processes of this stand without matching our own shell.
# The [s] trick keeps the pattern from matching the pkill command line itself;
# $$ and its ancestors are excluded so a caller that mentions the wine path
# in its own command line is never killed.
# Wine command lines use Windows backslashes ("C:\windows\system32\..."), so
# the path separator is matched as [\\/].
self=$$
ppid=$PPID
for pat in '[w]ine-stable/lib/wine/../../bin' '[w]ine-stable/bin/wine' \
	'[w]ineserver' \
	'[s]ystem32[\\/]wine' '[s]ystem32[\\/]services' '[s]ystem32[\\/]explorer' \
	'[s]ystem32[\\/]rundll32' '[s]ystem32[\\/]winedevice' '[s]ystem32[\\/]conhost' \
	'[s]ystem32[\\/]wineboot' '[s]ystem32[\\/]notepad' '[s]ystem32[\\/]msiexec' \
	'[s]ystem32[\\/]control' '[s]ystem32[\\/]setup' '[s]ystem32[\\/]start' \
	'[s]ystem32[\\/]winedbg' \
	'[s]yswow64[\\/]wine' '[s]yswow64[\\/]notepad' '[s]yswow64[\\/]msiexec' \
	'[s]yswow64[\\/]control' '[s]yswow64[\\/]setup' '[s]yswow64[\\/]rundll32' \
	'[s]yswow64[\\/]winedevice' '[s]yswow64[\\/]conhost' '[s]yswow64[\\/]services' \
	'[i]386-unix[\\/]wine' '[x]86_64-unix[\\/]wine' \
	'[i]nstall_mono' '[s]etupapi,InstallHinfSection' \
	'[P]hotoshop CS2' '[S]etup.exe'; do
	for pid in $(pgrep -f "$pat" 2>/dev/null); do
		[ "$pid" = "$self" ] && continue
		[ "$pid" = "$ppid" ] && continue
		kill -9 "$pid" 2>/dev/null
	done
done
sleep 1
exit 0
