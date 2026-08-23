# VCP + L6 study

Quick research probe: does a Minervini VCP (Volatility Contraction
Pattern) breakout strategy have per-trade edge on the NSE 500, and does
gating entries to the top quartile of stocks by L6 momentum (raw 126-day
return, point-in-time cross-sectional rank) improve it?

## Design (user-confirmed 2026-08-22)

- **Form:** per-trade event stats, no capital constraint. Not a
  portfolio simulation.
- **Data:** `nse500_data_merged/` (corporate-action adjusted, current
  NSE 500 constituents, per-symbol history back to ~2010, ends
  2026-08-19). Benchmark `indices_data/NIFTY_500.csv` (starts 2020 —
  alpha is only computed for 2020+ trades).
- **Entry:** signal on close > pivot x 1.001 with volume >= 1.5x 50d
  avg; fill at next day's open, 0.2% slippage each side.
- **Exits (Minervini-style):** hard stop at final-contraction low
  capped at -8%; sell half at +20% close (stop to breakeven on rest);
  trail remainder out on a close below the 50DMA.
- **Gates on breakout day:** Stage-2 trend template (close > 50 > 150 >
  200DMA, 200DMA rising over 21 sessions, >= 30% above 52w low, within
  25% of 52w high) + L6 top quartile. RS rank >= 70 is subsumed by the
  L6 quartile gate.
- **Pattern:** fractal +/-5-bar swing pivots; base = ascending swing
  highs walked back from the pivot; 2-6 contractions, monotonic
  tightening, first leg 15-35%, final leg < 10%, base 3-65 weeks, prior
  advance >= 30%; volume dry-up + accumulation checks; 5-bar tightness.
- **Tiers:** the full spec as provided ("strict") plus "standard" and
  "loose" relaxations, because the strict spec chains ~12 AND-gates and
  fires rarely. Controls "standard_no_l6" / "loose_no_l6" isolate what
  the L6 gate contributes.

## Known limitations

- Survivorship bias: current-constituent universe; worse pre-2024.
- One concurrent trade per symbol; no portfolio-level netting.
- Benchmark alpha unavailable pre-2020.

## Files

- `vcp_backtest.py` — detector + trade sim + tier summaries.
- `trades_<tier>.csv`, `summary.json` — outputs.
- `RESULTS.md` — findings.
