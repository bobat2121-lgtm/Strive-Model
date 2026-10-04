"""One-off calibration (2026-10-04): weekly SATA and common-ATM issuance since SATA reached par.

Share counts come from strive.com's dashboard (base.json) and SATA shares from the weekly 8-K feed (feed.json).
8-Ks stopped disclosing ATM dollars after 8/7, so common ATM $ = (change in issued shares - warrant exercises)
x the week's ASST VWAP. Check: sources (ATM + warrants + SATA) vs uses (BTC bought + change in cash + dividends + opex).
Run: python research/issuance_calibration.py  (needs pandas + yfinance)
"""
import json, warnings
from pathlib import Path
import pandas as pd, yfinance as yf
warnings.filterwarnings("ignore")
DATA = Path(__file__).parent / "data-2026-10-04"
base =json.load(open(DATA / "base.json"))["data"]
feed = json.load(open(DATA / "feed.json"))["filings"]

px = {}
for t in ["ASST", "SATA", "BTC-USD"]:
    h = yf.Ticker(t).history(start="2026-06-20", end="2026-10-04", interval="1d", auto_adjust=False)
    h.index = h.index.tz_localize(None).normalize()
    h["tp"] = (h["High"] + h["Low"] + h["Close"]) / 3
    px[t] = h
print("last closes:", {t: round(px[t]["Close"].iloc[-1], 2) for t in px})

# SATA closes vs par, from July on
s = px["SATA"]["Close"]
print("\nSATA weekly min/max close:")
print(s.resample("W-FRI").agg(["min", "max", "last"]).round(2).loc["2026-07-01":].to_string())

shares = {r["date"]: r for r in base["shares"]}
cash = {r["date"]: r for r in base["cashDebt"]}
btc_cost = {}
for t in base["transactions"]:
    btc_cost[t["transaction_date"]] = btc_cost.get(t["transaction_date"], 0) + t["cost"]
sata = {}
for x in feed:
    if x.get("ticker") == "ASST" and (e := x.get("extracted")) and "sata_shares" in (e.get("facts") or {}):
        sata[e["balanceDate"]] = e["facts"]["sata_shares"]
sata["2026-08-07"] = 7829502  # 10-Q / 8-K: unchanged 6/30 -> 8/14

weeks = ["2026-07-31","2026-08-07","2026-08-14","2026-08-21","2026-08-28","2026-09-04","2026-09-11","2026-09-18","2026-09-25"]
rows = []
for prev, cur in zip(weeks, weeks[1:]):
    win = lambda t: px[t].loc[(px[t].index > prev) & (px[t].index <= cur)]
    a, p = win("ASST"), win("SATA")
    vw_a = (a.tp * a.Volume).sum() / a.Volume.sum()
    vw_p = (p.tp * p.Volume).sum() / p.Volume.sum()
    s0, s1 = shares[prev], shares[cur]
    d_issued = s1["issued_shares"] - s0["issued_shares"]
    warr = s0["traditional_warrants"] - s1["traditional_warrants"]
    atm_sh = d_issued - warr
    d_sata = sata.get(cur, None) - sata.get(prev, None) if cur in sata and prev in sata else None
    sata_usd = d_sata * max(vw_p, 100) if d_sata is not None else None
    atm_usd = atm_sh * vw_a
    warr_usd = warr * 27
    uses = btc_cost.get(cur, 0) + (cash[cur]["cash"] - cash[prev]["cash"])
    divs = (sata.get(prev) or 0) * 0.0516 * 5
    rows.append(dict(week=cur, asst_vwap=round(vw_a, 2), sata_vwap=round(vw_p, 2),
        atm_sh=atm_sh, pct_sh=round(100 * atm_sh / s0["fully_diluted_shares"], 2), atm_usd_m=round(atm_usd / 1e6, 1),
        warr_sh=warr, sata_sh=d_sata, sata_usd_m=round(sata_usd / 1e6, 1) if sata_usd is not None else None,
        sources_m=round((atm_usd + warr_usd + (sata_usd or 0)) / 1e6, 1),
        uses_m=round((uses + divs + 1.4e6) / 1e6, 1), btc_buy_m=round(btc_cost.get(cur, 0) / 1e6, 1),
        btc_vwap=round(win("BTC-USD").Close.mean())))
df = pd.DataFrame(rows).set_index("week")
pd.set_option("display.width", 250)
print("\n", df.to_string())
act = df.loc["2026-08-21":]
print("\n6 weeks since SATA issuance resumed (wk ending 8/21 -> 9/25):")
print(" SATA $/wk avg: %.1fM | common ATM $/wk avg: %.1fM | common ATM %% FD shares/wk avg: %.2f%% | BTC bought $/wk: %.1fM"
      % (act.sata_usd_m.mean(), act.atm_usd_m.mean(), act.pct_sh.mean(), act.btc_buy_m.mean()))
print(" SATA share of new capital: %.0f%%" % (100 * act.sata_usd_m.sum() / (act.sata_usd_m.sum() + act.atm_usd_m.sum())))

print("\nWeekly state (Friday balance dates):")
hold = {}
for x in feed:
    if x.get("ticker") == "ASST" and (e := x.get("extracted")) and "btc_holdings" in (e.get("facts") or {}):
        hold[e["balanceDate"]] = e["facts"]["btc_holdings"]
hold["2026-08-07"] = 20167
out = []
for w in weeks[1:]:
    btcp = px["BTC-USD"].Close.loc[:w].iloc[-1]
    ap = px["ASST"].Close.loc[:w].iloc[-1]
    nav = hold[w] * btcp
    pref = sata[w] * 100
    c = cash[w]["cash"] + cash[w]["marketable_securities"]
    fd = shares[w]["fully_diluted_shares"]
    a = px["ASST"].loc[(px["ASST"].index > str(pd.Timestamp(w) - pd.Timedelta(days=7))[:10]) & (px["ASST"].index <= w)]
    out.append(dict(week=w, btc=hold[w], btc_px=round(btcp), asst=round(ap, 2), amplif_pct=round(100 * pref / nav, 1),
        ev_mnav=round((fd * ap + pref - c) / nav, 2), net_mnav=round(ap / ((nav - pref + c) / fd), 2),
        sats_fd=round(hold[w] / fd * 1e8), net_bps=round((nav - pref + c) / fd, 2),
        asst_adv_m=round((a.tp * a.Volume).mean() / 1e6, 1)))
print(pd.DataFrame(out).set_index("week").to_string())
