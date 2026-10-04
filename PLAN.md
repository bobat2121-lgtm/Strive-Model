# Strive (ASST) Model: Build Plan

*Drafted 2026-10-04. Holdings and price targets change weekly, so every number below is dated.*

> **Direction change (2026-10-04):** the user chose **one engine with one valuation framework**, driven by a few levers. The analyst-preset idea in §3 is dropped; analyst targets survive only as reference markers. The lever design and its calibration are in **§11**, which takes precedence over §3–§5 wherever they conflict. §11 was signed off on 2026-10-04 and is built (`model/`).

---

## 1. How the Street models ASST

### Coverage

| Firm | Analyst | Rating | PT (date) | Method (as reported) |
|---|---|---|---|---|
| TD Cowen | Lance Vitanza | Buy | **$44** (Sep 21) | BTC NAV net of claims, plus **k × FY BTC $ Gain**. k was 2× at initiation and 3× from Aug. Uses a forward year-end BTC price ($97.5k YE26) and forecasts **32,105 BTC** at YE26 with a 70.1% FY26 BTC Yield. |
| H.C. Wainwright | Mike Colonnese | Buy | **$36** (Aug 11) | **Target mNAV (1.75×)** applied to the forward YE26 BTC NAV (May: 18,017 BTC × $150k). Then adjusts for YE preferred, cash and STRC, and divides by FD shares. |
| B. Riley | Fedor Shabalin | Buy | **$33** (Sep 22) | **mNAV multiple** (1.1× at initiation). NAV includes the asset-management business, which makes it the only firm that values it. |
| Benchmark / StoneX | Mark Palmer | Buy | **$32** (Jun 2) | No ASST math published. His MSTR and Metaplanet models are a SOTP: YE BTC value + a multiple of FY BTC $ Gain + the operating business. |
| Maxim | Matthew Galinko | Buy | **$20** (Mar 23; possibly $21 now) | "Expected future value of BTC holdings." The PT moved exactly in proportion to the BTC assumption, which suggests a gross model with **no SATA deduction** (this is an inference). |

The consensus PT is about $33 (range $21–$44). ASST closed at $30.03 on Oct 2.

**Caveat:** sell-side notes are paywalled, so these methods are reconstructed from press summaries.

### The common template

```
PT = [ B_YE × P_fwd × (premium)  −  SATA_YE  −  Debt  +  Cash/STRC  (+ k × BTC$Gain_FY)  (+ AM business) ]
     ÷ assumed fully diluted shares (warrants excluded)
```

1. Forecast year-end BTC: current holdings plus purchases funded by SATA and the common ATM.
2. Price it at a **forward** year-end BTC forecast rather than spot.
3. Add a premium: either a fixed mNAV multiple or a multiple of BTC $ Gain.
4. Deduct SATA notional and add cash.
5. Divide by FD shares.

**The KPI that moves price targets is BTC Yield**, meaning growth in BTC per FD share.

### Where they differ (each difference becomes a toggle in our model)

| Toggle | Options | Who does what |
|---|---|---|
| BTC price | spot / 12-month forward / YE forecast | Everyone uses a forward price ($97.5k–$150k) |
| Premium | fixed × gross NAV / fixed × net NAV / k × BTC $ Gain | HCW fixed; TD Cowen k × Gain |
| SATA | deducted / not deducted | HCW and TD Cowen deduct; Maxim does not |
| Share base | basic / assumed FD / FD + warrants | Street uses Strive's assumed FD, which excludes the warrants |
| Asset-management business | included / excluded | B. Riley only |

### Worked check: reconstructing TD Cowen's $44 *(my reconstruction, not confirmed)*

- YE26 NAV = 32,105 × $97.5k = $3.13B.
- FY26 BTC Gain = 70.1% × ~12,675 BTC (start-of-year holdings pro forma for Semler) ≈ 8,885 BTC, which is $866M at $97.5k.
- 3× gain = $2.60B.
- YE26 SATA ≈ $1.64B, assuming Q4 buys are SATA-funded. Cash ≈ $0.3B.
- (3.13 − 1.64 + 0.30 + 2.60) / 100.8M FD shares ≈ **$43.6**.

Measuring the gain against the 7,627 BTC held *before* Semler gives about $33 instead. This kind of gap is why the model needs a calibration view: each analyst's preset shows which inputs reproduce their PT.

---

## 2. Findings that shape the design

1. **The mNAV definition swings the answer from 1.25× to 2.1×.** At ASST $30.03, BTC about $85.2k and 9/25 data:

   | Definition | Value |
   |---|---|
   | Basic market cap / NAV | 1.25× |
   | Fully diluted | 1.29× |
   | EV (FD market cap + SATA − cash/STRC) / NAV. This is Strive's dashboard method (`ev_to_btc_nav`). | ~1.69× |
   | Price / Net BPS (Strategy's definition since Jul 23, 2026) | ~2.1× |

   The model computes all four and labels which one each view uses.

2. **Gross vs net BTC per share.** Strive's headline BTC Yield is *gross*, so SATA issuance raises it with no new shares. Net BPS = (BTC NAV − SATA − debt + cash) / FD shares. Net BPS is ≈ **$14.1** today; gross is ≈ $23.2. Track both.

3. **ASST equity is about 1.65× levered to BTC.** That is Strategy-style amplification, BTC NAV / Net Reserve. Strive's own amplification ratio, (pref + debt) / BTC NAV, is about 52%.

4. **The warrants may be the next big event.** There are 25.35M PIPE warrants at a $27 strike. They expire **Oct 13, 2026**, but that date comes only from a CEO post on X and is **not confirmed in filings**.
   - They are in the money at $30, and Strive's FD count excludes them.
   - Full exercise means +$684M and about 8,000 BTC at $85k.
   - Sats per FD share would go from about 27,250 to about 28,150 (**+3.3%**).
   - **Net BPS would rise about 18%**, because $27 is about 1.9× net BPS.
   - The model needs this as a scenario branch.

5. **SATA credit matters as much as the equity.**
   - $1.219B notional at 13.00% is about $158.5M a year, paid daily.
   - Coverage is about 14.7 years on BTC alone, or about 16.6 years including cash and STRC (the dashboard's figure).
   - BTC breakeven ARR ≈ 6.8%.
   - SATA is issued only at ≥ $100; the target trading band is $99–$101.

6. **The operating businesses are rounding errors.**
   - Asset management: $2.8B AUM, $1.5M a quarter in fees.
   - QuantaFlo: $1.4M a quarter in revenue, and management "intends to monetize" it.
   - Cash opex is about $18–19M a quarter.
   - Model them as an optional SOTP add-on and an opex burn.

---

## 3. Recommendation: one engine, many lenses

Don't pick one analyst's method. Build **one projection engine and one valuation bridge**, with each analyst as a **preset of toggles** (§1 table). Then add a "House view" preset you control.

**Make Net BPS the core unit.**
- It handles SATA correctly.
- It is where Strategy moved in July 2026.
- The TD Cowen form reduces to it: PT = NetBPS + k · Y · (B₀/B) · GrossBPS.

Every lens becomes "Net BPS plus a justified premium," so the lenses can be compared directly.

---

## 4. Architecture

The layout mirrors Portfolio Dashboard: pure logic, UI kept separate, YAML config and pytest.

```
Strive Model/
├── streamlit_app.py            # st.navigation, layout="wide"
├── model/                      # pure Python, no Streamlit imports
│   ├── sources/
│   │   ├── strive_api.py       # strive.com JSON: treasury, base-data, calculated, aggregates
│   │   ├── edgar.py            # weekly 8-K table + XBRL companyfacts (CIK 1920406)
│   │   └── market.py           # ASST/SATA via yfinance (price, ADV), BTC via Coinbase
│   ├── snapshot.py             # merges sources → dated CapitalStack (value, as_of, source per field)
│   ├── capital.py              # share classes, options/RSUs, warrants, SATA, debt, cash → claims stack
│   ├── mnav.py                 # basic / FD / EV / net mNAV; both amplification definitions
│   ├── kpis.py                 # BPS (sats), BTC Yield (Strive's additive convention), Gain, $ Gain, Net BPS, months-to-cover
│   ├── credit.py               # SATA: BTC Rating, Floor, Risk, Credit (lognormal), coverage, breakeven/hurdle ARR
│   ├── projection.py           # quarterly engine to YE2027 (see §5)
│   ├── valuation.py            # the bridge + analyst presets + sensitivity grid
│   └── scenarios.py            # deterministic grids, GBM Monte Carlo, mNAV regimes
├── panel/                      # Streamlit pages + theme
├── config/
│   ├── assumptions.yaml        # house-view defaults
│   └── analysts.yaml           # each firm: PT, date, disclosed inputs, preset toggles, source URL
├── data/cache/                 # last-good JSON pulls (with as_of)
└── tests/                      # golden tests (§7), fixtures, no network
```

**Stack:**
- Python 3.12 and Streamlit 1.64, the same as your other two apps.
- httpx, pandas, numpy, pyyaml and Altair (bundled with Streamlit).
- pytest, with `streamlit.testing.v1.AppTest` for the app.
- **No database in v1**, because strive.com already serves the history. Neon can be added later if you want our own daily snapshots.

**Reused from X Agent** (copied in, not imported, so the two projects stay decoupled):
- `strive_inputs()` and `strive_mnav()` from `xcp/sources/market.py`.
- The SATA-rate fetch from `xcp/sources/issuers.py`.
- The real 2026-09-27 Strive fixture (mNAV 1.6972) from `tests/test_calendar_inputs.py`, as a golden test.

---

## 5. Projection engine (quarterly, Q4-26 → Q4-27)

**State each quarter:** BTC, cash, STRC, SATA shares, SATA rate, common shares (A+B), options, RSUs, warrants.

**Rules each quarter:**

1. **BTC price path:** a deterministic path (spot → YE target) or a Monte Carlo draw.
2. **Common ATM:** gated by mNAV regime.
   - Issue only when EV mNAV > threshold; size = % of ADV × trading days.
   - Below 1.0×, turn on buybacks ($500M authorized).
3. **SATA ATM:** issue only when SATA ≥ $100, sized in $ per quarter or as % of SATA ADV. The SATA rate is an input, defaulting to hold at 13%.
4. **Dividend reserve:** first keep the reserve at 12 months in cash plus 6 months in STRC (Strive's stated policy).
5. **Opex:** cash burn about $18.5M a quarter. Asset management and QuantaFlo revenue are optional offsets; the QuantaFlo sale is an optional one-time inflow.
6. **Warrant branch:** exercised on date X at $27 (full / partial / none), with proceeds going to BTC.
7. **Buy BTC** with whatever capital remains.
8. **Outputs:** sats per FD share (gross and net), BTC Yield (Strive's additive convention), BTC Gain, $ Gain, amplification, SATA coverage, and a claims stack.

---

## 6. Data sources (in priority order)

| Source | What it gives | Notes |
|---|---|---|
| `strive.com/treasury/api/dashboard/base-data` | Full BTC ledger and cost basis, share-count history, cash/debt history, daily dividend list | Unofficial endpoint, so cache the last good pull |
| `…/dashboard/calculated?fromDate&toDate&currency=USD` | Daily BTC NAV, NAV per share, SATA notional | ASST price and mNAV come back null; we compute those |
| `…/dashboard/aggregates` | Daily BTC OHLCV | |
| `strive.com/api/treasury` | Summary, SATA `dividendRate`, coverage | Already used by X Agent |
| Weekly Monday 8-K (Item 8.01) | Authoritative cash, STRC, BTC, every share class, warrants, SATA shares | X Agent's digital-exposure feed already parses these |
| Mid-month 8-K | Next month's SATA rate and daily payment schedule | |
| XBRL companyfacts | Quarterly GAAP figures (BTC fair value, SATA in mezzanine equity, dividends) | Needs a `SEC_USER_AGENT` header |
| yfinance / Coinbase | ASST and SATA price and ADV; BTC spot | Reuse X Agent's functions |
| `config/analysts.yaml` | Analyst PTs and disclosed inputs | Hand-maintained |

---

## 7. Golden tests (the model must reproduce Strive's and Strategy's own numbers)

| Test | Target |
|---|---|
| EV mNAV on the 2026-09-27 fixture | 1.6972 |
| Sats per FD share on 9/25/26 | 27,250 |
| BTC Yield / BTC Gain | Q4-25: 22.2% / 1,305 BTC · Q1-26: 11.1% / 848 BTC · Q2-26: 23.9% / 3,264 BTC |
| Amplification ratio at 6/30/26 | 67.2% |
| SATA total dividend coverage | ≈16.6 years (dashboard) |
| Credit module on Strategy STRC data from 2026-09-13 | Rating 5.89×, Floor $13,127, BTC Risk 4.63%, Credit 57 bps |
| Projection backtest: start at 3/31/26 and feed actual issuance | Reproduce 6/30/26 holdings and share counts |

---

## 8. Streamlit app (after the engine passes its tests)

1. **Today:** live strip (BTC, ASST, SATA); mNAV under all 4 definitions; sats per share; Net BPS; amplification; SATA vs par, effective yield and coverage; warrant countdown; data freshness.
2. **Street:** analyst table with published PT vs our reconstruction, preset toggles, a build-your-own bridge, and a BTC price × multiple grid.
3. **Projection:** assumptions sidebar, quarterly table, and charts of BTC holdings, sats per share (gross vs net), SATA notional and amplification.
4. **SATA credit:** Rating, Floor, Risk, Credit bps, breakeven ARR, coverage, and a stress slider.
5. **Scenarios:** Monte Carlo fan chart, distribution of YE27 Net BPS and PT, mNAV-regime outcomes.
6. **Data & audit:** every input with its source and as-of date, reconciliation against Strive-reported KPIs, and test status.

**Deploy:** Streamlit Community Cloud, using the same `boot()` pattern (st.secrets → env) as your other apps.

---

## 9. Phases

| Phase | Scope | Done when |
|---|---|---|
| **0. Setup** | Folder, venv, requirements, `.claude/launch.json`, copy the X Agent helpers and fixture | `pytest` runs |
| **1. Data layer** | strive.com, 8-K, XBRL and market sources; last-good cache; `snapshot.py` | `python -m model.snapshot` prints a capital stack matching the 9/28 8-K |
| **2. Core math** | `capital`, `mnav`, `kpis`, `credit` | All §7 golden tests pass except the backtest |
| **3. Projection** | Quarterly engine and warrant branch | Backtest passes; one quarter hand-checked |
| **4. Valuation** | Bridge, 5 analyst presets, house view, sensitivity grid | Each analyst PT reproduced within ±5% or the gap documented |
| **5. Streamlit** | Pages 1–4 and 6; deploy | `AppTest` smoke tests pass; app runs locally and on Cloud |
| **6. Scenarios** | GBM Monte Carlo (μ 10%, σ 40–60%), mNAV regimes, page 5 | Seeded runs are reproducible |

---

## 10. Unverified or open items

- Warrant expiry of Oct 13, 2026: CEO post on X only, not in filings.
- SATA ATM capacity remaining after 8/7 (estimated at about $1.8B).
- Exact composition of EV in Strive's dashboard mNAV.
- Benchmark's and B. Riley's current inputs; Maxim's current PT.
- The strive.com JSON endpoints are undocumented and could change without notice.

*This is a modeling tool that reconstructs published methods. It is not a recommendation.*

---

## Key sources

- [Strive 8-K, Sep 28 2026 (weekly table)](https://www.sec.gov/Archives/edgar/data/0001920406/000162828026063653/asst-20260928.htm)
- [Strive Q2-26 10-Q](https://www.sec.gov/Archives/edgar/data/1920406/000162828026054985/asst-20260630.htm) · [Q2-26 earnings release](https://www.sec.gov/Archives/edgar/data/1920406/000162828026054984/striveincq22026earningsrel.htm) · [8-K Jul 6 (KPI table)](https://www.sec.gov/Archives/edgar/data/1920406/000162828026047102/asst-20260706.htm)
- [TD Cowen ASST, Aug 31 (The Block)](https://www.theblock.co/news/business/2026-08-31-strive-fifth-largest-public-bitcoin-treasury-1800-btc-buy-td-cowen-lifts-asst-price-target-413112) · [Sep 21 (The Block)](https://www.theblock.co/news/markets/2026-09-21-strive-adds-1355-bitcoin-picks-up-pace-year-end-second-place-treasury-goal-415940) · [TD Cowen MSTR formula (The Block)](https://www.theblock.co/post/401824/td-cowen-raises-strategy-price-target-to-400-citing-faster-bitcoin-accumulation-and-accretive-deleveraging)
- [H.C. Wainwright method (Investing.com)](https://ca.investing.com/news/stock-market-news/hc-wainwright-lowers-strive-enterprises-stock-price-target-to-36-93CH-4643202) · [B. Riley initiation (Investing.com)](https://www.investing.com/news/analyst-ratings/briley-initiates-strive-enterprises-stock-with-buy-rating-93CH-4551236) · [Maxim cut (Yahoo)](https://finance.yahoo.com/markets/stocks/articles/maxim-lowers-price-target-strive-073001737.html) · [Benchmark initiation (Investing.com)](https://www.investing.com/news/analyst-ratings/benchmark-initiates-strive-enterprises-stock-with-buy-on-bitcoin-strategy-93CH-4722283)
- [Strategy mNAV redefinition FWP, Aug 2026](https://www.sec.gov/Archives/edgar/data/0001050446/000119312526363557/d431748dfwp.htm) · [STRC Investor Briefing (credit-model definitions)](https://assets.contentstack.io/v3/assets/bltf8d808d9b8cebd37/blt23d718fe5cf3132e/6aa742d1f08d251ec0991faf/STRC_Investor_Briefing_As_of_2026-09-13.pdf)
- [StockAnalysis ASST forecast](https://stockanalysis.com/stocks/asst/forecast/) · [MarketBeat](https://www.marketbeat.com/stocks/NASDAQ/ASST/forecast/) · [warrant expiry report (KuCoin)](https://www.kucoin.com/news/flash/strive-extends-exercise-deadline-for-718m-pipe-warrants-to-october-13)

---

## 11. Lever design (single framework, signed off and built 2026-10-04)

**Time step:** weekly, matching the Monday 8-K cadence. Starting state: the 9/25/26 8-K. Outputs at YE26, YE27 and YE28.

### Calibration: the last 8 weeks of 8-Ks (`research/issuance_calibration.py`)

**Method**
- Common ATM dollars = (change in issued shares − warrant exercises) × that week's ASST VWAP.
- Check: sources (ATM + warrants at $27 + SATA at $100) against uses (BTC bought + change in cash + SATA dividends + about $1.4M a week of opex).
- Result: **they reconcile within $2M every week.**

| Week ending | SATA issued | Common ATM (est.) | % FD shares | Warrants | Amplification | EV mNAV | Net mNAV | Sats/FD share |
|---|---|---|---|---|---|---|---|---|
| 8/14 | $0 | $7M | 0.67% | — | 61.4% | 1.32× | 1.58× | 22,671 |
| 8/21 | $44M | $58M | 4.08% | — | 49.4% | 1.37× | 1.59× | 22,976 |
| 8/28 | $80M | $76M | 3.85% | — | 50.3% | 1.54× | 1.86× | 23,990 |
| 9/04 | $92M | $42M | 1.73% | — | 51.1% | 1.75× | 2.21× | 24,994 |
| 9/11 | $40M | $1M | 0.03% | — | 53.9% | 1.81× | 2.37× | 25,474 |
| 9/18 | $79M | $36M | 1.27% | $21M | 52.5% | 1.81× | 2.33× | 26,317 |
| 9/25 | $101M | $6M | 0.19% | $12M | 52.8% | 1.68× | 2.14× | 27,250 |

**Findings**
- **SATA:** $72.7M a week on average over 6 weeks ($40–101M), with the trend rising.
  - SATA has closed at $100.01 since late August. Strive appears to sell into all demand at par.
  - There was **zero** SATA issuance from Jul 1 to Aug 14, when SATA traded at $91–99.7.
- **Common ATM:** $36.4M a week, or 1.86% of FD shares a week. The issuance was heavily front-loaded: about 0.5% a week over the last 3 weeks.
  - The ATM went quiet once ASST cleared the $27 warrant strike. One possible reason is protecting the price before the warrant deadline, but that is speculation.
- **Capital mix:** SATA was **67%** of new capital over the 6 weeks and 84% over the last 3.
- **Amplification fell from 61.4% to 52.8%** even though SATA notional rose 56% ($783M → $1,219M). BTC rose 33% and about $250M of equity-funded BTC was added. Amplification is the *output* of three forces.
- **Dividend reserve:** about 19.5% of each SATA dollar goes to cash (18 months × 13%). Cash rose $94M against the $85M this implies.

### The four levers (decisions locked 2026-10-04)

1. **BTC price:** a YE26 anchor, then a normalized CAGR with user-typed bands (default 30/40/50%, extendable).
   - Weekly path: log-linear from spot to the anchor, then (1+g) per year, actual/actual, exact at each Dec 31.
   - The user is bullish, so the bands stay above the 13% SATA rate by choice.
2. **SATA issuance:** always at $100 par, with no par gate. It has two phases (decided 2026-10-04):
   - **Phase 1:** a fixed $ per week through YE2026 ($70M; the 6-week average was $72.7M).
   - **Phase 2:** **a % of the BTC stack per week** (default 1.0%).
   - The two are blended over a 13-week glide.
   - At 40% CAGR, 1.0% holds amplification at about 49–51% through 2028, near today's 52%. A fixed $70M lets it fade to 33%.
   - The cost is demand: about $130M a week by YE27 and about $360M a week by YE28.
   - Each raise first tops the cash reserve back up to 18 months of dividends; the rest buys BTC.
3. **Common issuance:** **% of FD shares per week** (default 0.5%), sold at the modeled price.
   - The warrants are a separate one-off: 10/13, exercised at $27 only if in the money.
4. **Multiple:** **Strive's mNAV = "Multiple to Net Treasury Asset Value"**, i.e. ASST price / NTAV per diluted share. It was 2.13× on 10/4/26.
   - NTAV = BTC + cash + STRC − debt − SATA liquidation preference.
   - This corrects the EV/BTC NAV (1.69×) used in the draft. The user confirmed it from the strive.com dashboard.
   - Each table cell holds one multiple from YE26 on, gliding from today's. So the multiple also sets the price at which common is sold.
   - **Consequence:** SATA sold at par leaves NTAV per share unchanged and adds value only through BTC outrunning the dividend. Common sold at mNAV m adds 1 − 1/m per dollar.
   - Table rows default to 1.25–2.5×, plus a "today" row.

**Valuation (decided 2026-10-04, after the user audited why more SATA barely moved the YE28 price):**
- **Problem:** price = mNAV × NTAV doesn't pay for future growth. SATA adds nothing the day it's sold, and most of the extra SATA arrives late.
- **Price target, dated YE2028 (TD Cowen's structure):** PT = NTAV/share + k × the next year's **net** gain per share. Net gain = growth in net BTC per share (NTAV / BTC price), valued at the date's BTC price.
- **Defaults:** k = 3x (TD Cowen's); today's price implies about 1.5x. Gross gain (Strive's BTC Yield) is an option, but it counts SATA-funded BTC and inflates high-SATA cases.
- **Horizon:** the forecast now runs to 2031-12-31 so the target's forward year exists.
- **Market mNAV glide:** kept. It sets the price new common sells at.
- **Cash reserve:** the 18-month policy holds.
- **Base case:** PT ≈ $241, an implied 2.53x.

**SATA made demand-led (2026-10-04):**
- The "% of the BTC stack" rule compounded to an implausible $389B by YE31.
- New rule: $70M a week through YE26, then the weekly amount grows at a lever rate (default 50% a year).
- Result: SATA reaches $13.4B at YE28 and $62B at YE31. Base YE28 target ≈ $178 (implied 1.88×).
- Amplification drifts down after 2027 (42% at YE28, 15% at YE31) because common issuance outgrows SATA.

**Valuation switched to TD Cowen's method (2026-10-04, approved by the user):**
- PT = (NTAV + k × the year's BTC $ Gain) / FD shares. BTC $ Gain = start-of-year BTC × BTC Yield × year-end BTC price, gross, over the year ending at the target. k = 3.
- It reproduces TD Cowen's $44 (calculated $43.55). Today's price implies 3.37× on Strive's actual trailing 12 months.
- FY26 is stitched from history: the yield runs from actual 12/31/25 sats per share (17,037), and the gain base includes Semler's 5,048.1 BTC.
- The year-after window and the net/gross selector were removed for simplicity.
- The premium is split into SATA-funded and common-funded parts, and a net-basis value is shown as a reference.
- Base case YE28 ≈ $223, an implied 2.34×.

**Dividends and the rate (2026-10-04):**
- "Op. costs" is the net cash burn only.
- SATA dividends are their own attribution step, about −$14 a share by YE28 in the base case.
- The SATA rate holds at 13%, with an optional glide to a target by a date. 13% → 10% by YE27 lifts the YE28 target from about $241 to about $272.

**Publishing (2026-10-04):**
- Public GitHub repo `bobat2121-lgtm/Strive-Model`. Only the owner can push.
- The capital-report feed URL moved to a secret (`FILINGS_FEED_URL`).
- `data/seed/` is a committed fallback snapshot.

**Streamlit app (built 2026-10-04):** `streamlit_app.py`, with a Model page and an Issuance history page.
- Model page: the lever sidebar, today's tiles, the gain waterfall, the price table and the week-by-week charts.
- The final visual design is still to come.

**Attribution:** five parts that sum exactly:
- BTC move (one-for-one tracker)
- amplification (SATA leverage net of dividends)
- issuance (common + warrants)
- multiple
- op. costs

### Core identity (for the equity-return readout)

Equity return ≈ (r − A·d) / (1 − A), where r is the BTC return, A the amplification and d the SATA rate. This holds with A rebalanced to a constant and ignores premium and issuance effects.

- Equity breaks even at r = A·d (6.5% when A = 50% and d = 13%).
- Amplification beats unlevered BTC only when r > d (13%).
- Each YE price change is split into the parts above (see `model/valuation.py`).
