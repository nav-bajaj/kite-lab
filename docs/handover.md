# Kite-Lab Handover — Mac mini Setup

Runbook for bringing the Mac mini up to parity with the laptop so either
machine can run the daily pipeline, backtests, and analysis. Tested
against the May 2026 production layout.

## Coordination rule

**Whoever logs in wins.**

There is one Zerodha access token per user, and `login_and_save_token.py`
invalidates any prior token when it issues a new one. Both machines can
run the full pipeline, but only one machine has a valid Kite session at
a time.

In practice: when you switch machines, run
`python scripts/login_and_save_token.py` on the new one. The other one's
token is now dead — re-login there when you switch back.

This works because you only sit at one device at a time. If that
changes, the alternative is to designate one machine as the daily logger
and sync `access_token.txt` via iCloud Drive.

## One-time setup (~30 min)

### 1. Clone the repo

```bash
cd ~ && git clone https://github.com/nav-bajaj/kite-lab.git
cd kite-lab
```

### 2. Transfer secrets from the laptop

These files are gitignored and need to be copied manually (AirDrop or
1Password are both fine):

| Path on laptop | Notes |
|---|---|
| `/Users/navdeep/kite-lab/.env` | Kite API_KEY/API_SECRET/REDIRECT_URI plus any DB/Railway/Vercel keys |
| `~/.config/kite-lab/gdrive_client_secret.json` | Google Drive OAuth client (for `upload_to_gdrive.py`) |
| `~/.config/kite-lab/gdrive_token.json` | Drive refresh token; reuse so the Mac mini doesn't need a browser auth |

**Do not copy** `access_token.txt` — that's regenerated daily and is
machine-specific. Just run the login script on the Mac mini after setup.

### 3. Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The root `requirements.txt` is a `pip freeze` of the laptop's `.venv`
(scripts + API + dashboard deps combined). If you'll also run the API
locally on the Mac mini, the kite-api-only subset lives at
`kite-api/requirements.txt`.

### 4. Seed the stock_data folder

AirDrop the full `~/Documents/stock_data/` folder from the laptop to the
Mac mini. It's ~50MB and contains everything the pipeline needs:

- `nse500_data/` — daily OHLCV for NSE 500 (gitignored, lives outside repo)
- `nse500_data_hourly/` — 90 days hourly
- `nse500_data_historical/` — long-history panel
- `indices_data/` — Nifty index data
- `db_backups/` — Postgres tarballs (only needed if restoring)

The pipeline expects this exact path. If you ever lose it, you can also
restore from Google Drive — `upload_to_gdrive.py` keeps 7 daily tarballs
under `My Drive/kite-lab-backups/<dirname>_snapshots/`. There's no
auto-download script yet; if you need one, untar manually.

### 5. First Kite login on the Mac mini

```bash
source .venv/bin/activate
python scripts/login_and_save_token.py
```

This invalidates the laptop's token, which is expected (see Coordination
rule above).

### 6. Smoke test

End-to-end check that everything's wired up:

```bash
source .venv/bin/activate
python scripts/run_final_momentum_portfolio.py --universe nifty100
```

Successful run should write a timestamped folder under
`nifty_100_tests/` with `momentum_metrics.csv` and `report.html`.

## Daily workflow

On either machine:

```bash
cd ~/kite-lab
git pull
source .venv/bin/activate
python scripts/login_and_save_token.py        # if switching machines
python scripts/run_daily_pipeline.py          # fetch + signals + sync
```

After local work:

```bash
git add <files>
git commit -m "..."
git push
```

## Things that live outside the repo

A reminder of state that isn't synced via git and needs attention when
moving machines:

- **Price data** (`~/Documents/stock_data/`) — seeded once, then each
  machine fetches its own daily updates from Kite.
- **Secrets** (`.env`, `~/.config/kite-lab/gdrive_*.json`) — manual
  copy on first setup, then static.
- **Kite access token** (`access_token.txt`) — regenerated daily per
  machine; whoever logs in last wins.
- **Python venv** (`.venv/`) — recreate from `requirements.txt`.
- **Railway / Vercel / Postgres** — single shared production
  environment, no per-machine state. The dashboard hits
  `kite-lab-production.up.railway.app` from anywhere.

## Editor notes

VS Code on the Mac mini:

- Install the **Python** + **Pylance** extensions.
- Set interpreter to `~/kite-lab/.venv/bin/python` (Command Palette →
  "Python: Select Interpreter").
- `.vscode/` is gitignored, so workspace settings stay machine-local.

## When something breaks

| Symptom | Fix |
|---|---|
| Kite "Token is invalid or has expired" | Re-run `python scripts/login_and_save_token.py` on whichever machine you're on. |
| `ModuleNotFoundError` on a fresh setup | `pip install -r requirements.txt` again — the freeze list pins everything. |
| Stock data CSVs missing | AirDrop `~/Documents/stock_data/` from the other Mac, or restore from `My Drive/kite-lab-backups/`. |
| `instruments_full.csv` stale | `python scripts/login_and_save_token.py` (the login flow refreshes it), or run `run_daily_pipeline.py`. |
| Mac mini and laptop disagree on data | Each machine fetches its own daily updates — small divergences are normal. If you want them aligned, copy `~/Documents/stock_data/nse500_data/` between them. |
