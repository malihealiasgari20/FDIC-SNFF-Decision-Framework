"""Included and excluded transactions (release 4.7).

Of the 150 largest eligible failures, 94 were acquired by a bank whose parent was listed on a U.S.
exchange; the price data collected for the study cover 55 of them (the primary panel) and not the
other 39. This script compares the two groups on the characteristics a selection on survival could
act on (the acquirer's size and capital, the period, the target's size and distress) and asks how
the evaluation of the main models would change if the panel looked like all 94.

Every characteristic follows the reporting rules of the model inputs. The failed bank's figures come
from its last public call report (the latest quarter whose 30-day filing deadline fell before the
failure), with the deposit and NPL changes over the two quarters ending there; applied to the Stage 1
file, the rule reproduces the released inputs of all 90 listed-acquirer transactions exactly. The
acquiring bank's assets and total equity come from its call report at the last quarter-end at least
90 days before the failure: for the 55 the released inputs, for the 39 the FDIC BankFind reports in
`03_.../data/Excluded39_Buyer_Call_Reports.csv`, whose five check rows reproduce the released inputs
of the transactions they belong to exactly. No characteristic is missing for any of the 94.

Outputs (results folder):
  selection_characteristics_94.csv     the characteristics of the 94 transactions
  table_selection_comparison.csv       included against excluded: medians, quartiles, means, AUC of the
                                       characteristic for inclusion and a two-sided permutation p-value
                                       (inclusion permuted across listed parents, counted by holding company
                                       with 03_.../data/Parent_Crosswalk.csv, 10,000 permutations),
                                       with the medians of the 26 excluded transactions whose parent was
                                       later acquired and the 13 whose parent is still listed
  table_selection_size_classes.csv     mean AUC over the 50 partitions of Model 2, ridge regression,
                                       Model 3 and the Spider score among the included transactions whose
                                       acquiring bank is at most the median size of all 94 and among the
                                       others, for both benchmarks (from the released out-of-fold
                                       predictions; nothing is refitted)
  table_selection_reweighted.csv       the same mean AUCs with each included transaction weighted by the
                                       inverse of its estimated probability of inclusion (a logistic model
                                       of inclusion on the acquirer's log assets and capital, the 2008-2010
                                       period and the NPL ratio, fitted on all 94), untruncated and with the
                                       weights truncated at their 95th percentile
  selection_inclusion_weights.csv      the estimated probability of inclusion and the weights
  table_selection_balance.csv          covariate balance before and after weighting (release 4.8): for each
                                       characteristic, the mean of all 94 and of the included transactions,
                                       unweighted and with each weighting, and the standardized difference
                                       (included minus all 94, in standard deviations of the 94)
  table_selection_weight_diagnostics.csv  overlap of the estimated inclusion probabilities and the spread of
                                       the weights (release 4.8)

usage: python3 -I selection_comparison.py <research_folder> <results_dir>
  (run after final_analysis.py, whose out-of-fold predictions it reads from <results_dir>)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata
from sklearn.linear_model import LogisticRegression

T0 = time.time()
ROOT, OUT = Path(sys.argv[1]), Path(sys.argv[2])
S1 = ROOT / "02b_car_conventions_2026-10-29"
FW = ROOT / "03_revised_framework_2026-10-29/data"
NPERM, SEED = 10_000, 20261124
MODELS = {"Logistic regression (L2, C=1)": "Model 2", "Ridge logistic": "Ridge", "SNFF + LR (Model 3)": "Model 3",
          "Spider score alone (Model 1)": "Spider score"}
log = lambda m: print(f"[{time.time() - T0:7.0f}s] {m}", flush=True)
rd = lambda f: pd.read_csv(f, float_precision="round_trip")

A = rd(S1 / "Stage1_Cache_Only_Rebuild_All469_Outcomes.csv")
INC = pd.read_csv(S1 / "Stage1_Cache_Only_Rebuild_Inclusion_Log_502.csv")
P90 = rd(FW / "SNFF_Revised_Inputs_Broader90.csv")
P55 = rd(FW / "SNFF_Revised_Inputs_Primary55.csv")
BUY = pd.read_csv(FW / "Excluded39_Buyer_Call_Reports.csv")
STAT = pd.read_csv(FW / "Excluded39_Parent_Status.csv")

# ---- the 94 transactions with a U.S.-listed parent among the 150 largest ------------------------
m = A.merge(INC[["transaction_id", "meets_asset_threshold"]], on="transaction_id", how="left", validate="one_to_one")
u = m[(m.meets_asset_threshold == True) & (m.parent_listing == "US")].reset_index(drop=True)
assert len(u) == 94 and set(u.car_status) == {"CAR_COMPUTED", "NO_PRICE_DATA"}
assert set(u[u.car_status == "CAR_COMPUTED"].transaction_id) == set(P55.transaction_id)
assert set(u[u.car_status == "NO_PRICE_DATA"].transaction_id) == set(STAT.transaction_id) and len(STAT) == 39


# ---- failed bank: last public report P and the report two quarters earlier ------------------------
def failed_bank(df: pd.DataFrame) -> pd.DataFrame:
    fdate = pd.to_datetime(df.failure_date)
    rows = []
    for i in range(len(df)):
        reps = {}  # date -> quarter index (as in build_revised_variables.py)
        for k in (4, 3, 2, 1):
            reps[pd.Timestamp(df[f"failed_q_minus_{k}_repdate"].iloc[i])] = k
        pdate = max(d for d in reps if (fdate.iloc[i] - d).days > 30)
        bdate = (pdate - pd.DateOffset(months=6)) + pd.offsets.MonthEnd(0)
        assert bdate in reps
        kp, kb = reps[pdate], reps[bdate]
        g = lambda v, k: df[f"failed_{v}_q_minus_{k}"].iloc[i]
        rows.append({"transaction_id": df.transaction_id.iloc[i], "failed_report_date": str(pdate.date()),
                     "failed_report_date_base": str(bdate.date()), "assets": g("assets", kp), "dep": g("deposits", kp),
                     "npl": g("npl_ratio", kp), "dep_b": g("deposits", kb), "npl_b": g("npl_ratio", kb)})
    f = pd.DataFrame(rows)
    return pd.DataFrame({"transaction_id": f.transaction_id, "failed_report_date": f.failed_report_date,
                         "failed_report_date_base": f.failed_report_date_base, "failed_assets_usd_bn": f.assets / 1e6,
                         "G_deposits_usd_bn": f.dep / 1e6, "N_npl_pct": 100 * f.npl, "T_npl_change_pp": 100 * (f.npl - f.npl_b),
                         "L_deposit_change_pct": 100 * (f.dep / f.dep_b - 1), "_assets_k": f.assets})


# the rule reproduces the released inputs of all 90 listed-acquirer transactions exactly
chk = failed_bank(m[m.transaction_id.isin(P90.transaction_id)].reset_index(drop=True)).merge(P90, on="transaction_id",
                                                                                              suffixes=("", "_rel"))
for c in ("failed_assets_usd_bn", "G_deposits_usd_bn", "N_npl_pct", "T_npl_change_pp", "L_deposit_change_pct",
          "failed_report_date", "failed_report_date_base"):
    assert (chk[c].values == chk[c + "_rel"].values).all(), c
assert len(chk) == 90
log("failed-bank rule reproduces the released inputs of all 90 transactions exactly")


# ---- acquiring bank: last quarter-end at least 90 days before the failure -------------------------
def lag90(fd: str) -> str:
    d = pd.Timestamp(fd) - pd.Timedelta(days=90)
    qe = d + pd.offsets.QuarterEnd(0)
    return str((qe if qe <= d else d - pd.offsets.QuarterEnd(1)).date())


assert (P90.failure_date.map(lag90) == P90.buyer_report_date_lag90).all()
BUY["key"] = BUY.acquirer_bank_cert.astype(str) + "_" + BUY.report_date
chkb = BUY[BUY.role == "check against the released inputs"]
for r in chkb.itertuples(index=False):
    for t in r.transaction_ids.split(";"):
        rel = P90.set_index("transaction_id").loc[t]
        assert rel.acquirer_bank_cert == r.acquirer_bank_cert and rel.buyer_report_date_lag90 == r.report_date
        assert r.assets_usd_thousands / 1e6 == rel.buyer_assets_usd_bn_lag90
        assert 100 * r.total_equity_usd_thousands / r.assets_usd_thousands == rel.C_buyer_capital_pct, t
log(f"{len(chkb)} check reports reproduce the released buyer assets and capital exactly (total equity, EQTOT)")

X = failed_bank(u).merge(u[["transaction_id", "failure_date", "acquirer_cert", "ticker", "car_status"]], on="transaction_id")
X["included"] = (X.car_status == "CAR_COMPUTED").astype(int)
X["buyer_report_date"] = X.failure_date.map(lag90)
ex = BUY[BUY.role == "excluded acquirer"].set_index("key")
rel = P55.set_index("transaction_id")
bA, bC, par = [], [], []
for r in X.itertuples(index=False):
    if r.included:
        rr = rel.loc[r.transaction_id]
        assert rr.buyer_report_date_lag90 == r.buyer_report_date and rr.acquirer_bank_cert == r.acquirer_cert
        ak = float(round(rr.buyer_assets_usd_bn_lag90 * 1e6))  # call reports are in whole USD thousands
        assert ak / 1e6 == rr.buyer_assets_usd_bn_lag90
        bA.append(ak); bC.append(rr.C_buyer_capital_pct); par.append(rr.listed_parent_ticker)
    else:
        e = ex.loc[f"{r.acquirer_cert}_{r.buyer_report_date}"]
        assert r.transaction_id in e.transaction_ids.split(";")
        bA.append(float(e.assets_usd_thousands)); bC.append(100 * e.total_equity_usd_thousands / e.assets_usd_thousands)
        par.append(r.ticker)
X["buyer_assets_usd_bn"] = np.array(bA) / 1e6
X["C_buyer_capital_pct"] = bC
X["E_relative_size"] = X._assets_k / np.array(bA)
# stable parent identifiers: historical ticker aliases of one holding company map to one parent_id
CW = pd.read_csv(FW / "Parent_Crosswalk.csv").set_index("parent_identifier")
assert set(par) == set(CW.index), "parent identifier missing from the crosswalk"
assert CW.parent_id.nunique() == 51 and len(CW) == 52, "52 tickers of 51 holding companies"
_cert_parent = pd.Series(CW.loc[par, "parent_id"].to_numpy()).groupby(X.acquirer_cert.to_numpy()).nunique()
assert _cert_parent.max() == 1, "an acquiring bank under two holding companies"
X["parent_ticker"] = par
X["parent"] = CW.loc[par, "parent_id"].to_numpy()
for c, cr in (("N_npl_pct", "N_npl_pct"), ("G_deposits_usd_bn", "G_deposits_usd_bn"), ("L_deposit_change_pct", "L_deposit_change_pct"),
              ("T_npl_change_pp", "T_npl_change_pp"), ("E_relative_size", "E_relative_size"), ("C_buyer_capital_pct", "C_buyer_capital_pct")):
    i = X.included == 1
    assert (X.loc[i, c].values == rel.loc[X.loc[i, "transaction_id"], cr].values).all(), c
X["year"] = pd.to_datetime(X.failure_date).dt.year
X["crisis_2008_2010"] = X.year.between(2008, 2010).astype(int)
X = X.merge(STAT[["transaction_id", "parent_status"]], on="transaction_id", how="left")
X["group"] = np.where(X.included == 1, "included", "excluded, parent " + X.parent_status.fillna(""))
assert X.groupby("parent").included.nunique().max() == 1, "a parent in both groups"
rel_ev = rel.listed_parent_ticker + "_" + rel.first_reaction_date
X["event"] = np.where(X.included == 1, X.transaction_id.map(rel_ev), X.parent + "_" + X.failure_date)
SIZE_CUT = float(np.median(X.buyer_assets_usd_bn))
X["acquirer_size_class"] = np.where(X.buyer_assets_usd_bn <= SIZE_CUT, "at or below the median", "above the median")
X = X.drop(columns=["_assets_k", "car_status", "ticker", "parent_status"]).sort_values(["included", "transaction_id"],
                                                                                    ascending=[False, True])
assert X.notna().all().all(), "missing characteristic"
X.to_csv(OUT / "selection_characteristics_94.csv", index=False)
log(f"94 transactions: {X.included.sum()} included ({X[X.included == 1].event.nunique()} events, {X[X.included == 1].parent.nunique()} "
    f"parents), {(X.included == 0).sum()} excluded ({X[X.included == 0].event.nunique()} events, {X[X.included == 0].parent.nunique()} parents)")

# ---- comparison: AUC of each characteristic for inclusion, parents permuted ----------------------
VARS = [("crisis_2008_2010", "failed in 2008-2010"), ("buyer_assets_usd_bn", "acquiring bank assets, USD bn"),
        ("C_buyer_capital_pct", "acquiring bank capital C, %"), ("failed_assets_usd_bn", "failed bank assets, USD bn"),
        ("G_deposits_usd_bn", "failed bank deposits G, USD bn"), ("N_npl_pct", "NPL ratio N, %"),
        ("T_npl_change_pp", "NPL change T, pp"), ("L_deposit_change_pct", "deposit change L, %"),
        ("E_relative_size", "relative size M (failed / acquiring bank assets)")]
y = X.included.to_numpy()
parents = X.parent.to_numpy()
up = pd.unique(parents)
plab = pd.Series(X.groupby("parent").included.first()).loc[up].to_numpy()
pidx = pd.Series(np.arange(len(up)), index=up).loc[parents].to_numpy()
rng = np.random.default_rng(SEED)
LAB = np.stack([rng.permutation(plab)[pidx] for _ in range(NPERM)])  # NPERM x 94


def auc_incl(ranks: np.ndarray, lab: np.ndarray) -> np.ndarray:
    lab = np.atleast_2d(lab)
    n1 = lab.sum(axis=1); n0 = lab.shape[1] - n1
    return (lab @ ranks - n1 * (n1 + 1) / 2) / (n1 * n0)


rows = []
for c, label in VARS:
    v = X[c].to_numpy(dtype=float)
    r = rankdata(v)
    a = float(auc_incl(r, y)[0])
    null = auc_incl(r, LAB)
    p = (1 + int((np.abs(null - 0.5) >= abs(a - 0.5) - 1e-12).sum())) / (1 + NPERM)
    g = {k: X.loc[X.group == k, c] for k in ("included", "excluded, parent acquired", "excluded, parent listed")}
    inc, exc = X.loc[y == 1, c], X.loc[y == 0, c]
    rows.append({"characteristic": c, "label": label, "n_included": len(inc), "n_excluded": len(exc),
                 "included_median": inc.median(), "included_q25": inc.quantile(.25), "included_q75": inc.quantile(.75),
                 "included_mean": inc.mean(), "excluded_median": exc.median(), "excluded_q25": exc.quantile(.25),
                 "excluded_q75": exc.quantile(.75), "excluded_mean": exc.mean(),
                 "excluded_acquired_median": g["excluded, parent acquired"].median(),
                 "excluded_acquired_mean": g["excluded, parent acquired"].mean(),
                 "excluded_listed_median": g["excluded, parent listed"].median(),
                 "excluded_listed_mean": g["excluded, parent listed"].mean(),
                 "AUC_inclusion": a, "p_two_sided": p})
T = pd.DataFrame(rows)
order = np.argsort(T.p_two_sided.to_numpy(), kind="stable")
holm, run = np.empty(len(T)), 0.0
for j, i in enumerate(order):
    run = max(run, min(1.0, (len(T) - j) * T.p_two_sided.iloc[i]))
    holm[i] = run
T["p_holm"] = holm
T["n_parents_included"], T["n_parents_excluded"] = int(plab.sum()), int((1 - plab).sum())
T["n_events_included"], T["n_events_excluded"] = X[y == 1].event.nunique(), X[y == 0].event.nunique()
T["permutations"], T["seed"] = NPERM, SEED
T.to_csv(OUT / "table_selection_comparison.csv", index=False)
log("comparison written: " + "; ".join(f"{r.characteristic} {r.AUC_inclusion:.3f} (p {r.p_two_sided:.3f})" for r in T.itertuples()))


# ---- the models' ranking by acquirer size and reweighted toward all 94 --------------------------
def wauc(s: np.ndarray, yy: np.ndarray, w: np.ndarray) -> float:
    pos, neg = yy == 1, yy == 0
    d = s[pos][:, None] - s[neg][None, :]
    k = (d > 0) + 0.5 * (d == 0)
    return float((w[pos][:, None] * w[neg][None, :] * k).sum() / (w[pos].sum() * w[neg].sum()))


# the out-of-fold predictions and the model comparison of the final analysis, read from the results folder
OOF = {"S&P 500": rd(OUT / "out_of_fold_predictions.csv"), "bank-sector index": rd(OUT / "bank_out_of_fold_predictions.csv")}
REL = {"S&P 500": rd(OUT / "table_main_comparison.csv").set_index("model").AUC_mean,
       "bank-sector index": rd(OUT / "table_bank_main_comparison.csv").set_index("model").AUC_mean}
cls = X.set_index("transaction_id").acquirer_size_class


def mean_auc(d: pd.DataFrame, model: str, keep: set | None, w: pd.Series | None) -> float:
    vals = []
    for _, g in d[d.model == model].groupby("repeat", sort=True):
        if keep is not None:
            g = g[g.transaction_id.isin(keep)]
        ww = np.ones(len(g)) if w is None else g.transaction_id.map(w).to_numpy()
        vals.append(wauc(g.prediction.to_numpy(), g.y.to_numpy(), ww))
    assert len(vals) == 50
    return float(np.mean(vals))


small = set(cls[(cls == "at or below the median") & X.set_index("transaction_id").included.astype(bool)].index)
large = set(P55.transaction_id) - small
rows = []
for bm, d in OOF.items():
    yy = d.drop_duplicates("transaction_id").set_index("transaction_id").y
    for mdl, short in MODELS.items():
        full = mean_auc(d, mdl, None, None)
        assert np.isclose(full, REL[bm][mdl], rtol=0, atol=1e-12), (bm, mdl, full, REL[bm][mdl])
        for name, keep in (("all 55", None), ("at or below the median", small), ("above the median", large)):
            ids = set(P55.transaction_id) if keep is None else keep
            rows.append({"benchmark": bm, "model": short, "acquirer_size_class": name, "n": len(ids),
                         "n_positive": int(yy.loc[sorted(ids)].sum()), "AUC_mean": full if keep is None else mean_auc(d, mdl, keep, None),
                         "size_cut_usd_bn": SIZE_CUT,
                         "n_excluded_in_class": int(((X.included == 0) & (X.acquirer_size_class == name)).sum()) if keep is not None else 39})
S = pd.DataFrame(rows)
S.to_csv(OUT / "table_selection_size_classes.csv", index=False)
log(f"size classes (cut {SIZE_CUT:.3f} bn): " + "; ".join(f"{r.benchmark[:4]} {r.model} {r.acquirer_size_class[:5]} {r.AUC_mean:.3f}"
                                                         for r in S.itertuples() if r.acquirer_size_class != "all 55"))

Z = np.column_stack([np.log(X.buyer_assets_usd_bn), X.C_buyer_capital_pct, X.crisis_2008_2010, X.N_npl_pct]).astype(float)
Z = (Z - Z.mean(axis=0)) / Z.std(axis=0)
lr = LogisticRegression(C=np.inf, max_iter=10_000).fit(Z, y)
ph = lr.predict_proba(Z)[:, 1]
W = X[["transaction_id", "included"]].assign(p_inclusion=ph)
wi = pd.Series(1 / ph[y == 1], index=X.transaction_id[y == 1].to_numpy())
w_full = wi / wi.mean()
w_tr = w_full.clip(upper=float(np.quantile(w_full, 0.95)))
w_tr = w_tr / w_tr.mean()
W["weight"] = W.transaction_id.map(w_full)
W["weight_truncated_p95"] = W.transaction_id.map(w_tr)
for i, nm in enumerate(("log_acquirer_assets", "acquirer_capital", "crisis_2008_2010", "npl_ratio")):
    W[f"coef_std_{nm}"] = lr.coef_[0][i]
W["intercept"] = lr.intercept_[0]
W.to_csv(OUT / "selection_inclusion_weights.csv", index=False)
ess = lambda w: float(w.sum() ** 2 / (w ** 2).sum())
rows = []
for bm, d in OOF.items():
    for mdl, short in MODELS.items():
        for name, w in (("unweighted", None), ("inverse probability of inclusion", w_full), ("weights truncated at the 95th percentile", w_tr)):
            rows.append({"benchmark": bm, "model": short, "weighting": name, "AUC_mean": mean_auc(d, mdl, None, w),
                         "effective_n": 55.0 if w is None else ess(w), "max_weight_share": (1 / 55) if w is None else float(w.max() / w.sum())})
R = pd.DataFrame(rows)
R.to_csv(OUT / "table_selection_reweighted.csv", index=False)
log(f"reweighting: effective n {ess(w_full):.1f} (truncated {ess(w_tr):.1f}); " +
    "; ".join(f"{r.benchmark[:4]} {r.model} {r.weighting[:9]} {r.AUC_mean:.3f}" for r in R.itertuples() if r.weighting != "unweighted"))

# ---- covariate balance and overlap (release 4.8) -----------------------------------------------------
BAL = [("log_acquirer_assets", "log acquiring bank assets", np.log(X.buyer_assets_usd_bn), True),
       ("C_buyer_capital_pct", "acquiring bank capital C, %", X.C_buyer_capital_pct, True),
       ("crisis_2008_2010", "failed in 2008-2010", X.crisis_2008_2010.astype(float), True),
       ("N_npl_pct", "NPL ratio N, %", X.N_npl_pct, True),
       ("log_failed_assets", "log failed bank assets", np.log(X.failed_assets_usd_bn), False),
       ("log_G_deposits", "log failed bank deposits G", np.log(X.G_deposits_usd_bn), False),
       ("T_npl_change_pp", "NPL change T, percentage points", X.T_npl_change_pp, False),
       ("L_deposit_change_pct", "deposit change L, %", X.L_deposit_change_pct, False),
       ("log_M_relative_size", "log relative size M", np.log(X.E_relative_size), False)]
inc = y == 1
wf = X.transaction_id.map(w_full).to_numpy()[inc]
wt = X.transaction_id.map(w_tr).to_numpy()[inc]
rows = []
for key, label, v, in_model in BAL:
    v = v.to_numpy(dtype=float)
    m94, s94 = float(v.mean()), float(v.std(ddof=1))
    mi, mw, mt = float(v[inc].mean()), float(np.average(v[inc], weights=wf)), float(np.average(v[inc], weights=wt))
    rows.append({"characteristic": key, "label": label, "in_inclusion_model": in_model, "mean_all94": m94, "sd_all94": s94,
                 "mean_excluded": float(v[~inc].mean()), "mean_included": mi, "mean_included_weighted": mw,
                 "mean_included_truncated": mt, "std_diff_unweighted": (mi - m94) / s94,
                 "std_diff_weighted": (mw - m94) / s94, "std_diff_truncated": (mt - m94) / s94})
BT = pd.DataFrame(rows)
BT.to_csv(OUT / "table_selection_balance.csv", index=False)
pin, pex = ph[inc], ph[~inc]
below = X.transaction_id[~inc][pex < pin.min()].tolist()
diag = {"p_inclusion_included_min": float(pin.min()), "p_inclusion_included_max": float(pin.max()),
        "p_inclusion_excluded_min": float(pex.min()), "p_inclusion_excluded_max": float(pex.max()),
        "n_excluded_below_included_min": len(below), "excluded_below_included_min": ";".join(sorted(below)),
        "transaction_largest_weight": X.transaction_id[inc].to_numpy()[int(np.argmax(wf))]}
for nm, w in (("weighted", wf), ("truncated", wt)):
    diag.update({f"{nm}_weight_min": float(w.min()), f"{nm}_weight_median": float(np.median(w)), f"{nm}_weight_max": float(w.max()),
                 f"{nm}_max_weight_share": float(w.max() / w.sum()), f"{nm}_effective_n": ess(w)})
pd.DataFrame([diag]).to_csv(OUT / "table_selection_weight_diagnostics.csv", index=False)
log("balance (standardized difference, unweighted / weighted / truncated): " +
    "; ".join(f"{r.characteristic} {r.std_diff_unweighted:+.3f}/{r.std_diff_weighted:+.3f}/{r.std_diff_truncated:+.3f}" for r in BT.itertuples()))
log(f"overlap: inclusion probability {pin.min():.3f}-{pin.max():.3f} included, {pex.min():.3f}-{pex.max():.3f} excluded; "
    f"{len(below)} excluded below the lowest included")
log("selection comparison done")
