# Donchian Channel — Literature Review

Compiled 2026-07-22 via live web search. Primary-source verification was done
on the original Turtle rules PDF. Claims that could not be traced to a real,
checkable source are flagged in section 5 — nothing is cited from memory alone.

---

## 1. Origins and mechanics

### 1.1 Richard Donchian and the weekly rule

Richard Donchian (1905-1993), a commodities broker who founded Futures, Inc.
and later ran managed futures at Hayden Stone, is conventionally called the
"father of trend following." His **4-week rule**: go long when price exceeds
the highest high of the preceding four weeks; reverse to short when price
falls below the lowest low of the preceding four weeks. In original form it is
a stop-and-reverse system — always in the market.

The generalized **N-day Donchian channel**:

- Upper band = max(High, last N days)
- Lower band = min(Low, last N days)
- Midline = (upper + lower) / 2

Equity-relevant identity: **the 252-day Donchian upper band is the 52-week
high**, which connects this indicator directly to a large peer-reviewed
literature (section 3).

### 1.2 Standard parameterizations and variants

- **Symmetric stop-and-reverse** (classic 4-week rule): enter long at N-day
  high, flip short at N-day low.
- **Asymmetric entry/exit channels**: enter on a long channel, exit on a
  shorter one (20-day entry / 10-day exit; 55/20 — the Turtle configuration).
  Creates a "flat" state, which matters for long-only equity implementations.
- **Midline exit**: exit on a cross of the channel midline — faster, gives
  back less, whipsaws more.
- 20/55-day lookbacks are canonical purely because of Turtle lineage; 252-day
  is the 52-week-high case.

### 1.3 The Turtle system (primary source, verified)

Source: "The Original Turtle Trading Rules," Curtis M. Faith, free e-book
c. 2003 (mirror: <https://oxfordstrat.com/coasdfASD32/uploads/2016/01/turtle-rules.pdf>).
States explicitly the Turtle systems were "based on the Channel Breakout
systems taught by Richard Donchian." Verified rules:

- **System 1 (short-term)**: enter when price exceeds the 20-day high/low by
  one tick; exit on a 10-day breakout against the position. Filter: skip the
  breakout if the last breakout in that market was a winner (a breakout
  counts as a loser if price moved 2N against it first). The 55-day
  "Failsafe Breakout" catches skipped moves that run.
- **System 2 (long-term)**: enter at the 55-day high/low; exit on a 20-day
  breakout against the position. No filter.
- **N (volatility unit)**: 20-day Wilder-style ATR:
  `N = (19 * PDN + TR) / 20`, `TR = max(H-L, H-PDC, PDC-L)`.
- **Position sizing**: units sized so 1N move = 1% of account equity —
  inverse-volatility sizing, the direct ancestor of vol-targeted sizing in
  Moskowitz-Ooi-Pedersen.
- **Pyramiding**: add 1 unit every N/2 of favorable movement, max 4 units per
  market. **Stops**: 2N from entry, trailed as units are added.
- The exits chapter stresses that giving back 30-40% of open equity is
  intrinsic to positive expectancy — most breakouts fail; the fat right tail
  pays for them.

---

## 2. Academic evidence

### 2.1 Brock, Lakonishok & LeBaron (1992) — the anchor equity study

"Simple Technical Trading Rules and the Stochastic Properties of Stock
Returns," *Journal of Finance* 47(5), 1731-1764. Peer-reviewed.
<https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1992.tb04681.x>

Tests moving-average and **trading range breakout (TRB)** rules — the TRB
rule is exactly a Donchian-style rule (buy at the 50/150/200-day local max,
sell at the local min) — on the DJIA, 1897-1986. Bootstrap inference against
random-walk, AR(1), GARCH-M and EGARCH nulls: buy signals generate higher and
less volatile subsequent returns; inconsistent with all four nulls. The most
cited evidence that N-day-high breakouts carried predictive information in
equity indices historically. Caveats: index-level, pre-1987, no transaction
costs in headline tests — and see 2.5.

### 2.2 Lukac, Brorsen & Irwin — channel breakout in futures

"A Test of Futures Market Disequilibrium Using Twelve Different Technical
Trading Systems," *Applied Economics* 20(5), 1988. Peer-reviewed. Simulated
12 mechanical systems on 12 futures markets, 1978-1984, with realistic costs
and out-of-sample parameter re-optimization. Channel breakout (the Donchian
rule) was among the small set of systems producing statistically significant
net returns vs buy-and-hold — the standard citation for "channel breakout
worked in futures." Related: Lukac & Irwin, *Journal of Futures Markets*
1988 — high signal correlation among trend systems (Donchian breakouts, MA
crossovers etc. are near-substitutes).

**Out-of-sample sequel:** Park & Irwin, "The Profitability of Technical
Trading Rules in US Futures Markets: A Data Snooping Free Test," *Journal of
Futures Markets*. Replicated the exact Lukac-Brorsen-Irwin model on fresh
1985-2003 data: **the excess returns did not persist**. Same rules, same
assumptions, new data, profits gone.

### 2.3 Park & Irwin (2007) — the survey

"What Do We Know About the Profitability of Technical Analysis?", *Journal of
Economic Surveys* 21(4), 786-826. Peer-reviewed survey of ~137 studies.
<https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1467-6419.2007.00519.x>

Technical rules (including channel breakouts) generated economic profits in
futures and FX at least until the early 1990s; evidence in stock markets is
weaker and contested; most positive studies suffer from data snooping,
ex-post rule selection, and inadequate cost/risk treatment. One-line summary:
profitability evidence is strongest exactly where Donchian rules originated
(futures/FX) and weakest/most-decayed in equities.

### 2.4 Time-series momentum and the century of evidence

"Time Series Momentum," Moskowitz, Ooi, Pedersen, *Journal of Financial
Economics* 104(2), 228-250, 2012. Peer-reviewed.
<https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf>

Sign of an instrument's own past 12-month excess return predicts its
next-month return across 58 futures; persistence ~12 months, partial
reversal beyond — under-reaction then delayed over-reaction. Positions sized
inversely to ex-ante vol (academic descendant of Turtle 1N-=-1% sizing).
Relevance: a Donchian breakout is a path-dependent implementation of the same
signal class; MOP is the cleanest evidence the class is real at asset-class
level.

"A Century of Evidence on Trend-Following Investing," Hurst, Ooi, Pedersen,
*Journal of Portfolio Management* 2017. Practitioner whitepaper.
<https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2993026>
1/3/12-month TSM back to 1880: positive gross performance every decade,
strong in 8 of 10 worst equity drawdowns. AQR authors evaluating an AQR-style
strategy — treat economics as robust, Sharpe magnitudes as vendor-favorable.

Signal-equivalence: Beekhuizen & Hallerbach, "Uncovering Trend Rules,"
*Journal of Alternative Investments* 20(2), 2017.
<https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2604942>
Maps trend rules to implicit weighting schemes over past returns. Answer to
"is a 55-day Donchian breakout different from 55-day TSM?": same information
set, different (nonlinear, path-dependent) weighting, plus an implicit
trailing stop.

### 2.5 Data-snooping critiques and post-1990s decay in equities

"Data-Snooping, Technical Trading Rule Performance, and the Bootstrap,"
Sullivan, Timmermann, White, *Journal of Finance* 54(5), 1647-1691, 1999.
<https://onlinelibrary.wiley.com/doi/abs/10.1111/0022-1082.00163>
White's Reality Check over 7,846 rules (incl. channel breakouts) on 100 years
of DJIA. BLL-era results survive the snooping adjustment in-sample (to 1986),
but in 1987-1996 out-of-sample even the best rule shows no significant
outperformance. Canonical citation for post-1980s decay in US equities.

"Technical Analysis Around the World," Marshall, Cahan, Cahan (SSRN working
paper, Massey University). <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1181367>
5,000+ rules on all 49 MSCI country indices: nothing significant after
data-snooping adjustment in any country; weak (not robust) evidence that
rules do better in emerging markets.

Supporting decay evidence (peer-reviewed): Yu, Nartea, Gan & Yao, *IREF*
2013 (five SE Asian markets, power weakening post-1997); Shynkevich, *Review
of Financial Economics* 2013 (Taiwan TRB rules fade in 1997-2007).

### 2.6 Emerging markets / India

- Ratner & Leal (1999), "Tests of Technical Trading Strategies in the
  Emerging Equity Markets of Latin America and Asia," *Journal of Banking &
  Finance* 23, 1887-1905. Ten emerging markets **including India**,
  1982-1995: after costs only Taiwan, Thailand, Mexico show robust
  profitability; India is not among the winners. (MA rules, not channels —
  but per Lukac-Irwin the signals are highly correlated.)
- **Verified gap: no rigorous academic study of Donchian/N-day-channel
  breakout rules specifically on Indian single stocks was found.** The
  closest India-specific rigorous evidence is the 52-week-high literature
  (section 3.3). This is a genuine hole — and an opportunity for an internal
  study.

---

## 3. Relationship to momentum

### 3.1 Breakouts vs 12-1 momentum ranking

A 12-1 cross-sectional rank orders stocks by realized return; a Donchian
breakout is a binary, own-history trigger. Differences that matter for the
NSE 500 stack: (a) breakouts are time-series signals; (b) breakouts are
path-dependent — a stock can have a high 12-month return yet sit far below
its high (post-crash rebound) or a modest return yet sit at a new high
(steady grinder); the second profile is what the 52-week-high literature
shows is better rewarded; (c) asymmetric-exit variants embed a trailing stop,
which a rank-and-rebalance portfolio lacks.

### 3.2 The 52-week-high effect — key validation of the Donchian upper band

"The 52-Week High and Momentum Investing," George & Hwang, *Journal of
Finance* 59(5), 2145-2176, 2004.
<https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2004.00695.x>

Ranks US stocks by **nearness to the 52-week high** (price / 52-week high =
position relative to the 252-day Donchian upper band). This ratio explains a
large share of Jegadeesh-Titman momentum profits and **dominates past-return
rankings** as a predictor; unlike standard momentum, 52-week-high profits
**do not reverse long-term**. Explanation: anchoring — traders under-react to
good news near the visible high (reluctant to buy "at the top"), so news
diffuses slowly. The single most important paper for this task: top-journal
evidence that a Donchian-band-derived continuous signal is a first-class
momentum predictor in single-stock equities.

Follow-ons (peer-reviewed):

- Liu, Liu & Ma (2011), *JIMF* 30, 180-204: profitable in 18 of 20 markets
  (significant in 10); independent of stock and industry momentum; no
  long-run reversal.
- Du (2008), *QREF* 48(1), 61-77: at the index level 52-week-high profits
  exist but DO reverse long-run — the stock-level result doesn't fully carry
  to indices.
- "Momentum Crashes and the 52-Week High," *Financial Analysts Journal*
  79(2), 2023: 52-week-high-based strategies mitigate the classic
  momentum-crash profile relative to return-ranked momentum.

### 3.3 India-specific 52-week-high evidence

- Raju, "The 52-Week High Effect and Momentum Investing: Evidence from
  India" (SSRN working paper, 2023, id 4587697). NOT peer-reviewed; details
  from indexed abstract only (SSRN blocked direct fetch): Indian equities
  Oct 2004 - Aug 2023; effect distinct and robust, survives size controls,
  weaker long-term reversals and more stable alpha than 12-1 momentum.
  Pull the full PDF and replicate before relying on magnitudes.
- A smaller peer-reviewed-tier Indian study (431 stocks, 2015-2023) found
  52-week-high beats return-momentum in mid-caps (~0.99% vs 0.74%/month) —
  modest journal quality, corroborating only.

**Synthesis:** the academically defensible way to use Donchian bands on NSE
500 is not the binary 20/55-day breakout (weak/decayed evidence in equities)
but the **continuous nearness-to-252-day-upper-band ratio as a ranking
feature**.

---

## 4. Practical uses beyond entries

- **Channel width as a volatility/regime proxy.** Width = (upper-lower)/mid
  is a crude range-based vol estimator (cousin of Parkinson/Garman-Klass).
  No dedicated peer-reviewed study found; for an academically grounded regime
  input use ATR/realized vol directly — the Turtles themselves sized with
  ATR, not width.
- **% of stocks at N-day highs as breadth.** Fraction of universe printing
  N-day (typically 252-day) highs minus lows = the classic Net New Highs /
  High-Low Index breadth family. Practitioner-grade only: **no rigorous
  peer-reviewed study establishing predictive power of net-new-highs breadth
  was found.** Treat as a monitoring/regime overlay, not an evidenced alpha
  source, until validated internally.
- **Channel position (0-100) as a continuous signal.**
  `(C - L_N) / (H_N - L_N)` is mathematically identical to raw stochastic %K
  over N days (and 100 minus Williams %R) — know this to avoid reinventing
  or double-counting a feature. At N=252 it inherits the George-Hwang
  evidence base; at short lookbacks it behaves as a mean-reversion
  oscillator with no comparable academic support.
- **Trailing exits / risk overlay.** The asymmetric short-exit-channel
  (Turtle 55/20, 20/10) is a systematic trailing-stop discipline; the FAJ
  2023 momentum-crash paper is the closest academic support that
  high-anchored signals with implicit exits soften momentum's left tail.

---

## 5. Claims that could NOT be verified — do not cite without further work

1. "Dunn & Hargitt's 1970 *Traders' Notebook* found the 4-week rule the best
   system tested" — repeated across practitioner sites; primary document not
   located. Unverified folklore.
2. "A 1990 *Financial Review* study of 23 systems (1976-1986) found channel
   breakout and MA crossover on top" — matches Lukac & Brorsen 1990 but only
   seen second-hand; confirm before citing numbers.
3. "Donchian channels work for commodities/FX but not stocks" — practitioner
   backtest claim (QuantifiedStrategies); cite the Park-Irwin survey's
   futures-vs-stocks asymmetry instead.
4. Raju (2023) India paper details — abstract-level only; pull the PDF.
5. No peer-reviewed paper was found testing the Turtle system verbatim on any
   equity universe, nor Donchian rules on Indian single stocks.

---

## 6. Bottom line

1. **Provenance is futures, not equities.** Strong evidence for raw N-day
   breakouts is in futures/FX, and even there the exact rules stopped working
   out-of-sample post-1985. In US equities, breakout profits failed the
   1987-1996 out-of-sample test after data-snooping adjustment.
2. **The equity-native descendant of the Donchian band is the 52-week-high
   ratio** — top-journal evidence, international replication, no long-run
   reversal at stock level, crash-mitigation properties, India-specific
   support (unrefereed).
3. **Keep the Turtle machinery, not the Turtle entry**: ATR inverse-vol
   sizing and channel-based trailing exits have a continuous line of support
   into modern academic TSM; the binary 20/55-day equity entry does not.
4. **Cheap internal wins**: % of NSE 500 at 252-day highs minus lows as a
   breadth/regime series (partially exists as `net_new_highs_pct`), and a
   52-week-high ranking replication vs the existing momentum signals — which
   would also fill a genuine gap in the published India literature.
