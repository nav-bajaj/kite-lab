# Dip feed: top quartile vs third quartile momentum sleeve (2026-08-26)

**Verdict: the sleeve is the strategy. Moving the dip entry from the top
momentum quartile to the third quartile costs 12.1pp of CAGR and 0.51 of
Sharpe under the sleeve-consistent exit, and 14.8pp of CAGR with a
drawdown blowout to -53% under the literal one-thing-changed exit. At
cohort level the third-quartile dip has no edge at all: -0.01pp excess
at 20 days (t=-0.1) against +1.02pp (t=15.1) for the top quartile. The
dip is an entry timer for a momentum sleeve, not a standalone signal.**

## What was changed

One thing: the momentum band the dip entry may buy. Everything else is
the daily arm from `dd_optimization.py` (`dip_6m_ts20`) untouched —
5-day return < -5% trigger, 126d vol-scaled momentum rank, cap 25,
rank-priority slots, signal at close / fill next day at OHLC/4 ± 20bps,
20% trailing stop, 2010-06-01 → 2026-08-21, nse500 merged universe less
`CLIFF_SYMBOLS` (467 symbols).

| band | rank |
|---|---|
| Q1 (top) | ≥ 0.75 |
| Q2 (second, context row) | 0.50–0.75 |
| Q3 (third) | 0.25–0.50 |

**Exit-rule wrinkle.** The momentum-decay exit fires at rank < 0.35,
which sits *inside* the Q3 band. A literal one-thing change therefore
kicks Q3 positions out as soon as they drift below 0.35 — a different
strategy, not just a different sleeve. Both readings are reported:

- `_std` — exit rank left at 0.35 (literal one-thing-changed).
- `_band` — exit rank shifted with the sleeve (band floor − 0.40, the
  same 0.40 of rank slack Q1 gets); for Q3 that floors at 0, so exits
  are trail-only.

`q1_top` reproduces `dip_6m_ts20` from yesterday's grid to the decimal
(36.7 CAGR / 1.734 Sharpe / -34.59 DD) — the engine is a faithful port.

## Portfolio results (cap 25, full history)

| arm | calls/yr | n | win% | mean | median | hold (td) | CAGR | Sharpe | maxDD | Calmar |
|---|---|---|---|---|---|---|---|---|---|---|
| **q1_top** | 64.5 | 1047 | 49.8 | +17.58 | -0.12 | 84 | **36.70** | **1.734** | -34.6 | **1.061** |
| q2_std | 81.1 | 1315 | 45.1 | +11.35 | -1.26 | 59 | 30.73 | 1.501 | -33.6 | 0.913 |
| q2_band | 44.2 | 717 | 49.0 | +22.61 | -0.53 | 102 | 30.26 | 1.495 | -33.4 | 0.907 |
| q3_std | 241.3 | 3915 | 32.9 | +3.22 | -0.99 | 6 | 21.90 | 0.970 | **-53.0** | 0.413 |
| q3_band | 36.7 | 596 | 43.6 | +24.20 | -4.66 | 123 | 24.57 | 1.227 | -39.0 | 0.630 |

Tail window (2023-07 →): Q1 36.98 CAGR / 1.487 Sharpe; q3_band 26.72 /
1.263; q3_std 26.99 / 1.100. The ordering holds out of the deep history.

Monotonic in the sleeve, both exit readings: Q1 > Q2 > Q3 on CAGR,
Sharpe and Calmar. Q2 costs ~6pp of CAGR; Q3 costs another ~6pp.

Yearly portfolio return, Q1 vs Q3: **Q1 wins 14 of 17 years** against
q3_band (Q3 ahead only in 2016, 2022, 2025) and 13 of 17 against
q3_std. Q3's edge years are the flat/rotational ones — 2025 (+7.3 vs
+5.2) is the only recent case, and it is small.

## Why q3_std collapses

The exit mix explains it. With the exit rank left at 0.35 inside the
band, 3,523 of 3,915 closed calls (90%) exit on momentum decay, median
hold **6 trading days** — the arm has degenerated into a high-churn
mean-reversion scalp: 241 calls/yr, 32.9% win rate, mean +3.22%, and a
-53% drawdown. Restoring the sleeve's rank slack (`q3_band`, trail-only
exits, 100% trail exits) rebuilds a coherent swing strategy, but it
still lands 12.1pp of CAGR below Q1 with a worse drawdown.

Note the trap in `q3_band`'s per-call stats: mean +24.20% *beats* Q1's
+17.58% while the median is **-4.66%** vs Q1's -0.12%. The third
quartile's payoff is a thinner tail carrying a worse body — more calls
that quietly bleed, a few that run. As a published call feed that is the
wrong shape regardless of the CAGR.

## Cohort check (portfolio mechanics removed)

Q3 sees 42,481 dip signals vs Q1's 30,776, so the cap binds differently
across arms. Measuring the raw signal instead — forward return from the
signal, in excess of the same-day equal-weight universe:

| cohort | n | mean excess | t | median excess | win vs universe |
|---|---|---|---|---|---|
| q1 20d | 28,687 | **+1.02pp** | 15.1 | +0.03 | 50.1% |
| q2 20d | 32,971 | +0.42pp | 7.4 | -0.58 | 47.1% |
| q3 20d | 39,990 | **-0.01pp** | -0.1 | -0.79 | 45.9% |
| q1 60d | 28,264 | **+2.43pp** | 18.1 | -0.55 | 48.6% |
| q2 60d | 32,618 | +0.51pp | 4.8 | -1.68 | 45.2% |
| q3 60d | 39,633 | **-0.25pp** | -2.7 | -2.16 | 43.8% |

The top-quartile cohort's +1.02pp @20d is the figure already logged in
`tasks/insight_engine/VALIDITY_PROTOCOL.md`. The third-quartile cohort
is indistinguishable from the universe at 20 days and mildly negative at
60 — it would **fail** the validity protocol, so no forward-return claim
could be published on it.

## What this means

- The published dip feed's edge comes from the momentum sleeve; the dip
  only times the entry into it. Buying dips in mid-ranked names is
  buying dips, full stop.
- No reason to revisit the quartile choice. Q1 is not a tuned parameter
  sitting on a cliff — the gradient is smooth and monotonic through Q2,
  which is what you want from a robust cut.
- If more call volume is ever wanted, widen with Q2 (30.7 CAGR, 81
  calls/yr) rather than dropping to Q3 — but yesterday's trail ladder
  (`dip_6m_ts15`, 96.5 calls/yr at 39.4 CAGR) is the better lever for
  that, since it adds volume without leaving the sleeve.

## Files

- `quartile_compare.py` — portfolio arms; `summary_quartile.csv`,
  `report_quartile.json`, `calls_q_*.csv`, `curve_q_*.csv`.
- `quartile_cohort.py` — cohort forward returns;
  `summary_quartile_cohort.csv`, `report_quartile_cohort.json`.
- Caveats inherited from the parent study: current-constituent universe
  (survivorship), `CLIFF_SYMBOLS` excluded, 20bps/side costs, no taxes.

---

# Addendum: exit hysteresis for lower-quartile entries (2026-08-26)

**Verdict: the exit was genuinely mis-specified for Q2/Q3, and fixing it
removes the pathology — the 6-day churn and the -53% drawdown both go
away. It does not close the gap. Across 22 exit variants, the best Q2
arm reaches 30.3 CAGR / 1.50 Sharpe and the best Q3 arm 28.1 / 1.40,
against the published Q1 feed's 36.7 / 1.73. The sleeve ordering
survives every exit rule tested, and the one Q3 rule that comes closest
works by waiting for the name to become a top-quartile name.**

## Exit families tested

Entry, sleeve, cap, slots, execution and window all held fixed; only the
exit rule varies. `trail` is the 20% trailing stop unless noted.

| family | rule |
|---|---|
| `ts15/20/25` | trailing stop only, no rank exit |
| `f10 / f20` | absolute rank floor well below the band |
| `rel15 / rel25` | rank < entry_rank − d (entry-relative hysteresis) |
| `ratchet20 / ratchet30` | rank < peak-rank-since-entry − d (a trailing stop on rank itself) |
| `p{target}g{grace}` | "prove it": must reach rank ≥ target within `grace` days, else exit; once promoted, trail only |

## Best of each sleeve

| arm | exit | calls/yr | win% | mean | median | hold | CAGR | Sharpe | maxDD | tail Sharpe |
|---|---|---|---|---|---|---|---|---|---|---|
| **q1_published** | floor 0.35 | 64.5 | 49.8 | +17.6 | −0.12 | 84 | **36.70** | **1.734** | −34.6 | 1.487 |
| q1_rel25 | rel 0.25 | 103.7 | 48.5 | +10.0 | −0.35 | 53 | 37.00 | 1.678 | −33.7 | 1.413 |
| q1_ts20 | trail only | 42.8 | 50.7 | +25.6 | +0.55 | 97 | 33.78 | 1.692 | −32.8 | 1.533 |
| q2_f10 | floor 0.10 | 44.2 | 49.0 | +22.6 | −0.53 | 102 | 30.26 | 1.495 | −33.4 | 1.345 |
| q2_p75g20 | prove 0.75/20d | 50.3 | 50.1 | +20.0 | +0.03 | 60 | 28.28 | 1.427 | −36.8 | 1.045 |
| q3_p65g20 | prove 0.65/20d | 100.5 | 44.9 | +10.8 | −1.15 | 21 | 28.08 | 1.400 | −37.5 | 1.167 |
| q3_ts20 | trail only | 36.7 | 43.6 | +24.2 | −4.66 | 123 | 24.57 | 1.227 | −39.0 | 1.263 |
| q3_ratchet20 | ratchet 0.20 | 222.4 | 43.5 | +1.9 | −1.12 | 23 | 17.03 | 0.673 | −50.0 | 0.955 |

(Full 22-arm grid in `summary_quartile_exits.csv` +
`summary_quartile_promote.csv`.)

## What the grid says

1. **The founder's diagnosis was right.** The 0.35 floor inside the Q2/Q3
   band was the pathology, not a real exit: replacing it lifts Q3 from
   21.9 CAGR / 0.97 Sharpe / −53% DD to 28.1 / 1.40 / −37.5%. That is a
   large repair.

2. **But the exit is not the binding constraint.** Nine exit families
   move Q2 only between 22.3 and 30.3 CAGR, and Q3 between 17.0 and
   28.1 — while every single one stays below the Q1 arm. What the exit
   rule mostly trades is hold length for turnover, not return:
   `q2_ratchet20` runs 200 calls/yr at a +3.5% mean; `q2_ts25` runs 23
   calls/yr at +37.4%; they land 7pp apart on CAGR and identical on
   drawdown. That is the signature of reshaping a distribution rather
   than adding edge — consistent with the cohort test, where the Q3 dip
   has no forward edge to harvest at all (−0.01pp @20d, t=−0.1).

3. **The best Q3 rule is a disguised Q1 entry.** `q3_p65g20` works by
   discarding any Q3 dip that fails to climb to rank 0.65 within 20
   days. Survivors are, by construction, names that have become
   upper-sleeve momentum names — so the rule's content is "buy the dip
   early, keep only the ones that turn into leaders." It still gives up
   8.6pp of CAGR and 3pp of drawdown against simply buying leaders'
   dips, and it triples turnover (100 vs 64 calls/yr).

4. **Hysteresis is not a free win on the top sleeve either.** Applying
   the same rules to Q1: `rel25` 37.0 / 1.678, `ratchet20` 36.6 / 1.646,
   `ts20` 33.8 / 1.692 — all within noise of, or below, the published
   36.7 / 1.734. So this is not "a better exit we were missing"; the
   published floor is already well-matched to the top-quartile band.

   Worth one footnote for a different question: `q1_ts20` (trail only,
   no rank exit) has the best drawdown of any arm here (−32.8%) and the
   best tail-window Sharpe (1.533) at only 43 calls/yr. If the drawdown
   work from `dd_optimization.py` gets picked up again, that row is
   worth a look — it is a cleaner rule with one fewer parameter.

## Where this leaves the question

Both readings of "use lower-quartile stocks" are now closed: with the
original exit (incoherent) and with four families of properly specified
hysteresis (coherent). The answer does not change. The dip is an entry
timer for a momentum sleeve; the sleeve is where the return lives.

Open threads, if the lower sleeves are worth another pass:
- The promotion rule is the only structurally interesting result — it is
  a *momentum-rebuild* signal, not a dip signal. Tested as an entry in
  its own right (buy when a name climbs from Q3 into Q1 after a dip) it
  would be a different study, and a legitimate one. **Tested 2026-08-27
  and closed — no forward excess at 20d or 60d, and the dip screen makes
  a plain rank crossing worse. See `RESULTS.md` → Addendum 8 → "Tested
  and closed: momentum-rebuild as an entry".**
- Cost sensitivity was not swept; the high-churn arms (>150 calls/yr)
  carry 40bps round-trip on a +2-5% mean trade, so they are the most
  fragile to a slippage assumption change. The recommended arms are all
  under 105 calls/yr.

## Files (addendum)

- `quartile_exits.py` — exit grid + `--promote` addendum;
  `summary_quartile_exits.csv`, `summary_quartile_promote.csv`,
  `report_quartile_exits.json`, `report_quartile_promote.json`,
  `calls_qx_*.csv`, `curve_qx_*.csv`.
