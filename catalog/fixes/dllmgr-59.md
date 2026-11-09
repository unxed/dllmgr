---
id: dllmgr-59
kind: fix
bug: https://github.com/unxed/dllmgr/issues/59
title: "wined3d: command stream lost wakeup freezes rendering (ARM)"
dlls: [wined3d]
wine: [wine-11.21]
patch: https://raw.githubusercontent.com/unxed/dllmgr/main/patches/max-rm/wined3d-cs-lost-wakeup.patch
patch_sha256: 0ec9f09228a633b257019f5e84fcfefef7fabddc9e3f8e04b659fd84d0c30a4b
evidence: https://github.com/unxed/fix-it-in-wine/issues/15
authors: [Max-RM]
license: LGPL-2.1-or-later
---

# dllmgr-59

External fix by Max-RM (Wine 11.21 on an ARM32/armhf host, Windows ARM32
games; https://github.com/Max-RM/wine/commit/2bf1881262ef7ab7452deff0a2427a25e477e589). Not measured by dllmgr
yet; the author reports Minecraft PE 0.10.4.40 and Bedrock 1.2.8 running with
his set of fixes.

## Problem

Rendering freezes after 15 to 110 seconds on ARM: wined3d_cs_mt_finish spins waiting for the queue to drain while the command stream thread sleeps after a missed wakeup.

## Windows behavior

Not applicable (Wine-internal threading).

## The fix, in words

While wined3d_cs_mt_finish waits past the spin limit, re-wake the command stream thread (NtAlertThreadByThreadId, or the event). This is a workaround; the root cause is most likely missing ordering between the queue tail store and the waiting flag on weakly ordered CPUs, which an upstream fix should address with the right barriers. The patch also applies to wine-11.0.
