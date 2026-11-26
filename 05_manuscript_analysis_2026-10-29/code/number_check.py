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


def unrev(s: str) -> str:
    """Remove the revision highlighting \\rev{...} (brace-balanced), keeping its content."""
    out, i = [], 0
    while True:
        j = s.find(r"\rev{", i)
        if j < 0:
            return "".join(out) + s[i:]
        out.append(s[i:j])
        k, depth = j + 5, 1
        while depth:
            depth += {"{": 1, "}": -1}.get(s[k], 0)
            k += 1
        out.append(unrev(s[j + 5:k - 1]))
        i = k


tex = re.sub(r"\s+", " ", unrev(TEX.read_text()))  # highlighting removed, all whitespace collapsed
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
check("with prices (primary)", str(sm["150: U.S.-listed with prices (primary panel)"]), "are in the price data collected for this study for {v} of the 94")
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
check("bank-benchmark label changes (robustness)", {10: "Ten"}.get(nflip, str(nflip)), "{v} labels\nchange under the bank-sector benchmark")
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
check_text("[-1,+1] window", f"announcement date ({rv(VJ, LRm)[1]} positive), the AUCs are slightly lower than in the main specification "
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
check_true("Brier: Model 3 above ridge in the main specification, below under the three alternatives and the bank-sector benchmark", bp > 0 and min(ba) > 0,
           f"main {bp:+.4f}; alt {ba}")
check_text("Brier relative to ridge", f"raise the Brier score in the main specification (by {f(bp)}) and lower it under these three alternatives and against the bank-sector benchmark "
           f"(by {f(min(ba))} to {f(max(ba))})")
lower_b = all(rb_brier(v, M3m) < rb_brier(v, LRm) for v in ALT)
most = all((rb_brier(v, LRm) - rb_brier(v, RIm)) > 0.5 * (rb_brier(v, LRm) - rb_brier(v, M3m)) for v in ALT)
check_true("H1 paragraph: Model 3 Brier below Model 2 under alternative outcomes; ridge accounts for most of the reduction", lower_b and most,
           ", ".join(f"{(rb_brier(v, LRm) - rb_brier(v, RIm)) / (rb_brier(v, LRm) - rb_brier(v, M3m)):.2f}" for v in ALT))
base3 = rv(VP, M3m)[0]
# broad support definition (corrected 2026-11-23: Westernbank and Eurobank added): lowers all three logistic models
VBR, VUH, VZ = "Broad support definition", "U rule requires support (broad)", "Z rule removed"
check_true("broad support: lower mean AUC than the primary specification for Model 2, ridge and Model 3",
           all(rv(VBR, m)[0] < rv(VP, m)[0] for m in (LRm, RIm, M3m)), ", ".join(f"{rv(VBR, m)[0] - rv(VP, m)[0]:+.3f}" for m in (LRm, RIm, M3m)))
check_text("broad support numbers", f"lowers the mean AUC of all three logistic models (to {f(rv(VBR, LRm)[0])} for Model~2, "
           f"{f(rv(VBR, RIm)[0])} for ridge regression, and {f(rv(VBR, M3m)[0])} for Model~3)")
check_true("U requires broad support: Model 3 above Model 2, below ridge", rv(VUH, LRm)[0] < rv(VUH, M3m)[0] < rv(VUH, RIm)[0],
           f"{rv(VUH, M3m)[0]:.3f} vs {rv(VUH, LRm)[0]:.3f}/{rv(VUH, RIm)[0]:.3f}")
check_text("U requires broad support numbers", f"Model~3 reaches {f(rv(VUH, M3m)[0])}, above Model~2 ({f(rv(VUH, LRm)[0])}) but below ridge "
           f"regression ({f(rv(VUH, RIm)[0])})")
check_text("H1 paragraph: U requires broad support", f"it ranks above Model~2 ({f(rv(VUH, M3m)[0])} against {f(rv(VUH, LRm)[0])}) but below ridge "
           f"regression ({f(rv(VUH, RIm)[0])})")
check_true("Z rule removed changes Model 3 AUC by < 0.01", abs(rv(VZ, M3m)[0] - base3) < 0.01, f"change {rv(VZ, M3m)[0] - base3:+.4f}")
VAR_M3_BELOW = (VPUB, VBR, VZ)
check_true("published-only, broad support and Z removed: Model 3 below Model 2 and ridge", all(rv(v, M3m)[0] < min(rv(v, LRm)[0], rv(v, RIm)[0]) for v in VAR_M3_BELOW),
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
check_text("Spider score range across the variants of Panel A", f"in every variant of Panel~A ({f(scv.min())} to {f(scv.max())}), and in the broader panel")
_fb_sc = float(pd.read_csv(R / "table_fbop_influence.csv").query("outcome == 'y' and sample == 'without the FBOP cluster' and model == @SCm").AUC_mean.iloc[0])
check_true("Panel A: the Spider score without the FBOP cluster lies in that range", scv.min() <= _fb_sc <= scv.max(), f"{_fb_sc:.3f}")
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
# outside the primary panel: the 35, and the 28 whose acquirer and reaction day are not in the primary panel (release 4.2)
D55, D35, D28 = "primary 55", "35 broader-only (rules fitted on the 55)", "28 broader-only with own event (rules fitted on the 55)"
b90 = pd.read_csv(FW / "data/SNFF_Revised_Inputs_Broader90.csv")


def ev(d):
    return (d.listed_parent_ticker.astype(str) + "|" + d.first_reaction_date.astype(str)).to_numpy()


o35 = b90[b90.in_primary_panel == 0]
own = ~pd.Series(ev(o35)).isin(set(ev(p55))).to_numpy()
n28, g28 = int(own.sum()), len(set(ev(o35)[own]))
s7 = pd.read_csv(R / "broader_only_shared_events.csv")
fb = s7[s7.listed_parent_ticker == "USB"]
lp, tf = s7[s7.listed_parent_ticker == "WTFC"], s7[s7.listed_parent_ticker == "ABCB"]
check_true("seven of the 35 share an event with the primary panel: five FBOP subsidiaries (USB, with the four in the panel), "
           "Lincoln Park (WTFC, with Wheatland), Tifton (ABCB, with Darby)",
           len(o35) == 35 and len(s7) == 7 == 35 - n28 and len(fb) == 5 and set(fb.primary_panel_transactions_same_event) == {"PA-0385;PA-0386;PA-0387;PA-0388"}
           and list(lp.failed_bank_name) == ["LINCOLN PARK SAVINGS BANK"] and list(lp.primary_panel_banks_same_event) == ["WHEATLAND BANK"]
           and list(tf.failed_bank_name) == ["TIFTON BANKING COMPANY"] and list(tf.primary_panel_banks_same_event) == ["DARBY BANK & TRUST COMPANY"],
           ", ".join(s7.transaction_id))
check_text("the seven (text)", "Seven of these 35, however, share an acquirer and an announcement return with a transaction in the primary panel: the five "
           "FBOP subsidiaries that U.S. Bank bought together with the four in the primary panel, Lincoln Park Savings Bank, which Wintrust bought on the "
           "day it bought Wheatland Bank, and Tifton Banking Company, which Ameris bought on the day it bought Darby Bank \\& Trust.")
check_text("the 28 and their event clusters", f"the other {n28}, which form {g28} event clusters")
compt = pd.read_csv(R / "table_spider_components.csv")


def cpf(dd, c):
    return compt[(compt.deals == dd) & (compt.component == c)].iloc[0]


cp = {(dd, c): cpf(dd, c) for dd in (D55, D35, D28) for c in ("R_score", "B_score")}
r55c, r35c, r28c = cp[(D55, "R_score")], cp[(D35, "R_score")], cp[(D28, "R_score")]
check_text("Risk component, primary panel", f"(AUC {r55c.AUC:.3f}, $p = {r55c.p_two_sided:.3f}$)")
check_text("Risk component, the 35 and the 28", f"its AUC is {r35c.AUC:.3f} ($p = {r35c.p_two_sided:.3f}$); without the seven, it is "
           f"{r28c.AUC:.3f} ($p = {r28c.p_two_sided:.3f}$) in the other 28")
check_true("the 28: same direction, not distinguishable from chance at conventional levels", r28c.AUC > 0.5 and r28c.p_two_sided >= 0.10,
           f"AUC {r28c.AUC:.3f}, p {r28c.p_two_sided:.3f}")
b55c, b35c, b28c = cp[(D55, "B_score")], cp[(D35, "B_score")], cp[(D28, "B_score")]
check_text("Buyer Strength, the 35, the 28 and the 55", f"Buyer Strength has an AUC of {b35c.AUC:.3f} ($p = {b35c.p_two_sided:.3f}$) in the 35, in the "
           f"direction the framework assumes, but {b28c.AUC:.3f} ($p = {b28c.p_two_sided:.3f}$) in the 28 and {b55c.AUC:.3f} in the primary panel")
check_true("Buyer Strength: above one half in the 35 and the 28 (the direction the framework assumes), weaker in the 28",
           b35c.AUC > b28c.AUC > 0.5, f"{b35c.AUC:.3f} > {b28c.AUC:.3f} > 0.5")
r28 = rvt[rvt.deals == D28].set_index("outcome")
shown_p = [r28c.p_two_sided] + [float(r28.loc[o, "p_AUC"]) for o in r28.index if o != "Reaction-day CAR[-1,+1], SPY (primary)"]  # as in Table 13
a28 = r28.AUC_R
check_true("the 28: AUC above one half under every outcome, lowest under the market model, highest against SPY", (a28 > 0.5).all()
           and a28.idxmin() == "Reaction-day CAR[-1,+1], market model" and a28.idxmax() == "Reaction-day CAR[-1,+1], SPY (primary)",
           ", ".join(f"{v:.3f}" for v in a28))
check_text("the 28 under the five outcomes (text)", f"from {a28.min():.3f} under the market model to {a28.max():.3f} against SPY, and is "
           f"{a28[VB]:.3f} against the bank-sector index")
pfloor = int(min(shown_p) * 100) / 100  # a lower bound, so the rounded figure in the text never exceeds the smallest p
check_text("the 28: smallest p-value in Table 13", f"($p \\geq {pfloor:.2f}$)")
check_true("the 28: no p-value in Table 13 below 0.10", min(shown_p) >= 0.10, f"min {min(shown_p):.3f}")
check_true("Discussion: the 28 have an AUC similar to the primary panel's (within 0.02)", abs(r28c.AUC - r55c.AUC) < 0.02, f"{r28c.AUC:.3f} vs {r55c.AUC:.3f}")
check_text("Discussion: the 28", "in the 28 transactions outside it that have their own announcement return")
check_true("no unfilled @@ markers in the manuscript", "@@" not in tex, "none" if "@@" not in tex else "marker left")
check_text("Data and Code Availability cites release 4.17", "constitute the Version 4.17 research replication package")
check_text("release 4.2 described", f"Version 4.2 added the evaluation of the Spider components on the {n28} transactions outside the primary panel "
           "that share no announcement return with it")
check_text("release 4.3 described", "Version 4.3 added the scoring and evaluation of acquisition events, with each multi-bank purchase consolidated")
check_text("release 4.4 described", "Version 4.4 added the retrospective scoring of SVB on its deposits at failure and on those First Citizens assumed")
check_text("release 4.5 described", "Version 4.5 added every analysis under the bank-sector benchmark, reported as the second co-primary specification")
check_text("release 4.6 described", "Version 4.6 added the sensitivity of the Spider score and Model~3 to the expert weights and interaction adjustments;")
check_text("releases 4.7 to 4.17 described", "Version 4.7 added the comparison of the included and excluded transactions, with the call reports of the excluded transactions' acquirers and the later status of their parents; Version 4.8 added the balance and overlap diagnostics of its reweighting; Versions 4.9 to 4.16 extend the checks of the manuscript's numbers to the revised discussion of the FBOP cluster, of statistical power, of the decision problem, and of the cost scenario, to the note relating the two Spider-score AUCs, to the restructured title, abstract, introduction, and conclusion, to the shortened literature review, case study, discussion, and conclusion, and to the qualified statements on event-level discrimination, weight sensitivity, sample selection, significance thresholds, hypothetical payoffs, the information available to the bidder and to investors, and the recovery of missing prices, without changing any analysis; and Version 4.17 prepares the package for publication, adding its licenses, a quick verification mode, and revised documentation. Versions 4.1 to 4.5 each reran the complete analysis; Versions 4.6 to 4.8 run their analyses after it and leave every earlier result unchanged, and Versions 4.9 to 4.17 change no result")
check_text("E1: licenses stated", "The code is released under the MIT License, and the data compiled by the authors, the results, and the documentation under the Creative Commons Attribution 4.0 International License; the third-party sources remain subject to their providers' terms.")
check_true("E1: price series not redistributed", "The original historical stock-price series are not redistributed." in tex, "Data and Code Availability")
check_text("Data and Code Availability lists the deposit stages", "SVB's deposits and assets at its last call report, at failure, and at its sale")

# ------------------------------------------------------------ acquisition events (release 4.3)
EV51 = pd.read_csv(FW / "data/SNFF_Event_Inputs_Primary51.csv")
MB = pd.read_csv(R / "table_multibank_events.csv")
EVL = pd.read_csv(R / "table_event_level.csv").set_index("model")
EVR = pd.read_csv(R / "event_level_by_repeat.csv")
EPOL = pd.read_csv(R / "table_event_level_decision_policies.csv").set_index("policy")
TPOL = pd.read_csv(R / "table_decision_policies.csv").set_index("policy")
MAINC = pd.read_csv(R / "table_main_comparison.csv").set_index("model")
FB, DP, WT, AM = "USB|2009-11-02", "USB|2008-11-24", "WTFC|2010-04-26", "ABCB|2010-11-15"
LR, RIDGE, SNFF = "Logistic regression (L2, C=1)", "Ridge logistic", "SNFF + LR (Model 3)"
SC = "Spider score alone (Model 1)"
EIGHT = [m for m in EVL.index if m != SC]


def bk(e):
    return MB[(MB.event_id == e) & (MB.row == "bank")]


def cons(e, scope="all banks bought that day"):
    return MB[(MB.event_id == e) & (MB.row == "consolidated event") & (MB.scope == scope)].iloc[0]


def mean_of(e, kind, scope="all banks bought that day"):
    return MB[(MB.event_id == e) & (MB.row == kind) & (MB.scope == scope)].iloc[0]


def bank(e, name):
    return bk(e)[bk(e).name == name].iloc[0]


f3_ = "{:.3f}".format
# IV-F and Section V: the events
fbk = bk(FB)
check_true("FBOP: nine banks, four in the primary panel, five below the size cut ($351.5 million)",
           len(fbk) == 9 and int(fbk.in_primary_panel.sum()) == 4 and (fbk[fbk.in_primary_panel == 0].failed_assets_usd_bn < 0.3515).all(), "")
check_text("FBOP purchase (IV-F)", "U.S.~Bank bought nine FBOP subsidiaries in one transaction~\\cite{fdic_pr195_2009}, four of them in the primary "
           "panel and five below its size cut, and its winning bids for the four are marked as linked bids in the FDIC's bid summaries")
check_true("four of the 51 events contain more than one bank", int((EV51.n_banks > 1).sum()) == 4 and len(EV51) == 51, "")
check_text("multi-bank events (IV-F)", "Four of the 51 events of the primary panel contain more than one bank")
lp, tf = bank(WT, "LINCOLN PARK SAVINGS BANK"), bank(AM, "TIFTON BANKING COMPANY")
check_true("Lincoln Park and Tifton are below the size cut", lp.failed_assets_usd_bn < 0.3515 and tf.failed_assets_usd_bn < 0.3515 and
           lp.in_primary_panel == 0 and tf.in_primary_panel == 0, "")
# Section VII-A, VII-D and the conclusion: event-level AUCs
lo8, hi8 = EVL.loc[EIGHT, "AUC_mean"].min(), EVL.loc[EIGHT, "AUC_mean"].max()
check_text("event-level AUC range of the eight models (VII-A)", f"scoring each event on the consolidated inputs of its banks ({f3_(lo8)} to {f3_(hi8)}")
check_true("every one of the eight models has a lower AUC at the event level than at the transaction level",
           all(EVL.loc[m, "AUC_mean"] < MAINC.loc[m, "AUC_mean"] for m in EIGHT), "")
m2e, rde, m3e, sce = (EVL.loc[m, "AUC_mean"] for m in (LR, RIDGE, SNFF, SC))
check_text("event level in VII-D", f"Model~3 ({f3_(m3e)}) again ranks below Model~2 ({f3_(m2e)}) and ridge regression ({f3_(rde)})")
check_true("event level: Model 3 below Model 2 and ridge; Spider score below one half", m3e < m2e and m3e < rde and sce < 0.5, "")
check_text("event level Spider score (VII-D)", f"and among the acquisition events ({f3_(sce)})")
# Section VII-H: the policies
p4a, p4b, p4c, pall, pnone = (EPOL.loc[k] for k in ("4A: fixed Spider thresholds", "4B: F1-tuned threshold", "4C: cost-based threshold (3:1)",
                                                     "Pursue all", "Pursue none"))
check_text("event-level policies (VII-H)", f"Configuration~4A pursues about three of the 51 events per partition for a small positive utility ({f3_(p4a.utility_3to1)}), "
           f"4C and 4B realize ${f3_(p4c.utility_3to1)}$ and ${f3_(p4b.utility_3to1)}$, and pursuing every event ${f3_(pall.utility_3to1)}$")
check_true("event-level 4A pursues about three events", round(p4a.pursue) == 3, f"{p4a.pursue:.2f}")
order_e = list(EPOL.utility_3to1.sort_values(ascending=False).index)
order_t = list(TPOL.utility_3to1.sort_values(ascending=False).index)
check_true("the policies keep their order by utility (Panels A and B)", order_e == order_t, " > ".join(order_e))
# Section VII-I: FBOP
f4 = fbk[fbk.in_primary_panel == 1]
small = fbk[fbk.in_primary_panel == 0]
lem = bank(FB, "COMMUNITY BANK OF LEMONT")
c9, c4 = cons(FB), cons(FB, "banks in the primary panel")
check_text("FBOP panel banks alone", f"the four FBOP subsidiaries in the panel lie between {f3_(f4.S_final.min())} and {f3_(f4.S_final.max())}, all in the Caution band")
check_true("FBOP: panel banks Caution; four of the five smaller Caution; Lemont Avoid", (f4.band == "Caution").all() and
           int((small.band == "Caution").sum()) == 4 and lem.band == "Avoid", "")
check_text("Lemont", f"Community Bank of Lemont, with an NPL ratio of {lem.N_npl_pct:.1f}\\% and a deposit outflow, falls in the Avoid band ({f3_(lem.S_final)})")
check_true("Lemont: deposit outflow flag", int(lem.L_flag) == 1, "")
check_text("FBOP consolidated", f"The consolidated purchase of all nine banks scores {f3_(c9.S_final)}: Caution")
check_true("FBOP consolidated: Caution, above every bank's score", c9.band == "Caution" and c9.S_final > fbk.S_final.max(), "")
check_text("FBOP Value and Execution", f"combined deposit base of \\${c9.G_deposits_usd_bn:.1f} billion gives a Value score of {f3_(c9.V_score)}, against at most "
           f"{f3_(fbk.V_score.max())} for one bank, and the combined assets, {100 * c9.E_relative_size:.1f}\\% of U.S.~Bank's, give an Execution score of "
           f"{f3_(c9.E_score)}, against at most {f3_(fbk.E_score.max())}")
check_text("FBOP consolidated risk inputs", f"consolidated NPL ratio ({c9.N_npl_pct:.1f}\\%), deposit change (${c9.L_deposit_change_pct:+.1f}\\%$), and NPL change "
           f"(${c9.T_npl_change_pp:+.1f}$ percentage points)")
check_true("FBOP consolidated: inputs within the banks' range, no flag or rule",
           all(fbk[c].min() <= c9[c] <= fbk[c].max() for c in ("N_npl_pct", "L_deposit_change_pct", "T_npl_change_pp")) and
           sum(int(c9[c]) for c in ("L_flag", "T_flag", "Q_rule", "U_rule", "Z_rule", "K_rule")) == 0, "")
ms, mw = mean_of(FB, "mean of the bank scores"), mean_of(FB, "asset-weighted mean of the bank scores")
check_text("FBOP means", f"the simple mean of the nine is {f3_(ms.S_final)}, pulled down by the smallest bank, and the asset-weighted mean is {f3_(mw.S_final)}")
check_true("Lemont is the smallest FBOP bank", lem.failed_assets_usd_bn == fbk.failed_assets_usd_bn.min(), "")
share5 = 100 * small.failed_assets_usd_bn.sum() / fbk.failed_assets_usd_bn.sum()
check_text("FBOP four in the panel", f"Restricted to the four banks in the panel, the consolidated score is also {f3_(c4.S_final)}, because the other five hold "
           f"{share5:.0f}\\% of the assets")
check_true("FBOP: four and nine give the same score and band", f3_(c4.S_final) == f3_(c9.S_final) and c4.band == c9.band, "")
# Section VII-I: the other three events
dw, pf, cdp = bank(DP, "DOWNEY SAVINGS AND LOAN ASSOCIATION, F.A."), bank(DP, "PFF BANK & TRUST"), cons(DP)
check_text("Downey and PFF", f"Downey (Caution) and PFF (Avoid, after a {abs(pf.L_deposit_change_pct):.0f}\\% deposit outflow and an NPL rise of "
           f"{pf.T_npl_change_pp:.1f} points set off $L$, $T$, and $Q$) consolidate to Caution ({f3_(cdp.S_final)})")
check_true("Downey Caution, PFF Avoid with L, T, Q; consolidated Caution without flags; Downey > 3 x PFF assets",
           dw.band == "Caution" and pf.band == "Avoid" and int(pf.L_flag) == int(pf.T_flag) == int(pf.Q_rule) == 1 and cdp.band == "Caution" and
           int(cdp.L_flag) == int(cdp.T_flag) == 0 and dw.failed_assets_usd_bn > 3 * pf.failed_assets_usd_bn, "")
check_text("Downey and PFF consolidated changes", f"combined deposit change (${cdp.L_deposit_change_pct:.1f}\\%$) and NPL change (${cdp.T_npl_change_pp:+.1f}$ points)")
wh, cwt, mwt = bank(WT, "WHEATLAND BANK"), cons(WT), mean_of(WT, "mean of the bank scores")
check_text("Wheatland and Lincoln Park", f"Wheatland (Avoid) and Lincoln Park (Caution) consolidate to Avoid ({f3_(cwt.S_final)}), whereas the simple mean of "
           f"their scores ({f3_(mwt.S_final)}) would recommend Caution")
check_true("Wintrust bands", wh.band == "Avoid" and lp.band == "Caution" and cwt.band == "Avoid" and mwt.band == "Caution", "")
db, cam = bank(AM, "DARBY BANK & TRUST COMPANY"), cons(AM)
n75_pct = None
sv = json.loads((R / "svb_case.json").read_text())["fit_parameters"]
n75_pct = sv["N_min"] + sv["N75"] * (sv["N_max"] - sv["N_min"] + 1e-12)
check_text("Darby and Tifton", f"Darby (Caution) and Tifton (Pursue, through rules $Q$ and $U$) consolidate to Caution ({f3_(cam.S_final)}), below both banks")
check_true("Ameris: bands, Tifton's rules, consolidated below both, Q off, larger Execution score",
           db.band == "Caution" and tf.band == "Pursue" and int(tf.Q_rule) == int(tf.U_rule) == 1 and cam.band == "Caution" and
           cam.S_final < min(db.S_final, tf.S_final) and int(cam.Q_rule) == 0 and cam.E_score > db.E_score, "")
check_text("Ameris combined NPL ratio and the 75th percentile", f"the combined ratio ({cam.N_npl_pct:.1f}\\%) is below the panel's 75th percentile ({n75_pct:.1f}\\%)")
outside = [e for e in (FB, DP, WT, AM) if not (bk(e).S_final.min() <= cons(e).S_final <= bk(e).S_final.max())]
flip = [e for e in (FB, DP, WT, AM) if mean_of(e, "mean of the bank scores").band != cons(e).band]
check_true("two events outside the range of the bank scores (FBOP, Ameris); one where the simple mean changes the band (Wintrust)",
           outside == [FB, AM] and flip == [WT], f"outside {outside}; flip {flip}")
check_text("outside the range (text)", "In two of the four events the consolidated score lies outside the range of the bank scores, and in one the simple "
           "mean of the scores would change the recommendation")
# Section VII-I: evaluation
check_text("event-level evaluation (text)", f"the mean AUCs over 50 partitions of the 51 events ({int(EV51.y.sum())} with a positive CAR) are {f3_(m2e)} for "
           f"Model~2, {f3_(rde)} for ridge regression, {f3_(m3e)} for Model~3, and {f3_(sce)} for the Spider score")
check_text("event-level range and averaged-prediction range", f"across the eight models they range from {f3_(lo8)} to {f3_(hi8)}, close to the "
           f"transaction-level AUCs with each event's predictions averaged ({f3_(MAINC.loc[EIGHT, 'AUC_event_mean'].min())} to "
           f"{f3_(MAINC.loc[EIGHT, 'AUC_event_mean'].max())})")
bprev = EVR.groupby("repeat").Brier_prevalence.first().mean()
check_true("every model's mean Brier score is above that of the training-fold share", (EVL.loc[EIGHT, "Brier_mean"] > bprev).all(),
           f"prevalence {bprev:.3f}; lowest model {EVL.loc[EIGHT, 'Brier_mean'].min():.3f}")
check_text("Brier of the training-fold share (text)", f"predicting the training-fold share of positive events ({bprev:.3f})")
pv = EVR.pivot_table(index="repeat", columns="model", values="AUC")
g2, gr = 100 * (pv[SNFF] > pv[LR]).mean(), 100 * (pv[SNFF] > pv[RIDGE]).mean()
check_text("Model 3 above Model 2 and ridge (share of partitions)", f"Model~3 ranks above Model~2 in {g2:.0f}\\% of the partitions and above ridge "
           f"regression in {gr:.0f}\\%")
check_text("H1 at the event level", "and in the broader panel it again ranks below both, as it does among the 51 acquisition events")
# Discussion and limitations
check_true("Discussion: in each multi-bank event at least one bank falls in a different band", all(bk(e).band.nunique() > 1 for e in (FB, DP, WT, AM)), "")
check_text("Discussion (text)", "in each of the four multi-bank events of the panel at least one bank, scored alone, falls in a different band from the "
           "others, and the consolidated score can lie above or below every bank's score")
seven = MB[(MB.row == "bank") & (MB.in_primary_panel == 0)]
check_true("Limitations: the seven banks below the size cut have Value scores of zero", len(seven) == 7 and (seven.V_score == 0).all(), "")
check_text("Limitations (text)", "The seven banks below the size cut enter only through their events")
# release 4.13: 'Conclusion: event level' reworded; checked in the release 4.13 block below
# ------------------------------------------------------------ SVB's deposits at three dates (release 4.4)
STG = pd.read_csv(FW / "data/SVB_Deposit_Stages.csv").set_index("stage")
SST = pd.read_csv(R / "table_svb_deposit_stages.csv")
SBE = pd.read_csv(R / "table_svb_deposit_breakeven.csv").set_index(["variant", "bounds"])
VA, VL = "deposits and assets", "deposits, assets and deposit change"
CR, AF, AS = "last call report", "at failure", "assumed by the acquirer"


def sst(stage, bounds="all 55", variant=VA):
    return SST[(SST.stage == stage) & (SST.bounds == bounds) & (SST.variant == variant)].iloc[0]


sv0 = p55[p55.transaction_id == "PA-0006"].iloc[0]
dcr, daf, das = (float(STG.loc[k].deposits_usd_bn) for k in (CR, AF, AS))
c_, f_, a_, a54 = sst(CR), sst(AF), sst(AS), sst(AS, "other 54")
check_true("deposit stages: the call-report row equals the panel's inputs; only it is in the information set",
           dcr == sv0.G_deposits_usd_bn and STG.loc[CR].assets_usd_bn == sv0.failed_assets_usd_bn and list(STG.in_information_set) == [1, 0, 0], "")
check_text("VI-B: deposits at the call report", f"\\${dcr:.1f} billion at December~31, 2022")
check_text("VI-B: deposits at failure", f"its deposits were about \\${daf:.0f} billion")
check_text("VI-B: deposits assumed", f"First Citizens assumed \\${das:.2f} billion")
check_true("VI-B: the deposits assumed are less than a third of the call-report figure", das / dcr < 1 / 3, f"{das / dcr:.3f}")
check_text("VI-B: less than a third (text)", "less than a third of the reported figure")
rel_as = STG.loc[AS].assets_usd_bn / sv0.buyer_assets_usd_bn_lag90
check_text("VI-B: assets taken on and relative size", f"the relative size stays above its cap even with the \\${STG.loc[AS].assets_usd_bn:.1f} billion of assets that First Citizens took "
           f"on~\\cite{{firstcitizens2023}}, {rel_as:.2f} times its own assets")
check_true("VI-B: the relative size stays above its cap (E = 1) at every date and on both bounds",
           (SST.relative_size > SST.relative_size_cap).all() and (SST.E_n > 1 - 1e-9).all(), "")
check_text("VI-B: V and S*", f"$V$ falls from {f3_(c_.V_score)} to {f3_(a_.V_score)} and $S^*$ from {f3_(c_.S_adj)} to {f3_(a_.S_adj)}, from the highest "
           "score in the panel to the fourth")
check_true("VI-B: rank 1 with the call-report deposits, 4 with the deposits assumed", int(c_.rank_S_adj_of_55) == 1 and int(a_.rank_S_adj_of_55) == 4, "")
check_true("VI-B: SVB's own score is the upper bound of the full-panel rescaling", abs(svb["fit_parameters"]["S_max"] - c_.S_adj) < 1e-12, "")
check_text("VI-B: rescaled score on the full-panel bounds", f"on those bounds the rescaled score falls to {f3_(a_.S_final)}, in the {a_.band} zone")
be55, be54 = SBE.loc[(VA, "all 55")], SBE.loc[(VA, "other 54")]
check_text("VI-B: break-even deposits on the full-panel bounds", f"only with deposits above \\${be55.deposits_needed_usd_bn:.1f} billion, a level that "
           "the deposits at failure exceed")
check_true("VI-B: the deposits at failure exceed that level (Pursue) and the deposits assumed do not",
           daf > be55.deposits_needed_usd_bn > das and f_.band == "Pursue", f"{be55.deposits_needed_usd_bn:.2f}")
check_text("VI-B: bounds without SVB", f"the threshold is \\${be54.deposits_needed_usd_bn:.1f} billion and the score is {f3_(a54.S_final)}, in the "
           f"{a54.band} zone")
check_true("VI-B: near the Pursue boundary: Caution on the full-panel bounds, Pursue without SVB",
           a_.band == "Caution" and a54.band == "Pursue" and be54.deposits_needed_usd_bn < das, "")
dl = [sst(st, b, VL).S_adj - sst(st, b, VA).S_adj for st in (AF, AS) for b in ("all 55", "other 54")]
check_true("VI-B: letting L react (rule U) adds the same amount to each substituted S* and changes no zone",
           max(dl) - min(dl) < 1e-12 and all(sst(st, b, VL).band == sst(st, b, VA).band for st in (AF, AS) for b in ("all 55", "other 54")),
           f"{dl[0]:.4f}")
check_text("VI-B: L and rule U (text)", f"would add {dl[0]:.3f} to each substituted $S^*$ and change no zone")
check_text("VI-B: contributions of protection and of the deposits assumed", f"its protection, which contributes {0.20 * svb['scores']['P_score']:.3f} "
           f"to $S^*$, outweighs its deposit franchise, which contributes {0.30 * a_.V_score:.3f}")
check_true("VI-B: price terms as in the source document", "without a premium" in STG.loc[AS].source and "$16.45 billion" in STG.loc[AS].source, "")
check_text("VI-B: price terms (text)", "assumed the deposits without a premium and bought the assets at a discount of \\$16.45 billion")
bb = led[led.transaction_id.isin(p55.transaction_id) & (led.bridge_bank == 1)]
check_true("III-B: SVB is the one bridge-bank sale in the panel", list(bb.transaction_id) == ["PA-0006"] and int(p55.H_support_narrow.sum()) == 1, "")
check_text("III-B (text)", "Section~\\ref{sec:svb} shows how large the difference was for SVB, the one bridge-bank sale in the panel")
lag = p55.failed_report_lag_days
check_text("Limitations: lag of the last call report", f"predates the failure by {int(lag.min())} to {int(lag.max())} days (median {lag.median():.0f})")
check_true("Limitations: SVB lost more than two-thirds of its reported deposits", 1 - das / dcr > 2 / 3, f"{1 - das / dcr:.3f}")
check_text("Limitations (text)", "SVB lost more than two-thirds of its reported deposits before First Citizens assumed them")
check_text("Conclusion (text)", "the deposits First Citizens assumed, less than a third as large, the transaction ranks fourth and lies near the Pursue boundary")

# ------------------------------------------------------------ the bank-sector benchmark as a co-primary outcome (release 4.5)
BMC = pd.read_csv(R / "table_bank_main_comparison.csv").set_index("model")
SMC = pd.read_csv(R / "table_main_comparison.csv").set_index("model")
BMR = pd.read_csv(R / "bank_main_by_repeat.csv")
FITTED = [m for m in BMC.index if m != SCm]
f2 = lambda x: f"{x:.2f}"
pct1 = lambda x: f"{100 * x:.1f}".replace("-", "$-$")
# VII-A, Panel B
check_true("bank: 39 positive labels and every fitted model below one half", int(yb.sum()) == 39 and BMC.loc[FITTED, "AUC_mean"].max() < 0.5,
           f"max {BMC.loc[FITTED, 'AUC_mean'].max():.3f}")
top_b = BMC.loc[FITTED, "AUC_mean"].idxmax()
check_true("bank: the LASSO model has the highest mean AUC of the fitted models", top_b == "LASSO logistic", top_b)
check_text("VII-A bank: AUCs", f"one half: {f(BMC.loc[LRm, 'AUC_mean'])} for Model~2 and {f(BMC.loc[RIm, 'AUC_mean'])} for ridge regression, "
           f"{f(BMC.loc[M3m, 'AUC_mean'])} for Model~3, and at most {f(BMC.loc['LASSO logistic', 'AUC_mean'])}, for the LASSO model")
p95 = BMC.loc[FITTED, "AUC_p95"]
check_true("bank: the 95th percentile is below one half for every fitted model but the LASSO model", p95.drop("LASSO logistic").max() < 0.5 <= p95["LASSO logistic"],
           ", ".join(f"{v:.3f}" for v in p95))
ev_b = BMC.loc[FITTED, "AUC_event_mean"]
check_text("VII-A bank: event-weighted range", f"Counting each event once gives {f(ev_b.min())} to {f(ev_b.max())}.")
check_text("VII-A bank: Brier of the training-fold share", f"of positive outcomes ({f(BMR.Brier_prevalence.mean())}), with a Brier skill from "
           f"{pct1(BMC.loc[FITTED, 'Brier_skill_mean'].max())}\\% for the\nLASSO model to {pct1(BMC.loc[FITTED, 'Brier_skill_mean'].min())}\\% for the decision tree")
check_true("bank: every Brier skill negative; LASSO highest, tree lowest", BMC.loc[FITTED, "Brier_skill_mean"].max() < 0
           and BMC.loc[FITTED, "Brier_skill_mean"].idxmax() == "LASSO logistic" and BMC.loc[FITTED, "Brier_skill_mean"].idxmin() == "Decision tree", "holds")
check_text("VII-A bank: Spider score", f"The Spider score has a\nmean AUC of {f(BMC.loc[SCm, 'AUC_mean'])}.")
rkb_ = pd.read_csv(R / "table_bank_rank_by_group.csv").set_index("model").iloc[:, 0]
check_text("VII-A bank: FBOP ranks", f"(mean percentile rank {f2(rkb_[LRm])} and {f2(rkb_[RIm])}) and in the\nlowest quarter by Model~3 ({f2(rkb_[M3m])})")
check_true("bank: Model 3's FBOP rank in the lowest quarter", rkb_[M3m] < 0.25, f"{rkb_[M3m]:.3f}")
# VII-B, Panel B: paired differences and bootstraps
BPD = pd.read_csv(R / "table_bank_paired_differences.csv")


def bpd(other, metric="AUC", col="mean"):
    return float(BPD[(BPD.comparison == f"SNFF minus {other}") & (BPD.metric == metric)][col].iloc[0])


check_text("VII-B bank: differences with Model 2 and ridge", f"Model~3's AUC is higher than Model~2's by {f(bpd(LRm))} and than\nridge regression's by "
           f"{f(bpd(RIm))}, in every one of the 50 partitions")
check_true("bank: Model 3 above Model 2 and ridge in every partition", bpd(LRm, col="share_SNFF_better") == 1 and bpd(RIm, col="share_SNFF_better") == 1, "holds")
check_text("VII-B bank: differences with RF, XGBoost, pairwise", f"by {f(bpd(RFm))}, {f(bpd('XGBoost'))}, and {f(bpd(PAm))} on average")
check_true("bank: those three differences positive", min(bpd(RFm), bpd("XGBoost"), bpd(PAm)) > 0, "holds")
check_text("VII-B bank: Brier lower than Model 2's", f"its Brier score is lower than\nModel~2's by {f(-bpd(LRm, 'Brier'))} and close to ridge regression's")
check_true("bank: Brier difference with ridge within 0.002", abs(bpd(RIm, "Brier")) < 0.002, f"{bpd(RIm, 'Brier'):+.4f}")
BCB = pd.read_csv(R / "table_bank_cluster_bootstrap.csv").set_index("quantity")
sg3 = lambda x: f"{x:+.3f}".replace("+", "$+$").replace("-", "$-$")
cbl, cbr = BCB.loc[f"AUC difference SNFF minus {LRm}"], BCB.loc[f"AUC difference SNFF minus {RIm}"]
check_text("VII-B bank: conditional bootstrap differences", f"exclude zero ([{sg3(cbl.ci_low)}, {sg3(cbl.ci_high)}] and [{sg3(cbr.ci_low)}, {sg3(cbr.ci_high)}])")
check_true("bank: both conditional difference intervals above zero", cbl.ci_low > 0 and cbr.ci_low > 0, "holds")
cal_, car_ = BCB.loc[f"AUC {LRm}"], BCB.loc[f"AUC {RIm}"]
check_text("VII-B bank: conditional AUC intervals", f"below one half ([{f(cal_.ci_low)}, {f(cal_.ci_high)}] and [{f(car_.ci_low)}, {f(car_.ci_high)}])")
check_true("bank: those AUC intervals wholly below one half", cal_.ci_high < 0.5 and car_.ci_high < 0.5, "holds")
BRF = pd.read_csv(R / "table_bank_bootstrap_refit.csv").set_index("quantity")
lows = [BRF.loc[f"AUC {m}"].ci_low for m in (LRm, RIm, M3m)]
highs = [BRF.loc[f"AUC {m}"].ci_high for m in (LRm, RIm, M3m)]
check_true("bank refitting bootstrap: AUC intervals 'from about 0.13 to 0.68', each containing one half",
           all(abs(x - 0.13) <= 0.03 for x in lows) and all(abs(x - 0.68) <= 0.01 for x in highs) and max(lows) < 0.5 < min(highs),
           ", ".join(f"[{a:.3f}, {b:.3f}]" for a, b in zip(lows, highs)))
rdl, rdr = BRF.loc[f"diff SNFF minus {LRm}"], BRF.loc[f"diff SNFF minus {RIm}"]
check_text("VII-B bank: refitting bootstrap differences", f"and [{sg3(rdl.ci_low)}, {sg3(rdl.ci_high)}] and [{sg3(rdr.ci_low)}, {sg3(rdr.ci_high)}] for\nModel~3's differences")
check_text("VII-B bank: share of resamples with a negative difference", f"negative in only {100 * rdl.share_below_zero:.0f}\\% and\n{100 * rdr.share_below_zero:.0f}\\% of the resamples")
check_true("bank refitting bootstrap: 500 replicates, none skipped", int(BRF.replicates.iloc[0]) == 500 and int(BRF.skipped.iloc[0]) == 0, "holds")
# VII-B, Panel B: permutation tests under both benchmarks, two-sided, and the differences
PCP = pd.read_csv(R / "table_permutation_coprimary.csv")


def pcp(bench, model, col):
    return float(PCP[(PCP.benchmark == bench) & (PCP.model == model)][col].iloc[0])


SB, BB = "SPY", "bank-sector index"
check_true("co-primary permutation table: SPY rows equal the release 4.4 permutation table",
           all(abs(pcp(SB, m, "observed_mean_AUC") - float(pt.loc[m, "observed_mean_AUC"])) < 1e-12 for m in (LRm, RIm, M3m)), "holds")
check_text("VII-B bank: observed AUCs", f"observed AUCs of\nModel~2 ({f(pcp(BB, LRm, 'observed_mean_AUC'))}), ridge regression ({f(pcp(BB, RIm, 'observed_mean_AUC'))}), "
           f"and Model~3 ({f(pcp(BB, M3m, 'observed_mean_AUC'))}) lie\nbelow the permutation mean ({f2(pcp(BB, LRm, 'null_mean'))})")
check_true("bank: null means of the three models round to the same value", len({f2(pcp(BB, m, "null_mean")) for m in (LRm, RIm, M3m)}) == 1, "holds")
check_text("VII-B bank: two-sided p", f"(two-sided\n$p = {f2(pcp(BB, LRm, 'p_two_sided'))}$, {f2(pcp(BB, RIm, 'p_two_sided'))}, and {f2(pcp(BB, M3m, 'p_two_sided'))}; "
           f"{f2(pcp(BB, LRm, 'p_holm_two_sided'))} for each after a Holm adjustment)")
check_true("bank: the Holm-adjusted two-sided p is the same for the three models", len({round(pcp(BB, m, "p_holm_two_sided"), 6) for m in (LRm, RIm, M3m)}) == 1, "holds")
check_text("VII-B bank: share of permuted runs", f"occur in {100 * pcp(BB, LRm, 'p_two_sided'):.0f}\\%, {100 * pcp(BB, RIm, 'p_two_sided'):.0f}\\%, and "
           f"{100 * pcp(BB, M3m, 'p_two_sided'):.0f}\\% of the permuted runs")
check_text("VII-B bank: Spider score", f"the Spider score is at chance ({f(pcp(BB, SCm, 'observed_mean_AUC'))}, $p = {f2(pcp(BB, SCm, 'p_two_sided'))}$)")
check_text("VII-B bank: Model 2's permutation interval", f"For Model~2, 95\\% of\nthe permuted AUCs lie between {f2(pcp(BB, LRm, 'null_p025'))} and {f2(pcp(BB, LRm, 'null_p975'))}")
check_true("bank: every fitted model's observed AUC above its permutation 2.5th percentile", all(pcp(BB, m, "observed_mean_AUC") > pcp(BB, m, "null_p025")
           for m in (LRm, RIm, M3m)), "holds")
for bench, lab in ((SB, "S\\&P~500"), (BB, "bank-sector benchmark")):
    pass
dS = [pcp(SB, f"SNFF minus {m}", c) for m in (LRm, RIm) for c in ("observed_mean_AUC", "p_two_sided")]
dB = [pcp(BB, f"SNFF minus {m}", c) for m in (LRm, RIm) for c in ("observed_mean_AUC", "p_two_sided")]
check_text("VII-B: Model 3's differences under the S&P 500", f"Against the S\\&P~500, its differences with\nModel~2 ({sg3(dS[0]).replace('$+$', '')}) and ridge regression "
           f"({sg3(dS[2]).replace('$+$', '')}) have two-sided\n$p$-values of {f2(dS[1])} and {f2(dS[3])}")
check_text("VII-B: Model 3's differences under the bank-sector benchmark", f"against the bank-sector benchmark\n({sg3(dB[0])} and {sg3(dB[2])}), of "
           f"{f2(dB[1])} and {f2(dB[3])}")
check_true("no difference distinguishable from chance (two-sided p >= 0.10)", min(dS[1], dS[3], dB[1], dB[3]) >= 0.10, "holds")
check_true("bank permutation: 400 permutations", len(pd.read_csv(R / "bank_permutation_null.csv")) == 400, "holds")
# VII-D: the FBOP cluster under both benchmarks
FBI = pd.read_csv(R / "table_fbop_influence.csv")
AL, WO = "all 55 transactions", "without the FBOP cluster"


def fbi(oc, sample, m, col="AUC_mean"):
    return float(FBI[(FBI.outcome == oc) & (FBI["sample"] == sample) & (FBI.model == m)][col].iloc[0])


check_true("FBOP table: Model 2 equals the cluster-influence check (both benchmarks, with and without the cluster)",
           all(abs(fbi(oc, smp, LRm) - float(fi[(fi.outcome == lab) & (fi["sample"] == smp)].AUC_mean.iloc[0])) < 1e-12
               for oc, lab in (("y", VP.replace(" (primary)", ", SPY (primary)")), ("y_bank", VB)) for smp in (AL, WO)), "holds")
check_true("FBOP table: the all-55 rows equal the main comparisons", all(abs(fbi("y", AL, m) - SMC.loc[m, "AUC_mean"]) < 1e-12 and
           abs(fbi("y_bank", AL, m) - BMC.loc[m, "AUC_mean"]) < 1e-12 for m in (LRm, RIm, M3m, SCm)), "holds")
check_text("VII-D: Spider score's FBOP ranks", f"in its upper third (mean percentile rank {f2(fbi('y', AL, SCm, 'fbop_mean_percentile_rank'))} and "
           f"{f2(fbi('y_bank', AL, SCm, 'fbop_mean_percentile_rank'))})")
check_true("Spider score's FBOP rank in the upper third under both", min(fbi("y", AL, SCm, "fbop_mean_percentile_rank"), fbi("y_bank", AL, SCm, "fbop_mean_percentile_rank")) > 2 / 3, "holds")
check_text("VII-D: FBOP under the S&P 500", f"this lowers the mean AUC of Model~2\nfrom {f(fbi('y', AL, LRm))} to {f(fbi('y', WO, LRm))}, of ridge regression from "
           f"{f(fbi('y', AL, RIm))} to {f(fbi('y', WO, RIm))}, and of\nModel~3 from {f(fbi('y', AL, M3m))} to {f(fbi('y', WO, M3m))}, and raises the Spider score's from "
           f"{f(fbi('y', AL, SCm))}\nto {f(fbi('y', WO, SCm))}")
check_text("VII-D: FBOP under the bank-sector benchmark", f"it raises the three\nmodels' AUCs from {f(fbi('y_bank', AL, LRm))} to {f(fbi('y_bank', WO, LRm))}, from "
           f"{f(fbi('y_bank', AL, RIm))} to {f(fbi('y_bank', WO, RIm))}, and from {f(fbi('y_bank', AL, M3m))}\nto {f(fbi('y_bank', WO, M3m))}, and lowers the Spider score's from "
           f"{f(fbi('y_bank', AL, SCm))} to {f(fbi('y_bank', WO, SCm))}")
gap = {m: (fbi("y", AL, m) - fbi("y_bank", AL, m), fbi("y", WO, m) - fbi("y_bank", WO, m)) for m in (LRm, RIm, M3m)}
check_text("VII-D: gap between the benchmarks", f"shrinks from\n{f(gap[LRm][0])} to {f(gap[LRm][1])} for Model~2 and from {f(gap[RIm][0])} to {f(gap[RIm][1])} "
           f"for ridge\nregression, and for Model~3 it changes sign ({sg3(gap[M3m][1])})")
check_true("Model 3's gap changes sign", gap[M3m][0] > 0 > gap[M3m][1], "holds")
w8 = [fbi(oc, WO, m) for oc in ("y", "y_bank") for m in (LRm, RIm, M3m, SCm)]
check_true("without FBOP: all eight AUCs between 0.41 and 0.52", 0.41 <= min(w8) and max(w8) <= 0.52, f"{min(w8):.3f} to {max(w8):.3f}")
# V-E and Table 5: the two co-primary outcomes
BKF = pd.read_csv(ROOT / "05_manuscript_analysis_2026-10-29/data/Bank_Benchmark_CAR_90.csv").set_index("transaction_id")
carb = p55.transaction_id.map(BKF.car_reaction_m1p1_bank)
check_text("V-E: correlation of the two CARs", f"The two CARs are highly correlated\n({f(p55.car_reaction_m1p1.corr(carb))})")
flip = (yb != p55.y)
grp55 = p55.listed_parent_ticker.astype(str) + "|" + p55.first_reaction_date.astype(str)
w_ = {10: "ten", 6: "six", 8: "eight"}
check_text("V-E: label changes and their clusters", f"but {w_.get(int(flip.sum()), '?')} labels differ, in {w_.get(grp55[flip].nunique(), '?')} event clusters, and "
           f"{w_.get(int((flip & (p55.car_reaction_m1p1.abs() < 0.01)).sum()), '?')} of\nthese ten transactions have an SPY-adjusted CAR within one percentage\npoint of zero")
fb_spy, fb_bank = p55[fbop].car_reaction_m1p1.iloc[0], carb[fbop].iloc[0]
check_true("V-E: one CAR per benchmark for the FBOP cluster", p55[fbop].car_reaction_m1p1.nunique() == 1 and carb[fbop].nunique() == 1, "holds")
check_text("V-E: the FBOP CARs", f"whose CAR is\n$-{abs(100 * fb_spy):.1f}\\%$ against SPY and $+{100 * fb_bank:.1f}\\%$ against the bank-sector benchmark")
check_text("Table 5: the labels of both outcomes", f"& Target & {int(p55.y.sum())} of 55 (SPY); {int(yb.sum())} (bank) \\\\")
check_text("limitations: the six events whose labels depend on the benchmark", f"around some of the {w_.get(grp55[flip].nunique(), '?')} events whose\nlabels depend on the benchmark")
# VII-C, Panel B: ablation
BAB = pd.read_csv(R / "table_bank_ablation.csv").set_index("model")
BABR = pd.read_csv(R / "bank_ablation_by_repeat.csv").pivot_table(index="repeat", columns="model", values="AUC")
STA, STB, STC, STD, STE, STF = ("A: measured inputs", "B: A + Spider score", "C: A + interaction rules", "D: full SNFF (Model 3)",
                                "E: D without protection inputs", "F: D without buyer capital")
check_true("bank ablation: stage A is the ridge model of Panel B", abs(BAB.loc[STA, "AUC_mean"] - BMC.loc[RIm, "AUC_mean"]) < 1e-12, "holds")
check_text("VII-C bank: stages", f"stage~A ranks below\none half ({f(BAB.loc[STA, 'AUC_mean'])}), and the same additions move the AUC the other way. "
           f"Adding the Spider score leaves it essentially unchanged ({f(BAB.loc[STB, 'AUC_mean'])}), whereas adding the interaction rules raises it to "
           f"{f(BAB.loc[STC, 'AUC_mean'])}, above stage~A\nin every partition, and the full specification to {f(BAB.loc[STD, 'AUC_mean'])}; removing the "
           f"protection inputs leaves it at {f(BAB.loc[STE, 'AUC_mean'])}, and removing buyer capital raises\nit to {f(BAB.loc[STF, 'AUC_mean'])}")
check_true("bank ablation: C above A in every partition; B within 0.005 of A; E within 0.005 of D; F above D", ((BABR[STC] - BABR[STA]) > 0).all()
           and abs(BAB.loc[STB, "AUC_mean"] - BAB.loc[STA, "AUC_mean"]) < 0.005 and abs(BAB.loc[STE, "AUC_mean"] - BAB.loc[STD, "AUC_mean"]) < 0.005
           and BAB.loc[STF, "AUC_mean"] > BAB.loc[STD, "AUC_mean"], "holds")
check_true("ablation: the rules move the AUC toward one half in both panels (A to C)", ab.loc[STA, "AUC_mean"] > ab.loc[STC, "AUC_mean"] > 0.5
           and BAB.loc[STA, "AUC_mean"] < BAB.loc[STC, "AUC_mean"] < 0.5, "holds")
check_true("bank ablation: no stage reaches one half", BAB.AUC_mean.max() < 0.5, f"max {BAB.AUC_mean.max():.3f}")
# VII-D, Panel B: specifications and samples
BRB = pd.read_csv(R / "table_bank_robustness.csv")
BBR = pd.read_csv(R / "table_bank_broader90.csv").set_index("model")
BEV = pd.read_csv(R / "table_bank_event_level.csv").set_index("model")


def brb(variant, m):
    return float(BRB[(BRB.variant == variant) & (BRB.model == m)].AUC_mean.iloc[0])


rowsB = {"main": {m: BMC.loc[m, "AUC_mean"] for m in (LRm, RIm, M3m, SCm)}}
for v in (VPUB, VBR, VUH, VZ):
    rowsB[v] = {m: brb(v, m) for m in (LRm, RIm, M3m, SCm)}
rowsB["fbop"] = {m: fbi("y_bank", WO, m) for m in (LRm, RIm, M3m, SCm)}
rowsB["broader"] = {m: BBR.loc[m, "AUC_mean"] for m in (LRm, RIm, M3m, SCm)}
rowsB["events"] = {m: BEV.loc[m, "AUC_mean"] for m in (LRm, RIm, M3m, SCm)}
base_ = [r[m] for r in rowsB.values() for m in (LRm, RIm)]
m3_ = [r[M3m] for r in rowsB.values()]
sc_ = [r[SCm] for r in rowsB.values()]
check_true("Panel B: Model 2, ridge and Model 3 below one half in every row", max(base_ + m3_) < 0.5, f"max {max(base_ + m3_):.3f}")
check_true("Panel B: Model 3 above both baselines in every row", all(r[M3m] > max(r[LRm], r[RIm]) for r in rowsB.values()), "holds")
check_text("VII-D Panel B: ranges", f"from {f(min(base_))} to {f(max(base_))} for\nthe two logistic baselines and from {f(min(m3_))} to {f(max(m3_))} for Model~3, "
           f"which\nranks above both in every row; the Spider score lies between {f(min(sc_))} and\n{f(max(sc_))}")
BEPOL = pd.read_csv(R / "table_bank_event_level_decision_policies.csv").set_index("policy")
check_text("VII-D Panel B: published inputs and events", f"Without the deal terms the three models reach {f(rowsB[VPUB][LRm])}, {f(rowsB[VPUB][RIm])}, and\n"
           f"{f(rowsB[VPUB][M3m])}, and among the 51 acquisition events, of which {int(BEPOL.loc['Pursue all', 'TP'])} have a positive\nCAR, "
           f"{f(rowsB['events'][LRm])}, {f(rowsB['events'][RIm])}, and {f(rowsB['events'][M3m])}")
above = BBR.drop(index=[LRm, RIm, M3m]).AUC_mean
above = above[above > 0.5].sort_values(ascending=False)
check_true("Panel B broader panel: above one half exactly XGBoost, random forest, tree, pairwise, Spider score",
           set(above.index) == {"XGBoost", RFm, "Decision tree", PAm, SCm}, str(above.round(3).to_dict()))
check_true("broader panel: tree and pairwise round to the same AUC", f(BBR.loc["Decision tree", "AUC_mean"]) == f(BBR.loc[PAm, "AUC_mean"]), "holds")
check_text("VII-D Panel B: broader panel", f"In the broader panel, where they reach\n{f(rowsB['broader'][LRm])}, {f(rowsB['broader'][RIm])}, and {f(rowsB['broader'][M3m])}, "
           f"XGBoost ({f(BBR.loc['XGBoost', 'AUC_mean'])}), the random forest ({f(BBR.loc[RFm, 'AUC_mean'])}),\nthe decision tree and the pairwise model "
           f"({f(BBR.loc[PAm, 'AUC_mean'])} each), and the Spider\nscore ({f(BBR.loc[SCm, 'AUC_mean'])}) rank above one half")
# VII-E: calibration, Panel B of the figure
BCAL = pd.read_csv(R / "table_bank_calibration_bins.csv")


def bcal(model, b, col):
    return float(BCAL[(BCAL.model == model) & (BCAL.bin == b)][col].iloc[0])


BOO = pd.read_csv(R / "bank_out_of_fold_predictions.csv")
bmp = BOO[BOO.model.isin([LRm, RIm, M3m])].groupby("model").prediction.mean()
check_text("VII-E bank: overall share", f"(mean predictions of\n{f2(bmp.min())} to {f2(bmp.max())} against an observed share of {f2(BOO.y.mean())})")
check_text("VII-E bank: Model 2's extreme quintiles", f"which average {f(bcal(LRm, 1, 'mean_prediction'))} and\n{f(bcal(LRm, 5, 'mean_prediction'))}, "
           f"the observed shares are {f(bcal(LRm, 1, 'observed_rate'))} and {f(bcal(LRm, 5, 'observed_rate'))}")
check_text("VII-E bank: ridge", f"ridge regression shows\nthe same reversal ({f(bcal(RIm, 1, 'observed_rate'))} and {f(bcal(RIm, 5, 'observed_rate'))})")
check_text("VII-E bank: Model 3", f"with\n{f(bcal(M3m, 1, 'observed_rate'))} in its lowest quintile, {f(bcal(M3m, 4, 'observed_rate'))} in its fourth, and "
           f"{f(bcal(M3m, 5, 'observed_rate'))} in its\nhighest")
check_true("VII-E bank: observed share falls across the quintiles of Model 2 and ridge; each lowest quintile has the highest share",
           all(all(bcal(m, k + 1, "observed_rate") < bcal(m, k, "observed_rate") for k in range(1, 5)) for m in (LRm, RIm))
           and all(bcal(m, 1, "observed_rate") == max(bcal(m, k, "observed_rate") for k in range(1, 6)) for m in (LRm, RIm, M3m)), "holds")
# VII-F, Panel B: components
BCO = pd.read_csv(R / "table_bank_spider_components.csv")
b55 = BCO[BCO.deals == D55].set_index("component")
b28 = BCO[BCO.deals == D28].set_index("component")
comps = ["V_score", "P_score", "B_score", "R_score", "E_score"]
pfl = int(b55.p_two_sided.min() * 100) / 100
check_text("VII-F bank: the primary panel", f"the AUCs lie between\n{f(b55.loc[comps, 'AUC'].min())} and {f(b55.loc[comps, 'AUC'].max())}, every $p$-value is at least "
           f"{pfl:.2f}, and the Spider\nscore's AUC is {f(b55.loc['S_final', 'AUC'])} ($p = {f2(b55.loc['S_final', 'p_two_sided'])}$)")
check_true("VII-F bank: the Spider score's AUC lies inside the components' range", b55.loc[comps, "AUC"].min() <= b55.loc["S_final", "AUC"] <= b55.loc[comps, "AUC"].max(), "holds")
check_text("VII-F bank: the 28", f"Buyer Strength has an AUC of {f(b28.loc['B_score', 'AUC'])} ($p = {b28.loc['B_score', 'p_two_sided']:.3f}$), in the\ndirection the "
           f"framework assumes, and Risk {f(b28.loc['R_score', 'AUC'])} ($p = {f2(b28.loc['R_score', 'p_two_sided'])}$)")
oth = b28.drop(index=["B_score", "R_score"]).AUC
check_true("VII-F bank: the other components and the Spider score within 0.09 of one half in the 28", (oth - 0.5).abs().max() < 0.09, f"{(oth - 0.5).abs().max():.3f}")
check_true("VII-F bank: Risk row equals Table 13", abs(b55.loc["R_score", "AUC"] - float(rvt[(rvt.deals == D55) & (rvt.outcome == VB)].AUC_R.iloc[0])) < 1e-12, "holds")
# VII-H, Panel B and D: Model 4
BPOL = pd.read_csv(R / "table_bank_decision_policies.csv").set_index("policy")
BSW = pd.read_csv(R / "table_bank_cost_ratio_sweep.csv").set_index("ratio")
f3n = lambda x: f"{x:.3f}".replace("-", "$-$") if x >= 0 else f"$-{abs(x):.3f}$"
b4a, b4b, b4c, ball = (BPOL.loc[k] for k in ("4A: fixed Spider thresholds", "4B: F1-tuned threshold", "4C: cost-based threshold (3:1)", "Pursue all"))
check_text("VII-H bank: pursue all", f"39 of the 55\ntransactions have a positive CAR, so pursuing every transaction loses\nless ($-{abs(ball.utility_3to1):.3f}$) "
           f"and again attains the highest F1 score ({f(ball.F1)})")
check_true("VII-H bank: pursue-all F1 highest of any policy", ball.F1 == BPOL.F1.max(), "holds")
check_text("VII-H bank: 4B", f"Configuration~4B recommends Pursue on {b4b.pursue:.1f} of 55 transactions on average,\napproves {100 * b4b.FPR:.1f}\\% of the "
           f"{int(ball.FP)} acquisitions with a negative CAR, and\nrealizes $-{abs(b4b.utility_3to1):.3f}$, less than pursuing every transaction")
check_true("VII-H bank: 4B below pursue-all", b4b.utility_3to1 < ball.utility_3to1, "holds")
check_text("VII-H bank: 4C and 4A", f"Configuration~4C pursues {b4c.pursue:.1f} of the 55 transactions with a false-positive rate of\n{100 * b4c.FPR:.1f}\\% and realizes "
           f"$-{abs(b4c.utility_3to1):.3f}$; and Configuration~4A pursues about three of the 55\ntransactions per partition for a small positive utility ({f(b4a.utility_3to1)})")
check_true("VII-H bank: 4A pursues about three", round(b4a.pursue) == 3 and b4a.utility_3to1 > 0, f"{b4a.pursue:.2f}")
pa = {r: (39 - r * 16) / 55 for r in BSW.index}
check_true("VII-H bank sweep: loses to the better trivial policy at every ratio; pursue-all better at 1:1 and 2:1, none from 3:1",
           (BSW.gain_vs_trivial < 0).all() and pa[1] > 0 and pa[2] > 0 and all(pa[r] < 0 for r in (3, 4, 5)), str(BSW.gain_vs_trivial.round(3).to_dict()))
check_text("VII-H bank sweep: gains at 1:1 and 2:1", f"to pursuing every\ntransaction at 1:1 and 2:1, by {f(-BSW.loc[1, 'gain_vs_trivial'])} and {f(-BSW.loc[2, 'gain_vs_trivial'])}")
check_true("VII-H bank sweep: every threshold negative at 3:1", (BSW.utility_3to1 < 0).all(), "holds")
e4a, e4b, e4c, eall = (BEPOL.loc[k] for k in ("4A: fixed Spider thresholds", "4B: F1-tuned threshold", "4C: cost-based threshold (3:1)", "Pursue all"))
check_text("VII-H bank events (Panel D)", f"Configuration~4A pursues about\nthree of the 51 events per partition for a small positive utility ({f(e4a.utility_3to1)}), 4C and\n"
           f"4B realize $-{abs(e4c.utility_3to1):.3f}$ and $-{abs(e4b.utility_3to1):.3f}$, and pursuing every event $-{abs(eall.utility_3to1):.3f}$")
allpol = [pol, BPOL, EPOL, BEPOL]
check_true("VII-H: same conclusions under both benchmarks (4B approves most negatives; 4C below zero; only 4A positive)",
           all(t.loc["4B: F1-tuned threshold", "FPR"] > 0.5 and t.loc["4C: cost-based threshold (3:1)", "utility_3to1"] < 0
               and t.loc["4A: fixed Spider thresholds", "utility_3to1"] > 0 and (t.drop(index="4A: fixed Spider thresholds").utility_3to1 <= 0).all()
               and round(t.loc["4A: fixed Spider thresholds", "pursue"]) == 3 for t in allpol), "holds")
# Discussion VIII-B: 4A pursues SVB and First Republic in every partition against the bank-sector benchmark
sc_b = BOO[BOO.model == SCm]
hi_b = sc_b[sc_b.prediction >= 0.70].groupby("transaction_id").repeat.nunique()
every = set(hi_b[hi_b == sc_b.repeat.nunique()].index)
check_true("VIII-B: against the bank-sector benchmark 4A pursues SVB and First Republic in every partition, and no other transaction in every partition",
           every == {"PA-0006", "PA-0004"}, str(sorted(every)))
check_true("VIII-B: without them 4A's bank-sector utility would be negative", (b4a.TP - 2 - 3 * b4a.FP) < 0, f"{b4a.TP - 2 - 3 * b4a.FP:.2f}")
check_text("VIII-B: text", "the fixed-threshold rule's gain rests on SVB and First Republic, the two transactions it pursues in every partition")
# VII-I: events under the bank-sector benchmark
BEVR = pd.read_csv(R / "bank_event_level_by_repeat.csv")
pwe = BEVR.pivot_table(index="repeat", columns="model", values="AUC")
check_text("VII-I bank: events", f"Against the bank-sector benchmark, {int(eall.TP)} of the 51 events have a\npositive CAR, and the mean AUCs are "
           f"{f(BEV.loc[LRm, 'AUC_mean'])} for Model~2, {f(BEV.loc[RIm, 'AUC_mean'])} for ridge\nregression, {f(BEV.loc[M3m, 'AUC_mean'])} for Model~3, and "
           f"{f(BEV.loc[SCm, 'AUC_mean'])} for the Spider score; across\nthe eight models they range from {f(BEV.drop(index=SCm).AUC_mean.min())} to "
           f"{f(BEV.drop(index=SCm).AUC_mean.max())}")
check_text("VII-I bank: transaction-level comparison", f"(0.291 to 0.465 with each event counted\nonce)".replace("0.291", f(ev_b.min())).replace("0.465", f(ev_b.max())))
check_true("VII-I bank: events closer to one half than the transactions (both ends of the range)", BEV.drop(index=SCm).AUC_mean.min() > ev_b.min(), "holds")
check_text("VII-I bank: Brier and shares", f"Every Brier score is again higher than that of the training-fold\nshare ({f(BEVR.Brier_prevalence.mean())}), "
           f"and Model~3 ranks above Model~2 in {100 * ((pwe[M3m] - pwe[LRm]) > 0).mean():.0f}\\% of the\npartitions and above ridge regression in "
           f"{100 * ((pwe[M3m] - pwe[RIm]) > 0).mean():.0f}\\%")
check_true("VII-I bank: every Brier skill negative", (BEV.drop(index=SCm).Brier_skill_mean < 0).all(), "holds")
# VII-J: H1 under the bank-sector benchmark
check_text("VII-J bank: Model 3 against Model 2", f"Model~3 ranks above Model~2 in\nevery partition (AUC {f(BMC.loc[M3m, 'AUC_mean'])} against "
           f"{f(BMC.loc[LRm, 'AUC_mean'])}) and has a lower Brier score\n({f(BMC.loc[M3m, 'Brier_mean'])} against {f(BMC.loc[LRm, 'Brier_mean'])})")
check_text("VII-J bank: Brier against ridge and the base rate", f"its Brier score is about the same as ridge regression's ({f(BMC.loc[M3m, 'Brier_mean'])}\n"
           f"against {f(BMC.loc[RIm, 'Brier_mean'])}) and worse than that of predicting the training-fold\nshare ({f(BMR.Brier_prevalence.mean())})")
check_true("VII-J bank: Model 3's Brier within 0.005 of ridge's and above the base rate", abs(BMC.loc[M3m, "Brier_mean"] - BMC.loc[RIm, "Brier_mean"]) < 0.005
           and BMC.loc[M3m, "Brier_mean"] > BMR.Brier_prevalence.mean(), "holds")
check_text("VII-J bank: permutation p of the differences", f"outcomes carry no information ($p = {f2(dB[1])}$ and {f2(dB[3])})")
# VIII and the conclusion
check_true("VIII: (release 4.12) the range of the bank-sector AUCs is left to Table 7; every fitted model is below one half",
           BMC.loc[FITTED, 'AUC_mean'].max() < 0.5 and "below one half (0.277 to 0.461)" not in tex, f"{BMC.loc[FITTED, 'AUC_mean'].max():.3f}")
check_text("VIII: labels that change with the benchmark", f"and {nflip} with the choice of\nbenchmark")
check_text("conclusion: the three models against the bank-sector benchmark", f"all three ranked below one half\n({f(BMC.loc[M3m, 'AUC_mean'])}, "
           f"{f(BMC.loc[LRm, 'AUC_mean'])}, and {f(BMC.loc[RIm, 'AUC_mean'])})")
check_text("conclusion: the Spider score under both", f"(cross-validated AUC {f(SMC.loc[SCm, 'AUC_mean'])} and {f(BMC.loc[SCm, 'AUC_mean'])})")
check_true("conclusion: the Spider score not distinguishable from chance under either benchmark (two-sided p > 0.3)",
           pcp(SB, SCm, "p_two_sided") > 0.3 and pcp(BB, SCm, "p_two_sided") > 0.3, "holds")
# ------------------------------------------------------------ sensitivity to the expert constants (release 4.6)
WVA = pd.read_csv(R / "weight_sensitivity_variants.csv")
WSP = pd.read_csv(R / "weight_sensitivity_spider.csv", float_precision="round_trip").merge(WVA[["variant_id", "family", "label"]], on="variant_id")
WM3 = pd.read_csv(R / "weight_sensitivity_model3.csv", float_precision="round_trip").merge(WVA[["variant_id", "family", "label"]], on="variant_id")
WNE = pd.read_csv(R / "weight_sensitivity_nested_by_repeat.csv", float_precision="round_trip")
WCH = pd.read_csv(R / "weight_sensitivity_nested_choices.csv").merge(WVA.drop(columns=["family"]), on="variant_id")
WPT = pd.read_csv(R / "table_weight_sensitivity_permutation.csv", float_precision="round_trip")
fams = WVA.family.value_counts()
check_true("weights: 22 one-at-a-time, 3 structural, 1,000 + 1,000 random draws; Model 3 for 26 + 100 + 100",
           fams["one_at_a_time"] == 22 and fams["structural"] == 3 and fams["random_local"] == 1000 and fams["random_wide"] == 1000
           and int(WVA.model3.sum()) == 226 and WVA[WVA.model3].family.value_counts().get("random_local") == 100
           and WVA[WVA.model3].family.value_counts().get("random_wide") == 100, str(fams.to_dict()))
check_true("weights: every variant keeps the signs and component weights sum to one", (WVA[["wV", "wP", "wB", "wR", "wE"]] >= 0).all().all()
           and ((WVA[["wV", "wP", "wB", "wR", "wE"]].sum(axis=1) - 1).abs() < 1e-12).all() and (WVA[["cQ", "cU"]] >= 0).all().all()
           and (WVA[["cZ", "cK"]] <= 0).all().all(), "holds")
check_text("VII-E design: draws and Model 3 refits", "In 1,000 random draws, every constant varies independently between half and one and a half times its value; "
           "in 1,000 further draws")
check_text("VII-E design: Model 3 refits", "and the first 100 draws of each random set")


def wsp(bench, fam_=None, label=None):
    x = WSP[WSP.benchmark == bench]
    return x[x.label == label] if label else x[x.family == fam_]


for bench in ("SPY", "bank-sector index"):
    ref_ = wsp(bench, label="expert weights (reference)").AUC_mean.iloc[0]
    want = SMC.loc[SCm, "AUC_mean"] if bench == "SPY" else BMC.loc[SCm, "AUC_mean"]
    check_true(f"weights ({bench}): the reference equals Table 7's Spider score", abs(ref_ - want) < 1e-12, f"{ref_:.4f}")
o_s = wsp("SPY", "one_at_a_time")
lo_, hi_ = o_s.loc[o_s.AUC_mean.idxmin()], o_s.loc[o_s.AUC_mean.idxmax()]
check_true("VII-E: SPY extremes are U removed and R halved", lo_.label == "adjustment U x 0" and hi_.label == "weight of R x 0.5", f"{lo_.label}; {hi_.label}")
check_text("VII-E SPY: one constant", f"Changing one constant moves its mean AUC between {f(lo_.AUC_mean)}, without the adjustment of rule~$U$, and "
           f"{f(hi_.AUC_mean)}, with the weight of Risk halved")
st_s = wsp("SPY", "structural").set_index("label").AUC_mean
check_text("VII-E SPY: structural", f"equal weights, no adjustments, and both lower it to {f(st_s['equal component weights'])}, "
           f"{f(st_s['no interaction adjustments'])}, and {f(st_s['equal weights, no adjustments'])}")
check_true("VII-E SPY: every one-at-a-time and structural variant below one half and the structural ones below the reference",
           o_s.AUC_mean.max() < 0.5 and st_s.max() < wsp("SPY", label="expert weights (reference)").AUC_mean.iloc[0], "holds")
rl_s, rw_s = wsp("SPY", "random_local").AUC_mean, wsp("SPY", "random_wide").AUC_mean
check_text("VII-E SPY: +/-50% draws", f"its median is {f(rl_s.median())} (5th to 95th percentile {f(rl_s.quantile(0.05))} to {f(rl_s.quantile(0.95))}), "
           f"and {int((rl_s > 0.5).sum())} of the 1,000 exceed one half, the highest at {f(rl_s.max())}")
check_text("VII-E SPY: sign-preserving draws", f"do more sets rank above one half, {int((rw_s > 0.5).sum())} of the 1,000, at most {f(rw_s.max())}, "
           f"still below Model~2 ({f(SMC.loc[LRm, 'AUC_mean'])}) and ridge regression ({f(SMC.loc[RIm, 'AUC_mean'])})")
check_true("VII-E SPY: the best Spider draw below both logistic baselines", rw_s.max() < min(SMC.loc[LRm, "AUC_mean"], SMC.loc[RIm, "AUC_mean"]), "holds")
o_b, st_b = wsp("bank-sector index", "one_at_a_time").AUC_mean, wsp("bank-sector index", "structural").AUC_mean
rl_b, rw_b = wsp("bank-sector index", "random_local").AUC_mean, wsp("bank-sector index", "random_wide").AUC_mean
check_text("VII-E bank: one constant and structural", f"between {f(o_b.min())} and {f(o_b.max())} for one constant changed, between {f(st_b.min())}\nand "
           f"{f(st_b.max())} for the structural alternatives")
check_text("VII-E bank: random sets", f"with medians of {f(rl_b.median())}\n({f(rl_b.quantile(0.05))} to {f(rl_b.quantile(0.95))}) and {f(rw_b.median())} "
           f"({f(rw_b.quantile(0.05))} to {f(rw_b.quantile(0.95))}) for the two random sets")
# constants chosen in the training folds
chw = WCH[(WCH.benchmark == "SPY") & (WCH.family == "random_wide")][["wV", "wP", "wB", "wR", "wE"]].mean()
check_text("VII-E: weights chosen in the training folds", f"on average the chosen sets give {f2(chw.wV)} to Value,\n{f2(chw.wB)} to Buyer Strength, and "
           f"{f2(chw.wP)} each to Protection and Risk")
check_true("VII-E: Protection and Risk round to the same chosen weight", f2(chw.wP) == f2(chw.wR), f"{chw.wP:.3f}, {chw.wR:.3f}")
ne = WNE.groupby(["benchmark", "family"])[["AUC", "training_AUC_mean"]].mean()
check_text("VII-E: training and held-out AUC (sign-preserving, SPY)", f"Their mean AUC is {f(ne.loc[('SPY', 'random_wide'), 'training_AUC_mean'])} on the "
           f"training folds but {f(ne.loc[('SPY', 'random_wide'), 'AUC'])} on the held-out folds")
check_true("VII-E: below both logistic baselines", ne.loc[("SPY", "random_wide"), "AUC"] < min(SMC.loc[LRm, "AUC_mean"], SMC.loc[RIm, "AUC_mean"]), "holds")
wpt = WPT.set_index(["benchmark", "constants"])
check_text("VII-E: permutation of the choice", f"({f(wpt.loc[('SPY', 'random_wide'), 'observed_mean_AUC'])} on its three partitions; one-sided\n"
           f"$p = {f2(wpt.loc[('SPY', 'random_wide'), 'p_one_sided_upper'])}$, two-sided $p = {f2(wpt.loc[('SPY', 'random_wide'), 'p_two_sided'])}$)")
check_text("VII-E: the other three choices", f"the constants reach {f(ne.loc[('SPY', 'random_local'), 'AUC'])}, and against the bank-sector\nbenchmark "
           f"the two choices reach {f(ne.loc[('bank-sector index', 'random_local'), 'AUC'])} and {f(ne.loc[('bank-sector index', 'random_wide'), 'AUC'])}, below the expert\nconstants")
three = [wpt.loc[k, "p_two_sided"] for k in (("SPY", "random_local"), ("bank-sector index", "random_local"), ("bank-sector index", "random_wide"))]
check_text("VII-E: their permutation p", f"(two-sided $p \\geq {int(min(three) * 100) / 100:.2f}$)")
check_true("VII-E: bank choices below the expert constants", max(ne.loc[("bank-sector index", "random_local"), "AUC"], ne.loc[("bank-sector index", "random_wide"), "AUC"])
           < BMC.loc[SCm, "AUC_mean"], "holds")
check_true("weights permutation: the reference reproduces Table 9's Spider p-values", abs(wpt.loc[("SPY", "reference"), "p_two_sided"] - pcp(SB, SCm, "p_two_sided")) < 1e-12
           and abs(wpt.loc[("bank-sector index", "reference"), "p_two_sided"] - pcp(BB, SCm, "p_two_sided")) < 1e-12, "holds")
# Model 3 and the policies under the alternative constants (VII-E)
m3s, m3b = WM3[WM3.benchmark == "SPY"], WM3[WM3.benchmark == "bank-sector index"]
struct_s = m3s[m3s.family.isin(["one_at_a_time", "structural"])]
rand_s = m3s[m3s.family.isin(["random_local", "random_wide"])]
check_true("VII-E: 25 structured and 200 random Model 3 sets per benchmark", len(struct_s) == 25 and len(rand_s) == 200 and len(m3s) == 226 and len(m3b) == 226, "holds")
check_text("VII-E Model 3 SPY: ranges", f"its mean AUC lies between {f(struct_s.AUC_mean.min())} and\n{f(struct_s.AUC_mean.max())} for the 25 one-at-a-time and structural "
           f"alternatives and between\n{f(rand_s.AUC_mean.min())} and {f(rand_s.AUC_mean.max())} for the 200 random draws refitted")
n_above_r, n_below_m2 = int((m3s.diff_ridge_mean > 0).sum()), int((m3s.diff_Model2_mean < 0).sum())
w4 = {4: "four"}
check_text("VII-E Model 3 SPY: against the baselines", f"it ranks below ridge\nregression in {226 - n_above_r} of the 226 constant sets, and above it in the "
           f"other\n{w4.get(n_above_r, str(n_above_r))} by at most {f(m3s.diff_ridge_mean.max())}, and below Model~2 in {n_below_m2}")
check_true("VII-E Model 3 SPY: no set level with ridge", (m3s.diff_ridge_mean != 0).all() and (m3s.diff_Model2_mean != 0).all(), "holds")
check_text("VII-E Model 3 bank", f"it lies between {f(m3b.AUC_mean.min())} and {f(m3b.AUC_mean.max())} in every set,\nbelow one half and above both logistic baselines")
check_true("VII-E Model 3 bank: below one half, above both baselines in every set", m3b.AUC_mean.max() < 0.5 and (m3b.diff_ridge_mean > 0).all()
           and (m3b.diff_Model2_mean > 0).all(), "holds")
check_true("VII-E: 4B and 4C below zero under every constant set and both benchmarks", (WM3.utility_4B_mean < 0).all() and (WM3.utility_4C_mean < 0).all(),
           f"max 4B {WM3.utility_4B_mean.max():.3f}, 4C {WM3.utility_4C_mean.max():.3f}")
ref4a = wsp("SPY", label="expert weights (reference)").utility_4A_mean.iloc[0]
loc4a, wide4a = wsp("SPY", "random_local").utility_4A_mean, wsp("SPY", "random_wide").utility_4A_mean
eqw = wsp("SPY", label="equal component weights").iloc[0]
check_text("VII-E: 4A", f"its\nsmall positive utility ({f(ref4a)}) persists in {100 * (loc4a > 0).mean():.0f}\\% of the draws within\n$\\pm$50\\%, but not with equal "
           f"weights, under which the rescaled score\nreaches 0.70 for twelve transactions on average and the utility falls\nto $-{abs(eqw.utility_4A_mean):.3f}$, "
           f"nor in most sign-preserving draws (median $-{abs(wide4a.median()):.3f}$)")
check_true("VII-E: 4A with equal weights pursues twelve on average; wide median negative", round(eqw.pursue_4A_mean) == 12 and wide4a.median() < 0
           and (wide4a > 0).mean() < 0.5, f"{eqw.pursue_4A_mean:.2f}")
# the closing paragraph of VII-E, the Discussion and the Conclusion
check_true("VII-E: 'nearly every' +/-50% set and 'most' sign-preserving sets leave the score below one half (SPY)", (rl_s < 0.5).mean() >= 0.99 and (rw_s < 0.5).mean() > 0.5,
           f"{(rl_s < 0.5).mean():.3f}, {(rw_s < 0.5).mean():.3f}")
# release 4.13: 'VII-E closing' reworded; checked in the release 4.13 block below
check_true("VII-E: the score never beats ridge (SPY)", WSP[WSP.benchmark == "SPY"].AUC_mean.max() < SMC.loc[RIm, "AUC_mean"], "holds")
best_s = WSP[WSP.benchmark == "SPY"].merge(WVA[["variant_id", "wP", "wR"]], on="variant_id").nlargest(10, "AUC_mean")
check_true("VII-E: the ten best sets against the S&P 500 put almost no weight on Protection and Risk (expert: 0.40 together)",
           (best_s.wP + best_s.wR).mean() < 0.1 and (best_s.wP + best_s.wR).max() < 0.15, f"mean {(best_s.wP + best_s.wR).mean():.3f}, max {(best_s.wP + best_s.wR).max():.3f}")
# release 4.13: 'VIII weights sentence' reworded; checked in the release 4.13 block below
check_true("VIII: the score below both baselines in every set (SPY)", WSP[WSP.benchmark == "SPY"].AUC_mean.max() < min(SMC.loc[LRm, "AUC_mean"], SMC.loc[RIm, "AUC_mean"]), "holds")
check_true("VIII: the four exceptions are alternatives, not the reference", float(m3s[m3s.family == "reference"].diff_ridge_mean.iloc[0]) < 0, "holds")
# release 4.13: 'conclusion weights' reworded; checked in the release 4.13 block below
check_true("conclusion: weights: across the alternatives Model 3 never ranks above ridge regression by more than 0.002",
           round(float(m3s.diff_ridge_mean.max()), 3) <= 0.002, f"{m3s.diff_ridge_mean.max():.4f}")
# ---- included and excluded transactions (release 4.7; release 4.8)
SEL = pd.read_csv(R / "table_selection_comparison.csv").set_index("characteristic")
SSZ = pd.read_csv(R / "table_selection_size_classes.csv")
SRW = pd.read_csv(R / "table_selection_reweighted.csv")
SXX = pd.read_csv(R / "selection_characteristics_94.csv")
SBL = pd.read_csv(R / "table_selection_balance.csv").set_index("characteristic")
SDG = pd.read_csv(R / "table_selection_weight_diagnostics.csv").iloc[0]
PST = pd.read_csv(FW / "data/Excluded39_Parent_Status.csv")
n_inc, n_exc = int(SXX.included.sum()), int((SXX.included == 0).sum())
n_acq, n_lst = int((PST.parent_status == "acquired").sum()), int((PST.parent_status == "listed").sum())
p_inc, p_exc = SXX[SXX.included == 1].parent.nunique(), SXX[SXX.included == 0].parent.nunique()
p_acq, p_lst = PST[PST.parent_status == "acquired"].parent_ticker.nunique(), PST[PST.parent_status == "listed"].parent_ticker.nunique()
check_true("VII-F: 94 = 55 + 39 transactions; 52 = 28 + 24 parents; 39 = 26 + 13 transactions of 17 + 7 parents",
           (n_inc, n_exc, p_inc, p_exc, n_acq, n_lst, p_acq, p_lst) == (55, 39, 28, 24, 26, 13, 17, 7),
           f"{n_inc}, {n_exc}, {p_inc}, {p_exc}, {n_acq}, {n_lst}, {p_acq}, {p_lst}")
check_true("VII-F: the parents of the 39 in the status file are those of the characteristics file",
           set(PST.parent_ticker) == set(SXX[SXX.included == 0].parent), "holds")
check_true("VII-F: some listed parents trade under a new name", int(PST[PST.parent_status == "listed"].parent_later_event.str.contains("renamed").sum()) >= 2, "NYCB, SCBT")
check_text("V-A: the 39", f"do not cover the other {n_exc}. These {n_exc} transactions have {p_exc} listed parents: {p_acq} of them, with {n_acq} of the "
           f"transactions, were later acquired by other banks and delisted, and the other {p_lst}, with {n_lst} transactions, still trade, some under a "
           f"new name, but their prices were not retrieved (Section~\\ref{{sec:selection}} compares the two groups).")
check_text("VII-F: opening", f"Of the {len(SXX)} transactions in which the acquiring bank had a U.S.-listed parent, {n_exc} are not in the panel")
check_text("VII-F: parents", f"These {n_exc} transactions have {p_exc} listed parents, and the {n_inc} in the panel have {p_inc}. Seventeen of the {p_exc} "
           f"parents, with {n_acq} of the excluded transactions, were later acquired by other banks and delisted; the other {p_lst}, with {n_lst} "
           f"transactions, still trade")
check_true("VII-F: 'Seventeen' is the number of acquired parents", p_acq == 17, str(p_acq))
check_true("VII-F: no characteristic missing", bool(SXX.notna().all().all()), "holds")
check_true("VII-F: a parent is either in the panel or out of it", bool((SXX.groupby("parent").included.nunique() == 1).all()), "holds")
check_text("VII-F: parents permuted", f"reassigns inclusion across the {SXX.parent.nunique()} listed parents, not across transactions")
pv = lambda p: "$p < 0.01$" if p < 0.01 else f"$p = {p:.2f}$"
ba, cp, fa, mm, cr = (SEL.loc[k] for k in ("buyer_assets_usd_bn", "C_buyer_capital_pct", "failed_assets_usd_bn", "E_relative_size", "crisis_2008_2010"))
check_text("VII-F: acquirer size and capital", f"The median acquiring bank held \\${ba.excluded_median:.2f} billion of assets, against \\${ba.included_median:.2f} "
           f"billion in the panel (AUC {ba.AUC_inclusion:.3f}, {pv(ba.p_two_sided)}), and it was better capitalized ({cp.excluded_median:.2f}\\% against "
           f"{cp.included_median:.2f}\\%, {pv(cp.p_two_sided)}).")
check_text("VII-F: failed-bank size and relative size", f"The failed banks were smaller (median assets \\${fa.excluded_median:.2f} billion against "
           f"\\${fa.included_median:.2f} billion, {pv(fa.p_two_sided)}) and, relative to the acquirer, larger ({mm.excluded_median:.2f} against "
           f"{mm.included_median:.2f}, {pv(mm.p_two_sided)}).")
check_text("VII-F: period", f"fell in 2008--2010 ({100 * cr.excluded_mean:.0f}\\% against {100 * cr.included_mean:.0f}\\%, {pv(cr.p_two_sided)}), the difference "
           f"coming from the {n_acq} transactions whose parents were later acquired ({100 * cr.excluded_acquired_mean:.0f}\\%, against "
           f"{100 * cr.excluded_listed_mean:.0f}\\% for the {n_lst} whose parents still trade).")
check_true("VII-F: the period difference comes from the acquired parents", abs(cr.excluded_listed_mean - cr.included_mean) < 0.05 < cr.excluded_acquired_mean - cr.included_mean,
           f"{cr.included_mean:.3f}, {cr.excluded_listed_mean:.3f}, {cr.excluded_acquired_mean:.3f}")
nn, tt, ll = (SEL.loc[k] for k in ("N_npl_pct", "T_npl_change_pp", "L_deposit_change_pct"))
check_text("VII-F: distress, no detectable difference", f"No statistically detectable difference in target distress was found: the excluded targets' median "
           f"NPL ratio was {nn.excluded_median:.2f}\\%, against {nn.included_median:.2f}\\% ({pv(nn.p_two_sided)}), and neither the change in the NPL "
           f"ratio nor the change in deposits differs detectably ($p = {tt.p_two_sided:.2f}$ and {ll.p_two_sided:.2f}). With {p_exc} and {p_inc} parents, "
           f"these tests cannot rule out moderate differences, so they do not show that the targets were equally distressed.")
check_true("VII-F: no distress p-value below 0.05", min(nn.p_two_sided, tt.p_two_sided, ll.p_two_sided) > 0.05, f"{nn.p_two_sided:.3f}")
check_true("VII-F: the excluded acquirers smaller, better capitalized; targets smaller, relatively larger",
           ba.AUC_inclusion > 0.5 > cp.AUC_inclusion and fa.AUC_inclusion > 0.5 > mm.AUC_inclusion and cr.excluded_mean > cr.included_mean, "holds")
hmin = SEL.p_holm.idxmin()
check_text("VII-F: Holm", f"after a Holm adjustment across the {w.get(len(SEL), str(len(SEL)))} characteristics, the smallest, for acquirer size, is {SEL.p_holm.min():.2f}.")
check_true("VII-F: the smallest Holm p is acquirer size", hmin == "buyer_assets_usd_bn", hmin)
cut = float(SSZ.size_cut_usd_bn.iloc[0])
sz = lambda bm, cl, mdl: SSZ[(SSZ.benchmark == bm) & (SSZ.acquirer_size_class == cl) & (SSZ.model == mdl)].iloc[0]
LOG3 = ("Model 2", "Ridge", "Model 3")
SM, LG = "at or below the median", "above the median"
nsmall_ex = int(sz("S&P 500", SM, "Model 2").n_excluded_in_class)
check_text("VII-F: size cut", f"Panel~B divides the {n_inc} at the median acquiring bank of all {len(SXX)} (\\${cut:.1f} billion), at or below which lie "
           f"{nsmall_ex} of the {n_exc} excluded transactions.")
lg, smv = [sz("S&P 500", LG, m_) for m_ in LOG3], [sz("S&P 500", SM, m_) for m_ in LOG3]
check_text("VII-F: SPY by size", f"rank the {lg[0].n} transactions with larger acquirers well above chance (mean AUC {lg[0].AUC_mean:.3f}, {lg[1].AUC_mean:.3f}, "
           f"and {lg[2].AUC_mean:.3f}) and the {smv[0].n} with smaller acquirers below it ({smv[0].AUC_mean:.3f}, {smv[1].AUC_mean:.3f}, and {smv[2].AUC_mean:.3f}).")
spl, sps = sz("S&P 500", LG, "Spider score").AUC_mean, sz("S&P 500", SM, "Spider score").AUC_mean
check_text("VII-F: Spider score by size", f"The Spider score is below one half in both groups ({spl:.3f} and {sps:.3f}), and among the smaller acquirers its AUC "
           f"is higher than those of the three models.")
check_true("VII-F: Spider below one half in both SPY groups and above the three models among smaller acquirers",
           max(spl, sps) < 0.5 and all(sps > s_.AUC_mean for s_ in smv), "holds")
bsp = sz("bank-sector index", SM, "Spider score").AUC_mean
check_text("VII-F: bank by size", f"Against the bank-sector benchmark, the three models rank both groups below one half, and the Spider score ranks the smaller "
           f"acquirers' transactions above it ({bsp:.3f}).")
check_true("VII-F: bank benchmark, both size classes below one half; Spider above one half among smaller acquirers",
           all(sz("bank-sector index", c_, m_).AUC_mean < 0.5 for c_ in (SM, LG) for m_ in LOG3) and bsp > 0.5, "holds")
check_true("VII-F/VIII/IX: the three models rank smaller-acquirer transactions worse under both benchmarks",
           all(sz(b_, SM, m_).AUC_mean < sz(b_, LG, m_).AUC_mean for b_ in ("S&P 500", "bank-sector index") for m_ in LOG3), "holds")
check_true("VIII: the three models' AUCs among the smaller acquirers' transactions are below one half against the S&P 500", all(s_.AUC_mean < 0.5 for s_ in smv), "holds")
rw = lambda bm, wt, mdl: SRW[(SRW.benchmark == bm) & (SRW.weighting == wt) & (SRW.model == mdl)].AUC_mean.iloc[0]
IP, TR = "inverse probability of inclusion", "weights truncated at the 95th percentile"
rows_b = [(b_, sz(b_, c_, "Model 3").AUC_mean, sz(b_, c_, "Ridge").AUC_mean) for b_ in ("S&P 500", "bank-sector index") for c_ in ("all 55", SM, LG)]
rows_b += [(b_, rw(b_, wt_, "Model 3"), rw(b_, wt_, "Ridge")) for b_ in ("S&P 500", "bank-sector index") for wt_ in (IP, TR)]
check_true("VII-F: Model 3 below ridge (SPY) and above it (bank) in both size groups and under both weightings",
           all((m3 < rd_) if b_ == "S&P 500" else (m3 > rd_) for b_, m3, rd_ in rows_b), f"{len(rows_b)} rows")
check_text("VII-F: parents decide inclusion", f"although inclusion is decided by their {SXX.parent.nunique()} parents.")
check_text("VII-F: overlap and weight concentration", f"{w.get(int(SDG.n_excluded_below_included_min), str(int(SDG.n_excluded_below_included_min))).capitalize()} "
           f"excluded transactions have an estimated probability of inclusion below the lowest among the included ({SDG.p_inclusion_included_min:.3f}), and the "
           f"weights are concentrated: the effective sample is {SDG.weighted_effective_n:.0f} of {n_inc}, and one transaction carries "
           f"{100 * SDG.weighted_max_weight_share:.0f}\\% of the total weight.")
bl = lambda k, c_: SBL.loc[k, c_]
f2 = lambda x: f"$-{abs(x):.2f}$" if x < 0 else f"{x:.2f}"
nb = lambda c_, t_: int((SBL[c_].abs() >= t_).sum())
num = {5: "five", 7: "seven", 9: "nine"}
check_text("VII-F: balance threshold", f"for which an absolute value below 0.1 is conventionally taken to indicate balance~\\cite{{austin2015}}. Before "
           f"weighting, {num[nb('std_diff_unweighted', 0.1)]} of the {num[len(SBL)]} characteristics exceed that threshold, acquirer size the most "
           f"({bl('log_acquirer_assets', 'std_diff_unweighted'):.2f}).")
check_true("VII-F: acquirer size has the largest unweighted standardized difference", SBL.std_diff_unweighted.abs().idxmax() == "log_acquirer_assets",
           SBL.std_diff_unweighted.abs().idxmax())
check_true("VII-F: no unweighted difference between 0.095 and 0.105 (the count does not hinge on rounding)",
           not SBL.std_diff_unweighted.abs().between(0.095, 0.105).any(), "holds")
check_true("VII-F: the untruncated weights reverse the sign of each inclusion-model difference",
           bool((SBL[SBL.in_inclusion_model].std_diff_unweighted * SBL[SBL.in_inclusion_model].std_diff_weighted < 0).all()), "holds")
check_text("VII-F: balance, untruncated", f"The untruncated weights overcorrect: they reverse the sign of the difference in each of the inclusion model's "
           f"four characteristics, leave {num[nb('std_diff_weighted', 0.1)]} of the nine at or above 0.1 in absolute value, raise the difference in the NPL "
           f"ratio from {f2(bl('N_npl_pct', 'std_diff_unweighted'))} to {f2(bl('N_npl_pct', 'std_diff_weighted'))}, and create one of "
           f"{f2(bl('T_npl_change_pp', 'std_diff_weighted'))} in its change, where there was almost none ({f2(bl('T_npl_change_pp', 'std_diff_unweighted'))}).")
check_true("VII-F: four characteristics in the inclusion model", int(SBL.in_inclusion_model.sum()) == 4, str(int(SBL.in_inclusion_model.sum())))
mod_t = SBL[SBL.in_inclusion_model].std_diff_truncated.abs().max()
oth = SBL[~SBL.in_inclusion_model].std_diff_truncated.abs()
check_true("VII-F: truncated, model characteristics within 0.03; the others within 0.05 except the NPL change",
           mod_t <= 0.03 and oth.drop("T_npl_change_pp").max() <= 0.05 and oth.idxmax() == "T_npl_change_pp", f"{mod_t:.3f}, {oth.drop('T_npl_change_pp').max():.3f}")
check_text("VII-F: balance, truncated", f"Truncated at their 95th percentile, the weights bring every characteristic of the inclusion model within 0.03 "
           f"standard deviations of all {len(SXX)} and every other within 0.05 except the change in the NPL ratio "
           f"({bl('T_npl_change_pp', 'std_diff_truncated'):.2f}), with an effective sample of {SDG.truncated_effective_n:.0f}.")
check_true("VII-F: only the NPL change at or above 0.1 after truncation", nb("std_diff_truncated", 0.1) == 1, str(nb("std_diff_truncated", 0.1)))
check_true("VII-F: the truncated weights balance better than the untruncated",
           SBL.std_diff_truncated.abs().max() < SBL.std_diff_weighted.abs().max() and mod_t < SBL[SBL.in_inclusion_model].std_diff_weighted.abs().max(), "holds")
check_text("VII-F: reweighted AUCs", f"With the untruncated weights, the three models' mean AUC against the S\\&P~500 falls to {rw('S&P 500', IP, 'Model 2'):.3f}, "
           f"{rw('S&P 500', IP, 'Ridge'):.3f}, and {rw('S&P 500', IP, 'Model 3'):.3f}; with the truncated weights, which balance better, to "
           f"{rw('S&P 500', TR, 'Model 2'):.3f}, {rw('S&P 500', TR, 'Ridge'):.3f}, and {rw('S&P 500', TR, 'Model 3'):.3f}.")
check_true("VII-F: both weightings lower the three models against the S&P 500", all(rw("S&P 500", wt_, m_) < rw("S&P 500", "unweighted", m_) for wt_ in (IP, TR) for m_ in LOG3), "holds")
check_text("VII-F: Spider reweighted", f"The Spider score's AUC is {rw('S&P 500', IP, 'Spider score'):.3f} and {rw('S&P 500', TR, 'Spider score'):.3f}, and under "
           f"both weightings Model~3 remains below ridge regression against the S\\&P~500 and above it against the bank-sector benchmark.")
check_text("VII-F: two weightings", "Because the AUCs under the two weightings differ by more than 0.1 and rest on few transactions")
check_true("VII-F: the two weightings differ by more than 0.1 for the three models", all(abs(rw("S&P 500", IP, m_) - rw("S&P 500", TR, m_)) > 0.1 for m_ in LOG3), "holds")
adv = lambda b_, wt_: [rw(b_, wt_, m_) - rw(b_, wt_, "Spider score") for m_ in LOG3]
adv_small = [sz("S&P 500", SM, m_).AUC_mean - sz("S&P 500", SM, "Spider score").AUC_mean for m_ in LOG3]
check_true("VII-F/VIII: the models' advantage over the Spider score shrinks under both weightings and reverses under the untruncated and among smaller acquirers",
           all(x < y for wt_ in (IP, TR) for x, y in zip(adv("S&P 500", wt_), adv("S&P 500", "unweighted")))
           and max(adv("S&P 500", IP)) < 0 and max(adv_small) < 0 < min(adv("S&P 500", "unweighted")), "holds")
check_text("VII-F: direction", "a panel that contained them would show weaker discrimination by the three models against the S\\&P~500, and their "
           "advantage over the Spider score would shrink or reverse; Model~3's position relative to ridge regression, by contrast, holds in both size "
           "groups and under both weightings.")
check_text("VII-F: not resolved", "The analyses therefore indicate the direction in which the observed selection could bias the evaluation, under an "
           "assumption that cannot be tested, and leave the selection concern unresolved.")
check_text("VII-F: IPW assumptions", "The weighted AUC represents all 94 only under three assumptions~\\cite{seaman2013}")
check_text("VIII: selection pointer to VII-F and the limitations", "(Sections~\\ref{sec:selection} and~\\ref{sec:limitations})")
check_text("VIII-E: reweighting", f"the overlap between the two groups is incomplete, and the weights leave an effective sample of "
           f"{SDG.weighted_effective_n:.0f} to {SDG.truncated_effective_n:.0f} transactions. No analysis here addresses selection on unobserved "
           f"characteristics, so the selection concern is not resolved.")
check_true("VIII-E: overlap incomplete", int(SDG.n_excluded_below_included_min) > 0, str(int(SDG.n_excluded_below_included_min)))
check_text("VII-F: closing", f"Historical prices for the {n_lst} transactions involving seven still-listed parents may be recoverable through "
           f"improved ticker mapping and price retrieval. A database covering delisted securities, such as that of the Center for Research in Security "
           f"Prices (CRSP), may also help recover historical prices for the remaining {n_acq} transactions involving {p_acq} parents.")
check_true("VII-F: the seven still-listed parents", p_lst == 7, str(p_lst))
# release 4.13: 'VIII selection sentence' reworded; checked in the release 4.13 block below
# release 4.13 (second pass): reworded; checked in the block below
# release 4.13: 'VIII-F second limitation' reworded; checked in the release 4.13 block below
check_text("VIII-E: second limitation, distress", "no statistically detectable difference in target distress was found, which does not establish that there was none")
check_true("VIII-E: the 39 had smaller and better-capitalized acquirers and more often fell in 2008-2010",
           ba.excluded_median < ba.included_median and cp.excluded_median > cp.included_median and cr.excluded_mean > cr.included_mean, "holds")
# release 4.13: 'IX selection sentence' reworded; checked in the release 4.13 block below
for phrase in ("equally distressed targets", "about as distressed", "flatters the models", "cannot explain why", "Nor do they reflect", "Nor do they depend on which",
               "would not change", "None can be verified", "smaller advantage, or none"):
    check_true(f"Comment 4: no claim that the selection is resolved ('{phrase}')", phrase not in tex, "absent")
# FDIC financing of the buyer: the winning-bid record of all 90 transactions (release 4.1)
fc = pd.read_csv(FW / "data/FDIC_Financing_Check_90.csv", dtype=str, keep_default_na=False)
nbs = int((fc.evidence_source == "FDIC bid summary").sum())
oth = fc[fc.evidence_source != "FDIC bid summary"]
check("winning bids read in an FDIC bid summary", str(nbs), "the FDIC's bid summary, which we found for {v} of the 90 transactions")
months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
d0, d1 = pd.to_datetime(oth.failure_date.min()), pd.to_datetime(oth.failure_date.max())
check_text("transactions without a bid summary: count, panel, period",
           f"for the other {({10: 'ten'}).get(len(oth), str(len(oth)))}, all in the primary panel and all closed between "
           f"{months[d0.month - 1]} {d0.year} and {months[d1.month - 1]} {d1.year}")
check_true("transactions without a bid summary are all in the primary panel", (oth.in_primary_panel == "1").all(), f"{len(oth)} transactions")
fin_ids = set(fc.loc[fc.buyer_financing_in_winning_bid == "1", "transaction_id"])
check_true("winning bids with FDIC financing of the buyer: SVB, First Republic, Westernbank, Eurobank",
           fin_ids == {"PA-0006", "PA-0004", "PA-0306", "PA-0308"}, ", ".join(sorted(fin_ids)))
check_text("winning bids with FDIC financing of the buyer (text)",
           "Only the winning bids for SVB, First Republic, Westernbank Puerto Rico, and Eurobank include FDIC financing of the buyer")
check_true("documents agree with the ledger's FDIC financing coding",
           (fc.set_index("transaction_id").buyer_financing_in_winning_bid
            == led.set_index("transaction_id").fdic_buyer_financing.astype(str).reindex(fc.transaction_id)).all(), "all 90")
# outcome wording
vc = re.findall(r"value-creat\w*|value creation|value-destroy\w*|created value", tex)
check_true("'value-creating' no longer describes the outcome (one use, in the sentence that rejects it)", len(vc) == 1 and "rather than as value-creating" in tex,
           f"{len(vc)} uses: {vc}")
# ---- the FBOP cluster and benchmark dependence (release 4.9; Section VIII-A)
g2, g3 = (lambda x: f"{x:.2f}"), (lambda x: f"{x:.3f}")
pct1 = lambda x: f"{100 * x:.1f}\\%"
fb4 = p55.transaction_id.isin(["PA-0385", "PA-0386", "PA-0387", "PA-0388"])
check_true("VIII-A: the four FBOP subsidiaries share one event cluster, one CAR, label 0 (SPY) and 1 (bank)",
           int(fb4.sum()) == 4 and grp55[fb4].nunique() == 1 and p55[fb4].car_reaction_m1p1.nunique() == 1
           and set(p55[fb4].y) == {0} and set(yb[fb4]) == {1}, "holds")
n_oth, agree = int((~fb4).sum()), int(((p55.y == yb) & ~fb4).sum())
check_text("VIII-A: opposite movements", f"Removing the cluster lowers Model~2's mean AUC from {g3(fbi('y', AL, LRm))} to {g3(fbi('y', WO, LRm))} "
           f"against the S\\&P~500 and raises it from {g3(fbi('y_bank', AL, LRm))} to {g3(fbi('y_bank', WO, LRm))} against the bank-sector benchmark")
check_text("VIII-A: labels the benchmarks share", f"their predictions always come from models fitted on the other {n_oth} transactions, {agree} of which have "
           f"the same label under both benchmarks.")
RKS = pd.read_csv(R / "table_rank_by_group.csv").set_index("model")
RKB = pd.read_csv(R / "table_bank_rank_by_group.csv").set_index("model")
FS, FB_ = "FBOP subsidiaries (one event, y=0)", "FBOP subsidiaries (one event, y_bank=1)"
check_text("VIII-A: FBOP percentile ranks", f"Model~2's mean percentile rank for them is {g2(RKS.loc[LRm, FS])} against the S\\&P~500 and "
           f"{g2(RKB.loc[LRm, FB_])} against the bank-sector benchmark.")
fbr = BKF.loc["PA-0385"]
check_text("VIII-A: window returns and CARs", f"Over the outcome's three-day window the S\\&P~500 fell {-100 * fbr.spy_return_window:.1f}\\% and the "
           f"bank-sector benchmark {-100 * fbr.bank_index_return_window:.1f}\\%, and U.S.~Bancorp's shares fell by more than the market but by less than "
           f"the other banks, so the CAR is ${100 * fbr.car_reaction_m1p1_spy_check:+.1f}\\%$ against the S\\&P~500 and "
           f"${100 * fbr.car_reaction_m1p1_bank:+.1f}\\%$ against the bank-sector benchmark")
check_true("VIII-A: U.S. Bancorp fell, by more than SPY and by less than the bank benchmark",
           fbr.car_reaction_m1p1_spy_check < 0 < fbr.car_reaction_m1p1_bank and fbr.spy_return_window < 0 and fbr.bank_index_return_window < fbr.spy_return_window
           and all(BKF.loc[t].car_reaction_m1p1_bank == fbr.car_reaction_m1p1_bank for t in p55[fb4].transaction_id), "holds")
check_true("VIII-A: SPY CAR of the cluster equals the frozen CAR", abs(float(p55[fb4].car_reaction_m1p1.iloc[0]) - fbr.car_reaction_m1p1_spy_check) < 1e-12, "holds")
npS, nnS, npB, nnB = int(p55.y.sum()), int((p55.y == 0).sum()), int(yb.sum()), int((yb == 0).sum())
pS, pB = 4 * npS, 4 * nnB
check_text("VIII-A: pairs", f"Against the S\\&P~500 the four transactions are 4 of the {nnS} negatives and enter {pS} of the {npS * nnS} "
           f"positive--negative pairs on which the AUC is computed ({100 * pS / (npS * nnS):.0f}\\%); against the bank-sector benchmark they are 4 of the "
           f"{npB} positives and enter {pB} of the {npB * nnB} pairs ({100 * pB / (npB * nnB):.0f}\\%).")
check_true("VIII-A: Model 2 ranks the cluster near the bottom under both benchmarks, the other groups near the middle",
           RKS.loc[LRm, FS] < 0.1 and RKB.loc[LRm, FB_] < 0.15 and min(RKS.loc[LRm, "other positive CAR"], RKB.loc[LRm, "other positive CAR"]) > 0.45, "holds")
check_text("VIII-A: other transactions, SPY", f"Model~2 gives the other transactions with a positive and with a negative CAR almost the same mean percentile rank "
           f"against the S\\&P~500 ({g2(RKS.loc[LRm, 'other positive CAR'])} and {g2(RKS.loc[LRm, 'other negative CAR'])}), so nearly all of its "
           f"above-chance discrimination comes from the four FBOP transactions; refitted without them, its mean AUC on the remaining {n_oth} is "
           f"{g3(fbi('y', WO, LRm))}.")
check_text("VIII-A: other transactions, bank", f"it ranks the other negative transactions above the other positive ones "
           f"({g2(RKB.loc[LRm, 'other negative CAR'])} and {g2(RKB.loc[LRm, 'other positive CAR'])}), so the cluster accounts for only part of the AUC below "
           f"one half, and refitted without it Model~2's mean AUC is still {g3(fbi('y_bank', WO, LRm))}.")
check_true("VIII-A: other positives and negatives within 0.05 against SPY; other negatives above other positives against the bank benchmark",
           abs(RKS.loc[LRm, "other positive CAR"] - RKS.loc[LRm, "other negative CAR"]) < 0.05
           and RKB.loc[LRm, "other negative CAR"] > RKB.loc[LRm, "other positive CAR"] and fbi("y_bank", WO, LRm) < 0.5, "holds")
check_text("VIII-A: ridge regression", f"Ridge regression behaves in the same way (from {g3(fbi('y', AL, RIm))} to {g3(fbi('y', WO, RIm))}, and from "
           f"{g3(fbi('y_bank', AL, RIm))} to {g3(fbi('y_bank', WO, RIm))}).")
check_true("VIII-A: ridge's ranks follow the same pattern", RKS.loc[RIm, FS] < 0.1 and RKB.loc[RIm, FB_] < 0.15
           and abs(RKS.loc[RIm, "other positive CAR"] - RKS.loc[RIm, "other negative CAR"]) < 0.05
           and RKB.loc[RIm, "other negative CAR"] > RKB.loc[RIm, "other positive CAR"], "holds")
pmB = PCP[(PCP.benchmark == "bank-sector index") & (PCP.model == LRm)].iloc[0]
check_text("VIII-A: permutation", f"the permutation test places Model~2's AUC within the range that uninformative outcomes produce (two-sided "
           f"$p = {pmB.p_two_sided:.2f}$; Table~\\ref{{tab:perm}})")
rS, rB = rfb.loc[f"AUC {LRm}"], BRF.loc[f"AUC {LRm}"]
check_text("VIII-A: a fifth of the pairs", "With 51 events, one of which supplies a fifth of the pairs under one benchmark")
check_true("VIII-A: a fifth", pS / (npS * nnS) == 0.2 and man["event_groups_primary"] == 51, f"{pS}/{npS * nnS}")
check_text("VIII-A: refitting bootstrap intervals", f"the refitting bootstrap's intervals for Model~2's AUC, from about {g2(rS.ci_low)} to {g2(rS.ci_high)} "
           f"against the S\\&P~500 and from {g2(rB.ci_low)} to {g2(rB.ci_high)} against the bank-sector benchmark")
check_true("VIII-A: both intervals contain one half and values of 0.65 or more", rS.ci_low < 0.5 < rS.ci_high and rB.ci_low < 0.5 < rB.ci_high
           and min(rS.ci_high, rB.ci_high) >= 0.65, "holds")
check_text("VIII-A: eight AUCs", "without the event, every one of the eight AUCs lies between 0.41 and 0.52")
evp_S, evp_B = int(EV51.y.sum()), int(EV51.member_transaction_ids.map(lambda t: int(BKF.loc[t.split(";")[0]].y_reaction_m1p1_bank)).sum())
ev_fb = EV51[EV51.member_transaction_ids.str.contains("PA-0385")].iloc[0]
check_true("VIII-A: the FBOP event is negative (SPY) and positive (bank) and its members share the bank label",
           int(ev_fb.y) == 0 and all(len({int(BKF.loc[t].y_reaction_m1p1_bank) for t in ids.split(";") if t in BKF.index}) == 1
                                     for ids in EV51.member_transaction_ids), "holds")
shS, shB = 1 * evp_S / (evp_S * (51 - evp_S)), 1 * (51 - evp_B) / (evp_B * (51 - evp_B))
check_text("VIII-A: event-level shares and AUCs", f"makes FBOP one of {len(EV51)} events and reduces its share of the positive--negative pairs to "
           f"{100 * shS:.0f}\\% against the S\\&P~500 and {100 * shB:.0f}\\% against the bank-sector benchmark; Model~2's mean AUC becomes "
           f"{g3(EVL.loc[LRm, 'AUC_mean'])} and {g3(BEV.loc[LRm, 'AUC_mean'])}, and the gap between the benchmarks narrows from "
           f"{g3(fbi('y', AL, LRm) - fbi('y_bank', AL, LRm))} to {g3(EVL.loc[LRm, 'AUC_mean'] - BEV.loc[LRm, 'AUC_mean'])}.")
check_true("VIII-A: event-level positives 34 (SPY) and 36 (bank)", (evp_S, evp_B) == (34, 36), f"{evp_S}, {evp_B}")
d_ = lambda oc, smp, a, b: fbi(oc, smp, a) - fbi(oc, smp, b)
check_text("VIII-A: Model 3 against the baselines with and without the cluster", f"Without it, Model~3 still ranks below Model~2 and ridge regression "
           f"against the S\\&P~500, by {g3(d_('y', WO, LRm, M3m))} and {g3(d_('y', WO, RIm, M3m))} against {g3(d_('y', AL, LRm, M3m))} and "
           f"{g3(d_('y', AL, RIm, M3m))} with it, and above both against the bank-sector benchmark, by {g3(d_('y_bank', WO, M3m, LRm))} and "
           f"{g3(d_('y_bank', WO, M3m, RIm))} against {g3(d_('y_bank', AL, M3m, LRm))} and {g3(d_('y_bank', AL, M3m, RIm))}")
check_true("VIII-A: the four differences keep their signs without the cluster",
           all(d_("y", smp, b_, M3m) > 0 and d_("y_bank", smp, M3m, b_) > 0 for smp in (AL, WO) for b_ in (LRm, RIm)), "holds")
pdif = PCP[PCP.model.str.startswith("SNFF minus")]
check_true("VIII-A: neither test distinguishes Model 3's differences from zero (permutation two-sided p > 0.10; refitting intervals contain zero)",
           bool((pdif.p_two_sided > 0.10).all()) and all(t.loc[q].ci_low < 0 < t.loc[q].ci_high for t in (rfb, BRF)
                                                         for q in (f"diff SNFF minus {RIm}", f"diff SNFF minus {LRm}")), "holds")
check_text("VIII-A: Caution", f"U.S.~Bank's linked bid was one decision, which the consolidated inputs place in the Caution band ({f3_(c9.S_final)};")
check_text("VIII-A: returns", "a return of $-0.9\\%$ or $+1.3\\%$ is economically small")
check_text("VIII-A: pointer from VII-D", "Section~\\ref{sec:fbop} discusses what this concentration implies.")
for phrase in ("no predictive signal", "evidence of absence"):
    check_true(f"VIII-A: no claim of absent signal ('{phrase}')", phrase not in tex, "absent")
check_true("no claim of absent signal ('no signal' only where the text says the results should not be read that way)",
           tex.count("no signal") == tex.count("should not be read as showing that financial ratios carry no signal") + tex.count("not that the inputs carry no signal"), f"{tex.count('no signal')} use(s)")

# ---- statistical power and nonsignificant results (release 4.9)
PT = pd.read_csv(R / "table_permutation_test.csv").set_index("model")
p95 = PT.loc[[LRm, RIm, M3m], "null_p95"]
holm_min = float(PT.p_holm_one_sided.min())
check_true("C5: the smallest Holm-adjusted p is 0.13 and above 0.10 (insufficient to establish discrimination)",
           f"{holm_min:.2f}" == "0.13" and holm_min > 0.10 and PT.p_holm_one_sided.idxmin() == RIm, f"{holm_min:.4f}")
# release 4.13: 'abstract power' reworded; checked in the release 4.13 block below
# release 4.13: 'abstract risk link' reworded; checked in the release 4.13 block below
# release 4.13: 'VII-B significance threshold' reworded; checked in the release 4.13 block below
check_true("C5: the null 95th percentiles of the three models lie between 0.645 and 0.665", 0.645 <= p95.min() and p95.max() < 0.665, f"{p95.min():.4f}-{p95.max():.4f}")
check_text("C5 VII-C: bank reading", "The bank-sector results therefore do not establish a ranking ability in either direction, and in particular not a ranking "
           "worse than chance.")
check_text("C5 VII-C: Model 3's advantage under the bank benchmark", "Model~3's higher AUC means that it misorders fewer pairs than the logistic "
           "baselines, not that it ranks better than chance, and the permutation test does not distinguish its advantage from what uninformative outcomes "
           "produce")
check_true("C5: the advantage is not distinguishable (two-sided p >= 0.10 for both differences under the bank benchmark)",
           bool((PCP[(PCP.benchmark == "bank-sector index") & PCP.model.str.startswith("SNFF minus")].p_two_sided >= 0.10).all()), "holds")
sg = lambda x: f"$-${abs(x):.3f}" if x < 0 else f"$+${x:.3f}"
iv = lambda t, q: f"[{sg(t.loc[q].ci_low)}, {sg(t.loc[q].ci_high)}]"
check_text("C5 H1: refitting intervals of Model 3's differences", f"Model~3's differences from Model~2 and ridge regression, "
           f"{iv(rfb, 'diff SNFF minus ' + LRm)} and {iv(rfb, 'diff SNFF minus ' + RIm)} against the S\\&P~500 and {iv(BRF, 'diff SNFF minus ' + LRm)} and "
           f"{iv(BRF, 'diff SNFF minus ' + RIm)} against the bank-sector benchmark (Table~\\ref{{tab:paired}}), include gains as well as losses large enough "
           "to matter.")
check_true("C5 H1: each interval contains zero and reaches at least 0.10 on both sides",
           all(t.loc[q].ci_low <= -0.10 and t.loc[q].ci_high >= 0.10 for t in (rfb, BRF) for q in ("diff SNFF minus " + LRm, "diff SNFF minus " + RIm)), "holds")
check_text("C5 VIII: summary sentence", f"These are failures to reject the null hypothesis, not evidence that the models have no predictive value: with "
           f"{man['event_groups_primary']} independent events, the tests cannot rule out moderate predictive effects (Section~\\ref{{sec:limitations}}).")
lo_, hi_ = min(rfb.loc[f"AUC {m_}"].ci_low for m_ in (LRm, RIm, M3m)), max(rfb.loc[f"AUC {m_}"].ci_high for m_ in (LRm, RIm, M3m))
# release 4.13: 'VIII-F first limitation' reworded; checked in the release 4.13 block below
check_text("C5 IX: conclusion", f"With {man['event_groups_primary']} independent events and a smallest Holm-adjusted $p$-value of {holm_min:.2f}, the "
           "permutation tests and the refitting bootstrap can establish neither discrimination above chance nor its absence: H1 is not supported, but "
           "moderate predictive effects cannot be ruled out")
for phrase in ("show no ranking ability", "and no evidence that any model", "none that any ranks differently", "rank them no better than chance",
               "do no better than chance", "a ranking closer to chance, not a better one", "is not a better ranking", "disappears against a bank-sector"):
    check_true(f"C5: overstated phrase removed ('{phrase}')", phrase not in tex, "absent")

# ---- the decision problem: proposed bids, bid structures, and the market's reaction (release 4.9)
RBS = pd.read_csv(R / "table_robustness.csv")
RBB_ = pd.read_csv(R / "table_bank_robustness.csv")
PUB = "Published call-report inputs only"
pubS = {m_: float(RBS[(RBS.variant == PUB) & (RBS.model == m_)].AUC_mean.iloc[0]) for m_ in (LRm, RIm, M3m)}
pubB = {m_: float(RBB_[(RBB_.variant == PUB) & (RBB_.model == m_)].AUC_mean.iloc[0]) for m_ in (LRm, RIm, M3m)}
# release 4.13: 'abstract information sets' reworded; checked in the release 4.13 block below
check_text("C6 V-D: Protection score and rule Q depend on the terms", "Because the Protection score ($P_i = 0.60F_i + 0.40H_i$) and rule~$Q_i$, "
           "which requires $F_i = 1$, depend on the specified terms, as does the variant of rule~$U_i$ that requires support, each structure receives "
           "its own score.")
check_text("C6: the component definition uses the same weights", "P_i = 0.60\\, F_i + 0.40\\, H_i,")
check_text("C6: rule Q's condition includes F = 1", "$N_i \\geq N_{75}$ \\textbf{and} $F_i = 1$")
check_true("C6: the variant of rule U that requires support is in the robustness results", "U rule requires support (broad)" in set(RBS.variant), "holds")
check_text("C6 V-D: published inputs", f"Against the S\\&P~500 they rank the transactions about as well as the full models (mean AUC "
           f"{g3(pubS[LRm])}, {g3(pubS[RIm])}, and {g3(pubS[M3m])} for Model~2, ridge regression, and Model~3, against {g3(fbi('y', AL, LRm))}, "
           f"{g3(fbi('y', AL, RIm))}, and {g3(fbi('y', AL, M3m))}), and against the bank-sector benchmark about as poorly ({g3(pubB[LRm])}, "
           f"{g3(pubB[RIm])}, and {g3(pubB[M3m])}, against {g3(fbi('y_bank', AL, LRm))}, {g3(fbi('y_bank', AL, RIm))}, and "
           f"{g3(fbi('y_bank', AL, M3m))}; Table~\\ref{{tab:robustness}}).")
dmax = max(max(abs(pubS[m_] - fbi("y", AL, m_)), abs(pubB[m_] - fbi("y_bank", AL, m_))) for m_ in (LRm, RIm, M3m))
check_true("C6: 'about as well / as poorly' (published-input AUCs within 0.035 of the full models under both benchmarks)", dmax <= 0.035, f"{dmax:.3f}")
check_text("C6 V-D: what the analysis evaluates", "It evaluates realized winning bids: each transaction is scored with the terms its winning bid "
           "specified, and the criterion is the market's reaction to the announcement")
check_text("C6 V-D: not validated", "it does not validate the framework as a tool for screening prospective acquisitions or for choosing among bid structures.")
check_text("C6 VIII-D", "None of the uses for which such a framework is intended has been validated here.")
check_text("C6 VIII-F: fourth limitation", "The panel contains only realized winning bids, with the terms they specified, and no losing bids or alternative "
           "structures for the same target")
check_text("C6 IX", "The evaluation therefore concerns realized winning bids, scored with the terms those bids specified.")
check_true("C6: no claim of a validated screening tool", "validated screening" not in tex and "validated tool" not in tex, "absent")

# ---- the cost scenario as hypothetical (release 4.9)
SWP = pd.read_csv(R / "table_cost_ratio_sweep.csv")
ratios = sorted(SWP.ratio.astype(float).unique())
check_true("C7: the sweep covers the ratios 1:1 to 5:1", ratios[0] == 1 and ratios[-1] == 5, f"{ratios}")
# release 4.13: 'abstract hypothetical payoffs' reworded; checked in the release 4.13 block below
check_text("C7 IV-D: assumed payoffs", "To show how the choice of threshold interacts with asymmetric payoffs, we assume that in distressed M\\&A a false "
           "positive")
check_text("C7 IV-D: hypothetical ratio and sweep", f"The 3:1 ratio is a hypothetical scenario rather than an externally documented industry parameter, so "
           f"Table~\\ref{{tab:sensitivity}} sweeps it from {int(ratios[0])}:1 to {int(ratios[-1])}:1; each ratio in the sweep is an alternative "
           f"hypothetical scenario, not an estimate.")
check_text("C7 IV-D: what utility is not", "It is a payoff under these assumptions, not a measure of what an acquisition cost or earned.")
check_text("C7 Table 2 caption", "Utility under the Hypothetical Payoffs $B=1$, $L=3$")
check_text("C7 VII-J", "The utilities are computed on the actual outcomes with the assumed payoffs ($B = 1$, $L = 3$)")
check_text("C7 VIII-C", "The 3:1 ratio assumes that pursuing an acquisition that the market receives negatively costs three times what pursuing one that "
           "it receives positively gains. It is a hypothetical scenario")
check_text("C7 VIII-C: sweep", f"the ratios from {int(ratios[0])}:1 to {int(ratios[-1])}:1 in Table~\\ref{{tab:sensitivity}} are alternative scenarios of the "
           "same kind")
check_text("C7 VIII-F: third limitation", f"its 3:1 loss-to-benefit ratio and the alternatives from {int(ratios[0])}:1 to {int(ratios[-1])}:1 are hypothetical "
           "scenarios")
check_text("C7 IX", "These utilities illustrate the consequences of threshold selection under assumed payoffs.")
check_true("C7: the policies' utilities are computed at L = 3 (pursue-all utility = (P - 3N)/55)",
           abs(float(pol.loc[pol.index[pol.index.str.contains("all", case=False)][0]].filter(like="utility").iloc[0]) - (35 - 3 * 20) / 55) < 1e-9
           if any(pol.index.str.contains("all", case=False)) else False, "holds")
for phrase in ("conservative 3:1", "a conservative scenario", "realize negative utility when each costs"):
    check_true(f"C7: phrase removed ('{phrase}')", phrase not in tex, "absent")

# ---- the two Spider-score AUCs: out-of-sample (Table 7) and descriptive full panel (Table 14) (release 4.10)
CMP_S = pd.read_csv(R / "table_spider_components.csv")
CMP_B = pd.read_csv(R / "table_bank_spider_components.csv")
sf_S = float(CMP_S[(CMP_S.component == "S_final") & (CMP_S.deals == "primary 55")].AUC.iloc[0])
sf_B = float(CMP_B[(CMP_B.component == "S_final") & (CMP_B.deals == "primary 55")].AUC.iloc[0])
cv_S = float(pd.read_csv(R / "table_main_comparison.csv").set_index("model").loc[SCm, "AUC_mean"])
cv_B = float(pd.read_csv(R / "table_bank_main_comparison.csv").set_index("model").loc[SCm, "AUC_mean"])
check_text("C8 Table 14 caption", "Descriptive, Full-Panel AUC against a Positive CAR)}")
check_true("C8 Table 14 caption begins as before", "\\caption{Direction of the Spider Score and Its Components (" in tex, "holds")
check_text("C8 Table 14 note", f"The table describes the full panel and is not an out-of-sample evaluation: the Spider score's AUCs here ({g3(sf_S)} and "
           f"{g3(sf_B)}) use bounds and thresholds fitted once on all 55 transactions, whereas its out-of-sample AUCs in Table~\\ref{{tab:main_results}} "
           f"({g3(cv_S)} and {g3(cv_B)}) use bounds and thresholds fitted inside each training fold of the repeated grouped cross-validation. The two "
           "follow different protocols and do not contradict each other.")
check_true("C8: the full-panel and cross-validated values differ, and Table 14's rows are the full-panel values", g3(sf_S) != g3(cv_S) and g3(sf_B) != g3(cv_B)
           and f"Spider score $\\tilde S$ & $+$ & {g3(sf_S)} &" in tex, f"{sf_S:.4f} vs {cv_S:.4f}; {sf_B:.4f} vs {cv_B:.4f}")
check_text("C8 Table 7 note", "its normalization bounds and thresholds are fitted inside each training fold, and Table~\\ref{tab:components} gives its "
           "descriptive AUC with bounds fitted once on the full panel.")
check_text("C8 VII-A", f"The Spider score itself has a mean out-of-sample AUC of {g3(cv_S)} ({g3(sf_S)} on the full panel with bounds fitted once; "
           "Table~\\ref{tab:components})")
check_text("C8 VII-H", f"With bounds and thresholds fitted once on all 55 transactions, the Spider score's AUC is {g3(sf_S)} against the S\\&P~500; "
           f"Table~\\ref{{tab:main_results}} reports {g3(cv_S)}, the mean over the 50 partitions of the repeated grouped cross-validation")
check_text("C8 IX", f"(cross-validated AUC {g3(cv_S)} and {g3(cv_B)})")

# ---- the paper led by its empirical finding (release 4.11)
STA_, STB_, STC_ = "A: measured inputs", "B: A + Spider score", "C: A + interaction rules"
abB = pd.read_csv(R / "table_bank_ablation.csv").set_index("model")
aA, aB, aC = (ab.loc[k, "AUC_mean"] for k in (STA_, STB_, STC_))
check_true("C1: adding the Spider score leaves the AUC essentially unchanged; adding the rules lowers it (S&P 500)",
           abs(aB - aA) < 0.005 and aC < aA - 0.02, f"{aA:.3f}, {aB:.3f}, {aC:.3f}")
check_true("C1: under the bank-sector benchmark the rules move the AUC toward one half from below",
           abB.loc[STA_, "AUC_mean"] < abB.loc[STC_, "AUC_mean"] < 0.5, f"{abB.loc[STA_, 'AUC_mean']:.3f} -> {abB.loc[STC_, 'AUC_mean']:.3f}")
check_text("C1 title", "Do Interaction Rules Improve Decisions on FDIC-Assisted Bank Acquisitions? A Leakage-Controlled Evaluation of the Spider Network "
           "Filtering Framework")
check_text("C1 abstract: main result", f"the Spider-enhanced model's mean area under the receiver operating characteristic curve is "
           f"{f(SMC.loc[M3m, 'AUC_mean'])}, against {f(SMC.loc[LRm, 'AUC_mean'])} for logistic and {f(SMC.loc[RIm, 'AUC_mean'])} for ridge regression; "
           "an ablation traces the shortfall to the interaction rules, not the component scores.")
# release 4.13: 'abstract weights' reworded; checked in the release 4.13 block below
check_true("C1 abstract: every fitted model below one half against the bank-sector benchmark",
           all(BMC.loc[m_, "AUC_mean"] < 0.5 for m_ in BMC.index if m_ != SCm), "holds")
check_text("C1 introduction: first contribution", f"(mean area under the receiver operating characteristic curve, AUC, {f(SMC.loc[M3m, 'AUC_mean'])} against {f(SMC.loc[LRm, 'AUC_mean'])}) and ridge "
           f"regression ({f(SMC.loc[RIm, 'AUC_mean'])}), and an ablation locates the shortfall in the interaction rules rather than in the component "
           f"scores: adding the Spider score to the measured inputs leaves the mean AUC essentially unchanged ({f(aB)} against {f(aA)}), whereas adding "
           f"the four rules lowers it to {f(aC)}.")
# release 4.13: 'introduction weights' reworded; checked in the release 4.13 block below
# release 4.13: 'introduction selection' reworded; checked in the release 4.13 block below
check_text("C1 introduction: power", f"With {man['event_groups_primary']} independent events and a smallest Holm-adjusted $p$-value of {holm_min:.2f}, "
           "the evidence that any model ranks better than chance is weak, but the tests cannot rule out moderate predictive effects either")
p4B = pol.loc["4B: F1-tuned threshold"]
check_text("C1 introduction: decision analysis", f"A threshold tuned for the F1 score (the harmonic mean of precision and recall) approves most of the acquisitions that the market received negatively "
           f"({100 * p4B.FPR:.1f}\\% against the S\\&P~500)")
check_text("C1 introduction: utility", f"it realizes a utility well below that of declining every transaction (${p4B.utility_3to1:.3f}$)")
check_true("C1: the F1-tuned rule's utility is negative and its FPR above one half", p4B.utility_3to1 < 0 and p4B.FPR > 0.5, "holds")
check_text("C1 VIII: lead", "The central result of this evaluation is that the Spider interaction features did not reliably improve on logistic models "
           "that use the same inputs")
check_text("C1 IX: lead", "The main finding of this paper is a rigorously validated non-improvement")
check_text("C1 IX: ablation", f"left the mean AUC against the S\\&P~500 unchanged ({f(aB)} against {f(aA)}), whereas adding the four rules lowered it to "
           f"{f(aC)}")
check_text("C1 Table 17", "What the Evaluation Implies for Potential Users of an Interaction-Aware Decision Framework")

# ---- conciseness and editorial consistency (release 4.12)
DP4 = pd.read_csv(R / "table_decision_policies.csv").set_index("policy")
p4a_t = DP4.loc["4A: fixed Spider thresholds", "pursue"]
check_text("C9 Table 2: Pursue counts read relative to n", f"Pursue (of $n$): mean number of the $n$ transactions (Panels C and D: acquisition events) "
           f"recommended for pursuit, e.g., {p4a_t:.1f} of 55 for 4A in Panel~A;")
check_text("C9 VII-J: 4C relative to n", f"pursues {DP4.loc['4C: cost-based threshold (3:1)', 'pursue']:.1f} of the 55 transactions with a")
check_text("C9 VII-J: 4B relative to n", f"recommends Pursue on {DP4.loc['4B: F1-tuned threshold', 'pursue']:.1f} of 55 transactions on average")
check_true("C9: 'Pursue' counts in Table 2 never exceed n (55 transactions, 51 events)", (DP4.pursue <= 55).all(), f"{DP4.pursue.max():.1f}")
fc = [m.start() for m in re.finditer("First-Citizens", tex)]
check_true("C9: 'First-Citizens' appears only in the bank's official name",
           len(fc) >= 1 and all(tex.startswith("First-Citizens Bank \\& Trust", i) for i in fc), f"{len(fc)} occurrences")
check_true("C9: the hyphenated short forms are gone", "First-Citizens Bank's" not in tex and "which First-Citizens was" not in tex, "absent")
check_text("C9: the acquirer's short name defined", "a subsidiary of First Citizens BancShares (together, First Citizens)")
check_true("C9: AUC is abbreviated consistently (no 'AUC-ROC')", "AUC-ROC" not in tex, "absent")
check_text("C9: AUC defined at its first use in the body", "(mean area under the receiver operating characteristic curve, AUC,")
check_true("C9: AUC defined before H1 uses the abbreviation", tex.index("receiver operating characteristic curve, AUC,") < tex.index("measured by the AUC"), "holds")
check_text("C9: F1 defined at its first use", "the F1 score (the harmonic mean of precision and recall)")
check_true("C9: F1 defined once", tex.count("harmonic mean of precision and recall") == 1, str(tex.count("harmonic mean of precision and recall")))
check_text("C9: CRSP defined", "the Center for Research in Security Prices (CRSP)")
check_text("C9: SEC spelled out", "filing with the Securities and Exchange Commission")
check_text("C9: SPY defined in Table 5", "SPY: S\\&P~500 benchmark; bank: bank-sector benchmark")
check_true("C9: equations cited as Eq./Eqs.", re.search(r"(?<!Eq\.~)(?<!Eqs\.~)(?<!and~)\\eqref\{", tex) is None, "holds")
check_true("C9: new labels referenced", "\\ref{sec:future}" in tex and "\\ref{sec:explain}" in tex, "holds")
for phrase in ("A single transaction cannot validate or refute the framework", "The public data available before the failure did not show the run",
               "Mean AUCs range from", "was a robustness check in the submitted version and was made co-primary during the revision"):
    check_true(f"C9: repeated passage removed ('{phrase[:40]}...')", phrase not in tex, "absent")
# ---- remaining audit issues (release 4.13): event level, weights, selection, significance vs power, hypothetical payoffs, abstract
abs_tex = tex[tex.index("\\begin{abstract}"):tex.index("\\end{abstract}")]
EVs = pd.read_csv(R / "table_event_level.csv").set_index("model").AUC_mean
EVb = pd.read_csv(R / "table_bank_event_level.csv").set_index("model").AUC_mean
TXs, TXb, TXs_avg = SMC.AUC_mean, BMC.AUC_mean, SMC.AUC_event_mean
FIT = [m_ for m_ in TXs.index if m_ != SCm]
check_true("A1: every fitted model's event-level AUC is lower than its transaction-level AUC against the S&P 500", all(EVs[m_] < TXs[m_] for m_ in FIT), "holds")
check_true("A1: every fitted model's event-level AUC is higher, and below one half, against the bank-sector benchmark",
           all(TXb[m_] < EVb[m_] < 0.5 for m_ in FIT), f"max {EVb[FIT].max():.3f}")
check_true("A1: the Spider score moves the other way under both benchmarks", EVs[SCm] > TXs[SCm] and EVb[SCm] < TXb[SCm], "holds")
check_text("A1 VII-K: the Spider score's two moves", f"(from {f(TXs[SCm])} to\n{f(EVs[SCm])} and from {f(TXb[SCm])} to {f(EVb[SCm])})")
closer_s = [m_ for m_ in FIT if abs(EVs[m_] - 0.5) < abs(TXs[m_] - 0.5)]
closer_b = [m_ for m_ in FIT if abs(EVb[m_] - 0.5) < abs(TXb[m_] - 0.5)]
LAm = [m_ for m_ in FIT if m_.startswith("LASSO")][0]
check_true("A1: seven of eight fitted models closer to one half at the event level against the S&P 500, the exception the LASSO model",
           len(closer_s) == 7 and set(FIT) - set(closer_s) == {LAm}, str(sorted(set(FIT) - set(closer_s))))
check_true("A1: all eight fitted models closer to one half at the event level against the bank-sector benchmark", len(closer_b) == 8, str(len(closer_b)))
check_text("A1 VII-K: the LASSO exception", f"all but the LASSO model's\n({f(TXs[LAm])} against {f(EVs[LAm])})")
check_text("A1 VII-K: reading", "Counting by decisions therefore weakens the evidence of ranking ability in either direction rather than revealing a different ranking")
check_text("A1 VII-K: S&P 500 fall attributed to counting each event once", "every fitted model's AUC is lower against the S\\&P~500, mostly because each multi-bank event, "
           "above all the FBOP purchase, counts once")
check_true("A1: averaging each event's predictions already lowers every fitted model's AUC (the attribution)", all(TXs_avg[m_] < TXs[m_] for m_ in FIT)
           and abs(TXs_avg[FIT].min() - EVs[FIT].min()) < 0.01 and abs(TXs_avg[FIT].max() - EVs[FIT].max()) < 0.01, "ranges within 0.01")
check_true("A1 VII-A: the Spider score's averaged AUC rises, so 'every fitted model' is needed", TXs_avg[SCm] > TXs[SCm], f"{TXs_avg[SCm]:.3f}")
check_text("A1 VII-A: every fitted model", "Counting each event once lowers every fitted model's AUC, to between")
check_text("A1 IX: event level", "the AUCs of nearly all fitted models lie closer to one half under both benchmarks, which weakens the evidence in either "
           "direction, and these conclusions do not change")
check_true("A1: the unqualified event-level phrase is gone", "discriminates less" not in tex, "absent")

mx = f(m3s.diff_ridge_mean.max())
check_true("A2: across every constant set the score stays below ridge regression and Model 3 never beats it by more than 0.002 (SPY)",
           WSP[WSP.benchmark == "SPY"].AUC_mean.max() < SMC.loc[RIm, "AUC_mean"] and round(float(m3s.diff_ridge_mean.max()), 3) <= 0.002, mx)
check_text("A2 VII-E: closing, qualified", f"Within the alternatives examined, the unfavorable comparison with the logistic baselines therefore does not depend on the "
           f"particular constants: against the S\\&P~500, no constant set lets the score or Model~3 rank the transactions better than ridge regression by more than {mx}")
check_text("A2 VII-E: the score's position depends on the constants", f"{int((rw_s > 0.5).sum())} of the 1,000 sign-preserving sets place it above one half")
# release 4.13 (second pass): reworded; checked in the block below
check_true("A2: 226 refitted sets of 2,026", len(m3s) == 226 and len(WVA) == 2026, f"{len(m3s)} of {len(WVA)}")
check_text("A2 VII-E: not varied", "no alternative varies the weights inside the Protection and Risk components, the rule thresholds, or the rules themselves")
check_text("A2 VII-E: no claim for new acquisitions", "the analysis does not show that any alternative weighting would rank new acquisitions better")
# release 4.13 (second pass): reworded; checked in the block below
check_text("A2 VIII: Discussion", "or, within the alternatives examined, on the expert weights and adjustments (Section~\\ref{sec:weights})")
# release 4.13 (second pass): reworded; checked in the block below
# release 4.13 (second pass): reworded; checked in the block below
for phrase in ("do not depend on the particular constants", "neither result depends on the expert constants", "Results hold across", "The comparison holds across"):
    check_true(f"A2: unqualified weight claim gone ('{phrase}')", phrase not in tex, "absent")

check_text("A3 I: introduction", f"an analysis of the {n_exc} eligible transactions whose prices were not collected shows how sample selection could bias the "
           "evaluation, without resolving that concern.")
check_text("A3 VIII: Discussion", f"the {n_exc} eligible transactions whose prices were not collected had smaller acquirers, and within the panel the three "
           f"models' AUCs among transactions with smaller acquirers are below one half against the S\\&P~500")
# release 4.13 (second pass): reworded; checked in the block below
check_true("A3: the 26 and 13 add up to the 39, and 17 and 7 parents to 24", n_acq + n_lst == n_exc and p_acq + p_lst == p_exc, f"{n_acq}+{n_lst}, {p_acq}+{p_lst}")
check_text("A3 IX: Conclusion", f"Whether they extend to the {n_exc} eligible transactions whose prices were not collected, which had smaller acquirers, "
           "remains open.")
for phrase in ("without prices", "available prices:", "are missing,", "acquirers below chance"):
    check_true(f"A3: imprecise selection wording gone ('{phrase}')", phrase not in tex, "absent")

check_text("A4 VII-B: critical values", f"The 95th percentiles of the permutation distributions, {p95.min():.2f} to {p95.max():.2f}, are the critical values of "
           f"the one-sided tests: an observed cross-validated AUC must exceed about {p95.min():.2f} to be significant at the 5\\% level, before the Holm "
           "adjustment. These are thresholds for significance, not measures of power, which we did not estimate")
lo_r, hi_r = lo_, hi_
check_text("A4 VII-B: variability of the AUC", f"(from about {lo_r:.2f} to {hi_r:.2f} in the refitting bootstrap above)")
check_text("A4 VIII-F: first limitation", f"The smallest Holm-adjusted $p$-value, {holm_min:.2f}, means that the evidence is insufficient to establish "
           f"discrimination above chance, not that the models have no predictive value: an observed cross-validated AUC must exceed about "
           f"{p95.min():.2f}, the 95th percentile of the permutation distribution, to be significant at the 5\\% level (Table~\\ref{{tab:perm}}), a "
           f"critical value rather than a measure of power, which was not estimated; and the refitting bootstrap's intervals for each model's AUC, from "
           f"about {lo_r:.2f} to {hi_r:.2f} against the S\\&P~500, include values that would indicate moderate discrimination.")
for phrase in ("before the test detects it", "before the permutation test detects it", "could easily go undetected"):
    check_true(f"A4: threshold no longer presented as power ('{phrase}')", phrase not in tex, "absent")

for phrase in ("the cost-based threshold", "under symmetric costs", "common 3:1 loss", "Because a false positive costs more", "the asymmetric cost of the decision"):
    check_true(f"A5: decision cost stated as fact gone ('{phrase}')", phrase not in tex, "absent")
for phrase in ("the threshold derived from the hypothetical 3:1 payoffs", "under symmetric hypothetical payoffs", "the common hypothetical 3:1 ratio",
               "are only assumed to be asymmetric in the decision analysis", "the decision's payoffs, here assumed to be asymmetric",
               "Under hypothetical payoffs in which a negatively received acquisition costs three times the gain from a well-received one"):
    check_text(f"A5: payoffs labeled hypothetical or assumed ('{phrase[:40]}')", phrase)

check_true("A6: the abstract leads with the finding", abs_tex[len("\\begin{abstract}"):].replace("\\rev{", "").lstrip().startswith(
    "The four interaction rules of the Spider Network Filtering Framework, which feed a logistic model and a Pursue/Caution/Avoid rule, did not "
    "improve on logistic models with the same inputs"), abs_tex[17:90])
check_text("A6 abstract: sample", "the winning bids in 55 acquisitions assisted by the Federal Deposit Insurance Corporation (2008--2024)")
# release 4.13 (second pass): reworded; checked in the block below
check_text("A6 abstract: power", f"find little evidence that any model beats chance but, with {man['event_groups_primary']} independent events, cannot rule "
           "out moderate effects.")
check_text("A6 abstract: risk link", "an apparent link between target distress and higher returns fails against the bank-sector benchmark.")
# release 4.13 (second pass): reworded; checked in the block below
_at = re.sub(r"\\rev\{|\\protect", "", abs_tex[len("\\begin{abstract}"):]).replace("}", "").replace("S\\&P~500", "S&P 500").replace("\\&", "&").replace("~", " ")
check_true("A6: abstract within 250 words (S&P 500 as two)", len(_at.split()) <= 250, str(len(_at.split())))
# ---- release 4.13, second pass: weights by benchmark, the reasons for missing prices, the information sets
M3W = pd.read_csv(R / "weight_sensitivity_model3.csv")
w_s, w_b = M3W[M3W.benchmark == "SPY"], M3W[M3W.benchmark == "bank-sector index"]
check_true("B1: 226 refitted Model 3 sets per benchmark (the reference and 225 alternatives)", len(w_s) == 226 and len(w_b) == 226, f"{len(w_s)}, {len(w_b)}")
check_true("B1 SPY: 4 sets above ridge, by at most 0.002; best Model 3 AUC 0.634",
           int((w_s.diff_ridge_mean > 0).sum()) == 4 and f(w_s.diff_ridge_mean.max()) == "0.002" and f(w_s.AUC_mean.max()) == "0.634", f(w_s.AUC_mean.max()))
check_true("B1 bank: every set above ridge, by 0.128 to 0.155, and below one half (at most 0.435)",
           (w_b.diff_ridge_mean > 0).all() and (w_b.AUC_mean < 0.5).all(), f"{f(w_b.diff_ridge_mean.min())}-{f(w_b.diff_ridge_mean.max())}, {f(w_b.AUC_mean.max())}")
rng_b = f"by {f(w_b.diff_ridge_mean.min())} to {f(w_b.diff_ridge_mean.max())}"
check_text("B1 abstract", f"One four-bank purchase supplies most of the models' discrimination against the S\\&P~500, where none of {len(w_s) - 1} "
           f"alternative weightings lifts the refitted Spider-enhanced model more than {f(w_s.diff_ridge_mean.max())} above ridge regression.")
check_text("B1 introduction", f"Across {len(WVA) - 1:,} alternative Spider-score specifications and {len(w_s) - 1} alternative refitted specifications of the "
           f"Spider-enhanced model, the largest improvement over ridge regression against the S\\&P~500 is about {f(w_s.diff_ridge_mean.max())} AUC; "
           "against the bank-sector benchmark the refitted model ranks above ridge regression in every tested specification but below one half throughout")
check_text("B1 conclusion", f"across {len(WVA) - 1:,} alternative Spider-score specifications and {len(w_s) - 1} alternative refitted specifications of "
           f"the Spider-enhanced model, the largest improvement over ridge regression against the S\\&P~500 is about {f(w_s.diff_ridge_mean.max())} AUC, "
           f"and against the bank-sector benchmark the refitted model ranks above ridge regression in every tested specification ({rng_b}) but below "
           f"one half throughout (at most {f(w_b.AUC_mean.max())}). These are descriptive sensitivity results, not validated optimal models")
check_text("B1 VII-E", f"every set leaves Model~3 above ridge regression, {rng_b}, but below one half, at most {f(w_b.AUC_mean.max())}.")
check_text("B1 VII-E: refitted subset", f"Model~3 was refitted for {len(w_s)} of the {len(WVA):,} constant sets (the reference and {len(w_s) - 1} "
           "alternatives), not for all of them")
for phrase in ("neither the score nor the Spider-enhanced model materially beats", "neither the score nor the refitted Spider-enhanced model ranks",
               "across the 2,025 alternative constant sets examined, neither"):
    check_true(f"B1: benchmark-free weight claim gone ('{phrase[:45]}')", phrase not in tex, "absent")

check_text("B2 VIII-F: second limitation", f"the panel covers only acquirers with a U.S.-listed parent whose prices the study's price data include: "
           f"{n_exc} of the 94 such transactions among the 150 largest failures are not in the panel. Of these, {n_acq} involved {p_acq} acquiring "
           f"parents that were later acquired and delisted, and {n_lst} involved {p_lst} parents that remain publicly traded; these characteristics "
           "describe the excluded transactions but do not establish the precise reasons why their historical prices were not retrieved.")
check_text("B2 VIII-E: future work", f"historical prices for the {n_lst} transactions involving seven still-listed parents may be recoverable "
           f"through improved ticker mapping and price retrieval, and a database covering delisted securities may also help recover those for the "
           f"remaining {n_acq} transactions involving {p_acq} parents")
for phrase in ("because the parent was later", "would recover the other"):
    check_true(f"B2: delisting no longer asserted as the cause ('{phrase}')", phrase not in tex, "absent")

check_text("B3 abstract: information sets", "Financial inputs predate failure; transaction inputs reflect bid terms and publicly announced regulatory support;")
check_text("B3 V-D: the two deal terms", "To show that the conclusions do not depend on the two deal terms, Section")
check_text("B3 VII-D: the two deal terms", "so none of the conclusions depends on the two deal terms.")
check_text("B3 VIII: SVB exception", "which the winning bidder knows before outside investors do, except for SVB's publicly announced support,")
check_text("B3 V-D: SVB's support public before its sale", "The narrow support indicator is an exception: it equals one only for SVB")
for phrase in ("known in advance only to the winning bidder", "information that only the bidder had", "which only the bidder knows"):
    check_true(f"B3: bidder-only claim that contradicts the SVB exception gone ('{phrase[:40]}')", phrase not in tex, "absent")
# ---- release 4.15: price recovery stated as possible, and the investors' information
check_text("C1 V-D: when outside investors learn the terms", "Outside investors generally learn these transaction terms through the FDIC announcement or "
           "subsequent acquirer disclosures, although certain regulatory support arrangements may already be publicly known before the acquisition announcement.")
for phrase in ("Outside investors learn these terms only from", "Prices are available from the price source used here", "would provide them for the other",
               "the price source of this study covers"):
    check_true(f"C1: superseded claim gone ('{phrase[:40]}')", phrase not in tex, "absent")
# ---- release 4.16: when the deal terms become public, in III-B, V-D and VIII-F
check_text("D1 III-B: how the terms become public", "that become public through the FDIC's announcement, the acquirer's subsequent disclosures, or, "
           "for regulatory support, earlier regulatory announcements.")
check_text("D1 V-D: the investor's problem", "learns most terms at the announcement or from later disclosures, although regulatory support such as "
           "SVB's may be public earlier.")
check_text("D1 VIII-F: fourth limitation", "Outside investors generally learn them through the FDIC's announcement or the acquirer's subsequent "
           "disclosures, except that SVB's regulatory support, the systemic-risk exception and the bridge bank, was publicly announced two weeks "
           "before its acquisition.")
check_text("D1 V-D: the dates that support 'two weeks'", "announced on March~12 and~13, 2023~\\cite{jointstatement2023}, two weeks before its sale")
for phrase in ("the market learns from the FDIC's announcement", "but not to that of outside investors before the announcement", "learns the terms only at the announcement"):
    check_true(f"D1: announcement-only claim gone ('{phrase[:40]}')", phrase not in tex, "absent")
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
