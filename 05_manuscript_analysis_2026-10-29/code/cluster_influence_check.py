"""Influence of the FBOP event cluster on Model 2 (run after final_analysis.py).

The four FBOP subsidiaries sold to U.S. Bank on October 30, 2009 form the
largest event cluster of the primary panel and share one CAR. Their outcome is
negative against SPY and positive against the bank-sector benchmark. This
script reruns Model 2 (L2 logistic regression, C = 1, on the eight standardized
inputs) exactly as final_analysis.py does, with the same partition seeds, and
checks that every per-repeat AUC equals the value in main_by_repeat.csv
(primary outcome) and robustness_by_repeat.csv (bank-sector benchmark). It then
repeats the 50 partitions without the FBOP cluster (51 transactions, 50 event
clusters; folds re-drawn with the same seeds and the same grouped, stratified
procedure). For the full panel it also reports where Model 2 ranks the FBOP
transactions: their mean percentile rank among the 55 out-of-fold predictions
(0 = lowest), averaged over the 50 partitions.

usage: python3 -I cluster_influence_check.py <research_folder> <results_dir>
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import StandardScaler
from scipy.stats import rankdata

warnings.filterwarnings("ignore", message=".*did not converge.*")
ROOT, RES = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
FW = ROOT / "03_revised_framework_2026-10-29"
sys.path.insert(0, str(FW / "code"))
from snff_revised_features import raw_inputs  # noqa: E402

SEED0, REPEATS = 5000, 50  # as in final_analysis.py
LR = "Logistic regression (L2, C=1)"
BANK_VARIANT = "Reaction-day CAR[-1,+1], bank-index benchmark"

p55 = pd.read_csv(FW / "data/SNFF_Revised_Inputs_Primary55.csv")
bank = pd.read_csv(ROOT / "05_manuscript_analysis_2026-10-29/data/Bank_Benchmark_CAR_90.csv").set_index("transaction_id")
p55["y_bank"] = p55.transaction_id.map(bank.y_reaction_m1p1_bank).astype(int)
assert len(p55) == 55 and int(p55.y.sum()) == 35


def groups(d: pd.DataFrame) -> np.ndarray:
    return (d.listed_parent_ticker.astype(str) + "|" + d.first_reaction_date.astype(str)).to_numpy()


def model2_auc(d: pd.DataFrame, ycol: str, seed: int, mark=None):
    y = d[ycol].astype(int).to_numpy()
    pred = np.full(len(d), np.nan)
    for it, iv in StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed).split(np.zeros(len(d)), y, groups(d)):
        a, b = raw_inputs(d.iloc[it]), raw_inputs(d.iloc[iv])
        s = StandardScaler().fit(a)
        pred[iv] = LogisticRegression(C=1.0, max_iter=5000).fit(s.transform(a), y[it]).predict_proba(s.transform(b))[:, 1]
    if mark is None:
        return roc_auc_score(y, pred)
    return roc_auc_score(y, pred), float(((rankdata(pred) - 1) / (len(pred) - 1))[mark].mean())


fbop = (p55.listed_parent_ticker == "USB") & (p55.first_reaction_date.astype(str) == "2009-11-02")
assert int(fbop.sum()) == 4 and p55[fbop].car_reaction_m1p1.nunique() == 1
d51 = p55[~fbop].reset_index(drop=True)

main = pd.read_csv(RES / "main_by_repeat.csv")
rob = pd.read_csv(RES / "robustness_by_repeat.csv")
ref = {"y": main[main.model == LR].set_index("repeat").AUC,
       "y_bank": rob[(rob.variant == BANK_VARIANT) & (rob.model == LR)].set_index("repeat").AUC}
rows = []
for ycol, label in (("y", "Reaction-day CAR[-1,+1], SPY (primary)"), ("y_bank", BANK_VARIANT)):
    fr = [model2_auc(p55, ycol, SEED0 + r, mark=fbop.to_numpy()) for r in range(REPEATS)]
    full, rank = np.array([a for a, _ in fr]), float(np.mean([k for _, k in fr]))
    assert np.allclose(full, ref[ycol].reindex(range(REPEATS)).to_numpy(), rtol=0, atol=1e-12), f"Model 2 not reproduced for {ycol}"
    drop = np.array([model2_auc(d51, ycol, SEED0 + r) for r in range(REPEATS)])
    for sample, v, d in (("all 55 transactions", full, p55), ("without the FBOP cluster", drop, d51)):
        rows.append({"outcome": label, "sample": sample, "n": len(d), "event_clusters": len(set(groups(d))),
                     "positive": int(d[ycol].sum()), "model": LR, "AUC_mean": v.mean(),
                     "AUC_p05": np.quantile(v, 0.05), "AUC_p95": np.quantile(v, 0.95),
                     "fbop_mean_percentile_rank": rank if sample == "all 55 transactions" else np.nan})
t = pd.DataFrame(rows)
t.to_csv(RES / "table_fbop_influence_model2.csv", index=False)
print(t.round(3).to_string(index=False))
