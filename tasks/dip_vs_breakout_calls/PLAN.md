# Dip-entry vs breakout-entry call feeds at tight caps

Follow-on to `tasks/donchian_channel` (closed 2026-07-24) answering two
open questions with the same engine:

1. The surviving India config (NSE 500, fresh 20d-high cross,
   top-quartile 126d momentum score, slots by momentum rank, exit at
   momentum rank < 0.35) was productized at caps 50-150 but never
   simulated at a tight cap (~25). What are the economics there?
2. H4b concluded the breakout is "an entry timer for the momentum
   sleeve; momentum owns the exit". Test the other entry timer we have
   evidence for (`tasks/meanrev_largecap_study`): a 5-day return
   < -5% dip entry into the same momentum sleeve with the same exit.

Founder brief (2026-08-23): a swing product needs enough calls/year,
few concurrent positions, always-on, holds longer than the 3-day
meanrev sleeve.

## Method

- Engine: faithful numpy port of the h4c/h4f/h4h simulator. Signal at
  close, fill next day at OHLC/4 +/- 20bps, momentum-rank slot
  priority, one call per symbol, portfolio = equal 1/cap slots (idle
  slots earn 0), Sharpe = (CAGR - 5%) / vol (house convention).
- Regression gate: full universe, END 2026-05-08, cap 50, xr35,
  no stop -> Sharpe 1.494 vs 1.489 published in h4g (n differs from
  the 1,377 xr50 figure by design; xr35 holds longer).
- Window 2010-06-01 -> 2026-08-19; tail split at 2023-07-01 (house
  convention).
- Arms (all exit rank < 0.35): entry {breakout20, dip5d<-5%,
  dip+200DMA} x cap {25, 50} x trail {none, 20%-from-peak}, 7 cells
  (not full grid; pre-chosen).

## Data cleaning

33 symbols excluded from study arms (kept in the regression arm):
30 with one-day close drops < -30% (mix of unadjusted corporate
actions and real crashes — ADANIENT 2015 demerger, ANGELONE -90%
2026-01, ECLERX x4 2026, IRB x2, LICI, TRENT/ANANDRATHI/ZFCVINDIA
2026-05-29, YESBANK, IDEA, RPOWER, ...) plus 3 with upside cliffs
> +50% (BRITANNIA 2010, SUNDARMFIN 2012, NMDC 2022). Excluding real
crashes biases results modestly up; including fake -50/-90% prints
while in top-quartile momentum biases arbitrarily. Exclusion applies
identically to all arms, so between-arm comparisons are clean.
**The corporate-action gaps themselves are a live pipeline bug —
flagged to founder 2026-08-22/23, needs its own fix.**

## Known limitations

- Current-constituent universe (survivorship) — same as all prior
  studies in this line.
- 20bps slippage only; no STT/taxes.
- Winner-of-7 selection; treat between-arm deltas as indicative.
- The donchian validity-gate failure (negative direction lift vs
  same-date baseline) was established for BREAKOUT entries. The dip
  arm has NOT been through `pattern_validity_study.py`; no
  subscriber-facing forward-return claims until it is.

## Files

- `experiment.py` — engine port + arms + regression gate.
- `calls_<arm>.csv`, `summary.csv`, `report.json` — outputs.
- `RESULTS.md` — findings.
