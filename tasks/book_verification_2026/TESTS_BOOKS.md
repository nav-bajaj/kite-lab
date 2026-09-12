# TESTS_BOOKS — behavioural tests for `mm_v1` and `om25_v4`

Spec: `tasks/mm_rebuild/MECHANICS.md` (the locked rules, lock date 2026-09-12) plus
`tasks/mm_rebuild/RESULTS.md` §23 (a stopped name is sold and replaced, never rebought on the
same action day; engine switch `stop_reentry_block=1`).

Under test: `scripts/rebuilt_books.py` (LOCKED configs + assembly), `scripts/run_rebuilt_book.py`
(the runner), `scripts/_clean_engine.py::run_strategy` (the engine) and
`data_pipeline/strategies/*` (score, regime, sizing, calendar, sectors), as they behave on the
local master store (`data/master`).

## Data each test uses

| Name | What it is |
|---|---|
| **runner output** | A fresh run of `scripts/run_rebuilt_book.py --book <b> --start 2010-01-01`: `<b>_equity.csv`, `<b>_trades.csv`, `<b>_exits.csv`, `<b>_signals.csv`, `metrics.json`, `backtests/baseline/momentum_*.csv`. |
| **store context** | An independent re-assembly of the same inputs (price-return panels, point-in-time membership, score function, regime series, inverse-vol weight function, sector map, monthly signal dates) built by the same library calls `scripts/rebuilt_books.build_and_run` makes — used to re-derive what the engine *should* have done. |
| **replay** | A per-rebalance re-derivation. At every action day the state (holdings, cash) is taken from the runner's own trades and equity, then entrants, exits, peaks and share counts are recomputed from the store context and compared with what the engine actually did. Each rebalance is therefore judged independently: one bad month does not cascade. |
| **synthetic panel** | A small deterministic price panel driven straight into `run_strategy`, used where a rule is easier to prove in isolation (perturbation, unlabelled sectors). Same pattern as `tests/test_engine_hooks.py`. |

Both books are checked by every runner-output test unless the rule is book-specific.

---

## A — Selection

### A-01 Entrants come only from the top 45 by rank
- **Rule** — "entrants are drawn by rank from the top 45 (`fill_from_buffer`, 2026-09-11)"; in a
  bear, "entries capped so the book holds <= 15 names", so the draw depth is `bear_n + buffer` = 35.
- **Check** — replay: at each action day rebuild the ranking the engine used (score at the signal
  date, ordered `nlargest(45)` then the remainder descending, restricted to
  members-as-of-signal-date *or* current holdings), take the first `top_n_at_date + 20` and assert
  every BUY symbol is in that set.
- **Data** — runner trades + store context (score, membership).
- **Pass** — zero entrants outside the pool, on every action day, for both books.
- **Failure means** — the engine is buying outside the sanctioned buy list: either the buffer draw
  or the membership filter is wrong, and published holdings are not the book's holdings.

### A-02 Entrants are Nifty 250 members as of the signal date
- **Rule** — "Universe: NIFTY LARGEMIDCAP 250, point-in-time membership".
- **Check** — every BUY symbol is in `members_asof(nifty250, signal_date)`. Separately: no symbol
  whose first membership window opens *after* the signal date appears in that date's score.
- **Data** — runner trades + `data/master/membership/nifty250.csv`.
- **Pass** — zero non-member entrants; zero future-dated names in any sampled score.
- **Failure means** — look-ahead through the universe (buying a name the index had not yet added),
  the single largest source of fake backtest return.

### A-03 No entrant lacks the minimum history
- **Rule** — "Eligibility: >= 219 priced sessions in the window" (MM), ">= 220" (OM25).
- **Check** — for every entrant, count non-NaN returns in the score window
  (`[signal-272, signal-21]` sessions) and assert it reaches `min_obs`.
- **Data** — runner trades + returns panel.
- **Pass** — zero entrants below `min_obs`.
- **Failure means** — the score is being computed on too little history, so a recent listing can
  out-rank a real 12-month trend.

### A-04 The score window ends 21 sessions before the signal date
- **Rule** — "return over the 252 sessions ending 21 sessions before the signal date".
- **Check** — triple the returns of the last 21 sessions before the signal date and assert the
  score at that date does not change.
- **Data** — returns panel (real), one sampled signal date.
- **Pass** — scores identical.
- **Failure means** — the 12-1 skip is not being applied; the book is buying one-month reversal
  instead of twelve-month momentum.

### A-05 MM's score is vol-adjusted momentum with the 5% vol floor
- **Rule** — "vol-adjusted momentum: return over the 252 sessions ... divided by annualised daily
  vol over the same window, floored at 5%".
- **Check** — recompute `((1+r).prod()-1) / max(std*sqrt(252), 0.05)` over the window from the
  returns panel and compare with the assembled score at sampled signal dates. Also assert no
  entrant's window vol is below the floor (the floor must never manufacture a buy).
- **Data** — store context + returns panel + runner trades.
- **Pass** — scores match to 1e-9; zero entrants whose vol was floored.
- **Failure means** — either the score is not the locked score, or a stale/illiquid series is
  ranking high purely because the floor rescued a near-zero denominator.

### A-06 OM25's score is the 50/50 rank blend
- **Rule** — "rank blend: ... **weight fixed at 50/50**".
- **Check** — rebuild the momentum leg and the capture leg with the LOCKED arguments, take
  `0.5*rank_pct(mom) + 0.5*rank_pct(cr)` over the intersection, compare with the assembled score.
- **Data** — store context, sampled signal dates.
- **Pass** — identical series.
- **Failure means** — the blend weight drifted, or one leg is silently dropping names.

### A-07 The blend applies the return filter; MM does not
- **Rule** — OM25: "positive window return required". MM's eligibility is "no other filter".
- **Check** — for OM25, every scored name (and therefore every entrant) has a positive
  252-session window return; for MM, scored names with a non-positive window return exist.
- **Data** — store context + returns panel + runner trades.
- **Pass** — OM25: zero non-positive names scored; MM: at least one.
- **Failure means** — the two books are not the two books: either OM25 lost its quality filter or
  MM acquired one, which changes both records.

### A-08 Entrants are priced, not stale
- **Rule** — implied by "priced sessions" eligibility; the panel is forward-filled, so a delisted
  or suspended name keeps passing a naive count.
- **Check** — every entrant has a real row in its own `panels/pr/<SYM>_day.csv` on the signal
  date, and fewer than 25% zero-return sessions in the score window.
- **Data** — runner trades + per-symbol price files.
- **Pass** — zero entrants without a traded row on the signal date; max zero-return share < 0.25.
- **Failure means** — the book is buying forward-filled ghosts; the entry price is not a price
  anyone could have traded.

### A-09 The signals file reproduces the ranking
- **Rule** — the signals CSV is the published rebalance view; it must be the ranking the engine used.
- **Check** — per signal date: ranks are 1..N contiguous, score is non-increasing with rank, depth
  is 45 in a bull and 35 in a bear, the regime label matches the recomputed regime, and the set of
  names equals the engine's own top-45 (`nlargest`) set.
- **Data** — runner signals CSV + store context.
- **Pass** — all four structural checks; identical sets.
- **Failure means** — the dashboard shows a different buy list from the one that traded. Note the
  known tie-ordering gap: `scripts/rebuilt_books.py` builds the CSV with
  `sort_values(ascending=False).head(45)` while the engine uses `scores.nlargest(45)`, and the two
  order ties differently.

---

## B — Rebalance timing

### B-01 Signal dates are the first trading day of each month
- **Rule** — "close of the first trading day of each month"; "one order day a month".
- **Check** — the signal dates in the signals CSV equal `monthly_on_or_after(calendar, 1)`
  restricted to the run window, and each is the first calendar-ordered session of its month.
- **Data** — runner signals CSV + store calendar.
- **Pass** — exact set equality.
- **Failure means** — the cadence is not the locked cadence; live rebalances would fall on the
  wrong day.

### B-02 Trades execute on the next session and on no other day
- **Rule** — "orders at the next session's trade price".
- **Check** — every trade date is the session immediately after a signal date; the set of trade
  dates is a subset of `{next_session(sd)}`; no trade falls on a signal date itself.
- **Data** — runner trades + calendar + signals CSV.
- **Pass** — zero trade dates outside the mapped exec set.
- **Failure means** — same-close execution (a one-day look-ahead worth several points of CAGR) or
  an unscheduled action day.

### B-03 One action day a month, exits and entries together
- **Rule** — "**one order day a month**; no weekly action"; "a stopped name is sold and replaced".
- **Check** — group trades by calendar month: exactly one distinct trade date per month that has
  any trade. On dates with both sides, SELLs and BUYs carry the same date.
- **Data** — runner trades.
- **Pass** — zero months with more than one action day.
- **Failure means** — the book is trading more often than the record assumes; turnover and
  slippage in the published figures are understated.

### B-04 No weekly machinery is active
- **Rule** — "no weekly action"; "no position is ever trimmed" (§19).
- **Check** — trade reasons are a subset of `{entry, rank, atr_stop}`: no `rank_weekly`, no `trim`,
  no `regime_bear`, no `regime_topup`.
- **Data** — runner trades.
- **Pass** — exact subset.
- **Failure means** — an optional engine hook has been switched on and the book is no longer the
  locked book.

---

## C — Exits

### C-01 Exits are only rank or stop, one SELL each
- **Rule** — the only exits in the spec are the rank exit and the 20% trailing stop.
- **Check** — `exits.reason` values are `{rank, atr_stop}`; the exits row count equals the SELL
  trade count; every exit row pairs one-to-one with a SELL at the same date and symbol.
- **Data** — runner exits + trades.
- **Pass** — exact.
- **Failure means** — an undocumented exit path, or exits and trades disagreeing (the dashboard
  reads both).

### C-02 Rank exits are exactly the holdings below the buffer
- **Rule** — "a holding exits at the monthly review if its rank falls below 45 (25 + buffer 20)";
  bear: "exits at rank 35".
- **Check** — replay: the keep set is the membership-filtered ranking's first 45 (in a bear the
  score itself is truncated to 35, so the keep set is those 35); expected rank exits are the
  holdings outside it, less the names already stopped that day. Compare with the engine's `rank`
  SELLs, at every action day.
- **Data** — runner trades + store context.
- **Pass** — zero mismatched action days for both books.
- **Failure means** — either names are being held past their exit rank (the drawdown control is
  not working) or sold early (unnecessary turnover).

### C-03 Stop exits are exactly the 20%-from-peak breaches at the signal close
- **Rule** — "20% trailing from the position's peak, checked at the monthly signal, executed next
  session".
- **Check** — replay: track each position's peak, then at every action day the expected stop set is
  `{s : close[signal_date, s] / peak[s] - 1 < -0.20}` over current holdings. Compare with the
  engine's `atr_stop` SELLs.
- **Data** — runner trades + close panel.
- **Pass** — zero mismatched action days.
- **Failure means** — the only hard risk control in the book is not firing when it should, or
  firing when it should not.

### C-04 The peak is the running peak of closes since entry
- **Rule** — "the position's peak" (MECHANICS); read as the running peak of closes since entry.
- **Check** — two reconstructions of the peak: (a) **engine convention** — `max(entry trade price,
  closes from the session after entry through the action day)`; (b) **literal convention** —
  the same but with the entry session's own close folded in. Assert both reproduce every stop exit.
- **Data** — runner trades + close panel.
- **Pass** — both conventions reproduce the engine.
- **Failure means** — if (a) passes and (b) fails, the engine's peak excludes the entry-session
  close (`scripts/_clean_engine.py:344-349` runs the peak update before the entry block, so the
  entry day's close is folded in only on the following session). That is a one-day off-by-one, not
  a rule the founder has signed: it belongs in RESULTS.md as a rule question, not a silent fix,
  because changing it moves the locked figures.

### C-05 The stop is never triggered between signal dates
- **Rule** — "checked at the monthly signal".
- **Check** — walk every session: count days where a held position's close is more than 20% below
  its peak; assert none of them produced a trade (trades exist only on action days).
- **Data** — runner trades + close panel.
- **Pass** — zero trades outside the action-day set while breaches exist (the real books breach on
  well over a thousand non-action days, so this is a live check, not a vacuous one).
- **Failure means** — the stop has become intraperiod; the book would trade far more often than
  the record and the "one order day" promise would be broken.

### C-06 Stop exits execute next session at the trade-panel price
- **Rule** — "checked at the monthly signal, executed next session".
- **Check** — every `atr_stop` SELL is dated on the exec session of the signal date that triggered
  it, and priced at the trade panel (OHLC/4) value for that date and symbol.
- **Data** — runner trades + trade panel.
- **Pass** — exact for every stop exit.
- **Failure means** — the stop is being filled at a price no one could get (the signal close), or
  on the wrong day.

### C-07 A stopped name is never bought back on the same day
- **Rule** — founder 2026-09-12 (§23): "It makes no sense to buy and sell something on the same
  day. Either we hold it or sell and replace." `stop_reentry_block=1`.
- **Check** — zero `(date, symbol)` pairs carrying both a BUY and a SELL; and for every stop exit,
  no BUY of that symbol on that date.
- **Data** — runner trades.
- **Pass** — zero pairs, both books.
- **Failure means** — the change the founder signed on 2026-09-12 is not in the run; the
  rebalance view will show sell-and-rebuy pairs again and each costs two slippage legs.

### C-08 The block lasts exactly one entry date
- **Rule** — `stop_reentry_block=1`: "a stopped name is ineligible for the next 1 entry dates".
- **Check** — replay: apply the block for one entry date when re-deriving entrants (A-01/D-01
  reconcile exactly only if the block length is 1); plus, on the real books, at least one name is
  stopped and then re-entered at the *following* action day (a two-month block would forbid that).
- **Data** — runner trades + replay.
- **Pass** — the replay reconciles with block = 1 and at least one next-month re-entry exists.
- **Failure means** — `k` drifted to 2 (which the §23 grid shows costs both books) or back to 0.

---

## D — Sizing and cash

### D-01 Golden replay: entrants and share counts
- **Rule** — the whole entry path: buffer draw, membership, stop block, sector cap, slot cap,
  inverse-vol target, 10% cap, the two-pass allocation.
- **Check** — at every action day, using the engine's own pre-entry holdings and cash, re-derive
  the entrant list and the exact share count for each entrant and compare with the trades.
- **Data** — runner trades + equity (start-of-day cash) + store context.
- **Pass** — zero mismatched action days for both books.
- **Failure means** — this is the single most informative test in the suite; a failure localises to
  whichever narrow test (A-01, C-07, E-01, D-02, D-03) also fails. If only D-01 fails, the
  allocation arithmetic itself moved.

### D-02 No entry weight exceeds 10% of the book
- **Rule** — "inverse-volatility ... capped at 10%".
- **Check** — for every action day, each entrant's total BUY notional divided by the book value at
  that rebalance is <= 0.10 (+50 bp tolerance for share rounding and the slippage leg).
- **Data** — runner trades + equity.
- **Pass** — no entry weight above 10.5%.
- **Failure means** — the cap is not binding; single-name risk is larger than the record assumes.

### D-03 Entry weights are inverse-volatility from returns up to the signal date
- **Rule** — "inverse-volatility across the intended book (63-day vol), capped at 10%".
- **Check** — at each action day, the target weight map for `holdings + entrants` is proportional
  to `1 / std_63` with the 10% cap and renormalisation; assert the weight ordering across entrants
  is the reverse of their 63-day vol ordering, and that the map sums to 1.
- **Data** — store context (weight function) + runner trades.
- **Pass** — rank agreement on every action day with more than one entrant.
- **Failure means** — sizing has reverted to equal weight or is reading the wrong vol window.

### D-04 Sizing uses no information after the signal date
- **Rule** — "The entry executes the next session, so sizing never sees the entry day."
- **Check** — recompute the weight map from a returns panel truncated at the signal date and
  compare with the map from the full panel, on sampled real signal dates.
- **Data** — returns panel.
- **Pass** — identical to 1e-12.
- **Failure means** — position sizes are set with tomorrow's volatility.

### D-05 Cash never goes negative, and is small in a full bull book
- **Rule** — "residual cash tolerated" (bear); a 25-name bull book should be close to fully invested.
- **Check** — `equity.cash >= 0` every day; on days with 25 holdings, the median cash share is
  under 2% and the maximum under 15%.
- **Data** — runner equity.
- **Pass** — no negative day; median cash share < 0.02.
- **Failure means** — negative cash is leverage the book does not have; a large cash share with a
  full book means the allocator is failing to deploy and the return is understated.

### D-06 Equity equals cash plus marked holdings, every day
- **Rule** — bookkeeping; the equity curve is the published record.
- **Check** — replay shares from the trades, then for every session assert
  `pv == cash + sum(shares * close)` using the engine's own convention (the equity row is written
  before that day's trades).
- **Data** — runner equity + trades + close panel.
- **Pass** — max absolute error 0 (integer shares, exact arithmetic).
- **Failure means** — the equity curve and the trade log describe different portfolios; every
  published figure derives from the former and every holdings view from the latter.

### D-07 No position is ever partially sold or trimmed
- **Rule** — "no position is ever trimmed to make room (trimming sells the winners, §19)".
- **Check** — every SELL's share count equals the full holding at that moment; no trade carries
  `reason == 'trim'`.
- **Data** — runner trades.
- **Pass** — zero partial sells, zero trims.
- **Failure means** — `trim_to_target` is on, which the research explicitly rejected.

### D-08 No held position is topped up
- **Rule** — "positions drift, never resized".
- **Check** — no BUY for a symbol that was held at the open of that action day and survived that
  day's exits. (Two BUY rows for the same *new* entrant on one day are the allocator's two passes
  and are allowed.)
- **Data** — runner trades.
- **Pass** — zero top-ups.
- **Failure means** — the book is being rebalanced back to target, which changes its character and
  its turnover.

### D-09 Costs and prices
- **Rule** — "net of 20 bps slippage each way"; "orders at the next session's trade price";
  initial capital Rs 10,00,000.
- **Check** — `slippage == 0.002 * notional` on every row, both sides; `price` equals the trade
  panel (OHLC/4) value at that date and symbol; the first equity row is 10,00,000 in cash.
- **Data** — runner trades + equity + trade panel.
- **Pass** — exact on all three.
- **Failure means** — the cost model in the published record is not the cost model of the run.

---

## E — Sector cap

### E-01 At most 5 names per labelled sector after any rebalance
- **Rule** — "at most 5 names per NSE sector at entry (21 sectors)".
- **Check** — replay holdings after every action day, count by `sector_v2` label, assert the
  maximum is <= 5.
- **Data** — runner trades + `data/static/sectors/sector_v2_lookup.csv`.
- **Pass** — maximum sector count 5 for both books.
- **Failure means** — concentration risk the record does not price; a single-sector drawdown would
  be worse than the backtest.

### E-02 The cap is applied to entrants in rank order
- **Rule** — the cap skips entrants; it does not reorder the buy list.
- **Check** — replay: when a sector is full, the *lower*-ranked candidate is the one dropped and
  the next eligible candidate by rank takes the slot; D-01's exact reconciliation is the assertion.
- **Data** — replay.
- **Pass** — D-01 reconciles with the rank-order cap implementation.
- **Failure means** — the cap is dropping the wrong names, so the book is not the top-ranked
  sector-capped book.

### E-03 Unlabelled names are unconstrained, and the map is the 21-sector scheme
- **Rule** — "21 sectors; historical labels in `sector/`"; names with no label cannot be capped.
- **Check** — synthetic panel: with `sector_of` covering only some symbols, more than `sector_cap`
  unlabelled names can be held simultaneously. On the real map: exactly 21 distinct `sector_v2`
  values, and >= 95% of traded symbols labelled.
- **Data** — synthetic panel + sector lookup + runner trades.
- **Pass** — unlabelled names are not blocked; 21 sectors; coverage >= 0.95.
- **Failure means** — either the cap silently lumps every unlabelled name into one bucket (over-
  constraining) or the label file has drifted off the NSE scheme.

---

## F — Regime

### F-01 The regime is NIFTY 100 ROC31, 3-day confirmation, lagged one session
- **Rule** — "NIFTY 100 31-session rate of change, sign, 3-day confirmation to flip, decided from
  the prior close".
- **Check** — recompute independently from `data/master/benchmarks/NIFTY_100.csv`: `roc = c/c.shift(31)-1`,
  flip to bear only after 3 consecutive `roc <= 0` readings and back only after 3 consecutive
  `roc > 0`, then `shift(1)`; compare with the assembled series over the whole calendar and with
  the `regime` column of the signals CSV.
- **Data** — benchmark CSV + store context + runner signals CSV.
- **Pass** — zero mismatched sessions; zero mismatched signal-date labels.
- **Failure means** — the only exposure control in either book is reading a different state from
  the one documented, so the bear rules fire at the wrong times.

### F-02 Bull books hold at most 25 names
- **Rule** — "up to 25 names".
- **Check** — after every bull action day the holding count is <= 25; the equity series never
  exceeds 25.
- **Data** — runner trades + equity.
- **Pass** — max 25.
- **Failure means** — the slot cap is not binding; weights and the record no longer line up.

### F-03 Bear entries are capped so the book holds at most 15
- **Rule** — "entries capped so the book holds <= 15 names".
- **Check** — on a bear action day, the holding count after entries is <= `max(15, count after that
  day's exits)`: the cap restricts *entries*, it never forces a sale.
- **Data** — runner trades + store context (regime).
- **Pass** — zero violations.
- **Failure means** — the book keeps adding risk into a downtrend, which is what the bear rule
  exists to stop.

### F-04 The bear exit rank is 35
- **Rule** — "exits at rank 35".
- **Check** — on bear signal dates the scored depth (and hence the signals CSV depth and the keep
  set) is exactly `bear_n + bear_buffer` = 35, not 45.
- **Data** — runner signals CSV + store context.
- **Pass** — every bear signal date has depth 35; every bull date 45.
- **Failure means** — the bear tightening is absent (or applied in a bull), so churn and holding
  discipline are both wrong.

### F-05 A bear runs the book down only as positions exit
- **Rule** — "after a bear the book rebuilds over the following rebalances as positions exit";
  "the top names stay fully sized; residual cash tolerated".
- **Check** — no trade carries `reason == 'regime_bear'` (no pro-rata de-risking); on each bear
  action day the holding count falls only by that day's exits; holdings above 15 at the onset of a
  bear are not sold down.
- **Data** — runner trades + equity + regime.
- **Pass** — zero forced-sale trades; holding counts consistent with exits alone.
- **Failure means** — `bear_exposure` has been wired in, which sells the winners — the behaviour
  §19 rejected.

### F-06 Bear entrants keep full inverse-vol size
- **Rule** — "the top names stay fully sized".
- **Check** — on bear action days, entrant target weights equal the unscaled inverse-vol weights
  (no `target_exposure` multiplier). D-01's exact reconciliation on bear dates is the assertion.
- **Data** — replay.
- **Pass** — D-01 reconciles on every bear action day.
- **Failure means** — entrants are being sized down in a bear, which is not the locked rule and
  would flatten the recovery.

---

## G — Look-ahead

### G-01 A score at t does not move when data after t is removed
- **Rule** — "every input used on signal date t is known at the close of t or earlier".
- **Check** — recompute the book's score at sampled real signal dates from a returns panel
  truncated at t; compare with the full-panel score.
- **Data** — returns panel, several signal dates across the history.
- **Pass** — identical series.
- **Failure means** — the published history is not reproducible in real time.

### G-02 Inverse-vol weights at t do not move when data after t is removed
- See D-04; listed here as the sizing leg of the same invariant.

### G-03 The regime at t does not move when the index file is truncated at t
- **Rule** — "decided from the prior close".
- **Check** — write the NIFTY 100 series truncated at t to a temp file, recompute `roc_regime`, and
  compare the value at t with the full-history value, on sampled dates.
- **Data** — benchmark CSV.
- **Pass** — identical booleans.
- **Failure means** — the confirmation hysteresis is peeking forward; bear calls in the record
  could not have been made on the day.

### G-04 Prices after the execution date cannot change earlier trades
- **Rule** — the general no-look-ahead invariant, tested end-to-end through `run_strategy`.
- **Check** — synthetic panel: run the engine, then multiply every close and trade price strictly
  after one execution date E by 1.5 and re-run; assert every trade dated on or before E is
  identical (date, symbol, side, shares, price).
- **Data** — synthetic panel.
- **Pass** — byte-identical trade prefix.
- **Failure means** — some engine input is reading forward; every figure in the record is suspect.

### G-05 No stop decision depends on the execution-day close
- **Rule** — the stop is decided at the signal close; the order is placed before the execution
  session trades.
- **Check** — reconstruct the peak *excluding* the execution-day close and assert the resulting
  stop set still equals the engine's, on every action day of both books.
- **Data** — runner trades + close panel.
- **Pass** — zero differences.
- **Failure means** — a live dependency on the execution day's close. Structurally the engine does
  fold the execution-day close into the peak before the check
  (`scripts/_clean_engine.py:344-349` runs before the stop check at `:505`), so this test is the
  materiality guard on a latent look-ahead rather than proof that it cannot happen. If it ever
  fires, the fix is to evaluate the peak as of `signal_date`.

---

## H — Outputs and bookkeeping

### H-01 metrics.json carries the LOCKED config
- **Rule** — the run must be the locked book: `lock_date` 2026-09-12, `stop_reentry_block` 1,
  every one of the 9/10 parameters as in MECHANICS.
- **Check** — `metrics.json["config"] == scripts.rebuilt_books.LOCKED[book]`, and the LOCKED dict
  itself matches MECHANICS (already pinned by `tests/test_rebuilt_books_wiring.py`).
- **Data** — runner metrics.json.
- **Pass** — exact dict equality.
- **Failure means** — a research override reached a production run.

### H-02 metrics.json tail values match the run
- **Check** — `holdings` and `cash_pct` equal the last equity row; `regime_today` equals the
  recomputed regime on the last session; `start`/`end` match the equity range.
- **Data** — runner metrics.json + equity + regime.
- **Pass** — exact.
- **Failure means** — the admin panel's "regime today" and holdings count are decorative.

### H-03 The DB-facing trade file reconciles with the runner's trades
- **Rule** — `backtests/baseline/momentum_*.csv` is what `sync_service` loads into Postgres.
- **Check** — `momentum_trades.csv` has the same row count and the same
  `(date, symbol, side, shares, price, notional, slippage)` values as `<book>_trades.csv`.
- **Data** — runner outputs.
- **Pass** — exact.
- **Failure means** — the dashboard's trade history is not the backtest's trade history.

### H-04 The DB-facing equity file reconciles
- **Check** — `momentum_equity.csv.portfolio_value` equals `equity.pv` session for session;
  `drawdown` equals `pv / pv.cummax() - 1`; the benchmark column is carried through.
- **Data** — runner outputs.
- **Pass** — exact to 1e-9.
- **Failure means** — the published curve and drawdown differ from the run's.

### H-05 The DB-facing holdings file reconciles with the replayed book
- **Check** — `momentum_holdings.csv` symbols and share counts equal the positions left open after
  replaying every trade.
- **Data** — runner outputs.
- **Pass** — exact.
- **Failure means** — the "current holdings" view is wrong, which is the one screen a client acts on.

### H-06 The DB-facing metrics file reconciles
- **Check** — every numeric field of `momentum_metrics.csv` equals `metrics.json["result"]`.
- **Data** — runner outputs.
- **Pass** — exact.
- **Failure means** — two published sets of headline numbers.

### H-07 The run reproduces the §23 reference figures
- **Rule** — §23 decision line: MM 2010-26 23.5% / −26.3%; OM25 v4 2010-26 22.6% / −28.3%
  (runner convention, `stop_reentry_block=1`).
- **Check** — CAGR and max drawdown from `metrics.json` within 0.15 pp of those figures; the equity
  calendar is contiguous from the first execution date; the benchmark column equals
  `NIFTY_100_bench.csv` forward-filled onto that calendar.
- **Data** — runner metrics.json + equity + benchmark CSV.
- **Pass** — within tolerance.
- **Failure means** — the store, the engine or the assembly moved since the lock. This is the
  regression anchor: it should be the first test to look at after any change to `data/master`.

### H-08 Per-trade P&L is net of both slippage legs
- **Rule** — the founder's standing instruction: per-trade P&L uses effective prices, both sides.
- **Check** — `exits.pnl_pct` equals `exit_price*(1-slippage) / avg_buy_cost - 1`, where
  `avg_buy_cost` already includes the buy-side leg.
- **Data** — runner exits + trades.
- **Pass** — equal to 1e-9.
- **Failure means** — `scripts/_clean_engine.py:531-533` computes `exec_price / avg_cost - 1`, i.e.
  net of the buy leg but gross of the sell leg, so every exit's P&L and the `hit_rate_overall`
  metric derived from it are overstated by 20 bp. Equity and CAGR are unaffected (cash accounting
  applies both legs); only the per-trade figures are.
