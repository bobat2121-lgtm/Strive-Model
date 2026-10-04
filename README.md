# Strive Model

One weekly engine for Strive (ASST), driven by four levers. It projects the balance sheet week by week to the end of 2028 and
values ASST with the multiple Strive itself publishes. A Streamlit app puts the levers in a sidebar and shows where the gain comes from.

## The levers (`config/levers.yaml`)

1. **BTC price**: a year-end anchor, then a normalized CAGR. Each band you list becomes a column of the price table.
2. **SATA** (always at $100 par): a fixed $ per week through YE2026 ($70M), then a % of the BTC stack per week (1.0%).
   The two are blended over a 13-week glide. Each raise first tops the cash dividend reserve back up to 18 months; the rest buys BTC.
   The dividend rate holds at 13% (Strive's current rate), or glides in a straight line to a target rate by a date you pick.
3. **Common**: new shares each week as a % of fully diluted shares, sold at the modeled price.
4. **Price target** (TD Cowen's method), dated 12/31/2028:
   ```
   PT = (NTAV + k x the year's BTC $ Gain) / diluted shares
   ```
   - **BTC $ Gain** = BTC held at the start of the year × BTC Yield × the year-end BTC price.
   - **k** defaults to 3x, TD Cowen's multiple. Today's price implies about 3.4x on Strive's actual trailing 12 months.
   - The forecast runs to 2031.
5. **Market mNAV**: Strive's "Multiple to Net Treasury Asset Value", i.e. ASST price ÷ NTAV per diluted share (2.13x on 10/4/26). During the forecast it sets the price new common sells at. Hold today's multiple, or glide to a target.

**Fixed assumptions:**
- the PIPE warrants (25.35M at $27, exercised on 10/13/26 if in the money)
- a net cash burn of about $1.2M a week

## How it values ASST

```
NTAV per share = (BTC x BTC price + cash + STRC - debt - SATA liquidation preference) / assumed fully diluted shares
BTC Yield      = growth in BTC per diluted share over the year (Strive's KPI)
BTC $ Gain     = BTC held at the start of the year x BTC Yield x year-end BTC price
Price target   = (NTAV + k x BTC $ Gain) / diluted shares          (TD Cowen; reproduces their $44 on ASST)
Market price   = market mNAV x NTAV per share   (the price new common sells at during the forecast)
```

In plain terms, the price target is what common owns at the date plus k years' worth of the bitcoin the company
added per share that year.

- **BTC Yield counts every bitcoin bought, including bitcoin bought with SATA money.** SATA holders are owed $100 a share, and NTAV deducts that. The page therefore splits the premium into a SATA-funded and a common-funded part, and shows a net-basis value (gain counted on NTAV ÷ BTC price) as a reference.
- **FY2026 is stitched from actual history:** the yield is measured from Strive's actual 12/31/25 BTC per share (17,037 sats), and the BTC Gain base includes the 5,048.1 BTC from the Semler merger.

- **SATA:** sold at par, it leaves NTAV per share unchanged on the day. It adds value only while BTC outruns the dividend.
- **Common:** sold at an mNAV above 1, it adds 1 − 1/mNAV of each dollar raised to NTAV per share.

**Attribution:** the price target is built up in steps that add up exactly:

    NTAV today → BTC move → amplification → SATA dividends → issuance → op. costs → NTAV at the date
               → growth premium (SATA-funded + common-funded) → price target

- **BTC move**: net assets tracking BTC one-for-one.
- **Amplification**: what the SATA-funded BTC gains, after the 18-month cash-reserve drag.
- **SATA dividends**: the dividends paid on that SATA.
- **Issuance**: common and warrants sold above NTAV per share.
- **Op. costs**: Strive's net cash burn. This is not dividends.
- **Growth premium**: k × the year's BTC $ Gain per share, split by who paid for that year's bitcoin.

## Run

```
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m streamlit run streamlit_app.py --server.port 8521   # the app
.venv\Scripts\python -m model                 # snapshot, levers, price tables, base path, attribution
.venv\Scripts\python -m model --offline       # cached data only
.venv\Scripts\python -m model --live-prices   # Coinbase BTC spot + latest ASST close
.venv\Scripts\python -m model calibrate       # weekly SATA / common issuance from 8-K share counts x VWAP
.venv\Scripts\python -m pytest
```

## Deploy on Streamlit Community Cloud

1. On [share.streamlit.io](https://share.streamlit.io), choose **Create app** and pick `bobat2121-lgtm/Strive-Model`, branch `main`, main file `streamlit_app.py`.
2. Under **Advanced settings**, pick Python 3.12 or 3.13.
3. Optionally, paste `FILINGS_FEED_URL = "…"` into **Secrets**. It is the capital-report feed behind the Issuance history page; `.streamlit/secrets.toml.example` shows the format.
4. Without the secret, the page uses the snapshot bundled in `data/seed/`.

## Data

| Source | Used for |
|---|---|
| strive.com dashboard JSON | balance sheet, SATA, prices, warrants (cached in `data/cache/`) |
| capital-report feed (secret `FILINGS_FEED_URL`) | weekly 8-K facts, including the SATA share history |
| Yahoo | ASST/SATA bars for the calibration |
| Coinbase | live BTC spot |

Each source falls back to this machine's last good pull (`data/cache/`, not in git), then to the snapshot committed in
`data/seed/`, so a fresh deploy still runs if a source is down.

The tests run on frozen copies in `tests/fixtures/` and never touch the network. Every metric is pinned to a number Strive publishes.
