# Source and license notices

The wrapper and tests are Copyright (c) 2026, unxed, under BSD-3-Clause.
See `licenses/dllmgr.txt`.

The statically linked implementation uses exact official source revisions:

| Component | Release | Commit | Source |
| --- | --- | --- | --- |
| libavif | v1.4.2 | `c5240fc79fe5c2407e10afd35f5505ef6333ea49` | https://github.com/AOMediaCodec/libavif |
| libaom | v3.14.1 | `03087864cf4bea6abb0d28f95cf7843511413d8f` | https://aomedia.googlesource.com/aom |

The primary libraries use BSD-2-Clause; retain their complete license notices
and the AOM patent-license text (`licenses/aom-PATENTS.txt`). AOM also contains
third-party source with separate notices. Installation copies all bundled
third-party LICENSE/PATENTS/COPYING files into `licenses/aom/third_party/`,
preserving their paths, including the libyuv notice. The packaged notice set is
intentionally broader than the production decoder's linked components.

The production DLL does not include an encoder. A separate, unshipped fixture
encoder is built from these same revisions solely for the synthetic CI test.
The workflow's source-revisions.txt records the wrapper SHA, and SHA256SUMS.txt
records the actual artifact files.
