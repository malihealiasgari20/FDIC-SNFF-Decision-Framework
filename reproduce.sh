#!/bin/bash
# Verify and reproduce release 4.17 of the SNFF replication package.
#
# usage: bash reproduce.sh [--quick] [manuscript.tex]
#
#   Full mode (default, about 3.5 hours on one core): reruns every analysis script that does not need
#   daily prices and requires every output to equal the released results.
#   --quick (under a minute): skips the two long runs (final_analysis.py and weight_sensitivity.py) and starts
#   from the released results; it still rebuilds the acquisition-event inputs, reruns Model 2 in all 50
#   partitions (cluster_influence_check.py, which asserts every released Model 2 AUC), reruns the comparison of
#   included and excluded transactions, regenerates every LaTeX table and the calibration figure, and runs the
#   FDIC-financing check.
#   With the manuscript's .tex file, step 6 also checks its tables and prose numbers.
set -euo pipefail
QUICK=0
if [ "${1:-}" = "--quick" ]; then QUICK=1; shift; fi
HERE=$(cd "$(dirname "$0")" && pwd)
R=$HERE/05_manuscript_analysis_2026-10-29
FW=$HERE/03_revised_framework_2026-10-29
TEX=""
if [ $# -ge 1 ]; then TEX=$(cd "$(dirname "$1")" && pwd)/$(basename "$1"); fi
cd "$HERE"
echo "1. checksums"
sha256sum -c --quiet MANIFEST.sha256 && echo "   every file matches MANIFEST.sha256"
WORK=$(mktemp -d)
cd "$WORK"
echo "1b. acquisition-event inputs: rebuilt from the call reports and compared with the released files"
python3 -I -B "$FW/code/build_event_inputs.py" "$HERE" "$WORK/event_inputs" > /dev/null
for f in SNFF_Event_Inputs_Primary51.csv SNFF_Event_Consolidations.csv Event_Inputs_Report.txt; do
  cmp -s "$FW/data/$f" "$WORK/event_inputs/$f" || { echo "   $f differs"; exit 1; }
done
echo "   identical"
if [ "$QUICK" -eq 1 ]; then
  echo "2. quick mode: released results as the starting point; Model 2 rerun in all 50 partitions and the included vs"
  echo "   excluded comparison rerun (seconds); output in $WORK/results"
  cp -a "$R/results" "$WORK/results"
  rm -f "$WORK/results/table_fbop_influence_model2.csv" "$WORK/results"/selection_*.csv "$WORK/results"/table_selection_*.csv
  python3 -I -B "$R/code/cluster_influence_check.py" "$HERE" "$WORK/results" > /dev/null
  python3 -I -B "$R/code/selection_comparison.py" "$HERE" "$WORK/results" > "$WORK/selection_comparison_log.txt"
else
  echo "2. final analysis (about 2 hours), sensitivity to the expert constants (about 1.5 hours) and included vs excluded"
  echo "   transactions (seconds); output in $WORK/results"
  python3 -I -B "$R/code/final_analysis.py" "$HERE" "$WORK/results" > "$WORK/run_log.txt"
  python3 -I -B "$R/code/cluster_influence_check.py" "$HERE" "$WORK/results" > /dev/null
  python3 -I -B "$R/code/weight_sensitivity.py" "$HERE" "$WORK/results" > "$WORK/weight_sensitivity_log.txt"
  python3 -I -B "$R/code/selection_comparison.py" "$HERE" "$WORK/results" > "$WORK/selection_comparison_log.txt"
fi
echo "3. comparison with the released results"
python3 -I -B "$R/code/compare_clean_rerun.py" "$R/results" "$WORK/results" "$WORK/comparison.txt" \
  && echo "   every output reproduces" || { echo "   differences: see $WORK/comparison.txt"; exit 1; }
echo "4. LaTeX tables and the calibration figure"
python3 -I -B "$R/code/make_tex_tables.py" "$WORK/results" "$WORK/tables"
python3 -I -B "$R/code/make_figures.py" "$WORK/results" "$WORK/tables" > /dev/null
diff -r -x '*.png' "$R/tables" "$WORK/tables" > "$WORK/tables_diff.txt" \
  && echo "   tables identical" || { echo "   differences: see $WORK/tables_diff.txt"; exit 1; }
cmp -s "$R/tables/figure_calibration_coprimary.png" "$WORK/tables/figure_calibration_coprimary.png" \
  && echo "   calibration figure identical" || echo "   calibration figure differs in rendering (see README)"
echo "5. FDIC financing of the buyer: winning-bid record against the ledger and the inputs"
python3 -I -B "$FW/code/check_fdic_financing.py" "$HERE" "$WORK/financing_check.txt" > /dev/null \
  && echo "   all checks pass" || { echo "   failures: see $WORK/financing_check.txt"; exit 1; }
if [ -n "$TEX" ]; then
  echo "6. manuscript: tables and prose numbers against the results"
  python3 -I -B "$R/code/table_check.py" "$WORK/tables" "$TEX" "$WORK/table_check.txt" > /dev/null \
    && echo "   every table equals the generated table" || { echo "   differences: see $WORK/table_check.txt"; exit 1; }
  python3 -I -B "$R/code/number_check.py" "$HERE" "$WORK/results" "$TEX" "$WORK/number_check.txt" > /dev/null \
    && echo "   every checked number matches" || { echo "   mismatches: see $WORK/number_check.txt"; exit 1; }
fi
if [ "$QUICK" -eq 1 ]; then
  echo "Quick verification passed. The cross-validated models were not refitted; run without --quick for that."
else
  echo "Full reproduction passed."
fi
