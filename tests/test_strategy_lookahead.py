"""P0 (2026-09-11): no-look-ahead guards for the rebuilt books' inputs — a value at date t must not change when the data after t-1 is removed."""
import numpy as np, pandas as pd, tempfile, os
from data_pipeline.strategies.regime import roc_regime
from data_pipeline.strategies.momentum import make_momentum_score
from data_pipeline.strategies.sizing import make_inverse_vol_weights
from data_pipeline.strategies.calendar import monthly_on_or_after


def _index_csv(series, path):
    pd.DataFrame({"date": series.index, "close": series.values}).to_csv(path, index=False)


def test_roc_regime_uses_prior_close_only():
    rng = np.random.default_rng(3); cal = pd.bdate_range("2019-01-01", "2020-12-31"); s = pd.Series(1000 * np.exp(np.cumsum(rng.normal(0, 0.01, len(cal)))), index=cal)
    t = cal[300]; prev = cal[299]
    with tempfile.TemporaryDirectory() as d:
        full, cut = os.path.join(d, "full.csv"), os.path.join(d, "cut.csv"); _index_csv(s, full); _index_csv(s[s.index <= prev], cut)
        assert bool(roc_regime(full, 31, 3, cal).loc[t]) == bool(roc_regime(cut, 31, 3, cal).loc[t])


def test_momentum_score_at_t_ignores_data_after_t():
    rng = np.random.default_rng(5); cal = pd.bdate_range("2019-01-01", "2020-12-31"); rets = pd.DataFrame(rng.normal(0, 0.02, (len(cal), 8)), index=cal, columns=list("ABCDEFGH"))
    t = cal[400]; fn_full = make_momentum_score(rets, kind="voladj", lookback=252, min_obs=219, skip=21); fn_cut = make_momentum_score(rets[rets.index <= t], kind="voladj", lookback=252, min_obs=219, skip=21)
    pd.testing.assert_series_equal(fn_full(t), fn_cut(t))


def test_inverse_vol_weights_at_signal_date_ignore_later_returns():
    rng = np.random.default_rng(9); cal = pd.bdate_range("2019-01-01", "2020-12-31"); rets = pd.DataFrame(rng.normal(0, 0.02, (len(cal), 6)), index=cal, columns=list("ABCDEF"))
    t = cal[300]; syms = list("ABCDEF")
    w_full = make_inverse_vol_weights(rets, 63, 0.3)(t, syms); w_cut = make_inverse_vol_weights(rets[rets.index <= t], 63, 0.3)(t, syms)
    assert {k: round(v, 12) for k, v in w_full.items()} == {k: round(v, 12) for k, v in w_cut.items()}
    assert max(w_full.values()) <= 0.3 + 1e-9 and abs(sum(w_full.values()) - 1) < 1e-9


def test_monthly_on_or_after_day1_matches_engine():
    from scripts._clean_engine import monthly_first_trading_day
    cal = pd.bdate_range("2020-01-01", "2021-12-31")
    assert monthly_on_or_after(cal, 1).equals(pd.DatetimeIndex(monthly_first_trading_day(cal)))
    assert all(d.day >= 15 for d in monthly_on_or_after(cal, 15))
