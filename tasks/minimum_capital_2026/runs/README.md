# runs/

Outputs of the six analysis scripts in the parent folder. All regenerable
— see `../STATE.md` for the run order.

| pattern | produced by | what it is |
|---|---|---|
| `capital_sizing.json` | `capital_sizing.py` | Phase 1: cost drag, replication, granularity, SIP tables |
| `om25_cap_sweep_results.json` | `om25_cap_sweep.py` | Headline metrics per OM25 cap arm |
| `om25_equity_*.csv`, `om25_trades_*.csv` | `om25_cap_sweep.py` | Per-arm equity curve and trade log (`baseline`, `cap1000`…`cap12000`) |
| `om25_placebo_cap{2000,4000}.csv` + `_summary.json` | `om25_cap_placebo.py` | Random-exclusion distribution, one row per seed |
| `results_l6_combo_cap4000.json` | `l6_combo_cap_study.py` | L6 + COMBO baseline, capped arm, both placebo summaries |
| `equity_l6_*.csv`, `trades_l6_*.csv`, `equity_combo_*.csv`, `trades_combo_*.csv` | `l6_combo_cap_study.py` | Per-arm equity and trades |
| `placebo_l6_cap4000.csv`, `placebo_combo_cap4000.csv` | `l6_combo_cap_study.py` | Per-seed placebo draws |
| `price_deciles_h63.csv` + `_summary.json` | `price_decile_study.py` | Forward return by price decile, per rebalance date and by year |
| `forced_exit_audit_cap4000.json` | `forced_exit_audit.py` | Days held after crossing the cap, and P&L above it, per arm |

## What is committed, and what is not

`*.csv` is globally gitignored (`.gitignore:58`). Committed here, matching
the `portfolio_risk_2026/runs/` precedent: the **JSON summaries** and the
small **per-seed placebo CSVs** and **decile CSV** — everything a reader
needs to check a number in the write-ups.

**Not committed:** the per-arm equity curves and trade logs
(`om25_equity_*.csv`, `om25_trades_*.csv`, `equity_l6_*`, `trades_l6_*`,
`equity_combo_*`, `trades_combo_*`) — ~2.5 MB of regenerable
intermediate. Re-create them with the two cap studies:

```
python tasks/minimum_capital_2026/om25_cap_sweep.py --caps 1000 2000 3000 4000 6000 8000 12000
python tasks/minimum_capital_2026/l6_combo_cap_study.py --cap 4000 --placebo-seeds 30
```

`forced_exit_audit.py` reads those trade logs, so it needs the cap studies
run first. Every other script is self-contained.
