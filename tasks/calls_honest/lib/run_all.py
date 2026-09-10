"""Run both strategies on both universes, 2010-01-01 to the store end. Outputs under runs/<strategy>_<universe>/."""
from __future__ import annotations

import json, sys, time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import panels, save_run, RUNS
import s2 as S2
import dip as DIPM

which = sys.argv[1:] or ["s2", "dip"]
for uni in ("nse500", "nifty250"):
    if "s2" in which:
        t = time.time()
        cfg, res, calls = S2.run_s2(uni)
        out = save_run(f"s2_{uni}", res["equity"], calls, {"trades": res["trades"]})
        json.dump(cfg, open(out / "config.json", "w"), indent=1)
        print(f"s2 {uni}: {len(calls)} calls, equity end {res['equity']['pv'].iloc[-1]:.0f}, {time.time()-t:.0f}s", flush=True)
    if "dip" in which:
        t = time.time()
        calls, equity, skipped = DIPM.simulate(uni)
        out = save_run(f"dip_{uni}", equity, calls)
        json.dump({**DIPM.DIP, "universe": uni, "skipped_for_capacity": int(skipped)}, open(out / "config.json", "w"), indent=1)
        print(f"dip {uni}: {len(calls)} calls, equity end {equity['pv'].iloc[-1]:.0f}, gross-slot {equity['pv_gross_slot'].iloc[-1]:.0f}, skipped {skipped}, {time.time()-t:.0f}s", flush=True)
