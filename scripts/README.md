# scripts/

The production scripts layer — daily pipeline, portfolio runners, sync,
DB ops, deploys. Restricted to the closed dependency set of the daily
cron + dashboard COMMANDS layer (`kite-api/app/services/job_service.py`).

Closed research / old experiments live on the archive branch
(`repo-snapshot-2026-05-20`) — see `MAP.md` at the repo root.

## Layout

| Group | Files | Purpose |
|---|---|---|
| **Daily pipeline** | `run_daily_pipeline.py`, `apply_corporate_actions.py`, `cache_instruments.py`, `compute_benchmark.py`, `fetch_indices_history.py`, `fetch_nse500_history.py`, `login_and_save_token.py`, `preflight_token.py`, `pipeline_core.py`, `sync_data_backup.py` | Run-once-a-day orchestration + data refresh |
| **Portfolio runners** | `run_final_momentum_portfolio.py`, `run_om25_v3_portfolio.py`, `run_tl25_v3_portfolio.py`, `run_l6_v2_portfolio.py`, `run_combo_defensive_portfolio.py`, `update_all_portfolios.py` | The 4 production portfolios + the legacy L6 helper, plus the orchestrator that runs all of them |
| **Strategy libs** | `_clean_engine.py`, `_momentum_engine.py`, `om25_v3.py`, `tl25_v3.py`, `combo_defensive.py`, `backtest_momentum.py`, `build_om25_signals.py`, `metrics_common.py` | Algorithm implementations imported by the runners |
| **Signal building** | `build_momentum_signals.py`, `build_momentum_signals_flexible.py` | Top-N momentum rankings; the `_flexible` variant is exposed as a dashboard COMMAND |
| **DB + cloud sync** | `sync_to_database.py`, `backup_database.py`, `restore_database.py`, `upload_to_gdrive.py`, `upload_price_data.py` | Push results to Postgres, rotate DB backups, mirror data to Google Drive |
| **Operator utils** | `headless_login.py`, `update_prices.py`, `utils.py`, `history_utils.py` | Manual ops, used from CLI or dashboard admin |
| **Content bridge** | `publish_signal.py`, `generate_quant_note.py`, `analyse_topic.py` | `publish_signal.py` emits Signal-shaped JSON to `data/published/signals/` for the content engine. `analyse_topic.py` is the founder-facing "quick analysis" tool — takes a topic phrase and produces a verified-data dossier the content writers ground their pieces in. See `tasks/content_bridge/` + `tasks/content_redesign/`. |
| **Sector data** (reconstitution-time, not daily) | `fetch_sector_constituents.py`, `fetch_zerodha_sectors.py` | Refresh the sector taxonomies. `fetch_sector_constituents.py` snapshots the 12 NSE thematic *indices* (NIFTY_BANK…) for sector RS / breadth. `fetch_zerodha_sectors.py` writes `data/static/zerodha_sectors.csv`, a per-stock label from Zerodha's finer 35-sector taxonomy. Both change only at an NSE reconstitution — run them alongside the `tasks/universe_membership/` refresh, not in the daily cron. |
| **Docker** | `entrypoint.sh`, `init_persistent_storage.sh` | Run in `kite-api` container at boot |

## How to add a new script

1. Check whether an existing script in the same group already does
   the job (or could with a flag).
2. Header docstring is required — first line is a one-sentence
   description; second paragraph explains *when* you'd run it.
3. If the script needs to be runnable from the dashboard admin
   panel, add an entry to `kite-api/app/services/job_service.py`
   COMMANDS dict.
4. If the script is part of the daily cron, add a call from
   `run_daily_pipeline.py` (or another orchestrator) and document
   the cron-step it belongs to.
5. If it's a one-off operator utility, that's fine — add it directly
   to `scripts/` and document in this README.

## How not to add a new script

- Don't drop research probes here. Put them in `tasks/<initiative>/`
  while you're working on them, and either promote (rare) or archive
  when done.
- Don't add `compare_*.py`, `_diff_*.py`, `_probe_*.py` — those are
  research patterns. They go in a task folder.
