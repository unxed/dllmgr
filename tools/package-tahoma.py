#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,zipfile
import argparse
parser=argparse.ArgumentParser(description="Package the corrected Wine Tahoma Bold and corresponding source")
parser.add_argument('wine_source',type=Path)
parser.add_argument('font',type=Path)
parser.add_argument('output',type=Path)
args=parser.parse_args()
repo=Path(__file__).resolve().parents[1];wine=args.wine_source; font=args.font
assert hashlib.sha256((wine/'fonts/tahomabd.ttf').read_bytes()).hexdigest()=='508a2acc88cd6abdd399ae79c9965db43fba75a46bb115117b55d2be2272d889'
assert hashlib.sha256((wine/'fonts/tahomabd.sfd').read_bytes()).hexdigest()=='90e42b98fc092034e6485a7f8f811195ca2ca148b6704e5d2df56a4c97dfca49'
notice='''Corrected Wine Tahoma Bold, candidate .009, 2026-11-07.
Original font: (C) 2004 Larry Snyder, based on Bitstream Vera Sans,
(C) 2003 Bitstream, Inc. Modified by unxed with AI assistance, 2026.
Font-derived material: LGPL-2.1-or-later. Complete license follows below.
Original notices and embedded copyright/name records are retained.

This package includes the original Wine font sources and modification scripts.
Wine source: https://github.com/wine-mirror/wine
Exact original revision: db11d0fe6a169c457e23d007e20404643d067aa8
See source/README.md for tools and reproduction. No system Wine file is replaced.

'''
files={'tahomabd.ttf':font.read_bytes(),'THIRD-PARTY-NOTICES.txt':notice.encode()+(repo/'experiments/tahoma-bold/COPYING.LIB').read_bytes(),
       'source/wine/fonts/tahomabd.ttf':(wine/'fonts/tahomabd.ttf').read_bytes(),
       'source/wine/fonts/tahomabd.sfd':(wine/'fonts/tahomabd.sfd').read_bytes(),
       'source/COPYING.LIB':(repo/'experiments/tahoma-bold/COPYING.LIB').read_bytes()}
for name in ['build_clean.py','build_candidate.py','prepare-directions.py','cleanup.py','cleanup-counter-safe.py','validate_counters.py','affected.json']:
 files['source/'+name]=(repo/'experiments/tahoma-bold/freetype'/name).read_bytes()
files['source/README.md']=b'''Build with Python 3 fontTools/freetype-py, FontForge 20230101 and ttfautohint 1.8.4.
Run in this directory:
python3 build_clean.py wine OUTPUT --component-safe
Use --ttfautohint PATH if the executable is outside PATH.
The command writes an experimental .009 font to OUTPUT. It does not install it.
Original input TTF SHA256: 508a2acc88cd6abdd399ae79c9965db43fba75a46bb115117b55d2be2272d889.
Tool versions/timestamps can affect binary identity; no bit-identical rebuild claim.
All advances and unrelated outlines are preserved. Whole-font hinting may change
raster metrics. Final choice still depends on visual checks at the actual DPI.
For results and previous failed candidates, see unxed/dllmgr experiments/tahoma-bold.
'''
files['SHA256SUMS.txt']=''.join(hashlib.sha256(data).hexdigest()+'  '+name+'\n' for name,data in sorted(files.items())).encode()
out=args.output;out.parent.mkdir(exist_ok=True,parents=True)
with zipfile.ZipFile(out,'w') as z:
 for name,data in sorted(files.items()):
  info=zipfile.ZipInfo(name,date_time=(2026,11,7,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,data)
print(hashlib.sha256(out.read_bytes()).hexdigest(),out.name)
