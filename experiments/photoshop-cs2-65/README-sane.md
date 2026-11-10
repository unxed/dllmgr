# Photoshop start: Wine's TWAIN source probes all SANE backends (2026-11-10)

Found with the new in-process sampler (DLLMGR_SAMPLE in the dllmgr-27
proxy): from ~6.8 s after launch the main thread sits in sane.ds
(twaindsm.dll -> sane.ds -> libsane sane_get_devices) while Photoshop lists
TWAIN sources for File > Import. Wine's sane.ds turns every SANE device into
a TWAIN source, so listing sources means probing every backend.

Stand (Xvfb :96 + Muffin, rt-cur3, prefix copy; time from launch to the
trial Activation dialog, experiments/photoshop-cs2-47/tstart.sh):
- default (libsane with 77 backends incl. airscan): 19.3, 19.4 s
- network backends off (net, escl, airscan): 19.2 s (not the cost)
- no backends (SANE_CONFIG_DIR=/nonexistent): 14.6, 15.2 s
So ~4.5 s of the start is local backend probing with no scanner attached.

Setting `scanner=off|on`, default **on** for every application (the owner,
2026-11-10: never switch a feature off without explicit permission; scanners
are needed in Photoshop). `dllmgr set photoshop-cs2 scanner=off` is only an
opt-in speedup. The real fix to find: keep TWAIN scanning and remove the
start cost (lazy sane.ds: report a source without probing, probe on open;
or probe in the background).

## Fix that keeps scanning: #74, patches/dllmgr-74-sane.patch

sane.ds Unix side: TWAIN sources from the previous probe's device list
($XDG_CACHE_HOME/wine-sane-devices) at once; a detached grandchild process
(fork, no Wine calls) re-probes and rewrites the cache; MSG_OPENDS probes
in-process as before, so a scan always uses the current devices. No cache
yet or DLLMGR74_SANE_SYNC=1: the old synchronous probe. A first version
probed in a pthread: Photoshop died silently right after the source
manager unloaded sane.ds (thread in an unloaded library), so it uses a
process instead.

Stand, time to the trial dialog: cached 15.2, 16.4, 15.5, 15.9 s;
DLLMGR74_SANE_SYNC=1 17.9, 20.7, 20.5 s; first start (no cache) 20.4 s.
SANE "test" backend (SANE_CONFIG_DIR with dll.conf "test", 2 devices):
Photoshop's source list (+twain trace) is the same from the cache as from a
probe; tw/twopen.c (list sources through twain_32, MSG_OPENDS/CLOSEDS):
open works with stock sane.so, new sane.so without and with cache. Seen in
passing: asking twain_32 to open "test:1" opens test:0, with stock Wine too
(DSM / sane.ds identity matching), not touched.
