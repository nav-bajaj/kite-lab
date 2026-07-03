#!/bin/sh
# Initialize persistent storage on Railway.
#
# Railway mounts a volume at /data. This script creates subdirectories
# there and symlinks them into /app so all scripts work unchanged.
#
# Runs at container startup before the API server starts.

VOLUME="/data"
APP="/app"

# Exit early if no volume is mounted (local dev / no Railway volume)
if [ ! -d "$VOLUME" ]; then
    echo "[init-storage] No persistent volume at $VOLUME, skipping."
    exit 0
fi

echo "[init-storage] Persistent volume detected at $VOLUME"

# Create subdirectories in the volume
mkdir -p "$VOLUME/nse500_data"
mkdir -p "$VOLUME/nse500_data_hourly"
mkdir -p "$VOLUME/nse500_data_historical"  # 2009-2019 GDF backfill (Phase 2.5.6)
mkdir -p "$VOLUME/nse500_data_gdf_full"    # 2009-2023 deep GDF backfill (raw)
mkdir -p "$VOLUME/nse500_data_full"        # stocks: GDF + Kite stitched
mkdir -p "$VOLUME/indices_data_full"       # indices: historical + Kite stitched
mkdir -p "$VOLUME/indices_data"
mkdir -p "$VOLUME/instruments"
mkdir -p "$VOLUME/benchmarks"
mkdir -p "$VOLUME/final_portfolio"
mkdir -p "$VOLUME/nifty_100_tests"
mkdir -p "$VOLUME/nifty_250_tests"
mkdir -p "$VOLUME/experiments"
mkdir -p "$VOLUME/logs/jobs"
mkdir -p "$VOLUME/tokens"
# v3 strategy portfolio dirs — the daily runners write timestamped runs
# here. Symlinked so runs survive Railway container restarts (deploys).
# Without this, /app/data/<strategy>_portfolios/ is ephemeral: every
# redeploy wipes the runs, and any producer job (e.g. eod_proposed_orders)
# that expects to find a completed run dir fails until the next
# daily_pipeline populates them.
mkdir -p "$VOLUME/om25_v3_portfolios"
mkdir -p "$VOLUME/tl25_v3_portfolios"
mkdir -p "$VOLUME/l6_v2_portfolios"
mkdir -p "$VOLUME/combo_defensive_portfolios"

# Helper: create symlink if target doesn't already point to the volume
link() {
    src="$1"  # volume path
    dst="$2"  # app path
    # Remove existing directory/file (but not if it's already a correct symlink)
    if [ -L "$dst" ]; then
        current=$(readlink "$dst")
        if [ "$current" = "$src" ]; then
            return  # Already correct
        fi
        rm "$dst"
    elif [ -e "$dst" ]; then
        # Copy any existing data into volume before replacing
        if [ -d "$dst" ] && [ -z "$(ls -A "$src" 2>/dev/null)" ]; then
            echo "[init-storage] Migrating existing $dst -> $src"
            cp -a "$dst/." "$src/" 2>/dev/null || true
        elif [ -f "$dst" ] && [ ! -f "$src" ]; then
            echo "[init-storage] Migrating existing $dst -> $src"
            cp "$dst" "$src" 2>/dev/null || true
        fi
        rm -rf "$dst"
    fi
    ln -s "$src" "$dst"
    echo "[init-storage] Linked $dst -> $src"
}

# Symlink directories
link "$VOLUME/nse500_data"             "$APP/nse500_data"
link "$VOLUME/nse500_data_hourly"      "$APP/nse500_data_hourly"
link "$VOLUME/nse500_data_historical"  "$APP/nse500_data_historical"
link "$VOLUME/nse500_data_gdf_full"    "$APP/nse500_data_gdf_full"
link "$VOLUME/nse500_data_full"        "$APP/nse500_data_full"
link "$VOLUME/indices_data_full"       "$APP/indices_data_full"
# fetch_indices_history.py writes to relative "indices_data/" — which
# with cwd=/app resolves to /app/indices_data, NOT /app/data/indices_data.
# The old symlink at /app/data/indices_data caught nothing and left the
# real indices output ephemeral. That was invisible until anything OUTSIDE
# a single daily_pipeline run tried to read the CSV (e.g. the EOD producer
# for om25_v3 after a redeploy). Fix by symlinking the path scripts
# actually use.
link "$VOLUME/indices_data"      "$APP/indices_data"
link "$VOLUME/instruments"       "$APP/data/instruments"
link "$VOLUME/benchmarks"        "$APP/data/benchmarks"
link "$VOLUME/final_portfolio"   "$APP/data/final_portfolio"
link "$VOLUME/nifty_100_tests"   "$APP/nifty_100_tests"
link "$VOLUME/nifty_250_tests"   "$APP/nifty_250_tests"
link "$VOLUME/experiments"       "$APP/experiments"
link "$VOLUME/logs/jobs"         "$APP/logs/jobs"
# v3 strategy portfolio dirs — see mkdir block above.
link "$VOLUME/om25_v3_portfolios"          "$APP/data/om25_v3_portfolios"
link "$VOLUME/tl25_v3_portfolios"          "$APP/data/tl25_v3_portfolios"
link "$VOLUME/l6_v2_portfolios"            "$APP/data/l6_v2_portfolios"
link "$VOLUME/combo_defensive_portfolios"  "$APP/data/combo_defensive_portfolios"

# Symlink individual files (access token, session, instruments CSV)
# For files, symlink the parent isn't practical — symlink the file directly
if [ -f "$VOLUME/tokens/access_token.txt" ]; then
    link "$VOLUME/tokens/access_token.txt" "$APP/access_token.txt"
else
    # Create empty placeholder so the symlink target exists
    touch "$VOLUME/tokens/access_token.txt"
    link "$VOLUME/tokens/access_token.txt" "$APP/access_token.txt"
fi

if [ -f "$VOLUME/tokens/session.json" ]; then
    link "$VOLUME/tokens/session.json" "$APP/session.json"
else
    touch "$VOLUME/tokens/session.json"
    link "$VOLUME/tokens/session.json" "$APP/session.json"
fi

# instruments_full.csv lives in data/ but is written by cache_instruments.py to data/instruments_full.csv
if [ -f "$VOLUME/instruments/instruments_full.csv" ]; then
    link "$VOLUME/instruments/instruments_full.csv" "$APP/data/instruments_full.csv"
else
    touch "$VOLUME/instruments/instruments_full.csv"
    link "$VOLUME/instruments/instruments_full.csv" "$APP/data/instruments_full.csv"
fi

echo "[init-storage] Persistent storage initialized successfully"
