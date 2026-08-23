"""Capacity-capped portfolio simulation of the drop5d mean-reversion
variant (5-day return < -5%, stock > 200DMA, regime on).

Day-by-day: signals at close t fill at open t+1, ranked deepest 5-day
drop first, max 25 concurrent positions, 4% of current equity per
position. Exit close > 5DMA or 10-day time stop, no hard stop.
Entries limited to the last 3 years (from 2023-08-23).

Run:  .venv/bin/python tasks/meanrev_largecap_study/capped_sim.py
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

START = "2023-08-23"      # first allowed entry signal date
MAX_POS = 25
POS_FRAC = 0.04           # 4% of current equity per position
SLIPPAGE = 0.001
DROP_THR = -0.05
EXIT_SMA = 5
TIME_STOP = 10

# TRENT 2026-05-29 unadjusted bonus: block entries whose window could span it
ARTIFACT_BLOCK = {"TRENT": ("2026-05-08", "2026-06-05")}


def load_index():
    hist = pd.read_csv(INDEX_HIST, parse_dates=["date"]).set_index("date")["close"]
    live = pd.read_csv(INDEX_LIVE, parse_dates=["date"]).set_index("date")["close"]
    return pd.concat([hist, live[live.index > hist.index.max()]]).sort_index()


def main():
    universe = pd.read_csv(UNIVERSE_CSV)["Symbol"].str.strip().tolist()
    idx = load_index()
    regime = (idx > idx.rolling(200).mean())

    data = {}
    for sym in universe:
        df = pd.read_csv(DATA_DIR / f"{sym}_day.csv", parse_dates=["date"]).set_index("date")
        if len(df) < 300:
            continue
        df["s5"] = df["close"].rolling(EXIT_SMA).mean()
        df["s200"] = df["close"].rolling(200).mean()
        df["ret5"] = df["close"] / df["close"].shift(5) - 1
        data[sym] = df

    dates = sorted(set().union(*[d.index for d in data.values()]))
    dates = [d for d in dates if str(d.date()) >= "2023-01-01"]
    regime = regime.reindex(pd.Index(dates)).ffill().fillna(False)

    equity = 1.0
    cash = 1.0
    positions = {}            # sym -> dict
    pending = []              # (depth, sym) signals from yesterday
    trades = []
    curve = []
    skipped_cap = 0
    signal_days = 0

    for d in dates:
        # 1) entries at the open from yesterday's signals
        pending.sort()        # most negative 5d return first
        for depth, sym in pending:
            if len(positions) >= MAX_POS:
                skipped_cap += 1
                continue
            if sym in positions:
                continue
            df = data[sym]
            if d not in df.index:
                continue
            px = df.at[d, "open"] * (1 + SLIPPAGE)
            invest = equity * POS_FRAC
            if invest > cash:
                skipped_cap += 1
                continue
            cash -= invest
            positions[sym] = dict(entry_px=px, invest=invest, entry_date=d,
                                  days=0, depth=depth)
        pending = []

        # 2) exits at the close
        for sym in list(positions):
            p = positions[sym]
            df = data[sym]
            if d not in df.index:
                continue
            if p["entry_date"] == d:
                continue
            p["days"] += 1
            cl, s5 = df.at[d, "close"], df.at[d, "s5"]
            if (not np.isnan(s5) and cl > s5) or p["days"] >= TIME_STOP:
                sell = cl * (1 - SLIPPAGE)
                ret = sell / p["entry_px"] - 1
                cash += p["invest"] * (1 + ret)
                trades.append(dict(
                    symbol=sym, entry_date=str(p["entry_date"].date()),
                    exit_date=str(d.date()), ret=round(ret, 4),
                    hold_days=p["days"], depth=round(p["depth"], 4),
                    exit_reason="sma5_cross" if cl > s5 else "time_stop",
                ))
                del positions[sym]

        # 3) mark to market
        mtm = cash
        for sym, p in positions.items():
            df = data[sym]
            cl = df.at[d, "close"] if d in df.index else np.nan
            if np.isnan(cl):
                cl = p["entry_px"]
            mtm += p["invest"] * (cl / p["entry_px"])
        equity = mtm
        curve.append((d, equity, len(positions)))

        # 4) tonight's signals -> tomorrow's entries
        if str(d.date()) < START or not regime.loc[d]:
            continue
        found = False
        for sym, df in data.items():
            if d not in df.index or sym in positions:
                continue
            blk = ARTIFACT_BLOCK.get(sym)
            if blk and blk[0] <= str(d.date()) <= blk[1]:
                continue
            r5, cl, s200 = df.at[d, "ret5"], df.at[d, "close"], df.at[d, "s200"]
            if np.isnan(r5) or np.isnan(s200):
                continue
            if r5 < DROP_THR and cl > s200:
                pending.append((r5, sym))
                found = True
        if found:
            signal_days += 1

    # force-close remaining
    for sym, p in list(positions.items()):
        df = data[sym]
        cl = df["close"].iloc[-1]
        ret = cl * (1 - SLIPPAGE) / p["entry_px"] - 1
        trades.append(dict(symbol=sym, entry_date=str(p["entry_date"].date()),
                           exit_date=str(df.index[-1].date()), ret=round(ret, 4),
                           hold_days=p["days"], depth=round(p["depth"], 4),
                           exit_reason="open_at_end"))

    tdf = pd.DataFrame(trades)
    cdf = pd.DataFrame(curve, columns=["date", "equity", "n_pos"]).set_index("date")
    sim = cdf[cdf.index >= pd.Timestamp(START)]
    eq = sim.equity / sim.equity.iloc[0]
    dd = (eq / eq.cummax() - 1).min()
    daily = eq.pct_change().dropna()
    years = (sim.index[-1] - sim.index[0]).days / 365.25
    bench = load_index().reindex(sim.index).ffill()
    bench_tr = bench.iloc[-1] / bench.iloc[0] - 1

    wins = tdf[tdf.ret > 0]
    losses = tdf[tdf.ret <= 0]
    out = dict(
        window=f"{sim.index[0].date()} -> {sim.index[-1].date()}",
        trades=len(tdf),
        win_rate=round(len(wins) / len(tdf), 3),
        avg_ret=round(tdf.ret.mean(), 4),
        median_ret=round(tdf.ret.median(), 4),
        avg_win=round(wins.ret.mean(), 4),
        avg_loss=round(losses.ret.mean(), 4),
        profit_factor=round(wins.ret.sum() / -losses.ret.sum(), 2),
        avg_hold_days=round(tdf.hold_days.mean(), 1),
        worst_trade=round(tdf.ret.min(), 4),
        exit_reasons=tdf.exit_reason.value_counts().to_dict(),
        skipped_due_to_cap=skipped_cap,
        avg_positions=round(sim.n_pos.mean(), 1),
        max_positions=int(sim.n_pos.max()),
        avg_exposure=round((sim.n_pos * POS_FRAC).mean(), 3),
        total_return=round(eq.iloc[-1] - 1, 4),
        cagr=round(eq.iloc[-1] ** (1 / years) - 1, 4),
        max_drawdown=round(dd, 4),
        ann_vol=round(daily.std() * np.sqrt(252), 4),
        sharpe=round(daily.mean() / daily.std() * np.sqrt(252), 2),
        nifty100_total_return=round(bench_tr, 4),
        by_year={str(y): dict(n=len(g), wr=round((g.ret > 0).mean(), 3),
                              avg=round(g.ret.mean(), 4))
                 for y, g in tdf.groupby(tdf.entry_date.str[:4])},
    )
    tdf.to_csv(OUT_DIR / "trades_capped25_3y.csv", index=False)
    cdf.to_csv(OUT_DIR / "equity_capped25_3y.csv")
    (OUT_DIR / "summary_capped25_3y.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
