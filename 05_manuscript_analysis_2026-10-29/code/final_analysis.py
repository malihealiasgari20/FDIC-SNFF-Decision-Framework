"""Final analysis for the revised manuscript (Step 5).

Every number in the revised paper is produced here from the frozen Step 3
inputs (03_revised_framework_2026-10-29/data) and the full cache-only rebuild
(02b_car_conventions_2026-10-29, for the sample counts). The design follows the
verified Step 4 package (grouped nested cross-validation, the same eight models
and tuning grids, the same decision policies), with these changes:

* event groups are the listed parent plus the reaction day, i.e. transactions
  that share one CAR always fall in the same fold (the package grouped by bank
  certificate, which splits one Wintrust return in the broader panel; the
  grouping check below reruns the broader panel with that grouping);
* 50 repeats of 5-fold cross-validation for every comparison; an alternative
  outcome window is evaluated on grouped folds stratified on its own labels;
* logistic models use L-BFGS (L2) or SAGA (L1), so the intercept is not penalized;
* group-level permutation tests that repeat the complete nested procedure,
  including tuning, on every permutation (Holm-adjusted across the three models);
* two cluster bootstraps: one conditional on the repeat-averaged out-of-fold
  predictions, and one that reruns the whole nested cross-validation on each
  resample of event clusters (refitting and tuning included);
* robustness to the information set (published call-report inputs only, without
  the deal terms F and H) and to a bank-sector benchmark for the CAR
  (05_.../data/Bank_Benchmark_CAR_90.csv, built by bank_benchmark_cars.py);
* validation of the direction of the Risk component (benchmarks, windows,
  leave-one-event-out and influential transactions);
* the component AUCs outside the primary panel are also reported for the 28
  transactions whose acquirer and reaction day, and so whose CAR, do not appear
  in the primary panel (added in release 4.2; broader_only_shared_events.csv
  lists the seven others);
* the acquisition events: each multi-bank purchase scored on its banks'
  consolidated call reports, and the cross-validated comparison and the Model 4
  policies repeated on the 51 events (added in release 4.3);
* a retrospective description of the SVB case with SVB's deposits at failure and
  as assumed by its acquirer (data/SVB_Deposit_Stages.csv), which are outside the
  information set and used nowhere else (added in release 4.4);
* the bank-sector benchmark as a co-primary outcome (added in release 4.5; a
  robustness check in the submitted paper): every analysis of the SPY outcome
  repeated with the bank-sector labels, with the same design and seeds, together
  with two-sided permutation p-values for both benchmarks and the influence of the
  FBOP cluster on every core model under both.

usage: python3 -I final_analysis.py <research_folder> <out_dir> [--quick]
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, f1_score, log_loss, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*did not converge.*")

ROOT, OUT = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
QUICK = "--quick" in sys.argv
OUT.mkdir(parents=True, exist_ok=True)
FW = ROOT / "03_revised_framework_2026-10-29"
sys.path.insert(0, str(FW / "code"))
from snff_revised_features import RevisedSpider, raw_inputs  # noqa: E402

REPEATS = 3 if QUICK else 50
NPERM = 20 if QUICK else 400          # permutations; each reruns the nested procedure with tuning
PERM_REPEATS = 2 if QUICK else 3      # cross-validation repeats per permutation (same seeds for observed and null)
NBOOT = 20 if QUICK else 500          # refitting cluster-bootstrap replicates
SEED0 = 5000
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.0f}s] {msg}", flush=True)


# ---------------------------------------------------------------- data
p55 = pd.read_csv(FW / "data/SNFF_Revised_Inputs_Primary55.csv")
b90 = pd.read_csv(FW / "data/SNFF_Revised_Inputs_Broader90.csv")
ledger = pd.read_csv(FW / "data/Source_Verification_Ledger_90.csv")
evc = pd.read_csv(FW / "data/Event_Convention_Comparison_90.csv")
mm = evc.set_index("transaction_id").y_reaction_m1p1_market_model
mmc = evc.set_index("transaction_id").car_reaction_m1p1_market_model
BANK_CSV = ROOT / "05_manuscript_analysis_2026-10-29/data/Bank_Benchmark_CAR_90.csv"
bank = pd.read_csv(BANK_CSV).set_index("transaction_id")
for d in (p55, b90):
    d["y_market_model"] = d.transaction_id.map(mm).astype(int)
    d["car_market_model"] = d.transaction_id.map(mmc)
    d["car_bank"] = d.transaction_id.map(bank.car_reaction_m1p1_bank)
    d["y_bank"] = d.transaction_id.map(bank.y_reaction_m1p1_bank).astype(int)
assert len(p55) == 55 and int(p55.y.sum()) == 35 and len(b90) == 90 and int(b90.y.sum()) == 56


GROUPING = {"fn": None}  # None: the corrected event groups below; set only for the grouping check


def groups(d: pd.DataFrame) -> np.ndarray:
    """Event clusters: transactions with the same listed parent and reaction day share one CAR."""
    if GROUPING["fn"] is not None:
        return GROUPING["fn"](d)
    return (d.listed_parent_ticker.astype(str) + "|" + d.first_reaction_date.astype(str)).to_numpy()


def make_folds(d: pd.DataFrame, y: np.ndarray, k: int, seed: int):
    sk = StratifiedGroupKFold(n_splits=k, shuffle=True, random_state=seed)
    return list(sk.split(np.zeros(len(d)), y, groups(d)))


# ------------------------------------------------------------- features
RULES = ["Q_rule", "U_rule", "Z_rule", "K_rule"]


def _rescale(train_s: pd.Series, test_s: pd.Series):
    lo, hi = train_s.min(), train_s.max()
    return (train_s - lo) / (hi - lo + 1e-12), ((test_s - lo) / (hi - lo + 1e-12)).clip(0, 1)


def features(tr: pd.DataFrame, te: pd.DataFrame, kind: str, h_col="H_support_narrow", u_requires_h=False, z_removed=False, public_only=False):
    """Returns standardized train/test matrices and the test-fold Spider frame (or None).
    Every transformation is fitted on the training rows only.
    public_only: only the six inputs published in call reports before the announcement; the deal terms F and H
    are dropped and the Spider score loses its Protection component and rule Q (as in ablation stage E)."""
    a, b = raw_inputs(tr, h_col), raw_inputs(te, h_col)
    if public_only and kind == "full":
        kind = "no_protection"
    if kind == "no_protection" or public_only:
        a, b = a.drop(columns=["F_loss_share", h_col]), b.drop(columns=["F_loss_share", h_col])
    if kind == "no_capital":
        a, b = a.drop(columns=["C_buyer_capital_pct"]), b.drop(columns=["C_buyer_capital_pct"])
    if kind == "pairwise":
        s = StandardScaler().fit(a)
        p = PolynomialFeatures(2, interaction_only=True, include_bias=False).fit(s.transform(a))
        xa, xb = p.transform(s.transform(a)), p.transform(s.transform(b))
        s2 = StandardScaler().fit(xa)
        return s2.transform(xa), s2.transform(xb), None
    if kind == "base":
        s = StandardScaler().fit(a)
        return s.transform(a), s.transform(b), None
    sp = RevisedSpider(h_col=h_col, u_requires_h=u_requires_h).fit(tr)
    fa, fb = sp.transform(tr), sp.transform(te)
    if z_removed:
        fa["S_final"], fb["S_final"] = _rescale(fa.S_adj + 0.10 * fa.Z_rule, fb.S_adj + 0.10 * fb.Z_rule)
    if kind == "no_protection":
        sa = 0.30 * fa.V_score + 0.20 * fa.B_score - 0.20 * fa.R_score - 0.10 * fa.E_score + 0.07 * fa.U_rule - 0.10 * fa.Z_rule - 0.06 * fa.K_rule
        sb = 0.30 * fb.V_score + 0.20 * fb.B_score - 0.20 * fb.R_score - 0.10 * fb.E_score + 0.07 * fb.U_rule - 0.10 * fb.Z_rule - 0.06 * fb.K_rule
        fa["S_final"], fb["S_final"] = _rescale(sa, sb)
    if kind == "no_capital":
        sa = 0.30 * fa.V_score + 0.20 * fa.P_score - 0.20 * fa.R_score - 0.10 * fa.E_score + 0.08 * fa.Q_rule + 0.07 * fa.U_rule
        sb = 0.30 * fb.V_score + 0.20 * fb.P_score - 0.20 * fb.R_score - 0.10 * fb.E_score + 0.08 * fb.Q_rule + 0.07 * fb.U_rule
        fa["S_final"], fb["S_final"] = _rescale(sa, sb)
    if kind == "score":
        names = ["S_final"]
    elif kind == "rules":
        names = RULES
    elif kind == "no_protection":
        names = ["S_final", "U_rule", "Z_rule", "K_rule"]
    elif kind == "no_capital":
        names = ["S_final", "Q_rule", "U_rule"]
    else:  # full
        names = ["S_final"] + RULES
    if z_removed:
        names = [n for n in names if n != "Z_rule"]
    ca, cb = pd.concat([a, fa[names]], axis=1), pd.concat([b, fb[names]], axis=1)
    s = StandardScaler().fit(ca)
    return s.transform(ca), s.transform(cb), fb


# ------------------------------------------------------------- models
MODELS = {  # name: (feature kind, grid)
    "Logistic regression (L2, C=1)": ("base", [1.0]),
    "LASSO logistic": ("base", [0.1, 1.0, 10.0]),
    "Ridge logistic": ("base", [0.1, 1.0, 10.0]),
    "Decision tree": ("base", [2, 3]),
    "Random forest": ("base", [2, 4]),
    "XGBoost": ("base", [1, 2]),
    "LR + pairwise interactions": ("pairwise", [0.1, 1.0, 10.0]),
    "SNFF + LR (Model 3)": ("full", [0.1, 1.0, 10.0]),
}
SNFF = "SNFF + LR (Model 3)"
LR = "Logistic regression (L2, C=1)"
RIDGE = "Ridge logistic"
SCORE = "Spider score alone (Model 1)"
ABLATIONS = {
    "A: measured inputs": "base",
    "B: A + Spider score": "score",
    "C: A + interaction rules": "rules",
    "D: full SNFF (Model 3)": "full",
    "E: D without protection inputs": "no_protection",
    "F: D without buyer capital": "no_capital",
}


def estimator(name: str, param, seed: int):
    if name == "LASSO logistic":
        return LogisticRegression(C=float(param), l1_ratio=1.0, solver="saga", max_iter=20000, random_state=seed)
    if name == "Decision tree":
        return DecisionTreeClassifier(max_depth=int(param), min_samples_leaf=4, random_state=seed)
    if name == "Random forest":
        return RandomForestClassifier(n_estimators=100, max_depth=int(param), min_samples_leaf=3, random_state=seed, n_jobs=1)
    if name == "XGBoost":
        return XGBClassifier(n_estimators=100, max_depth=int(param), learning_rate=0.05, subsample=0.9, reg_lambda=2.0,
                             eval_metric="logloss", n_jobs=1, random_state=seed)
    return LogisticRegression(C=float(param), max_iter=5000)  # L2 logistic (L-BFGS)


def tune(tr: pd.DataFrame, ytr: np.ndarray, name: str, kind: str, grid, seed: int, opts: dict):
    """Inner grouped 3-fold CV on the training rows; minimizes the mean Brier score.
    Returns the chosen parameter and the inner out-of-fold predictions at that parameter."""
    inner = make_folds(tr, ytr, 3, seed)
    mats = [features(tr.iloc[it], tr.iloc[iv], kind, **opts)[:2] + (it, iv) for it, iv in inner]
    best = None
    for param in grid:
        oof = np.full(len(tr), np.nan)
        for xa, xb, it, iv in mats:
            m = estimator(name, param, seed).fit(xa, ytr[it])
            oof[iv] = m.predict_proba(xb)[:, 1]
        bs = np.mean([brier_score_loss(ytr[iv], oof[iv]) for _, _, _, iv in mats])
        if best is None or bs < best[0] - 1e-12:
            best = (bs, param, oof)
    return best[1], best[2]


def outer_run(d: pd.DataFrame, ycol: str, folds, models: dict, seed: int, opts=None, policies=False, score=False):
    opts = opts or {}
    y = d[ycol].astype(int).to_numpy()
    pred = {nm: np.full(len(d), np.nan) for nm in models}
    if score:
        pred[SCORE] = np.full(len(d), np.nan)
    chosen, pol = [], {}
    if policies:
        pol = {k: np.zeros(len(d), dtype=int) for k in ("4A: fixed Spider thresholds", "4B: F1-tuned threshold", "4C: cost-based threshold (3:1)")}
    for k, (it, iv) in enumerate(folds):
        tr, te = d.iloc[it], d.iloc[iv]
        assert not set(groups(tr)) & set(groups(te)), "event shared between training and test"
        assert len(set(y[it])) == 2
        for nm, (kind, grid) in models.items():
            s = seed * 31 + k
            if len(grid) > 1:
                param, inner_oof = tune(tr, y[it], nm, kind, grid, s, opts)
            else:
                param, inner_oof = grid[0], None
            xa, xb, fb = features(tr, te, kind, **opts)
            m = estimator(nm, param, s).fit(xa, y[it])
            pred[nm][iv] = m.predict_proba(xb)[:, 1]
            chosen.append({"fold": k, "model": nm, "param": param})
            if policies and nm == SNFF:
                sfin = fb.S_final.to_numpy()
                pol["4A: fixed Spider thresholds"][iv] = np.where(sfin >= 0.70, 2, np.where(sfin >= 0.40, 1, 0))
                thr = [round(t, 2) for t in np.arange(0.55, 0.8001, 0.05)]
                f1s = [(f1_score(y[it], inner_oof >= t, zero_division=0), t) for t in thr]
                t_best = sorted(f1s, key=lambda z: (-z[0], -z[1]))[0][1]
                p = pred[nm][iv]
                pol["4B: F1-tuned threshold"][iv] = np.where(p >= t_best, 2, np.where(p >= 0.20, 1, 0))
                pol["4C: cost-based threshold (3:1)"][iv] = np.where(p >= 0.75, 2, np.where(p >= 0.45, 1, 0))
                chosen.append({"fold": k, "model": "4B threshold", "param": t_best})
        if score:
            _, _, fb = features(tr, te, "full", **opts)
            pred[SCORE][iv] = fb.S_final.to_numpy()
    for v in pred.values():
        assert np.isfinite(v).all()
    return pred, pol, chosen


def event_auc(y, p, g):
    t = pd.DataFrame({"g": g, "y": y, "p": p}).groupby("g").agg(y=("y", "first"), p=("p", "mean"))
    return roc_auc_score(t.y, t.p)


def metrics(d, ycol, pred, folds):
    y = d[ycol].astype(int).to_numpy()
    g = groups(d)
    prev = np.full(len(d), np.nan)
    for it, iv in folds:
        prev[iv] = y[it].mean()
    bs0 = brier_score_loss(y, prev)
    rows = []
    for nm, p in pred.items():
        r = {"model": nm, "AUC": roc_auc_score(y, p), "AUC_event": event_auc(y, p, g), "Brier_prevalence": bs0}
        if nm != SCORE:
            r.update({"Brier": brier_score_loss(y, p), "log_loss": log_loss(y, np.clip(p, 1e-7, 1 - 1e-7)),
                      "F1_at_0.5": f1_score(y, p >= 0.5, zero_division=0)})
            r["Brier_skill"] = 1 - r["Brier"] / bs0
        rows.append(r)
    return rows


def utility(y, pursue, loss=3.0):
    tp, fp = int(np.sum(pursue & (y == 1))), int(np.sum(pursue & (y == 0)))
    return tp, fp, (tp - loss * fp) / len(y)


# ============================================================ main comparison
log(f"main comparison: {REPEATS} repeats, 55 deals, {len(set(groups(p55)))} event groups")
y55 = p55.y.to_numpy()
main_rows, pol_rows, sweep_rows, chosen_rows, oof_rows, fold_sets = [], [], [], [], [], []
for r in range(REPEATS):
    folds = make_folds(p55, y55, 5, SEED0 + r)
    fold_sets.append(folds)
    pred, pol, chosen = outer_run(p55, "y", folds, MODELS, SEED0 + r, policies=True, score=True)
    for row in metrics(p55, "y", pred, folds):
        main_rows.append({"repeat": r, **row})
    for c in chosen:
        chosen_rows.append({"repeat": r, **c})
    for nm, p in pred.items():
        for i, tid in enumerate(p55.transaction_id):
            oof_rows.append({"repeat": r, "model": nm, "transaction_id": tid, "y": int(y55[i]), "prediction": p[i]})
    pol["Pursue all"] = np.full(55, 2)
    pol["Pursue none"] = np.zeros(55, dtype=int)
    for nm, dec in pol.items():
        pursue = dec == 2
        tp, fp, u = utility(y55, pursue)
        pol_rows.append({"repeat": r, "policy": nm, "pursue": int(pursue.sum()), "caution": int((dec == 1).sum()), "TP": tp, "FP": fp,
                         "FPR": fp / int((y55 == 0).sum()), "F1": f1_score(y55, pursue, zero_division=0), "utility_3to1": u})
    psnff = pred[SNFF]
    for ratio in (1, 2, 3, 4, 5):
        thr = ratio / (1 + ratio)
        pursue = psnff >= thr
        tp, fp, u_own = utility(y55, pursue, ratio)
        trivial = max(0.0, (int(y55.sum()) - ratio * int((y55 == 0).sum())) / 55)
        sweep_rows.append({"repeat": r, "ratio": ratio, "threshold": thr, "pursue": int(pursue.sum()), "TP": tp, "FP": fp,
                           "FPR": fp / int((y55 == 0).sum()), "F1": f1_score(y55, pursue, zero_division=0), "utility_own": u_own,
                           "gain_vs_trivial": u_own - trivial, "utility_3to1": utility(y55, pursue, 3)[2]})
    if r % 10 == 9 or QUICK:
        log(f"  repeat {r + 1}/{REPEATS}")
M = pd.DataFrame(main_rows)
M.to_csv(OUT / "main_by_repeat.csv", index=False)
pd.DataFrame(chosen_rows).to_csv(OUT / "tuned_parameters_by_fold.csv", index=False)
OOF = pd.DataFrame(oof_rows)
OOF.to_csv(OUT / "out_of_fold_predictions.csv", index=False)
POL = pd.DataFrame(pol_rows)
POL.to_csv(OUT / "decision_policies_by_repeat.csv", index=False)
SW = pd.DataFrame(sweep_rows)
SW.to_csv(OUT / "cost_ratio_sweep_by_repeat.csv", index=False)


def summarize(df: pd.DataFrame, keys=("model",)):
    agg = {}
    for c in ("AUC", "AUC_event", "Brier", "Brier_skill", "log_loss", "F1_at_0.5"):
        if c in df.columns:
            agg[c + "_mean"] = (c, "mean")
            agg[c + "_p05"] = (c, lambda s: s.quantile(0.05))
            agg[c + "_p95"] = (c, lambda s: s.quantile(0.95))
    return df.groupby(list(keys), sort=False).agg(**agg).reset_index()


summarize(M).to_csv(OUT / "table_main_comparison.csv", index=False)

# where the shared-outcome clusters sit in each model's ranking (mean percentile rank within a repeat)
FBOP = {"PA-0385", "PA-0386", "PA-0387", "PA-0388"}
rk = OOF.assign(rank=OOF.groupby(["repeat", "model"]).prediction.rank(pct=True))
rk["group"] = np.where(rk.transaction_id.isin(FBOP), "FBOP subsidiaries (one event, y=0)",
                       np.where(rk.y == 1, "other positive CAR", "other negative CAR"))
rk.groupby(["model", "group"])["rank"].mean().unstack().reset_index().to_csv(OUT / "table_rank_by_group.csv", index=False)
POL.groupby("policy", sort=False).mean(numeric_only=True).drop(columns="repeat").reset_index().to_csv(OUT / "table_decision_policies.csv", index=False)
SW.groupby("ratio").mean(numeric_only=True).drop(columns="repeat").reset_index().to_csv(OUT / "table_cost_ratio_sweep.csv", index=False)

# paired differences across the same partitions
pw = M.pivot_table(index="repeat", columns="model", values=["AUC", "AUC_event", "Brier"])
paired = []
for other in (LR, RIDGE, "Random forest", "LR + pairwise interactions", "XGBoost"):
    for met in ("AUC", "AUC_event", "Brier"):
        dlt = pw[(met, SNFF)] - pw[(met, other)]
        better = (dlt < 0) if met == "Brier" else (dlt > 0)
        paired.append({"comparison": f"SNFF minus {other}", "metric": met, "mean": dlt.mean(), "p05": dlt.quantile(0.05),
                       "p95": dlt.quantile(0.95), "share_SNFF_better": better.mean()})
pd.DataFrame(paired).to_csv(OUT / "table_paired_differences.csv", index=False)

# cluster bootstrap on repeat-averaged out-of-fold predictions
g55 = groups(p55)
avg = OOF.groupby(["model", "transaction_id"]).prediction.mean().unstack(0).reindex(p55.transaction_id)
ug = pd.unique(g55)
gi = [np.flatnonzero(g55 == u) for u in ug]
rng = np.random.default_rng(20261029)
boot = []
for b in range(500 if QUICK else 4000):
    take = np.concatenate([gi[j] for j in rng.integers(0, len(gi), len(gi))])
    yb = y55[take]
    if len(set(yb)) < 2:
        continue
    boot.append({nm: roc_auc_score(yb, avg[nm].to_numpy()[take]) for nm in avg.columns})
B = pd.DataFrame(boot)
brows = [{"quantity": f"AUC {nm}", "estimate": roc_auc_score(y55, avg[nm]), "ci_low": B[nm].quantile(0.025), "ci_high": B[nm].quantile(0.975)} for nm in avg.columns]
for other in (LR, RIDGE, "LR + pairwise interactions", "Random forest"):
    dd = B[SNFF] - B[other]
    brows.append({"quantity": f"AUC difference SNFF minus {other}", "estimate": roc_auc_score(y55, avg[SNFF]) - roc_auc_score(y55, avg[other]),
                  "ci_low": dd.quantile(0.025), "ci_high": dd.quantile(0.975)})
pd.DataFrame(brows).to_csv(OUT / "table_cluster_bootstrap.csv", index=False)
log("main comparison done")

# ============================================================ ablation (same outer folds)
abl_rows = []
abl_models = {nm: (kind, [0.1, 1.0, 10.0]) for nm, kind in ABLATIONS.items()}
for r in range(REPEATS):
    pred, _, _ = outer_run(p55, "y", fold_sets[r], abl_models, SEED0 + r)
    for row in metrics(p55, "y", pred, fold_sets[r]):
        abl_rows.append({"repeat": r, **row})
A = pd.DataFrame(abl_rows)
A.to_csv(OUT / "ablation_by_repeat.csv", index=False)
summarize(A).to_csv(OUT / "table_ablation.csv", index=False)
log("ablation done")

# ============================================================ robustness (same outer folds)
core = {LR: MODELS[LR], RIDGE: MODELS[RIDGE], SNFF: MODELS[SNFF]}
rob_rows = []
variants = [("Reaction-day CAR[-1,+1] (primary)", "y", {}),
            ("Release-date CAR[0,+1]", "y_release_0p1", {}),
            ("Release-date CAR[-1,+1] (June window)", "y_release_m1p1_june", {}),
            ("Reaction-day CAR[-1,+1], market model", "y_market_model", {}),
            ("Reaction-day CAR[-1,+1], bank-index benchmark", "y_bank", {}),
            ("Published call-report inputs only", "y", {"public_only": True}),
            ("Broad support definition", "y", {"h_col": "H_support_broad"}),
            ("U rule requires support (broad)", "y", {"h_col": "H_support_broad", "u_requires_h": True}),
            ("Z rule removed", "y", {"z_removed": True})]
for label, ycol, opts in variants:
    for r in range(REPEATS):
        # the primary outcome keeps the main partitions (paired with the main comparison); an alternative
        # outcome gets grouped folds with the same seed stratified on its own labels, as in the main protocol
        folds = fold_sets[r] if ycol == "y" else make_folds(p55, p55[ycol].astype(int).to_numpy(), 5, SEED0 + r)
        pred, _, _ = outer_run(p55, ycol, folds, core, SEED0 + r, opts=opts, score=True)
        for row in metrics(p55, ycol, pred, folds):
            rob_rows.append({"variant": label, "outcome": ycol, "positives": int(p55[ycol].sum()), "repeat": r, **row})
    log(f"robustness: {label}")
R = pd.DataFrame(rob_rows)
R.to_csv(OUT / "robustness_by_repeat.csv", index=False)
summarize(R, keys=("variant", "outcome", "positives", "model")).to_csv(OUT / "table_robustness.csv", index=False)

# ============================================================ broader panel (own folds)
y90 = b90.y.to_numpy()
br_rows = []
for r in range(REPEATS):
    folds = make_folds(b90, y90, 5, SEED0 + 100 + r)
    pred, _, _ = outer_run(b90, "y", folds, MODELS, SEED0 + 100 + r, score=True)
    for row in metrics(b90, "y", pred, folds):
        br_rows.append({"repeat": r, **row})
    if r % 10 == 9 or QUICK:
        log(f"  broader panel repeat {r + 1}/{REPEATS}")
BR = pd.DataFrame(br_rows)
BR.to_csv(OUT / "broader90_by_repeat.csv", index=False)
summarize(BR).to_csv(OUT / "table_broader90.csv", index=False)
log("broader panel done")

# ============================================================ shared-acquirer grouping check (broader panel)
# The Step 4 package grouped the broader panel by acquiring-bank certificate and day (79 groups). Wheatland and
# Lincoln Park were bought on the same day by two Wintrust subsidiaries and share one WTFC return, so that
# grouping can place them on opposite sides of a fold. Rerun the core models with it, same seeds, and compare.
def groups_cert(d: pd.DataFrame) -> np.ndarray:
    return (d.acquirer_bank_cert.astype(str) + "|" + d.first_reaction_date.astype(str)).to_numpy()


pair = np.flatnonzero(b90.transaction_id.isin(["PA-0309", "PA-0311"]).to_numpy())
assert len(pair) == 2 and len(set(groups(b90)[pair])) == 1 and len(set(groups_cert(b90)[pair])) == 2
assert b90.car_reaction_m1p1.iloc[pair[0]] == b90.car_reaction_m1p1.iloc[pair[1]]
gc_rows = [{"grouping": "listed parent + reaction day (corrected)", "groups": int(len(set(groups(b90)))), "wintrust_pair_split": 0, **row}
           for row in BR[BR.model.isin(list(core) + [SCORE])].to_dict("records")]
GROUPING["fn"] = groups_cert
n_cert = int(len(set(groups(b90))))
for r in range(REPEATS):
    folds = make_folds(b90, y90, 5, SEED0 + 100 + r)
    fold_of = np.empty(len(b90), dtype=int)
    for k, (_, iv) in enumerate(folds):
        fold_of[iv] = k
    pred, _, _ = outer_run(b90, "y", folds, core, SEED0 + 100 + r, score=True)
    for row in metrics(b90, "y", pred, folds):
        gc_rows.append({"grouping": "acquiring-bank certificate + day (Step 4 package)", "groups": n_cert,
                        "wintrust_pair_split": int(fold_of[pair[0]] != fold_of[pair[1]]), "repeat": r, **row})
GROUPING["fn"] = None
GC = pd.DataFrame(gc_rows)
GC.to_csv(OUT / "broader90_grouping_check_by_repeat.csv", index=False)
GC.groupby(["grouping", "groups", "model"], sort=False).agg(
    AUC_mean=("AUC", "mean"), AUC_p05=("AUC", lambda x: x.quantile(0.05)), AUC_p95=("AUC", lambda x: x.quantile(0.95)),
    Brier_mean=("Brier", "mean"), partitions_with_pair_split=("wintrust_pair_split", "sum")).reset_index().to_csv(
    OUT / "table_broader90_grouping_check.csv", index=False)
log("grouping check done")

# ============================================================ permutation test
tuned = pd.DataFrame(chosen_rows)
modal = {nm: tuned[tuned.model == nm].param.mode().iloc[0] for nm in (RIDGE, SNFF)}
# the complete procedure of the main comparison, including the inner tuning, is rerun on every permutation
perm_models = {LR: MODELS[LR], RIDGE: MODELS[RIDGE], SNFF: MODELS[SNFF]}
perm_folds_seeds = [SEED0 + 900 + r for r in range(PERM_REPEATS)]


def mean_auc(yv: np.ndarray):
    d = p55.assign(y_perm=yv)
    acc = {nm: [] for nm in list(perm_models) + [SCORE]}
    for s in perm_folds_seeds:
        folds = make_folds(d, yv, 5, s)
        pred, _, _ = outer_run(d, "y_perm", folds, perm_models, s, score=True)
        for nm, p in pred.items():
            acc[nm].append(roc_auc_score(yv, p))
    return {nm: float(np.mean(v)) for nm, v in acc.items()}


obs = mean_auc(y55)
gy = pd.Series(y55, index=g55).groupby(level=0).first().reindex(ug).to_numpy()
idx = np.array([np.flatnonzero(ug == x)[0] for x in g55])
rng = np.random.default_rng(7)
null = []
for i in range(NPERM):
    null.append(mean_auc(rng.permutation(gy)[idx]))
    if (i + 1) % 100 == 0 or QUICK and (i + 1) % 10 == 0:
        log(f"  permutation {i + 1}/{NPERM}")
N = pd.DataFrame(null)
N.to_csv(OUT / "permutation_null.csv", index=False)
perm = [{"model": nm, "setting": ("C=1" if nm == LR else ("no fitting" if nm == SCORE else "C tuned in each fold")),
         "observed_mean_AUC": obs[nm], "null_mean": N[nm].mean(), "null_p95": N[nm].quantile(0.95),
         "p_value_one_sided": (1 + (N[nm] >= obs[nm]).sum()) / (1 + len(N)),
         "p_value_two_sided": (1 + (np.abs(N[nm] - 0.5) >= abs(obs[nm] - 0.5)).sum()) / (1 + len(N))} for nm in obs]
PT = pd.DataFrame(perm)
# Holm adjustment of the one-sided p-values over the three fitted models
fit = PT[PT.model != SCORE].sort_values("p_value_one_sided")
adj, run = [], 0.0
for k, pv in enumerate(fit.p_value_one_sided):
    run = max(run, min(1.0, (len(fit) - k) * pv))
    adj.append(run)
PT["p_holm_one_sided"] = PT.model.map(dict(zip(fit.model, adj)))
PT.to_csv(OUT / "table_permutation_test.csv", index=False)
log("permutation test done")

# ============================================================ refitting cluster bootstrap
# Resample the 51 event clusters with replacement and rerun the whole nested cross-validation (tuning included)
# on each resample; copies of a cluster share its group label, so they always fall in the same fold.
boot_models = {LR: MODELS[LR], RIDGE: MODELS[RIDGE], SNFF: MODELS[SNFF]}
rng = np.random.default_rng(20261030)
rb_rows, boot_skipped = [], 0
for b in range(NBOOT):
    take = np.concatenate([gi[j] for j in rng.integers(0, len(gi), len(gi))])
    d_b = p55.iloc[take].reset_index(drop=True)
    y_b = d_b.y.to_numpy()
    try:
        pred_b, _, _ = outer_run(d_b, "y", make_folds(d_b, y_b, 5, SEED0 + 3000 + b), boot_models, SEED0 + 3000 + b)
    except (AssertionError, ValueError):
        boot_skipped += 1
        continue
    a = {nm: roc_auc_score(y_b, pv) for nm, pv in pred_b.items()}
    rb_rows.append({"replicate": b, **{f"AUC {nm}": v for nm, v in a.items()},
                    f"diff SNFF minus {RIDGE}": a[SNFF] - a[RIDGE], f"diff SNFF minus {LR}": a[SNFF] - a[LR]})
    if (b + 1) % 100 == 0 or QUICK and (b + 1) % 10 == 0:
        log(f"  refitting bootstrap {b + 1}/{NBOOT}")
RB = pd.DataFrame(rb_rows)
RB.to_csv(OUT / "bootstrap_refit_by_replicate.csv", index=False)
pd.DataFrame([{"quantity": c, "mean": RB[c].mean(), "ci_low": RB[c].quantile(0.025), "ci_high": RB[c].quantile(0.975),
               "share_below_zero": (RB[c] < 0).mean() if c.startswith("diff") else np.nan, "replicates": len(RB), "skipped": boot_skipped}
              for c in RB.columns if c != "replicate"]).to_csv(OUT / "table_bootstrap_refit.csv", index=False)
log("refitting bootstrap done")

# ============================================================ Spider components (descriptive)
o35 = b90[b90.in_primary_panel == 0].reset_index(drop=True)
# Seven of the 35 share the listed parent and reaction day, and therefore the CAR, with a primary-panel transaction
# (five FBOP subsidiaries bought by U.S. Bank, and the banks Wintrust and Ameris bought on the days they bought Wheatland
# and Darby), so their outcomes are not new observations; the 28 others are the independent check. They are evaluated
# after the 55 and the 35, so the permutation draws behind those two sets are unchanged.
shared = np.isin(groups(o35), groups(p55))
o28 = o35[~shared].reset_index(drop=True)
assert sorted(o35.transaction_id[shared]) == ["PA-0225", "PA-0311", "PA-0382", "PA-0383", "PA-0384", "PA-0389", "PA-0390"]
assert len(o28) == 28 and len(set(groups(o28))) == 27
g55_of = pd.Series(p55.transaction_id.to_numpy(), index=groups(p55))
name55 = p55.set_index("transaction_id").failed_bank_name
car55 = p55.set_index("transaction_id").car_reaction_m1p1
rows7 = []
for r, gv in zip(o35[shared].itertuples(), groups(o35)[shared]):
    ids = sorted(g55_of.loc[[gv]])
    assert all(car55[i] == r.car_reaction_m1p1 for i in ids)  # the same CAR as the primary-panel transactions of that event
    rows7.append({"transaction_id": r.transaction_id, "failed_bank_name": r.failed_bank_name, "acquirer_bank_name": r.acquirer_bank_name,
                  "listed_parent_ticker": r.listed_parent_ticker, "first_reaction_date": r.first_reaction_date,
                  "car_reaction_m1p1": r.car_reaction_m1p1, "y": int(r.y), "primary_panel_transactions_same_event": ";".join(ids),
                  "primary_panel_banks_same_event": ";".join(name55.loc[ids])})
pd.DataFrame(rows7).to_csv(OUT / "broader_only_shared_events.csv", index=False)
SETS = (("primary 55", p55), ("35 broader-only (rules fitted on the 55)", o35),
        ("28 broader-only with own event (rules fitted on the 55)", o28))
sp55 = RevisedSpider().fit(p55)
comp_rows = []
rng = np.random.default_rng(11)
for nm, d in SETS:
    f = sp55.transform(d)
    g = groups(d)
    u = pd.unique(g)
    gyy = pd.Series(d.y.to_numpy(), index=g).groupby(level=0).first().reindex(u).to_numpy()
    ix = np.array([np.flatnonzero(u == x)[0] for x in g])
    for c, sign in (("S_final", "+"), ("V_score", "+"), ("P_score", "+"), ("B_score", "+"), ("R_score", "-"), ("E_score", "-")):
        x = f[c].to_numpy(float)
        a = roc_auc_score(d.y, x)
        nul = np.array([roc_auc_score(rng.permutation(gyy)[ix], x) for _ in range(2000 if QUICK else 10000)])
        comp_rows.append({"deals": nm, "component": c, "sign_in_S": sign, "AUC": a,
                          "p_two_sided": (1 + (np.abs(nul - 0.5) >= abs(a - 0.5)).sum()) / (1 + len(nul))})
pd.DataFrame(comp_rows).to_csv(OUT / "table_spider_components.csv", index=False)
f55 = sp55.transform(p55)
terc = p55.assign(R=f55.R_score.values)
terc["R_third"] = pd.qcut(terc.R.rank(method="first"), 3, labels=["lowest third", "middle third", "highest third"])
terc.groupby("R_third", observed=True).agg(deals=("y", "size"), positive=("y", "sum"), median_CAR=("car_reaction_m1p1", "median"),
                                            positive_bank=("y_bank", "sum"), median_CAR_bank=("car_bank", "median"),
                                            mean_NPL=("N_npl_pct", "mean"), mean_deposit_change=("L_deposit_change_pct", "mean")).reset_index().to_csv(
    OUT / "table_risk_thirds.csv", index=False)
# ============================================================ risk-direction validation (descriptive)
from scipy.stats import rankdata  # noqa: E402

RISK_OUTCOMES = [("Reaction-day CAR[-1,+1], SPY (primary)", "y", "car_reaction_m1p1"),
                 ("Reaction-day CAR[-1,+1], bank-index benchmark", "y_bank", "car_bank"),
                 ("Reaction-day CAR[-1,+1], market model", "y_market_model", "car_market_model"),
                 ("Release-date CAR[0,+1]", "y_release_0p1", "car_release_0p1"),
                 ("Release-date CAR[-1,+1] (June window)", "y_release_m1p1_june", "car_release_m1p1_june")]
NPR = 2000 if QUICK else 10000


def spearman(x, y):
    return float(np.corrcoef(rankdata(x), rankdata(y))[0, 1])


def cluster_perm_p(d, x, ycol, carcol, rng):
    """Two-sided p-values for the AUC of x and its Spearman correlation with the CAR, permuting outcomes across event clusters."""
    g = groups(d)
    u = pd.unique(g)
    ix = np.array([np.flatnonzero(u == v)[0] for v in g])
    yy = pd.Series(d[ycol].to_numpy(), index=g).groupby(level=0).first().reindex(u).to_numpy()
    cc = pd.Series(d[carcol].to_numpy(), index=g).groupby(level=0).first().reindex(u).to_numpy()
    a, r = roc_auc_score(d[ycol], x), spearman(x, d[carcol])
    na, nr = [], []
    for _ in range(NPR):
        o = rng.permutation(len(u))
        na.append(roc_auc_score(yy[o][ix], x))
        nr.append(spearman(x, cc[o][ix]))
    na, nr = np.array(na), np.array(nr)
    return a, (1 + (np.abs(na - 0.5) >= abs(a - 0.5)).sum()) / (1 + NPR), r, (1 + (np.abs(nr) >= abs(r)).sum()) / (1 + NPR)


rng = np.random.default_rng(12)
rv_rows = []
for pname, d in SETS:
    x = sp55.transform(d).R_score.to_numpy(float)
    for oname, ycol, carcol in RISK_OUTCOMES:
        a, pa, r, pr_ = cluster_perm_p(d, x, ycol, carcol, rng)
        rv_rows.append({"deals": pname, "outcome": oname, "n": len(d), "positive": int(d[ycol].sum()), "AUC_R": a, "p_AUC": pa,
                        "spearman_R_CAR": r, "p_spearman": pr_})
pd.DataFrame(rv_rows).to_csv(OUT / "table_risk_validation.csv", index=False)
# influence: leave one event cluster out, drop the largest transactions, drop the most extreme returns, by period
inf_rows = []
x55 = f55.R_score.to_numpy(float)
for oname, ycol, carcol in RISK_OUTCOMES[:2]:
    yv = p55[ycol].to_numpy()
    loo = []
    for u0 in ug:
        keep = g55 != u0
        loo.append((roc_auc_score(yv[keep], x55[keep]), spearman(x55[keep], p55[carcol].to_numpy()[keep]), u0))
    lo, hi = min(loo), max(loo)
    inf_rows.append({"outcome": oname, "analysis": "leave one event cluster out: minimum", "n": 55 - int((g55 == lo[2]).sum()),
                     "AUC_R": lo[0], "spearman_R_CAR": min(v[1] for v in loo), "detail": lo[2]})
    inf_rows.append({"outcome": oname, "analysis": "leave one event cluster out: maximum", "n": 55 - int((g55 == hi[2]).sum()),
                     "AUC_R": hi[0], "spearman_R_CAR": max(v[1] for v in loo), "detail": hi[2]})
    big3 = ~p55.transaction_id.isin(["PA-0006", "PA-0004", "PA-0497"]).to_numpy()
    inf_rows.append({"outcome": oname, "analysis": "without SVB, First Republic and Washington Mutual", "n": int(big3.sum()),
                     "AUC_R": roc_auc_score(yv[big3], x55[big3]), "spearman_R_CAR": spearman(x55[big3], p55[carcol].to_numpy()[big3]), "detail": ""})
    ext = pd.Series(np.abs(p55[carcol].to_numpy()), index=g55).groupby(level=0).first().sort_values(ascending=False).index[:5]
    keep = ~np.isin(g55, ext)
    inf_rows.append({"outcome": oname, "analysis": "without the five event clusters with the largest absolute CAR", "n": int(keep.sum()),
                     "AUC_R": roc_auc_score(yv[keep], x55[keep]), "spearman_R_CAR": spearman(x55[keep], p55[carcol].to_numpy()[keep]),
                     "detail": ";".join(ext)})
    yr = pd.to_datetime(p55.announcement_date).dt.year.to_numpy()
    for lab, m in (("announced 2008-2010", yr <= 2010), ("announced 2011-2024", yr >= 2011)):
        inf_rows.append({"outcome": oname, "analysis": lab, "n": int(m.sum()), "positive": int(yv[m].sum()),
                         "AUC_R": roc_auc_score(yv[m], x55[m]) if len(set(yv[m])) == 2 else np.nan,
                         "spearman_R_CAR": spearman(x55[m], p55[carcol].to_numpy()[m]), "detail": ""})
pd.DataFrame(inf_rows).to_csv(OUT / "table_risk_influence.csv", index=False)
log("risk-direction validation done")
top = p55.assign(S=f55.S_final.values).sort_values("S", ascending=False)
top[top.S >= 0.70][["transaction_id", "failed_bank_name", "listed_parent_ticker", "S", "car_reaction_m1p1", "y"]].to_csv(OUT / "spider_score_pursue_zone_fullsample.csv", index=False)

# ============================================================ SVB case (full-panel normalization)
svb = p55[p55.transaction_id == "PA-0006"]
fs = sp55.transform(svb).iloc[0]
pr = sp55.params
case = {"inputs": svb[["N_npl_pct", "G_deposits_usd_bn", "C_buyer_capital_pct", "E_relative_size", "L_deposit_change_pct", "T_npl_change_pp",
                       "F_loss_share", "H_support_narrow", "failed_report_date", "buyer_report_date_lag90", "car_reaction_m1p1"]].iloc[0].to_dict(),
        "scores": {k: float(fs[k]) for k in ["G_n", "N_n", "C_n", "E_n", "L_flag", "T_flag", "V_score", "P_score", "R_score", "B_score", "E_score",
                                             "S_raw", "Q_rule", "U_rule", "Z_rule", "K_rule", "S_adj", "S_final"]},
        "fit_parameters": {k: (float(v) if np.isscalar(v) else v) for k, v in pr.items()}}
(OUT / "svb_case.json").write_text(json.dumps(case, indent=2, default=str))

# ============================================================ SHAP and calibration figures
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

pooled = OOF[OOF.model.isin([LR, RIDGE, SNFF])].copy()
cal_rows = []
fig, ax = plt.subplots(figsize=(6.2, 4.6))
ax.plot([0, 1], [0, 1], "--", color="#888888", lw=1, label="Perfect calibration")
for nm, mk in ((LR, "o"), (RIDGE, "s"), (SNFF, "^")):
    x = pooled[pooled.model == nm]
    bins = pd.qcut(x.prediction.rank(method="first"), 5, labels=False)
    t = x.groupby(bins).agg(mean_pred=("prediction", "mean"), observed=("y", "mean"), n=("y", "size")).reset_index()
    for _, rr in t.iterrows():
        cal_rows.append({"model": nm, "bin": int(rr.iloc[0]) + 1, "mean_prediction": rr.mean_pred, "observed_rate": rr.observed, "n": int(rr.n)})
    label = {LR: "Logistic regression (Model 2)", RIDGE: "Ridge logistic", SNFF: "SNFF + LR (Model 3)"}[nm]
    ax.plot(t.mean_pred, t.observed, marker=mk, lw=1.4, label=label)
ax.set_xlim(0.2, 1.0)  # every bin mean lies inside these limits (checked below)
ax.set_ylim(0.2, 1.0)
ax.set_xlabel("Mean predicted probability (quintile bins)")
ax.set_ylabel("Observed share with positive CAR")
ax.grid(alpha=0.25)
ax.legend(fontsize=8, loc="upper left")
fig.tight_layout()
fig.savefig(OUT / "figure_calibration.png", dpi=300)
plt.close(fig)
pd.DataFrame(cal_rows).to_csv(OUT / "table_calibration_bins.csv", index=False)
assert all(0.2 < r["mean_prediction"] < 1.0 and 0.2 < r["observed_rate"] < 1.0 for r in cal_rows), "calibration point outside the plotted range"

try:
    import shap

    full_folds = make_folds(p55, y55, 5, 4242)
    best = None
    for c in (0.1, 1.0, 10.0):
        oof = np.full(55, np.nan)
        for it, iv in full_folds:
            xa, xb, _ = features(p55.iloc[it], p55.iloc[iv], "full")
            oof[iv] = estimator(SNFF, c, 0).fit(xa, y55[it]).predict_proba(xb)[:, 1]
        bs = brier_score_loss(y55, oof)
        if best is None or bs < best[0] - 1e-12:
            best = (bs, c)
    c_full = best[1]
    fa = pd.concat([raw_inputs(p55, "H_support_narrow"), sp55.transform(p55)[["S_final"] + RULES]], axis=1)
    names = {"N_npl_pct": "NPL ratio (N)", "G_deposits_usd_bn": "Deposits (G)", "C_buyer_capital_pct": "Buyer capital (C)",
             "E_relative_size": "Relative size (E)", "L_deposit_change_pct": "Deposit change (L)", "T_npl_change_pp": "NPL change (T)",
             "F_loss_share": "Loss share (F)", "H_support_narrow": "Support (H)", "S_final": "Spider score",
             "Q_rule": "Rule Q", "U_rule": "Rule U", "Z_rule": "Rule Z", "K_rule": "Rule K"}
    sc = StandardScaler().fit(fa)
    X = sc.transform(fa)
    mfull = estimator(SNFF, c_full, 0).fit(X, y55)
    ex = shap.LinearExplainer(mfull, X)
    sv = ex(X)
    imp = pd.DataFrame({"feature": [names[c] for c in fa.columns], "mean_abs_shap": np.abs(sv.values).mean(0),
                        "coefficient_standardized": mfull.coef_.ravel()}).sort_values("mean_abs_shap", ascending=False)
    imp.to_csv(OUT / "table_shap_fullsample.csv", index=False)
    shap.summary_plot(sv.values, X, feature_names=[names[c] for c in fa.columns], show=False, max_display=13, plot_size=(7.0, 4.8),
                      rng=np.random.default_rng(0))  # seeded jitter, so the figure is reproducible byte for byte
    plt.tight_layout()
    plt.savefig(OUT / "figure_shap_fullsample.png", dpi=300, bbox_inches="tight")
    plt.close("all")
    shap_info = {"C_full_sample": c_full, "shap_version": shap.__version__}
except Exception as e:  # keep the run usable without shap
    shap_info = {"error": repr(e)}

# ============================================================ sample construction counts
oall = pd.read_csv(ROOT / "02b_car_conventions_2026-10-29/Stage1_Cache_Only_Rebuild_All469_Outcomes.csv")
inc = pd.read_csv(ROOT / "02b_car_conventions_2026-10-29/Stage1_Cache_Only_Rebuild_Inclusion_Log_502.csv")
top150 = set(inc.loc[inc.inclusion_exclusion_reason == "INCLUDED", "transaction_id"])
oall["top150"] = oall.transaction_id.isin(top150)
cnt = pd.crosstab([oall.top150, oall.parent_listing.fillna("NA")], oall.car_status)
cnt.to_csv(OUT / "table_sample_construction.csv")
t150 = oall[oall.top150]
sample = {"P&A failures": int(len(inc)), "with complete call reports": int(len(oall)), "150 largest": int(len(t150)),
          "150: U.S.-listed parent": int((t150.parent_listing == "US").sum()),
          "150: U.S.-listed with prices (primary panel)": int(((t150.parent_listing == "US") & (t150.car_status == "CAR_COMPUTED")).sum()),
          "150: U.S.-listed without prices": int(((t150.parent_listing == "US") & (t150.car_status == "NO_PRICE_DATA")).sum()),
          "150: private": int((t150.parent_listing == "PRIVATE").sum()), "150: foreign-owned": int((t150.parent_listing == "FOREIGN").sum()),
          "150: OTC": int((t150.parent_listing == "OTC").sum()),
          "469: U.S.-listed parent": int((oall.parent_listing == "US").sum()),
          "469: U.S.-listed with prices (broader panel)": int(((oall.parent_listing == "US") & (oall.car_status == "CAR_COMPUTED")).sum())}
assert sample["150: U.S.-listed with prices (primary panel)"] == 55 and sample["469: U.S.-listed with prices (broader panel)"] == 90

# ============================================================ appendix table rows
lg = ledger.set_index("transaction_id")
app = p55[["transaction_id", "failed_bank_name", "acquirer_bank_name", "listed_parent_ticker", "announcement_date", "announcement_timing",
           "first_reaction_date", "F_loss_share", "H_support_narrow", "H_support_broad", "car_reaction_m1p1", "y", "failed_assets_usd_bn"]].copy()
app["fdic_release"] = app.transaction_id.map(lg.fdic_pr)
app.sort_values("failed_assets_usd_bn", ascending=False).to_csv(OUT / "appendix_primary55.csv", index=False)

# ============================================================ acquisition events (release 4.3)
# BEGIN EVENT-LEVEL SECTION
# The unit of decision is the acquisition event: every failed bank that one acquirer bought from the FDIC on one day.
# build_event_inputs.py scores each of the 51 events of the primary panel on the consolidated call reports of every bank
# its acquirer bought that day. (a) The multi-bank events, scored with the full-panel Spider fit of the SVB case:
# each bank alone, the consolidated event, and the simple and asset-weighted means of the bank scores. (b) The
# cross-validated comparison and the Model 4 policies repeated on the 51 events, with the same partition seeds.
# This section runs last, so every earlier result is unchanged.
ev51 = pd.read_csv(FW / "data/SNFF_Event_Inputs_Primary51.csv")
evcons = pd.read_csv(FW / "data/SNFF_Event_Consolidations.csv")
assert len(ev51) == 51 and int(ev51.y.sum()) == 34 and len(set(groups(ev51))) == 51 and int(ev51.n_banks.sum()) == 62


def band(s):
    return np.where(np.asarray(s, dtype=float) >= 0.70, "Pursue", np.where(np.asarray(s, dtype=float) >= 0.40, "Caution", "Avoid"))


SPC = ["G_n", "N_n", "C_n", "E_n", "L_flag", "T_flag", "V_score", "P_score", "R_score", "B_score", "E_score", "S_raw",
       "Q_rule", "U_rule", "Z_rule", "K_rule", "S_adj", "S_final"]
INP = ["failed_assets_usd_bn", "G_deposits_usd_bn", "N_npl_pct", "L_deposit_change_pct", "T_npl_change_pp", "C_buyer_capital_pct",
       "E_relative_size", "F_loss_share", "H_support_narrow", "car_reaction_m1p1", "y"]
mrows = []
b90e = b90.assign(event_id=groups(b90))
for e in pd.unique(evcons.event_id):
    banks = b90e[b90e.event_id == e].sort_values("failed_assets_usd_bn", ascending=False)
    fbk = sp55.transform(banks)
    for (_, r), (_, f) in zip(banks.iterrows(), fbk.iterrows()):
        mrows.append({"event_id": e, "row": "bank", "scope": "", "transaction_id": r.transaction_id, "name": r.failed_bank_name,
                      "in_primary_panel": int(r.in_primary_panel), "n_banks": 1, **{c: r[c] for c in INP}, **{c: f[c] for c in SPC}})
    cons_e = evcons[evcons.event_id == e]
    fcs = sp55.transform(cons_e)
    for (_, r), (_, f) in zip(cons_e.iterrows(), fcs.iterrows()):
        mrows.append({"event_id": e, "row": "consolidated event", "scope": r.scope, "transaction_id": r.member_transaction_ids,
                      "name": r.failed_bank_name, "in_primary_panel": int(r.in_primary_panel), "n_banks": int(r.n_banks),
                      **{c: r[c] for c in INP}, **{c: f[c] for c in SPC}})
    s, w, pm = fbk.S_final.to_numpy(), banks.failed_assets_usd_bn.to_numpy(), banks.in_primary_panel.to_numpy() == 1
    for scope, m in (("all banks bought that day", np.ones(len(s), dtype=bool)), ("banks in the primary panel", pm)):
        if m.sum() < 2 or (scope == "banks in the primary panel" and m.all()):
            continue
        for lab, val in (("mean of the bank scores", s[m].mean()), ("asset-weighted mean of the bank scores", np.average(s[m], weights=w[m]))):
            mrows.append({"event_id": e, "row": lab, "scope": scope, "n_banks": int(m.sum()), "S_final": val})
MB = pd.DataFrame(mrows)
MB["band"] = band(MB.S_final)
MB.to_csv(OUT / "table_multibank_events.csv", index=False)

y51 = ev51.y.to_numpy()
ev_rows, evpol_rows = [], []
for r in range(REPEATS):
    folds = make_folds(ev51, y51, 5, SEED0 + r)
    pred, pol, _ = outer_run(ev51, "y", folds, MODELS, SEED0 + r, policies=True, score=True)
    for row in metrics(ev51, "y", pred, folds):
        ev_rows.append({"repeat": r, **row})
    pol["Pursue all"] = np.full(51, 2)
    pol["Pursue none"] = np.zeros(51, dtype=int)
    for nm, dec in pol.items():
        pursue = dec == 2
        tp, fp, u = utility(y51, pursue)
        evpol_rows.append({"repeat": r, "policy": nm, "pursue": int(pursue.sum()), "caution": int((dec == 1).sum()), "TP": tp, "FP": fp,
                           "FPR": fp / int((y51 == 0).sum()), "F1": f1_score(y51, pursue, zero_division=0), "utility_3to1": u})
    if r % 10 == 9 or QUICK:
        log(f"  event level: repeat {r + 1}/{REPEATS}")
EV = pd.DataFrame(ev_rows)
EV.to_csv(OUT / "event_level_by_repeat.csv", index=False)
summarize(EV).to_csv(OUT / "table_event_level.csv", index=False)
EP = pd.DataFrame(evpol_rows)
EP.to_csv(OUT / "event_level_decision_policies_by_repeat.csv", index=False)
EP.groupby("policy", sort=False).mean(numeric_only=True).drop(columns="repeat").reset_index().to_csv(
    OUT / "table_event_level_decision_policies.csv", index=False)
log("acquisition events done")
# END EVENT-LEVEL SECTION

# BEGIN SVB DEPOSIT STAGES SECTION (release 4.4)
# A retrospective description of the SVB case, outside the information set: SVB's deposits (and assets) at its last
# call report, at failure, and as assumed by First Citizens (data/SVB_Deposit_Stages.csv). Each later figure replaces
# the call-report figure of the SVB case, every other input unchanged, and is scored with the full-panel Spider fit of
# Table 6 and with a fit on the other 54 transactions (as cross-validation scores a held-out transaction). Variant
# "deposits and assets": the deposit level (V) and the assets in the relative size (E); variant "... and deposit
# change": also the deposit change, measured from the report two quarters before the call report to the stage date.
# The figures are used nowhere else, and the panel keeps the call-report inputs. No random numbers are drawn.
stages = pd.read_csv(FW / "data/SVB_Deposit_Stages.csv")
assert list(stages.stage) == ["last call report", "at failure", "assumed by the acquirer"]
assert list(stages.in_information_set) == [1, 0, 0]
assert stages.as_of_date.iloc[0] == svb.failed_report_date.iloc[0]
assert np.isclose(stages.deposits_usd_bn.iloc[0], svb.G_deposits_usd_bn.iloc[0], atol=1e-9)
assert np.isclose(stages.assets_usd_bn.iloc[0], svb.failed_assets_usd_bn.iloc[0], atol=1e-9)
assert np.isclose(stages.assets_usd_bn.iloc[0] / svb.buyer_assets_usd_bn_lag90.iloc[0], svb.E_relative_size.iloc[0], atol=1e-6)
dep_base = float(svb.G_deposits_usd_bn.iloc[0] / (1 + svb.L_deposit_change_pct.iloc[0] / 100))  # deposits two quarters earlier
not_svb = p55.transaction_id.to_numpy() != "PA-0006"
sp54 = RevisedSpider().fit(p55[not_svb])
other_s = f55.S_adj.to_numpy()[not_svb]
FITS = (("all 55", sp55), ("other 54", sp54))
VARIANTS = ("deposits and assets", "deposits, assets and deposit change")
srows, brows = [], []
for variant in VARIANTS:
    for _, st in stages.iterrows():
        d = svb.copy()
        if st.in_information_set == 0:
            d["G_deposits_usd_bn"] = st.deposits_usd_bn
            d["E_relative_size"] = st.assets_usd_bn / svb.buyer_assets_usd_bn_lag90.iloc[0]
            if variant != VARIANTS[0]:
                d["L_deposit_change_pct"] = 100 * (st.deposits_usd_bn / dep_base - 1)
        for bname, sp in FITS:
            f = sp.transform(d).iloc[0]
            pr_ = sp.params
            srows.append({"variant": variant, "stage": st.stage, "as_of_date": st.as_of_date, "in_information_set": int(st.in_information_set),
                          "bounds": bname, "deposits_usd_bn": float(d.G_deposits_usd_bn.iloc[0]), "assets_usd_bn": float(st.assets_usd_bn),
                          "relative_size": float(d.E_relative_size.iloc[0]), "relative_size_cap": pr_["E_cap"],
                          "L_deposit_change_pct": float(d.L_deposit_change_pct.iloc[0]),
                          **{c: float(f[c]) for c in ["G_n", "L_flag", "V_score", "R_score", "E_n", "E_score", "U_rule", "S_adj"]},
                          "rank_S_adj_of_55": int(1 + (other_s > f.S_adj + 1e-12).sum()),
                          "S_final_unclipped": float((f.S_adj - pr_["S_min"]) / (pr_["S_max"] - pr_["S_min"] + 1e-12)),
                          "S_final": float(f.S_final), "band": str(band(f.S_final))})
    for bname, sp in FITS:
        pr_ = sp.params
        # deposits at which the substituted score reaches the Pursue threshold (0.70) on these bounds, with the other
        # substituted inputs of the variant at their values for the deposits assumed (E stays at its cap throughout)
        last = [r for r in srows if r["variant"] == variant and r["bounds"] == bname and r["stage"] == "assumed by the acquirer"][0]
        s_pursue = pr_["S_min"] + 0.70 * (pr_["S_max"] - pr_["S_min"] + 1e-12)
        v_need = last["V_score"] + (s_pursue - last["S_adj"]) / 0.30
        brows.append({"variant": variant, "bounds": bname, "S_adj_at_pursue_threshold": s_pursue, "V_needed": v_need,
                      "deposits_needed_usd_bn": pr_["G_min"] + v_need * (pr_["G_max"] - pr_["G_min"] + 1e-12)})
sst = pd.DataFrame(srows)
assert (sst.E_n > 1 - 1e-9).all() and (sst.relative_size > sst.relative_size_cap).all()  # the relative size stays above its cap
assert (sst[sst.variant == VARIANTS[0]].L_flag == 0).all() and (sst[(sst.variant == VARIANTS[1]) & (sst.in_information_set == 0)].U_rule == 1).all()
sst.to_csv(OUT / "table_svb_deposit_stages.csv", index=False)
pd.DataFrame(brows).to_csv(OUT / "table_svb_deposit_breakeven.csv", index=False)
log("SVB deposit stages done")
# END SVB DEPOSIT STAGES SECTION

# BEGIN BANK-BENCHMARK CO-PRIMARY SECTION (release 4.5)
# The submitted paper used the SPY-adjusted CAR as its primary outcome and the bank-sector benchmark only as a robustness
# check. In the revision the bank-sector outcome (data/Bank_Benchmark_CAR_90.csv, y_bank) is reported as a co-primary
# specification: every analysis reported for the SPY outcome is repeated with the bank-sector labels, with the same
# design and seeds. Partitions are grouped and stratified on the bank labels with the seeds of the SPY analysis, as in
# the bank row of the robustness analysis, which the three core models therefore reproduce exactly (checked below).
# This section runs last, so every earlier result is unchanged.
YB = "y_bank"
yb55 = p55[YB].astype(int).to_numpy()
assert int(yb55.sum()) == 39 and int((yb55 != y55).sum()) == 10
assert (pd.Series(yb55, index=g55).groupby(level=0).nunique() == 1).all()  # one bank-sector label per event cluster

# (1) all eight models and the Spider score; Model 4 policies; cost-ratio sweep; out-of-fold predictions
bmain, bpol, bsweep, boof, bfolds = [], [], [], [], []
nneg_b = int((yb55 == 0).sum())
for r in range(REPEATS):
    folds = make_folds(p55, yb55, 5, SEED0 + r)
    bfolds.append(folds)
    pred, pol, _ = outer_run(p55, YB, folds, MODELS, SEED0 + r, policies=True, score=True)
    for row in metrics(p55, YB, pred, folds):
        bmain.append({"repeat": r, **row})
    for nm, p in pred.items():
        for i, tid in enumerate(p55.transaction_id):
            boof.append({"repeat": r, "model": nm, "transaction_id": tid, "y": int(yb55[i]), "prediction": p[i]})
    pol["Pursue all"] = np.full(55, 2)
    pol["Pursue none"] = np.zeros(55, dtype=int)
    for nm, dec in pol.items():
        pursue = dec == 2
        tp, fp, u = utility(yb55, pursue)
        bpol.append({"repeat": r, "policy": nm, "pursue": int(pursue.sum()), "caution": int((dec == 1).sum()), "TP": tp, "FP": fp,
                     "FPR": fp / nneg_b, "F1": f1_score(yb55, pursue, zero_division=0), "utility_3to1": u})
    psnff = pred[SNFF]
    for ratio in (1, 2, 3, 4, 5):
        thr = ratio / (1 + ratio)
        pursue = psnff >= thr
        tp, fp, u_own = utility(yb55, pursue, ratio)
        trivial = max(0.0, (int(yb55.sum()) - ratio * nneg_b) / 55)
        bsweep.append({"repeat": r, "ratio": ratio, "threshold": thr, "pursue": int(pursue.sum()), "TP": tp, "FP": fp, "FPR": fp / nneg_b,
                       "F1": f1_score(yb55, pursue, zero_division=0), "utility_own": u_own, "gain_vs_trivial": u_own - trivial,
                       "utility_3to1": utility(yb55, pursue, 3)[2]})
    if r % 10 == 9 or QUICK:
        log(f"  bank benchmark: repeat {r + 1}/{REPEATS}")
BM = pd.DataFrame(bmain)
BM.to_csv(OUT / "bank_main_by_repeat.csv", index=False)
summarize(BM).to_csv(OUT / "table_bank_main_comparison.csv", index=False)
rob_bank = pd.read_csv(OUT / "robustness_by_repeat.csv")
rob_bank = rob_bank[rob_bank.outcome == YB].set_index(["repeat", "model"]).AUC.sort_index()
chk = BM[BM.model.isin(list(core) + [SCORE])].set_index(["repeat", "model"]).AUC.sort_index()
assert chk.index.equals(rob_bank.index) and np.allclose(chk.to_numpy(), rob_bank.to_numpy(), atol=1e-12, rtol=0)
BO = pd.DataFrame(boof)
BO.to_csv(OUT / "bank_out_of_fold_predictions.csv", index=False)
rkb = BO.assign(rank=BO.groupby(["repeat", "model"]).prediction.rank(pct=True))
rkb["group"] = np.where(rkb.transaction_id.isin(FBOP), "FBOP subsidiaries (one event, y_bank=1)",
                        np.where(rkb.y == 1, "other positive CAR", "other negative CAR"))
rkb.groupby(["model", "group"])["rank"].mean().unstack().reset_index().to_csv(OUT / "table_bank_rank_by_group.csv", index=False)
BP = pd.DataFrame(bpol)
BP.to_csv(OUT / "bank_decision_policies_by_repeat.csv", index=False)
BP.groupby("policy", sort=False).mean(numeric_only=True).drop(columns="repeat").reset_index().to_csv(
    OUT / "table_bank_decision_policies.csv", index=False)
BSW = pd.DataFrame(bsweep)
BSW.to_csv(OUT / "bank_cost_ratio_sweep_by_repeat.csv", index=False)
BSW.groupby("ratio").mean(numeric_only=True).drop(columns="repeat").reset_index().to_csv(OUT / "table_bank_cost_ratio_sweep.csv", index=False)
cal_b = []
for nm in (LR, RIDGE, SNFF):
    x = BO[BO.model == nm]
    bins = pd.qcut(x.prediction.rank(method="first"), 5, labels=False)
    t = x.groupby(bins).agg(mean_pred=("prediction", "mean"), observed=("y", "mean"), n=("y", "size")).reset_index()
    for _, rr in t.iterrows():
        cal_b.append({"model": nm, "bin": int(rr.iloc[0]) + 1, "mean_prediction": rr.mean_pred, "observed_rate": rr.observed, "n": int(rr.n)})
pd.DataFrame(cal_b).to_csv(OUT / "table_bank_calibration_bins.csv", index=False)
log("bank benchmark: main comparison done")

# (2) paired differences across the same partitions, and the conditional cluster bootstrap (same cluster draws as for SPY)
pwb = BM.pivot_table(index="repeat", columns="model", values=["AUC", "AUC_event", "Brier"])
paired_b = []
for other in (LR, RIDGE, "Random forest", "LR + pairwise interactions", "XGBoost"):
    for met in ("AUC", "AUC_event", "Brier"):
        dlt = pwb[(met, SNFF)] - pwb[(met, other)]
        better = (dlt < 0) if met == "Brier" else (dlt > 0)
        paired_b.append({"comparison": f"SNFF minus {other}", "metric": met, "mean": dlt.mean(), "p05": dlt.quantile(0.05),
                         "p95": dlt.quantile(0.95), "share_SNFF_better": better.mean()})
pd.DataFrame(paired_b).to_csv(OUT / "table_bank_paired_differences.csv", index=False)
avg_b = BO.groupby(["model", "transaction_id"]).prediction.mean().unstack(0).reindex(p55.transaction_id)
rng = np.random.default_rng(20261029)
boot_b = []
for b in range(500 if QUICK else 4000):
    take = np.concatenate([gi[j] for j in rng.integers(0, len(gi), len(gi))])
    yb_ = yb55[take]
    if len(set(yb_)) < 2:
        continue
    boot_b.append({nm: roc_auc_score(yb_, avg_b[nm].to_numpy()[take]) for nm in avg_b.columns})
BB = pd.DataFrame(boot_b)
bbrows = [{"quantity": f"AUC {nm}", "estimate": roc_auc_score(yb55, avg_b[nm]), "ci_low": BB[nm].quantile(0.025),
           "ci_high": BB[nm].quantile(0.975)} for nm in avg_b.columns]
for other in (LR, RIDGE, "LR + pairwise interactions", "Random forest"):
    dd = BB[SNFF] - BB[other]
    bbrows.append({"quantity": f"AUC difference SNFF minus {other}", "estimate": roc_auc_score(yb55, avg_b[SNFF]) - roc_auc_score(yb55, avg_b[other]),
                   "ci_low": dd.quantile(0.025), "ci_high": dd.quantile(0.975)})
pd.DataFrame(bbrows).to_csv(OUT / "table_bank_cluster_bootstrap.csv", index=False)

# (3) permutation test with the complete nested procedure, as for SPY (same partitions and permutation seed), and the
# co-primary summary: two-sided p-values (centred at 0.5) for both benchmarks, Holm-adjusted over the three fitted models
# within each benchmark, and the permutation distribution of Model 3's differences from Models 2 and ridge
obs_b = mean_auc(yb55)
gy_b = pd.Series(yb55, index=g55).groupby(level=0).first().reindex(ug).to_numpy()
rng = np.random.default_rng(7)
null_b = []
for i in range(NPERM):
    null_b.append(mean_auc(rng.permutation(gy_b)[idx]))
    if (i + 1) % 100 == 0 or QUICK and (i + 1) % 10 == 0:
        log(f"  bank permutation {i + 1}/{NPERM}")
NB = pd.DataFrame(null_b)
NB.to_csv(OUT / "bank_permutation_null.csv", index=False)


def holm(pvals: dict) -> dict:
    out, run = {}, 0.0
    for k, (nm, pv) in enumerate(sorted(pvals.items(), key=lambda t: t[1])):
        run = max(run, min(1.0, (len(pvals) - k) * pv))
        out[nm] = run
    return out


cp_rows = []
for bench, ob, nl in (("SPY", obs, N), ("bank-sector index", obs_b, NB)):
    two = {nm: (1 + (np.abs(nl[nm] - 0.5) >= abs(ob[nm] - 0.5)).sum()) / (1 + len(nl)) for nm in ob}
    upper = {nm: (1 + (nl[nm] >= ob[nm]).sum()) / (1 + len(nl)) for nm in ob}
    h_two = holm({nm: two[nm] for nm in (LR, RIDGE, SNFF)})
    h_up = holm({nm: upper[nm] for nm in (LR, RIDGE, SNFF)})
    for nm in ob:
        cp_rows.append({"benchmark": bench, "model": nm, "observed_mean_AUC": ob[nm], "null_mean": nl[nm].mean(),
                        "null_p025": nl[nm].quantile(0.025), "null_p975": nl[nm].quantile(0.975), "p_one_sided_upper": upper[nm],
                        "p_holm_one_sided_upper": h_up.get(nm, np.nan), "p_two_sided": two[nm], "p_holm_two_sided": h_two.get(nm, np.nan)})
    for other in (LR, RIDGE):
        d_obs, d_null = ob[SNFF] - ob[other], nl[SNFF] - nl[other]
        cp_rows.append({"benchmark": bench, "model": f"SNFF minus {other}", "observed_mean_AUC": d_obs, "null_mean": d_null.mean(),
                        "null_p025": d_null.quantile(0.025), "null_p975": d_null.quantile(0.975),
                        "p_two_sided": (1 + (np.abs(d_null) >= abs(d_obs)).sum()) / (1 + len(d_null))})
pd.DataFrame(cp_rows).to_csv(OUT / "table_permutation_coprimary.csv", index=False)
log("bank benchmark: permutation test done")

# (4) refitting cluster bootstrap, as for SPY (same cluster draws and partition seeds)
rng = np.random.default_rng(20261030)
rbb_rows, bboot_skipped = [], 0
for b in range(NBOOT):
    take = np.concatenate([gi[j] for j in rng.integers(0, len(gi), len(gi))])
    d_b = p55.iloc[take].reset_index(drop=True)
    y_b = d_b[YB].astype(int).to_numpy()
    try:
        pred_b, _, _ = outer_run(d_b, YB, make_folds(d_b, y_b, 5, SEED0 + 3000 + b), boot_models, SEED0 + 3000 + b)
    except (AssertionError, ValueError):
        bboot_skipped += 1
        continue
    a = {nm: roc_auc_score(y_b, pv) for nm, pv in pred_b.items()}
    rbb_rows.append({"replicate": b, **{f"AUC {nm}": v for nm, v in a.items()},
                     f"diff SNFF minus {RIDGE}": a[SNFF] - a[RIDGE], f"diff SNFF minus {LR}": a[SNFF] - a[LR]})
    if (b + 1) % 100 == 0 or QUICK and (b + 1) % 10 == 0:
        log(f"  bank refitting bootstrap {b + 1}/{NBOOT}")
RBB = pd.DataFrame(rbb_rows)
RBB.to_csv(OUT / "bank_bootstrap_refit_by_replicate.csv", index=False)
pd.DataFrame([{"quantity": c, "mean": RBB[c].mean(), "ci_low": RBB[c].quantile(0.025), "ci_high": RBB[c].quantile(0.975),
               "share_below_zero": (RBB[c] < 0).mean() if c.startswith("diff") else np.nan, "replicates": len(RBB), "skipped": bboot_skipped}
              for c in RBB.columns if c != "replicate"]).to_csv(OUT / "table_bank_bootstrap_refit.csv", index=False)

# (5) the FBOP cluster under both benchmarks: the three core models and the Spider score without it (51 transactions,
# 50 clusters; partitions re-drawn with the same seeds), and where each model ranks it (mean percentile rank)
d51 = p55[~p55.transaction_id.isin(FBOP)].reset_index(drop=True)
fb_rows = []
for oc, full in (("y", M), (YB, BM)):
    for _, row in full[full.model.isin(list(core) + [SCORE])].iterrows():
        fb_rows.append({"outcome": oc, "sample": "all 55 transactions", "repeat": int(row["repeat"]), "model": row["model"], "AUC": row["AUC"]})
    y51_ = d51[oc].astype(int).to_numpy()
    for r in range(REPEATS):
        pred, _, _ = outer_run(d51, oc, make_folds(d51, y51_, 5, SEED0 + r), core, SEED0 + r, score=True)
        for nm, p in pred.items():
            fb_rows.append({"outcome": oc, "sample": "without the FBOP cluster", "repeat": r, "model": nm, "AUC": roc_auc_score(y51_, p)})
FBI = pd.DataFrame(fb_rows)
FBI.to_csv(OUT / "fbop_influence_by_repeat.csv", index=False)
fsum = FBI.groupby(["outcome", "sample", "model"], sort=False).AUC.agg(AUC_mean="mean", AUC_p05=lambda s: s.quantile(0.05),
                                                                      AUC_p95=lambda s: s.quantile(0.95)).reset_index()
rk_spy = rk[rk.transaction_id.isin(FBOP)].groupby("model")["rank"].mean()
rk_bank = rkb[rkb.transaction_id.isin(FBOP)].groupby("model")["rank"].mean()
fsum["fbop_mean_percentile_rank"] = [(rk_spy if o == "y" else rk_bank).get(m, np.nan) if s == "all 55 transactions" else np.nan
                                     for o, s, m in zip(fsum.outcome, fsum["sample"], fsum.model)]
fsum.to_csv(OUT / "table_fbop_influence.csv", index=False)
log("bank benchmark: bootstrap and FBOP influence done")

# (6) robustness variants, the ablation and the broader panel with the bank-sector labels
rbk_rows = []
for label, opts in (("Published call-report inputs only", {"public_only": True}), ("Broad support definition", {"h_col": "H_support_broad"}),
                    ("U rule requires support (broad)", {"h_col": "H_support_broad", "u_requires_h": True}), ("Z rule removed", {"z_removed": True})):
    for r in range(REPEATS):
        pred, _, _ = outer_run(p55, YB, bfolds[r], core, SEED0 + r, opts=opts, score=True)
        for row in metrics(p55, YB, pred, bfolds[r]):
            rbk_rows.append({"variant": label, "outcome": YB, "positives": int(yb55.sum()), "repeat": r, **row})
RBK = pd.DataFrame(rbk_rows)
RBK.to_csv(OUT / "bank_robustness_by_repeat.csv", index=False)
summarize(RBK, keys=("variant", "outcome", "positives", "model")).to_csv(OUT / "table_bank_robustness.csv", index=False)
abl_b = []
for r in range(REPEATS):
    pred, _, _ = outer_run(p55, YB, bfolds[r], abl_models, SEED0 + r)
    for row in metrics(p55, YB, pred, bfolds[r]):
        abl_b.append({"repeat": r, **row})
AB = pd.DataFrame(abl_b)
AB.to_csv(OUT / "bank_ablation_by_repeat.csv", index=False)
summarize(AB).to_csv(OUT / "table_bank_ablation.csv", index=False)
yb90 = b90[YB].astype(int).to_numpy()
br_b = []
for r in range(REPEATS):
    folds = make_folds(b90, yb90, 5, SEED0 + 100 + r)
    pred, _, _ = outer_run(b90, YB, folds, MODELS, SEED0 + 100 + r, score=True)
    for row in metrics(b90, YB, pred, folds):
        br_b.append({"repeat": r, **row})
BRB = pd.DataFrame(br_b)
BRB.to_csv(OUT / "bank_broader90_by_repeat.csv", index=False)
summarize(BRB).to_csv(OUT / "table_bank_broader90.csv", index=False)
log("bank benchmark: robustness, ablation and broader panel done")

# (7) acquisition events with the bank-sector labels (every bank of an event shares the event's return)
bank_by_tid = pd.concat([p55, b90]).drop_duplicates("transaction_id").set_index("transaction_id")[YB].astype(int)
evb = []
for ids in ev51.member_transaction_ids:
    labs = {int(bank_by_tid[t]) for t in str(ids).split(";") if t in bank_by_tid.index}
    assert len(labs) == 1, ids
    evb.append(labs.pop())
ev51[YB] = evb
yb51 = ev51[YB].to_numpy()
evb_rows, evbpol_rows = [], []
for r in range(REPEATS):
    folds = make_folds(ev51, yb51, 5, SEED0 + r)
    pred, pol, _ = outer_run(ev51, YB, folds, MODELS, SEED0 + r, policies=True, score=True)
    for row in metrics(ev51, YB, pred, folds):
        evb_rows.append({"repeat": r, **row})
    pol["Pursue all"] = np.full(51, 2)
    pol["Pursue none"] = np.zeros(51, dtype=int)
    for nm, dec in pol.items():
        pursue = dec == 2
        tp, fp, u = utility(yb51, pursue)
        evbpol_rows.append({"repeat": r, "policy": nm, "pursue": int(pursue.sum()), "caution": int((dec == 1).sum()), "TP": tp, "FP": fp,
                            "FPR": fp / int((yb51 == 0).sum()), "F1": f1_score(yb51, pursue, zero_division=0), "utility_3to1": u})
EVB = pd.DataFrame(evb_rows)
EVB.to_csv(OUT / "bank_event_level_by_repeat.csv", index=False)
summarize(EVB).to_csv(OUT / "table_bank_event_level.csv", index=False)
EVBP = pd.DataFrame(evbpol_rows)
EVBP.to_csv(OUT / "bank_event_level_decision_policies_by_repeat.csv", index=False)
EVBP.groupby("policy", sort=False).mean(numeric_only=True).drop(columns="repeat").reset_index().to_csv(
    OUT / "table_bank_event_level_decision_policies.csv", index=False)

# (8) the Spider components against the bank-sector labels (55 and the 28); the Risk row takes the AUC and p-value of the
# risk-direction validation for the same sample and outcome, so the two tables report one number
rv_b = pd.DataFrame(rv_rows).set_index(["deals", "outcome"])
BANK_OUTCOME = "Reaction-day CAR[-1,+1], bank-index benchmark"
comp_b = []
rng = np.random.default_rng(13)
for nm, d in SETS:
    if nm.startswith("35"):
        continue
    f = sp55.transform(d)
    g = groups(d)
    u = pd.unique(g)
    gyy = pd.Series(d[YB].astype(int).to_numpy(), index=g).groupby(level=0).first().reindex(u).to_numpy()
    ix = np.array([np.flatnonzero(u == x)[0] for x in g])
    for c, sign in (("S_final", "+"), ("V_score", "+"), ("P_score", "+"), ("B_score", "+"), ("R_score", "-"), ("E_score", "-")):
        x = f[c].to_numpy(float)
        if c == "R_score":
            a, pv = rv_b.loc[(nm, BANK_OUTCOME), "AUC_R"], rv_b.loc[(nm, BANK_OUTCOME), "p_AUC"]
            assert abs(a - roc_auc_score(d[YB].astype(int), x)) < 1e-12
        else:
            a = roc_auc_score(d[YB].astype(int), x)
            nul = np.array([roc_auc_score(rng.permutation(gyy)[ix], x) for _ in range(2000 if QUICK else 10000)])
            pv = (1 + (np.abs(nul - 0.5) >= abs(a - 0.5)).sum()) / (1 + len(nul))
        comp_b.append({"deals": nm, "component": c, "sign_in_S": sign, "AUC": a, "p_two_sided": pv})
pd.DataFrame(comp_b).to_csv(OUT / "table_bank_spider_components.csv", index=False)
log("bank benchmark: events and components done")
# END BANK-BENCHMARK CO-PRIMARY SECTION

# ============================================================ manifest
def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


import sklearn  # noqa: E402
import xgboost  # noqa: E402

manifest = {
    "date": "2026-10-30", "quick": QUICK, "repeats": REPEATS, "outer_folds": 5, "inner_folds": 3, "permutations": NPERM,
    "permutation_repeats": PERM_REPEATS, "permutation_tuning": "complete nested procedure rerun on every permutation",
    "bootstrap_refit_replicates": NBOOT, "bootstrap_refit_skipped": boot_skipped, "seed_base": SEED0, "event_groups_primary": int(len(ug)), "event_groups_broader": int(len(set(groups(b90)))),
    "acquisition_events_primary": {"events": int(len(ev51)), "banks": int(ev51.n_banks.sum()), "positive": int(ev51.y.sum()),
                                   "multi_bank_events": int((ev51.n_banks > 1).sum())},
    "modal_tuned_C": {k: float(v) for k, v in modal.items()}, "sample": sample, "shap": shap_info,
    "inputs_sha256": {p.name: sha(p) for p in [FW / "data/SNFF_Revised_Inputs_Primary55.csv", FW / "data/SNFF_Revised_Inputs_Broader90.csv",
                                               FW / "data/Source_Verification_Ledger_90.csv", FW / "data/Event_Convention_Comparison_90.csv",
                                               FW / "data/SNFF_Event_Inputs_Primary51.csv", FW / "data/SNFF_Event_Consolidations.csv",
                                               FW / "data/SVB_Deposit_Stages.csv",
                                               FW / "code/snff_revised_features.py", BANK_CSV, Path(__file__).resolve()]},
    "versions": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "scikit-learn": sklearn.__version__,
                 "xgboost": xgboost.__version__, "scipy": __import__("scipy").__version__, "matplotlib": matplotlib.__version__,
                 "shap": shap_info.get("shap_version")},
    "runtime_seconds": round(time.time() - T0),
}
(OUT / "RUN_MANIFEST.json").write_text(json.dumps(manifest, indent=2))
log("DONE")
