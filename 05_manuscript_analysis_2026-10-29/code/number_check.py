"""Check the numbers written directly into the revised manuscript's text against the data.

Placeholder numbers are inserted by fill_manuscript.py and tables by
make_tex_tables.py; this script covers the numbers typed into the prose
(sample counts, SVB case, ablation and risk-thirds sentences, Model 4 constants)
and confirms that each appears in the final .tex file.

usage: python3 -I number_check.py <research_folder> <results_dir> <final_tex> <out_txt>
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing the framework code must not leave __pycache__ in the research folder

import pandas as pd

ROOT, R, TEX, OUT = (Path(a) for a in sys.argv[1:5])
tex = re.sub(r"\s+", " ", TEX.read_text())  # compare with all whitespace collapsed
FW = ROOT / "03_revised_framework_2026-10-29"
p55 = pd.read_csv(FW / "data/SNFF_Revised_Inputs_Primary55.csv")
led = pd.read_csv(FW / "data/Source_Verification_Ledger_90.csv")
man = json.loads((R / "RUN_MANIFEST.json").read_text())
svb = json.loads((R / "svb_case.json").read_text())
ab = pd.read_csv(R / "table_ablation.csv").set_index("model")
abr = pd.read_csv(R / "ablation_by_repeat.csv")
th = pd.read_csv(R / "table_risk_thirds.csv")
pol = pd.read_csv(R / "table_decision_policies.csv").set_index("policy")
sm = man["sample"]
lines, fails = [], 0


def check(label: str, computed: str, text_snippet: str):
    global fails
    snip = re.sub(r"\s+", " ", text_snippet.format(v=computed))
    ok_val = snip in tex
    fails += not ok_val
    lines.append(f"[{'ok' if ok_val else 'FAIL'}] {label}: computed {computed!r}; text contains {snip!r}")


def check_text(label: str, snippet: str):
    """A prose snippet whose numbers were formatted from the results."""
    global fails
    snip = re.sub(r"\s+", " ", snippet)
    ok_val = snip in tex
    fails += not ok_val
    lines.append(f"[{'ok' if ok_val else 'FAIL'}] {label}: text contains {snip!r}")


def check_true(label: str, cond: bool, detail: str):
    """A qualitative statement in the prose (ordering, bound) checked against the results."""
    global fails
    fails += not cond
    lines.append(f"[{'ok' if cond else 'FAIL'}] {label}: {detail}")


w = {3: "three", 9: "nine", 44: "44"}
check("P&A failures", str(sm["P&A failures"]), "Of {v}\npurchase-and-assumption failures")
check("complete call reports", str(sm["with complete call reports"]), "{v} have complete call-report data")
check("U.S.-listed parents in top 150", str(sm["150: U.S.-listed parent"]), "In {v} of the 150 transactions")
check("private acquirers", str(sm["150: private"]), "{v} acquirers were privately held")
check("foreign-owned", w[sm["150: foreign-owned"]], "{v} were owned by a\nforeign bank")
check("OTC parents", w[sm["150: OTC"]], "and {v} parents traded only over the counter")
check("with prices (primary)", str(sm["150: U.S.-listed with prices (primary panel)"]), "are available for {v} of the 94")
check("without prices", str(sm["150: U.S.-listed without prices"]), "do not cover the other {v}")
check("broader panel", str(sm["469: U.S.-listed with prices (broader panel)"]), "give {v} transactions with prices")
check("U.S.-listed in all 469", str(sm["469: U.S.-listed parent"]), "out of {v} with\na U.S.-listed parent")
check("event clusters", str(man["event_groups_primary"]), "transactions form {v} clusters")
check("reports not yet public at Q-1", str(int((p55.failed_report_is_stage1_q1 == 0).sum())), "For {v} of the 55 banks, which failed within 30 days")
check("loss share count", "Forty" if int(p55.F_loss_share.sum()) == 40 else str(int(p55.F_loss_share.sum())), "{v} of the 55 primary\ntransactions include an FDIC loss-share agreement")
check("after-close count", {53: "Fifty-three"}.get(int((led[led.in_primary_panel == 1].timing_class == "AFTER_CLOSE").sum()), "?"), "{v} of the\n55 were released after the market close")
fri = int(((led.in_primary_panel == 1) & (led.timing_class == "AFTER_CLOSE") & (led.announcement_weekday == "Friday")).sum())
check("Friday evening count", str(fri), "{v} on a Friday evening")
check("labels primary", str(int(p55.y.sum())), "{v} of the 55 transactions have a positive CAR under the primary window")
check("labels [0,+1]", str(int(p55.y_release_0p1.sum())), "window, {v} under $[0,+1]$")
check("labels June", str(int(p55.y_release_m1p1_june.sum())), "and {v} under\n$[-1,+1]$ around it")
corr = pd.read_csv(ROOT / "04b_step4_verification_2026-10-29/Loss_Share_Negatives_Corroboration.csv")
check("loss-share negatives confirmed", {8: "eight"}.get(len(corr), str(len(corr))), "for each of the {v} such transactions we checked")
check("label changes", str(int((p55.y != p55.y_release_m1p1_june).sum())), "which changes {v} labels")
mm = pd.read_csv(FW / "data/Event_Convention_Comparison_90.csv")
check("market-model labels", str(int(mm[mm.in_primary_panel == 1].y_reaction_m1p1_market_model.sum())), "labels {v} of the 55 transactions positive")
# bank-sector benchmark (Section V, robustness, limitations)
bk = pd.read_csv(ROOT / "05_manuscript_analysis_2026-10-29/data/Bank_Benchmark_CAR_90.csv").set_index("transaction_id")
yb = p55.transaction_id.map(bk.y_reaction_m1p1_bank).astype(int)
check("bank-benchmark positives", str(int(yb.sum())), "it labels {v} of\nthe 55 transactions positive")
nflip = int((yb != p55.y).sum())
check("bank-benchmark label changes (robustness)", {10: "Ten"}.get(nflip, str(nflip)), "{v} labels change under this benchmark")
check("bank-benchmark label changes (limitations)", str(nflip), "and {v} change when a bank-sector index replaces")
fbop = (p55.listed_parent_ticker == "USB") & (p55.first_reaction_date.astype(str) == "2009-11-02")
check_true("the four FBOP transactions change from negative to positive", int(fbop.sum()) == 4 and (p55[fbop].y == 0).all() and (yb[fbop] == 1).all(),
           f"{int(fbop.sum())} transactions")
cache_path = ROOT / "00_original_stage1_2026-06-19/raw_pulls/car_price_cache.json"
if cache_path.exists():  # the constituent count needs the price cache, which the public release does not contain
    cache = json.loads(cache_path.read_text())
    cons = sorted(k for k, v in cache.items() if v and "|" not in k and k != "SPY" and k not in {"BBVA", "BNS", "SAN", "TD", "CYN", "EVER"})
    check("bank-index constituents", str(len(cons)), "the {v} U.S.-listed bank holding companies")
check_true("every bank-index window has at least 24 constituents", int(bk.index_constituents_min.min()) >= 24, f"minimum {int(bk.index_constituents_min.min())}")
# SVB case
inp, sc, fp = svb["inputs"], svb["scores"], svb["fit_parameters"]
check("SVB deposits", f"{inp['G_deposits_usd_bn']:.1f}", "\\${v}B")
check("SVB G", f"{sc['G_n']:.3f}", "$G = {v}$")
check("SVB NPL", f"{inp['N_npl_pct']:.2f}", "{v}\\%")
check("SVB N", f"{sc['N_n']:.3f}", "$N = {v}$")
check("SVB deposit change", f"{inp['L_deposit_change_pct']:.1f}".replace("-", ""), "$-{v}\\%$")
check("SVB NPL change", f"{inp['T_npl_change_pp']:.2f}", "$+{v}$ pp")
check("SVB R", f"{sc['R_score']:.3f}", "\\textbf{{{v}}}")
check("SVB buyer capital", f"{inp['C_buyer_capital_pct']:.2f}", "{v}\\%")
check("SVB C", f"{sc['C_n']:.3f}", "$C = {v}$")
check("SVB relative size", f"{inp['E_relative_size']:.2f}", "& {v} & $M")
check("SVB S", f"{sc['S_raw']:.3f}", "&= {v}.")
check("SVB S tilde", f"{sc['S_final']:.3f}", "\\tilde S_{{\\text{{SVB}}}} = {v}")
check("SVB CAR", f"{100 * inp['car_reaction_m1p1']:.1f}", "is {v}\\%")
for k in ("N75", "C25", "E75"):
    pass
n75_raw = fp["N_min"] + fp["N75"] * (fp["N_max"] - fp["N_min"])
c25_raw = fp["C_min"] + fp["C25"] * (fp["C_max"] - fp["C_min"])
e75_raw = fp["E_min"] + fp["E75"] * (fp["E_max"] - fp["E_min"])
check("N75 raw", f"{n75_raw:.1f}", "NPL ratio of {v}\\%")
check("C25 raw", f"{c25_raw:.2f}", "buyer capital ratio of {v}\\%")
check("M75 raw", f"{e75_raw:.2f}", "relative\nsize of {v}")
check("L quartile threshold", f"{fp['L_q25']:.1f}".replace("-", ""), "bottom quartile ($-{v}\\%$)")
# ablation sentence
for st, snip in (("A: measured inputs", "against {v} for stage~A"), ("B: A + Spider score", "unchanged ({v} against"),
                 ("C: A + interaction rules", "lowers it to {v},"), ("D: full SNFF (Model 3)", "inherits this loss ({v})"),
                 ("E: D without protection inputs", "recovers part\nof the loss ({v})"), ("F: D without buyer capital", "recovers all of it ({v})")):
    check(f"ablation {st}", f"{ab.loc[st, 'AUC_mean']:.3f}", snip)
pw = abr.pivot_table(index="repeat", columns="model", values="AUC")
check("ablation C below A share", f"{100 * ((pw['C: A + interaction rules'] - pw['A: measured inputs']) < 0).mean():.0f}", "below stage~A in {v}\\% of the partitions")
# risk thirds
lo = th[th.R_third == "lowest third"].iloc[0]
mid = th[th.R_third == "middle third"].iloc[0]
hi = th[th.R_third == "highest third"].iloc[0]
check("lowest third", f"{int(lo.positive)} of {int(lo.deals)}", "{v} have a positive CAR")
check("other thirds", f"{int(mid.positive)} of {int(mid.deals)}", "{v} in each of the other two thirds")
assert int(mid.positive) == int(hi.positive) and int(mid.deals) == int(hi.deals)
check_true("thirds sizes 19/18/18 as written", (int(lo.deals), int(mid.deals), int(hi.deals)) == (19, 18, 18), "holds")
check("lowest third median CAR", f"{100 * lo.median_CAR:.1f}".replace("-", ""), "(median CAR\n$-{v}\\%$)")
check("middle/high median CAR", f"+{100 * mid.median_CAR:.1f}\\%$ and $+{100 * hi.median_CAR:.1f}", "${v}\\%$)")
# Model 4 constants
check("pursue-all F1", f"{pol.loc['Pursue all', 'F1']:.3f}", "policy ({v})")
check("pursue-all utility", f"{pol.loc['Pursue all', 'utility_3to1']:.3f}".replace("-", ""), "utility ($-{v}$)")
# robustness paragraph
rb = pd.read_csv(R / "table_robustness.csv")
br = pd.read_csv(R / "table_broader90.csv").set_index("model")
LRm, RIm, M3m, SCm, PAm, RFm = "Logistic regression (L2, C=1)", "Ridge logistic", "SNFF + LR (Model 3)", "Spider score alone (Model 1)", "LR + pairwise interactions", "Random forest"


def rv(variant, model):
    x = rb[(rb.variant == variant) & (rb.model == model)]
    return float(x.AUC_mean.iloc[0]), int(x.positives.iloc[0])


V01, VJ, VMM, VP = "Release-date CAR[0,+1]", "Release-date CAR[-1,+1] (June window)", "Reaction-day CAR[-1,+1], market model", "Reaction-day CAR[-1,+1] (primary)"
VB, VPUB = "Reaction-day CAR[-1,+1], bank-index benchmark", "Published call-report inputs only"
ALT = (V01, VJ, VMM)          # the two announcement-date windows and the market model
ALT4 = ALT + (VB,)            # plus the bank-sector benchmark
f = lambda x: f"{x:.3f}"


def rb_brier(variant, model):
    return float(rb[(rb.variant == variant) & (rb.model == model)].Brier_mean.iloc[0])


check_text("[0,+1] window", f"which labels {rv(V01, LRm)[1]} transactions positive, every model's mean AUC is close to one half "
           f"({f(rv(V01, LRm)[0])} for Model~2, {f(rv(V01, RIm)[0])} for ridge regression, and {f(rv(V01, M3m)[0])} for Model~3)")
check_true("[0,+1]: all three within 0.06 of one half", all(abs(rv(V01, m)[0] - 0.5) < 0.06 for m in (LRm, RIm, M3m)), "holds")
check_text("[-1,+1] window", f"announcement date ({rv(VJ, LRm)[1]} positive), the AUCs are slightly lower than in the primary specification "
           f"({f(rv(VJ, LRm)[0])}, {f(rv(VJ, RIm)[0])}, and {f(rv(VJ, M3m)[0])})")
check_true("[-1,+1]: each model below its primary AUC by less than 0.05", all(0 < rv(VP, m)[0] - rv(VJ, m)[0] < 0.05 for m in (LRm, RIm, M3m)),
           ", ".join(f"{rv(VP, m)[0] - rv(VJ, m)[0]:.3f}" for m in (LRm, RIm, M3m)))
mmv = [rv(VMM, m)[0] for m in (LRm, RIm, M3m)]
check_text("market model", f"market-model outcome ({rv(VMM, LRm)[1]} positive) the three models perform alike ({f(min(mmv))} to {f(max(mmv))})")
up = [rv(v, M3m)[0] - rv(v, LRm)[0] for v in ALT]
dn = [rv(v, RIm)[0] - rv(v, M3m)[0] for v in ALT]
check_true("three alternatives: Model 3 above Model 2, ridge at or above Model 3", min(up) > 0 and min(dn) >= 0, f"up {up}, ridge-M3 {dn}")
check_true("bank benchmark: every fitted model below one half", all(rv(VB, m)[0] < 0.5 for m in (LRm, RIm, M3m)), ", ".join(f"{rv(VB, m)[0]:.3f}" for m in (LRm, RIm, M3m)))
check_text("alternative outcomes: margins", f"Model~2, by {f(min(up))} to {f(max(up))}, and level with or slightly below ridge regression, by {f(min(dn))} to {f(max(dn))}")
bp = rb_brier(VP, M3m) - rb_brier(VP, RIm)
ba = [rb_brier(v, RIm) - rb_brier(v, M3m) for v in ALT4]
check_true("Brier: Model 3 above ridge in primary, below in all four alternative outcomes", bp > 0 and min(ba) > 0, f"primary {bp:+.4f}; alt {ba}")
check_text("Brier relative to ridge", f"raise the Brier score in the primary specification (by {f(bp)}) and lower it under the four alternative outcomes "
           f"(by {f(min(ba))} to {f(max(ba))})")
lower_b = all(rb_brier(v, M3m) < rb_brier(v, LRm) for v in ALT)
most = all((rb_brier(v, LRm) - rb_brier(v, RIm)) > 0.5 * (rb_brier(v, LRm) - rb_brier(v, M3m)) for v in ALT)
check_true("H1 paragraph: Model 3 Brier below Model 2 under alternative outcomes; ridge accounts for most of the reduction", lower_b and most,
           ", ".join(f"{(rb_brier(v, LRm) - rb_brier(v, RIm)) / (rb_brier(v, LRm) - rb_brier(v, M3m)):.2f}" for v in ALT))
base3 = rv(VP, M3m)[0]
dd = [abs(rv(v, M3m)[0] - base3) for v in ("Broad support definition", "U rule requires support (broad)", "Z rule removed")]
check_true("support/rule variants change Model 3 AUC by < 0.01", max(dd) < 0.01, f"max change {max(dd):.4f}")
VAR_M3_BELOW = (VPUB, "Broad support definition", "U rule requires support (broad)", "Z rule removed")
check_true("published-only and support/rule variants: Model 3 below Model 2 and ridge", all(rv(v, M3m)[0] < min(rv(v, LRm)[0], rv(v, RIm)[0]) for v in VAR_M3_BELOW),
           "; ".join(f"{rv(v, M3m)[0]:.3f} vs {rv(v, LRm)[0]:.3f}/{rv(v, RIm)[0]:.3f}" for v in VAR_M3_BELOW))
pub_d = [rv(VPUB, m)[0] - rv(VP, m)[0] for m in (LRm, RIm, M3m)]
check_true("published-only: about as well as with the deal terms, or slightly better (0 <= change < 0.03)", all(0 <= x < 0.03 for x in pub_d),
           ", ".join(f"{x:+.3f}" for x in pub_d))
check_text("broader panel ranking", f"Model~3 ({f(br.loc[M3m, 'AUC_mean'])}) again ranks below Model~2 ({f(br.loc[LRm, 'AUC_mean'])}) and ridge regression ({f(br.loc[RIm, 'AUC_mean'])})")
check_text("broader panel leaders", f"pairwise-interaction model ({f(br.loc[PAm, 'AUC_mean'])}) and the random forest ({f(br.loc[RFm, 'AUC_mean'])}) rank highest")
top2 = br.drop(index=SCm).AUC_mean.sort_values(ascending=False).index[:2].tolist()
check_true("pairwise and random forest are the top two in the broader panel", set(top2) == {PAm, RFm}, str(top2))
check_true("Model 3 below Model 2 and ridge in the broader panel", br.loc[M3m, "AUC_mean"] < min(br.loc[LRm, "AUC_mean"], br.loc[RIm, "AUC_mean"]), "ordering holds")
scv = rb[(rb.model == SCm) & (rb.variant != VB)].AUC_mean
check_text("Spider score range across variants", f"in every variant ({f(scv.min())} to {f(scv.max())}) except the\nbank-sector benchmark")
check_true("Spider score below 0.5 in every variant but the bank benchmark, and in the broader panel", scv.max() < 0.5 and br.loc[SCm, "AUC_mean"] < 0.5
           and rv(VB, SCm)[0] >= 0.5, f"bank {rv(VB, SCm)[0]:.3f}")
check_text("Spider score in the broader panel", f"and in the broader panel\n({f(br.loc[SCm, 'AUC_mean'])})")
# FBOP ranking sentence
rk = pd.read_csv(R / "table_rank_by_group.csv").set_index("model")
fb = rk.loc[[LRm, RIm, PAm, M3m], "FBOP subsidiaries (one event, y=0)"]
check_true("FBOP subsidiaries' mean percentile rank below 0.08 (Model 2, ridge, pairwise, Model 3)", fb.max() < 0.08, f"max {fb.max():.3f}")
# calibration paragraph
cb = pd.read_csv(R / "table_calibration_bins.csv")


def cbin(model, b, col):
    return float(cb[(cb.model == model) & (cb.bin == b)][col].iloc[0])


check_text("calibration Model 2 extremes", f"average {f(cbin(LRm, 1, 'mean_prediction'))} and {f(cbin(LRm, 5, 'mean_prediction'))}, while the observed shares in them are "
           f"{f(cbin(LRm, 1, 'observed_rate'))} and {f(cbin(LRm, 5, 'observed_rate'))}")
check_text("calibration Model 3 top quintiles", f"with a mean prediction of {f(cbin(M3m, 5, 'mean_prediction'))}, contains a lower share of positive outcomes "
           f"({f(cbin(M3m, 5, 'observed_rate'))}) than its fourth quintile ({f(cbin(M3m, 4, 'observed_rate'))})")
lohi = [cbin(m, 1, "mean_prediction") for m in (RIm, M3m)] + [cbin(m, 5, "mean_prediction") for m in (RIm, M3m)]
check_true("ridge/Model 3 quintile means 'about 0.44 to 0.83'", all(abs(x - 0.44) <= 0.01 for x in lohi[:2]) and all(abs(x - 0.83) <= 0.01 for x in lohi[2:]),
           ", ".join(f"{x:.3f}" for x in lohi))
check_true("ridge/Model 3 observed share not monotone", all(any(cbin(m, k + 1, "observed_rate") < cbin(m, k, "observed_rate") for k in range(1, 5)) for m in (RIm, M3m)), "holds")
oo = pd.read_csv(R / "out_of_fold_predictions.csv")
mp = oo[oo.model.isin([LRm, RIm, M3m])].groupby("model").prediction.mean()
check_true("mean predictions about 0.64 and observed share 0.64", all(abs(x - 0.64) < 0.005 for x in mp) and abs(oo.y.mean() - 0.64) < 0.005,
           ", ".join(f"{x:.3f}" for x in mp) + f"; observed {oo.y.mean():.3f}")
# SHAP paragraph (full-sample fit, descriptive)
sh = pd.read_csv(R / "table_shap_fullsample.csv").reset_index(drop=True)
imp = sh.set_index("feature").mean_abs_shap
coef = sh.set_index("feature").coefficient_standardized
check_true("deposit change is the top SHAP feature with a negative coefficient", sh.feature.iloc[0] == "Deposit change (L)" and coef["Deposit change (L)"] < 0,
           f"top {sh.feature.iloc[0]}, coefficient {coef['Deposit change (L)']:.3f}")
check_true("deposit change 'by far' (at least 2.5 times the second)", imp.iloc[0] >= 2.5 * imp.iloc[1], f"{imp.iloc[0]:.3f} vs {imp.iloc[1]:.3f}")
nxt = ["Buyer capital (C)", "Spider score", "Loss share (F)", "Deposits (G)"]
check_true("ranks 2-5 are buyer capital, Spider score, loss share, deposits", set(sh.feature.iloc[1:5]) == set(nxt), str(sh.feature.iloc[1:5].tolist()))
ratios = [imp[k] / imp.iloc[0] for k in nxt]
check_true("each between a quarter and a third of the top weight", all(0.25 <= x <= 0.34 for x in ratios), ", ".join(f"{x:.2f}" for x in ratios))
check_true("Spider score and loss share have negative coefficients", coef["Spider score"] < 0 and coef["Loss share (F)"] < 0,
           f"{coef['Spider score']:.3f}, {coef['Loss share (F)']:.3f}")
inputs = ["NPL ratio (N)", "Deposits (G)", "Buyer capital (C)", "Relative size (E)", "Deposit change (L)", "NPL change (T)", "Loss share (F)", "Support (H)"]
check_true("rule U comparable to the inputs (above at least two of them)", (imp["Rule U"] > imp[inputs]).sum() >= 2, f"U {imp['Rule U']:.3f}")
check_true("rules Q and K contribute little (below every input except support)",
           all(imp[r] < imp[[i for i in inputs if i != "Support (H)"]].min() for r in ("Rule Q", "Rule K")), f"Q {imp['Rule Q']:.3f}, K {imp['Rule K']:.3f}")
check_true("model rewards deposit outflows and high NPL ratios", coef["Deposit change (L)"] < 0 and coef["NPL ratio (N)"] > 0,
           f"L {coef['Deposit change (L)']:.3f}, N {coef['NPL ratio (N)']:.3f}")
sys.path.insert(0, str(FW / "code"))
from snff_revised_features import RevisedSpider  # noqa: E402
zf = RevisedSpider().fit(p55).transform(p55)
check_true("rule Z fires for a single transaction in the full sample", int(zf.Z_rule.sum()) == 1, f"{int(zf.Z_rule.sum())}")
# permutation paragraph: qualitative statements
pt = pd.read_csv(R / "table_permutation_test.csv").set_index("model")
nm2 = round(float(pt.loc[LRm, "null_mean"]), 2)
check_true("null means of the three logistic models all round to the stated value", all(round(float(pt.loc[m, "null_mean"]), 2) == nm2 for m in (LRm, RIm, M3m)),
           ", ".join(f"{pt.loc[m, 'null_mean']:.3f}" for m in (LRm, RIm, M3m)))
pv = {m: float(pt.loc[m, "p_value_one_sided"]) for m in (LRm, RIm, M3m)}
ph = {m: float(pt.loc[m, "p_holm_one_sided"]) for m in (LRm, RIm, M3m)}
check_true("no model below 0.05 after the Holm adjustment", min(ph.values()) >= 0.05, str({k[:12]: round(v, 3) for k, v in ph.items()}))
check_true("Model 3 has the largest one-sided p of the three", pv[M3m] >= max(pv[LRm], pv[RIm]), str({k[:12]: round(v, 3) for k, v in pv.items()}))
check_true("permutation run settings as stated", man["permutations"] == 400 and man["permutation_repeats"] == 3 and len(pd.read_csv(R / "permutation_null.csv")) == 400,
           f"{man['permutations']} permutations x {man['permutation_repeats']} partitions")
# refitting bootstrap
rfb = pd.read_csv(R / "table_bootstrap_refit.csv").set_index("quantity")
for other in (RIm, LRm):
    q = rfb.loc[f"diff SNFF minus {other}"]
    check_true(f"refitting bootstrap: interval for Model 3 minus {other[:20]} contains zero", q.ci_low < 0 < q.ci_high, f"[{q.ci_low:+.3f}, {q.ci_high:+.3f}]")
check_true("refitting bootstrap: no replicate skipped, 500 replicates", int(rfb.skipped.iloc[0]) == 0 and int(rfb.replicates.iloc[0]) == 500,
           f"{int(rfb.replicates.iloc[0])} replicates, {int(rfb.skipped.iloc[0])} skipped")
cb2 = pd.read_csv(R / "table_cluster_bootstrap.csv").set_index("quantity")
qr, qm = cb2.loc[f"AUC difference SNFF minus {RIm}"], cb2.loc[f"AUC difference SNFF minus {LRm}"]
check_true("conditional bootstrap: ridge interval excludes zero, Model 2 interval borders it", qr.ci_high < 0 and abs(qm.ci_high) < 0.005,
           f"ridge [{qr.ci_low:+.3f}, {qr.ci_high:+.3f}]; Model 2 [{qm.ci_low:+.3f}, {qm.ci_high:+.3f}]")
# FBOP influence on Model 2
fi = pd.read_csv(R / "table_fbop_influence_model2.csv")
fa_ = float(fi[(fi.outcome == VP.replace(" (primary)", ", SPY (primary)")) & (fi["sample"] == "all 55 transactions")].AUC_mean.iloc[0])
fd_ = float(fi[(fi.outcome == VP.replace(" (primary)", ", SPY (primary)")) & (fi["sample"] == "without the FBOP cluster")].AUC_mean.iloc[0])
check_true("'most of Model 2's discrimination comes from a single event' (dropping it removes over half of the AUC above 0.5)",
           fa_ - fd_ > 0.5 * (fa_ - 0.5), f"{fa_:.3f} -> {fd_:.3f}")
pdf_ = pd.read_csv(R / "table_paired_differences.csv")
shr = {o: float(pdf_[(pdf_.comparison == f"SNFF minus {o}") & (pdf_.metric == "AUC")].share_SNFF_better.iloc[0]) for o in (LRm, RIm)}
check_true("Model 3 below Model 2 and ridge in most partitions", max(shr.values()) < 0.5, str({k[:12]: v for k, v in shr.items()}))
fr_ = float(fi[(fi.outcome == VB) & (fi["sample"] == "all 55 transactions")].fbop_mean_percentile_rank.iloc[0])
check_true("bank benchmark: Model 2 still ranks the FBOP transactions near the bottom (mean percentile rank at most 0.10)", fr_ <= 0.10, f"{fr_:.3f}")
check_true("FBOP cluster check: 51 transactions, 50 clusters without it", set(fi[fi["sample"] == "without the FBOP cluster"].n) == {51}
           and set(fi[fi["sample"] == "without the FBOP cluster"].event_clusters) == {50}, "holds")
# risk-direction checks
rvt = pd.read_csv(R / "table_risk_validation.csv")
r55 = rvt[rvt.deals == "primary 55"].set_index("outcome").AUC_R
check_true("release-date windows: Risk AUC below one half in the primary panel", r55["Release-date CAR[0,+1]"] < 0.5 and r55["Release-date CAR[-1,+1] (June window)"] < 0.5,
           f"{r55['Release-date CAR[0,+1]']:.3f}, {r55['Release-date CAR[-1,+1] (June window)']:.3f}")
rit = pd.read_csv(R / "table_risk_influence.csv")
bank_p = rit[(rit.outcome == VB) & (rit.analysis.str.startswith("announced"))].set_index("analysis").AUC_R
check_true("bank benchmark: reversed in 2008-2010, positive in 2011-2024", bank_p["announced 2008-2010"] < 0.5 < bank_p["announced 2011-2024"],
           f"{bank_p['announced 2008-2010']:.3f}, {bank_p['announced 2011-2024']:.3f}")
spy_ex = rit[(rit.outcome == "Reaction-day CAR[-1,+1], SPY (primary)") & ~rit.analysis.str.startswith("announced")].AUC_R
check_true("SPY: every exclusion keeps the Risk AUC above 0.6", spy_ex.min() > 0.6, f"min {spy_ex.min():.3f}")
# outcome wording
vc = re.findall(r"value-creat\w*|value creation|value-destroy\w*|created value", tex)
check_true("'value-creating' no longer describes the outcome (one use, in the sentence that rejects it)", len(vc) == 1 and "rather than as value-creating" in tex,
           f"{len(vc)} uses: {vc}")
# references: every cited key listed, every listed key cited, numbered in order of first citation
cited = []
for mt in re.finditer(r"\\cite\{([^}]*)\}", tex):
    for k in mt.group(1).split(","):
        if k.strip() not in cited:
            cited.append(k.strip())
bib = re.findall(r"\\bibitem\{([^}]*)\}", tex)
check_true("references: cited = listed, in order of first citation", cited == bib, f"{len(cited)} cited, {len(bib)} listed")
OUT.write_text("\n".join(lines) + f"\n\n{'ALL TEXT NUMBERS MATCH' if fails == 0 else f'{fails} MISMATCH(ES)'}\n")
print("\n".join(lines[-5:]))
print("ALL TEXT NUMBERS MATCH" if fails == 0 else f"{fails} MISMATCH(ES)")
sys.exit(1 if fails else 0)
