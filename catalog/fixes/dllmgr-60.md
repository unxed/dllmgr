---
id: dllmgr-60
kind: fix
bug: https://github.com/unxed/dllmgr/issues/60
title: "vkd3d-shader: HLSL CalculateLevelOfDetail and CalculateLevelOfDetailUnclamped are not implemented"
dlls: [vkd3d]
wine: [wine-11.21]
patch: https://raw.githubusercontent.com/Max-RM/wine/2bf1881262ef7ab7452deff0a2427a25e477e589/patches/vkd3d-calculate-lod.patch
patch_sha256: df7af5a7b7281b66bbca8de7e7d6a578963b62049e4a886e44817d960c93639a
evidence: https://github.com/unxed/fix-it-in-wine/issues/15
authors: [Max-RM]
license: LGPL-2.1-or-later
---

# dllmgr-60

External fix by Max-RM (Wine 11.21 on an ARM32/armhf host, Windows ARM32
games; https://github.com/Max-RM/wine/commit/2bf1881262ef7ab7452deff0a2427a25e477e589). Not measured by dllmgr
yet; the author reports Minecraft PE 0.10.4.40 and Bedrock 1.2.8 running with
his set of fixes.

## Problem

Shaders that call Texture.CalculateLevelOfDetail or CalculateLevelOfDetailUnclamped fail to compile in the vkd3d HLSL frontend.

## Windows behavior

The methods return the LOD the sampler would use (clamped to the mip range, or unclamped).

## The fix, in words

Add both methods to the HLSL frontend and lower them to a texture LOD query; the author maps them to the GLSL backend with clamping. vkd3d is a separate upstream project; a SPIR-V lowering would be needed there as well.
