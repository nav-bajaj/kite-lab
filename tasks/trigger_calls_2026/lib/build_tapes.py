from __future__ import annotations
import sys, time
import pandas as pd
sys.path.insert(0, "tasks/trigger_calls_2026/lib")
from daily_features import regime_gate, benchmark
from tapes import load_daily, triggers, trade_all

t0 = time.time()
d = load_daily()
trig = triggers(d)
print(trig.kind.value_counts(), time.time() - t0, flush=True)
tr = trade_all(trig)
print("trades", len(tr), time.time() - t0, flush=True)

g = regime_gate()
b = benchmark()
tape = trig.merge(tr, on=["symbol", "trigger_date"], how="inner")
tape["gate_on"] = pd.Series(g.reindex(
    g.index.union(tape.trigger_date.unique())).ffill().reindex(
    tape.trigger_date).to_numpy(), index=tape.index).fillna(False).astype(bool)
bi = b.reindex(b.index.union(
    pd.Index(tape.entry_date.unique()).union(pd.Index(tape.exit_date.unique())))).ffill()
tape["bench_ret"] = bi.reindex(tape.exit_date).to_numpy() / bi.reindex(tape.entry_date).to_numpy() - 1
tape["alpha"] = tape["ret"] - tape["bench_ret"]
tape.to_parquet("tasks/trigger_calls_2026/data/tapes.parquet", index=False)
print("tape", len(tape), time.time() - t0, flush=True)
