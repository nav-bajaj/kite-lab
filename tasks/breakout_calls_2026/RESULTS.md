# Results — breakout_calls_2026

**Verdict:** The VCP breakout pattern has a real per-trade edge that survives
every honest test put to it, and the portfolio built on it fails 5 of 7
pre-committed gates. Closed as not-shippable. Its machinery — universe,
detector, exit ladder, book simulator — was inherited wholesale by
`trend_screen_2026`, which beats it on the same exit with seven times the
opportunities.

Opened 2026-09-11, closed 2026-09-12. Commit `a30d59a`.

## What was shipped vs planned

| Phase | Planned | Actual |
|---|---|---|
| §1 data layer | ~191 adjusted panels | **1,193** — the spine's per-symbol layer was index-members-only; the gap was in the raw export, not the adjusted view |
| §2 signal tape | E1/E2/failed-poke labels | Done, 2,787 events |
| §3 per-trade | gate C1-C5 | Done — passes on E1, E2 fails C3 |
| §4 exit ladder | grid + walk-forward | Done, 144 cells |
| §5 portfolio | gate P1-P7 | Done — fails P1, P3, P5, P6, P7 |
| §6 decomposition | attribute the competitor's 64.5% | **Not run** — superseded when the founder redirected to the trend screen. The competitor audit in COMPETITOR.md already isolates each source qualitatively. |
| §7 product decision | recommendation | Superseded by `trend_screen_2026` |

## The numbers that mattered

**Competitor audit (COMPETITOR.md).** Their engine reproduced exactly —
19.75x vs 19.82x, drawdown 12.3% vs 12.3% — which is what identifies the
flaw: the drawdown is realised-only. Marked to market the same book falls
~50%. Corporate actions, liquidity floor and sizing all checked out.

**The 42% number.** Keeping the pivot fill price but dropping the failed
pokes reads 0.664R instead of 0.467R. That is their entry bias measured on
our own honest tape.

**Mutual exclusivity.** The breakout-volume confirmation is an end-of-day
quantity; a stop-buy fills intraday. You cannot have both. Gating E1 on volume
produced zero events.

**Per-trade (E1, 1,751 trades):** 0.467R, 30.0% win, +1.70% alpha. E2 0.324R.
The cheaper fill more than pays for a 19% failed-poke rate.

**Exit ladder:** ma150 median 0.587R vs ma50 0.322R vs chandelier 0.266R. The
best cell (1.062R) does **not** clear the Gumbel expected max of 108 draws
(1.068R) — the trail axis is the finding, not the cell.

**Portfolio:** best 16.7% CAGR / −30.5% DD / 0.64 Sharpe at 10 slots.
Capacity is the hard fail — 7.2% at ₹25cr, because the edge lives in names too
small to hold at size.

## Deferred / superseded

- §6 decomposition — not run, see above.
- Slot-count and ordering findings (10 slots optimal; random vs
  tightest-first indistinguishable) carried into `trend_screen_2026`.
- The 8% stop inherited from `vcp_l6_study` was later shown wrong for a trend
  entry (`trend_screen_2026` §7); it remains correct for this task's
  tight-base entry.

## Verification log

- §1 gate: 2020 universe carries 45 names that have since stopped trading
  (2008: 42.8%). The competitor's book carries zero. **Passed.**
- §1 idempotency: of 1,340 pre-existing manifest entries, **zero** changed
  sha256; `INFY.csv` byte-identical in raw and adjusted layers.
- §2 gate: E1 tape +69% larger than E2, 19.0% failed pokes. **Passed.**
- §4 deflation: best cell inside the Gumbel bound. **Recorded as a fail.**
- Old-store cross-check: median price ratio exactly 1.0000, but only 34% of
  2010-2015 prices within 0.5% — pre-2016 differences vs `vcp_l6_study` must
  be attributed to the store before method.

## Known defects, fixed later

**Fill convention.** Entries filled at next open, trail exits at the signal
close. Production (`scripts/_clean_engine.py`) uses **OHLC/4 of T+1** for
every execution. Corrected in `trend_screen_2026` §9 via an opt-in
`exec_ohlc4` flag in `exits.simulate`; costs 0.2-0.4pp per trade. Figures in
this task's TASKS.md are on the old basis and are superseded for anything
client-facing.

**Near-duplicate signals.** 8.2% of the tape was two adjacent swing highs
anchoring nearly the same pivot. Book results unaffected (same-name
concurrency was already rejected); per-call mean R moves 1.06 → 1.03.
