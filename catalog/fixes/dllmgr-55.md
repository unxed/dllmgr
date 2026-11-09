---
id: dllmgr-55
kind: fix
bug: https://github.com/unxed/dllmgr/issues/55
title: "threadpoolwinrt: Windows.System.Threading.ThreadPoolTimer is not implemented"
dlls: [threadpoolwinrt]
wine: [wine-11.21]
patch: https://raw.githubusercontent.com/Max-RM/wine/2bf1881262ef7ab7452deff0a2427a25e477e589/patches/threadpooltimer-winrt.patch
patch_sha256: 29716668274d5167922658310616a73890d605c58044e9bc80734d6d35b9e120
evidence: https://github.com/unxed/fix-it-in-wine/issues/15
authors: [Max-RM]
license: LGPL-2.1-or-later
---

# dllmgr-55

External fix by Max-RM (Wine 11.21 on an ARM32/armhf host, Windows ARM32
games; https://github.com/Max-RM/wine/commit/2bf1881262ef7ab7452deff0a2427a25e477e589). Not measured by dllmgr
yet; the author reports Minecraft PE 0.10.4.40 and Bedrock 1.2.8 running with
his set of fixes.

## Problem

Programs that create a DispatcherTimer (WinRT, UWP-style apps) receive no timer ticks: the runtime class Windows.System.Threading.ThreadPoolTimer is declared but threadpoolwinrt does not implement it.

## Windows behavior

ThreadPoolTimer.CreateTimer / CreatePeriodicTimer call the handler once / periodically from a thread-pool thread; Cancel stops it.

## The fix, in words

Add the runtime class and its statics interface to threadpoolwinrt (and the IDL in include/windows.system.threading.idl). The author uses one thread per timer; an upstream version would rather sit on the existing Win32 thread pool timer (CreateThreadpoolTimer) and come with tests.
