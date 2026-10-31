"""Compare the results of the final run with a rerun from a fresh copy of the research folder.

Every output file must be byte-identical, except RUN_MANIFEST.json, whose fields must be equal
apart from the runtime.

usage: python3 -I compare_clean_rerun.py <results_dir> <rerun_results_dir> <out_txt>
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

A, B, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
fa, fb = sorted(p.name for p in A.iterdir()), sorted(p.name for p in B.iterdir())
lines, bad = [], 0
if fa != fb:
    bad += 1
    lines.append(f"FILE LISTS DIFFER: only in final run {sorted(set(fa) - set(fb))}; only in rerun {sorted(set(fb) - set(fa))}")
for name in sorted(set(fa) & set(fb)):
    if name == "RUN_MANIFEST.json":
        ma, mb = json.loads((A / name).read_text()), json.loads((B / name).read_text())
        ra, rb = ma.pop("runtime_seconds"), mb.pop("runtime_seconds")
        same = ma == mb
        lines.append(f"{'same     ' if same else 'DIFFERENT'} {name} (all fields except runtime: {ra} s vs {rb} s)")
    else:
        ha, hb = (hashlib.sha256((d / name).read_bytes()).hexdigest() for d in (A, B))
        same = ha == hb
        lines.append(f"{'identical' if same else 'DIFFERENT'} {name}  sha256 {ha[:16]}")
    bad += not same
summary = (f"All {len(fa)} result files reproduce exactly (RUN_MANIFEST.json equal except runtime)." if bad == 0
           else f"{bad} difference(s) found.")
OUT.write_text("Clean rerun comparison: results/ of the final run against the results of final_analysis.py run again\n"
               "from a fresh copy of the research folder (same code, same inputs)\n\n" + "\n".join(lines) + f"\n\n{summary}\n")
print(summary)
sys.exit(1 if bad else 0)
