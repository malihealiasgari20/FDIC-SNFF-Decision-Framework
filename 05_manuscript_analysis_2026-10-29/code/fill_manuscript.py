"""Insert the generated tables and the computed numbers into the revised manuscript.

Replaces %%TAB_*%% markers with the generated LaTeX tables and @@NAME@@ markers
with numbers read from the final-analysis outputs, then checks that no marker
is left.

usage: python3 -I fill_manuscript.py <results_dir> <tables_dir> <tex_in> <tex_out>
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

R, T, TIN, TOUT = (Path(a) for a in sys.argv[1:5])
s = TIN.read_text()

for name in ("MAIN", "PAIRED", "PERM", "ABLATION", "ROBUSTNESS", "MODEL4", "SENSITIVITY", "COMPONENTS", "RISK", "APPENDIX"):
    s = s.replace(f"%%TAB_{name}%%", (T / f"tab_{name.lower()}.tex").read_text().rstrip())

SNFF, LR, RIDGE, PAIR, SCORE = "SNFF + LR (Model 3)", "Logistic regression (L2, C=1)", "Ridge logistic", "LR + pairwise interactions", "Spider score alone (Model 1)"
m = pd.read_csv(R / "table_main_comparison.csv").set_index("model")
pdiff = pd.read_csv(R / "table_paired_differences.csv")
boot = pd.read_csv(R / "table_cluster_bootstrap.csv").set_index("quantity")
perm = pd.read_csv(R / "table_permutation_test.csv").set_index("model")
null = pd.read_csv(R / "permutation_null.csv")
pol = pd.read_csv(R / "table_decision_policies.csv").set_index("policy")
sw = pd.read_csv(R / "table_cost_ratio_sweep.csv").set_index("ratio")
comp = pd.read_csv(R / "table_spider_components.csv")
mr = pd.read_csv(R / "main_by_repeat.csv")


def f3(x: float) -> str:
    return f"{x:.3f}".replace("-", "$-$") if x < 0 else f"{x:.3f}"


def d3(x: float) -> str:  # magnitude of a negative difference, written as a positive number
    return f"{abs(x):.3f}"


def sg(x: float) -> str:
    return f"{x:+.3f}".replace("-", "$-$").replace("+", "$+$")


def pd2(x: float) -> str:
    return f"{x:.2f}"


def paired(other, met="AUC"):
    return pdiff[(pdiff.comparison == f"SNFF minus {other}") & (pdiff.metric == met)].iloc[0]


eight = [k for k in m.index if k != SCORE]
vals = {
    "RIDGE_AUC": f3(m.loc[RIDGE, "AUC_mean"]), "PAIR_AUC": f3(m.loc[PAIR, "AUC_mean"]), "M2_AUC": f3(m.loc[LR, "AUC_mean"]),
    "RF_AUC": f3(m.loc["Random forest", "AUC_mean"]), "XGB_AUC": f3(m.loc["XGBoost", "AUC_mean"]), "M3_AUC": f3(m.loc[SNFF, "AUC_mean"]),
    "TREE_AUC": f3(m.loc["Decision tree", "AUC_mean"]), "LASSO_AUC": f3(m.loc["LASSO logistic", "AUC_mean"]),
    "SCORE_AUC": f3(m.loc[SCORE, "AUC_mean"]),
    "AUC_MIN": f3(m.loc[eight, "AUC_mean"].min()), "AUC_MAX": f3(m.loc[eight, "AUC_mean"].max()),
    "EVAUC_MIN": f3(m.loc[eight, "AUC_event_mean"].min()), "EVAUC_MAX": f3(m.loc[eight, "AUC_event_mean"].max()),
    "PAIR_BRIER": f3(m.loc[PAIR, "Brier_mean"]), "RIDGE_BRIER": f3(m.loc[RIDGE, "Brier_mean"]), "M3_BRIER": f3(m.loc[SNFF, "Brier_mean"]),
    "M2_BRIER": f3(m.loc[LR, "Brier_mean"]), "PREV_BRIER": f3(mr.Brier_prevalence.mean()),
    "D_M2": d3(paired(LR)["mean"]), "S_M2": f"{100 * paired(LR).share_SNFF_better:.0f}",
    "D_RIDGE": d3(paired(RIDGE)["mean"]), "S_RIDGE": f"{100 * paired(RIDGE).share_SNFF_better:.0f}",
    "D_PAIR": d3(paired(PAIR)["mean"]), "S_PAIR": f"{100 * paired(PAIR).share_SNFF_better:.0f}",
}
for key, other in (("B_RIDGE", RIDGE), ("B_M2", LR)):
    q = boot.loc[f"AUC difference SNFF minus {other}"]
    vals[key] = sg(q.estimate)
    vals[key + "_CI"] = f"[{sg(q.ci_low)}, {sg(q.ci_high)}]"
vals.update({
    "P_M2_OBS": f3(perm.loc[LR, "observed_mean_AUC"]), "P_M2_PCT": f"{100 * (null[LR] >= perm.loc[LR, 'observed_mean_AUC']).mean():.0f}",
    "P_M2": pd2(perm.loc[LR, "p_value_one_sided"]), "P_RIDGE": pd2(perm.loc[RIDGE, "p_value_one_sided"]),
    "P_M3": pd2(perm.loc[SNFF, "p_value_one_sided"]), "P_SCORE2": pd2(perm.loc[SCORE, "p_value_two_sided"]),
    "P_MIN": pd2(min(perm.loc[x, "p_value_one_sided"] for x in (LR, RIDGE, SNFF))),
    "NULL_M2": f3(perm.loc[LR, "null_mean"]), "NULL_M2_2": f"{perm.loc[LR, 'null_mean']:.2f}",
    "P_M3_OBS": f3(perm.loc[SNFF, "observed_mean_AUC"]), "P_M3_PCT": f"{100 * (null[SNFF] >= perm.loc[SNFF, 'observed_mean_AUC']).mean():.0f}",
    "P_RIDGE_OBS": f3(perm.loc[RIDGE, "observed_mean_AUC"]),
    "P_RIDGE_PCT": f"{100 * (null[RIDGE] >= perm.loc[RIDGE, 'observed_mean_AUC']).mean():.0f}",
    "PH_M2": pd2(perm.loc[LR, "p_holm_one_sided"]), "PH_RIDGE": pd2(perm.loc[RIDGE, "p_holm_one_sided"]),
    "PH_M3": pd2(perm.loc[SNFF, "p_holm_one_sided"]),
})
WORDS = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}
man = __import__("json").loads((R / "RUN_MANIFEST.json").read_text())
rfb = pd.read_csv(R / "table_bootstrap_refit.csv").set_index("quantity")
vals.update({"NPERM": f"{man['permutations']}", "PERM_REPEATS": WORDS.get(man["permutation_repeats"], str(man["permutation_repeats"])),
             "BR_N": f"{int(rfb.replicates.iloc[0])}"})
br_auc = rfb.loc[[f"AUC {nm}" for nm in (LR, RIDGE, SNFF)]]
vals["BR_AUC_LO"], vals["BR_AUC_HI"] = f"{br_auc.ci_low.min():.2f}", f"{br_auc.ci_high.max():.2f}"
for key, other in (("BR_RIDGE", RIDGE), ("BR_M2", LR)):
    q = rfb.loc[f"diff SNFF minus {other}"]
    vals[key] = sg(q["mean"])
    vals[key + "_CI"] = f"[{sg(q.ci_low)}, {sg(q.ci_high)}]"
    vals[key + "_SHARE"] = f"{100 * q.share_below_zero:.0f}"
for c, key in (("R_score", "R"), ("B_score", "B")):
    a = comp[(comp.component == c) & (comp.deals == "primary 55")].iloc[0]
    b = comp[(comp.component == c) & (comp.deals != "primary 55")].iloc[0]
    vals[f"{key}_AUC55"], vals[f"{key}_P55"] = f3(a.AUC), f"{a.p_two_sided:.3f}"
    vals[f"{key}_AUC35"], vals[f"{key}_P35"] = f3(b.AUC), f"{b.p_two_sided:.3f}"
for k, key in (("4A: fixed Spider thresholds", "P4A"), ("4B: F1-tuned threshold", "P4B"), ("4C: cost-based threshold (3:1)", "P4C")):
    r = pol.loc[k]
    vals[f"{key}_PURSUE"] = f"{r.pursue:.1f}"
    vals[f"{key}_FPR"] = f"{100 * r.FPR:.1f}"
    vals[f"{key}_U"] = f3(r.utility_3to1)
vals["SW1_GAIN"] = f3(sw.loc[1, "gain_vs_trivial"])
vals["SW2_GAIN"] = f3(sw.loc[2, "gain_vs_trivial"])
vals["PH_MIN"] = pd2(min(perm.loc[x, "p_holm_one_sided"] for x in (LR, RIDGE, SNFF)))

# robustness: bank-sector benchmark and the six published inputs only
rb = pd.read_csv(R / "table_robustness.csv")
VB, VPUB = "Reaction-day CAR[-1,+1], bank-index benchmark", "Published call-report inputs only"


def rbv(variant, model, col="AUC_mean"):
    return float(rb[(rb.variant == variant) & (rb.model == model)][col].iloc[0])


for key, var in (("BANK", VB), ("PUB", VPUB)):
    for mk, mn in (("M2", LR), ("RIDGE", RIDGE), ("M3", SNFF), ("SCORE", SCORE)):
        vals[f"{key}_{mk}"] = f3(rbv(var, mn))
vals["BANK_POS"] = str(int(rb[rb.variant == VB].positives.iloc[0]))
# influence of the FBOP cluster on Model 2
fi = pd.read_csv(R / "table_fbop_influence_model2.csv")
for key, out in (("SPY", "Reaction-day CAR[-1,+1], SPY (primary)"), ("BANK", VB)):
    for sk, smp in (("ALL", "all 55 transactions"), ("DROP", "without the FBOP cluster")):
        vals[f"FB_{key}_{sk}"] = f3(float(fi[(fi.outcome == out) & (fi["sample"] == smp)].AUC_mean.iloc[0]))
vals["FB_RANK_BANK"] = f"{float(fi[(fi.outcome == VB) & (fi['sample'] == 'all 55 transactions')].fbop_mean_percentile_rank.iloc[0]):.2f}"
# direction of the Risk component: benchmarks, windows, influence
rv = pd.read_csv(R / "table_risk_validation.csv")
ri = pd.read_csv(R / "table_risk_influence.csv")
P55 = "primary 55"


def rvv(outcome, primary=True):
    return rv[(rv.outcome == outcome) & ((rv.deals == P55) if primary else (rv.deals != P55))].iloc[0]


for key, out in (("BANK", VB), ("MM", "Reaction-day CAR[-1,+1], market model")):
    a, b = rvv(out), rvv(out, False)
    vals[f"RV_{key}55"], vals[f"RV_{key}55_P"] = f3(a.AUC_R), pd2(a.p_AUC)
    vals[f"RV_{key}35"], vals[f"RV_{key}35_P"] = f3(b.AUC_R), pd2(b.p_AUC)
vals["RV_R01_55"] = f3(rvv("Release-date CAR[0,+1]").AUC_R)
vals["RV_R11_55"] = f3(rvv("Release-date CAR[-1,+1] (June window)").AUC_R)


def riv(outcome, analysis, col="AUC_R"):
    return ri[(ri.outcome == outcome) & (ri.analysis == analysis)].iloc[0][col]


SPYO = "Reaction-day CAR[-1,+1], SPY (primary)"
LOO = ("leave one event cluster out: minimum", "leave one event cluster out: maximum")
EXCL = LOO + ("without SVB, First Republic and Washington Mutual", "without the five event clusters with the largest absolute CAR")
vals["RI_SPY_LOO_MIN"], vals["RI_SPY_LOO_MAX"] = f3(riv(SPYO, LOO[0])), f3(riv(SPYO, LOO[1]))
vals["RI_SPY_BIG3"], vals["RI_SPY_EXT"] = f3(riv(SPYO, EXCL[2])), f3(riv(SPYO, EXCL[3]))
bank_ex = [float(riv(VB, a)) for a in EXCL]
vals["RI_BANK_MIN"], vals["RI_BANK_MAX"] = f3(min(bank_ex)), f3(max(bank_ex))
vals["RI_N0810"], vals["RI_N1124"] = str(int(riv(VB, "announced 2008-2010", "n"))), str(int(riv(VB, "announced 2011-2024", "n")))
vals["RI_BANK_0810"], vals["RI_BANK_1124"] = f3(riv(VB, "announced 2008-2010")), f3(riv(VB, "announced 2011-2024"))
th = pd.read_csv(R / "table_risk_thirds.csv").set_index("R_third")
for key, t in (("LOW", "lowest third"), ("MID", "middle third"), ("HIGH", "highest third")):
    vals[f"TH_BANK_{key}"] = str(int(th.loc[t, "positive_bank"]))

for k, v in vals.items():
    s = s.replace(f"@@{k}@@", v)
left = sorted(set(re.findall(r"@@[A-Z0-9_]+@@", s)) | set(re.findall(r"%%TAB_[A-Z0-9_]+%%", s)))
TOUT.write_text(s)
print("markers left:", left if left else "none")
