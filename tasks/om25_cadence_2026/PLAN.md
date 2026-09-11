# OM25 entry cadence — weekly re-test, plus NSE 500

**Status:** in-progress · **Opened:** 2026-09-08

## Why

Two prior cadence results on OM25 disagree, and neither settles the
question for the stack we actually run:

1. **May 2026 parameter review** (`tasks/om25/experiments/_om25_cadence_test.py`,
   archive branch) swept Weekly / Bi-weekly / Monthly / Bi-monthly across
   three universes on 2021-02 → 2026-05. **Weekly won every aggregate
   metric** (CAGR 51.9%, DD −31.2%, Sharpe 2.05, Calmar 1.67 vs bi-weekly
   51.0 / −32.5 / 1.98 / 1.57). It was rejected explicitly on
   branding/operational grounds, not performance. That sweep ran the **v2
   stack** — no regime tilt, no 20% drawdown stop, exit-buffer 15, return
   filter off.

2. **v3 OOS retune** (`tasks/oos_retune_2026/`) locked Nifty 250 +
   bi-weekly. Its `RESULTS.md` claims bi-weekly "also beats weekly", but
   the task's own search space was `Cadence | monthly, biweekly` (PLAN.md
   stage 2), every cadence table in `PROGRESS.md` has two rows, and
   `scripts/run_cadence_variants_oos.py` says "two entry cadences". **No
   weekly arm was ever run on the v3 stack.** The claim is unsupported.

So: the production OM25 v3 has never been evaluated at weekly entry on
the 2017–2026 OOS window. Separately, the v3 retune rejected NSE 500 on
drawdown *before* the regime tilt existed — the tilt was introduced
specifically to fix NSE 500's DD, and then the universe choice was never
revisited head-to-head against Nifty 250 under the final locked stack.

Per the standing stance that the production portfolios are working well,
this is **diagnostic, not a search for a replacement**. The output we
want is "how cadence-sensitive is OM25's edge, and how much slack is in
the Friday execution window" — not a candidate swap.

## Scope

Hold the entire production stack fixed (`scripts/om25_v3.py:LOCKED`) and
vary exactly two dimensions:

| Dimension | Values |
|---|---|
| Entry cadence | weekly · **bi-weekly (control)** · monthly |
| Universe | **Nifty 250 (control)** · NSE 500 |

= 6 runs. Weekly exit checks (20%-from-peak drawdown stop) fire every
Friday in all six, exactly as production does. Rank exits fire at entry
rebalance dates (`weekly_rank_check=False`, production behaviour), so a
weekly cadence also means weekly rank-exit evaluation — the same
construction the May 2026 sweep used.

### Evaluation

- Windows from the v3 retune (`multi_window_oos_eval.py`, vendored here):
  IS 2010-01→2016-12, OOS_A 2017–2019, OOS_B 2020–2022, OOS_C 2023→panel
  end, OOS_full 2017→panel end. Panel now runs to **2026-08-21**, three
  months past the retune's 2026-05-08 cutoff, so absolute numbers will
  not match the published 44.78% exactly.
- Pass criteria carried over from `tasks/oos_retune_2026/PLAN.md`:
  OOS_full Sharpe ≥ 1.0, each OOS sub-window Sharpe ≥ 0.7, OOS_full
  Max DD ≥ −45%.
- **Post-tax on both arms.** Cadence is a turnover decision and the
  pre-tax comparison is the misleading one. Reuse
  `tasks/tax_study/tax_engine.py` (FIFO lots, STCG 20% / LTCG 12.5%
  above ₹1.25L, 8-FY loss carry-forward) and `forced_sale.py` for the
  post-tax equity curve, with the forced-sale slippage rate set to the
  backtest's 20 bps rather than the tax study's 30.

### Out of scope

- Any change to production. No edits to `scripts/`, no pipeline wiring.
- Re-tuning anything else (top-N, buffer, lookback, regime params).
- Brokerage, STT, stamp duty — slippage at 20 bps is the only cost model
  besides tax, same as every other OM25 result we publish.

## Known caveats going in

- **Survivorship.** Both membership CSVs are 2026-vintage snapshots
  (`nse500_membership.csv`: 500 rows at 1900-01-01 + 34 dated 2026
  edits). Pre-2026 delistings are absent. Inflates all six arms; should
  not bias the *comparison* between them.
- **Split-adjusted panel.** `nse500_data_merged` prices are
  split-adjusted, so they are not what traded. Returns are unaffected and
  the drawdown stop is a price *ratio*, so this study is safe — but no
  price-level claim can be made from it.
- **Cadence aliasing.** `biweekly_fridays()` is `fridays()[::2]`, so the
  bi-weekly arm's phase is fixed by the panel start. The weekly arm is a
  superset of both bi-weekly phases and so is not exposed to this; the
  bi-weekly control is.

## Critical files

| Path | Role |
|---|---|
| `_cadence_run.py` | One run: universe × cadence → equity/trades/exits |
| `_summarise.py` | Window metrics + tax overlay → comparison tables |
| `multi_window_oos_eval.py` | Vendored from the archive branch |
| `runs/<universe>_<cadence>/` | Per-run artifacts |
| `scripts/om25_v3.py` | Locked stack, read-only here |
| `tasks/tax_study/tax_engine.py` | Reused post-tax model |
