/* SPDX-License-Identifier: BSD-3-Clause */
#ifndef DLLMGR_AVIF_IDS_H
#define DLLMGR_AVIF_IDS_H
#include <guiddef.h>
/* These identifiers are permanent and belong only to this decoder. */
DEFINE_GUID(CLSID_DllmgrAvifDecoder,0x13b0a525,0x1176,0x4b40,0x81,0x34,0xd7,0x2a,0x67,0xb1,0x6b,0xe8);
DEFINE_GUID(GUID_DllmgrAvifVendor,0xe2491a3d,0xb71a,0x4c4d,0x85,0xd1,0xc8,0xda,0xfb,0x6a,0xf0,0x11);
/* Public WIC HEIF container identifier; AVIF is an HEIF specialization. */
DEFINE_GUID(GUID_DllmgrAvifContainer,0xe1e62521,0x6787,0x405b,0xa3,0x39,0x50,0x07,0x15,0xb5,0x76,0x3f);
#define DLLMGR_AVIF_CLSID L"{13B0A525-1176-4B40-8134-D72A67B16BE8}"
#define DLLMGR_AVIF_VENDOR L"{E2491A3D-B71A-4C4D-85D1-C8DAFB6AF011}"
#define DLLMGR_AVIF_CONTAINER L"{E1E62521-6787-405B-A339-500715B5763F}"
#define DLLMGR_AVIF_CATEGORY L"{7ED96837-96F0-4812-B211-F13C24117ED3}"
#define DLLMGR_AVIF_BGRA L"{6FDDC324-4E03-4BFE-B185-3D77768DC90F}"
#endif
