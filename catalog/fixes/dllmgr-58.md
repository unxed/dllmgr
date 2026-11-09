---
id: dllmgr-58
kind: fix
bug: https://github.com/unxed/dllmgr/issues/58
title: "winex11: stale clip window after desktop recreate; touch/WM_POINTER from mouse; pointer grab over VNC"
dlls: [winex11]
wine: [wine-11.21]
patch: https://raw.githubusercontent.com/unxed/dllmgr/main/patches/max-rm/winex11-touch-grab-clipwindow.patch
patch_sha256: 9d21328110b7da51393a9192d3b2b36772208a01bfbf978dc2d8e94368416713
evidence: https://github.com/unxed/fix-it-in-wine/issues/15
authors: [Max-RM]
license: LGPL-2.1-or-later
---

# dllmgr-58

External fix by Max-RM (Wine 11.21 on an ARM32/armhf host, Windows ARM32
games; https://github.com/Max-RM/wine/commit/2bf1881262ef7ab7452deff0a2427a25e477e589). Not measured by dllmgr
yet; the author reports Minecraft PE 0.10.4.40 and Bedrock 1.2.8 running with
his set of fixes.

## Problem

Three separate problems on X11: (1) the cursor clip window is reparented into the desktop window and dies with it, so a recreated desktop leaves a stale id and the next X request fails with BadWindow; (2) programs that only listen to touch / WM_POINTER input (WinRT CoreIndependentInputSource) get nothing from a mouse; (3) the pointer grab together with the clip window makes the window manager close button unusable over VNC.

## Windows behavior

(1) is a Wine-internal object, no Windows counterpart. (2) and (3) are host-environment workarounds, not Windows behavior.

## The fix, in words

(1) Keep the clip window a child of the root window and validate it before use (generic, worth sending separately). (2) Opt-in mode WINE_X11_MOUSE_AS_TOUCH (1 = legacy touch extra info, p = WM_POINTER through the wineserver). (3) Opt-in mode that skips the pointer grab. (2) and (3) are opt-in workarounds and stay off by default.
