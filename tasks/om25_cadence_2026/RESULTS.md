# OM25 entry cadence — results

**Run date:** 2026-09-08 · **Panel:** `nse500_data_merged` (2005-01-03 → 2026-08-21)
**Stack:** `scripts/om25_v3.py:LOCKED`, unmodified. Only entry cadence and universe vary.

---

## ⚠️ Read this first: the control does not reproduce the published v3 numbers

Before any cadence conclusion, the bi-weekly Nifty 250 control was checked
against the archived winner curve
(`tasks/oos_retune_2026/winner_artifacts/om25_winner_equity.csv`, archive
branch). The archived curve reproduces the published figures. **A rerun of
the identical config today does not.**

| OOS_full 2017 → 2026-05-08 | CAGR | Sharpe | Max DD | OOS_A CAGR |
|---|---|---|---|---|
| A — archived winner curve (May-2026 data + code) | **43.57%** | **1.86** | −31.44% | 26.14% |
| B — rerun today, membership ON, start 2010-01 | 34.94% | 1.42 | −34.78% | 16.02% |
| C — rerun today, membership ON, start 2010-03 | 34.93% | 1.42 | −34.78% | 16.02% |
| D — rerun today, membership OFF, start 2010-03 | 37.31% | 1.51 | −36.20% | 16.45% |

Variant A is the published 44.78% / 1.86 / −36.6% headline (small deltas are
the retune quoting a slightly different slice).

**Which arm is the archive's equivalent? Membership ON — verified, not assumed.**
This matters, and an earlier draft of this page got it backwards. The archive
ran the May-2026 snapshot of `nifty250_universe.csv`, which contained the 12
names dropped at the 2026-07-15 refresh and none of the 12 added. Membership ON
reproduces exactly that for any pre-cutover date: `candidate_fn(d)` admits every
symbol whose `effective_from` (1900-01-01 for the originals) is ≤ d and excludes
the 2026 additions, and `membership_fn(d)` does the same for entries. Membership
OFF instead applies *today's* 250-name snapshot to all of history. Confirmed in
the trade logs:

| Pre-cutover BUYs, 2016-01-01 → 2026-07-15 | archive | mem ON | mem OFF |
|---|---|---|---|
| in the 12 names **dropped** at the refresh | 39 | 45 | **0** |
| in the 12 names **added** at the refresh | 0 | 0 | **20** |

So membership ON is the like-for-like arm on the *universe* dimension, and
**the price panel is the whole of the remaining gap** — not a mixture of panel and membership. Membership OFF
is simply a third, differently-wrong configuration: it deletes twelve real
2017–2019 index members from history and substitutes twelve stocks that were
added in 2026 *because they had performed*. That inclusion bias is why D scores
2.4pp above C, and it is bias, not signal.

| Cause | Effect on OOS_full CAGR |
|---|---|
| Backtest start date (2010-01 vs 2010-03) | **0.01pp** — nil |
| **Price panel changed since May 2026** | **−5.54pp** (like-for-like, phase-matched) |
| Bi-weekly phase luck (A→B grid offset) | 3.10pp — see phase note below |
| *(memo)* what backdating the July-2026 reconstitution would inject | +2.38pp of fake return (C → D) |

Membership is **not** a contributor. It was seeded by backdating the
then-current snapshot to 1900-01-01, so mem ON is the universe every published
figure used — verified: NSE 500 rows at `effective_from=1900-01-01` are
identical to the May-2026 snapshot, 500/500. Nothing needs restating on
membership's account. Full argument in `tasks/panel_drift_audit_2026`.

The price-panel cause is confirmed directly. Replaying the archived v3 trade
log against today's panel, **104 of 1,414 executions (7.4%) price differently by
>0.5%**, with unmistakable corporate-action signatures:

```
IRB      2020-07-27   arch 12.3125  today  6.1600   ratio 1.999   (2:1 split)
TRENT    2016-05-09   arch 166.18   today 113.88    ratio 1.459
MPHASIS  2016-01-04   arch 467.66   today 423.55    ratio 1.104
NMDC     2022-10-31   arch  29.61   today  28.18    ratio 1.051
BANKINDIA 2017-11-06  arch 198.30   today 190.13    ratio 1.043
```

**The damage is concentrated in 2017–2019.** Same config, membership held
constant, archived curve vs today by era:

| Window | archived CAGR / Sharpe | today CAGR / Sharpe |
|---|---|---|
| 2010-03 → 2016-12 | 28.59% / 1.60 | 30.23% / 1.56 |
| **2017-01 → 2019-12** | **26.14% / 1.60** | **15.03% / 0.76** |
| 2020-01 → 2026-05 | 52.65% / 1.98 | 50.42% / 1.92 |
| OOS_full 2017 → 2026-05 | 43.57% / 1.86 | 38.03% / 1.52 |

**Phase correction (2026-09-08).** An earlier version of this table compared
the archive against the *wrong bi-weekly phase*. `biweekly_fridays()` is
`fridays()[::2]`, and the archive's v3 runs sat on the odd grid — 201 of its
296 trade dates fit phase 1, only 66 fit phase 0. The rows above are now
phase-matched (`--biweekly-phase 1`). Phase alone is worth **3.10pp** of
OOS_full CAGR (34.93% on phase 0 vs 38.03% on phase 1), which is itself a
result: the bi-weekly grid offset is a bigger lever than the entry cadence
this task set out to test. The 2017–2019 collapse survives the correction
unchanged.

Pre-2017 is fine (today is marginally *higher*). 2020+ is a few points light
but the Sharpe is intact. 2017–2019 halves its Sharpe. It is not a coverage
gap — row counts per year rise smoothly through the window and only NMDC
carries the known phantom-timestamp rows. `tasks/panel_drift_audit_2026`
carries the follow-through: L6 v2 is hit too, by −3.19pp over its own
published window — less than OM25 because none of that window sits in
2017–2019.

**Consequences:**

1. The published OM25 v3 figures (44.78% CAGR / 1.86 Sharpe, in
   `docs/portfolios.md` and on the dashboard) **no longer reproduce on
   current data**. The same locked config now backtests to ~35%. This is a
   live-documentation problem independent of anything in this task.
2. The **cadence and universe comparison below is still valid** — all six
   arms share one panel, one harness, one code path, run within minutes of
   each other. Relative differences are clean. **Absolute levels are not
   comparable to any previously published OM25 number.**
3. Which panel is *correct* is not settled here. `tasks/corporate_actions_fix`
   and `tasks/adjusted_price_series` are the open threads.

---

## Cadence — Nifty 250 (production universe)

OOS_full = 2017-01-01 → 2026-08-21 (9.6y). Post-tax uses
`tasks/tax_study/tax_engine.py` with forced-sale slippage set to this study's
20 bps.

| Cadence | Entries | CAGR | **Post-tax CAGR** | Sharpe | Max DD | Tax drag | RT/yr | Avg hold | ST share of gains |
|---|---|---|---|---|---|---|---|---|---|
| **Weekly** | 868 | **35.10%** | **28.71%** | **1.42** | −35.94% | 6.39pp | 86.2 | 96d | 53.3% |
| Bi-weekly *(production)* | 434 | 34.02% | 28.20% | 1.40 | −34.78% | 5.83pp | 76.5 | 105d | 46.4% |
| Monthly | 200 | 31.92% | 26.52% | 1.38 | −33.79% | 5.40pp | 62.6 | 117d | 40.2% |

All three PASS every pre-registered criterion.

**Weekly wins, and the win is not worth having.** +1.08pp CAGR and +0.02
Sharpe over bi-weekly, paid for with 1.16pp more drawdown and 13% more
turnover. Then tax takes most of it: **the pre-tax gap of 1.08pp shrinks to
0.51pp post-tax**, because weekly pushes the short-term share of gains from
46% to 53%. Half a point of post-tax CAGR is inside the noise of a single
year's regime luck — OOS_B alone swings 6pp between the two.

The direction does replicate the May 2026 v2-stack sweep (weekly > bi-weekly >
monthly on CAGR, monotone in cadence), and the ordering is monotone in
drawdown the other way. So the shape of that old finding survives the v3
stack; the magnitude does not justify a change.

## Universe — NSE 500 vs Nifty 250

| Universe / cadence | CAGR | **Post-tax** | Sharpe | Max DD | Verdict |
|---|---|---|---|---|---|
| nse500 / weekly | 40.62% | 32.23% | 1.51 | **−52.20%** | FAIL DD |
| nse500 / bi-weekly | 39.21% | 31.48% | 1.48 | **−47.75%** | FAIL DD |
| **nse500 / monthly** | **41.26%** | **33.35%** | **1.62** | −42.22% | **PASS** |
| nifty250 / weekly | 35.10% | 28.71% | 1.42 | −35.94% | PASS |
| nifty250 / bi-weekly | 34.02% | 28.20% | 1.40 | −34.78% | PASS |
| nifty250 / monthly | 31.92% | 26.52% | 1.38 | −33.79% | PASS |

Two things fall out, and they point opposite ways.

**1. NSE 500 still fails on drawdown at production cadence — the regime tilt
did not fix it.** The v3 retune rejected NSE 500 because bi-weekly ran
−48.60% max DD against a −45% threshold. On today's data with the full
regime-tilted stack in place, NSE 500 bi-weekly runs **−47.75%**. That is
essentially the same rejection, reproduced. The regime tilt was introduced to
rescue NSE 500's drawdown and, on this evidence, it did not. Nifty 250 remains
the right production universe at bi-weekly cadence.

**2. The cadence ordering inverts on NSE 500.** On Nifty 250 more frequent is
(marginally) better. On NSE 500 it is clearly worse: weekly is the worst
drawdown in the entire matrix (−52.2%) while monthly is the *best Sharpe in
the matrix* (1.62) and the only NSE 500 arm that passes. Going from weekly to
monthly on NSE 500 costs nothing in CAGR (40.62% → 41.26%, it actually gains)
and buys 10pp of drawdown.

Mechanism: every arm's worst drawdown bottoms at COVID (2020-03-23/24), but
the NSE 500 arms peak at **2018-01-15** and never recover before it — they
carry the 2018–19 mid/small-cap bear all the way into the crash as one
unbroken drawdown. Nifty 250 bi-weekly's peak is 2020-02-20, i.e. it made new
highs in 2019 and took only the COVID leg. Faster rebalancing in a broad
universe rotates *into* the falling mid-cap cohort repeatedly; slower
rebalancing sits through less of it. NSE 500's short-term share of gains is
77% at weekly and bi-weekly vs 46-53% on Nifty 250 — it is a structurally
higher-churn, higher-tax portfolio.

## Answering the framing question

*How cadence-sensitive is OM25's edge?* On the production universe, barely:
0.5pp of post-tax CAGR across a 4× range of entry frequency (weekly to
monthly), with Sharpe flat at 1.38–1.42. **Cadence is not a lever on OM25 v3
at Nifty 250.** That is the useful diagnostic result — it means the Friday
execution window has real slack. A subscriber who acts on Monday instead of
Friday, or misses a rebalance entirely, is giving up single-digit basis points
per event, not a strategy.

*Is there slack in the Friday window?* Yes. Monthly entry on Nifty 250 keeps
94% of bi-weekly's post-tax CAGR at 82% of the turnover. Nothing about the
edge requires the bi-weekly beat.

## Not recommended

No production change. Bi-weekly Nifty 250 stays. Weekly's edge is inside
noise and negative after tax-adjusted risk; NSE 500 fails the DD gate at
production cadence exactly as it did in the retune.

The one result worth a second look is **NSE 500 monthly** (Sharpe 1.62,
post-tax 33.35%, PASS) — best risk-adjusted arm in the matrix. Flagging it,
not proposing it: it is one un-replicated cell, on a panel whose corporate-
action state is in flux, sharing ~all its machinery with a portfolio we
already ship. Per the standing stance it should not be chased without a
reason beyond "the number is high."

## Caveats

- **The panel discrepancy above dominates everything.** Every absolute number
  on this page is conditional on a price panel that has changed since the
  numbers we publish were computed, and whose correctness is an open thread.
- **Survivorship.** Both membership CSVs are 2026-vintage
  (`nse500_membership.csv`: 500 rows at 1900-01-01 + 34 dated 2026 edits).
  Pre-2026 delistings are absent from all six arms. Inflates all of them;
  should not bias the comparison.
- **Split-adjusted prices** — no price-*level* claim can be drawn from this
  study. Returns and the drawdown-stop ratio are unaffected.
- **Bi-weekly phase.** `biweekly_fridays()` is `fridays()[::2]`, so the
  bi-weekly arm's phase is pinned by the panel start. It was not re-run on the
  opposite phase; the weekly arm is a superset of both and is not exposed.
- **Costs modelled:** 20 bps slippage + Indian CGT (STCG 20%, LTCG 12.5% over
  ₹1.25L, 8-FY carry-forward). No brokerage, STT, or stamp duty.
- **Single realisation.** No walk-forward, no bootstrap. Differences under
  ~2pp CAGR should be read as ties.

## Files

| Path | What |
|---|---|
| `_cadence_run.py` | One run: universe × cadence (`--no-membership`, `--tag` for diagnostics) |
| `_summarise.py` | Window metrics + tax overlay → the tables above |
| `multi_window_oos_eval.py` | Vendored from archive branch, unmodified |
| `summary_headline.csv` | One row per arm |
| `summary_windows.csv` | Per-arm, per-window IS / OOS_A / OOS_B / OOS_C / OOS_full |
| `summary_tax.csv` | Per-arm, per-FY tax detail |
| `runs/<universe>_<cadence>/` | equity, trades, exits, meta |
| `runs/diag_nomem/`, `runs/diag_memstart/` | The control-drift attribution runs |
