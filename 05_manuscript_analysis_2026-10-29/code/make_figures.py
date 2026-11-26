"""Draw the calibration figure of the revised manuscript for the two co-primary benchmarks (release 4.5).

Reads the quintile bins that final_analysis.py writes for the S&P 500 benchmark (table_calibration_bins.csv; the
same bins as figure_calibration.png) and for the bank-sector benchmark (table_bank_calibration_bins.csv) and draws
them in two panels with the styling of figure_calibration.png.

usage: python3 -I make_figures.py <results_dir> <out_dir>
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

R, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
LR, RIDGE, SNFF = "Logistic regression (L2, C=1)", "Ridge logistic", "SNFF + LR (Model 3)"
LABEL = {LR: "Logistic regression (Model 2)", RIDGE: "Ridge logistic", SNFF: "SNFF + LR (Model 3)"}
LO, HI = 0.2, 1.0
fig, axes = plt.subplots(2, 1, figsize=(6.2, 8.6))
for ax, (fname, title, legend_at) in zip(axes, (("table_calibration_bins.csv", "A. S&P 500 benchmark", "upper left"),
                                                ("table_bank_calibration_bins.csv", "B. Bank-sector benchmark", "lower right"))):
    cb = pd.read_csv(R / fname)
    # Compare ordinary Python lists, not a Series against a nested list:
    # pandas versions differ in how they broadcast the latter comparison.
    assert set(cb.model) == {LR, RIDGE, SNFF} and all(
        sorted(group["bin"].tolist()) == [1, 2, 3, 4, 5]
        for _, group in cb.groupby("model")
    )
    assert cb.mean_prediction.between(LO, HI, inclusive="neither").all() and cb.observed_rate.between(LO, HI, inclusive="neither").all(), \
        f"calibration point outside the plotted range in {fname}"
    ax.plot([0, 1], [0, 1], "--", color="#888888", lw=1, label="Perfect calibration")
    for nm, mk in ((LR, "o"), (RIDGE, "s"), (SNFF, "^")):
        t = cb[cb.model == nm].sort_values("bin")
        ax.plot(t.mean_prediction, t.observed_rate, marker=mk, lw=1.4, label=LABEL[nm])
    ax.set_xlim(LO, HI)
    ax.set_ylim(LO, HI)
    ax.set_title(title, fontsize=10, loc="left")
    ax.set_xlabel("Mean predicted probability (quintile bins)")
    ax.set_ylabel("Observed share with positive CAR")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, loc=legend_at)  # panel B: the lower right is empty (no bin there; checked by eye)
fig.tight_layout()
fig.savefig(OUT / "figure_calibration_coprimary.png", dpi=300)
plt.close(fig)
print("figure written:", OUT / "figure_calibration_coprimary.png")
