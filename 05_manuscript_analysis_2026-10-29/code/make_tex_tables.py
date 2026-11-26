"""Write the LaTeX tables of the revised manuscript from the final-analysis outputs.

usage: python3 -I make_tex_tables.py <results_dir> <out_dir>
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

R, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
SNFF = "SNFF + LR (Model 3)"
LR = "Logistic regression (L2, C=1)"
LABEL = {LR: "L2 logistic, $C=1$ (Model~2)", "LASSO logistic": "LASSO logistic", "Ridge logistic": "L2 logistic, $C$ tuned (ridge)",
         "Decision tree": "Decision tree", "Random forest": "Random forest", "XGBoost": "XGBoost",
         "LR + pairwise interactions": "LR + pairwise interactions", SNFF: "Spider + LR (Model~3)",
         "Spider score alone (Model 1)": "Spider score alone (Model~1)"}


def f3(x):
    return f"{x:.3f}".replace("-", "$-$") if x < 0 else f"{x:.3f}"


def sgn(x):
    s = f"{x:+.3f}"
    return s.replace("-", "$-$").replace("+", "$+$")


def rng(a, b):
    return f"[{f3(a)}, {f3(b)}]"


numbers = {}
# ------------------------------------------------------------ the two co-primary benchmarks (release 4.5)
# From release 4.5 every model-comparison table reports the S&P 500 (SPY) outcome in Panel A and the bank-sector
# outcome in Panel B (Table 2: Panels A-D); the bank-sector benchmark was a robustness check in the submitted paper.
SPYH, BANKH = "S\\&P~500 benchmark", "bank-sector benchmark"
POS = {"y": 35, "y_bank": 39}
MAIN_ORDER = [LR, "LASSO logistic", "Ridge logistic", "Decision tree", "Random forest", "XGBoost", "LR + pairwise interactions", SNFF,
              "Spider score alone (Model 1)"]


def main_rows(table_csv, tag):
    m_ = pd.read_csv(R / table_csv).set_index("model")
    out = []
    for k in MAIN_ORDER:
        r = m_.loc[k]
        brier = f"{f3(r.Brier_mean)} {rng(r.Brier_p05, r.Brier_p95)}" if pd.notna(r.Brier_mean) else "---"
        skill = f"{100 * r.Brier_skill_mean:.1f}\\%".replace("-", "$-$") if pd.notna(r.Brier_skill_mean) else "---"
        out.append(f"{LABEL[k]} & {f3(r.AUC_mean)} {rng(r.AUC_p05, r.AUC_p95)} & {f3(r.AUC_event_mean)} & {brier} & {skill} \\\\")
        numbers[f"{tag}main::{k}"] = {"AUC": round(r.AUC_mean, 3), "AUC_p05": round(r.AUC_p05, 3), "AUC_p95": round(r.AUC_p95, 3),
                                      "AUC_event": round(r.AUC_event_mean, 3), "Brier": None if pd.isna(r.Brier_mean) else round(r.Brier_mean, 3),
                                      "Brier_skill_pct": None if pd.isna(r.Brier_skill_mean) else round(100 * r.Brier_skill_mean, 1)}
    return out


rows_s, rows_b = main_rows("table_main_comparison.csv", ""), main_rows("table_bank_main_comparison.csv", "bank_")
prev = pd.read_csv(R / "main_by_repeat.csv").Brier_prevalence.mean()
prev_b = pd.read_csv(R / "bank_main_by_repeat.csv").Brier_prevalence.mean()
numbers["prevalence_brier"], numbers["bank_prevalence_brier"] = round(prev, 3), round(prev_b, 3)
(OUT / "tab_main.tex").write_text(r"""\begin{table*}[!t]
\caption{Model Comparison under the S\&P~500 and Bank-Sector Benchmarks: 50 Repeats of Grouped 5-Fold Cross-Validation ($n=55$, 51 Event Clusters)}
\label{tab:main_results}
\centering
\footnotesize
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lcccc}
\toprule
\textbf{Model} & \textbf{AUC [5th, 95th pct.]} & \textbf{Event-weighted AUC} & \textbf{Brier [5th, 95th pct.]} & \textbf{Brier skill} \\
\midrule
\multicolumn{5}{l}{\textit{A. """ + SPYH + f" ({POS['y']} of 55 transactions with a positive CAR)" + r"""}} \\
""" + "\n".join(rows_s[:-1]) + "\n\\midrule\n" + rows_s[-1] + r"""
\midrule
\multicolumn{5}{l}{\textit{B. Bank-sector benchmark (""" + f"{POS['y_bank']} of 55 positive" + r""")}} \\
""" + "\n".join(rows_b[:-1]) + "\n\\midrule\n" + rows_b[-1] + r"""
\bottomrule
\multicolumn{5}{p{0.96\textwidth}}{\scriptsize Means over the 50 repeats of the pooled out-of-fold AUC and Brier score;
brackets give the 5th and 95th percentiles across repeats (partition sensitivity, not a confidence interval).
Model~2 and the ridge comparator are the same L2-penalized logistic regression on the eight inputs; Model~2 fixes
$C=1$, the ridge comparator chooses $C$ by inner cross-validation. Event-weighted AUC collapses transactions that
share a CAR into one observation. Brier skill is the improvement over predicting the training-fold share of
positive-CAR transactions (Brier """ + f"{prev:.3f}" + r""" in Panel~A and """ + f"{prev_b:.3f}" + r""" in Panel~B). The Spider score is not a probability,
so only its ranking is evaluated; its normalization bounds and thresholds are fitted inside each training fold, and
Table~\ref{tab:components} gives its descriptive AUC with bounds fitted once on the full panel. Panel~B uses the bank-sector labels, with partitions stratified on them and the seeds of
Panel~A; the bank-sector specification was a robustness check in the submitted version.}\\
\end{tabular*}
\end{table*}
""")

# ------------------------------------------------------------ paired comparison + bootstrap + permutation
PAIRS = [(LR, "Model~2 ($C=1$)"), ("Ridge logistic", "Ridge ($C$ tuned)"), ("LR + pairwise interactions", "LR + pairwise"),
         ("Random forest", "Random forest"), ("XGBoost", "XGBoost")]


def paired_rows(pd_csv, boot_csv, refit_csv, tag):
    pdiff = pd.read_csv(R / pd_csv)
    boot = pd.read_csv(R / boot_csv).set_index("quantity")
    rfb = pd.read_csv(R / refit_csv).set_index("quantity")
    out = []
    for other, lab in PAIRS:
        a = pdiff[(pdiff.comparison == f"SNFF minus {other}") & (pdiff.metric == "AUC")].iloc[0]
        b = pdiff[(pdiff.comparison == f"SNFF minus {other}") & (pdiff.metric == "Brier")].iloc[0]
        key = f"AUC difference SNFF minus {other}"
        bt = f"{sgn(boot.loc[key, 'estimate'])} [{sgn(boot.loc[key, 'ci_low'])}, {sgn(boot.loc[key, 'ci_high'])}]" if key in boot.index else "---"
        rk = f"diff SNFF minus {other}"
        rt = f"[{sgn(rfb.loc[rk, 'ci_low'])}, {sgn(rfb.loc[rk, 'ci_high'])}]" if rk in rfb.index else "---"
        out.append(f"M3 $-$ {lab} & {sgn(a['mean'])} [{sgn(a.p05)}, {sgn(a.p95)}] & {100 * a.share_SNFF_better:.0f}\\% & "
                   f"{sgn(b['mean'])} [{sgn(b.p05)}, {sgn(b.p95)}] & {bt} & {rt} \\\\")
        numbers[f"{tag}paired::{other}"] = {"AUC_diff": round(a["mean"], 3), "p05": round(a.p05, 3), "p95": round(a.p95, 3),
                                            "share_better_pct": round(100 * a.share_SNFF_better), "Brier_diff": round(b["mean"], 3),
                                            "boot": None if key not in boot.index else [round(boot.loc[key, x], 3) for x in ("estimate", "ci_low", "ci_high")],
                                            "boot_refit": None if rk not in rfb.index else [round(rfb.loc[rk, x], 3) for x in ("mean", "ci_low", "ci_high")]}
    return out, int(rfb.replicates.iloc[0])


rows_s, nref = paired_rows("table_paired_differences.csv", "table_cluster_bootstrap.csv", "table_bootstrap_refit.csv", "")
rows_b, nref_b = paired_rows("table_bank_paired_differences.csv", "table_bank_cluster_bootstrap.csv", "table_bank_bootstrap_refit.csv", "bank_")
(OUT / "tab_paired.tex").write_text(r"""\begin{table*}[!t]
\caption{Paired Comparison of Model~3 with Selected Baselines (Same Partitions, 50 Repeats)}
\label{tab:paired}
\centering
\footnotesize
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lccccc}
\toprule
 & \multicolumn{3}{c}{\textbf{50 partitions}} & \multicolumn{2}{c}{\textbf{Cluster bootstrap, AUC diff. [95\% interval]}} \\
\cmidrule(lr){2-4}\cmidrule(lr){5-6}
\textbf{Comparison} & \textbf{AUC diff. [5th, 95th pct.]} & \textbf{M3 higher} & \textbf{Brier diff. [5th, 95th pct.]} & \textbf{Conditional} & \textbf{Refitting} \\
\midrule
\multicolumn{6}{l}{\textit{A. """ + SPYH + r"""}} \\
""" + "\n".join(rows_s) + r"""
\midrule
\multicolumn{6}{l}{\textit{B. Bank-sector benchmark}} \\
""" + "\n".join(rows_b) + r"""
\bottomrule
\multicolumn{6}{p{0.96\textwidth}}{\scriptsize Differences are Model~3 minus the comparator on the same partitions; a negative Brier
difference favors Model~3. M3 higher: share of the 50 repeats in which Model~3's AUC is higher. Both bootstraps resample the 51 event
clusters. The conditional bootstrap (4,000 draws) uses each transaction's out-of-fold prediction averaged over the 50 repeats and
is conditional on those fitted predictions; the refitting bootstrap (""" + f"{nref}" + r""" draws in Panel~A, """ + f"{nref_b}" + r""" in Panel~B) reruns the
whole nested cross-validation, including tuning, on every resample. Panel~B: bank-sector labels, with the same cluster draws and
partition seeds.}\\
\end{tabular*}
\end{table*}
""")

perm = pd.read_csv(R / "table_permutation_test.csv")
pcp = pd.read_csv(R / "table_permutation_coprimary.csv")
nb_null = pd.read_csv(R / "bank_permutation_null.csv")
plab = {LR: "Model~2 ($C=1$)", "Ridge logistic": "Ridge ($C$ tuned)", SNFF: "Model~3 ($C$ tuned)", "Spider score alone (Model 1)": "Spider score (Model~1)"}
mf = json.loads((R / "RUN_MANIFEST.json").read_text())
rows_s, rows_b = [], []
for r in perm.itertuples():
    holm = "---" if pd.isna(r.p_holm_one_sided) else f"{r.p_holm_one_sided:.2f}"
    rows_s.append(f"{plab[r.model]} & {f3(r.observed_mean_AUC)} & {f3(r.null_mean)} & {f3(r.null_p95)} & {r.p_value_one_sided:.2f} & {holm} & {r.p_value_two_sided:.2f} \\\\")
    numbers[f"perm::{r.model}"] = {"observed": round(r.observed_mean_AUC, 3), "null_mean": round(r.null_mean, 3), "null_p95": round(r.null_p95, 3),
                                   "p_one": round(r.p_value_one_sided, 3), "p_holm": None if pd.isna(r.p_holm_one_sided) else round(r.p_holm_one_sided, 3),
                                   "p_two": round(r.p_value_two_sided, 3)}
for r in pcp[pcp.benchmark == "bank-sector index"].itertuples():
    if r.model not in plab:
        continue
    holm = "---" if pd.isna(r.p_holm_one_sided_upper) else f"{r.p_holm_one_sided_upper:.2f}"
    p95 = nb_null[r.model].quantile(0.95)
    rows_b.append(f"{plab[r.model]} & {f3(r.observed_mean_AUC)} & {f3(r.null_mean)} & {f3(p95)} & {r.p_one_sided_upper:.2f} & {holm} & {r.p_two_sided:.2f} \\\\")
for r in pcp.itertuples():
    numbers[f"perm_coprimary::{r.benchmark}::{r.model}"] = {k: (None if pd.isna(getattr(r, k)) else round(float(getattr(r, k)), 3))
                                                           for k in ("observed_mean_AUC", "null_mean", "null_p025", "null_p975", "p_one_sided_upper",
                                                                     "p_holm_one_sided_upper", "p_two_sided", "p_holm_two_sided")}
(OUT / "tab_perm.tex").write_text(r"""\begin{table}[!t]
\caption{Permutation Tests: Does Discrimination Differ from Chance under Either Benchmark?}
\label{tab:perm}
\centering
\footnotesize
\setlength{\tabcolsep}{2.5pt}
\begin{tabular}{lcccccc}
\toprule
 & & \multicolumn{2}{c}{\textbf{Null AUC}} & \multicolumn{3}{c}{\textbf{$p$-value}} \\
\cmidrule(lr){3-4}\cmidrule(lr){5-7}
\textbf{Model} & \textbf{AUC} & \textbf{Mean} & \textbf{95th} & \textbf{1-sided} & \textbf{Holm} & \textbf{2-sided} \\
\midrule
\multicolumn{7}{l}{\textit{A. """ + SPYH + r"""}} \\
""" + "\n".join(rows_s) + r"""
\midrule
\multicolumn{7}{l}{\textit{B. Bank-sector benchmark}} \\
""" + "\n".join(rows_b) + r"""
\bottomrule
\multicolumn{7}{p{0.94\columnwidth}}{\scriptsize Outcomes permuted across the 51 event clusters (""" + f"{mf['permutations']}" + r""" permutations). On every
permutation the complete nested procedure, including the inner tuning of $C$, is rerun; AUC is the mean over """ + {2: "two", 3: "three", 4: "four", 5: "five"}.get(mf['permutation_repeats'], str(mf['permutation_repeats'])) + r"""
partitions, with the same partition seeds for the observed data. One-sided: AUC above the null; Holm: one-sided
$p$ adjusted for the three models tested; two-sided: distance from 0.5. Panel~B repeats the test with the bank-sector labels
(same partition seeds and permutation draws).}\\
\end{tabular}
\end{table}
""")

# ------------------------------------------------------------ ablation
ABL = ["A: measured inputs", "B: A + Spider score", "C: A + interaction rules", "D: full SNFF (Model 3)", "E: D without protection inputs", "F: D without buyer capital"]


def abl_rows(csv, tag):
    ab = pd.read_csv(R / csv).set_index("model")
    out = []
    for k in ABL:
        r = ab.loc[k]
        lab = k.replace("(Model 3)", "(Model~3)").replace("A +", "A $+$")
        out.append(f"{lab} & {f3(r.AUC_mean)} & {f3(r.AUC_event_mean)} & {f3(r.Brier_mean)} \\\\")
        numbers[f"{tag}ablation::{k}"] = {"AUC": round(r.AUC_mean, 3), "AUC_event": round(r.AUC_event_mean, 3), "Brier": round(r.Brier_mean, 3)}
    return out


rows_s, rows_b = abl_rows("table_ablation.csv", ""), abl_rows("table_bank_ablation.csv", "bank_")
(OUT / "tab_ablation.tex").write_text(r"""\begin{table}[!t]
\caption{Ablation Study: 50 Repeats of Grouped 5-Fold Cross-Validation}
\label{tab:ablation}
\centering
\footnotesize
\setlength{\tabcolsep}{4pt}
\begin{tabular}{lccc}
\toprule
\textbf{Stage} & \textbf{AUC} & \textbf{Event AUC} & \textbf{Brier} \\
\midrule
\multicolumn{4}{l}{\textit{A. """ + SPYH + r"""}} \\
""" + "\n".join(rows_s) + r"""
\midrule
\multicolumn{4}{l}{\textit{B. Bank-sector benchmark}} \\
""" + "\n".join(rows_b) + r"""
\bottomrule
\multicolumn{4}{p{0.94\columnwidth}}{\scriptsize All stages are L2 logistic regressions with the penalty chosen in the inner
cross-validation; stage A is the ridge model of Table~\ref{tab:main_results}. In E and F the Spider score is recomputed
without the removed inputs and the rules that use them. Panel~B: bank-sector labels, with the partitions of
Table~\ref{tab:main_results}, Panel~B.}\\
\end{tabular}
\end{table}
""")

# ------------------------------------------------------------ robustness
rb = pd.read_csv(R / "table_robustness.csv")
rbb = pd.read_csv(R / "table_bank_robustness.csv")
br = pd.read_csv(R / "table_broader90.csv").set_index("model")
brb = pd.read_csv(R / "table_bank_broader90.csv").set_index("model")
evl = pd.read_csv(R / "table_event_level.csv").set_index("model")
evlb = pd.read_csv(R / "table_bank_event_level.csv").set_index("model")
vlab = {"Reaction-day CAR[-1,+1] (primary)": "Main specification (reaction-day window)",
        "Release-date CAR[0,+1]": "Outcome: $CAR_{[0,+1]}$ around announcement date",
        "Release-date CAR[-1,+1] (June window)": "Outcome: $CAR_{[-1,+1]}$ around announcement date",
        "Reaction-day CAR[-1,+1], market model": "Outcome: market-model CAR",
        "Reaction-day CAR[-1,+1], bank-index benchmark": "Main specification (reaction-day window)",
        "Published call-report inputs only": "Published inputs only (no $F$, $H$)", "Broad support definition": "Broad support definition ($H$)",
        "U rule requires support (broad)": "Rule $U$ requires support (broad $H$)", "Z rule removed": "Rule $Z$ removed"}
SPEC = ["Published call-report inputs only", "Broad support definition", "U rule requires support (broad)", "Z rule removed"]


def rrow(lab, x, pos, n, key):
    numbers[key] = {"positives": pos, "LR": round(x.loc[LR, "AUC_mean"], 3), "Ridge": round(x.loc["Ridge logistic", "AUC_mean"], 3),
                    "SNFF": round(x.loc[SNFF, "AUC_mean"], 3), "Score": round(x.loc["Spider score alone (Model 1)", "AUC_mean"], 3)}
    return (f"{lab} & {pos}/{n} & {f3(x.loc[LR, 'AUC_mean'])} & {f3(x.loc['Ridge logistic', 'AUC_mean'])} & {f3(x.loc[SNFF, 'AUC_mean'])} & "
            f"{f3(x.loc['Spider score alone (Model 1)', 'AUC_mean'])} \\\\")


rows = ["\\multicolumn{6}{l}{\\textit{A. " + SPYH + "}} \\\\"]
for v in ["Reaction-day CAR[-1,+1] (primary)", "Release-date CAR[0,+1]", "Release-date CAR[-1,+1] (June window)",
          "Reaction-day CAR[-1,+1], market model"] + SPEC:
    x = rb[rb.variant == v].set_index("model")
    rows.append(rrow(vlab[v], x, int(x.positives.iloc[0]), 55, f"robust::{v}"))
x = rb[rb.variant == "Reaction-day CAR[-1,+1], bank-index benchmark"].set_index("model")
rrow(vlab["Reaction-day CAR[-1,+1], bank-index benchmark"], x, int(x.positives.iloc[0]), 55, "robust::Reaction-day CAR[-1,+1], bank-index benchmark")
fbi = pd.read_csv(R / "table_fbop_influence.csv")


def fbop_row(oc, key):
    x = fbi[(fbi.outcome == oc) & (fbi["sample"] == "without the FBOP cluster")].set_index("model")
    x = x.rename(columns={"AUC_mean": "AUC_mean"})
    return rrow("Without the FBOP cluster", x, POS[oc] - (4 if oc == "y_bank" else 0), 51, key)


rows.append(fbop_row("y", "robust::without FBOP"))
rows.append(rrow("Broader panel (no size cut)", br, 56, 90, "robust::broader"))
rows.append(rrow("Acquisition events (consolidated)", evl, 34, 51, "robust::events"))
numbers["broader"] = {k: round(br.loc[k, "AUC_mean"], 3) for k in br.index}
numbers["broader_brier"] = {k: (None if pd.isna(br.loc[k, "Brier_mean"]) else round(br.loc[k, "Brier_mean"], 3)) for k in br.index}
numbers["events"] = {k: round(evl.loc[k, "AUC_mean"], 3) for k in evl.index}
numbers["events_brier"] = {k: (None if pd.isna(evl.loc[k, "Brier_mean"]) else round(evl.loc[k, "Brier_mean"], 3)) for k in evl.index}
numbers["events_brier_skill"] = {k: (None if pd.isna(evl.loc[k, "Brier_skill_mean"]) else round(evl.loc[k, "Brier_skill_mean"], 3)) for k in evl.index}
rows.insert(len(rows) - 2, "\\midrule")
rows += ["\\midrule", "\\multicolumn{6}{l}{\\textit{B. Bank-sector benchmark}} \\\\"]
xb = rb[rb.variant == "Reaction-day CAR[-1,+1], bank-index benchmark"].set_index("model")
rows.append(rrow(vlab["Reaction-day CAR[-1,+1], bank-index benchmark"], xb, int(xb.positives.iloc[0]), 55, "bank_robust::primary"))
for v in SPEC:
    x = rbb[rbb.variant == v].set_index("model")
    rows.append(rrow(vlab[v], x, int(x.positives.iloc[0]), 55, f"bank_robust::{v}"))
rows.append(fbop_row("y_bank", "bank_robust::without FBOP"))
rows.append("\\midrule")
rvp = pd.read_csv(R / "table_risk_validation.csv")
BKEY = "Reaction-day CAR[-1,+1], bank-index benchmark"
pos90_b = int(rvp[(rvp.outcome == BKEY) & (rvp.deals == "primary 55")].positive.iloc[0]
              + rvp[(rvp.outcome == BKEY) & (rvp.deals == "35 broader-only (rules fitted on the 55)")].positive.iloc[0])
epol_b = pd.read_csv(R / "table_bank_event_level_decision_policies.csv").set_index("policy")
pos51_b = int(round(epol_b.loc["Pursue all", "TP"]))
numbers["bank_positives"] = {"transactions": POS["y_bank"], "broader90": pos90_b, "events51": pos51_b}
rows.append(rrow("Broader panel (no size cut)", brb, pos90_b, 90, "bank_robust::broader"))
rows.append(rrow("Acquisition events (consolidated)", evlb, pos51_b, 51, "bank_robust::events"))
(OUT / "tab_robustness.tex").write_text(r"""\begin{table*}[!t]
\caption{Robustness: Mean AUC over 50 Repeats under Alternative Outcomes, Specifications, and Samples}
\label{tab:robustness}
\centering
\footnotesize
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lccccc}
\toprule
\textbf{Variant} & \textbf{Positive CAR} & \textbf{Model~2} & \textbf{Ridge} & \textbf{Model~3} & \textbf{Spider score} \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\multicolumn{6}{p{0.96\textwidth}}{\scriptsize Variants with the S\&P~500 outcome use the partitions of Table~\ref{tab:main_results},
Panel~A, and those with the bank-sector outcome the partitions of its Panel~B; each alternative outcome in Panel~A uses 50
grouped partitions with the same seeds, stratified on its own labels. Published inputs only: the six call-report inputs, without
the deal terms $F$ and $H$; the Spider score is recomputed without its Protection component and rule~$Q$. Without the FBOP cluster:
the 51 transactions other than the four FBOP subsidiaries, with 50 partitions drawn with the same seeds. The broader panel of 90
transactions (78 event clusters) uses its own 50 grouped partitions. Acquisition events: the 51 events of the primary panel, each
scored on the consolidated inputs of every bank its acquirer bought that day (Section~\ref{sec:events}), with 50 partitions of the
events.}\\
\end{tabular*}
\end{table*}
""")

# ------------------------------------------------------------ decision policies (Panels A-D)
POLS = [("4A: fixed Spider thresholds", "4A: Fixed ($\\tilde S$)", "0.70/0.40"), ("4B: F1-tuned threshold", "4B: F1-tuned", "0.55--0.80"),
        ("4C: cost-based threshold (3:1)", "4C: Cost (3:1)", "0.75/0.45")]
rows = []
for tag, csv, header in (("", "table_decision_policies.csv", "A. Transactions ($n=55$), " + SPYH),
                         ("bank_", "table_bank_decision_policies.csv", "B. Transactions ($n=55$), " + BANKH),
                         ("event", "table_event_level_decision_policies.csv", "C. Acquisition events ($n=51$), " + SPYH),
                         ("bank_event", "table_bank_event_level_decision_policies.csv", "D. Acquisition events ($n=51$), " + BANKH)):
    P_ = pd.read_csv(R / csv).set_index("policy")
    if rows:
        rows.append("\\midrule")
    rows.append("\\multicolumn{7}{l}{\\textit{" + header + "}} \\\\")
    for k, lab, thr in POLS:
        r = P_.loc[k]
        rows.append(f"{lab} & {thr} & {r.pursue:.1f} & {r.TP:.1f}/{r.FP:.1f} & {r.F1:.3f} & {r.FPR:.3f} & {f3(r.utility_3to1)} \\\\")
        numbers[f"{tag}policy::{k}"] = {k2: round(float(r[k2]), 3) for k2 in ("pursue", "caution", "TP", "FP", "F1", "FPR", "utility_3to1")}
    rows.append("\\multicolumn{7}{l}{\\textit{Trivial policies}} \\\\")
    for k in ("Pursue all", "Pursue none"):
        r = P_.loc[k]
        rows.append(f"{k} & --- & {r.pursue:.0f} & {r.TP:.0f}/{r.FP:.0f} & {r.F1:.3f} & {r.FPR:.3f} & {f3(r.utility_3to1)} \\\\")
        numbers[f"{tag}policy::{k}"] = {k2: round(float(r[k2]), 3) for k2 in ("pursue", "TP", "FP", "F1", "FPR", "utility_3to1")}
NEG = {"A": 55 - POS["y"], "B": 55 - POS["y_bank"], "C": 51 - 34, "D": 51 - pos51_b}
(OUT / "tab_model4.tex").write_text(r"""\begin{table}[!t]
\caption{Model~4 Decision Policies (Mean over 50 Repeats; Utility under the Hypothetical Payoffs $B=1$, $L=3$)}
\label{tab:model4}
\centering
\footnotesize
\setlength{\tabcolsep}{2.5pt}
\begin{tabular}{lcccccc}
\toprule
\textbf{Policy} & \textbf{Thresh.} & \textbf{Pursue} & \textbf{TP/FP} & \textbf{F1} & \textbf{FPR} & \textbf{Util.} \\
 & & \textbf{(of $n$)} & & & & \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\multicolumn{7}{p{0.94\columnwidth}}{\scriptsize Pursue (of $n$): mean number of the $n$ transactions (Panels C and D: acquisition events) recommended for pursuit, e.g., """ + f"{pd.read_csv(R / 'table_decision_policies.csv').set_index('policy').loc['4A: fixed Spider thresholds', 'pursue']:.1f}" + r""" of 55 for 4A in Panel~A;
TP/FP: of these, those with a positive and with a negative announcement return; FPR: share of the negative-CAR observations
recommended (""" + f"{NEG['A']}, {NEG['B']}, {NEG['C']}, and {NEG['D']}" + r""" in Panels A to D); Util.: utility under the assumed payoffs, $(TP - 3\,FP)/n$. Panels C and D score each
event on the consolidated inputs of every bank its acquirer bought that day (Section~\ref{sec:events}) and use 50 partitions of the
51 events with the same seeds. Panels B and D use the bank-sector labels.}\\
\end{tabular}
\end{table}
""")


def sweep_rows(csv, tag):
    sw = pd.read_csv(R / csv)
    out = []
    for r in sw.itertuples():
        out.append(f"{int(r.ratio)}:1 & {r.threshold:.2f} & {r.pursue:.1f} & {r.TP:.1f}/{r.FP:.1f} & {r.FPR:.3f} & {r.F1:.3f} & {f3(r.utility_own)} & "
                   f"{f3(r.gain_vs_trivial)} & {f3(r.utility_3to1)} \\\\")
        numbers[f"{tag}sweep::{int(r.ratio)}"] = {k2: round(float(getattr(r, k2)), 3) for k2 in ("threshold", "pursue", "TP", "FP", "FPR", "F1",
                                                                                              "utility_own", "gain_vs_trivial", "utility_3to1")}
    return out


rows_s, rows_b = sweep_rows("table_cost_ratio_sweep.csv", ""), sweep_rows("table_bank_cost_ratio_sweep.csv", "bank_")
(OUT / "tab_sensitivity.tex").write_text(r"""\begin{table}[!t]
\caption{Utility Sensitivity to the Assumed Loss-to-Benefit Ratio (Model~3 Probabilities; Mean over 50 Repeats)}
\label{tab:sensitivity}
\centering
\footnotesize
\setlength{\tabcolsep}{2.2pt}
\begin{tabular}{lcccccccc}
\toprule
 & & & & & & \multicolumn{2}{c}{\textbf{Own ratio}} & \textbf{3:1} \\
\cmidrule(lr){7-8}\cmidrule(lr){9-9}
\textbf{Ratio} & \textbf{Thr.} & \textbf{Pursue} & \textbf{TP/FP} & \textbf{FPR} & \textbf{F1} & \textbf{Util.} & \textbf{Gain} & \textbf{Util.} \\
 & & \textbf{(of 55)} & & & & & & \\
\midrule
\multicolumn{9}{l}{\textit{A. """ + SPYH + r"""}} \\
""" + "\n".join(rows_s) + r"""
\midrule
\multicolumn{9}{l}{\textit{B. Bank-sector benchmark}} \\
""" + "\n".join(rows_b) + r"""
\bottomrule
\multicolumn{9}{p{0.94\columnwidth}}{\scriptsize Threshold $L/(B+L)$ applied to Model~3's out-of-fold probabilities. Gain: utility
minus that of the better trivial policy (pursue all or pursue none) at the same ratio. Each ratio is a hypothetical scenario. Panel~B: bank-sector labels.}\\
\end{tabular}
\end{table}
""")

# ------------------------------------------------------------ Spider components
# Deal sets: the primary panel, the 35 broader-panel transactions outside it, and the 28 of those whose acquirer and
# reaction day (and so whose CAR) are not those of a primary-panel transaction. The tables show the 55 and the 28.
D55, D35, D28 = "primary 55", "35 broader-only (rules fitted on the 55)", "28 broader-only with own event (rules fitted on the 55)"
comp = pd.read_csv(R / "table_spider_components.csv")
comp_b = pd.read_csv(R / "table_bank_spider_components.csv")
clab = {"S_final": "Spider score $\\tilde S$", "V_score": "Value $V$", "P_score": "Protection $P$", "B_score": "Buyer strength $B$",
        "R_score": "Risk $R$", "E_score": "Execution $E$"}
COMPS = ["S_final", "V_score", "P_score", "B_score", "R_score", "E_score"]
rows = ["\\multicolumn{6}{l}{\\textit{A. " + SPYH + "}} \\\\"]
for c in COMPS:
    a, b, e = (comp[(comp.component == c) & (comp.deals == dd)].iloc[0] for dd in (D55, D35, D28))
    rows.append(f"{clab[c]} & ${a.sign_in_S}$ & {f3(a.AUC)} & {a.p_two_sided:.2f} & {f3(e.AUC)} & {e.p_two_sided:.2f} \\\\")
    numbers[f"component::{c}"] = {"AUC55": round(a.AUC, 3), "p55": round(a.p_two_sided, 3), "AUC35": round(b.AUC, 3), "p35": round(b.p_two_sided, 3),
                                  "AUC28": round(e.AUC, 3), "p28": round(e.p_two_sided, 3)}
rows += ["\\midrule", "\\multicolumn{6}{l}{\\textit{B. Bank-sector benchmark}} \\\\"]
for c in COMPS:
    a, e = (comp_b[(comp_b.component == c) & (comp_b.deals == dd)].iloc[0] for dd in (D55, D28))
    rows.append(f"{clab[c]} & ${a.sign_in_S}$ & {f3(a.AUC)} & {a.p_two_sided:.2f} & {f3(e.AUC)} & {e.p_two_sided:.2f} \\\\")
    numbers[f"bank_component::{c}"] = {"AUC55": round(a.AUC, 3), "p55": round(a.p_two_sided, 3), "AUC28": round(e.AUC, 3), "p28": round(e.p_two_sided, 3)}
SC_FULL = (float(comp[(comp.component == "S_final") & (comp.deals == D55)].AUC.iloc[0]),
           float(comp_b[(comp_b.component == "S_final") & (comp_b.deals == D55)].AUC.iloc[0]))
SC_CV = tuple(float(pd.read_csv(R / f).set_index("model").loc["Spider score alone (Model 1)", "AUC_mean"])
              for f in ("table_main_comparison.csv", "table_bank_main_comparison.csv"))
(OUT / "tab_components.tex").write_text(r"""\begin{table}[!t]
\caption{Direction of the Spider Score and Its Components (Descriptive, Full-Panel AUC against a Positive CAR)}
\label{tab:components}
\centering
\footnotesize
\setlength{\tabcolsep}{3pt}
\begin{tabular}{lccccc}
\toprule
 & & \multicolumn{2}{c}{\textbf{Primary panel (55)}} & \multicolumn{2}{c}{\textbf{Other 28 deals}} \\
\cmidrule(lr){3-4}\cmidrule(lr){5-6}
\textbf{Component} & \textbf{Sign in $S$} & \textbf{AUC} & \textbf{$p$} & \textbf{AUC} & \textbf{$p$} \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\multicolumn{6}{p{0.94\columnwidth}}{\scriptsize Normalization bounds and thresholds fitted on the primary panel only; no outcome
is used. The table describes the full panel and is not an out-of-sample evaluation: the Spider score's AUCs here (""" + f"{SC_FULL[0]:.3f}" + r"""
and """ + f"{SC_FULL[1]:.3f}" + r""") use bounds and thresholds fitted once on all 55 transactions, whereas its out-of-sample AUCs in
Table~\ref{tab:main_results} (""" + f"{SC_CV[0]:.3f}" + r""" and """ + f"{SC_CV[1]:.3f}" + r""") use bounds and thresholds fitted inside each training fold of the
repeated grouped cross-validation. The two follow different protocols and do not contradict each other. ``Other 28 deals'' are the 35 broader-panel transactions outside the primary panel, less the seven that share an
acquirer and an announcement return with a primary-panel transaction. AUC above 0.5 means
higher component values go with a positive announcement return (reaction-day window; Panel~A against SPY, Panel~B against the
bank-sector index); $p$ is two-sided, from 10,000 permutations of outcomes across event clusters. Table~\ref{tab:risk} repeats the
Risk row under other benchmarks and windows.}\\
\end{tabular}
\end{table}
""")
thirds = pd.read_csv(R / "table_risk_thirds.csv")
numbers["risk_thirds"] = thirds.round(4).to_dict("records")

# ------------------------------------------------------------ risk component: benchmarks, windows, influence
rv = pd.read_csv(R / "table_risk_validation.csv")
ri = pd.read_csv(R / "table_risk_influence.csv")
RO = [("Reaction-day CAR[-1,+1], SPY (primary)", "SPY, reaction day (co-primary)"),
      ("Reaction-day CAR[-1,+1], bank-index benchmark", "Bank-sector index, reaction day (co-primary)"),
      ("Reaction-day CAR[-1,+1], market model", "Market model, reaction day"),
      ("Release-date CAR[0,+1]", "SPY, $[0,+1]$ around release date"),
      ("Release-date CAR[-1,+1] (June window)", "SPY, $[-1,+1]$ around release date")]
rows_a = []
cr = pd.read_csv(R / "table_spider_components.csv")
cr = cr[cr.component == "R_score"]
for key, lab in RO:
    a55, a35, a28 = (rv[(rv.outcome == key) & (rv.deals == dd)].iloc[0].copy() for dd in (D55, D35, D28))
    if key == RO[0][0]:
        # the primary-outcome row repeats the Risk row of the components table; show that table's p-values
        # (the same statistic, a separate draw of 10,000 permutations) so that the two tables agree
        c55, c35, c28 = (cr[cr.deals == dd].iloc[0] for dd in (D55, D35, D28))
        assert all(abs(c.AUC - a.AUC_R) < 1e-12 for c, a in ((c55, a55), (c35, a35), (c28, a28)))
        a55["p_AUC"], a35["p_AUC"], a28["p_AUC"] = c55.p_two_sided, c35.p_two_sided, c28.p_two_sided
    rows_a.append(f"{lab} & {f3(a55.AUC_R)} ({a55.p_AUC:.2f}) & {f3(a28.AUC_R)} ({a28.p_AUC:.2f}) \\\\")
    numbers[f"risk::{key}"] = {"AUC55": round(a55.AUC_R, 3), "p55": round(a55.p_AUC, 3), "rho55": round(a55.spearman_R_CAR, 3),
                               "p_rho55": round(a55.p_spearman, 3), "AUC35": round(a35.AUC_R, 3), "p35": round(a35.p_AUC, 3),
                               "rho35": round(a35.spearman_R_CAR, 3), "p_rho35": round(a35.p_spearman, 3),
                               "AUC28": round(a28.AUC_R, 3), "p28": round(a28.p_AUC, 3),
                               "rho28": round(a28.spearman_R_CAR, 3), "p_rho28": round(a28.p_spearman, 3)}


def infl(outcome, analysis):
    return ri[(ri.outcome == outcome) & (ri.analysis == analysis)].iloc[0]


SPYK, BANKK = RO[0][0], RO[1][0]
rows_b = [f"All 55 transactions & {f3(rv[(rv.outcome == SPYK) & (rv.deals == D55)].AUC_R.iloc[0])} & "
          f"{f3(rv[(rv.outcome == BANKK) & (rv.deals == D55)].AUC_R.iloc[0])} \\\\",
          f"Leave one event out (range) & {f3(infl(SPYK, 'leave one event cluster out: minimum').AUC_R)}--{f3(infl(SPYK, 'leave one event cluster out: maximum').AUC_R)} & "
          f"{f3(infl(BANKK, 'leave one event cluster out: minimum').AUC_R)}--{f3(infl(BANKK, 'leave one event cluster out: maximum').AUC_R)} \\\\"]
for an, lab in (("without SVB, First Republic and Washington Mutual", "Without SVB, First Republic, WaMu"),
                ("without the five event clusters with the largest absolute CAR", "Without the five largest $|CAR|$ events"),
                ("announced 2008-2010", f"Announced 2008--2010 ($n={int(infl(SPYK, 'announced 2008-2010').n)}$)"),
                ("announced 2011-2024", f"Announced 2011--2024 ($n={int(infl(SPYK, 'announced 2011-2024').n)}$)")):
    rows_b.append(f"{lab} & {f3(infl(SPYK, an).AUC_R)} & {f3(infl(BANKK, an).AUC_R)} \\\\")
for r in ri.itertuples():
    numbers[f"risk_influence::{r.outcome}::{r.analysis}"] = {"n": int(r.n), "AUC": round(r.AUC_R, 3), "rho": round(r.spearman_R_CAR, 3)}
(OUT / "tab_risk.tex").write_text(r"""\begin{table}[!t]
\caption{Sensitivity of the Risk Component's Association with Announcement Returns}
\label{tab:risk}
\centering
\footnotesize
\setlength{\tabcolsep}{3pt}
\begin{tabular}{lcc}
\toprule
\multicolumn{3}{l}{\textit{A. Benchmark and window: AUC (two-sided $p$)}} \\
\textbf{Outcome} & \textbf{Primary 55} & \textbf{Other 28} \\
\midrule
""" + "\n".join(rows_a) + r"""
\midrule
\multicolumn{3}{l}{\textit{B. Influence in the primary panel: AUC}} \\
\textbf{Sample} & \textbf{SPY} & \textbf{Bank index} \\
\midrule
""" + "\n".join(rows_b) + r"""
\bottomrule
\multicolumn{3}{p{0.94\columnwidth}}{\scriptsize AUC of the Risk score $R$ against a positive CAR; $p$ from 10,000 permutations of
outcomes across event clusters. Normalization bounds and thresholds are fitted on the primary panel. Other 28: the transactions
of Table~\ref{tab:components}. The bank-sector index is the
equal-weighted return of 27 U.S.-listed bank holding companies, excluding the acquirer and banks with their own announcement
within four days. Panel B drops, in turn, each of the 51 event clusters, the three largest transactions, and the five event
clusters with the largest absolute CAR under each benchmark, and splits the panel by announcement year.}\\
\end{tabular}
\end{table}
""")

# ------------------------------------------------------------ multi-bank purchases (release 4.3)
mb = pd.read_csv(R / "table_multibank_events.csv")
TITLE = {"CALIFORNIA NATIONAL BANK": "California National Bank", "PARK NATIONAL BANK": "Park National Bank",
         "SAN DIEGO NATIONAL BANK": "San Diego National Bank", "PACIFIC NATIONAL BANK": "Pacific National Bank",
         "NORTH HOUSTON BANK": "North Houston Bank", "MADISONVILLE STATE BANK": "Madisonville State Bank", "BANK USA, NA": "Bank USA",
         "CITIZENS NATIONAL BANK": "Citizens National Bank", "COMMUNITY BANK OF LEMONT": "Community Bank of Lemont",
         "DOWNEY SAVINGS AND LOAN ASSOCIATION, F.A.": "Downey Savings and Loan", "PFF BANK & TRUST": "PFF Bank \\& Trust",
         "WHEATLAND BANK": "Wheatland Bank", "LINCOLN PARK SAVINGS BANK": "Lincoln Park Savings Bank",
         "DARBY BANK & TRUST COMPANY": "Darby Bank \\& Trust", "TIFTON BANKING COMPANY": "Tifton Banking Company"}
EVS = [("USB|2009-11-02", "A. Nine FBOP Corporation subsidiaries, bought by U.S.~Bank on October~30, 2009", "all nine"),
       ("USB|2008-11-24", "B. Downey Savings and Loan and PFF Bank \\& Trust, bought by U.S.~Bank on November~21, 2008", "both banks"),
       ("WTFC|2010-04-26", "C. Wheatland Bank and Lincoln Park Savings Bank, bought by two Wintrust banks on April~23, 2010", "both banks"),
       ("ABCB|2010-11-15", "D. Darby Bank \\& Trust and Tifton Banking Company, bought by Ameris Bank on November~12, 2010", "both banks")]


def sg(x, d=1):
    return ("$-$" if x < 0 else "$+$") + f"{abs(x):.{d}f}"


def flags(r):
    on = [k for k, c in (("L", "L_flag"), ("T", "T_flag"), ("Q", "Q_rule"), ("U", "U_rule"), ("Z", "Z_rule"), ("K", "K_rule")) if int(r[c]) == 1]
    return "$" + ",".join(on) + "$" if on else "---"


def mrow(label, r):
    return (f"{label} & {r.failed_assets_usd_bn:.2f} & {r.G_deposits_usd_bn:.2f} & {r.N_npl_pct:.1f} & {sg(r.L_deposit_change_pct)} & "
            f"{sg(r.T_npl_change_pp)} & {r.E_relative_size:.3f} & {flags(r)} & {f3(r.V_score)} & {f3(r.R_score)} & {f3(r.B_score)} & "
            f"{f3(r.E_score)} & {f3(r.S_final)} & {r.band} \\\\")


rows = []
for e, head, alln in EVS:
    m = mb[mb.event_id == e]
    banks, cons, means = m[m.row == "bank"], m[m.row == "consolidated event"], m[m.row.str.contains("mean")]
    car = float(banks.car_reaction_m1p1.iloc[0])
    if rows:
        rows.append("\\midrule")
    rows.append(f"\\multicolumn{{14}}{{l}}{{\\textit{{{head} (CAR {sg(100 * car)}\\%)}}}} \\\\")
    for _, r in banks.iterrows():
        rows.append(mrow(TITLE[r["name"]] + ("$^{*}$" if r.in_primary_panel == 1 else ""), r))
        numbers[f"multibank::{e}::{r.transaction_id}"] = {"S": round(r.S_final, 3), "band": r.band}
    for scope, lab in (("all banks bought that day", f"Consolidated, {alln}"), ("banks in the primary panel", "Consolidated, four in panel")):
        c = cons[cons.scope == scope]
        if len(c):
            rows.append(mrow(lab, c.iloc[0]))
            numbers[f"multibank::{e}::consolidated::{scope}"] = {"S": round(c.iloc[0].S_final, 3), "band": c.iloc[0].band}
    for scope, lab in (("all banks bought that day", "the nine bank scores" if alln == "all nine" else "the two bank scores"),
                       ("banks in the primary panel", "the scores of the four in panel")):
        s = means[means.scope == scope].set_index("row")
        if len(s):
            a, w = s.loc["mean of the bank scores"], s.loc["asset-weighted mean of the bank scores"]
            rows.append(f"\\multicolumn{{12}}{{l}}{{Mean of {lab}}} & {f3(a.S_final)} & {a.band} \\\\")
            rows.append(f"\\multicolumn{{12}}{{l}}{{Asset-weighted mean of {lab}}} & {f3(w.S_final)} & {w.band} \\\\")
            numbers[f"multibank::{e}::mean::{scope}"] = {"simple": round(a.S_final, 3), "weighted": round(w.S_final, 3),
                                                         "band_simple": a.band, "band_weighted": w.band}
(OUT / "tab_events.tex").write_text(r"""\begin{table*}[!t]
\caption{Scoring Multi-Bank Purchases: Each Bank Alone and the Consolidated Acquisition Event (Full-Panel Spider Parameters)}
\label{tab:events}
\centering
\footnotesize
\setlength{\tabcolsep}{2pt}
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lccccccccccccc}
\toprule
 & \textbf{Assets} & \textbf{Deposits} & \textbf{NPL} & \textbf{Dep.\ chg.} & \textbf{NPL chg.} & \textbf{Rel.} & & & & & & & \\
\textbf{Bank or event} & \textbf{(\$B)} & \textbf{(\$B)} & \textbf{(\%)} & \textbf{(\%)} & \textbf{(pp)} & \textbf{size} & \textbf{Flags} &
$V$ & $R$ & $B$ & $E$ & $\tilde S$ & \textbf{Decision} \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\multicolumn{14}{p{0.96\textwidth}}{\scriptsize $^{*}$In the primary panel; the other banks are below its size cut. Inputs as in
Section~\ref{sec:components}, from each bank's last public call report and the report two quarters earlier. A consolidated event sums
the banks' assets, deposits, net loans, and noncurrent loans at both dates before the inputs are computed
(Section~\ref{sec:leakage}); the acquirer's capital and assets enter once (for the Wintrust event, its two acquiring banks combined).
Rel.\ size: failed-bank assets over acquiring-bank assets. Flags: the indicators $L$, $T$ and the rules $Q$, $U$, $Z$, $K$ that equal 1.
Normalization bounds, quartile thresholds, and rescaling are those of the full 55-transaction panel, as in
Table~\ref{tab:svb_scores}; deposits below the panel's minimum (\$0.29B) give $V = 0$. All 15 banks had loss sharing and no
government support ($P = 0.60$). Decision: the bands of Model~1.}\\
\end{tabular*}
\end{table*}
""")

# ------------------------------------------------------------ SVB case (Table 6): inputs and scores; deposits at three dates
MON = {1: "Jan.", 2: "Feb.", 3: "Mar.", 4: "Apr.", 5: "May", 6: "Jun.", 7: "Jul.", 8: "Aug.", 9: "Sep.", 10: "Oct.", 11: "Nov.", 12: "Dec."}


def dt(s: str) -> str:
    y, mth, d = (int(x) for x in s.split("-"))
    return f"{MON[mth]}~{d}, {y}"


case = json.loads((R / "svb_case.json").read_text())
ci, cs = case["inputs"], case["scores"]
assert all(cs[k] == 0 for k in ("Q_rule", "U_rule", "Z_rule", "K_rule")) and cs["S_adj"] == cs["S_raw"]
rows_a = [f"Deposits ({dt(ci['failed_report_date'])}) & \\${ci['G_deposits_usd_bn']:.1f}B & $G = {cs['G_n']:.3f}$ \\\\",
          f"\\textbf{{Value score}} $V$ & --- & \\textbf{{{cs['V_score']:.3f}}} \\\\[3pt]",
          f"FDIC loss share & {'Yes' if ci['F_loss_share'] else 'No'} & $F = {int(ci['F_loss_share'])}$ \\\\",
          f"Government support & {'Bridge bank' if ci['H_support_narrow'] else 'None'} & $H = {int(ci['H_support_narrow'])}$ \\\\",
          f"\\textbf{{Protection score}} $P$ & --- & \\textbf{{{cs['P_score']:.3f}}} \\\\[3pt]",
          f"NPL ratio & {ci['N_npl_pct']:.2f}\\% & $N = {cs['N_n']:.3f}$ \\\\",
          f"Deposit change, two quarters & ${ci['L_deposit_change_pct']:.1f}\\%$ & $L = {int(cs['L_flag'])}$ \\\\",
          f"NPL change, two quarters & ${ci['T_npl_change_pp']:+.2f}$ pp & $T = {int(cs['T_flag'])}$ \\\\",
          f"\\textbf{{Risk score}} $R$ & --- & \\textbf{{{cs['R_score']:.3f}}} \\\\[3pt]",
          f"Buyer capital ({dt(ci['buyer_report_date_lag90'])}) & {ci['C_buyer_capital_pct']:.2f}\\% & $C = {cs['C_n']:.3f}$ \\\\",
          f"\\textbf{{Buyer strength}} $B$ & --- & \\textbf{{{cs['B_score']:.3f}}} \\\\[3pt]",
          f"Relative size & {ci['E_relative_size']:.2f} & $M = {cs['E_n']:.3f}$ \\\\",
          f"\\textbf{{Execution score}} $E$ & --- & \\textbf{{{cs['E_score']:.3f}}} \\\\"]
stg = pd.read_csv(R / "table_svb_deposit_stages.csv")
stg = stg[stg.variant == "deposits and assets"]
STAGES = ["last call report", "at failure", "assumed by the acquirer"]
ZONE = {"Pursue": "P", "Caution": "C", "Avoid": "A"}


def bn(x: float) -> str:
    """USD billions to the precision of the source: the FDIC gives SVB's figures at failure to the nearest billion."""
    return f"{x:.0f}" if float(x).is_integer() else f"{x:.1f}"


def at(stage, bounds="all 55"):
    return stg[(stg.stage == stage) & (stg.bounds == bounds)].iloc[0]


first = at(STAGES[0])
assert abs(first.S_adj - cs["S_adj"]) < 1e-12 and abs(first.S_final - cs["S_final"]) < 1e-12 and first.deposits_usd_bn == ci["G_deposits_usd_bn"]
dates = " & ".join(dt(at(s).as_of_date) for s in STAGES)
rows_b = [r"\textbf{Deposits at} & \textbf{Call report} & \textbf{Failure}$^{\dagger}$ & \textbf{Sale}$^{\dagger}$ \\",
          f" & {dates} \\\\",
          r"\midrule",
          "Deposits (\\$B) & " + " & ".join(bn(at(s).deposits_usd_bn) for s in STAGES) + r" \\",
          "Value score $V$ & " + " & ".join(f3(at(s).V_score) for s in STAGES) + r" \\",
          "Adjusted score $S^*$ & " + " & ".join(f3(at(s).S_adj) for s in STAGES) + r" \\",
          "Rank of $S^*$ (of 55) & " + " & ".join(str(int(at(s).rank_S_adj_of_55)) for s in STAGES) + r" \\",
          "$\\tilde S$, all 55 & " + " & ".join(f"{f3(at(s).S_final)} ({ZONE[at(s).band]})" for s in STAGES) + r" \\",
          "$\\tilde S$, other 54 & " + " & ".join(f"{f3(at(s, 'other 54').S_final)} ({ZONE[at(s, 'other 54').band]})" for s in STAGES) + r" \\"]
for s in STAGES:
    for bnd in ("all 55", "other 54"):
        r = at(s, bnd)
        numbers[f"svb_stage::{s}::{bnd}"] = {"deposits": round(r.deposits_usd_bn, 2), "V": round(r.V_score, 3), "S_adj": round(r.S_adj, 3),
                                             "rank": int(r.rank_S_adj_of_55), "S_final": round(r.S_final, 3), "band": r.band}
asset_list = ", ".join(f"\\${bn(at(s).assets_usd_bn)}B" for s in STAGES)
(OUT / "tab_svb.tex").write_text(r"""\begin{table}[!t]
\caption{Spider Network Inputs and Scores: SVB--First Citizens}
\label{tab:svb_scores}
\centering
\footnotesize
\textit{A. Inputs and scores}\\[2pt]
\begin{tabular}{lcc}
\toprule
\textbf{Component} & \textbf{Raw value} & \textbf{Model value} \\
\midrule
""" + "\n".join(rows_a) + r"""
\bottomrule
\end{tabular}

\vspace{6pt}
\textit{B. Retrospective: SVB's deposits at three dates}\\[2pt]
\setlength{\tabcolsep}{4pt}
\begin{tabular}{lccc}
\toprule
""" + "\n".join(rows_b) + r"""
\bottomrule
\end{tabular}
\par\vspace{2pt}\parbox{0.94\columnwidth}{\scriptsize Panel~A: SVB's last public call report, First Citizens' call report 90 or
more days before the failure, and the terms of the FDIC's announcement, normalized with the bounds, thresholds, and rescaling of
the full 55-transaction panel. Panel~B: SVB's deposits at three points of its resolution, each in place of the figure of Panel~A,
with the assets of the same date in the relative size (""" + asset_list + r"""); the relative size stays above its cap, so only $V$ changes. $\tilde S$:
rescaled on the bounds of all 55 transactions, as in Panel~A, or of the other 54, clipped to $[0, 1]$; P = Pursue, C = Caution.
Sale: the deposits First Citizens assumed. $^{\dagger}$After the failure: outside the information set (Section~\ref{sec:infoset}) and used in no other analysis.
Sources: call report; FDIC~\cite{fdic2023svb}; First Citizens~\cite{firstcitizens2023}.}
\end{table}
""")

# ------------------------------------------------------------ appendix
app = pd.read_csv(R / "appendix_primary55.csv")
SMALL = {"OF", "AND", "THE", "DE"}
KEEP = {"N.A.": "N.A.", "NA": "N.A.", "F.A.": "F.A.", "SSB": "SSB", "FSB": "FSB", "F.S.B.": "F.S.B.", "NBC": "NBC", "PFF": "PFF", "K": "K", "U.S.": "U.S."}
OVERRIDE = {"INTER SAVINGS BANK, FSB D/B/A/ INTERBANK, FSB": "Inter Savings Bank, FSB (InterBank)", "TEAMBANK, N.A.": "TeamBank, N.A.",
            "INTEGRA BANK NATIONAL ASSOCIATION": "Integra Bank, N.A.", "VINEYARD BANK, NATIONAL ASSOCIATION": "Vineyard Bank, N.A.",
            "DOWNEY SAVINGS AND LOAN ASSOCIATION, F.A.": "Downey Savings and Loan Assoc., F.A."}


def title(name: str) -> str:
    if name in OVERRIDE:
        return OVERRIDE[name]
    out = []
    for i, w in enumerate(name.split()):
        core = w.rstrip(",")
        tail = w[len(core):]
        if core in KEEP:
            t = KEEP[core]
        elif core in SMALL and i > 0:
            t = core.lower()
        else:
            t = "-".join(p.capitalize() for p in core.split("-"))
        out.append(t + tail)
    return " ".join(out).replace("&", "\\&")


tim = {"AFTER_CLOSE": "A", "PRE_OPEN": "P", "NON_TRADING_DAY": "N"}
# bank-sector CAR and label (release 4.5): from the released benchmark file next to this script, checked against the labels
# with which final_analysis.py fitted the bank-sector models
bank_car = pd.read_csv(Path(__file__).resolve().parent.parent / "data" / "Bank_Benchmark_CAR_90.csv").set_index("transaction_id")
yb_fit = pd.read_csv(R / "bank_out_of_fold_predictions.csv").groupby("transaction_id").y.agg(["min", "max"])
assert (yb_fit["min"] == yb_fit["max"]).all() and set(yb_fit.index) == set(app.transaction_id)
assert all(int(bank_car.loc[t, "y_reaction_m1p1_bank"]) == int(yb_fit.loc[t, "min"]) == int(bank_car.loc[t, "car_reaction_m1p1_bank"] > 0)
           for t in app.transaction_id), "bank labels differ from the fitted labels"
rows = []
for r in app.itertuples():
    car = 100 * r.car_reaction_m1p1
    cs = f"{car:.2f}".replace("-", "$-$")
    cb = f"{100 * bank_car.loc[r.transaction_id, 'car_reaction_m1p1_bank']:.2f}".replace("-", "$-$")
    rows.append(f"{title(r.failed_bank_name)} & {r.listed_parent_ticker} & {r.announcement_date} & {r.fdic_release} & {tim[r.announcement_timing]} & "
                f"{int(r.F_loss_share)} & {int(r.H_support_narrow)} & {cs} & {int(r.y)} & {cb} & {int(bank_car.loc[r.transaction_id, 'y_reaction_m1p1_bank'])} \\\\")
(OUT / "tab_appendix.tex").write_text(r"""\begin{table*}[!t]
\caption{Primary Panel: Source-Verified Terms, Timing, and Outcomes of the 55 Transactions}
\label{tab:appendix}
\centering
\scriptsize
\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{0.95}
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}llllccccccc}
\toprule
 & & & & & & & \multicolumn{2}{c}{\textbf{S\&P~500}} & \multicolumn{2}{c}{\textbf{Bank sector}} \\
\cmidrule(lr){8-9}\cmidrule(lr){10-11}
\textbf{Failed bank} & \textbf{Parent} & \textbf{Announced} & \textbf{FDIC release} & \textbf{Timing} & \textbf{LS} & \textbf{H} & \textbf{CAR (\%)} & \textbf{Y} & \textbf{CAR (\%)} & \textbf{Y} \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\multicolumn{11}{p{0.96\textwidth}}{\scriptsize Ordered by failed-bank total assets. Parent: ticker of the acquiring bank's listed parent (Hancock
Holding appears as HBHC and, for 2017, under its later ticker HWC; BBT is BB\&T, now Truist). Timing: A = announced after the
close (day~0 is the next session), P = before the open (same day), N = on a non-trading day (next session).
LS = FDIC loss-share agreement; H = bridge bank or systemic-risk exception (narrow definition). CAR = market-adjusted
$CAR_{[-1,+1]}$ around day~0 against the S\&P~500 (SPY) and against the bank-sector benchmark of Section~\ref{sec:outcome}, the two co-primary
outcomes; Y = 1 if the unrounded CAR is positive. Transactions bought by one acquirer on the same day share a CAR.}\\
\end{tabular*}
\end{table*}
""")

# ------------------------------------------------------------ sensitivity to the expert constants (release 4.6)
WV = pd.read_csv(R / "weight_sensitivity_variants.csv")
WS = pd.read_csv(R / "weight_sensitivity_spider.csv").merge(WV[["variant_id", "family"]], on="variant_id")
WM = pd.read_csv(R / "weight_sensitivity_model3.csv").merge(WV[["variant_id", "family"]], on="variant_id")
WN = pd.read_csv(R / "weight_sensitivity_nested_by_repeat.csv")
WB = ("SPY", "bank-sector index")


def wcell(x: pd.Series, kind: str, signed: bool = False) -> str:
    fmt = sgn if signed else f3
    if kind == "single":
        assert len(x) == 1
        return fmt(float(x.iloc[0]))
    if kind == "range":
        return f"[{fmt(x.min())}, {fmt(x.max())}]"
    return f"{fmt(x.median())} [{fmt(x.quantile(0.05))}, {fmt(x.quantile(0.95))}]"


wrows = []
for b, head in (("SPY", "A. S\\&P~500 benchmark"), ("bank-sector index", "B. Bank-sector benchmark")):
    wrows.append(f"\\multicolumn{{5}}{{l}}{{\\textit{{{head}}}}} \\\\")
    for fam_, kind, lab in (("reference", "single", "Expert constants (reference)"), ("one_at_a_time", "range", "One constant changed"),
                            ("structural", "range", "Equal weights and/or no adjustments"),
                            ("random_local", "dist", "Random, each within $\\pm$50\\%"), ("random_wide", "dist", "Random, sign-preserving")):
        ns, nm = int((WS.family == fam_).sum() // 2), int((WM.family == fam_).sum() // 2)
        sv, mv = WS[(WS.family == fam_) & (WS.benchmark == b)], WM[(WM.family == fam_) & (WM.benchmark == b)]
        cells = [f"{ns:,}" if ns == nm else f"{ns:,} ({nm})", wcell(sv.AUC_mean, kind), wcell(mv.AUC_mean, kind),
                 wcell(mv.diff_ridge_mean, kind, signed=True)]
        wrows.append(f"{lab} & " + " & ".join(cells) + r" \\")
    for fam_, lab in (("random_local", "Chosen in training folds, $\\pm$50\\% draws"),
                      ("random_wide", "Chosen in training folds, sign-preserving draws")):
        e = WN[(WN.family == fam_) & (WN.benchmark == b)]
        assert len(e) > 0
        wrows.append(f"{lab} & --- & {f3(e.AUC.mean())} & --- & --- \\\\")
    if b == "SPY":
        wrows.append(r"\midrule")
(OUT / "tab_weights.tex").write_text(r"""\begin{table*}[!t]
\caption{Sensitivity of the Spider Score and Model~3 to the Expert Weights and Interaction Adjustments: Mean AUC over 50 Partitions}
\label{tab:weights}
\centering
\scriptsize
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lcccc}
\toprule
\textbf{Constants} & \textbf{Variants} & \textbf{Spider score} & \textbf{Model~3} & \textbf{Model~3 $-$ ridge} \\
\midrule
""" + "\n".join(wrows) + r"""
\bottomrule
\multicolumn{5}{p{0.96\textwidth}}{\scriptsize Partitions: those of Table~\ref{tab:main_results} for each benchmark. Reference: the constants
of Eqs.~\eqref{eq:raw} and~\eqref{eq:adjusted}. One constant changed: one component weight times 0.5 or 1.5, the five then rescaled so that
their absolute values again sum to one, or one adjustment times 0, 0.5, or 1.5 (22 variants); equal weights: 0.20 for each component;
no adjustments: those of $Q$, $U$, $Z$, and $K$ set to zero; brackets give the lowest and highest mean AUC of the set. Random within
$\pm$50\%: every constant times an independent factor drawn uniformly between 0.5 and 1.5, the component weights then rescaled;
sign-preserving: component weights drawn uniformly over all nonnegative weights that sum to one, and each adjustment uniformly between
zero and twice its value; median across draws, with the 5th and 95th percentiles in brackets. Variants: number of constant sets for the
Spider score and, in parentheses, for Model~3, refitted with its inner tuning for each set. Model~3 $-$ ridge: mean difference from
ridge regression on the same partitions (ridge regression and Model~2 do not use the constants). Chosen in training folds: the draw
of the set, or the reference, with the highest training-fold AUC scores the held-out fold.}\\
\end{tabular*}
\end{table*}
""")

# ------------------------------------------------------------ included and excluded transactions (release 4.7)
SC = pd.read_csv(R / "table_selection_comparison.csv").set_index("characteristic")
SS = pd.read_csv(R / "table_selection_size_classes.csv")
SR = pd.read_csv(R / "table_selection_reweighted.csv")
SX = pd.read_csv(R / "selection_characteristics_94.csv")
SB = pd.read_csv(R / "table_selection_balance.csv")
SD = pd.read_csv(R / "table_selection_weight_diagnostics.csv").iloc[0]


def num(x: float, d: int) -> str:
    s = f"{x:.{d}f}"
    return s.replace("-", "$-$") if s.startswith("-") else s


def pval(p: float) -> str:
    return f"{p:.2f}" if p >= 0.01 else "$<$0.01"


srows = [r"\multicolumn{6}{l}{\textit{A. Characteristics: median [first, third quartile]}} \\",
         r"\textbf{Characteristic} & \textbf{Included} & \textbf{Excluded} & \textbf{AUC ($p$)} & \textbf{Parent acquired} & \textbf{Parent listed} \\",
         r"\midrule"]
ng = SX.group.value_counts()
srows.append(f"Transactions (events) & {ng['included']} ({SX[SX.included == 1].event.nunique()}) & "
             f"{int((SX.included == 0).sum())} ({SX[SX.included == 0].event.nunique()}) & --- & "
             f"{ng['excluded, parent acquired']} & {ng['excluded, parent listed']} \\\\")
npar = {g: SX[SX.group == g].parent.nunique() for g in ("included", "excluded, parent acquired", "excluded, parent listed")}
srows.append(f"Listed parents & {npar['included']} & {SX[SX.included == 0].parent.nunique()} & --- & "
             f"{npar['excluded, parent acquired']} & {npar['excluded, parent listed']} \\\\")
for c, lab, d in (("crisis_2008_2010", "Failed in 2008--2010", None), ("buyer_assets_usd_bn", "Acquiring bank assets, \\$ billion", 2),
                  ("C_buyer_capital_pct", "Acquiring bank capital $C$, \\%", 2), ("failed_assets_usd_bn", "Failed bank assets, \\$ billion", 2),
                  ("G_deposits_usd_bn", "Failed bank deposits $G$, \\$ billion", 2), ("N_npl_pct", "NPL ratio $N$, \\%", 2),
                  ("T_npl_change_pp", "NPL change $T$, percentage points", 2), ("L_deposit_change_pct", "Deposit change $L$, \\%", 2),
                  ("E_relative_size", "Relative size $M$", 2)):
    r = SC.loc[c]
    auc = f"{f3(r.AUC_inclusion)} ({pval(r.p_two_sided)})"
    if d is None:
        cells = [f"{100 * r[k]:.0f}\\%" for k in ("included_mean", "excluded_mean")] + [auc] + \
                [f"{100 * r[k]:.0f}\\%" for k in ("excluded_acquired_mean", "excluded_listed_mean")]
    else:
        q = lambda g: f"{num(r[g + '_median'], d)} [{num(r[g + '_q25'], d)}, {num(r[g + '_q75'], d)}]"
        cells = [q("included"), q("excluded"), auc, num(r.excluded_acquired_median, d), num(r.excluded_listed_median, d)]
    srows.append(f"{lab} & " + " & ".join(cells) + r" \\")
cut = float(SS.size_cut_usd_bn.iloc[0])
srows += [r"\midrule", r"\multicolumn{6}{l}{\textit{B. Mean AUC of the included transactions, by acquirer size and reweighted to all 94}} \\",
          r"\textbf{Transactions} & \textbf{Positive} & \textbf{Model~2} & \textbf{Ridge} & \textbf{Model~3} & \textbf{Spider score} \\",
          r"\midrule"]
MOD4 = ("Model 2", "Ridge", "Model 3", "Spider score")
for bm, head in (("S&P 500", "S\\&P~500 benchmark"), ("bank-sector index", "Bank-sector benchmark")):
    srows.append(f"\\multicolumn{{6}}{{l}}{{{head}}} \\\\")
    for cl, lab in (("all 55", "All 55"), ("at or below the median", f"Acquiring bank $\\leq$ \\${cut:.1f} billion"),
                    ("above the median", f"Acquiring bank $>$ \\${cut:.1f} billion")):
        e = SS[(SS.benchmark == bm) & (SS.acquirer_size_class == cl)].set_index("model")
        n, pos = int(e.n.iloc[0]), int(e.n_positive.iloc[0])
        srows.append(f"\\quad {lab}{'' if cl == 'all 55' else f' ({n})'} & {pos} & " + " & ".join(f3(e.loc[mm, "AUC_mean"]) for mm in MOD4) + r" \\")
    for wt, lab in (("inverse probability of inclusion", "Reweighted to all 94"),
                    ("weights truncated at the 95th percentile", "Reweighted, truncated")):
        e = SR[(SR.benchmark == bm) & (SR.weighting == wt)].set_index("model")
        srows.append(f"\\quad {lab} (effective {e.effective_n.iloc[0]:.0f}) & --- & " + " & ".join(f3(e.loc[mm, "AUC_mean"]) for mm in MOD4) + r" \\")
sd2 = lambda x: f"{x:.2f}".replace("-", "$-$") if f"{x:.2f}" != "-0.00" else "0.00"
srows += [r"\midrule", r"\multicolumn{6}{l}{\textit{C. Balance: standardized difference of the included transactions from all 94}} \\",
          r"\textbf{Characteristic} & \textbf{Mean, all 94} & \textbf{Mean, included} & \textbf{Unweighted} & \textbf{Weighted} & \textbf{Truncated} \\",
          r"\midrule"]
BLAB = {"log_acquirer_assets": "Log acquiring bank assets$^{*}$", "C_buyer_capital_pct": "Acquiring bank capital $C$, \\%$^{*}$",
        "crisis_2008_2010": "Failed in 2008--2010 (share)$^{*}$", "N_npl_pct": "NPL ratio $N$, \\%$^{*}$",
        "log_failed_assets": "Log failed bank assets", "log_G_deposits": "Log failed bank deposits $G$",
        "T_npl_change_pp": "NPL change $T$, percentage points", "L_deposit_change_pct": "Deposit change $L$, \\%",
        "log_M_relative_size": "Log relative size $M$"}
for r in SB.itertuples():
    srows.append(f"{BLAB[r.characteristic]} & {sd2(r.mean_all94)} & {sd2(r.mean_included)} & {sd2(r.std_diff_unweighted)} & "
                 f"{sd2(r.std_diff_weighted)} & {sd2(r.std_diff_truncated)} \\\\")
SN = {"incl": int((SX.included == 1).sum()), "excl": int((SX.included == 0).sum()), "pi": SX[SX.included == 1].parent.nunique(),
      "pe": SX[SX.included == 0].parent.nunique(),
      "small_ex": int(((SX.included == 0) & (SX.acquirer_size_class == "at or below the median")).sum()),
      "large_ex": int(((SX.included == 0) & (SX.acquirer_size_class == "above the median")).sum()),
      "ess": SR[SR.weighting == "inverse probability of inclusion"].effective_n.iloc[0],
      "ess_t": SR[SR.weighting == "weights truncated at the 95th percentile"].effective_n.iloc[0], "perm": int(SC.permutations.iloc[0])}
(OUT / "tab_selection.tex").write_text(r"""\begin{table*}[!t]
\caption{Included and Excluded Transactions: Characteristics, the Models' Ranking by Acquirer Size, and Covariate Balance}
\label{tab:selection}
\centering
\scriptsize
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lccccc}
\toprule
""" + "\n".join(srows) + r"""
\bottomrule
\multicolumn{6}{p{0.96\textwidth}}{\scriptsize The 94 transactions among the 150 largest eligible failures whose acquiring bank had a
U.S.-listed parent: """ + f"{SN['incl']} included ({SN['pi']} parents) and {SN['excl']} without price data ({SN['pe']} parents)" + r""". Parent acquired:
the excluded transactions whose parent was later acquired and delisted; parent listed: those whose parent still trades, under the
same or a new ticker. The failed
bank's figures come from its last public call report and the acquiring bank's from its report at the last quarter-end at least
90 days before the failure, as for the model inputs. Panel~A: for the period, the share of transactions. AUC: probability that an
included transaction has the higher value; $p$: two-sided, with inclusion permuted across listed parents (""" + f"{SN['perm']:,}" + r"""
permutations), unadjusted. Panel~B: out-of-fold predictions of Table~\ref{tab:main_results} for each benchmark, nothing refitted;
the size cut is the median acquiring bank of all 94, and """ + f"{SN['small_ex']} of the {SN['excl']}" + r""" excluded transactions
lie at or below it. Reweighted: each transaction weighted by the inverse of its probability of inclusion, estimated on the 94 from the
acquiring bank's log assets and capital, the 2008--2010 period, and the NPL ratio ($^{*}$), normalized to a mean of one; truncated: the
weights capped at their 95th percentile. Effective: the effective sample size, the squared sum of the weights over the sum of their
squares. Panel~C: (mean of the included transactions, weighted as in the column, minus the mean of all 94) divided by the standard
deviation of all 94.}\\
\end{tabular*}
\end{table*}
""")

mf = json.loads((R / "RUN_MANIFEST.json").read_text())
numbers["manifest"] = {k: mf[k] for k in ("repeats", "permutations", "event_groups_primary", "event_groups_broader", "modal_tuned_C", "sample")}
(OUT / "manuscript_numbers.json").write_text(json.dumps(numbers, indent=2, default=str))

# Move each table note out of its tabular: a full-width \multicolumn note would widen the last column.
NOTE = re.compile(r"\\multicolumn\{\d+\}\{p\{([^}]*)\}\}\{(\\scriptsize .*?)\}\\\\\n\\end\{(tabular\*?)\}", re.S)
for f in sorted(OUT.glob("tab_*.tex")):
    tex = f.read_text()
    m = NOTE.search(tex)
    if m:
        tex = tex[:m.start()] + f"\\end{{{m.group(3)}}}\n\\par\\vspace{{2pt}}\\parbox{{{m.group(1)}}}{{{m.group(2)}}}" + tex[m.end():]
        f.write_text(tex)
print("tables written:", sorted(p.name for p in OUT.glob("*.tex")))
