"""Build CAR outcomes for all field-pass rows and ship the public modeling file.

REVISION 2026-10 (data audit). Changes relative to the June 2026 version:
  * CAR rows are built by build_car_outcomes.car_row, so the event-date
    overrides (bridge-bank sales announced after the failure date) and the
    certificate-based ticker rules apply here too.
  * Acquirers whose listed parent trades abroad (FOREIGN) or over the counter
    (OTC) are excluded from the modeling file by default; set the two flags
    below to False to keep them. Excluded rows stay in OUTPUT_ALL with their
    CARs, and the build log counts them.
  * The export keeps ticker_match_method, parent_listing and event_date_source
    so every outcome can be traced to its mapping rule and event date.
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from acquirer_ticker_map import build_ticker_map
from build_car_outcomes import (
    MARKET_END,
    MARKET_START,
    car_row,
    load_event_date_overrides,
    load_price_cache,
    save_price_cache,
)
from historical_prices import download_prices

INPUT_FINANCIALS = "Stage1_Master_Acquirer_Financials_Completed.csv"
INPUT_LOG = "Stage1_Inclusion_Exclusion_Log.csv"
OUTPUT_ALL = "Stage1_Master_Public_Outcomes_All.csv"
OUTPUT_CSV = "Stage1_Final_Public_Modeling_Dataset.csv"
OUTPUT_XLSX = "Stage1_Final_Public_Modeling_Dataset.xlsx"
OUTPUT_LOG = "Stage1_Public_Modeling_Build_Log.csv"
OUTPUT_MANIFEST = "Stage1_Public_Modeling_Manifest.txt"

TARGET_MIN = 80
TARGET_MAX = 150
MARKET_TICKER = "SPY"

# Recommended defaults (see the 2026-10 data audit). A three-day CAR of a
# foreign-listed parent around a small US deal is mostly noise and SPY is the
# wrong benchmark for it; OTC prices for these banks are thin and stale.
EXCLUDE_FOREIGN_PARENTS = True
EXCLUDE_OTC_PARENTS = True

# Stage 1 syllabus: 11 modeling variables + identity
MODELING_VARS = [
    "failed_assets_q_minus_1",
    "failed_deposits_q_minus_1",
    "failed_loans_q_minus_1",
    "failed_npl_ratio_q_minus_1",
    "failed_asset_quality_score",
    "acquirer_assets",
    "acquirer_deposits",
    "acquirer_equity",
    "acquirer_capital_ratio",
    "car_3day",
    "value_created_flag",
]

IDENTITY_COLS = [
    "transaction_id",
    "failure_date",
    "failed_bank_name",
    "failed_bank_state",
    "failed_bank_cert",
    "acquirer_name",
    "acquirer_cert",
    "ticker",
    "announcement_date",
]

TRACE_COLS = ["ticker_match_method", "parent_listing", "event_date_source", "event_trading_date",
              "announcement_timing", "first_reaction_date",
              "car_0p1", "value_created_flag_0p1", "car_reaction_m1p1", "value_created_flag_reaction"]

EXPORT_COLS = IDENTITY_COLS + MODELING_VARS + ["car_status", "inclusion_exclusion_reason"] + TRACE_COLS


def load_field_pass_universe() -> pd.DataFrame:
    fin = pd.read_csv(INPUT_FINANCIALS)
    log = pd.read_csv(INPUT_LOG)[
        ["transaction_id", "passes_required_fields", "inclusion_exclusion_reason"]
    ]
    df = fin.merge(log, on="transaction_id", how="left")
    df = df[df["passes_required_fields"] == True].copy()  # noqa: E712
    df["failure_date"] = pd.to_datetime(df["failure_date"])
    return df.sort_values(["failure_date", "transaction_id"]).reset_index(drop=True)


def build_car_for_universe(df: pd.DataFrame) -> pd.DataFrame:
    ticker_map = build_ticker_map(
        df["acquirer_name"],
        df["failure_date"],
        df["transaction_id"],
        df["acquirer_cert"] if "acquirer_cert" in df.columns else None,
    )
    merged = df.merge(
        ticker_map,
        on=["transaction_id", "acquirer_name", "failure_date"],
        how="left",
    )

    cache = load_price_cache()
    market, _ = download_prices([MARKET_TICKER], MARKET_START, MARKET_END)
    cache[MARKET_TICKER] = {d.strftime("%Y-%m-%d"): float(v) for d, v in market.items()}
    date_overrides = load_event_date_overrides()

    rows = []
    for _, row in merged.iterrows():
        rows.append(car_row(row, market, cache, date_overrides))
        time.sleep(0.05)

    save_price_cache(cache)
    return pd.DataFrame(rows)


def select_final_public_modeling(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    usable = df[df["car_status"] == "CAR_COMPUTED"].copy()
    for col in MODELING_VARS:
        usable[col] = pd.to_numeric(usable[col], errors="coerce")
    usable = usable.dropna(subset=MODELING_VARS)
    usable = usable[usable["ticker"].notna()]

    excluded = {}
    if "parent_listing" in usable.columns:
        for listing, flag in (("FOREIGN", EXCLUDE_FOREIGN_PARENTS), ("OTC", EXCLUDE_OTC_PARENTS)):
            mask = usable["parent_listing"] == listing
            excluded[listing] = int(mask.sum()) if flag else 0
            if flag:
                usable = usable[~mask]

    usable = usable.sort_values(
        ["failed_assets_q_minus_1", "failure_date", "transaction_id"],
        ascending=[False, True, True],
    )

    if len(usable) > TARGET_MAX:
        usable = usable.head(TARGET_MAX)

    if len(usable) < TARGET_MIN:
        raise RuntimeError(
            f"Only {len(usable)} public rows with all 11 variables; need {TARGET_MIN}+. "
            "Set FMP_API_KEY and re-run run_car_fmp_recovery.py for delisted tickers."
        )
    return usable.reset_index(drop=True), excluded


def main() -> None:
    universe = load_field_pass_universe()
    print(f"Building CAR for {len(universe)} field-pass transactions...")
    all_outcomes = build_car_for_universe(universe)
    all_outcomes.to_csv(OUTPUT_ALL, index=False)

    final, excluded = select_final_public_modeling(all_outcomes)
    export = final[[c for c in EXPORT_COLS if c in final.columns]]
    export.to_csv(OUTPUT_CSV, index=False)
    export.to_excel(OUTPUT_XLSX, index=False, sheet_name="Public_Modeling")

    included = final["inclusion_exclusion_reason"] == "INCLUDED"
    log = pd.DataFrame(
        [
            {"metric": "field_pass_universe", "value": len(universe)},
            {"metric": "public_acquirers_mapped", "value": int(all_outcomes["ticker"].notna().sum())},
            {"metric": "pending_ticker_verification", "value": int((all_outcomes["car_status"] == "PENDING_TICKER_VERIFICATION").sum())},
            {"metric": "car_computed_all", "value": int((all_outcomes["car_status"] == "CAR_COMPUTED").sum())},
            {"metric": "excluded_foreign_parent", "value": excluded.get("FOREIGN", 0)},
            {"metric": "excluded_otc_parent", "value": excluded.get("OTC", 0)},
            {"metric": "final_public_modeling_rows", "value": len(final)},
            {"metric": "final_rows_in_top150_sample", "value": int(included.sum())},
            {"metric": "target_band", "value": f"{TARGET_MIN}-{TARGET_MAX}"},
            {"metric": "value_created_flag_1", "value": int((final["value_created_flag"] == 1).sum())},
            {"metric": "value_created_flag_0", "value": int((final["value_created_flag"] == 0).sum())},
            {"metric": "top150_value_created_flag_1", "value": int((final.loc[included, "value_created_flag"] == 1).sum())},
            {"metric": "top150_value_created_flag_0", "value": int((final.loc[included, "value_created_flag"] == 0).sum())},
        ]
    )
    log.to_csv(OUTPUT_LOG, index=False)

    manifest = f"""Stage 1 Final Public Modeling Dataset (revision 2026-10)
Rows: {len(final)} (of which {int(included.sum())} in the 150-largest analytic sample)
Columns: {len(export.columns)} ({len(MODELING_VARS)} modeling variables)
Scope: Public acquirers with a US-listed parent; all 11 syllabus variables populated
Source universe: {len(universe)} transactions passing required-field rules (502 scoped P&A)
Selection: CAR_COMPUTED rows with complete financials; largest failed-bank assets first (cap {TARGET_MAX})
Excluded: foreign-listed parents {excluded.get('FOREIGN', 0)}, OTC parents {excluded.get('OTC', 0)}
Quarantined: {int((all_outcomes['car_status'] == 'PENDING_TICKER_VERIFICATION').sum())} rows whose proposed listed parent awaits the authors' sign-off (acquirer_ticker_map.py, note 6)
Event date: FDIC closing date, or the sale announcement date for bridge-bank resolutions (event_date_overrides.csv)
Files:
- {OUTPUT_CSV}
- {OUTPUT_XLSX}
- {OUTPUT_LOG}
"""
    Path(OUTPUT_MANIFEST).write_text(manifest, encoding="utf-8")

    pkg = Path("Stage1_Review_Package")
    pkg.mkdir(exist_ok=True)
    export.to_csv(pkg / OUTPUT_CSV, index=False)
    export.to_excel(pkg / OUTPUT_XLSX, index=False, sheet_name="Public_Modeling")
    log.to_csv(pkg / OUTPUT_LOG, index=False)
    (pkg / OUTPUT_MANIFEST).write_text(manifest, encoding="utf-8")

    print(manifest)
    print(log.to_string(index=False))


if __name__ == "__main__":
    main()
