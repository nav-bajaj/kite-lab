# runs/

## What is committed

- **Every summary / analysis CSV** — the actual evidence behind the tables in
  `RESULTS.md` (`summary.csv`, `regime_*/regime_summary.csv`,
  `om25_stop/stop_vs_overlay.csv`, `sip_analysis.csv`, `investor_horizon.csv`,
  and the rest).
- **`regime_idx/*.csv` and `nifty100_regime_merged.csv`** — spliced index
  series used as *inputs* to every regime test. Each stitches
  `indices_data_historical/` (long history, ends 2026-05-08) with
  `indices_data/` (live tail) — the 1,572 overlapping days agree to 5e-6.
  Committed because the splice was done inline and is not otherwise
  reproducible from a script.

## What is NOT committed, and how to regenerate it

Per-run **equity curves** (`*_equity.csv`, `recent_*.csv`) and all trade/exit
ledgers were left out — 5.3 MB of derived data that rebuilds in minutes, in a
repo that gitignores `*.csv` for good reason.

Three analysis scripts read those curves and will fail on a fresh checkout
until they are rebuilt. Run these first, from the repo root with the venv
active:

```bash
# L6 curves (buf00..buf20_equity.csv) — needed by rolling_returns, acceptance_audit
python tasks/portfolio_risk_2026/exit_buffer_sweep.py --buffers 0 5 10 15 20

# COMBO curve — needed by acceptance_audit
python tasks/portfolio_risk_2026/combo_buffer_sweep.py --buffers 0 20

# OM25 stop/overlay curves — needed by acceptance_audit
python tasks/portfolio_risk_2026/om25_stop_vs_overlay.py

# the headline walk-forward — needed by investor_stats and sip_analysis
python tasks/portfolio_risk_2026/om25_walkforward.py \
  --index NIFTY_100 --start 2010-07-01 --first-test 2013-07-01 --tag _n100_long

# TL25 curve is built automatically by acceptance_audit.py on first run
python tasks/portfolio_risk_2026/acceptance_audit.py
```

`recent_production.csv` and `recent_candidate_n100.csv` (read by
`investor_stats.py` and `sip_analysis.py`) were produced by an inline step, not
a committed script. To rebuild: run OM25 from 2010-07-01 with the production
config (tilt N100 100-DMA, no overlay, 20% stop) and with the candidate config
(same tilt, N100 ROC31 overlay at 75% bear exposure, stop disarmed), writing
each equity frame to those filenames. `om25_stop_and_tilt.py` builds both
configurations and can be adapted in a few lines.

All committed summary CSVs are complete on their own — the tables in
`RESULTS.md` do not depend on regenerating anything.
