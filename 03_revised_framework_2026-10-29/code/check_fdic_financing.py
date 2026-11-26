"""Cross-check the FDIC-financing coding against the transaction documents.

FDIC_Financing_Check_90.csv records, for each of the 90 transactions, the document that states the
winning bid (the FDIC bid summary where one exists; otherwise the purchase and assumption agreement,
the acquirer's SEC filing or the FDIC press release), the winning bid as stated, and whether it
includes FDIC financing of the buyer (a purchase money note or financing note issued by the buyer
to the FDIC). A value or equity appreciation instrument paid to the FDIC is recorded separately and
is not financing of the buyer.

The script checks that
  * the file covers the 90 transactions of Source_Verification_Ledger_90.csv once each,
  * every row names a source type and an https source,
  * the financing recorded from the documents equals the ledger's fdic_buyer_financing,
  * the ledger's broad support indicator equals bridge bank or systemic-risk exception or FDIC
    financing of the buyer, and
  * H_support_broad in both model-input files equals the ledger's broad indicator.

usage: python3 -I check_fdic_financing.py <package_root> [<report_txt>]
Exit status 1 if any check fails.
"""
import sys
from pathlib import Path

import pandas as pd

root = Path(sys.argv[1])
data = root / "03_revised_framework_2026-10-29" / "data"
report = Path(sys.argv[2]) if len(sys.argv) > 2 else None

L = pd.read_csv(data / "Source_Verification_Ledger_90.csv", dtype=str).set_index("transaction_id")
C = pd.read_csv(data / "FDIC_Financing_Check_90.csv", dtype=str, keep_default_na=False)
SOURCES = {"FDIC bid summary", "P&A agreement", "acquirer SEC filing", "FDIC press release"}
fails, lines = [], []


def check(name, ok, detail=""):
    lines.append(f"{'PASS' if ok else 'FAIL'}  {name}" + (f": {detail}" if detail else ""))
    if not ok:
        fails.append(name)


check("90 rows, one per transaction", len(C) == 90 and C.transaction_id.is_unique, f"{len(C)} rows")
check("same transactions as the ledger", set(C.transaction_id) == set(L.index))
check("source type recorded", C.evidence_source.isin(SOURCES).all(),
      ", ".join(C.loc[~C.evidence_source.isin(SOURCES), "transaction_id"]))
check("https source for every row", C.evidence_url.str.startswith("https://").all())
check("financing recorded as 0/1", C.buyer_financing_in_winning_bid.isin(["0", "1"]).all())
check("appreciation instrument recorded as 0/1/blank", C.appreciation_instrument_to_fdic.isin(["0", "1", ""]).all())

C = C.set_index("transaction_id")
mism = [t for t in C.index if C.at[t, "buyer_financing_in_winning_bid"] != L.at[t, "fdic_buyer_financing"]]
check("documents agree with the ledger's fdic_buyer_financing", not mism, ", ".join(mism))

narrow = (L.bridge_bank == "1") | (L.systemic_risk_exception == "1")
broad = narrow | (L.fdic_buyer_financing == "1")
check("ledger broad indicator = bridge bank or SRE or FDIC financing",
      (broad.astype(int).astype(str) == L.H_broad_any_extraordinary_support).all())
for f in ("SNFF_Revised_Inputs_Primary55.csv", "SNFF_Revised_Inputs_Broader90.csv"):
    d = pd.read_csv(data / f, dtype={"transaction_id": str}).set_index("transaction_id")
    bad = [t for t in d.index if int(d.at[t, "H_support_broad"]) != int(L.at[t, "H_broad_any_extraordinary_support"])]
    check(f"H_support_broad in {f} = ledger broad indicator", not bad, ", ".join(bad))

fin = C.index[C.buyer_financing_in_winning_bid == "1"]
vai = C.index[C.appreciation_instrument_to_fdic == "1"]
prim = C.in_primary_panel == "1"
lines += ["",
          "transactions by source of the winning bid (primary 55 / broader 35):"]
for s in ["FDIC bid summary", "P&A agreement", "acquirer SEC filing", "FDIC press release"]:
    lines.append(f"  {s:22s} {int(((C.evidence_source == s) & prim).sum()):3d} / {int(((C.evidence_source == s) & ~prim).sum()):3d}")
lines += [f"FDIC financing of the buyer ({len(fin)}): " + "; ".join(f"{t} {L.at[t, 'failed_bank_name']}" for t in fin),
          f"appreciation instrument paid to the FDIC, not financing ({len(vai)}): "
          + "; ".join(f"{t} {L.at[t, 'failed_bank_name']}" for t in vai),
          "", f"{len(fails)} check(s) failed" if fails else "all checks passed"]
text = "\n".join(lines) + "\n"
print(text, end="")
if report:
    report.write_text(text)
sys.exit(1 if fails else 0)
