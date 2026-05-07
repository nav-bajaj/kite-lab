# TL25 Parameter Review — May 2026

These scripts run the parameter studies that produced the locked-in TL25 stack.
All use `scripts/_clean_engine.py` (no-lookahead engine). Run from repo root:

```bash
source .venv/bin/activate
python tasks/trend_leaders/experiments/_tl25_ma_test.py
```

## Studies (in order they were run)

| Script | Study | Outcome |
|--------|-------|---------|
| `_tl25_ma_test.py` | MA Structure component variants | DROPPED (redundant with eligibility) |
| `_tl25_eligibility_test.py` | Eligibility filter variants (8) | Keep current (Close > 200 + 50 > 200 + 200 rising) |
| `_tl25_cadence_test.py` | Entry/exit cadence (5 combinations) | Keep bi-weekly entry, weekly exit |
| `_tl25_topn_buffer_test.py` | Top-N × buffer grid (3 × 3) | Keep 25/20 universal (universe-specific tuning rejected) |
| `_tl25_weights_test.py` | TQS weights (10 variants) | Keep equal 1/3 each |
| `_tl25_pyramid_test.py` | Pyramid into winners (5 variants) | REJECTED (no universal benefit) |

## Earlier studies

ATR multiplier/floor, drawdown function (linear/squared/cubed), persistence
window, momentum window — all run interactively before these scripts existed
and not preserved as standalone files. Findings recorded in `../DESIGN.md`.

## Locked-in stack

See `../DESIGN.md` for the full review writeup. Headline:

- Eligibility: Close > 200 + 50 > 200 + 200 rising 20d
- Score: 1/3 persistence (252d/100 DMA) + 1/3 drawdown ((Close/126d high)²) + 1/3 momentum (63d, pct-ranked)
- Exit: 5x ATR no floor + Close < 200 DMA on weekly Friday signal
- Cadence: bi-weekly entry, weekly exit
- Top-25, buffer 20, equal-weight 1/N, 7.5% cap
