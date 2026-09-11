"""VCP (Volatility Contraction Pattern) study on NSE 500, gated to the
top quartile of stocks by L6 momentum (raw 126-day return, point-in-time).

Quick research probe -- per-trade event stats, not a capital-constrained
portfolio. Three strictness tiers are run over the same candidate stream:
  strict   -- the full Minervini spec as provided (all gates)
  standard -- core structure + volume dry-up, softened thresholds
  loose    -- contracting structure only, no volume/tightness checks

Run:  .venv/bin/python tasks/vcp_l6_study/vcp_backtest.py
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "nse500_data_merged"
UNIVERSE_CSV = ROOT / "data/static/nse500_universe.csv"
INDEX_CSV = ROOT / "indices_data/NIFTY_500.csv"
OUT_DIR = Path(__file__).resolve().parent

# ---- shared parameters ------------------------------------------------
FRACTAL_N = 5              # +/- bars for swing pivots
BASE_MIN_BARS, BASE_MAX_BARS = 15, 325   # 3 to 65 weeks
PRIOR_ADVANCE_MIN = 0.30   # 30%+ advance in the 126 bars before base start
ABOVE_LOW_MIN = 0.30       # close >= 30% above 52w low
NEAR_HIGH_MAX = 0.25       # close within 25% of 52w high
BREAKOUT_BUFFER = 1.001    # close > pivot * 1.001
BREAKOUT_VOL_MULT = 1.5    # volume >= 1.5x 50d avg
BREAKOUT_WINDOW = 60       # bars after pivot confirmation to catch breakout
L6_LOOKBACK = 126
L6_QUARTILE = 0.75         # top quartile cross-sectionally (subsumes RS>=70)
SLIPPAGE = 0.002
STOP_CAP = 0.08            # stop no wider than 8% below entry
PARTIAL_GAIN = 0.20        # sell half into 20% strength

TIERS = {
    "strict": dict(
        min_contractions=2, max_contractions=6,
        tighten_ratio=0.85,          # C[i+1] < C[i] * ratio
        first_leg=(0.15, 0.35), final_leg_max=0.10,
        vol_dryup=0.60,              # final avg vol < ratio * first avg vol
        check_lowvol_position=True,  # lowest-vol day in last third of base
        check_accumulation=True,     # down-day vol < up-day vol
        tight_bars=5, tight_range=0.05,
    ),
    "standard": dict(
        min_contractions=2, max_contractions=6,
        tighten_ratio=1.00,
        first_leg=(0.10, 0.50), final_leg_max=0.12,
        vol_dryup=0.75,
        check_lowvol_position=False,
        check_accumulation=False,
        tight_bars=5, tight_range=0.07,
    ),
    "loose": dict(
        min_contractions=2, max_contractions=8,
        tighten_ratio=1.00,
        first_leg=(0.08, 0.50), final_leg_max=0.15,
        vol_dryup=None,
        check_lowvol_position=False,
        check_accumulation=False,
        tight_bars=None, tight_range=None,
    ),
}
# controls: same specs with the L6 top-quartile gate removed, to isolate
# what the momentum gate contributes to the pattern's edge
TIERS["standard_no_l6"] = dict(TIERS["standard"], l6_gate=False)
TIERS["loose_no_l6"] = dict(TIERS["loose"], l6_gate=False)


def load_panels():
    frames = {}
    universe = set(pd.read_csv(UNIVERSE_CSV)["Symbol"].str.strip())
    for f in sorted(DATA_DIR.glob("*_day.csv")):
        sym = f.name[: -len("_day.csv")]
        if sym not in universe:
            continue
        df = pd.read_csv(f, parse_dates=["date"]).set_index("date")
        frames[sym] = df
    panels = {}
    for col in ["open", "high", "low", "close", "volume"]:
        panels[col] = pd.DataFrame({s: d[col] for s, d in frames.items()}).sort_index()
    return panels


def find_pivots(high: np.ndarray, low: np.ndarray, n: int = FRACTAL_N):
    """Chronological list of (bar_index, 'H'|'L', price). A pivot at i is
    confirmed at i + n. Consecutive same-type pivots merge to the extreme."""
    T = len(high)
    raw = []
    for i in range(n, T - n):
        w_hi = high[i - n : i + n + 1]
        w_lo = low[i - n : i + n + 1]
        if high[i] == w_hi.max() and (w_hi == high[i]).sum() == 1:
            raw.append((i, "H", high[i]))
        if low[i] == w_lo.min() and (w_lo == low[i]).sum() == 1:
            raw.append((i, "L", low[i]))
    merged = []
    for p in raw:
        if merged and merged[-1][1] == p[1]:
            keep_new = (p[1] == "H" and p[2] >= merged[-1][2]) or (
                p[1] == "L" and p[2] <= merged[-1][2]
            )
            if keep_new:
                merged[-1] = p
        else:
            merged.append(p)
    return merged


def base_structure(pivots, k):
    """Walk back from the final swing high pivots[k]. Inside a contracting
    base, older swing highs ascend toward the base high; the first older
    high that sits below the last-accepted high marks the end of the base
    (it belongs to the prior advance). Returns (base_start_pivot_index)."""
    ph = pivots[k]
    last_high = ph[2]
    start = k
    i = k - 1
    while i >= 0:
        p = pivots[i]
        if ph[0] - p[0] > BASE_MAX_BARS:
            break
        if p[1] == "H":
            if p[2] >= last_high * 0.98:
                last_high = max(last_high, p[2])
                start = i
            else:
                break
        i -= 1
    return start


def contraction_legs(pivots, start, k):
    """Contraction list between base start and final swing high, as
    (hi_idx, hi, lo_idx, lo, depth) for each swing-high -> swing-low leg."""
    chron = pivots[start : k + 1]
    legs = []
    m = 0
    while m < len(chron):
        if chron[m][1] == "H" and m + 1 < len(chron) and chron[m + 1][1] == "L":
            h, l = chron[m], chron[m + 1]
            legs.append(dict(hi_idx=h[0], hi=h[2], lo_idx=l[0], lo=l[2],
                             depth=(h[2] - l[2]) / h[2]))
            m += 2
        else:
            m += 1
    return legs


def detect_and_trade():
    panels = load_panels()
    close_p, open_p, high_p, low_p, vol_p = (
        panels["close"], panels["open"], panels["high"], panels["low"], panels["volume"],
    )
    dates = close_p.index
    idx_df = pd.read_csv(INDEX_CSV, parse_dates=["date"]).set_index("date")
    bench = idx_df["close"].reindex(dates).ffill()

    ret126 = close_p / close_p.shift(L6_LOOKBACK) - 1.0
    l6_rank = ret126.rank(axis=1, pct=True)          # point-in-time percentile
    sma50 = close_p.rolling(50).mean()
    sma150 = close_p.rolling(150).mean()
    sma200 = close_p.rolling(200).mean()
    sma200_prev = sma200.shift(21)
    hi52 = high_p.rolling(252).max()
    lo52 = low_p.rolling(252).min()
    vol50 = vol_p.rolling(50).mean()

    funnels = {t: Counter() for t in TIERS}
    trades = {t: [] for t in TIERS}
    in_trade_until = {t: {} for t in TIERS}   # tier -> sym -> bar idx

    for sym in close_p.columns:
        c = close_p[sym].dropna()
        if len(c) < 300:
            continue
        o = open_p[sym].reindex(c.index).to_numpy()
        h = high_p[sym].reindex(c.index).to_numpy()
        l = low_p[sym].reindex(c.index).to_numpy()
        v = vol_p[sym].reindex(c.index).to_numpy()
        cl = c.to_numpy()
        n = len(cl)
        s50 = sma50[sym].reindex(c.index).to_numpy()
        s150 = sma150[sym].reindex(c.index).to_numpy()
        s200 = sma200[sym].reindex(c.index).to_numpy()
        s200p = sma200_prev[sym].reindex(c.index).to_numpy()
        h52 = hi52[sym].reindex(c.index).to_numpy()
        l52 = lo52[sym].reindex(c.index).to_numpy()
        v50 = vol50[sym].reindex(c.index).to_numpy()
        l6r = l6_rank[sym].reindex(c.index).to_numpy()

        pivots = find_pivots(h, l)

        for k, ph in enumerate(pivots):
            if ph[1] != "H":
                continue
            pi, _, pivot_price = ph
            confirm = pi + FRACTAL_N
            bo = None
            for j in range(confirm + 1, min(pi + BREAKOUT_WINDOW, n)):
                if cl[j] > pivot_price * BREAKOUT_BUFFER:
                    bo = j
                    break
                if h[j] > pivot_price * 1.02 and cl[j] <= pivot_price:
                    break  # poked above and failed; structure changed
            if bo is None or bo + 1 >= n or bo - pi < 2:
                continue

            # ---- gates shared by all tiers ----
            shared_fail = None
            if np.isnan(v50[bo]) or not (v[bo] >= BREAKOUT_VOL_MULT * v50[bo]):
                shared_fail = "fail_breakout_volume"
            elif np.isnan(s200p[bo]) or not (
                cl[bo] > s50[bo] > s150[bo] > s200[bo]
                and s200[bo] > s200p[bo]
                and cl[bo] >= (1 + ABOVE_LOW_MIN) * l52[bo]
                and cl[bo] >= (1 - NEAR_HIGH_MAX) * h52[bo]
            ):
                shared_fail = "fail_trend_template"
            l6_fail = np.isnan(l6r[bo]) or l6r[bo] < L6_QUARTILE

            start = base_structure(pivots, k)
            base_start = pivots[start][0]
            base_len = bo - base_start
            legs = contraction_legs(pivots, start, k)
            final_low = l[pi + 1 : bo].min()
            final_depth = (pivot_price - final_low) / pivot_price
            depths = [lg["depth"] for lg in legs] + [final_depth]

            for tier, cfg in TIERS.items():
                fn = funnels[tier]
                fn["breakout_candidates"] += 1
                if bo <= in_trade_until[tier].get(sym, -1):
                    fn["skip_in_trade"] += 1
                    continue
                if shared_fail:
                    fn[shared_fail] += 1
                    continue
                if cfg.get("l6_gate", True) and l6_fail:
                    fn["fail_l6_quartile"] += 1
                    continue
                if not (BASE_MIN_BARS <= base_len <= BASE_MAX_BARS):
                    fn["fail_base_length"] += 1
                    continue
                if not (cfg["min_contractions"] <= len(depths) <= cfg["max_contractions"]):
                    fn["fail_contraction_count"] += 1
                    continue
                if not (cfg["first_leg"][0] <= depths[0] <= cfg["first_leg"][1]):
                    fn["fail_first_leg_depth"] += 1
                    continue
                if final_depth >= cfg["final_leg_max"]:
                    fn["fail_final_leg_depth"] += 1
                    continue
                if any(depths[i + 1] >= depths[i] * cfg["tighten_ratio"]
                       for i in range(len(depths) - 1)):
                    fn["fail_monotonic_tightening"] += 1
                    continue
                pre_lo = l[max(0, base_start - 126) : base_start]
                if len(pre_lo) < 30 or (h[base_start] / pre_lo.min() - 1) < PRIOR_ADVANCE_MIN:
                    fn["fail_prior_advance"] += 1
                    continue
                if cfg["vol_dryup"] is not None:
                    first = legs[0]
                    v_first = v[first["hi_idx"] : first["lo_idx"] + 1].mean()
                    v_final = v[pi : bo].mean()
                    if not (v_final < cfg["vol_dryup"] * v_first):
                        fn["fail_vol_dryup"] += 1
                        continue
                if cfg["check_lowvol_position"]:
                    base_v = v[base_start:bo]
                    if np.argmin(base_v) < len(base_v) * (2 / 3):
                        fn["fail_lowvol_day_position"] += 1
                        continue
                if cfg["check_accumulation"]:
                    base_v = v[base_start:bo]
                    base_cl = cl[base_start:bo]
                    base_ret = np.diff(base_cl, prepend=base_cl[0])
                    up_v = base_v[base_ret > 0]
                    dn_v = base_v[base_ret < 0]
                    if len(up_v) == 0 or len(dn_v) == 0 or dn_v.mean() >= up_v.mean():
                        fn["fail_accumulation"] += 1
                        continue
                if cfg["tight_bars"] is not None:
                    t0 = max(base_start, bo - cfg["tight_bars"])
                    if (h[t0:bo].max() - l[t0:bo].min()) / pivot_price >= cfg["tight_range"]:
                        fn["fail_tightness"] += 1
                        continue
                fn["signals"] += 1

                tr = simulate_trade(sym, c, o, h, l, cl, s50, n, bo, pivot_price,
                                    final_low, depths, base_len, bench)
                tr["l6_pct"] = round(float(l6r[bo]), 3) if not np.isnan(l6r[bo]) else None
                in_trade_until[tier][sym] = tr.pop("_exit_i")
                trades[tier].append(tr)

    return trades, funnels


def simulate_trade(sym, c, o, h, l, cl, s50, n, bo, pivot_price, final_low,
                   depths, base_len, bench):
    """Minervini-style exits: hard stop at final-contraction low (capped 8%),
    sell half into 20% strength (stop to breakeven), trail rest on a close
    below the 50DMA."""
    e = bo + 1
    entry = o[e] * (1 + SLIPPAGE)
    stop = max(final_low, entry * (1 - STOP_CAP))
    stop_init = stop
    partial_done = False
    realized = 0.0
    weight_open = 1.0
    exit_i, exit_reason, still_open = None, None, False
    for t in range(e, n):
        if l[t] <= stop:
            px = min(o[t], stop) * (1 - SLIPPAGE)
            realized += weight_open * (px / entry - 1)
            weight_open = 0.0
            exit_i = t
            exit_reason = "stop" if not partial_done else "trail_stop"
            break
        if not partial_done and cl[t] >= entry * (1 + PARTIAL_GAIN):
            realized += 0.5 * (cl[t] * (1 - SLIPPAGE) / entry - 1)
            weight_open = 0.5
            partial_done = True
            stop = max(stop, entry)
        if t > e and not np.isnan(s50[t]) and cl[t] < s50[t]:
            px = cl[t] * (1 - SLIPPAGE)
            realized += weight_open * (px / entry - 1)
            weight_open = 0.0
            exit_i, exit_reason = t, "trail_50dma"
            break
    if weight_open > 0:
        realized += weight_open * (cl[n - 1] * (1 - SLIPPAGE) / entry - 1)
        exit_i, exit_reason, still_open = n - 1, "open_at_end", True

    d_entry, d_exit = c.index[e], c.index[exit_i]
    b0, b1 = bench.asof(d_entry), bench.asof(d_exit)
    has_bench = pd.notna(b0) and pd.notna(b1)
    bench_ret = (b1 / b0 - 1) if has_bench else np.nan
    risk = entry - stop_init
    return dict(
        symbol=sym, entry_date=str(d_entry.date()), exit_date=str(d_exit.date()),
        entry=round(entry, 2), pivot=round(pivot_price, 2),
        stop_pct=round((entry - stop_init) / entry, 4),
        n_contractions=len(depths),
        first_depth=round(depths[0], 3), final_depth=round(depths[-1], 3),
        base_weeks=round(base_len / 5, 1),
        ret=round(realized, 4),
        r_multiple=round(realized * entry / risk, 2) if risk > 0 else None,
        hold_days=exit_i - e, exit_reason=exit_reason,
        partial=partial_done, open_at_end=still_open,
        bench_ret=round(bench_ret, 4) if has_bench else None,
        alpha=round(realized - bench_ret, 4) if has_bench else None,
        _exit_i=exit_i,
    )


def summarize(trades, funnel):
    df = pd.DataFrame(trades)
    out = {"funnel": dict(funnel), "n_trades": len(df)}
    if not len(df):
        return out, df
    wins = df[df.ret > 0]
    losses = df[df.ret <= 0]
    out["stats"] = dict(
        n=len(df),
        n_open_at_end=int(df.open_at_end.sum()),
        win_rate=round(len(wins) / len(df), 3),
        avg_ret=round(df.ret.mean(), 4),
        median_ret=round(df.ret.median(), 4),
        avg_win=round(wins.ret.mean(), 4) if len(wins) else None,
        avg_loss=round(losses.ret.mean(), 4) if len(losses) else None,
        expectancy_R=round(df.r_multiple.dropna().mean(), 2),
        avg_hold_days=round(df.hold_days.mean(), 1),
        median_hold_days=int(df.hold_days.median()),
        avg_alpha=round(df.alpha.dropna().mean(), 4),
        median_alpha=round(df.alpha.dropna().median(), 4),
        pct_partial=round(df.partial.mean(), 3),
    )
    df = df.copy()
    df["year"] = df.entry_date.str[:4]
    out["by_year"] = {
        y: dict(n=len(g), win_rate=round((g.ret > 0).mean(), 3),
                avg_ret=round(g.ret.mean(), 4),
                avg_alpha=round(g.alpha.dropna().mean(), 4) if g.alpha.notna().any() else None)
        for y, g in df.groupby("year")
    }
    out["exit_reasons"] = df.exit_reason.value_counts().to_dict()
    return out, df


if __name__ == "__main__":
    all_trades, funnels = detect_and_trade()
    result = {}
    for tier in TIERS:
        summary, df = summarize(all_trades[tier], funnels[tier])
        result[tier] = summary
        df.to_csv(OUT_DIR / f"trades_{tier}.csv", index=False)
    (OUT_DIR / "summary.json").write_text(json.dumps(result, indent=2))
    for tier in TIERS:
        s = result[tier]
        print(f"\n=== {tier} ===")
        print(json.dumps({k: s[k] for k in ("n_trades", "stats") if k in s}, indent=2))
