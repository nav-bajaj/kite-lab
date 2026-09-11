"""§5 runner — slot sweep, ordering error bar, P1-P7."""
from __future__ import annotations

import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exits import load_panel, simulate  # noqa: E402
from book import build_book, era_sharpe  # noqa: E402

REPO = "/Users/navdeep/kite-lab"
TASK = f"{REPO}/tasks/breakout_calls_2026"
SLIPPAGE = 0.002
ERAS = [(2006, 2012, "2006-2012"), (2013, 2019, "2013-2019"), (2020, 2026, "2020-2026")]

# §4's choice. Quoted with its deflation caveat; used here because it is what
# walk-forward would have selected in every year since 2011.
EXIT = dict(stop_mode="structure", stop_pct=0.08, trail="ma150",
            partial_r=None, timestop=None, atr_mult=3.0)


def build_trades(tape, panels):
    """Resolve every E1 signal into an entry/exit pair under EXIT."""
    rows = []
    for ev in tape.itertuples():
        p = panels.get(ev.symbol)
        if p is None:
            continue
        e = p["pos"].get(pd.Timestamp(ev.signal_date))
        if e is None:
            continue
        entry = ev.entry * (1 + SLIPPAGE)
        stop0 = max(ev.stop_ref, entry * (1 - EXIT["stop_pct"]))
        out = simulate(p, e, entry, stop0, EXIT)
        if out is None:
            continue
        ret, r, hold, reason = out
        rows.append(dict(symbol=ev.symbol, entry_date=p["dates"][e],
                         exit_date=p["dates"][min(e + hold, len(p["c"]) - 1)],
                         entry=entry, stop=stop0, exit_px=entry * (1 + ret),
                         final_depth=ev.final_depth, r=r, ret=ret, hold=hold))
    return pd.DataFrame(rows)


def main():
    os.chdir(REPO)
    tape = pd.read_csv(f"{TASK}/data/signals_standard_no_l6.csv")
    tape = tape[tape.kind == "E1"]
    syms = sorted(tape.symbol.unique())
    panels = {s: p for s in syms if (p := load_panel(s)) is not None}
    print(f"{len(panels)} panels, {len(tape):,} E1 signals", flush=True)

    tr = build_trades(tape, panels)
    # ADV at entry, for the participation cap
    pit = pd.read_parquet(f"{TASK}/data/pit_universe.parquet", columns=["date", "symbol", "adv"])
    pit = pit.drop_duplicates(["symbol", "date"])   # never let a merge inflate the tape
    tr = tr.merge(pit, left_on=["symbol", "entry_date"], right_on=["symbol", "date"], how="left")
    tr["adv"] = tr.adv.fillna(tr.adv.median())
    tr = tr.drop(columns=["date"]).sort_values("entry_date").reset_index(drop=True)
    tr.to_csv(f"{TASK}/data/book_trades.csv", index=False)
    print(f"resolved {len(tr):,} trades; mean R {tr.r.mean():.3f}")

    pan = {s: {"close": pd.Series(panels[s]["c"], index=panels[s]["dates"])} for s in panels}
    # The trading calendar comes from the benchmark index, not from a sample of
    # symbols: a union over symbols would inherit any one name's odd sessions,
    # and a subset would silently drop days the book needed to mark.
    bench = pd.read_csv(f"{REPO}/data/master/benchmarks/NIFTY_500.csv", parse_dates=["date"])
    cal = pd.DatetimeIndex(sorted(bench.date.unique()))
    cal = cal[(cal >= "2006-01-01") & (cal <= "2026-09-09")]
    print(f"calendar {cal[0].date()} -> {cal[-1].date()}, {len(cal)} sessions", flush=True)

    print("\n=== slot sweep, random ordering, 12 seeds each ===")
    print(f"{'slots':>6} {'CAGR':>8} {'maxDD':>8} {'Sharpe':>7} {'taken':>7} {'expo':>6} {'open':>6}   (median of seeds, [p10-p90])")
    rows = []
    for slots in [3, 5, 8, 10, 15, 20]:
        res = [build_book(tr, pan, cal, slots=slots, seed=s) for s in range(12)]
        cg = np.array([r["cagr"] for r in res]); dd = np.array([r["maxdd"] for r in res])
        sh = np.array([r["sharpe"] for r in res]); tk = np.array([r["taken"] for r in res])
        ex = np.array([r["exposure"] for r in res]); op = np.array([r["avg_open"] for r in res])
        rows.append(dict(slots=slots, cagr=np.median(cg), maxdd=np.median(dd),
                         sharpe=np.median(sh), taken=np.median(tk),
                         cagr_p10=np.percentile(cg, 10), cagr_p90=np.percentile(cg, 90),
                         dd_p10=np.percentile(dd, 10), dd_p90=np.percentile(dd, 90),
                         exposure=np.median(ex), avg_open=np.median(op)))
        print(f"{slots:>6} {np.median(cg):>7.1%} {np.median(dd):>7.1%} {np.median(sh):>7.2f} "
              f"{np.median(tk):>7.0f} {np.median(ex):>5.0%} {np.median(op):>6.1f}   "
              f"CAGR [{np.percentile(cg,10):.1%}-{np.percentile(cg,90):.1%}]  "
              f"DD [{np.percentile(dd,10):.1%}-{np.percentile(dd,90):.1%}]", flush=True)
    pd.DataFrame(rows).to_csv(f"{TASK}/data/slot_sweep.csv", index=False)

    best = max(rows, key=lambda r: r["sharpe"])
    n = int(best["slots"])
    print(f"\n=== era stability at {n} slots (P4 needs >= 0.50 in each) ===")
    for s in range(3):
        b = build_book(tr, pan, cal, slots=n, seed=s)
        print(f"  seed {s}: " + "  ".join(f"{k} {v:.2f}" for k, v in era_sharpe(b["equity"], ERAS).items()))

    print(f"\n=== ordering: random vs tightest-base-first, {n} slots ===")
    rnd = [build_book(tr, pan, cal, slots=n, seed=s) for s in range(12)]
    tight = build_book(tr, pan, cal, slots=n, order="tight")
    print(f"  random  : CAGR {np.median([r['cagr'] for r in rnd]):.1%}  DD {np.median([r['maxdd'] for r in rnd]):.1%}  Sharpe {np.median([r['sharpe'] for r in rnd]):.2f}")
    print(f"  tightest: CAGR {tight['cagr']:.1%}  DD {tight['maxdd']:.1%}  Sharpe {tight['sharpe']:.2f}")

    b = build_book(tr, pan, cal, slots=n, seed=0)
    b["equity"].to_csv(f"{TASK}/data/equity_{n}slots.csv")
    print(f"\n  of {len(tr):,} signals: taken {b['taken']:,}, "
          f"passed no-slot {b['passed_full']:,}, passed no-cash {b['passed_cash']:,}, "
          f"passed ADV-cap {b['passed_adv']:,}")


if __name__ == "__main__":
    main()
