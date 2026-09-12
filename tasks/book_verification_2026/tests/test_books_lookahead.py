"""Group G of tasks/book_verification_2026/TESTS_BOOKS.md — no look-ahead.

The invariant: every input used on signal date t is known at the close of t or earlier, and nothing
that happens after t can change the orders t produced.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from _harness import BOOKS
from data_pipeline.strategies.regime import roc_regime
from scripts._clean_engine import monthly_first_trading_day, run_strategy

SYMS = [f"S{i:02d}" for i in range(10)]


@pytest.mark.parametrize("book", BOOKS)
def test_g01_score_at_t_ignores_data_after_t(ctxs, book):
    """G-01: the score at a signal date is identical when the returns panel is truncated there."""
    from data_pipeline.strategies.blend import make_blend_score
    from data_pipeline.strategies.capture import make_capture_score
    from data_pipeline.strategies.momentum import make_momentum_score

    ctx = ctxs[book]
    cfg = ctx.cfg

    def build(returns):
        mom = make_momentum_score(returns, kind="voladj", lookback=cfg["lookback"], min_obs=cfg["min_obs"],
                                  skip=cfg["skip"], candidate_fn=ctx.candidate_fn)
        if cfg["score"] == "voladj":
            return mom
        cap = make_capture_score(returns, None, w_uc_bull=0.0, w_cr_bull=1.0, return_filter=True,
                                 lookback=cfg["lookback"], min_obs=cfg["min_obs"], candidate_fn=ctx.candidate_fn)
        return make_blend_score(mom, cap, cfg["mix_w"])

    for sd in list(ctx.entries)[::47]:
        full = build(ctx.returns)(sd).sort_index()
        cut = build(ctx.returns[ctx.returns.index <= sd])(sd).sort_index()
        pd.testing.assert_series_equal(full, cut, check_names=False,
                                       obj=f"{book} score at {sd.date()} under truncation")


@pytest.mark.parametrize("book", BOOKS)
def test_g03_regime_at_t_ignores_data_after_t(ctxs, master, book):
    """G-03: the regime at t is unchanged when the index series is truncated at t."""
    ctx = ctxs[book]
    path = master / f"benchmarks/{ctx.cfg['regime_index']}.csv"
    s = pd.read_csv(path, parse_dates=["date"]).sort_values("date").set_index("date")["close"]
    cal = ctx.panels.calendar
    dates = [d for d in cal if d >= pd.Timestamp("2012-01-01")][::300]
    with tempfile.TemporaryDirectory() as tmp:
        for t in dates:
            cut = s[s.index <= t]
            p = Path(tmp) / "cut.csv"
            pd.DataFrame({"date": cut.index, "close": cut.values}).to_csv(p, index=False)
            got = roc_regime(p, ctx.cfg["roc_n"], ctx.cfg["confirm"], cal[cal <= t])
            assert bool(got.loc[t]) == bool(ctx.regime.loc[t]), f"{book}: regime at {t.date()} moves under truncation"


def _synthetic():
    rng = np.random.default_rng(23)
    cal = pd.bdate_range("2021-01-01", "2022-12-31")
    drift = np.linspace(0.0008, -0.0004, len(SYMS))
    close = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(drift, 0.015, size=(len(cal), len(SYMS))), axis=0)),
                         index=cal, columns=SYMS)
    trade = close * 1.001
    entries = pd.DatetimeIndex(monthly_first_trading_day(cal))
    return close, trade, cal, entries


def _kwargs(close, trade, cal, entries, **kw):
    ranks = close.pct_change(63)

    def score(date, **_):
        return ranks.loc[date].dropna()

    args = dict(close_panel=close, trade_panel=trade, calendar=cal, benchmark_aligned=close.mean(axis=1),
                entry_signal_dates=entries, weekly_signal_dates=entries, signal_function=score,
                signal_function_args={}, sma_200_panel=close.rolling(200).mean(),
                atr_20_panel=close.pct_change().rolling(20).std(), top_n=4, exit_buffer=2, max_weight=0.35,
                slippage=0.002, atr_mult=0.0, atr_min_floor=0.20, use_trailing_stop=True, use_dma_exit=False,
                initial_capital=1_000_000, stop_reentry_block=1, fill_from_buffer=True)
    args.update(kw)
    return args


def test_g04_prices_after_an_execution_date_cannot_change_earlier_trades():
    """G-04: perturb every price strictly after one execution date; earlier trades must be identical."""
    close, trade, cal, entries = _synthetic()
    base = run_strategy(**_kwargs(close, trade, cal, entries))
    assert not base["trades"].empty

    exec_dates = sorted(base["trades"].date.unique())
    cut = exec_dates[len(exec_dates) // 2]
    after = cal > cut
    close2, trade2 = close.copy(), trade.copy()
    close2.loc[after] *= 1.5
    trade2.loc[after] *= 1.5
    perturbed = run_strategy(**_kwargs(close2, trade2, cal, entries))

    cols = ["date", "symbol", "side", "shares", "price"]
    a = base["trades"][base["trades"].date <= cut][cols].sort_values(cols).reset_index(drop=True)
    b = perturbed["trades"][perturbed["trades"].date <= cut][cols].sort_values(cols).reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b, obj="trades up to the perturbation date")


@pytest.mark.parametrize("book", BOOKS)
def test_g05_no_stop_decision_depends_on_the_execution_day_close(replays, book):
    """G-05: the stop is decided at the signal close, so dropping the execution-day close from the
    peak must not change any stop.

    Structurally the engine does fold the execution-day close in before the check
    (scripts/_clean_engine.py:344-349 runs ahead of the stop check at :505), so this is a materiality
    guard on a latent look-ahead, not proof that it cannot bite.
    """
    bad = [(str(r.exec_date.date()), sorted(r.actual_stops - r.expected_stops_signal_only),
            sorted(r.expected_stops_signal_only - r.actual_stops))
           for r in replays[book].rebalances if r.actual_stops != r.expected_stops_signal_only]
    assert bad == [], f"{book}: {len(bad)} stop decisions depend on the execution-day close: {bad[:3]}"
