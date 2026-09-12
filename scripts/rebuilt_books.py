"""The two rebuilt books, research-locked 2026-09-11 (tasks/mm_rebuild/MECHANICS.md): LOCKED configs and the assembly that
turns the master store into one run_strategy call. Production port P2 (2026-09-12). Both read the honest master store
(price-return view, point-in-time membership) — never nse500_data — and share every device; they differ only in the score.

    mm_v1    "Momentum 25"        12-month vol-adjusted momentum (21-session skip)
    om25_v4  "Quality Momentum"   50/50 rank blend of that momentum with the capture ratio
"""
from __future__ import annotations
import os, sys
from pathlib import Path
import pandas as pd

ROOT = Path(os.environ.get("KITE_LAB_ROOT", Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from data_pipeline.master_store import MASTER  # noqa: E402
from data_pipeline.master_store.views import ensure_panel_views  # noqa: E402
from data_pipeline.strategies.momentum import make_momentum_score  # noqa: E402
from data_pipeline.strategies.capture import make_capture_score  # noqa: E402
from data_pipeline.strategies.blend import make_blend_score  # noqa: E402
from data_pipeline.strategies.regime import roc_regime  # noqa: E402
from data_pipeline.strategies.sizing import make_inverse_vol_weights, make_bear_top_n, truncate_in_bear  # noqa: E402
from data_pipeline.strategies.calendar import monthly_on_or_after  # noqa: E402
from data_pipeline.strategies.sectors import load_sector_map  # noqa: E402
from scripts._clean_engine import run_strategy  # noqa: E402
from scripts.backtest_momentum import load_price_panels, load_benchmark  # noqa: E402
from scripts.universe_membership import resolve_universe  # noqa: E402

STACK = dict(universe="nifty250", lookback=252, top_n=25, exit_buffer=20, cadence="monthly", rebalance_day=1,
             sizing="invvol", iv_window=63, max_weight=0.10, sector_cap=5,
             regime_index="NIFTY_100", roc_n=31, confirm=3, bear_n=15, bear_buffer=20,
             trailing_stop=0.20, stop_check="monthly", fill_from_buffer=True, slippage=0.002, initial_capital=1_000_000,
             lock_date="2026-09-11")
LOCKED = {
    "mm_v1":   dict(STACK, name="Momentum 25", score="voladj", skip=21, min_obs=219),
    "om25_v4": dict(STACK, name="Quality Momentum", score="mix", mix_w=0.5, skip=21, min_obs=220),
}
BOOKS = tuple(LOCKED)


def build_and_run(book: str, start: str, end: str | None = None, master: Path | None = None, verbose=print, overrides: dict | None = None):
    """Assemble the book from the store and run it. Returns (cfg, result dict, signals DataFrame, regime Series, close panel)."""
    cfg = dict(LOCKED[book], **(overrides or {})); master = Path(master or MASTER)   # overrides: research probes only; production runs the LOCKED config
    ensure_panel_views(master)
    close, trade = load_price_panels(master / "panels/pr"); cal = close.index
    bench = load_benchmark(master / f"benchmarks/{cfg['regime_index']}_bench.csv").reindex(cal).ffill()
    universe, membership_fn, candidate_fn = resolve_universe(master / f"membership/{cfg['universe']}.csv", master / f"membership/{cfg['universe']}.csv")
    cols = [s for s in close.columns if s in universe]; returns_uni = close[cols].pct_change()
    verbose(f"  store {master} · {len(cols)} members ever · calendar {cal[0].date()} → {cal[-1].date()}")
    regime = roc_regime(master / f"benchmarks/{cfg['regime_index']}.csv", cfg["roc_n"], cfg["confirm"], cal).reindex(cal).ffill().fillna(True).astype(bool)
    mom = make_momentum_score(returns_uni, kind="voladj", lookback=cfg["lookback"], min_obs=cfg["min_obs"], skip=cfg["skip"], candidate_fn=candidate_fn)
    if cfg["score"] == "voladj":
        score = mom
    else:
        cr = make_capture_score(returns_uni, None, w_uc_bull=0.0, w_cr_bull=1.0, return_filter=True, lookback=cfg["lookback"], min_obs=cfg["min_obs"], candidate_fn=candidate_fn)
        score = make_blend_score(mom, cr, cfg["mix_w"])
    score = truncate_in_bear(score, regime, cfg["bear_n"] + cfg["bear_buffer"])          # exits at rank 35 in bear
    top_n_fn = make_bear_top_n(regime, cfg["top_n"], cfg["bear_n"])                        # entries capped at 15 in bear
    size_weights = make_inverse_vol_weights(returns_uni, cfg["iv_window"], cfg["max_weight"])
    sector_of = load_sector_map()
    start_ts, end_ts = pd.Timestamp(start), (pd.Timestamp(end) if end else cal[-1])
    monthly = monthly_on_or_after(cal, cfg["rebalance_day"]); entries = monthly[(monthly >= start_ts) & (monthly <= end_ts)]
    res = run_strategy(close_panel=close, trade_panel=trade, calendar=cal, benchmark_aligned=bench,
                       entry_signal_dates=entries, weekly_signal_dates=entries,          # the stop is checked at the monthly signal (one action day)
                       signal_function=score, signal_function_args={},
                       sma_200_panel=close.rolling(200, min_periods=200).mean(), atr_20_panel=close.pct_change().rolling(20).std(),
                       top_n=cfg["top_n"], exit_buffer=cfg["exit_buffer"], max_weight=cfg["max_weight"], slippage=cfg["slippage"],
                       atr_mult=0.0, atr_min_floor=cfg["trailing_stop"], use_trailing_stop=True, use_dma_exit=False,
                       weekly_rank_check=False, regime_panel=None, bear_exposure=0.0, membership_fn=membership_fn,
                       size_weights=size_weights, top_n_fn=top_n_fn, sector_of=sector_of, sector_cap=cfg["sector_cap"],
                       fill_from_buffer=cfg["fill_from_buffer"], initial_capital=cfg["initial_capital"],
                       stop_reentry_block=cfg.get("stop_reentry_block", 0))
    rows = []
    for ed in entries:
        sc = score(ed)
        if sc is None or sc.empty:
            continue
        for rank, (sym, v) in enumerate(sc.sort_values(ascending=False).head(cfg["top_n"] + cfg["exit_buffer"]).items(), 1):
            rows.append({"date": ed, "rank": rank, "symbol": sym, "score": round(float(v), 4), "regime": "bull" if bool(regime.get(ed, True)) else "bear"})
    return cfg, res, pd.DataFrame(rows), regime, close
