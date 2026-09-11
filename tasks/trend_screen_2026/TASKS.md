# Tasks

Owners: 👤 founder · 🤖 agent.

> **Universe note (👤 2026-09-11).** §1 and §5 were first run on a pure
> top-750 turnover rank. A rank is not a liquidity test — the 750th name
> traded ₹0.03cr/day in 2006 — so the whole chain was re-run on **top 500 AND
> above the turnover-scaled floor**, survivorship-free (1,716 names, 1,134 of
> which stop trading before 2026). Every §1 and §5 finding survived; the
> numbers below are quoted at their original top-750 values, with the clean
> top-500 values in §7. Nothing reversed sign or ordering.

## §1 — classifier hardening 🤖 — DONE 2026-09-11

Built `lib/features.py`: every rule's raw ingredients stored once per name per
month-end (173,039 rows, 2,163 names, top-750-by-turnover universe, 2006-2026),
so thresholds sweep in memory instead of re-scanning 2,914 price files per
configuration. Forward returns are always **excess over the same month's
cross-sectional mean**.

- [x] Sweep thresholds; check the ordering survives
- [x] Check month-to-month stability
- [x] Measure list churn

### Result 1 — the thresholds do no work, so stop tuning them

135 configurations (extended cut 10-30%, 200-day slope lookback 21/42/63,
above-52w-low 20/30/40%, near-52w-high 20/25/30%):

| | |
|---|---|
| ordering EXTENDED > LEADING > ADVANCING > BASING > WEAKENING holds | **135 of 135** |
| buy-vs-avoid 6m spread | median 6.8%, range **6.5% to 7.1%** |
| buy-list excess positive in all three eras | 135 of 135 |
| EXTENDED beats LEADING | **135 of 135**, median margin +4.2% |

No axis moves the spread by more than 0.3pp. The finding is not
threshold-dependent, which is the best possible outcome: pick defensible
defaults, freeze them, and never present a tuned number. Defaults kept at
ext 20% / slope 21 / above-low 30% / near-high 25%.

It also settles the PLAN's finding 2 far more strongly than one configuration
could: EXTENDED out-earns LEADING under **every** threshold set tried.

### Result 2 — confirmation filters make it worse on both axes

The obvious fix for a churny list is to require the state to persist. It fails:

| buy list rule | names | 3m | 6m | 12m | turnover |
|---|---|---|---|---|---|
| ≥1 month in state | 147 | +2.3% | +3.9% | +5.9% | 32% |
| ≥2 months | 71 | +2.0% | +3.6% | +5.4% | 39% |
| ≥3 months | 36 | +1.8% | +3.4% | +5.1% | 36% |
| ≥4 months | 21 | +1.7% | +3.1% | +4.8% | 35% |

Confirmation **costs return and raises turnover**. It costs return because
momentum decays with age-in-state; it raises turnover because a name now falls
off the list the moment it blinks, and has to re-earn its streak to come back.
You cannot filter your way to a stable buy list — the instability is real,
not a measurement artifact. No confirmation filter is used.

### Result 3 — EXTENDED is a tag, not a state

25% month-to-month persistence; **74% of EXTENDED runs last exactly one
month**. It is the best-performing condition and the least durable category.
Carry it as a tag on a LEADING name ("extended from the 50-day"), never as its
own list — a list whose members leave three weeks later cannot be browsed.

### Result 4 — the two lists behave nothing alike

| | buy list (LEADING+EXTENDED) | avoid list (WEAKENING+DOWNTREND) |
|---|---|---|
| median size | 146 names (21% of universe) | 296 names |
| monthly turnover | **32%** | **14%** |
| state persistence | LEADING 57% | DOWNTREND **84%** |
| median contiguous stay | 2 months | — |
| appearances lasting 1 month only | 36% | — |

Each month the buy list takes ~54 additions and ~40 removals. That is not a
browse-and-pick product; it is a portfolio service with real subscriber
workload. The avoid list is quiet by comparison and needs far less of the
subscriber.

### Result 5 — the churn is substantive, so removals must be acted on

Whether leaving the list matters was the open question. It does:

| from a month on the buy list | n | 3m | 6m | 12m |
|---|---|---|---|---|
| stayed on the list | 27,514 | +2.3% | +4.1% | +6.1% |
| dropped off | 14,343 | +0.3% | +1.2% | +1.5% |
| &nbsp;&nbsp;→ fell to ADVANCING | 12,682 | | +1.5% | +2.1% |
| &nbsp;&nbsp;→ fell to WEAKENING | 1,558 | | −0.9% | −3.0% |

Dropping off costs ~3pp over six months. The turnover is not cosmetic and a
subscriber who ignores removals gives back most of the edge.

### Result 6 — entering the list is weaker than being on it

| | 3m | 6m | 12m |
|---|---|---|---|
| the month a name **enters** the buy list (n=13,191) | +1.7% | +2.7% | +4.2% |
| **any** month a name is on the buy list (n=42,985) | +2.3% | +3.9% | +5.9% |

Fresh entrants underperform established members. Same direction as the
EXTENDED result, and the same warning: the product's instinct to feature
"new this month" would be featuring the weakest slice of the list.

## §2 — the 15-second read 🤖

- [ ] Card content, every line traceable to a classifier fact: state, months
      in it, distance from the 50 and 200, base depth and length, distance to
      pivot, relative strength, and the EXTENDED tag from §1 result 3.
- [ ] A "why it left" line for removals, given §1 result 5 — ADVANCING and
      WEAKENING are different messages and must not read the same.

## §3 — entry location 👤🤖

Settles the PLAN's open contradiction. §1 result 1 strengthened it: EXTENDED
beats LEADING under all 135 threshold sets, so "buy near the 50-day" is
selecting the weaker half on raw return.

- [ ] Conditional on LEADING, measure forward return **and R-multiple** for
      entry near the 50, inside the 50/100 band, and on a pivot breakout.
- [ ] Reuse `breakout_calls_2026` §4's exit ladder so the R comparison is
      like-for-like. Raw return and R can disagree — a pullback buys a tighter
      stop — and that disagreement is the actual answer.

## §4 — the avoid list, shipped first 🤖

Cheapest defensible claim in the product and the one §1 most supports: stable
(14% turnover, 84% persistence), large sample (59,540 observations), negative
in every era, and it does not require the subscriber to pick well.

- [ ] Ship criteria, refresh cadence, and the copy that states what it is:
      a claim about a population, never a prediction about one stock.

## §5 — ranking and trim 🤖 — DONE 2026-09-11

- [x] Test 10 candidate ranks against the list average
- [x] Top-N sensitivity, era stability, deflation, churn

### Result 1 — ranking works, and it is one factor, not ten

Top 20 of the buy list each month, 6-month excess, against a whole-list
average of **+3.9%**:

| rank by | 3m | 6m | 12m | vs list |
|---|---|---|---|---|
| % above the 200-day | +4.9% | **+8.4%** | +11.8% | +4.5% |
| % above the 52-week low | +5.4% | **+8.4%** | +10.6% | +4.5% |
| % above the 50-day | +5.3% | +8.2% | +12.8% | +4.3% |
| 50/100 separation | +4.5% | +8.0% | +11.8% | +4.1% |
| 200-day slope | +4.1% | +6.5% | +9.0% | +2.7% |
| 6-month return | +3.2% | +5.8% | +9.2% | +1.9% |
| 12-month return | +3.6% | +5.5% | +6.8% | +1.6% |
| **months in state** | +1.2% | +2.7% | +3.0% | **−1.1%** |

**8 of 10 candidates beat the list.** They also correlate 0.73-0.89 with one
another — these are one factor, *how far the name has already run*, measured
four ways. Deflation says the same: the best (+8.4%) does not clear the Gumbel
expected maximum of 10 draws (+10.2%), so the family effect is what is real
and no single ranker should be called optimal.

**Months in state is the only negative**, and it is worst in the recent era
(−1.6%). §1 result 2 predicted exactly this. Two independent tests now say
time-in-trend is a liability, not a virtue.

### Result 2 — the cut is monotone, which is what makes it credible

| cut | 6m | 12m | hit rate 6m |
|---|---|---|---|
| top 10 | +10.5% | +13.5% | 47% |
| top 20 | +8.4% | +11.8% | 47% |
| top 30 | +7.7% | +11.8% | 48% |
| top 50 | +7.0% | +10.2% | 48% |
| top 100 | +6.1% | +9.0% | 48% |
| whole list (147) | +3.9% | +5.9% | 47% |

A clean gradient at every cut, not a cliff at one lucky N.

### Result 3 — % above the 52-week low is the pick

Not because it scores highest — it ties — but because it is the most stable
where it matters:

| rank by | 2006-2012 | 2013-2019 | 2020-2026 | worst era |
|---|---|---|---|---|
| % above 52-week low | +7.5% | +10.3% | **+7.1%** | **+7.1%** |
| % above the 200-day | +9.1% | +11.6% | +4.1% | +4.1% |
| 50/100 separation | +10.0% | +10.9% | +2.8% | +2.8% |
| months in state | +4.5% | +5.0% | −1.6% | −1.6% |

It also churns least (43% vs 50% for the 200-day ranker) at identical return.
Freeze it; do not re-tune.

### Result 4 — trimming raises return and raises churn, and that is the product decision

| list | size | turnover | median stay | 6m excess |
|---|---|---|---|---|
| whole buy list | 147 | 32% | 2 months | +3.9% |
| top 30 | 30 | 43% | 1 month | +7.7% |
| top 20 | 20 | 43% | 1 month | +8.4% |

Trimming doubles the excess return and pushes nearly half the list over every
month, with the median name present for a single month. There is no cut that
gets both.

**So rank the list; do not trim it.** The founder's product is browse-and-read
— a subscriber opens a chart and reads a structure summary — and 147 names
sorted by strength is an ordinary screener, not an unreadable wall. Sorting
delivers the ranking benefit to anyone who starts at the top, without shipping
a fixed 20-name list that replaces half its members monthly and implies an
act-now promise the turnover cannot support. A "strongest right now" ribbon
over the top names is fine as a view; it must not be presented as a buy list.

### Result 5 — the hit rate does not move, at any cut

47-48% at every N from 10 to the whole list. Trimming raises the mean and
leaves the odds for any one name a coin flip. **The basket framing from PLAN
finding 1 survives §5 intact** and is now the most-tested claim in this task:
the list beats the market, a name off the list does not reliably beat
anything.

## §6 — delivery 👤

- [ ] Refresh cadence, how removals are communicated, and what the subscriber
      sees when a name leaves.
- [ ] The basket framing from PLAN finding 1 — every bucket has a hit rate
      below 50%, so the copy has to sell a population, not a stock.


## §7 — expectancy and the portfolio question 🤖 — DONE 2026-09-11

All figures on the clean universe (top 500 + floor, survivorship-free).

### Trade expectancy — the stop inherited from the breakout work was wrong

The first run used an 8% hard stop carried over from `breakout_calls_2026` and
produced a 27% win rate. That stop does not fit this entry: at entry a LEADING
name sits a **median 24% above its own 150-day**, so an 8% stop fires long
before the trail can engage — 58% of trades died on it and the median trade
*was* the stop. In the breakout study 8% is a structural level below a tight
base; here it is arbitrary and tighter than the stock's own noise.

Exit = 150-day trail. Entry = next open after a month-end on the list.

| list | stop | trades | win | avg win | avg loss | ratio | exp/trade | per-era |
|---|---|---|---|---|---|---|---|---|
| whole list | 15% | 8,452 | 35% | +46.6% | −10.5% | 4.43 | +9.76% | +4.2 / +8.1 / +15.3 |
| whole list | none | 7,834 | 39% | +46.7% | −11.1% | 4.19 | +11.38% | +6.3 / +9.3 / +16.7 |
| top 50 | none | 3,634 | 40% | +54.0% | −13.3% | 4.06 | +13.81% | +8.0 / +12.2 / +20.3 |
| **top 20** | none | 1,785 | **40%** | +60.8% | −14.9% | 4.08 | **+15.57%** | +10.0 / +13.9 / +22.6 |

Widening the stop raises win rate and expectancy but *lowers* R-multiple,
because R divides by initial risk. Which metric governs depends on sizing:
risk-sized positions → R; roughly equal-weight positions → expectancy. A
subscriber buys similar amounts per name, so expectancy is the number here.

**This beats the breakout pattern it came from.** Same exit ladder, same
store: VCP breakout gave 1.06R on 1,751 trades; the trend screen gives
+11-16% per trade on 7,800. The base-anatomy detector — fractal pivots,
contraction counts, volume dry-up, tightness — is not earning its complexity.

### As a portfolio — one gate away

Equal-weight 1/N (risk sizing is undefined without a hard stop), daily
mark-to-market, 10% ADV participation cap, `breakout_calls_2026`'s book
simulator unchanged.

| config | CAGR | max DD | Sharpe | era Sharpes |
|---|---|---|---|---|
| **top 50, trail only, 25 slots** | **22.4%** | 48.6% | **0.83** | 0.77 / 0.55 / 1.16 |
| top 50, trail only, 20 slots | 21.6% | 50.1% | 0.78 | 0.78 / 0.52 / 1.06 |
| whole list, 15% stop, 20 slots | 20.6% | 49.7% | 0.74 | 0.61 / 0.41 / 1.23 |

Against `breakout_calls_2026` §0's gates: **P1 passes** (22.4% ≥ 18%), **P3
passes** (0.83 ≥ 0.80), **P4 passes** (all three eras ≥ 0.50). **P2 fails** —
48.6% drawdown against a −35% limit, and it is the only gate still failing.

Reference points: NIFTY 500 11.4% / −64.3% / 0.32; the breakout book 16.0% /
−30.5% / 0.64; production MM/OM25 ~20% / −31%. This earns more than production
and draws down far deeper.

The clean universe **improved** the portfolio (22.4% / 0.83 against 19.4% /
0.78 on the dirty one). Removing the illiquid tail removed noise, not signal.

### Capacity — and a correction

The first capacity run showed 7.8% CAGR at ₹25cr and looked like the breakout
book's death at size. It was an artifact: entries had a median ADV of ₹1.2cr
in 2006-2012 against ₹17.0cr in 2020-2026, so a 2026-sized book was being
tested against 2006 liquidity. Measured over the period a book would launch
into:

| capital | 2016-2026 | 2020-2026 |
|---|---|---|
| ₹1cr | 24.5% | 28.8% |
| ₹10cr | 18.6% | 28.4% |
| ₹25cr | **14.8%** | **23.2%** |
| ₹100cr | 7.7% | 12.8% |

**This is the real difference from the breakout work**, whose edge lived in
microcaps and died at ₹25cr. Capacity is no longer the binding constraint.

### What is left

Drawdown, and nothing else. Every other gate passes. The founder's breadth
idea aims straight at it — with the caveat that the naive version (200-day
index regime overlay) already *hurt* on the breakout book, Sharpe 0.65 → 0.56.
Breadth is a different signal and deserves its own test, not an assumption.
