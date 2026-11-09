---
id: dllmgr-57
kind: fix
bug: https://github.com/unxed/dllmgr/issues/57
title: "winebuild: 32-bit host build runs out of address space on resource-heavy DLLs"
dlls: [winebuild]
wine: [wine-11.21]
patch: https://raw.githubusercontent.com/Max-RM/wine/2bf1881262ef7ab7452deff0a2427a25e477e589/patches/winebuild-arm32-resources.patch
patch_sha256: c35d042611ba1c39b09f106c7c327cab160ccc0da386f14dd7ae7118fe4b9bd2
evidence: https://github.com/unxed/fix-it-in-wine/issues/15
authors: [Max-RM]
license: LGPL-2.1-or-later
---

# dllmgr-57

External fix by Max-RM (Wine 11.21 on an ARM32/armhf host, Windows ARM32
games; https://github.com/Max-RM/wine/commit/2bf1881262ef7ab7452deff0a2427a25e477e589). Not measured by dllmgr
yet; the author reports Minecraft PE 0.10.4.40 and Bedrock 1.2.8 running with
his set of fixes.

## Problem

Building Wine on a 32-bit host (armhf) fails for DLLs with many resources: the LLVM integrated assembler maps the whole .res file for every .incbin directive and exhausts the address space, then reports a bogus missing incbin file.

## Windows behavior

Not applicable (build tool).

## The fix, in words

In output_resources (tools/winebuild/res32.c), do not .incbin the whole .res once per resource. The author writes each resource to its own temporary file; an upstream version may prefer fewer files (or .byte data) to keep builds with thousands of resources fast.
