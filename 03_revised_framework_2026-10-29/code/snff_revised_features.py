"""Revised Spider Network features (Option B, measured inputs only).

Every quantity estimated from data (normalization bounds, winsorization cap,
flag and rule thresholds, score rescaling) is fitted on the training rows and
applied unchanged to the rows being scored, as in the July 2026 code.

Raw inputs (columns of SNFF_Revised_Inputs_*.csv). P is the failed bank's latest
call report whose 30-day filing deadline fell before the failure (public before
the announcement); the buyer's report is the last quarter-end >= 90 days before.
  N_npl_pct             failed-bank NPL ratio at P (%)
  G_deposits_usd_bn     failed-bank deposits at P (USD bn)
  C_buyer_capital_pct   acquiring bank equity / assets, last report >= 90 days before failure (%)
  E_relative_size       failed-bank assets at P / acquiring-bank assets (buyer report as for C)
  L_deposit_change_pct  failed-bank deposit change over the two quarters ending at P (%)
  T_npl_change_pp       failed-bank NPL ratio change over the same two quarters (pp)
  F_loss_share          FDIC loss-share agreement (0/1), from the FDIC release
  H column              extraordinary government support (0/1); narrow or broad definition
(The Step 2 values from Stage 1's Q-1 are in the same files with suffix _q1.)

Components (weights unchanged from the paper)
  V = G_n                       deposit franchise (purchase discount and asset quality removed)
  P = 0.60 F + 0.40 H           protection
  R = 0.40 N_n + 0.25 L + 0.35 T  risk; L = deposit outflow in the training fold's
                                  bottom quartile, T = NPL rise in its top quartile
  B = C_n                       buyer capital (pre-failure)
  E = E_n                       relative size, winsorized at the training q95
  S = 0.30 V + 0.20 P + 0.20 B - 0.20 R - 0.10 E

Rules (thresholds are training-fold quantiles of the normalized inputs)
  Q  protected credit risk     N_n >= N75 and F = 1                 +0.08
     (the July rule D >= D75 and F = 1 and A >= 0.5 is the same rule:
      D = 0.6 x NPL and A = 1 - NPL, so A >= 0.5 only drops NPL > 50%)
  U  recoverable distress      L = 1 and T = 0 [and H = 1]          +0.07
     (H is 1 for one or two of the 55 transactions, so the default drops it;
      u_requires_h=True restores the July form)
  Z  structural-risk penalty   T = 1 and C_n < C25                  -0.10
  K  size-burden penalty       E_n > E75 and C_n < C25              -0.06
     (replaces integration strain, M > M75 and C < C25)
  S* = S + 0.08 Q + 0.07 U - 0.10 Z - 0.06 K, rescaled to [0, 1] on the training fold.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

RAW_CONTINUOUS = ["N_npl_pct", "G_deposits_usd_bn", "C_buyer_capital_pct", "E_relative_size",
                  "L_deposit_change_pct", "T_npl_change_pp"]
RAW_BINARY = ["F_loss_share"]          # plus the chosen H column
SPIDER_COLS = ["S_final", "Q_rule", "U_rule", "Z_rule", "K_rule"]
W_COMPONENT = dict(V=0.30, P=0.20, B=0.20, R=0.20, E=0.10)
W_RULE = dict(Q=0.08, U=0.07, Z=-0.10, K=-0.06)


@dataclass
class RevisedSpider:
    h_col: str = "H_support_narrow"
    u_requires_h: bool = False
    clip: bool = True
    params: dict = field(default_factory=dict)

    def _minmax(self, x: pd.Series, name: str) -> pd.Series:
        lo, hi = self.params[f"{name}_min"], self.params[f"{name}_max"]
        z = (x - lo) / (hi - lo + 1e-12)
        return z.clip(0, 1) if self.clip else z

    def _base(self, df: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        out = pd.DataFrame(index=df.index)
        out["G_n"] = self._minmax(df.G_deposits_usd_bn, "G")
        out["N_n"] = self._minmax(df.N_npl_pct, "N")
        out["C_n"] = self._minmax(df.C_buyer_capital_pct, "C")
        out["E_n"] = self._minmax(df.E_relative_size.clip(upper=p["E_cap"]), "E")
        out["L_flag"] = (df.L_deposit_change_pct <= p["L_q25"]).astype(int)
        out["T_flag"] = (df.T_npl_change_pp >= p["T_q75"]).astype(int)
        F, H = df.F_loss_share.astype(float), df[self.h_col].astype(float)
        out["V_score"] = out.G_n
        out["P_score"] = 0.60 * F + 0.40 * H
        out["R_score"] = 0.40 * out.N_n + 0.25 * out.L_flag + 0.35 * out.T_flag
        out["B_score"] = out.C_n
        out["E_score"] = out.E_n
        out["S_raw"] = (W_COMPONENT["V"] * out.V_score + W_COMPONENT["P"] * out.P_score
                        + W_COMPONENT["B"] * out.B_score - W_COMPONENT["R"] * out.R_score
                        - W_COMPONENT["E"] * out.E_score)
        return out

    def _rules(self, out: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        F, H = df.F_loss_share.astype(float), df[self.h_col].astype(float)
        out["Q_rule"] = ((out.N_n >= p["N75"]) & (F == 1)).astype(int)
        u = (out.L_flag == 1) & (out.T_flag == 0)
        out["U_rule"] = (u & (H == 1) if self.u_requires_h else u).astype(int)
        out["Z_rule"] = ((out.T_flag == 1) & (out.C_n < p["C25"])).astype(int)
        out["K_rule"] = ((out.E_n > p["E75"]) & (out.C_n < p["C25"])).astype(int)
        out["S_adj"] = (out.S_raw + W_RULE["Q"] * out.Q_rule + W_RULE["U"] * out.U_rule
                        + W_RULE["Z"] * out.Z_rule + W_RULE["K"] * out.K_rule)
        return out

    def fit(self, train: pd.DataFrame) -> "RevisedSpider":
        if train.F_loss_share.isna().any() or train[self.h_col].isna().any():
            raise ValueError("F_loss_share and the H column must be coded for every training row")
        p = {}
        p["E_cap"] = train.E_relative_size.quantile(0.95)
        for name, col in [("G", train.G_deposits_usd_bn), ("N", train.N_npl_pct),
                          ("C", train.C_buyer_capital_pct), ("E", train.E_relative_size.clip(upper=p["E_cap"]))]:
            p[f"{name}_min"], p[f"{name}_max"] = col.min(), col.max()
        p["L_q25"] = train.L_deposit_change_pct.quantile(0.25)
        p["T_q75"] = train.T_npl_change_pp.quantile(0.75)
        self.params = p
        base = self._base(train)
        p["N75"], p["C25"], p["E75"] = base.N_n.quantile(0.75), base.C_n.quantile(0.25), base.E_n.quantile(0.75)
        tr = self._rules(base, train)
        p["S_min"], p["S_max"] = tr.S_adj.min(), tr.S_adj.max()
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        out = self._rules(self._base(df), df)
        z = (out.S_adj - self.params["S_min"]) / (self.params["S_max"] - self.params["S_min"] + 1e-12)
        out["S_final"] = z.clip(0, 1) if self.clip else z
        return out


def raw_inputs(df: pd.DataFrame, h_col: str = "H_support_narrow") -> pd.DataFrame:
    """The measured predictors for the baseline models (Model 2 and the comparators)."""
    return df[RAW_CONTINUOUS + RAW_BINARY + [h_col]].astype(float)
