"""Sensitivity of the one S2 interpretation: RS percentile across point-in-time members (main run, the rule as
stated) versus across every column with a price that day (what the branch code did on its own panel). On the
master store the second set includes delisted names carried flat, so it is reported, not adopted."""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import panels, universe, W, fmt, save_run, load_equity
import s2 as S2

P = panels(); close = P["close"]
for uni in ("nse500", "nifty250"):
    cols, mfn, cfn, mask = universe(uni)
    alive = close[cols].notna()
    S2._s2_cache[(uni, None)] = (S2.build_stage2_panels(close[cols], alive, None, min_stage_age=S2.S2V2["min_stage_age"]), mfn, cfn)
    cfg, res, calls = S2.run_s2(uni)
    save_run(f"s2_{uni}_rs_alive", res["equity"], calls)
    e = load_equity(f"s2_{uni}_rs_alive"); m = load_equity(f"s2_{uni}")
    for lab, (a, b) in (("IS 2010-15", ("2010-01-01", "2015-12-31")), ("OOS 2016-26", ("2016-01-01", "2099-12-31")), ("OOS 2017-26", ("2017-01-01", "2099-12-31"))):
        print(f"  S2 {uni} {lab}: RS across alive columns {fmt(W.stats(e, a, b))} | main (PIT members) {fmt(W.stats(m, a, b))}")
    print(f"    calls: alive {len(calls)} vs main {len(pd.read_csv(Path(__file__).resolve().parents[1] / 'runs' / f's2_{uni}' / 'calls.csv'))}")
