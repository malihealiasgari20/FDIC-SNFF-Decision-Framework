"""Sensitivity of the Spider score and of Model 3 to the expert weights and interaction adjustments (release 4.6).

The reference is the paper's specification, unchanged:
    S  = 0.30 V + 0.20 P + 0.20 B - 0.20 R - 0.10 E
    S* = S + 0.08 Q + 0.07 U - 0.10 Z - 0.06 K, rescaled to [0, 1] on the training fold.
No constant is chosen on the full sample. Every variant is evaluated with the design of the main comparison: for each
benchmark (SPY-adjusted CAR, y; bank-sector CAR, y_bank) the same 50 grouped partitions, stratified on that benchmark's
labels (seeds 5000 + r), with Model 3's inner tuning unchanged. The variants were fixed before they were run:

* one at a time: each component weight times 0.5 or 1.5, the five then rescaled so that they again sum to one (so the
  adjustments keep their size relative to S); each adjustment times 0, 0.5 or 1.5;
* equal component weights (0.20 each); no adjustments; both;
* 1,000 random draws within +/-50% of every constant: each component weight times an independent U(0.5, 1.5) factor, the
  five rescaled to sum to one, and each adjustment times an independent U(0.5, 1.5) factor (seed 20261124);
* 1,000 random sign-preserving draws over the whole range: component weights uniform on the simplex (Dirichlet(1, ..., 1))
  and each adjustment between zero and twice its value (seed 20261125);
* weights chosen from data inside each training fold: the draw of either set (or the reference) with the highest
  training-fold AUC scores the held-out fold. This is the only data-driven choice of constants, and because it uses no
  held-out outcome its pooled out-of-fold AUC estimates what constants fitted to the data would achieve. A permutation
  test reruns the whole choice on 400 cluster permutations of the outcomes with the draws and partition seeds of the
  main permutation test (seeds 7 and 5900-5902), whose Spider-score null it reproduces exactly.

The Spider score (Model 1) and Configuration 4A, which depend only on the constants, are evaluated for every variant. The
components and rule indicators do not depend on the constants, so they are computed once per fold and the score of every
variant is formed from them with the operations of RevisedSpider, in the same order. Model 3, which uses the score as a
feature, is refitted (inner tuning included) for the reference, the one-at-a-time and structural variants and the first 100
draws of each random set, together with Configurations 4B and 4C. Model 2 and ridge regression do not use the constants;
their per-partition AUCs are read from the released results. The reference must reproduce the released Spider-score,
Model 3 and policy results of both benchmarks exactly, or the script stops.

usage: python3 -I weight_sensitivity.py <research_folder> <results_dir> [--quick]
"""
from __future__ import annotations

import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, f1_score, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*did not converge.*")

ROOT, RES = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
FW = ROOT / "03_revised_framework_2026-10-29"
sys.path.insert(0, str(FW / "code"))
from snff_revised_features import W_COMPONENT, W_RULE, RevisedSpider, raw_inputs  # noqa: E402

QUICK = "--quick" in sys.argv                       # a test run: 3 partitions, 50 draws per set, 2 for Model 3, 20 permutations
REPEATS, SEED0, NDRAW, NDRAW_M3, NPERM = (3, 5000, 50, 2, 20) if QUICK else (50, 5000, 1000, 100, 400)
GRID = [0.1, 1.0, 10.0]
COMP = ["V_score", "P_score", "B_score", "R_score", "E_score", "Q_rule", "U_rule", "Z_rule", "K_rule"]
CONST = ["wV", "wP", "wB", "wR", "wE", "cQ", "cU", "cZ", "cK"]
REF = np.array([W_COMPONENT["V"], W_COMPONENT["P"], W_COMPONENT["B"], W_COMPONENT["R"], W_COMPONENT["E"],
                W_RULE["Q"], W_RULE["U"], W_RULE["Z"], W_RULE["K"]])
assert np.array_equal(REF, [0.30, 0.20, 0.20, 0.20, 0.10, 0.08, 0.07, -0.10, -0.06])
BENCH = {"y": "SPY", "y_bank": "bank-sector index"}
M3, LR, RIDGE, SCORE = "SNFF + LR (Model 3)", "Logistic regression (L2, C=1)", "Ridge logistic", "Spider score alone (Model 1)"
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.0f}s] {msg}", flush=True)


def rd(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, float_precision="round_trip")


# ---------------------------------------------------------------- data (as in final_analysis.py)
p55 = pd.read_csv(FW / "data/SNFF_Revised_Inputs_Primary55.csv")
bank = pd.read_csv(ROOT / "05_manuscript_analysis_2026-10-29/data/Bank_Benchmark_CAR_90.csv").set_index("transaction_id")
p55["y_bank"] = p55.transaction_id.map(bank.y_reaction_m1p1_bank).astype(int)
assert len(p55) == 55 and int(p55.y.sum()) == 35 and int(p55.y_bank.sum()) == 39
RAW = raw_inputs(p55).to_numpy(float)  # the eight measured inputs, in the column order of the main analysis
N = len(p55)


def groups(d: pd.DataFrame) -> np.ndarray:
    return (d.listed_parent_ticker.astype(str) + "|" + d.first_reaction_date.astype(str)).to_numpy()


def make_folds(d: pd.DataFrame, y: np.ndarray, k: int, seed: int):
    sk = StratifiedGroupKFold(n_splits=k, shuffle=True, random_state=seed)
    return list(sk.split(np.zeros(len(d)), y, groups(d)))


def components(tr: pd.DataFrame, te: pd.DataFrame):
    sp = RevisedSpider().fit(tr)
    fa, fb = sp.transform(tr), sp.transform(te)
    return fa[COMP].to_numpy(float), fb[COMP].to_numpy(float), fb.S_final.to_numpy()


def s_adj(comp: np.ndarray, W: np.ndarray) -> np.ndarray:
    """S* before rescaling for every row of W (m x 9) and every row of comp (n x 9): m x n. Same operations and order
    as RevisedSpider (S_raw, then the four adjustments; Z and K carry negative constants)."""
    V, P, B, R, E, Q, U, Z, K = (comp[:, j][None, :] for j in range(9))
    w = [W[:, j][:, None] for j in range(9)]
    s_raw = w[0] * V + w[1] * P + w[2] * B - w[3] * R - w[4] * E
    return s_raw + w[5] * Q + w[6] * U + w[7] * Z + w[8] * K


def s_final(ca: np.ndarray, cb: np.ndarray, W: np.ndarray):
    sa, sb = s_adj(ca, W), s_adj(cb, W)
    lo, hi = sa.min(axis=1, keepdims=True), sa.max(axis=1, keepdims=True)
    return np.clip((sa - lo) / (hi - lo + 1e-12), 0, 1), np.clip((sb - lo) / (hi - lo + 1e-12), 0, 1)


def auc2(scores: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Twice the Mann-Whitney U of each row (ties count one half), as exact integers."""
    r2 = np.rint(2 * rankdata(scores, axis=1, method="average")).astype(np.int64)
    npos = int(y.sum())
    return r2[:, y == 1].sum(axis=1) - npos * (npos + 1)


def auc_rows(scores: np.ndarray, y: np.ndarray) -> np.ndarray:
    npos, nneg = int(y.sum()), int((y == 0).sum())
    return auc2(scores, y) / (2 * npos * nneg)


# ---------------------------------------------------------------- variants
rows = [("reference", "expert weights (reference)", REF.copy())]
for j, nm in enumerate("VPBRE"):
    for fct in (0.5, 1.5):
        w = REF.copy()
        w[j] *= fct
        w[:5] = w[:5] / w[:5].sum()
        rows.append(("one_at_a_time", f"weight of {nm} x {fct:g}", w))
for j, nm in enumerate("QUZK"):
    for fct in (0.0, 0.5, 1.5):
        w = REF.copy()
        w[5 + j] *= fct
        rows.append(("one_at_a_time", f"adjustment {nm} x {fct:g}", w))
eq = REF.copy()
eq[:5] = 0.20
nadj = REF.copy()
nadj[5:] = 0.0
both = eq.copy()
both[5:] = 0.0
rows += [("structural", "equal component weights", eq), ("structural", "no interaction adjustments", nadj),
         ("structural", "equal weights, no adjustments", both)]
rng = np.random.default_rng(20261124)
fl, gl = rng.uniform(0.5, 1.5, size=(NDRAW, 5)), rng.uniform(0.5, 1.5, size=(NDRAW, 4))
for i in range(NDRAW):
    w = REF.copy()
    w[:5] = REF[:5] * fl[i]
    w[:5] = w[:5] / w[:5].sum()
    w[5:] = REF[5:] * gl[i]
    rows.append(("random_local", f"+/-50% draw {i}", w))
rng = np.random.default_rng(20261125)
dw, gw = rng.dirichlet(np.ones(5), size=NDRAW), rng.uniform(0.0, 2.0, size=(NDRAW, 4))
for i in range(NDRAW):
    w = REF.copy()
    w[:5] = dw[i]
    w[5:] = REF[5:] * gw[i]
    rows.append(("random_wide", f"sign-preserving draw {i}", w))
VAR = pd.DataFrame([{"variant_id": k, "family": f, "label": lab, **dict(zip(CONST, w))} for k, (f, lab, w) in enumerate(rows)])
W_ALL = VAR[CONST].to_numpy(float)
assert np.array_equal(W_ALL[0], REF)
assert (W_ALL[:, :5] >= 0).all() and (W_ALL[:, [5, 6]] >= 0).all() and (W_ALL[:, [7, 8]] <= 0).all()  # signs kept
fam = VAR.family.to_numpy()
M3_IDS = (list(VAR.index[np.isin(fam, ["reference", "one_at_a_time", "structural"])]) + list(VAR.index[fam == "random_local"][:NDRAW_M3])
          + list(VAR.index[fam == "random_wide"][:NDRAW_M3]))
VAR["model3"] = VAR.index.isin(M3_IDS)
VAR.to_csv(RES / "weight_sensitivity_variants.csv", index=False)
log(f"{len(VAR)} variants ({(fam == 'one_at_a_time').sum()} one at a time, {(fam == 'structural').sum()} structural, "
    f"{NDRAW} +/-50%, {NDRAW} sign-preserving); Model 3 refitted for {len(M3_IDS)}")

# ---------------------------------------------------------------- folds, components (once per fold), released results
rel_main = {"y": rd(RES / "main_by_repeat.csv"), "y_bank": rd(RES / "bank_main_by_repeat.csv")}
rel_pol = {"y": rd(RES / "decision_policies_by_repeat.csv"), "y_bank": rd(RES / "bank_decision_policies_by_repeat.csv")}
CACHE = {}
for ycol in BENCH:
    y = p55[ycol].to_numpy()
    for r in range(REPEATS):
        fl_ = []
        for k, (it, iv) in enumerate(make_folds(p55, y, 5, SEED0 + r)):
            tr, te = p55.iloc[it], p55.iloc[iv]
            assert not set(groups(tr)) & set(groups(te))
            ca, cb, ref_te = components(tr, te)
            inner = []
            for jt, jv in make_folds(tr, y[it], 3, (SEED0 + r) * 31 + k):
                ia, ib, _ = components(tr.iloc[jt], tr.iloc[jv])
                inner.append((jt, jv, ia, ib))
            fl_.append({"it": it, "iv": iv, "ca": ca, "cb": cb, "ref_te": ref_te, "inner": inner})
        CACHE[(ycol, r)] = fl_
log(f"components cached for 2 x {REPEATS} partitions")

# ---------------------------------------------------------------- the Spider score and 4A for every variant
spider_rows = []
for ycol in BENCH:
    y = p55[ycol].to_numpy()
    aucs = np.zeros((len(VAR), REPEATS))
    u4a, n4a = np.zeros((len(VAR), REPEATS)), np.zeros((len(VAR), REPEATS))
    for r in range(REPEATS):
        oof = np.zeros((len(VAR), N))
        for f in CACHE[(ycol, r)]:
            _, zb = s_final(f["ca"], f["cb"], W_ALL)
            assert np.array_equal(zb[0], f["ref_te"]), "reference score differs from RevisedSpider"
            oof[:, f["iv"]] = zb
        aucs[:, r] = auc_rows(oof, y)
        pursue = oof >= 0.70
        tp, fp = (pursue & (y == 1)).sum(axis=1), (pursue & (y == 0)).sum(axis=1)
        u4a[:, r], n4a[:, r] = (tp - 3.0 * fp) / N, pursue.sum(axis=1)
        rm = rel_main[ycol]
        rel_auc = float(rm[(rm.repeat == r) & (rm.model == SCORE)].AUC.iloc[0])
        assert roc_auc_score(y, oof[0]) == rel_auc and abs(aucs[0, r] - rel_auc) < 1e-12, (ycol, r)
        rp = rel_pol[ycol]
        rel_u = float(rp[(rp.repeat == r) & (rp.policy == "4A: fixed Spider thresholds")].utility_3to1.iloc[0])
        assert abs(u4a[0, r] - rel_u) < 1e-12, (ycol, r, "4A")
    for v in range(len(VAR)):
        spider_rows.append({"variant_id": v, "benchmark": BENCH[ycol], "AUC_mean": aucs[v].mean(), "AUC_p05": np.quantile(aucs[v], 0.05),
                            "AUC_p95": np.quantile(aucs[v], 0.95), "share_partitions_above_half": float((aucs[v] > 0.5).mean()),
                            "utility_4A_mean": u4a[v].mean(), "pursue_4A_mean": n4a[v].mean()})
    log(f"Spider score: {BENCH[ycol]} done; the reference reproduces the released score and 4A in all {REPEATS} partitions")
SP = pd.DataFrame(spider_rows)
SP.to_csv(RES / "weight_sensitivity_spider.csv", index=False)

# ---------------------------------------------------------------- constants chosen inside each training fold
nested_rows, choice_rows = [], []
for ycol in BENCH:
    y = p55[ycol].to_numpy()
    for family in ("random_local", "random_wide"):
        cand = np.r_[0, np.flatnonzero(fam == family)]      # the reference first, so it wins ties
        Wc = W_ALL[cand]
        for r in range(REPEATS):
            oof, tr_auc, picks = np.zeros(N), [], []
            for k, f in enumerate(CACHE[(ycol, r)]):
                za, zb = s_final(f["ca"], f["cb"], Wc)
                ytr = y[f["it"]]
                a2 = auc2(za, ytr)
                b = int(np.argmax(a2))                          # first maximum
                oof[f["iv"]] = zb[b]
                tr_auc.append(a2[b] / (2 * int(ytr.sum()) * int((ytr == 0).sum())))
                picks.append(int(cand[b]))
                choice_rows.append({"benchmark": BENCH[ycol], "family": family, "repeat": r, "fold": k, "variant_id": int(cand[b]),
                                    "training_AUC": tr_auc[-1]})
            nested_rows.append({"benchmark": BENCH[ycol], "family": family, "repeat": r, "AUC": roc_auc_score(y, oof),
                                "training_AUC_mean": float(np.mean(tr_auc)), "folds_choosing_reference": int(sum(p == 0 for p in picks))})
    log(f"constants chosen within training folds: {BENCH[ycol]} done")
NE = pd.DataFrame(nested_rows)
NE.to_csv(RES / "weight_sensitivity_nested_by_repeat.csv", index=False)
pd.DataFrame(choice_rows).to_csv(RES / "weight_sensitivity_nested_choices.csv", index=False)

# ---------------------------------------------------------------- permutation test of the constants chosen in training folds
PERM_SEEDS = [SEED0 + 900 + r for r in range(3)]
g55 = groups(p55)
ug = pd.unique(g55)
idx = np.array([np.flatnonzero(ug == x)[0] for x in g55])
CAND = {family: np.r_[0, np.flatnonzero(fam == family)] for family in ("random_local", "random_wide")}


def nested_mean_auc(yv: np.ndarray) -> dict:
    """Mean AUC over the three partitions of the main permutation test: the expert weights and the constants chosen in
    each training fold from either set."""
    acc = {"reference": [], "random_local": [], "random_wide": []}
    for sd in PERM_SEEDS:
        oof = {key: np.zeros(N) for key in acc}
        for it, iv in make_folds(p55, yv, 5, sd):
            assert len(set(yv[it])) == 2
            ca, cb, ref_te = components(p55.iloc[it], p55.iloc[iv])
            oof["reference"][iv] = ref_te
            for family, cand in CAND.items():
                za, zb = s_final(ca, cb, W_ALL[cand])
                oof[family][iv] = zb[int(np.argmax(auc2(za, yv[it])))]
        for key in acc:
            acc[key].append(roc_auc_score(yv, oof[key]))
    return {key: float(np.mean(v)) for key, v in acc.items()}


perm_rows, null_rows = [], []
rel_perm = rd(RES / "table_permutation_coprimary.csv")
for ycol in BENCH:
    y = p55[ycol].to_numpy()
    obs = nested_mean_auc(y)
    assert obs["reference"] == float(rel_perm[(rel_perm.benchmark == BENCH[ycol]) & (rel_perm.model == SCORE)].observed_mean_AUC.iloc[0])
    gy = pd.Series(y, index=g55).groupby(level=0).first().reindex(ug).to_numpy()
    rng = np.random.default_rng(7)
    null = pd.DataFrame([nested_mean_auc(rng.permutation(gy)[idx]) for _ in range(NPERM)])
    released = rd(RES / ("permutation_null.csv" if ycol == "y" else "bank_permutation_null.csv"))[SCORE].to_numpy()[:NPERM]
    assert np.array_equal(null.reference.to_numpy(), released), "the permutations differ from the main permutation test"
    for i, row in null.iterrows():
        null_rows.append({"benchmark": BENCH[ycol], "permutation": i, **row.to_dict()})
    for key in ("reference", "random_local", "random_wide"):
        x = null[key]
        perm_rows.append({"benchmark": BENCH[ycol], "constants": key, "observed_mean_AUC": obs[key], "null_mean": x.mean(),
                          "null_p025": x.quantile(0.025), "null_p975": x.quantile(0.975),
                          "p_one_sided_upper": (1 + (x >= obs[key]).sum()) / (1 + len(x)),
                          "p_two_sided": (1 + (np.abs(x - 0.5) >= abs(obs[key] - 0.5)).sum()) / (1 + len(x))})
    log(f"permutation test of the constants chosen in training folds: {BENCH[ycol]} done (the reference reproduces the released null)")
pd.DataFrame(null_rows).to_csv(RES / "weight_sensitivity_permutation_null.csv", index=False)
pd.DataFrame(perm_rows).to_csv(RES / "table_weight_sensitivity_permutation.csv", index=False)


# ---------------------------------------------------------------- Model 3 (refitted, inner tuning included) and 4B, 4C
def design(raw: np.ndarray, zf: np.ndarray, comp: np.ndarray) -> np.ndarray:
    """The measured inputs, S_final, Q, U, Z, K: the columns of the main analysis, in column-major order like the array
    pandas passes to scikit-learn there, so the linear algebra runs in the same order."""
    return np.asfortranarray(np.column_stack([raw, zf, comp[:, 5:9]]))


def model3_partition(ycol: str, r: int, w: np.ndarray):
    y = p55[ycol].to_numpy()
    W = w[None, :]
    pred, d4 = np.full(N, np.nan), {k: np.zeros(N, dtype=bool) for k in ("4A", "4B", "4C")}
    for k, f in enumerate(CACHE[(ycol, r)]):
        it, iv = f["it"], f["iv"]
        ytr = y[it]
        mats = []
        for jt, jv, ia, ib in f["inner"]:
            za, zb = s_final(ia, ib, W)
            xa, xb = design(RAW[it][jt], za[0], ia), design(RAW[it][jv], zb[0], ib)
            s = StandardScaler().fit(xa)
            mats.append((s.transform(xa), s.transform(xb), jt, jv))
        best = None
        for c in GRID:
            ioof = np.full(len(it), np.nan)
            for xa, xb, jt, jv in mats:
                ioof[jv] = LogisticRegression(C=c, max_iter=5000).fit(xa, ytr[jt]).predict_proba(xb)[:, 1]
            bs = np.mean([brier_score_loss(ytr[jv], ioof[jv]) for _, _, _, jv in mats])
            if best is None or bs < best[0] - 1e-12:
                best = (bs, c, ioof)
        za, zb = s_final(f["ca"], f["cb"], W)
        xa, xb = design(RAW[it], za[0], f["ca"]), design(RAW[iv], zb[0], f["cb"])
        s = StandardScaler().fit(xa)
        pred[iv] = LogisticRegression(C=best[1], max_iter=5000).fit(s.transform(xa), ytr).predict_proba(s.transform(xb))[:, 1]
        thr = [round(t, 2) for t in np.arange(0.55, 0.8001, 0.05)]
        t_best = sorted([(f1_score(ytr, best[2] >= t, zero_division=0), t) for t in thr], key=lambda z: (-z[0], -z[1]))[0][1]
        d4["4A"][iv], d4["4B"][iv], d4["4C"][iv] = zb[0] >= 0.70, pred[iv] >= t_best, pred[iv] >= 0.75
    assert np.isfinite(pred).all()
    util = {k: ((v & (y == 1)).sum() - 3.0 * (v & (y == 0)).sum()) / N for k, v in d4.items()}
    return pred, util


m3_rows = []
for ycol in BENCH:
    y = p55[ycol].to_numpy()
    rm, rp = rel_main[ycol], rel_pol[ycol]
    base = {m: rm[rm.model == m].set_index("repeat").AUC for m in (LR, RIDGE)}
    for n_done, v in enumerate(M3_IDS):
        for r in range(REPEATS):
            pred, util = model3_partition(ycol, r, W_ALL[v])
            a, bsc = roc_auc_score(y, pred), brier_score_loss(y, pred)
            if v == 0:
                rel = rm[(rm.repeat == r) & (rm.model == M3)].iloc[0]
                assert a == float(rel.AUC) and bsc == float(rel.Brier), (ycol, r, "Model 3")
                for key, pol in (("4A", "4A: fixed Spider thresholds"), ("4B", "4B: F1-tuned threshold"), ("4C", "4C: cost-based threshold (3:1)")):
                    assert abs(util[key] - float(rp[(rp.repeat == r) & (rp.policy == pol)].utility_3to1.iloc[0])) < 1e-12, (ycol, r, key)
            m3_rows.append({"variant_id": v, "benchmark": BENCH[ycol], "repeat": r, "AUC": a, "Brier": bsc,
                            "AUC_Model2": float(base[LR][r]), "AUC_ridge": float(base[RIDGE][r]),
                            "utility_4A": util["4A"], "utility_4B": util["4B"], "utility_4C": util["4C"]})
        if n_done == 0:
            log(f"Model 3, {BENCH[ycol]}: the reference reproduces the released Model 3, 4A, 4B and 4C in all {REPEATS} partitions")
        elif n_done % 10 == 9:
            log(f"  Model 3, {BENCH[ycol]}: {n_done + 1}/{len(M3_IDS)} variants")
M3R = pd.DataFrame(m3_rows)
M3R.to_csv(RES / "weight_sensitivity_model3_by_repeat.csv", index=False)
M3R["d_Model2"], M3R["d_ridge"] = M3R.AUC - M3R.AUC_Model2, M3R.AUC - M3R.AUC_ridge
M3S = M3R.groupby(["variant_id", "benchmark"], sort=False).agg(
    AUC_mean=("AUC", "mean"), Brier_mean=("Brier", "mean"), diff_Model2_mean=("d_Model2", "mean"), diff_ridge_mean=("d_ridge", "mean"),
    share_above_Model2=("d_Model2", lambda x: float((x > 0).mean())), share_above_ridge=("d_ridge", lambda x: float((x > 0).mean())),
    utility_4B_mean=("utility_4B", "mean"), utility_4C_mean=("utility_4C", "mean")).reset_index()
M3S.to_csv(RES / "weight_sensitivity_model3.csv", index=False)

# ---------------------------------------------------------------- summary table
summ = []
SPv = SP.merge(VAR[["variant_id", "family", "label"]], on="variant_id")
M3v = M3S.merge(VAR[["variant_id", "family", "label"]], on="variant_id")
for bench in BENCH.values():
    sp, m3 = SPv[SPv.benchmark == bench], M3v[M3v.benchmark == bench]
    for fam_, lab in (("reference", "expert weights (reference)"), ("one_at_a_time", "one constant changed (22 variants)"),
                      ("structural", "equal weights / no adjustments (3 variants)"), ("random_local", "random within +/-50%"),
                      ("random_wide", "random, sign-preserving")):
        a, b = sp[sp.family == fam_], m3[m3.family == fam_]
        row = {"benchmark": bench, "set": lab, "n_spider": len(a), "spider_AUC_median": a.AUC_mean.median(), "spider_AUC_min": a.AUC_mean.min(),
               "spider_AUC_p05": a.AUC_mean.quantile(0.05), "spider_AUC_p95": a.AUC_mean.quantile(0.95), "spider_AUC_max": a.AUC_mean.max(),
               "spider_share_above_half": float((a.AUC_mean > 0.5).mean()), "util4A_median": a.utility_4A_mean.median(),
               "util4A_min": a.utility_4A_mean.min(), "util4A_max": a.utility_4A_mean.max(), "n_model3": len(b)}
        if len(b):
            row.update({"m3_AUC_median": b.AUC_mean.median(), "m3_AUC_min": b.AUC_mean.min(), "m3_AUC_p05": b.AUC_mean.quantile(0.05),
                        "m3_AUC_p95": b.AUC_mean.quantile(0.95), "m3_AUC_max": b.AUC_mean.max(),
                        "m3_Brier_min": b.Brier_mean.min(), "m3_Brier_max": b.Brier_mean.max(),
                        "m3_diff_ridge_min": b.diff_ridge_mean.min(), "m3_diff_ridge_max": b.diff_ridge_mean.max(),
                        "m3_diff_Model2_min": b.diff_Model2_mean.min(), "m3_diff_Model2_max": b.diff_Model2_mean.max(),
                        "m3_share_variants_above_ridge": float((b.diff_ridge_mean > 0).mean()),
                        "m3_share_variants_above_Model2": float((b.diff_Model2_mean > 0).mean())})
        summ.append(row)
    for family, lab in (("random_local", "chosen in each training fold from the +/-50% draws"),
                        ("random_wide", "chosen in each training fold from the sign-preserving draws")):
        e = NE[(NE.benchmark == bench) & (NE.family == family)]
        summ.append({"benchmark": bench, "set": lab, "n_spider": 1, "spider_AUC_median": e.AUC.mean(), "spider_AUC_min": e.AUC.mean(),
                     "spider_AUC_max": e.AUC.mean(), "spider_AUC_p05": e.AUC.quantile(0.05), "spider_AUC_p95": e.AUC.quantile(0.95),
                     "training_AUC_mean": e.training_AUC_mean.mean()})
pd.DataFrame(summ).to_csv(RES / "table_weight_sensitivity.csv", index=False)
log("weight sensitivity done")
