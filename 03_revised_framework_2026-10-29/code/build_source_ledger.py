"""Source-verification ledger for the 90 listed-acquirer transactions (Step 3):
the 55 of the primary panel and the 35 more of the broader panel.

For each transaction the FDIC press release announcing the purchase and
assumption was read (FDIC press-release archive, archive.fdic.gov, or the FDIC's
GovDelivery bulletins, which carry a send time). Recorded: PR number and date,
the release's own timing language, any timestamp, the loss-share statement,
and any bridge bank, systemic-risk exception or FDIC financing of the buyer.
The evidence table below was transcribed on 2026-10-29; FDIC releases are U.S.
government works.

Event windows and CARs come from 02b_car_conventions_2026-10-29.

usage: python3 -I build_source_ledger.py <research_folder> <output_csv>
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pandas as pd

A = "https://archive.fdic.gov/view/fdic/"
G = "https://content.govdelivery.com/accounts/USFDIC/bulletins/"
EVIDENCE = f"""transaction_id|fdic_pr|release_date|release_url|timing_evidence|timestamp|timestamp_url|timing_class|loss_share|loss_share_evidence|bridge_bank|systemic_risk_exception|fdic_buyer_financing|notes
PA-0497|PR-85-2008|2008-09-25|{A}3396|"Thursday evening, Washington Mutual was closed"; business resumes "Friday morning"|||AFTER_CLOSE|0|no loss share in release|0|0|0|Thursday announcement; first session Friday 2008-09-26
PA-0004|PR-34-2023|2023-05-01|https://www.fdic.gov/news/press-releases/2023/pr23034.html|closed and sold before the Monday open|2023-05-01 03:33 EDT|{G}357fd15|PRE_OPEN|1|FDIC loss share on single-family residential and commercial loans (FDIC release; JPMorgan 8-K Ex. 99)|0|0|1|FDIC provided $50 bn of five-year fixed-rate financing (JPMorgan 8-K Ex. 99); timestamp is the FDIC board member's statement on the sale
PA-0006|PR-23-2023|2023-03-26|https://www.fdic.gov/news/press-releases/2023/pr23023.html|sale of Silicon Valley Bridge Bank announced on Sunday; First Citizens call 8:30 a.m. ET Monday (8-K)|||NON_TRADING_DAY|1|loss share on commercial loans (FDIC release); shared-loss agreement on approx. $60 bn of loans (First Citizens 8-K, 2023-03-27)|1|1|1|bank failed 2023-03-10 into a bridge bank; systemic-risk exception of 2023-03-12; buyer issued the FDIC a five-year $35 bn purchase money note at 3.50% and received a five-year $70 bn FDIC credit facility (First Citizens 8-K, 2023-03-27)
PA-0421|PR-143-2009|2009-08-14|{A}3715|"This evening and over the weekend"; hotline until 9 p.m. CDT|||AFTER_CLOSE|1|loss share on approx. $15 bn of assets|0|0|0|Bloomberg reported BB&T as buyer on Friday morning (posted 11:23 a.m.) and NYSE halted Colonial BancGroup before the open: same-day news falls on day -1 of the reaction-day window
PA-0490|PR-124-2008|2008-11-21|{A}3356|hotline "this evening until 9:00 p.m. pacific"|||AFTER_CLOSE|1|U.S. Bank takes the first $1.6 bn of losses on covered pools, FDIC shares further losses|0|0|0|joint release with PFF Bank & Trust
PA-0489|PR-124-2008|2008-11-21|{A}3356|hotline "this evening until 9:00 p.m. pacific"|||AFTER_CLOSE|1|as PA-0490 (joint release)|0|0|0|joint release with Downey
PA-0377|PR-201-2009|2009-11-06|{A}3647|"This evening and over the weekend"|||AFTER_CLOSE|1|loss share on approx. $7.7 bn of assets|0|0|0|
PA-0306|PR-97-2010|2010-04-30|{A}4066|"This evening and over the weekend"|||AFTER_CLOSE|1|loss share on $8.77 bn of assets|0|0|0|
PA-0387|PR-195-2009|2009-10-30|{A}3655|nine FBOP banks "closed this evening"|||AFTER_CLOSE|1|loss share on approx. $14.4 bn of $18.2 bn purchased (U.S. Bancorp: substantially all loans)|0|0|0|one release for nine banks
PA-0385|PR-195-2009|2009-10-30|{A}3655|nine FBOP banks "closed this evening"|||AFTER_CLOSE|1|as PA-0387|0|0|0|one release for nine banks
PA-0388|PR-195-2009|2009-10-30|{A}3655|nine FBOP banks "closed this evening"|||AFTER_CLOSE|1|as PA-0387|0|0|0|one release for nine banks
PA-0386|PR-195-2009|2009-10-30|{A}3655|nine FBOP banks "closed this evening"|||AFTER_CLOSE|1|as PA-0387|0|0|0|one release for nine banks
PA-0030|PR-24-2015|2015-02-27|{G}f45980|hotline "beginning this evening"|2015-02-27 16:31 EST|{G}f45980|AFTER_CLOSE|0|no loss share in release|0|0|0|
PA-0001|PR-30-2024|2024-04-26|{G}398f972|"This evening"; hotline until 9 p.m. ET|2024-04-26 18:17 EDT|{G}398f972|AFTER_CLOSE|0|no loss share in release|0|0|0|the WSJ reported the planned seizure first; the earliest dated report found (Reuters, citing the WSJ) is stamped 5:56 p.m. on 2024-04-26 (Investing.com), after the close; the WSJ's own time was not found
PA-0493|PR-113-2008|2008-11-07|{A}3367|hotline "this evening until 9 p.m. central"|||AFTER_CLOSE|0|none in release; P&A agreement (Prosperity 8-K, Ex. 2.1) has no loss-sharing section|0|0|0|
PA-0017|PR-34-2017|2017-04-28|{A}6473|hotline "this evening until 9 p.m., CT"|||AFTER_CLOSE|0|no loss share in release|0|0|0|
PA-0308|PR-95-2010|2010-04-30|{A}4070|"This evening and over the weekend"|||AFTER_CLOSE|1|loss share on $1.58 bn of assets|0|0|0|
PA-0203|PR-18-2011|2011-01-28|{A}4399|"This evening and over the weekend"|||AFTER_CLOSE|0|no loss share in release|0|0|0|
PA-0206|PR-13-2011|2011-01-21|{A}4404|"This evening and over the weekend"|||AFTER_CLOSE|1|loss share on $1.11 bn of assets|0|0|0|
PA-0347|PR-26-2010|2010-01-29|{A}4150|"This evening"; hotline until 9 p.m. PST|||AFTER_CLOSE|1|loss share on $2 bn of assets|0|0|0|
PA-0153|PR-128-2011|2011-07-29|{A}4289|"This evening and over the weekend"|||AFTER_CLOSE|1|loss share on $1.2 bn of assets|0|0|0|
PA-0363|PR-234-2009|2009-12-18|{A}3611|"This evening and over the weekend"|||AFTER_CLOSE|1|loss share on approx. $1.4 bn of assets|0|0|0|
PA-0480|PR-19-2009|2009-02-06|{A}3844|hotline "esta noche" (this evening; Spanish release PR-19-2009sp)|||AFTER_CLOSE|1|loss-share transaction (no amount stated)|0|0|0|
PA-0439|PR-125-2009|2009-07-17|{A}3733|hotline "this evening until 9:00 p.m., PDT"|||AFTER_CLOSE|1|loss share on approx. $1.5 bn of assets|0|0|0|
PA-0438|PR-126-2009|2009-07-17|{A}3732|hotline "this evening until 9:00 p.m."|||AFTER_CLOSE|1|loss share on approx. $1.3 bn of assets|0|0|0|
PA-0359|PR-4-2010|2010-01-08|{A}4175|"This evening and over the weekend"|||AFTER_CLOSE|1|loss share on approx. $1.0 bn of assets|0|0|0|
PA-0481|PR-18-2009|2009-02-06|{A}3845|hotline "this evening until 9:00 p.m., PST"|||AFTER_CLOSE|1|loss-share transaction (no amount stated)|0|0|0|
PA-0499|PR-74-2008|2008-08-29|{A}3408|hotline "today from 5 p.m. until 9 p.m., Eastern Time"|||AFTER_CLOSE|0|no loss share; premium of 1.012% and $34.4 m of assets purchased|0|0|0|first session Tuesday after Labor Day
PA-0016|PR-37-2017|2017-05-05|{A}6469|"This evening and over the weekend"|||AFTER_CLOSE|0|no loss share in release|0|0|0|
PA-0270|PR-164-2010|2010-07-23|{A}3997|"This evening and over the weekend"|||AFTER_CLOSE|1|loss share on $617.4 m of assets|0|0|0|
PA-0405|PR-170-2009|2009-09-11|{A}3684|"This evening and over the weekend"|||AFTER_CLOSE|1|loss share on approx. $715 m of assets|0|0|0|
PA-0352|PR-18-2010|2010-01-22|{A}4159|"This evening"|||AFTER_CLOSE|1|loss share on $697.4 m of assets|0|0|0|
PA-0165|PR-117-2011|2011-07-08|{A}4300|"This evening and over the weekend"|||AFTER_CLOSE|1|loss share on $699.8 m of assets|0|0|0|
PA-0108|PR-38-2012|2012-03-30|{A}4649|"This evening and over the weekend"|||AFTER_CLOSE|0|no loss share in release|0|0|0|
PA-0398|PR-185-2009|2009-10-16|{A}3667|"This evening and over the weekend"|||AFTER_CLOSE|1|loss share on approx. $683 m of assets|0|0|0|
PA-0470|PR-46-2009|2009-03-20|{A}3815|hotline "this evening until 9 p.m., CDT"|||AFTER_CLOSE|1|80/20 loss share on approx. $450 m of assets|0|0|0|
PA-0164|PR-118-2011|2011-07-08|{A}4299|"This evening and over the weekend"|||AFTER_CLOSE|1|loss share on $580.0 m of assets|0|0|0|
PA-0224|PR-249-2010|2010-11-12|{A}3911|hotline "this evening until 9:00 p.m. EST"|||AFTER_CLOSE|1|loss share on $560.2 m of the two failed banks' assets|0|0|0|joint release with Tifton Banking Company
PA-0487|PR-134-2008|2008-12-12|{A}3346|hotline "this evening until 9 p.m., EST"|||AFTER_CLOSE|0|no loss share in release|0|0|0|
PA-0151|PR-132-2011|2011-08-05|{A}4284|hotline "this evening until 9:00 p.m., PDT"|||AFTER_CLOSE|0|no loss share; $314.4 m of assets purchased|0|0|0|
PA-0229|PR-242-2010|2010-11-05|{A}3919|"This evening and over the weekend"|||AFTER_CLOSE|1|loss share on $289.0 m of assets|0|0|0|
PA-0150|PR-134-2011|2011-08-12|{A}4282|"This evening and over the weekend"|||AFTER_CLOSE|1|loss share on $419.6 m of assets|0|0|0|
PA-0338|PR-43-2010|2010-03-05|{A}4132|"This evening and over the weekend"|||AFTER_CLOSE|1|loss share on $433.0 m of assets|0|0|0|
PA-0285|PR-133-2010|2010-06-11|{A}4028|"This evening and over the weekend"|||AFTER_CLOSE|1|loss share on $418.8 m of assets|0|0|0|
PA-0335|PR-51-2010|2010-03-12|{A}4123|"This evening and over the weekend"|||AFTER_CLOSE|1|loss share on $379.8 m of assets|0|0|0|
PA-0401|PR-179-2009|2009-10-02|{A}3675|hotline "this evening until 9:00 p.m., EDT"|||AFTER_CLOSE|0|no loss share; approx. $83 m of assets purchased|0|0|0|
PA-0409|PR-163-2009|2009-09-04|{A}3691|"This evening and over the weekend"|||AFTER_CLOSE|1|loss share on approx. $338 m of assets|0|0|0|first session Tuesday after Labor Day
PA-0464|PR-60-2009|2009-04-24|{A}3801|hotline "this evening until 9:00 p.m., MDT"|||AFTER_CLOSE|0|no loss share; premium 0.55%, $17.8 m of assets purchased|0|0|0|
PA-0105|PR-48-2012|2012-04-27|{A}4639|"This evening and over the weekend"|||AFTER_CLOSE|1|loss share on $413.0 m of assets|0|0|0|
PA-0042|PR-47-2014|2014-06-20|{A}4883|hotline "this evening until 9:00 p.m."|||AFTER_CLOSE|0|no loss share; approx. $375.4 m of assets purchased|0|0|0|
PA-0238|PR-226-2010|2010-10-15|{A}3935|"This evening and over the weekend"|||AFTER_CLOSE|1|loss share on $334.2 m of assets|0|0|0|
PA-0414|PR-155-2009|2009-08-28|{A}3701|"This evening"|||AFTER_CLOSE|1|loss share on approx. $338 m of assets|0|0|0|
PA-0309|PR-90-2010|2010-04-23|{A}4076|"This evening and over the weekend"|||AFTER_CLOSE|1|loss share on $300.2 m of assets|0|0|0|
PA-0059|PR-50-2013|2013-06-07|{G}7e6c56|"This evening and over the weekend"|2013-06-07 18:10 EDT|{G}7e6c56|AFTER_CLOSE|0|no loss share; essentially all assets purchased|0|0|0|
PA-0138|PR-159-2011|2011-10-07|{A}4257|"This evening and over the weekend"|||AFTER_CLOSE|1|loss share on $351.9 m of assets|0|0|0|
"""

# The 35 transactions of the broader 90-row panel outside the 150 largest failures
# (same checks; FDIC releases read 2026-10-29). The five FBOP banks share the
# release of PA-0385..PA-0388; Tifton shares the release of PA-0224 (Darby).
EVIDENCE_BROADER = f"""transaction_id|fdic_pr|release_date|release_url|timing_evidence|timestamp|timestamp_url|timing_class|loss_share|loss_share_evidence|bridge_bank|systemic_risk_exception|fdic_buyer_financing|notes
PA-0482|PR-17-2009|2009-02-06|{A}3846|"closed today"; hotline "this evening until 9:00 p.m., EST"; offices reopen Monday|||AFTER_CLOSE|0|no loss share in release; approx. $17 m of assets purchased|0|0|0|
PA-0396|PR-187-2009|2009-10-23|{A}3664|"This evening and over the weekend"; hotline until 9:00 p.m. EDT|||AFTER_CLOSE|1|loss share on approx. $92 m of assets|0|0|0|
PA-0382|PR-195-2009|2009-10-30|{A}3655|nine FBOP banks "closed this evening"|||AFTER_CLOSE|1|as PA-0387 (one release for the nine FBOP banks)|0|0|0|one release for nine banks
PA-0389|PR-195-2009|2009-10-30|{A}3655|nine FBOP banks "closed this evening"|||AFTER_CLOSE|1|as PA-0387 (one release for the nine FBOP banks)|0|0|0|one release for nine banks
PA-0384|PR-195-2009|2009-10-30|{A}3655|nine FBOP banks "closed this evening"|||AFTER_CLOSE|1|as PA-0387 (one release for the nine FBOP banks)|0|0|0|one release for nine banks
PA-0383|PR-195-2009|2009-10-30|{A}3655|nine FBOP banks "closed this evening"|||AFTER_CLOSE|1|as PA-0387 (one release for the nine FBOP banks)|0|0|0|one release for nine banks
PA-0390|PR-195-2009|2009-10-30|{A}3655|nine FBOP banks "closed this evening"|||AFTER_CLOSE|1|as PA-0387 (one release for the nine FBOP banks)|0|0|0|one release for nine banks
PA-0381|PR-197-2009|2009-11-06|{A}3653|"This evening and over the weekend"; hotline until 9:00 p.m. EST|||AFTER_CLOSE|1|loss share on approx. $123 m of assets|0|0|0|
PA-0365|PR-226-2009|2009-12-11|{A}3619|"This evening and over the weekend"; hotline until 9:00 p.m. MST|||AFTER_CLOSE|1|loss share on approx. $29.8 m of assets|0|0|0|
PA-0346|PR-27-2010|2010-01-29|{A}4149|"This evening and over the weekend"; hotline until 9:00 p.m. PST|||AFTER_CLOSE|1|loss share on $255.1 m of assets|0|0|0|
PA-0336|PR-49-2010|2010-03-11|{A}4125|closed Thursday; "This evening, Friday, and over the weekend"; branches reopen Friday|||AFTER_CLOSE|1|loss share on $181.5 m of assets|0|0|0|Thursday announcement; first session Friday 2010-03-12
PA-0311|PR-88-2010|2010-04-23|{A}4078|"This evening and over the weekend"; hotline until 9:00 p.m. CDT|||AFTER_CLOSE|1|loss share on $141.5 m of assets|0|0|0|same buyer and day as PA-0309 (Wheatland)
PA-0295|PR-115-2010|2010-05-14|{A}4048|"This evening and over the weekend"; hotline until 9:00 p.m. CDT|||AFTER_CLOSE|1|loss share on $66.8 m of assets|0|0|0|
PA-0297|PR-113-2010|2010-05-14|{A}4050|"This evening and over the weekend"; hotline until 9:00 p.m. EDT|||AFTER_CLOSE|1|loss share on $101.0 m of assets|0|0|0|
PA-0259|PR-181-2010|2010-08-06|{A}3980|"This evening and over the weekend"; hotline until 9:00 p.m. CDT|||AFTER_CLOSE|1|loss share on $161.3 m of assets|0|0|0|
PA-0250|PR-196-2010|2010-08-20|{A}3965|"This evening and over the weekend"; hotline until 9:00 p.m. PDT|||AFTER_CLOSE|0|no loss share in release (2.0% deposit premium); none in Westamerica's release (8-K Ex. 99.1, 2010-08-20)|0|0|0|
PA-0235|PR-231-2010|2010-10-22|{A}3930|"This evening and over the weekend"; hotline until 9:00 p.m. EDT|||AFTER_CLOSE|1|loss share on $60.0 m of assets|0|0|0|
PA-0225|PR-249-2010|2010-11-12|{A}3911|hotline "this evening until 9:00 p.m. EST"|||AFTER_CLOSE|1|as PA-0224 (joint release; loss share on $560.2 m of the two banks' assets)|0|0|0|joint release with Darby Bank & Trust (PA-0224)
PA-0210|PR-3-2011|2011-01-07|{A}4414|"This evening and over the weekend"; hotline until 9:00 p.m. MST|||AFTER_CLOSE|1|loss share on $119.8 m of assets|0|0|0|
PA-0200|PR-25-2011|2011-02-04|{A}4392|"This evening and over the weekend"; hotline until 9:00 p.m. CST|||AFTER_CLOSE|1|loss share on $42.8 m of assets|0|0|0|
PA-0202|PR-23-2011|2011-02-04|{A}4394|hotline "this evening until 9:00 p.m., EST"|||AFTER_CLOSE|1|loss share on $94.3 m of assets (approx. $147.4 m purchased)|0|0|0|
PA-0171|PR-90-2011|2011-05-20|{A}4327|"This evening and over the weekend"; hotline until 9:00 p.m. PDT|||AFTER_CLOSE|1|loss share on $113.4 m of assets|0|0|0|
PA-0170|PR-94-2011|2011-05-27|{A}4323|"This evening and over the weekend"; hotline until 9:00 p.m. PDT|||AFTER_CLOSE|1|loss share on $142.2 m of assets|0|0|0|first session Tuesday after Memorial Day
PA-0161|PR-120-2011|2011-07-15|{A}4297|hotline "this evening until 9:00 p.m. EDT" (joint release with One Georgia Bank)|||AFTER_CLOSE|1|loss share on $164.8 m of assets|0|0|0|joint release with PA-0162
PA-0162|PR-120-2011|2011-07-15|{A}4297|hotline "this evening until 9:00 p.m. EDT" (joint release with High Trust Bank)|||AFTER_CLOSE|1|loss share on $146.3 m of assets|0|0|0|joint release with PA-0161
PA-0122|PR-195-2011|2011-12-16|{A}4221|"This evening and over the weekend"; hotline until 9:00 p.m. MST|||AFTER_CLOSE|0|no loss share in release; essentially all assets purchased|0|0|0|
PA-0115|PR-13-2012|2012-01-27|{A}4674|"This evening and over the weekend"; hotline until 9:00 p.m. EST|||AFTER_CLOSE|0|no loss share in release; essentially all assets purchased|0|0|0|
PA-0112|PR-21-2012|2012-02-24|{G}3019d6|hotline "this evening until 9:00 p.m., EST"|2012-02-24 17:02 EST|{G}3019d6|AFTER_CLOSE|1|loss share on $192.8 m of assets|0|0|0|
PA-0093|PR-80-2012|2012-07-06|{G}481076|hotline "this evening until 9:00 p.m., EDT"|2012-07-06 17:32 EDT|{G}481076|AFTER_CLOSE|0|no loss share in release; approx. $12.4 m of assets (mainly cash) purchased|0|0|0|
PA-0083|PR-106-2012|2012-09-14|{A}4581|"This evening and over the weekend"; hotline until 9:00 p.m. CDT|||AFTER_CLOSE|1|loss share on $117.8 m of assets|0|0|0|
PA-0079|PR-120-2012|2012-10-19|{A}4567|"This evening and over the weekend"; hotline until 9:00 p.m. CDT|||AFTER_CLOSE|1|loss share on $126.6 m of assets|0|0|0|
PA-0031|PR-16-2015|2015-02-13|{A}5019|hotline "this evening until 9:00 p.m., EST"|||AFTER_CLOSE|0|no loss share in release; essentially all assets purchased|0|0|0|first session Tuesday after Presidents' Day
PA-0025|PR-20-2016|2016-03-11|{A}5128|hotline "this evening until 9:00 p.m., CT"|||AFTER_CLOSE|0|no loss share in release; essentially all assets purchased|0|0|0|
PA-0023|PR-38-2016|2016-05-06|{A}5110|hotline "this evening until 9:00 p.m., ET"|||AFTER_CLOSE|0|no loss share in release; essentially all assets purchased|0|0|0|
PA-0020|PR-4-2017|2017-01-13|{A}6503|"This evening and over the weekend"; hotline until 9 p.m. ET|||AFTER_CLOSE|0|no loss share in release; essentially all assets purchased|0|0|0|first session Tuesday after Martin Luther King Jr. Day
"""

ROOT, OUT = Path(sys.argv[1]), Path(sys.argv[2])
ev55 = pd.read_csv(io.StringIO(EVIDENCE), sep="|", dtype=str, keep_default_na=False)
ev35 = pd.read_csv(io.StringIO(EVIDENCE_BROADER), sep="|", dtype=str, keep_default_na=False)
assert len(ev55) == 55 and len(ev35) == 35
ev = pd.concat([ev55, ev35], ignore_index=True)
assert ev.transaction_id.is_unique
cars = pd.read_csv(ROOT / "02b_car_conventions_2026-10-29/Stage1_Cache_Only_Rebuild_90.csv")
assert set(cars.transaction_id) == set(ev.transaction_id), "ledger and panel differ"
assert set(cars.loc[cars.inclusion_exclusion_reason == "INCLUDED", "transaction_id"]) == set(ev55.transaction_id)
cars["in_primary_panel"] = (cars.inclusion_exclusion_reason == "INCLUDED").astype(int)
keep = ["transaction_id", "in_primary_panel", "failed_bank_name", "acquirer_name", "ticker", "failure_date", "announcement_date",
        "announcement_timing", "event_trading_date", "first_reaction_date", "car_3day", "car_0p1", "car_reaction_m1p1"]
m = cars[keep].merge(ev, on="transaction_id", validate="one_to_one")
# the release date must be the announcement date used for the CARs, and the timing class must agree
assert (m.release_date == m.announcement_date).all(), m.loc[m.release_date != m.announcement_date, ["transaction_id", "release_date", "announcement_date"]]
assert (m.timing_class == m.announcement_timing).all()
m["announcement_weekday"] = pd.to_datetime(m.announcement_date).dt.day_name()
m["y_reaction_m1p1"] = (m.car_reaction_m1p1 > 0).astype(int)
m["y_release_0p1"] = (m.car_0p1 > 0).astype(int)
m["y_release_m1p1_june"] = (m.car_3day > 0).astype(int)
m["H_narrow_bridge_or_sre"] = ((m.bridge_bank == "1") | (m.systemic_risk_exception == "1")).astype(int)
m["H_broad_any_extraordinary_support"] = (m.H_narrow_bridge_or_sre.eq(1) | (m.fdic_buyer_financing == "1")).astype(int)
cols = ["transaction_id", "in_primary_panel", "failed_bank_name", "acquirer_name", "ticker", "failure_date", "fdic_pr", "release_date",
        "announcement_weekday", "release_url", "timing_evidence", "timestamp", "timestamp_url", "timing_class",
        "event_trading_date", "first_reaction_date", "car_reaction_m1p1", "y_reaction_m1p1", "car_0p1", "y_release_0p1",
        "car_3day", "y_release_m1p1_june", "loss_share", "loss_share_evidence", "bridge_bank", "systemic_risk_exception",
        "fdic_buyer_financing", "H_narrow_bridge_or_sre", "H_broad_any_extraordinary_support", "notes"]
assert m.loss_share.isin(["0", "1"]).all() and m[["bridge_bank", "systemic_risk_exception", "fdic_buyer_financing"]].isin(["0", "1"]).all().all()
m[cols].sort_values(["in_primary_panel", "transaction_id"], ascending=[False, True]).to_csv(OUT, index=False)
for nm, x in (("primary 55", m[m.in_primary_panel == 1]), ("broader 90", m)):
    print(f"{nm}: timing {x.timing_class.value_counts().to_dict()}; loss share 1 for {int((x.loss_share == '1').sum())}; "
          f"H narrow {int(x.H_narrow_bridge_or_sre.sum())}, broad {int(x.H_broad_any_extraordinary_support.sum())}; "
          f"labels reaction-day {int(x.y_reaction_m1p1.sum())}, release [0,+1] {int(x.y_release_0p1.sum())}, June [-1,+1] {int(x.y_release_m1p1_june.sum())}")
