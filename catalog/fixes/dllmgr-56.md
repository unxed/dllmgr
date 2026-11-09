---
id: dllmgr-56
kind: fix
bug: https://github.com/unxed/dllmgr/issues/56
title: "d3dcompiler: #include paths with forward slashes fail to open"
dlls: [d3dcompiler_43, d3dcompiler_47]
wine: [wine-11.21]
patch: https://raw.githubusercontent.com/Max-RM/wine/2bf1881262ef7ab7452deff0a2427a25e477e589/patches/d3dcompiler-include-forward-slash.patch
patch_sha256: 835e073f894b62ec75c10d2b262f6c0de986eddae579a673abf492a7f5d62df5
evidence: https://github.com/unxed/fix-it-in-wine/issues/15
authors: [Max-RM]
license: LGPL-2.1-or-later
---

# dllmgr-56

External fix by Max-RM (Wine 11.21 on an ARM32/armhf host, Windows ARM32
games; https://github.com/Max-RM/wine/commit/2bf1881262ef7ab7452deff0a2427a25e477e589). Not measured by dllmgr
yet; the author reports Minecraft PE 0.10.4.40 and Bedrock 1.2.8 running with
his set of fixes.

## Problem

A shader that includes data/shaders/.../name.fxh fails with "Failed to open": the default include handler looks only for backslash when it splits the directory of the including file.

## Windows behavior

Windows accepts both / and \\ as path separators. Whether the native handler also tries the bare include name is not measured yet (needs a Windows test).

## The fix, in words

In d3dcompiler_include_from_file_open, take the last / or \\ as the directory separator. The author also retries with the include name on its own when the relative path fails; keep that part only if a Windows test confirms it.
