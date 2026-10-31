"""Public acquirer name → ticker mapping for FDIC P&A acquirers.

REVISION 2026-10 (data audit). Changes relative to the June 2026 version:
  1. Name rules now match whole words only. The old substring test mapped
     "CERTUS BANK" and "SYNOVUS BANK" to U.S. Bancorp (both contain "US BANK")
     and "FIRST CALIFORNIA BANK" to Zions (contains "CALIFORNIA BANK").
  2. Rules keyed on the acquirer's FDIC certificate number run before the name
     rules. This separates First-Citizens Bank & Trust (NC, cert 11063, FCNCA)
     from First Citizens Bank and Trust Company, Inc. (SC, cert 15504, OTC: FCBN)
     and First Citizens Bank of Luverne, AL (cert 23152, private).
  3. Wrong tickers fixed: Flagstar Bank N.A. in 2023 belonged to New York
     Community Bancorp (NYCB, now FLG), not Truist (TFC); Union Bank N.A.
     belonged to Mitsubishi UFJ (MUFG), not Union Bankshares VT (UNB);
     Sabadell United Bank belonged to Banco Sabadell (Madrid: SAB.MC), not
     Banco Santander (SAN).
  4. Every mapping now carries a `parent_listing` label: US (US exchange),
     FOREIGN (parent is a foreign bank, even if its shares or ADRs trade in the
     US), OTC (over-the-counter), or PRIVATE. The dataset builder can then
     exclude foreign and OTC parents.
  5. (2026-10-28) The listing is taken as of the event date where it changed over
     time: Charter Financial (CHFN) was OTC until it moved to Nasdaq on 2010-09-29,
     so its March 2010 acquisition counts as OTC (finding of the 2026-10-28
     reconstruction audit, checked against the company's 8-K).
  6. (2026-10-28, second review) Mappings proposed for acquirers that were coded
     private in June 2026 wait for the authors' sign-off and are NOT applied by
     default: override rows whose status_note starts with "VERIFY:" and the name
     rules in PENDING_NAME_RULES (Northbrook Bank & Trust -> Wintrust). Such rows
     get match method PENDING_VERIFICATION and stay out of the panel. To approve
     one row, change its status_note prefix from "VERIFY:" to "VERIFIED:"; to
     apply all of them (e.g. for a sensitivity run), set
     APPLY_PENDING_TICKER_MAPPINGS = True.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

EVENT_OVERRIDES_CSV = "event_ticker_overrides.csv"

US, FOREIGN, OTC, PRIVATE = "US", "FOREIGN", "OTC", "PRIVATE"

# Parents listed outside the US (or only through ADRs). A three-day CAR of the
# parent around a small US bank deal is mostly noise, and SPY is the wrong
# benchmark for these stocks.
FOREIGN_TICKERS = {"TD", "BNS", "BBVA", "MUFG", "BMO", "RY", "SAB.MC", "NAB.AX"}
OTC_TICKERS = {"FCBN", "SBNC"}

# Listing venue that changed over time: ticker -> [(first date, listing), ...] in date order.
# Charter Financial was quoted on the OTC Bulletin Board (CHFN.OB) until it began trading
# on Nasdaq on 2010-09-29 (8-K exhibit 99.1, 2010-09-23).
LISTING_HISTORY: dict[str, list[tuple[str, str]]] = {
    "CHFN": [("1900-01-01", "OTC"), ("2010-09-29", "US")],
}

# (FDIC certificate of the acquiring bank, ticker or None if private).
# Checked before the name rules.
CERT_RULES: dict[str, str | None] = {
    "11063": "FCNCA",  # First-Citizens Bank & Trust Company, Raleigh NC
    "15504": "FCBN",   # First Citizens Bank and Trust Company, Inc., Columbia SC (OTC)
    "23152": None,     # First Citizens Bank, Luverne AL (private)
    "59028": None,     # CertusBank, N.A. (private; Certus Holdings)
    "873": "SNV",      # Synovus Bank
    "22819": "FCAL",   # First California Bank (First California Financial Group)
    "22826": "MUFG",   # Union Bank, N.A. (UnionBanCal, wholly owned by MUFG from Nov 2008)
    "32541": "FBC",    # Flagstar Bank; FBC -> NYCB from 2022-12-01 via DATE_OVERRIDES
}

# (pattern matched as whole words in the normalized acquirer name, ticker or
# None if private). Order matters: first match wins.
TICKER_RULES: list[tuple[str, str | None]] = [
    ("JPMORGAN CHASE", "JPM"),
    ("REGIONS BANK", "RF"),
    ("BRANCH BANKING AND TRUST", "BBT"),
    ("BB&T", "BBT"),
    ("BB AND T", "BBT"),
    ("CERTUS", None),
    ("SYNOVUS", "SNV"),
    ("U.S. BANK", "USB"),
    ("US BANK", "USB"),
    ("TD BANK", "TD"),
    ("HUNTINGTON", "HBAN"),
    ("MANUFACTURERS AND TRADERS", "MTB"),
    ("FLAGSTAR", "FBC"),
    ("FIRST TENNESSEE", "FHN"),
    ("IBERIABANK", "IBKC"),
    ("UMPQUA", "UMPQ"),
    ("EAST WEST", "EWBC"),
    ("VALLEY NATIONAL", "VLY"),
    ("NEW YORK COMMUNITY", "NYCB"),
    ("ONEWEST", None),
    ("GREAT WESTERN", "GWBI"),
    ("PROSPERITY", "PB"),
    ("RENASANT", "RNST"),
    ("SIMMONS FIRST", "SFNC"),
    ("CITIZENS BUSINESS", "CVBF"),
    ("EVERBANK", "EVER"),
    ("WHITNEY BANK", "WHIT"),
    ("WASHINGTON FEDERAL", "WAFD"),
    ("WESTAMERICA", "WABC"),
    ("FIRST MIDWEST", "FMBI"),
    ("MB FINANCIAL", "MBFI"),
    ("OLD NATIONAL", "ONB"),
    ("COLUMBIA STATE", "COLB"),
    # SC bank first: "FIRST-CITIZENS" normalizes to "FIRST CITIZENS" and would catch it.
    # Name-only fallback; the certificate rules above are the reliable test.
    ("FIRST CITIZENS BANK AND TRUST COMPANY INC", "FCBN"),
    ("FIRST-CITIZENS", "FCNCA"),
    ("FIRST CITIZENS", "FCNCA"),
    ("GREAT SOUTHERN", "GSBC"),
    ("FULTON BANK", "FULT"),
    ("ORIENTAL BANK", "OFG"),
    ("BANCO POPULAR", "BPOP"),
    ("SCOTIABANK", "BNS"),
    ("COMPASS BANK", "BBVA"),
    ("HANCOCK BANK", "HBHC"),
    ("HANCOCK WHITNEY", "HWC"),
    ("AMERIS BANK", "ABCB"),
    ("CENTERSTATE", "CSFL"),
    ("TALMER BANK", "TLMR"),
    ("FIRSTMERIT", "FMER"),
    ("HEARTLAND BANK AND TRUST", "HTLF"),
    ("ENTERPRISE BANK", "EFSC"),
    ("FIRST CALIFORNIA BANK", "FCAL"),
    ("CALIFORNIA BANK AND TRUST", "ZION"),
    ("CITY NATIONAL", "CYN"),
    ("UNION BANK NATIONAL ASSOCIATION", "MUFG"),
    ("WHEATON BANK", "WTFC"),
    ("PRIVATEBANK", "PVTB"),
    ("SABADELL UNITED", "SAB.MC"),
    ("HARRIS NATIONAL ASSOCIATION", "BMO"),
    ("PLAINSCAPITAL", "HTH"),
    ("RABOBANK", None),
    ("ARVEST", None),
    ("MUTUAL OF OMAHA", None),
    ("COMMUNITY & SOUTHERN", None),
    ("COMMUNITY AND SOUTHERN", None),
    ("ALOSTAR", None),
    ("BEAL BANK", None),
]

# Mappings proposed in the October 2026 audit for acquirers that were coded
# private in June 2026. They are applied only after the authors' sign-off (see
# note 6 in the module docstring); until then the rows are quarantined.
APPLY_PENDING_TICKER_MAPPINGS = False
PENDING_NAME_RULES: list[tuple[str, str]] = [
    # Northbrook Bank & Trust is a Wintrust subsidiary (2011 SEC exhibit cited for
    # PA-0165 in event_ticker_overrides.csv); same sign-off as PA-0165.
    ("NORTHBROOK BANK", "WTFC"),
]
PENDING_PREFIX = "VERIFY:"

# failure_date >= cutoff uses new_ticker (post-merger symbol for later events only)
DATE_OVERRIDES: list[tuple[str, str, str | None]] = [
    ("BBT", "2019-12-09", "TFC"),
    ("FBC", "2022-12-01", "NYCB"),  # Flagstar Bancorp merged into NYCB on 2022-12-01 (was TFC: wrong)
    ("NYCB", "2024-10-25", "FLG"),  # NYCB renamed Flagstar Financial (FLG)
    ("IBKC", "2020-07-01", "FHN"),
    ("WHIT", "2011-06-01", "HBHC"),
    ("HBHC", "2018-06-01", "HWC"),
    ("FMER", "2016-08-15", "HBAN"),
    ("GWBI", "2019-02-01", "PFBI"),
    ("MBFI", "2018-05-01", "MTB"),
    ("CSFL", "2020-07-01", "SBCF"),
    ("TLMR", "2016-09-01", "TCF"),
    ("CYN", "2015-11-01", "RY"),
]

# failure_date < cutoff means the acquirer had no listed parent yet.
PRIVATE_BEFORE: dict[str, tuple[str, str | None]] = {
    # ticker: (first trading date, ticker of the earlier listed parent or None)
    "TLMR": ("2014-02-01", None),        # Talmer Bancorp IPO
    "EVER": ("2012-05-03", None),        # EverBank Financial IPO (not 2010)
    "GWBI": ("2014-10-15", "NAB.AX"),    # Great Western Bancorp spun off from National Australia Bank
}

# Yahoo keeps the history of renamed tickers under the new symbol.
YAHOO_FALLBACKS: dict[str, list[str]] = {
    "NYCB": ["FLG"],
    "SCBT": ["SSB"],
}


def normalize_name(name: str) -> str:
    text = str(name).upper().strip()
    text = text.replace("&", " AND ")
    text = re.sub(r"[^A-Z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def name_matches(pattern: str, norm: str) -> bool:
    """Whole-word match of a normalized pattern inside a normalized name."""
    return re.search(rf"\b{re.escape(normalize_name(pattern))}\b", norm) is not None


def parent_listing(ticker: str | None, as_of=None) -> str:
    """Listing of the parent on the event date (as_of); static lists otherwise."""
    if ticker is None:
        return PRIVATE
    if ticker in LISTING_HISTORY and as_of is not None:
        d = pd.to_datetime(as_of)
        venue = None
        for start, listing in LISTING_HISTORY[ticker]:
            if d >= pd.Timestamp(start):
                venue = listing
        if venue is not None:
            return venue
    if ticker in FOREIGN_TICKERS:
        return FOREIGN
    if ticker in OTC_TICKERS:
        return OTC
    return US


def apply_date_override(ticker: str | None, failure_date: pd.Timestamp) -> str | None:
    if ticker is None:
        return None
    fd = pd.to_datetime(failure_date)
    if ticker in PRIVATE_BEFORE:
        cutoff, earlier = PRIVATE_BEFORE[ticker]
        if fd < pd.Timestamp(cutoff):
            return earlier
    for base, cutoff, new_ticker in DATE_OVERRIDES:
        if ticker == base and fd >= pd.Timestamp(cutoff):
            ticker = new_ticker  # chained: FBC -> NYCB -> FLG
            if ticker is None:
                return None
    return ticker


def candidates_for(final: str, fd: pd.Timestamp) -> list[str]:
    fallbacks = [final]
    if final == "HBHC" and fd >= pd.Timestamp("2011-06-01"):
        fallbacks.append("HWC")
    if final == "WHIT":
        fallbacks.extend(["HBHC", "HWC"])
    fallbacks.extend(YAHOO_FALLBACKS.get(final, []))
    return list(dict.fromkeys(fallbacks))


def load_event_overrides() -> pd.DataFrame:
    path = Path(EVENT_OVERRIDES_CSV)
    if not path.exists():
        return pd.DataFrame(
            columns=["transaction_id", "ticker_candidates", "status_note", "reclassify_private"]
        )
    df = pd.read_csv(path)
    df["reclassify_private"] = df["reclassify_private"].fillna(False).astype(bool)
    return df


def _clean_cert(cert) -> str | None:
    if cert is None or (isinstance(cert, float) and pd.isna(cert)):
        return None
    text = str(cert).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text or None


def resolve_ticker(
    acquirer_name: str,
    failure_date: pd.Timestamp | str,
    transaction_id: str | None = None,
    acquirer_cert: str | int | None = None,
) -> tuple[str | None, str, list[str]]:
    """Return (primary_ticker, match_method, ticker_candidates_for_price_pull)."""
    fd = pd.to_datetime(failure_date)
    norm = normalize_name(acquirer_name)

    overrides = load_event_overrides()
    if transaction_id and not overrides.empty:
        row = overrides[overrides["transaction_id"] == transaction_id]
        if not row.empty:
            r = row.iloc[0]
            note = str(r.get("status_note", "") or "")
            if note.strip().upper().startswith(PENDING_PREFIX) and not APPLY_PENDING_TICKER_MAPPINGS:
                return None, f"PENDING_VERIFICATION:{transaction_id}", []
            if r["reclassify_private"]:
                return None, f"OVERRIDE_PRIVATE:{r['status_note']}", []
            candidates = [c for c in str(r.get("ticker_candidates", "") or "").split("|") if c and c != "nan"]
            if candidates:
                primary = apply_date_override(candidates[0], fd)
                if primary is None:
                    return None, f"OVERRIDE_PRIVATE:{r['status_note']}", []
                # price pull starts with the date-adjusted symbol, then the listed ones,
                # then any symbol Yahoo moved the history to
                ordered = [primary] + candidates
                for c in list(ordered):
                    ordered.extend(YAHOO_FALLBACKS.get(c, []))
                return primary, f"OVERRIDE:{transaction_id}", list(dict.fromkeys(ordered))

    cert = _clean_cert(acquirer_cert)
    if cert is not None and cert in CERT_RULES:
        final = apply_date_override(CERT_RULES[cert], fd)
        if final:
            return final, f"CERT:{cert}", candidates_for(final, fd)
        return None, f"PRIVATE_CERT:{cert}", []

    for pattern, ticker in PENDING_NAME_RULES:
        if name_matches(pattern, norm):
            if not APPLY_PENDING_TICKER_MAPPINGS:
                return None, f"PENDING_VERIFICATION:{pattern}", []
            final = apply_date_override(ticker, fd)
            if final:
                return final, f"MATCH:{pattern}", candidates_for(final, fd)
            return None, f"PRIVATE:{pattern}", []

    for pattern, ticker in TICKER_RULES:
        if name_matches(pattern, norm):
            final = apply_date_override(ticker, fd)
            if final:
                return final, f"MATCH:{pattern}", candidates_for(final, fd)
            return None, f"PRIVATE:{pattern}", []

    return None, "UNMAPPED_PRIVATE", []


def build_ticker_map(
    acquirer_names: pd.Series,
    failure_dates: pd.Series,
    transaction_ids: pd.Series | None = None,
    acquirer_certs: pd.Series | None = None,
) -> pd.DataFrame:
    rows = []
    n = len(acquirer_names)
    tx_ids = transaction_ids if transaction_ids is not None else [None] * n
    certs = acquirer_certs if acquirer_certs is not None else [None] * n
    for name, fdate, tx, cert in zip(acquirer_names, failure_dates, tx_ids, certs):
        ticker, method, candidates = resolve_ticker(name, fdate, tx, cert)
        rows.append(
            {
                "transaction_id": tx,
                "acquirer_name": name,
                "failure_date": fdate,
                "ticker": ticker,
                "ticker_candidates": "|".join(candidates) if candidates else None,
                "ticker_match_method": method,
                "is_public_acquirer": ticker is not None,
                "parent_listing": parent_listing(ticker, fdate),
            }
        )
    return pd.DataFrame(rows)
