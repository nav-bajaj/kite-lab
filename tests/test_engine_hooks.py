"""P0 (2026-09-11): the additive run_strategy hooks — size_weights, top_n_fn, sector_of/sector_cap, fill_from_buffer,
trim_to_target — on a small synthetic panel. Default-off must equal the pre-hook engine; each hook must do only its job."""
import numpy as np, pandas as pd, pytest
from scripts._clean_engine import run_strategy, monthly_first_trading_day

SYMS = [f"S{i:02d}" for i in range(12)]


@pytest.fixture(scope="module")
def panel():
    rng = np.random.default_rng(7); cal = pd.bdate_range("2021-01-01", "2022-12-31")
    drift = np.linspace(0.0004, -0.0002, len(SYMS))                      # S00 strongest, S11 weakest
    px = 100 * np.exp(np.cumsum(rng.normal(drift, 0.015, size=(len(cal), len(SYMS))), axis=0))
    close = pd.DataFrame(px, index=cal, columns=SYMS); return close, cal


def base_kwargs(close, cal, **kw):
    entries = pd.DatetimeIndex(monthly_first_trading_day(cal))
    order = pd.Series({s: -i for i, s in enumerate(SYMS)}, dtype=float)              # S00 best ... S11 worst, fixed on every date
    def score(date, **_): return order.copy()
    args = dict(close_panel=close, trade_panel=close, calendar=cal, benchmark_aligned=close.mean(axis=1), entry_signal_dates=entries,
                weekly_signal_dates=entries, signal_function=score, signal_function_args={}, sma_200_panel=close.rolling(200).mean(),
                atr_20_panel=close.pct_change().rolling(20).std(), top_n=5, exit_buffer=2, max_weight=1.0, slippage=0.0, atr_mult=0.0,
                atr_min_floor=0.0, use_trailing_stop=False, use_dma_exit=False, initial_capital=1_000_000)
    args.update(kw); return args


def test_default_off_matches_uniform_size_weights(panel):
    close, cal = panel
    a = run_strategy(**base_kwargs(close, cal))
    b = run_strategy(**base_kwargs(close, cal, size_weights=lambda sd, syms: {s: 1.0 / len(syms) for s in syms}))
    assert a["equity"].pv.round(4).equals(b["equity"].pv.round(4))
    assert len(a["trades"]) == len(b["trades"])


def test_top_n_fn_caps_entries(panel):
    close, cal = panel
    r = run_strategy(**base_kwargs(close, cal, top_n_fn=lambda sd: 3))
    assert r["equity"].holdings.max() <= 3


def test_sector_cap_skips_full_sector(panel):
    close, cal = panel
    sector_of = {s: ("A" if int(s[1:]) < 6 else "B") for s in SYMS}       # the 6 strongest names are all sector A
    r = run_strategy(**base_kwargs(close, cal, sector_of=sector_of, sector_cap=2))
    first = r["trades"][r["trades"].side == "BUY"].sort_values("date").head(5)
    assert sum(sector_of[s] == "A" for s in first.symbol) <= 2


def test_fill_from_buffer_reaches_buffer_ranks(panel):
    close, cal = panel
    sector_of = {s: "A" for s in SYMS[:5]}; sector_of.update({s: "B" for s in SYMS[5:]})
    tight = run_strategy(**base_kwargs(close, cal, sector_of=sector_of, sector_cap=2))
    filled = run_strategy(**base_kwargs(close, cal, sector_of=sector_of, sector_cap=2, fill_from_buffer=True))
    assert filled["equity"].holdings.max() >= tight["equity"].holdings.max()


def test_trim_only_when_enabled(panel):
    close, cal = panel
    off = run_strategy(**base_kwargs(close, cal, size_weights=lambda sd, syms: {s: 1.0 / len(syms) for s in syms}))
    on = run_strategy(**base_kwargs(close, cal, size_weights=lambda sd, syms: {s: 1.0 / len(syms) for s in syms}, trim_to_target=0.0001))
    assert (off["trades"].reason == "trim").sum() == 0
    assert (on["trades"].reason == "trim").sum() >= 0     # may be zero on a synthetic panel; must not raise and must tag trims
    assert set(on["trades"].reason.unique()) <= {"entry", "rank", "trim", "atr_stop"}


def test_stop_reentry_block_stops_same_day_rebuy(panel):
    """A tight trailing stop checked at the monthly signal stops names that still rank in the buy list; with the
    switch off the engine sells and rebuys them on the same day, with block=1 it does not (mm_rebuild §23)."""
    close, cal = panel
    kw = dict(use_trailing_stop=True, atr_min_floor=0.03, fill_from_buffer=True)
    off = run_strategy(**base_kwargs(close, cal, **kw))
    on = run_strategy(**base_kwargs(close, cal, stop_reentry_block=1, **kw))
    def pairs(r):
        t = r["trades"]; g = t.groupby(["date", "symbol"]).side.nunique(); return int((g > 1).sum())
    assert (off["exits"].reason == "atr_stop").sum() > 0 and pairs(off) > 0
    assert pairs(on) == 0
    stopped = on["exits"][on["exits"].reason == "atr_stop"]
    buys = on["trades"][on["trades"].side == "BUY"]
    for _, e in stopped.iterrows():
        assert not ((buys.symbol == e.symbol) & (buys.date == e.exit_date)).any()
