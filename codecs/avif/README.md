# dllmgr AVIF WIC decoder (experimental)

A native x86 WIC COM decoder for AVIF still-image display. The DLL has no
registration exports or process-start side effects. dllmgr owns reversible
registration; the CI probe can temporarily register its own two HKCU subtrees.

- Decoder CLSID: `{13B0A525-1176-4B40-8134-D72A67B16BE8}` (permanent).
- Vendor: `{E2491A3D-B71A-4C4D-85D1-C8DAFB6AF011}`.
- Container: WIC HEIF `{E1E62521-6787-405B-A339-500715B5763F}`.
- DLL: `dllmgr-avif.dll`; `InprocServer32` uses its absolute path and `Both`.
- Category: `CATID_WICBitmapDecoders`, instance key named by the decoder CLSID.
- Pixel format: `GUID_WICPixelFormat32bppBGRA` (straight alpha).
- Two patterns: offset 4, length 8, bytes `ftypavif` and `ftypavis`, masks all
  `ff`, EndOfStream=0. Position is a registry QWORD; Length is a DWORD.
- MIME `image/avif`, extension `.avif`. SupportAnimation=0,
  SupportMultiframe=0, SupportChromakey=0, SupportLossless=1.

Only files with an `avif` or `avis` major brand are claimed. A generic `ftyp`
pattern would wrongly intercept other HEIF/ISO-BMFF files. Compatible-brand-only
AVIF files with another major brand are deliberately outside this first version.

The first image is exposed as one WIC frame, including for an AVIF sequence.
No animation/timing API is provided. Input must be seekable; Initialize seeks to
zero because WIC's signature matcher can leave the stream partway through the
header. Input is limited to 128 MiB, dimensions to 16384, image area to 64 Mi
pixels and parsed image count to 1024. libaom uses at most two decode threads.

Supported output is eight-bit sRGB BGRA with straight alpha, nominal 96 DPI.
SDR source depths are reduced to eight bits by libavif. CICP primaries must be
BT.709 or unspecified; transfer must be sRGB or unspecified. Unspecified values
are assumed sRGB. Matrix/range conversion is performed by libavif, including
full-range BT.601 matrix used by the reported FastStone sample.

ICC and Exif metadata are explicitly rejected, as are clean-aperture metadata,
nonzero rotations, mirroring, non-square sample aspect ratios and unsupported
CICP primaries/transfers (including HDR). These currently return
`WINCODEC_ERR_UNSUPPORTEDOPERATION`. This intentionally conservative restriction
avoids silently displaying incorrect colors or Exif orientation. XMP is not
exposed; thumbnails and metadata-query readers are not implemented. A returned
WIC color context identifies the supported output as sRGB. No visual-quality
or complete AVIF-conformance claim follows from CI passing.

## Build and test

The `avif-codec.yml` workflow uses Windows Server 2022, the installed MSVC x86
compiler, Ninja and static `/MT` dependencies. It triggers only for
`codec/faststone-avif*` branches or manually. It fetches the exact official
source commits in `NOTICE.md`; CMake checks HEAD and does not fetch dependencies
at configuration time. No package/binary from a third-party codec project is
used. A generic AOM CPU target avoids requiring AVX/AVX2 in the decoder.

The first build tree contains an encoder only to generate tiny deterministic
AVIF test images. The separate production build disables the AOM encoder and
builds the decoder DLL plus a standalone WIC test program. The artifact includes
both binaries, fixtures, dependency notices and source revision/hash evidence.

For a read-only probe of the already installed codec:

```
avif-codec.exe --file C:\images\sample.avif
```

For CI / a disposable Windows test account only:

```
avif-codec.exe --self-test C:\build\dllmgr-avif.dll C:\build\fixtures
```

The self-test refuses existing registrations under this CLSID; it creates and
then deletes only its decoder CLSID and its category instance subtrees in HKCU.
It does not change another codec's registration. It checks lossless RGBA pixels,
alpha premultiplication through the system WIC FormatConverter, source lifetime,
rectangle/stride/buffer bounds, malformed/truncated/foreign-brand input,
unsupported ICC/rotation, generic WIC discovery and discovery after rollback.
Empty shared parent registry keys may remain. It does not use or modify a Wine
prefix automatically. Read-only `--file` never registers or unregisters anything.

CI proves the standalone COM/WIC behavior on Windows. Wine 11 and the actual
FastStone image/panel require separate local checks before calling this a fix.
