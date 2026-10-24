# Strive Model

One weekly engine for Strive (ASST), driven by four levers. It projects the balance sheet week by week to the end of 2028 and
values ASST with the multiple Strive itself publishes. A Streamlit app puts the levers in a sidebar and shows where the gain comes from.

## The levers (`config/levers.yaml`)

1. **BTC price**: a year-end anchor, then a normalized CAGR. Each band you list becomes a column of the price table.
2. **SATA** (always at $100 par), demand-led: a fixed $ per week through YE2026 ($70M), then that weekly amount grows at a rate you set (default 50% a year; about $13B outstanding by YE2028).
   Each raise first tops the cash dividend reserve back up to 18 months; the rest buys BTC.
   The dividend rate holds at 13% (Strive's current rate), or glides in a straight line to a target rate by a date you pick.
3. **Common**: new shares each week as a % of fully diluted shares, sold at the modeled price.
4. **Price target** (BTC-earnings method), dated 12/31/2028:
   ```
   PT = (NTAV + k x the year's BTC $ Gain) / diluted shares
   ```
   - **BTC $ Gain** = BTC held at the start of the year × BTC Yield × the year-end BTC price.
   - **k** starts at what today's price implies (about 3.4x on Strive's actual trailing 12 months) and glides in a straight line to your k (default 3x) by a date (default the target date). You can also turn the glide off.
   - The forecast runs to 2031.
5. **Market mNAV**: Strive's "Multiple to Net Treasury Asset Value", i.e. ASST price ÷ NTAV per diluted share (2.13x on 10/4/26). During the forecast it sets the price new common sells at.
   - **Default, "Follow the model's valuation":** the model solves for a path where the market multiple at each year end equals the price target's implied mNAV, so shares sell at what the model says they're worth.
   - **Manual:** hold today's multiple, or glide to a target.

**Fixed assumptions:**
- the PIPE warrants (25.35M at $27, exercised on 10/13/26 if in the money)
- a net cash burn of about $1.2M a week

## How it values ASST

```
NTAV per share = (BTC x BTC price + cash + STRC - debt - SATA claim - SATS claim) / assumed fully diluted shares
BTC Yield      = growth in BTC per diluted share over the year (Strive's KPI)
BTC $ Gain     = BTC held at the start of the year x BTC Yield x year-end BTC price
Price target   = (NTAV + k x BTC $ Gain) / diluted shares          (reproduces a published $44 sell-side target on ASST)
Market price   = market mNAV x NTAV per share   (the price new common sells at during the forecast)
```

In plain terms, the price target is what common owns at the date plus k years' worth of the bitcoin the company
added per share that year.

- **BTC Yield counts every bitcoin bought, including bitcoin bought with SATA money.** SATA holders are owed $100 a share, and NTAV deducts that. The page therefore splits the premium into a SATA-funded and a common-funded part, and shows a net-basis value (gain counted on NTAV ÷ BTC price) as a reference.
- **FY2026 is stitched from actual history:** the yield is measured from Strive's actual 12/31/25 BTC per share (17,037 sats), and the BTC Gain base includes the 5,048.1 BTC from the Semler merger.

- **SATS:** the October 20, 2026 IPO adds 7 million nonconvertible preferred shares: $700M stated amount, $608.15M estimated net proceeds, and $105M annual dividends. The engine inserts the IPO once into a pre-IPO forecast, deducts the preferred claim in NTAV, reserves dividend cash, and accrues SATS dividends on a 30/360 basis. It does not add diluted common shares. The forecast assumes the $100 liquidation-preference floor and no additional SATS issuance. See the [final prospectus](https://www.sec.gov/Archives/edgar/data/1920406/000095010326015734/dp255138_424b5.htm).

- **SATA:** sold at par, it leaves NTAV per share unchanged on the day. It adds value only while BTC outruns the dividend.
- **Common:** sold at an mNAV above 1, it adds 1 − 1/mNAV of each dollar raised to NTAV per share.

**Attribution:** the price target is built up in steps that add up exactly:

    NTAV today → BTC move → amplification → SATA dividends → SATS dividends → SATS issuance cost → common issuance → op. costs → NTAV at the date
               → growth premium (SATA-funded + SATS-funded + common-funded) → price target

- **BTC move**: net assets tracking BTC one-for-one.
- **Amplification**: what preferred-funded BTC gains, after the dividend cash-reserve drag.
- **SATA / SATS dividends**: the separate dividend costs. **SATS issuance cost**: the difference between the initial preferred claim and estimated net proceeds.
- **Issuance**: common and warrants sold above NTAV per share.
- **Op. costs**: Strive's net cash burn. This is not dividends.
- **Growth premium**: k × the year's BTC $ Gain per share, split by who paid for that year's bitcoin.

## Live metrics and model detail

**Strive today** always loads current company data and market quotes independently of the selected published scenario. It refreshes every 60 seconds while the browser session is active. BTC spot and ASST quotes refresh independently, and their source timestamps are shown. Reported holdings remain dated to the latest filing; live prices do not imply live holdings. A pre-IPO reported cash balance is supplemented by the estimated SATS net proceeds, explicitly labeled pro forma; reported balances that already include the IPO are not supplemented again. Cached or unavailable sources are identified instead of silently presented as current.

The first **Full model detail** tab is **Model**, with the requested column order. Rows show the starting snapshot and each forecast year end. BTC yield and BTC dollar gain are for that calendar year (year to date on the starting row), rather than cumulative forecast yield. Historical published targets retain their original values; when the new SATS model changes the recomputed target, the hero identifies the previously published target.

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
