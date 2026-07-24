"""H4 — Momentum-filtered Donchian breakout calls (daily recommendation sim).

Rules (pre-registered in PLAN.md):
  signal (day T close): fresh cross above prior N-day high, and -- for the
    filtered arm -- stock in the top quartile of the L6-style momentum score
    (126d momentum / max(vol, 0.05)) that day.
  entry: T+1 at OHLC/4 + 20bps. exit signal: close < prior M-day low ->
    T+1 at OHLC/4 - 20bps. P&L strictly net of slippage (house rule).
  capacity: max 25 concurrent calls; candidates prioritized by momentum
    rank; skipped-for-capacity logged. No pyramiding (one call per symbol
    at a time).

Arms: {filtered, unfiltered} x {55/20, 20/10}, capped; plus uncapped runs
of the 55/20 pair to prove the 25-slot cap isn't doing the work.

Also runs a validity-gate dry run on filtered calls: forward 5/20/60d
returns from signal close vs the same-date NSE-500 universe mean (matches
drift + survivorship), direction lift, and first/second-half persistence.
Note: `.shift(-k)` here is post-hoc event-study measurement of realized
forward returns, not a signal input -- the no-lookahead rule applies to
signal panels only.

Run:
    python tasks/donchian_channel/h4_breakout_calls.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tasks.donchian_channel.channel_panels import (  # noqa: E402
    load_ohlc_panels, load_universe_symbols, donchian_upper, donchian_lower,
    breakout_cross,
)

SLIPPAGE = 0.002
MAX_ACTIVE = 25
QUARTILE = 0.75          # momentum score percentile floor for filtered arm
START = pd.Timestamp("2010-06-01")   # match production breadth panel start
END = pd.Timestamp("2026-05-08")
PAIRS = ((55, 20), (20, 10))
FWD_HORIZONS = (5, 20, 60)


def simulate(close, trade, cross, exit_mask, mom_rank, *,
             filtered: bool, max_active: int | None) -> tuple[pd.DataFrame, pd.Series, dict]:
    """Event-driven simulation. Returns (calls df, active-count series, skips)."""
    cal = close.index
    cal_pos = {d: i for i, d in enumerate(cal)}
    active: dict[str, dict] = {}
    calls = []
    active_counts = {}
    n_skipped = 0

    start_i, end_i = cal_pos[cal[cal >= START][0]], cal_pos[cal[cal <= END][-1]]
    for i in range(start_i, end_i + 1):
        d = cal[i]
        # 1. exits first (frees slots same day, matching a real daily workflow)
        if active:
            ex_row = exit_mask.loc[d]
            for sym in [s for s in active if bool(ex_row.get(s, False))]:
                if i + 1 > end_i:
                    continue           # exit would execute past study end
                px = trade.iat[i + 1, trade.columns.get_loc(sym)]
                if pd.isna(px) or px <= 0:
                    continue           # retry next day
                pos = active.pop(sym)
                eff_exit = px * (1 - SLIPPAGE)
                calls.append({**pos, "exit_signal": d, "exit_date": cal[i + 1],
                              "exit_px": eff_exit,
                              "pnl_pct": eff_exit / pos["entry_px"] - 1.0,
                              "hold_days": (cal[i + 1] - pos["entry_date"]).days,
                              "status": "closed"})
        # 2. entries
        row = cross.loc[d]
        cands = [s for s in row.index[row.values] if s not in active]
        if filtered:
            ranks = mom_rank.loc[d]
            cands = [s for s in cands
                     if not pd.isna(ranks.get(s, np.nan)) and ranks[s] >= QUARTILE]
        if cands:
            ranks = mom_rank.loc[d]
            cands.sort(key=lambda s: -(ranks.get(s) if not pd.isna(ranks.get(s, np.nan)) else -1))
            for sym in cands:
                if max_active is not None and len(active) >= max_active:
                    n_skipped += sum(1 for s in cands if s not in active)
                    break
                if i + 1 > end_i:
                    continue
                px = trade.iat[i + 1, trade.columns.get_loc(sym)]
                if pd.isna(px) or px <= 0:
                    continue
                active[sym] = {"symbol": sym, "signal_date": d,
                               "entry_date": cal[i + 1],
                               "entry_px": px * (1 + SLIPPAGE),
                               "signal_close": close.iat[i, close.columns.get_loc(sym)],
                               "mom_rank": float(ranks.get(sym, np.nan))}
        active_counts[d] = len(active)

    # mark remaining open calls at final close (reported separately)
    last_d = cal[end_i]
    for sym, pos in active.items():
        px = close.iat[end_i, close.columns.get_loc(sym)]
        calls.append({**pos, "exit_signal": None, "exit_date": last_d,
                      "exit_px": px * (1 - SLIPPAGE),
                      "pnl_pct": px * (1 - SLIPPAGE) / pos["entry_px"] - 1.0,
                      "hold_days": (last_d - pos["entry_date"]).days,
                      "status": "open"})
    return (pd.DataFrame(calls), pd.Series(active_counts, dtype=float),
            {"skipped_for_capacity": int(n_skipped)})


def group_stats(calls: pd.DataFrame) -> dict:
    closed = calls[calls["status"] == "closed"]
    if closed.empty:
        return {"n": 0}
    p = closed["pnl_pct"]
    return {
        "n_closed": int(len(closed)),
        "n_open": int((calls["status"] == "open").sum()),
        "win_rate_pct": round(float((p > 0).mean()) * 100, 1),
        "mean_pnl_pct": round(float(p.mean()) * 100, 2),
        "median_pnl_pct": round(float(p.median()) * 100, 2),
        "p5_pnl_pct": round(float(p.quantile(.05)) * 100, 2),
        "p95_pnl_pct": round(float(p.quantile(.95)) * 100, 2),
        "expectancy_pct": round(float(p.mean()) * 100, 2),
        "median_hold_days": float(closed["hold_days"].median()),
        "mean_hold_days": round(float(closed["hold_days"].mean()), 1),
    }


def yearly_table(calls: pd.DataFrame) -> pd.DataFrame:
    closed = calls[calls["status"] == "closed"].copy()
    closed["year"] = pd.to_datetime(closed["signal_date"]).dt.year
    g = closed.groupby("year")["pnl_pct"]
    return pd.DataFrame({
        "n": g.size(),
        "win_rate_pct": (g.apply(lambda x: (x > 0).mean()) * 100).round(1),
        "mean_pnl_pct": (g.mean() * 100).round(2),
        "median_pnl_pct": (g.median() * 100).round(2),
    })


def portfolio_curve(calls: pd.DataFrame, close: pd.DataFrame,
                    slots: int = MAX_ACTIVE) -> pd.Series:
    """Equal-slot portfolio equivalent: each call occupies 1/slots of capital
    from entry_date to exit_date; uninvested slots earn 0."""
    cal = close.loc[(close.index >= START) & (close.index <= END)].index
    daily = pd.Series(0.0, index=cal)
    counts = pd.Series(0, index=cal, dtype=int)
    rets = close.pct_change()
    for _, c in calls.iterrows():
        sl = rets.loc[c["entry_date"]:c["exit_date"], c["symbol"]].reindex(cal).dropna()
        if len(sl) <= 1:
            continue
        sl = sl.iloc[1:]  # first day return is entry-day (already in entry px)
        daily.loc[sl.index] = daily.loc[sl.index].add(sl, fill_value=0.0)
        counts.loc[sl.index] += 1
    port_ret = daily / slots  # idle slots contribute 0
    return (1 + port_ret).cumprod()


def curve_metrics(pv: pd.Series) -> dict:
    rets = pv.pct_change().dropna()
    years = max((pv.index[-1] - pv.index[0]).days / 365.25, 1e-9)
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / years) - 1
    vol = rets.std() * math.sqrt(252)
    dd = (pv / pv.cummax() - 1).min()
    return {"cagr_pct": round(cagr * 100, 2),
            "sharpe": round((cagr - 0.05) / vol, 3) if vol > 0 else None,
            "max_dd_pct": round(dd * 100, 2)}


def validity_dry_run(calls: pd.DataFrame, close: pd.DataFrame) -> pd.DataFrame:
    """Forward-return excess vs same-date universe mean (event study)."""
    rows = []
    sig = calls.dropna(subset=["signal_date"]).copy()
    sig["signal_date"] = pd.to_datetime(sig["signal_date"])
    for k in FWD_HORIZONS:
        fwd = close.shift(-k) / close - 1.0          # post-hoc measurement
        base_mean = fwd.mean(axis=1)
        call_f, base_f = [], []
        for _, c in sig.iterrows():
            d, s = c["signal_date"], c["symbol"]
            if d in fwd.index and s in fwd.columns:
                v = fwd.loc[d, s]
                if not pd.isna(v):
                    call_f.append(v)
                    base_f.append(base_mean.loc[d])
        cf, bf = np.array(call_f), np.array(base_f)
        half = len(cf) // 2
        rows.append({
            "horizon_d": k, "n": len(cf),
            "call_mean_pct": round(float(cf.mean()) * 100, 2),
            "baseline_mean_pct": round(float(bf.mean()) * 100, 2),
            "excess_pp": round(float(cf.mean() - bf.mean()) * 100, 2),
            "direction_lift_pp": round(float((cf > 0).mean() - (bf > 0).mean()) * 100, 2),
            "excess_first_half_pp": round(float(cf[:half].mean() - bf[:half].mean()) * 100, 2),
            "excess_second_half_pp": round(float(cf[half:].mean() - bf[half:].mean()) * 100, 2),
        })
    return pd.DataFrame(rows)


def main():
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "tasks/donchian_channel/runs" / f"h4_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[h4] loading panels")
    panels = load_ohlc_panels(symbols=load_universe_symbols())
    high, low, close, trade = (panels["high"], panels["low"],
                               panels["close"], panels["trade"])

    mom = close.shift(0) / close.shift(126) - 1.0
    vol = close.pct_change().rolling(126, min_periods=63).std().clip(lower=0.05 / math.sqrt(252) * 1.0)
    # match L6 convention: daily vol floored so score is momentum / max(vol_ann, 0.05)
    vol_ann = close.pct_change().rolling(126, min_periods=63).std() * math.sqrt(252)
    score = mom / vol_ann.clip(lower=0.05)
    mom_rank = score.rank(axis=1, pct=True)

    summary_rows, val_tables, yearly = {}, {}, {}
    for entry_n, exit_m in PAIRS:
        up = donchian_upper(high, entry_n)
        lo = donchian_lower(low, exit_m)
        cross = breakout_cross(close, up).fillna(False)
        exit_mask = (close < lo).fillna(False)
        for filtered in (True, False):
            arm = f"{'filt' if filtered else 'all'}_{entry_n}_{exit_m}"
            print(f"  simulating {arm} (capped)")
            calls, counts, skips = simulate(
                close, trade, cross, exit_mask, mom_rank,
                filtered=filtered, max_active=MAX_ACTIVE)
            calls.to_csv(out_dir / f"calls_{arm}.csv", index=False)
            pv = portfolio_curve(calls, close)
            pv.to_frame("pv").to_csv(out_dir / f"pv_{arm}.csv")
            summary_rows[arm] = {
                **group_stats(calls), **skips,
                "mean_active": round(float(counts.mean()), 1),
                "pct_days_full": round(float((counts >= MAX_ACTIVE).mean()) * 100, 1),
                **{f"port_{k}": v for k, v in curve_metrics(pv).items()},
            }
            yearly[arm] = yearly_table(calls)
            if filtered:
                val_tables[arm] = validity_dry_run(calls, close[
                    [c for c in close.columns]])

    # Uncapped control for the headline pair
    up = donchian_upper(high, 55)
    lo = donchian_lower(low, 20)
    cross = breakout_cross(close, up).fillna(False)
    exit_mask = (close < lo).fillna(False)
    for filtered in (True, False):
        arm = f"{'filt' if filtered else 'all'}_55_20_uncapped"
        print(f"  simulating {arm}")
        calls, counts, skips = simulate(close, trade, cross, exit_mask,
                                        mom_rank, filtered=filtered,
                                        max_active=None)
        calls.to_csv(out_dir / f"calls_{arm}.csv", index=False)
        summary_rows[arm] = {**group_stats(calls),
                             "mean_active": round(float(counts.mean()), 1)}

    summary = pd.DataFrame(summary_rows).T
    summary.index.name = "arm"
    summary.to_csv(out_dir / "summary.csv")
    print("\n=== H4 group stats ===")
    print(summary.to_string())
    for arm, yt in yearly.items():
        yt.to_csv(out_dir / f"yearly_{arm}.csv")
        print(f"\n=== Yearly: {arm} ===")
        print(yt.to_string())
    for arm, vt in val_tables.items():
        vt.to_csv(out_dir / f"validity_{arm}.csv", index=False)
        print(f"\n=== Validity dry run (signal-date forward returns): {arm} ===")
        print(vt.to_string(index=False))

    (out_dir / "config.json").write_text(json.dumps({
        "pairs": PAIRS, "max_active": MAX_ACTIVE, "quartile": QUARTILE,
        "slippage": SLIPPAGE, "study": [str(START.date()), str(END.date())],
        "score": "126d momentum / max(annualized 126d vol, 0.05), pct-rank per day",
    }, indent=2))
    print(f"\n[wrote] {out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
