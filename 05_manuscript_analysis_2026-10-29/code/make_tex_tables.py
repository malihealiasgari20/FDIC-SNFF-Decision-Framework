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
# ------------------------------------------------------------ main comparison
m = pd.read_csv(R / "table_main_comparison.csv").set_index("model")
rows = []
for k in [LR, "LASSO logistic", "Ridge logistic", "Decision tree", "Random forest", "XGBoost", "LR + pairwise interactions", SNFF, "Spider score alone (Model 1)"]:
    r = m.loc[k]
    brier = f"{f3(r.Brier_mean)} {rng(r.Brier_p05, r.Brier_p95)}" if pd.notna(r.Brier_mean) else "---"
    skill = f"{100 * r.Brier_skill_mean:.1f}\\%".replace("-", "$-$") if pd.notna(r.Brier_skill_mean) else "---"
    rows.append(f"{LABEL[k]} & {f3(r.AUC_mean)} {rng(r.AUC_p05, r.AUC_p95)} & {f3(r.AUC_event_mean)} & {brier} & {skill} \\\\")
    numbers[f"main::{k}"] = {"AUC": round(r.AUC_mean, 3), "AUC_p05": round(r.AUC_p05, 3), "AUC_p95": round(r.AUC_p95, 3),
                             "AUC_event": round(r.AUC_event_mean, 3), "Brier": None if pd.isna(r.Brier_mean) else round(r.Brier_mean, 3),
                             "Brier_skill_pct": None if pd.isna(r.Brier_skill_mean) else round(100 * r.Brier_skill_mean, 1)}
mr = pd.read_csv(R / "main_by_repeat.csv")
prev = mr.Brier_prevalence.mean()
numbers["prevalence_brier"] = round(prev, 3)
(OUT / "tab_main.tex").write_text(r"""\begin{table*}[!t]
\caption{Model Comparison: 50 Repeats of Grouped 5-Fold Cross-Validation ($n=55$, 51 Event Clusters)}
\label{tab:main_results}
\centering
\footnotesize
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lcccc}
\toprule
\textbf{Model} & \textbf{AUC [5th, 95th pct.]} & \textbf{Event-weighted AUC} & \textbf{Brier [5th, 95th pct.]} & \textbf{Brier skill} \\
\midrule
""" + "\n".join(rows[:-1]) + "\n\\midrule\n" + rows[-1] + r"""
\bottomrule
\multicolumn{5}{p{0.96\textwidth}}{\scriptsize Means over the 50 repeats of the pooled out-of-fold AUC and Brier score;
brackets give the 5th and 95th percentiles across repeats (partition sensitivity, not a confidence interval).
Model~2 and the ridge comparator are the same L2-penalized logistic regression on the eight inputs; Model~2 fixes
$C=1$, the ridge comparator chooses $C$ by inner cross-validation. Event-weighted AUC collapses transactions that
share a CAR into one observation. Brier skill is the improvement over predicting the training-fold share of
positive-CAR transactions (Brier """ + f"{prev:.3f}" + r"""). The Spider score is not a probability, so only its ranking is evaluated.}\\
\end{tabular*}
\end{table*}
""")

# ------------------------------------------------------------ paired comparison + bootstrap + permutation
pdiff = pd.read_csv(R / "table_paired_differences.csv")
boot = pd.read_csv(R / "table_cluster_bootstrap.csv").set_index("quantity")
rfb = pd.read_csv(R / "table_bootstrap_refit.csv").set_index("quantity")
rows = []
for other, lab in [(LR, "Model~2 ($C=1$)"), ("Ridge logistic", "Ridge ($C$ tuned)"), ("LR + pairwise interactions", "LR + pairwise"),
                   ("Random forest", "Random forest"), ("XGBoost", "XGBoost")]:
    a = pdiff[(pdiff.comparison == f"SNFF minus {other}") & (pdiff.metric == "AUC")].iloc[0]
    b = pdiff[(pdiff.comparison == f"SNFF minus {other}") & (pdiff.metric == "Brier")].iloc[0]
    key = f"AUC difference SNFF minus {other}"
    bt = f"{sgn(boot.loc[key, 'estimate'])} [{sgn(boot.loc[key, 'ci_low'])}, {sgn(boot.loc[key, 'ci_high'])}]" if key in boot.index else "---"
    rk = f"diff SNFF minus {other}"
    rt = f"[{sgn(rfb.loc[rk, 'ci_low'])}, {sgn(rfb.loc[rk, 'ci_high'])}]" if rk in rfb.index else "---"
    rows.append(f"M3 $-$ {lab} & {sgn(a['mean'])} [{sgn(a.p05)}, {sgn(a.p95)}] & {100 * a.share_SNFF_better:.0f}\\% & "
                f"{sgn(b['mean'])} [{sgn(b.p05)}, {sgn(b.p95)}] & {bt} & {rt} \\\\")
    numbers[f"paired::{other}"] = {"AUC_diff": round(a["mean"], 3), "p05": round(a.p05, 3), "p95": round(a.p95, 3),
                                   "share_better_pct": round(100 * a.share_SNFF_better), "Brier_diff": round(b["mean"], 3),
                                   "boot": None if key not in boot.index else [round(boot.loc[key, x], 3) for x in ("estimate", "ci_low", "ci_high")],
                                   "boot_refit": None if rk not in rfb.index else [round(rfb.loc[rk, x], 3) for x in ("mean", "ci_low", "ci_high")]}
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
""" + "\n".join(rows) + r"""
\bottomrule
\multicolumn{6}{p{0.96\textwidth}}{\scriptsize Differences are Model~3 minus the comparator on the same partitions; a negative Brier
difference favors Model~3. M3 higher: share of the 50 repeats in which Model~3's AUC is higher. Both bootstraps resample the 51 event
clusters. The conditional bootstrap (4,000 draws) uses each transaction's out-of-fold prediction averaged over the 50 repeats and
is conditional on those fitted predictions; the refitting bootstrap (""" + f"{int(rfb.replicates.iloc[0])}" + r""" draws) reruns the whole nested
cross-validation, including tuning, on every resample.}\\
\end{tabular*}
\end{table*}
""")

perm = pd.read_csv(R / "table_permutation_test.csv")
rows = []
plab = {LR: "Model~2 ($C=1$)", "Ridge logistic": "Ridge ($C$ tuned)", SNFF: "Model~3 ($C$ tuned)", "Spider score alone (Model 1)": "Spider score (Model~1)"}
mf = json.loads((R / "RUN_MANIFEST.json").read_text())
for r in perm.itertuples():
    holm = "---" if pd.isna(r.p_holm_one_sided) else f"{r.p_holm_one_sided:.2f}"
    rows.append(f"{plab[r.model]} & {f3(r.observed_mean_AUC)} & {f3(r.null_mean)} & {f3(r.null_p95)} & {r.p_value_one_sided:.2f} & {holm} & {r.p_value_two_sided:.2f} \\\\")
    numbers[f"perm::{r.model}"] = {"observed": round(r.observed_mean_AUC, 3), "null_mean": round(r.null_mean, 3), "null_p95": round(r.null_p95, 3),
                                   "p_one": round(r.p_value_one_sided, 3), "p_holm": None if pd.isna(r.p_holm_one_sided) else round(r.p_holm_one_sided, 3),
                                   "p_two": round(r.p_value_two_sided, 3)}
(OUT / "tab_perm.tex").write_text(r"""\begin{table}[!t]
\caption{Permutation Tests: Is Discrimination Above Chance?}
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
""" + "\n".join(rows) + r"""
\bottomrule
\multicolumn{7}{p{0.94\columnwidth}}{\scriptsize Outcomes permuted across the 51 event clusters (""" + f"{mf['permutations']}" + r""" permutations). On every
permutation the complete nested procedure, including the inner tuning of $C$, is rerun; AUC is the mean over """ + {2: "two", 3: "three", 4: "four", 5: "five"}.get(mf['permutation_repeats'], str(mf['permutation_repeats'])) + r"""
partitions, with the same partition seeds for the observed data. One-sided: AUC above the null; Holm: one-sided
$p$ adjusted for the three models tested; two-sided: distance from 0.5.}\\
\end{tabular}
\end{table}
""")

# ------------------------------------------------------------ ablation
ab = pd.read_csv(R / "table_ablation.csv").set_index("model")
rows = []
for k in ["A: measured inputs", "B: A + Spider score", "C: A + interaction rules", "D: full SNFF (Model 3)", "E: D without protection inputs", "F: D without buyer capital"]:
    r = ab.loc[k]
    lab = k.replace("(Model 3)", "(Model~3)").replace("A +", "A $+$")
    rows.append(f"{lab} & {f3(r.AUC_mean)} & {f3(r.AUC_event_mean)} & {f3(r.Brier_mean)} \\\\")
    numbers[f"ablation::{k}"] = {"AUC": round(r.AUC_mean, 3), "AUC_event": round(r.AUC_event_mean, 3), "Brier": round(r.Brier_mean, 3)}
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
""" + "\n".join(rows) + r"""
\bottomrule
\multicolumn{4}{p{0.94\columnwidth}}{\scriptsize All stages are L2 logistic regressions with the penalty chosen in the inner
cross-validation; stage A is the ridge model of Table~\ref{tab:main_results}. In E and F the Spider score is recomputed
without the removed inputs and the rules that use them.}\\
\end{tabular}
\end{table}
""")

# ------------------------------------------------------------ robustness
rb = pd.read_csv(R / "table_robustness.csv")
br = pd.read_csv(R / "table_broader90.csv").set_index("model")
rows = []
order = ["Reaction-day CAR[-1,+1] (primary)", "Release-date CAR[0,+1]", "Release-date CAR[-1,+1] (June window)",
         "Reaction-day CAR[-1,+1], market model", "Reaction-day CAR[-1,+1], bank-index benchmark", "Published call-report inputs only",
         "Broad support definition", "U rule requires support (broad)", "Z rule removed"]
vlab = {"Reaction-day CAR[-1,+1] (primary)": "Primary specification", "Release-date CAR[0,+1]": "Outcome: $CAR_{[0,+1]}$ around announcement date",
        "Release-date CAR[-1,+1] (June window)": "Outcome: $CAR_{[-1,+1]}$ around announcement date",
        "Reaction-day CAR[-1,+1], market model": "Outcome: market-model CAR",
        "Reaction-day CAR[-1,+1], bank-index benchmark": "Outcome: CAR against bank-sector index",
        "Published call-report inputs only": "Published inputs only (no $F$, $H$)", "Broad support definition": "Broad support definition ($H$)",
        "U rule requires support (broad)": "Rule $U$ requires support (broad $H$)", "Z rule removed": "Rule $Z$ removed"}
for v in order:
    x = rb[rb.variant == v].set_index("model")
    pos = int(x.positives.iloc[0])
    rows.append(f"{vlab[v]} & {pos}/55 & {f3(x.loc[LR, 'AUC_mean'])} & {f3(x.loc['Ridge logistic', 'AUC_mean'])} & {f3(x.loc[SNFF, 'AUC_mean'])} & "
                f"{f3(x.loc['Spider score alone (Model 1)', 'AUC_mean'])} \\\\")
    numbers[f"robust::{v}"] = {"positives": pos, "LR": round(x.loc[LR, "AUC_mean"], 3), "Ridge": round(x.loc["Ridge logistic", "AUC_mean"], 3),
                               "SNFF": round(x.loc[SNFF, "AUC_mean"], 3), "Score": round(x.loc["Spider score alone (Model 1)", "AUC_mean"], 3)}
rows.append("\\midrule")
rows.append(f"Broader panel (no size cut) & 56/90 & {f3(br.loc[LR, 'AUC_mean'])} & {f3(br.loc['Ridge logistic', 'AUC_mean'])} & {f3(br.loc[SNFF, 'AUC_mean'])} & "
            f"{f3(br.loc['Spider score alone (Model 1)', 'AUC_mean'])} \\\\")
numbers["broader"] = {k: round(br.loc[k, "AUC_mean"], 3) for k in br.index}
numbers["broader_brier"] = {k: (None if pd.isna(br.loc[k, "Brier_mean"]) else round(br.loc[k, "Brier_mean"], 3)) for k in br.index}
(OUT / "tab_robustness.tex").write_text(r"""\begin{table*}[!t]
\caption{Robustness: Mean AUC over 50 Repeats under Alternative Outcomes, Specifications, and Sample}
\label{tab:robustness}
\centering
\footnotesize
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lccccc}
\toprule
\textbf{Variant} & \textbf{Positive CAR} & \textbf{Model~2} & \textbf{Ridge} & \textbf{Model~3} & \textbf{Spider score} \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\multicolumn{6}{p{0.96\textwidth}}{\scriptsize Variants with the primary outcome use the partitions of Table~\ref{tab:main_results};
each alternative outcome uses 50 grouped partitions with the same seeds, stratified on its own labels. Published inputs only:
the six call-report inputs, without the deal terms $F$ and $H$; the Spider score is recomputed without its Protection component and
rule~$Q$. The broader panel of 90 transactions (78 event clusters) uses its own 50 grouped partitions.}\\
\end{tabular*}
\end{table*}
""")

# ------------------------------------------------------------ decision policies
pol = pd.read_csv(R / "table_decision_policies.csv").set_index("policy")
rows = []
for k, lab, thr in [("4A: fixed Spider thresholds", "4A: Fixed ($\\tilde S$)", "0.70/0.40"), ("4B: F1-tuned threshold", "4B: F1-tuned", "0.55--0.80"),
                    ("4C: cost-based threshold (3:1)", "4C: Cost (3:1)", "0.75/0.45")]:
    r = pol.loc[k]
    rows.append(f"{lab} & {thr} & {r.pursue:.1f} & {r.TP:.1f}/{r.FP:.1f} & {r.F1:.3f} & {r.FPR:.3f} & {f3(r.utility_3to1)} \\\\")
    numbers[f"policy::{k}"] = {k2: round(float(r[k2]), 3) for k2 in ("pursue", "TP", "FP", "F1", "FPR", "utility_3to1")}
rows.append("\\midrule")
rows.append("\\multicolumn{7}{l}{\\textit{Trivial policies}} \\\\")
for k in ("Pursue all", "Pursue none"):
    r = pol.loc[k]
    rows.append(f"{k} & --- & {r.pursue:.0f} & {r.TP:.0f}/{r.FP:.0f} & {r.F1:.3f} & {r.FPR:.3f} & {f3(r.utility_3to1)} \\\\")
    numbers[f"policy::{k}"] = {k2: round(float(r[k2]), 3) for k2 in ("pursue", "TP", "FP", "F1", "FPR", "utility_3to1")}
(OUT / "tab_model4.tex").write_text(r"""\begin{table}[!t]
\caption{Model~4 Decision Policies ($n=55$; Mean over 50 Repeats; Utility with $B=1$, $L=3$)}
\label{tab:model4}
\centering
\footnotesize
\setlength{\tabcolsep}{2.5pt}
\begin{tabular}{lcccccc}
\toprule
\textbf{Policy} & \textbf{Thresh.} & \textbf{Pursue} & \textbf{TP/FP} & \textbf{F1} & \textbf{FPR} & \textbf{Util.} \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\multicolumn{7}{p{0.94\columnwidth}}{\scriptsize Pursue: transactions recommended for pursuit; TP/FP: of these, transactions with a
positive and with a negative announcement return; FPR: share of the 20 negative-CAR transactions recommended; Util.: realized
utility $(TP - 3\,FP)/55$.}\\
\end{tabular}
\end{table}
""")

sw = pd.read_csv(R / "table_cost_ratio_sweep.csv")
rows = []
for r in sw.itertuples():
    rows.append(f"{int(r.ratio)}:1 & {r.threshold:.2f} & {r.pursue:.1f} & {r.TP:.1f}/{r.FP:.1f} & {r.FPR:.3f} & {r.F1:.3f} & {f3(r.utility_own)} & {f3(r.gain_vs_trivial)} & {f3(r.utility_3to1)} \\\\")
    numbers[f"sweep::{int(r.ratio)}"] = {k2: round(float(getattr(r, k2)), 3) for k2 in ("threshold", "pursue", "TP", "FP", "FPR", "F1", "utility_own", "gain_vs_trivial", "utility_3to1")}
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
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\multicolumn{9}{p{0.94\columnwidth}}{\scriptsize Threshold $L/(B+L)$ applied to Model~3's out-of-fold probabilities. Gain: utility
minus that of the better trivial policy (pursue all or pursue none) at the same ratio.}\\
\end{tabular}
\end{table}
""")

# ------------------------------------------------------------ Spider components
comp = pd.read_csv(R / "table_spider_components.csv")
clab = {"S_final": "Spider score $\\tilde S$", "V_score": "Value $V$", "P_score": "Protection $P$", "B_score": "Buyer strength $B$",
        "R_score": "Risk $R$", "E_score": "Execution $E$"}
rows = []
for c in ["S_final", "V_score", "P_score", "B_score", "R_score", "E_score"]:
    a = comp[(comp.component == c) & (comp.deals == "primary 55")].iloc[0]
    b = comp[(comp.component == c) & (comp.deals != "primary 55")].iloc[0]
    rows.append(f"{clab[c]} & ${a.sign_in_S}$ & {f3(a.AUC)} & {a.p_two_sided:.2f} & {f3(b.AUC)} & {b.p_two_sided:.2f} \\\\")
    numbers[f"component::{c}"] = {"AUC55": round(a.AUC, 3), "p55": round(a.p_two_sided, 3), "AUC35": round(b.AUC, 3), "p35": round(b.p_two_sided, 3)}
(OUT / "tab_components.tex").write_text(r"""\begin{table}[!t]
\caption{Direction of the Spider Score and Its Components (AUC against a Positive CAR)}
\label{tab:components}
\centering
\footnotesize
\setlength{\tabcolsep}{3pt}
\begin{tabular}{lccccc}
\toprule
 & & \multicolumn{2}{c}{\textbf{Primary panel (55)}} & \multicolumn{2}{c}{\textbf{Other 35 deals}} \\
\cmidrule(lr){3-4}\cmidrule(lr){5-6}
\textbf{Component} & \textbf{Sign in $S$} & \textbf{AUC} & \textbf{$p$} & \textbf{AUC} & \textbf{$p$} \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\multicolumn{6}{p{0.94\columnwidth}}{\scriptsize Normalization bounds and thresholds fitted on the primary panel only; no outcome
is used. ``Other 35 deals'' are the broader-panel transactions outside the primary panel. AUC above 0.5 means
higher component values go with a positive announcement return (SPY-adjusted, primary window); $p$ is two-sided, from
10,000 permutations of outcomes across event clusters. Table~\ref{tab:risk} repeats the Risk row under other benchmarks.}\\
\end{tabular}
\end{table}
""")
thirds = pd.read_csv(R / "table_risk_thirds.csv")
numbers["risk_thirds"] = thirds.round(4).to_dict("records")

# ------------------------------------------------------------ risk component: benchmarks, windows, influence
rv = pd.read_csv(R / "table_risk_validation.csv")
ri = pd.read_csv(R / "table_risk_influence.csv")
RO = [("Reaction-day CAR[-1,+1], SPY (primary)", "SPY, reaction day (primary)"),
      ("Reaction-day CAR[-1,+1], bank-index benchmark", "Bank-sector index, reaction day"),
      ("Reaction-day CAR[-1,+1], market model", "Market model, reaction day"),
      ("Release-date CAR[0,+1]", "SPY, $[0,+1]$ around release date"),
      ("Release-date CAR[-1,+1] (June window)", "SPY, $[-1,+1]$ around release date")]
rows_a = []
cr = pd.read_csv(R / "table_spider_components.csv")
cr = cr[cr.component == "R_score"]
for key, lab in RO:
    a55 = rv[(rv.outcome == key) & (rv.deals == "primary 55")].iloc[0].copy()
    a35 = rv[(rv.outcome == key) & (rv.deals != "primary 55")].iloc[0].copy()
    if key == RO[0][0]:
        # the primary-outcome row repeats the Risk row of the components table; show that table's p-values
        # (the same statistic, a separate draw of 10,000 permutations) so that the two tables agree
        c55, c35 = cr[cr.deals == "primary 55"].iloc[0], cr[cr.deals != "primary 55"].iloc[0]
        assert abs(c55.AUC - a55.AUC_R) < 1e-12 and abs(c35.AUC - a35.AUC_R) < 1e-12
        a55["p_AUC"], a35["p_AUC"] = c55.p_two_sided, c35.p_two_sided
    rows_a.append(f"{lab} & {f3(a55.AUC_R)} ({a55.p_AUC:.2f}) & {f3(a35.AUC_R)} ({a35.p_AUC:.2f}) \\\\")
    numbers[f"risk::{key}"] = {"AUC55": round(a55.AUC_R, 3), "p55": round(a55.p_AUC, 3), "rho55": round(a55.spearman_R_CAR, 3),
                               "p_rho55": round(a55.p_spearman, 3), "AUC35": round(a35.AUC_R, 3), "p35": round(a35.p_AUC, 3),
                               "rho35": round(a35.spearman_R_CAR, 3), "p_rho35": round(a35.p_spearman, 3)}


def infl(outcome, analysis):
    return ri[(ri.outcome == outcome) & (ri.analysis == analysis)].iloc[0]


SPYK, BANKK = RO[0][0], RO[1][0]
rows_b = [f"All 55 transactions & {f3(rv[(rv.outcome == SPYK) & (rv.deals == 'primary 55')].AUC_R.iloc[0])} & "
          f"{f3(rv[(rv.outcome == BANKK) & (rv.deals == 'primary 55')].AUC_R.iloc[0])} \\\\",
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
\textbf{Outcome} & \textbf{Primary 55} & \textbf{Other 35} \\
\midrule
""" + "\n".join(rows_a) + r"""
\midrule
\multicolumn{3}{l}{\textit{B. Influence in the primary panel: AUC}} \\
\textbf{Sample} & \textbf{SPY} & \textbf{Bank index} \\
\midrule
""" + "\n".join(rows_b) + r"""
\bottomrule
\multicolumn{3}{p{0.94\columnwidth}}{\scriptsize AUC of the Risk score $R$ against a positive CAR; $p$ from 10,000 permutations of
outcomes across event clusters. Normalization bounds and thresholds are fitted on the primary panel. The bank-sector index is the
equal-weighted return of 27 U.S.-listed bank holding companies, excluding the acquirer and banks with their own announcement
within four days. Panel B drops, in turn, each of the 51 event clusters, the three largest transactions, and the five event
clusters with the largest absolute CAR under each benchmark, and splits the panel by announcement year.}\\
\end{tabular}
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
rows = []
for r in app.itertuples():
    car = 100 * r.car_reaction_m1p1
    cs = f"{car:.2f}".replace("-", "$-$")
    rows.append(f"{title(r.failed_bank_name)} & {r.listed_parent_ticker} & {r.announcement_date} & {r.fdic_release} & {tim[r.announcement_timing]} & "
                f"{int(r.F_loss_share)} & {int(r.H_support_narrow)} & {cs} & {int(r.y)} \\\\")
(OUT / "tab_appendix.tex").write_text(r"""\begin{table*}[!t]
\caption{Primary Panel: Source-Verified Terms, Timing, and Outcome of the 55 Transactions}
\label{tab:appendix}
\centering
\scriptsize
\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{0.95}
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}llllccccc}
\toprule
\textbf{Failed bank} & \textbf{Parent} & \textbf{Announced} & \textbf{FDIC release} & \textbf{Timing} & \textbf{LS} & \textbf{H} & \textbf{CAR (\%)} & \textbf{Y} \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\multicolumn{9}{p{0.96\textwidth}}{\scriptsize Ordered by failed-bank total assets. Parent: ticker of the acquiring bank's listed parent (Hancock
Holding appears as HBHC and, for 2017, under its later ticker HWC; BBT is BB\&T, now Truist). Timing: A = announced after the
close (day~0 is the next session), P = before the open (same day), N = on a non-trading day (next session).
LS = FDIC loss-share agreement; H = bridge bank or systemic-risk exception (narrow definition). CAR = market-adjusted
$CAR_{[-1,+1]}$ around day~0; Y = 1 if the unrounded CAR is positive. Transactions bought by one acquirer on the same day share a CAR.}\\
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
