"""Fill the audit-report and checklist templates with the final numbers.

usage: python3 -I fill_reports.py <results_dir> <final_tex> <templates_dir> <out_dir> <number_check_txt>
                                  <pages> <latex_status> <clean_rerun_status> <bank_rerun_status> <release_zip>
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

R, TEX, TPL, OUT, NC = (Path(a) for a in sys.argv[1:6])
pages, latex_status, clean, bank_rerun, release_zip = sys.argv[6], sys.argv[7], sys.argv[8], sys.argv[9], Path(sys.argv[10])
SNFF, LR, RIDGE, PAIR, SCORE = "SNFF + LR (Model 3)", "Logistic regression (L2, C=1)", "Ridge logistic", "LR + pairwise interactions", "Spider score alone (Model 1)"
m = pd.read_csv(R / "table_main_comparison.csv").set_index("model")
perm = pd.read_csv(R / "table_permutation_test.csv").set_index("model")
boot = pd.read_csv(R / "table_cluster_bootstrap.csv").set_index("quantity")
comp = pd.read_csv(R / "table_spider_components.csv")
pol = pd.read_csv(R / "table_decision_policies.csv").set_index("policy")
rb = pd.read_csv(R / "table_robustness.csv")
br = pd.read_csv(R / "table_broader90.csv").set_index("model")
gc = pd.read_csv(R / "table_broader90_grouping_check.csv")
man = json.loads((R / "RUN_MANIFEST.json").read_text())
eight = [k for k in m.index if k != SCORE]
r55 = comp[(comp.component == "R_score") & (comp.deals == "primary 55")].iloc[0]
r35 = comp[(comp.component == "R_score") & (comp.deals != "primary 55")].iloc[0]


def bq(other):
    q = boot.loc[f"AUC difference SNFF minus {other}"]
    return f"{q.estimate:+.3f}", f"[{q.ci_low:+.3f}, {q.ci_high:+.3f}]"


# robustness table (markdown)
order = [("Reaction-day CAR[-1,+1] (primary)", "Primary specification"), ("Release-date CAR[0,+1]", "CAR[0,+1] around the announcement date"),
         ("Release-date CAR[-1,+1] (June window)", "CAR[-1,+1] around the announcement date (June window)"),
         ("Reaction-day CAR[-1,+1], market model", "Market-model CAR"),
         ("Reaction-day CAR[-1,+1], bank-index benchmark", "CAR against the bank-sector benchmark"),
         ("Published call-report inputs only", "Six published inputs only (no F, H)"), ("Broad support definition", "Broad support definition"),
         ("U rule requires support (broad)", "Rule U requires support"), ("Z rule removed", "Rule Z removed")]
rows = ["| Variant | Positive CAR | Model 2 | Ridge | Model 3 | Spider score |", "|---|---|---|---|---|---|"]
for v, lab in order:
    x = rb[rb.variant == v].set_index("model")
    rows.append(f"| {lab} | {int(x.positives.iloc[0])}/55 | {x.loc[LR, 'AUC_mean']:.3f} | {x.loc[RIDGE, 'AUC_mean']:.3f} | {x.loc[SNFF, 'AUC_mean']:.3f} | "
                f"{x.loc[SCORE, 'AUC_mean']:.3f} |")
rows.append(f"| Broader panel (90) | 56/90 | {br.loc[LR, 'AUC_mean']:.3f} | {br.loc[RIDGE, 'AUC_mean']:.3f} | {br.loc[SNFF, 'AUC_mean']:.3f} | "
            f"{br.loc[SCORE, 'AUC_mean']:.3f} |")
rob_table = "\n".join(rows)

# grouping check table (markdown)
gp = gc.pivot_table(index="model", columns="grouping", values="AUC_mean")
cor = [c for c in gp.columns if c.startswith("listed parent")][0]
pkg = [c for c in gp.columns if c.startswith("acquiring-bank")][0]
lab = {LR: "Model 2 (logistic, C = 1)", RIDGE: "Ridge logistic", SNFF: "Model 3 (Spider + LR)", SCORE: "Spider score alone"}
rows = [f"| Model | Corrected grouping ({int(gc[gc.grouping == cor].groups.iloc[0])} clusters) | Step 4 package grouping "
        f"({int(gc[gc.grouping == pkg].groups.iloc[0])} clusters) | Difference |", "|---|---|---|---|"]
for k in (LR, RIDGE, SNFF, SCORE):
    rows.append(f"| {lab[k]} | {gp.loc[k, cor]:.3f} | {gp.loc[k, pkg]:.3f} | {gp.loc[k, pkg] - gp.loc[k, cor]:+.3f} |")
grouping_table = "\n".join(rows)
gc_split = int(gc[gc.grouping == pkg].partitions_with_pair_split.max())
gc_maxdiff = f"{(gp[pkg] - gp[cor]).abs().max():.3f}"

# number check summary
nct = NC.read_text()
n_ok, n_fail = nct.count("[ok]"), nct.count("[FAIL]")
number_check = f"all {n_ok} prose checks pass" if n_fail == 0 else f"{n_fail} of {n_ok + n_fail} prose checks FAIL"

# abstract length
tex = "\n".join(re.sub(r"(?<!\\)%.*", "", line) for line in TEX.read_text().splitlines())  # drop LaTeX comments, keep \%
abstract = tex[tex.index(r"\begin{abstract}") + 16: tex.index(r"\end{abstract}")]
abstract = re.sub(r"\\emph\{([^}]*)\}", r"\1", abstract)
markers = []
for mt in re.finditer(r"\\confirm\{([^}]*)", tex):
    # the name is the last braced group on the \begin{IEEEbiography...} line (the photo argument nests brackets and braces)
    bio = list(re.finditer(r"\\begin\{IEEEbiography(?:nophoto)?\}[^\n]*\{([^{}\n]*)\}[ \t]*$", tex[:mt.start()], re.M))
    inside = bio and tex.rfind("\\end{IEEEbiography", 0, mt.start()) < bio[-1].start()
    where = f"Biography of {bio[-1].group(1)}: " if inside else ""
    if not where:
        sec = list(re.finditer(r"\\(?:section\*?|subsection)\{([^}]*)\}|\\tfootnote", tex[:mt.start()]))
        where = "First-page footnote: " if sec and sec[-1].group(0) == "\\tfootnote" else (f"{sec[-1].group(1)}: " if sec else "")
    markers.append(where + mt.group(1))

WORDS = {2: "two", 3: "three", 4: "four", 5: "five"}
rfb = pd.read_csv(R / "table_bootstrap_refit.csv").set_index("quantity")
fi = pd.read_csv(R / "table_fbop_influence_model2.csv")
rv = pd.read_csv(R / "table_risk_validation.csv")
VB = "Reaction-day CAR[-1,+1], bank-index benchmark"
rvb55 = rv[(rv.outcome == VB) & (rv.deals == "primary 55")].iloc[0]
rvb35 = rv[(rv.outcome == VB) & (rv.deals != "primary 55")].iloc[0]
pub = rb[rb.variant == "Published call-report inputs only"].set_index("model")


def rq(other):
    q = rfb.loc[f"diff SNFF minus {other}"]
    return f"{q['mean']:+.3f}", f"[{q.ci_low:+.3f}, {q.ci_high:+.3f}]", f"{100 * q.share_below_zero:.0f}"


def fb(out, smp):
    return f"{float(fi[(fi.outcome == out) & (fi['sample'] == smp)].AUC_mean.iloc[0]):.3f}"


vc = re.findall(r"value-creat\w*|value creation|value-destroy\w*|created value", re.sub(r"\s+", " ", TEX.read_text()))
value_words = ("no remaining use" if not vc else
               f"{len(vc)} remaining use{'s' if len(vc) > 1 else ''}, in the sentence that says the transactions are not called value-creating")
with zipfile.ZipFile(release_zip) as z:
    release_files = sum(1 for i in z.infolist() if not i.is_dir())
release_sha = hashlib.sha256(release_zip.read_bytes()).hexdigest()
vals = {
    "M3_AUC": f"{m.loc[SNFF, 'AUC_mean']:.3f}", "M2_AUC": f"{m.loc[LR, 'AUC_mean']:.3f}", "RIDGE_AUC": f"{m.loc[RIDGE, 'AUC_mean']:.3f}",
    "PAIR_AUC": f"{m.loc[PAIR, 'AUC_mean']:.3f}", "SCORE_AUC": f"{m.loc[SCORE, 'AUC_mean']:.3f}",
    "EVAUC_MIN": f"{m.loc[eight, 'AUC_event_mean'].min():.3f}", "EVAUC_MAX": f"{m.loc[eight, 'AUC_event_mean'].max():.3f}",
    "P_M2": f"{perm.loc[LR, 'p_value_one_sided']:.2f}", "P_RIDGE": f"{perm.loc[RIDGE, 'p_value_one_sided']:.2f}",
    "P_M3": f"{perm.loc[SNFF, 'p_value_one_sided']:.2f}", "P_SCORE2": f"{perm.loc[SCORE, 'p_value_two_sided']:.2f}",
    "B_RIDGE": bq(RIDGE)[0], "B_RIDGE_CI": bq(RIDGE)[1], "B_M2": bq(LR)[0], "B_M2_CI": bq(LR)[1],
    "R_AUC55": f"{r55.AUC:.3f}", "R_P55": f"{r55.p_two_sided:.3f}", "R_AUC35": f"{r35.AUC:.3f}", "R_P35": f"{r35.p_two_sided:.3f}",
    "P4A_U": f"{pol.loc['4A: fixed Spider thresholds', 'utility_3to1']:+.3f}", "P4A_PURSUE": f"{pol.loc['4A: fixed Spider thresholds', 'pursue']:.1f}",
    "P4B_U": f"{pol.loc['4B: F1-tuned threshold', 'utility_3to1']:+.3f}", "P4C_U": f"{pol.loc['4C: cost-based threshold (3:1)', 'utility_3to1']:+.3f}",
    "ROBUSTNESS_TABLE": rob_table, "GROUPING_TABLE": grouping_table, "GC_SPLIT": str(gc_split), "GC_MAXDIFF": gc_maxdiff,
    "NUMBER_CHECK": number_check, "ABSTRACT_WORDS": str(len(abstract.split())),
    "RUNTIME_MIN": f"{man['runtime_seconds'] / 60:.0f}", "CLEAN_RERUN": clean, "PAGES": pages, "LATEX_STATUS": latex_status,
    "MARKERS": "\n".join(f"* {re.sub(r'\s+', ' ', x).strip()}" for x in markers) or "* None.",
    "PH_M2": f"{perm.loc[LR, 'p_holm_one_sided']:.2f}", "PH_RIDGE": f"{perm.loc[RIDGE, 'p_holm_one_sided']:.2f}",
    "PH_M3": f"{perm.loc[SNFF, 'p_holm_one_sided']:.2f}", "NPERM": str(man["permutations"]),
    "PERM_REPEATS": WORDS.get(man["permutation_repeats"], str(man["permutation_repeats"])),
    "BR_N": str(int(rfb.replicates.iloc[0])), "BR_RIDGE": rq(RIDGE)[0], "BR_RIDGE_CI": rq(RIDGE)[1], "BR_RIDGE_SHARE": rq(RIDGE)[2],
    "BR_M2": rq(LR)[0], "BR_M2_CI": rq(LR)[1], "BR_M2_SHARE": rq(LR)[2],
    "PUB_M2": f"{pub.loc[LR, 'AUC_mean']:.3f}", "PUB_RIDGE": f"{pub.loc[RIDGE, 'AUC_mean']:.3f}", "PUB_M3": f"{pub.loc[SNFF, 'AUC_mean']:.3f}",
    "PUB_SCORE": f"{pub.loc[SCORE, 'AUC_mean']:.3f}",
    "RV_BANK55": f"{rvb55.AUC_R:.3f}", "RV_BANK55_P": f"{rvb55.p_AUC:.2f}", "RV_BANK35": f"{rvb35.AUC_R:.3f}",
    "FB_SPY_ALL": fb("Reaction-day CAR[-1,+1], SPY (primary)", "all 55 transactions"),
    "FB_SPY_DROP": fb("Reaction-day CAR[-1,+1], SPY (primary)", "without the FBOP cluster"),
    "FB_BANK_ALL": fb(VB, "all 55 transactions"), "FB_BANK_DROP": fb(VB, "without the FBOP cluster"),
    "VALUE_WORDS": value_words, "N_REFS": str(len(re.findall(r"\\bibitem\{", tex))),
    "RELEASE_FILES": str(release_files), "RELEASE_SHA": release_sha, "BANK_RERUN": bank_rerun,
}
for name in ("AUDIT_REPORT", "SUBMISSION_CHECKLIST"):
    t = (TPL / f"{name}_TEMPLATE.md").read_text()
    for k, v in vals.items():
        t = t.replace("{{" + k + "}}", v)
    left = re.findall(r"\{\{[A-Z0-9_]+\}\}", t)
    assert not left, left
    (OUT / f"{name}.md").write_text(t)
print("reports written; markers:", len(markers), "; abstract words:", vals["ABSTRACT_WORDS"], ";", number_check)
