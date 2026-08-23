"""Oversold mean-reversion study on Nifty 100 large caps (Connors-style).

Setup: stock above its 200DMA, market regime filter (Nifty 100 index
above its 200DMA), buy after a short sharp selloff, exit into the first
strength (close > 5DMA) or a 10-day time stop. Per-trade event stats.

Entry variants: RSI(2)<10, RSI(2)<5, 4+ consecutive down closes,
5-day return < -5%. Ablations on the RSI(2)<10 base: regime filter off,
-7% hard stop on.

Run:  .venv/bin/python tasks/meanrev_largecap_study/meanrev_backtest.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "nse500_data_merged"
UNIVERSE_CSV = ROOT / "data/static/nifty100_universe.csv"
INDEX_HIST = ROOT / "indices_data_historical/NIFTY_100.csv"
INDEX_LIVE = ROOT / "indices_data/NIFTY_100.csv"
OUT_DIR = Path(__file__).resolve().parent

SLIPPAGE = 0.001          # each side; Nifty 100 liquidity
EXIT_SMA = 5              # exit on close > 5DMA
TIME_STOP = 10            # trading days
STOCK_TREND_SMA = 200

# Unadjusted corporate actions found in nse500_data_merged (one-day close
# drops matching bonus/demerger ratios, verified by eye). Trades whose
# window spans one of these dates are excluded as data artifacts.
ARTIFACTS = {
    ("ZYDUSLIFE", "2010-04-05"),   # ~-33.5%, 1:2 bonus signature
    ("MOTHERSON", "2013-12-20"),   # ~-31.3%, 1:2 bonus signature
    ("ADANIENT", "2015-06-03"),    # ~-82.8%, ports/power/transmission demerger
    ("TRENT", "2026-05-29"),       # ~-33.7%, 1:2 bonus signature
}

VARIANTS = {
    "rsi2_10":      dict(entry="rsi2", thr=10, regime=True,  stop=None),
    "rsi2_5":       dict(entry="rsi2", thr=5,  regime=True,  stop=None),
    "down4":        dict(entry="down", thr=4,  regime=True,  stop=None),
    "drop5d":       dict(entry="drop", thr=-0.05, regime=True, stop=None),
    "rsi2_10_noregime": dict(entry="rsi2", thr=10, regime=False, stop=None),
    "rsi2_10_stop7":    dict(entry="rsi2", thr=10, regime=True,  stop=0.07),
}


def load_index():
    hist = pd.read_csv(INDEX_HIST, parse_dates=["date"]).set_index("date")["close"]
    live = pd.read_csv(INDEX_LIVE, parse_dates=["date"]).set_index("date")["close"]
    idx = pd.concat([hist, live[live.index > hist.index.max()]]).sort_index()
    return idx


def rsi2(close: np.ndarray) -> np.ndarray:
    delta = np.diff(close, prepend=close[0])
    gain = pd.Series(np.where(delta > 0, delta, 0.0))
    loss = pd.Series(np.where(delta < 0, -delta, 0.0))
    ag = gain.ewm(alpha=0.5, adjust=False).mean()
    al = loss.ewm(alpha=0.5, adjust=False).mean()
    rs = ag / al.replace(0, np.nan)
    out = (100 - 100 / (1 + rs)).to_numpy()
    out[al.to_numpy() == 0] = 100.0
    return out


def run():
    universe = pd.read_csv(UNIVERSE_CSV)["Symbol"].str.strip().tolist()
    idx = load_index()
    idx_sma200 = idx.rolling(200).mean()
    regime_ok = (idx > idx_sma200)

    trades = {v: [] for v in VARIANTS}

    for sym in universe:
        f = DATA_DIR / f"{sym}_day.csv"
        df = pd.read_csv(f, parse_dates=["date"]).set_index("date")
        if len(df) < 300:
            continue
        cl = df["close"].to_numpy()
        op = df["open"].to_numpy()
        lo = df["low"].to_numpy()
        n = len(cl)
        dts = df.index
        s5 = df["close"].rolling(EXIT_SMA).mean().to_numpy()
        s200 = df["close"].rolling(STOCK_TREND_SMA).mean().to_numpy()
        r = rsi2(cl)
        downs = np.zeros(n)
        for i in range(1, n):
            downs[i] = downs[i - 1] + 1 if cl[i] < cl[i - 1] else 0
        ret5 = np.full(n, np.nan)
        ret5[5:] = cl[5:] / cl[:-5] - 1
        reg = regime_ok.reindex(dts).ffill().fillna(False).to_numpy()
        ib0 = idx.reindex(dts).ffill().to_numpy()

        for name, cfg in VARIANTS.items():
            if cfg["entry"] == "rsi2":
                sig = r < cfg["thr"]
            elif cfg["entry"] == "down":
                sig = downs >= cfg["thr"]
            else:
                sig = ret5 < cfg["thr"]
            sig &= ~np.isnan(s200) & (cl > s200)
            if cfg["regime"]:
                sig &= reg

            t_list = trades[name]
            i = STOCK_TREND_SMA
            while i < n - 1:
                if not sig[i]:
                    i += 1
                    continue
                e = i + 1
                entry = op[e] * (1 + SLIPPAGE)
                stop_px = entry * (1 - cfg["stop"]) if cfg["stop"] else None
                exit_i, exit_reason, px = None, None, None
                for t in range(e, min(e + TIME_STOP + 1, n)):
                    if stop_px is not None and lo[t] <= stop_px:
                        px = min(op[t], stop_px) * (1 - SLIPPAGE)
                        exit_i, exit_reason = t, "stop"
                        break
                    if t > e and not np.isnan(s5[t]) and cl[t] > s5[t]:
                        px = cl[t] * (1 - SLIPPAGE)
                        exit_i, exit_reason = t, "sma5_cross"
                        break
                    if t - e >= TIME_STOP:
                        px = cl[t] * (1 - SLIPPAGE)
                        exit_i, exit_reason = t, "time_stop"
                        break
                if exit_i is None:
                    exit_i = n - 1
                    px = cl[exit_i] * (1 - SLIPPAGE)
                    exit_reason = "open_at_end"
                ret = px / entry - 1
                b1 = idx.reindex([dts[exit_i]]).ffill().iloc[0]
                bench_ret = b1 / ib0[e] - 1 if ib0[e] and not np.isnan(ib0[e]) else np.nan
                t_list.append(dict(
                    symbol=sym, entry_date=str(dts[e].date()),
                    exit_date=str(dts[exit_i].date()),
                    ret=round(ret, 4), hold_days=exit_i - e,
                    exit_reason=exit_reason,
                    bench_ret=round(bench_ret, 4) if not np.isnan(bench_ret) else None,
                    alpha=round(ret - bench_ret, 4) if not np.isnan(bench_ret) else None,
                ))
                i = exit_i + 1   # one open trade per symbol
    return trades


def summarize(t_list):
    df = pd.DataFrame(t_list)
    if not len(df):
        return {}, df
    bad = df.apply(
        lambda t: any(s == t.symbol and t.entry_date <= d <= t.exit_date
                      for s, d in ARTIFACTS), axis=1)
    df = df[~bad].reset_index(drop=True)
    wins = df[df.ret > 0]
    losses = df[df.ret <= 0]
    gross_w = wins.ret.sum()
    gross_l = -losses.ret.sum()
    # concurrency: open positions per calendar day
    ent = pd.to_datetime(df.entry_date)
    ext = pd.to_datetime(df.exit_date)
    days = pd.date_range(ent.min(), ext.max(), freq="B")
    conc = pd.Series(0, index=days)
    for a, b in zip(ent, ext):
        conc[a:b] += 1
    active = conc[conc > 0]
    df2 = df.copy()
    df2["year"] = df2.entry_date.str[:4]
    out = dict(
        n=len(df),
        win_rate=round(len(wins) / len(df), 3),
        avg_ret=round(df.ret.mean(), 4),
        median_ret=round(df.ret.median(), 4),
        avg_win=round(wins.ret.mean(), 4) if len(wins) else None,
        avg_loss=round(losses.ret.mean(), 4) if len(losses) else None,
        profit_factor=round(gross_w / gross_l, 2) if gross_l > 0 else None,
        avg_hold_days=round(df.hold_days.mean(), 1),
        avg_alpha=round(df.alpha.dropna().mean(), 4),
        worst_trade=round(df.ret.min(), 4),
        p5_ret=round(df.ret.quantile(0.05), 4),
        trades_per_year=round(len(df) / max(1, len(df2.year.unique())), 1),
        avg_concurrent=round(active.mean(), 1),
        max_concurrent=int(conc.max()),
        exit_reasons=df.exit_reason.value_counts().to_dict(),
        by_year={y: dict(n=len(g), wr=round((g.ret > 0).mean(), 3),
                         avg=round(g.ret.mean(), 4))
                 for y, g in df2.groupby("year")},
    )
    return out, df


if __name__ == "__main__":
    all_trades = run()
    result = {}
    for name in VARIANTS:
        s, df = summarize(all_trades[name])
        result[name] = s
        df.to_csv(OUT_DIR / f"trades_{name}.csv", index=False)
    (OUT_DIR / "summary.json").write_text(json.dumps(result, indent=2))
    hdr = ["variant", "n", "wr", "avg", "med", "pf", "hold", "alpha", "worst", "p5", "conc"]
    print(("{:<18}" + "{:>8}" * (len(hdr) - 1)).format(*hdr))
    for name, s in result.items():
        if not s:
            continue
        print(("{:<18}" + "{:>8}" * (len(hdr) - 1)).format(
            name, s["n"], s["win_rate"], s["avg_ret"], s["median_ret"],
            s["profit_factor"], s["avg_hold_days"], s["avg_alpha"],
            s["worst_trade"], s["p5_ret"], s["avg_concurrent"]))
