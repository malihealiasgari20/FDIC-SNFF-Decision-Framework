#!/bin/bash
# Verify and reproduce release 4.0 of the SNFF replication package.
# usage: bash reproduce.sh
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
R=$HERE/05_manuscript_analysis_2026-10-29
cd "$HERE"
echo "1. checksums"
sha256sum -c --quiet MANIFEST.sha256 && echo "   every file matches MANIFEST.sha256"
WORK=$(mktemp -d)
cd "$WORK"
echo "2. final analysis (about 77 minutes); output in $WORK/results"
python3 -I -B "$R/code/final_analysis.py" "$HERE" "$WORK/results" > "$WORK/run_log.txt"
python3 -I -B "$R/code/cluster_influence_check.py" "$HERE" "$WORK/results" > /dev/null
echo "3. comparison with the released results"
python3 -I -B "$R/code/compare_clean_rerun.py" "$R/results" "$WORK/results" "$WORK/comparison.txt" \
  && echo "   every output reproduces" || { echo "   differences: see $WORK/comparison.txt"; exit 1; }
echo "4. LaTeX tables"
python3 -I -B "$R/code/make_tex_tables.py" "$WORK/results" "$WORK/tables"
diff -r "$R/tables" "$WORK/tables" > "$WORK/tables_diff.txt" \
  && echo "   tables identical" || { echo "   differences: see $WORK/tables_diff.txt"; exit 1; }
