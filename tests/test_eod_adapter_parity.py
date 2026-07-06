"""Adapter-vs-runner parity guard (audit L3).

The EOD producer's ``_prepare_<strategy>`` adapters in
``data_pipeline/eod_proposal.py`` must feed the engine the SAME config the
production daily runner (``scripts/run_<strategy>_portfolio.py``) does — that is
the whole "read the engine, don't re-implement it" guarantee. Nothing else
tests this, so a runner change (exit_buffer, min_hold_days, weekly_rank_check,
regime wiring, ...) not mirrored in the adapter would silently show clients a
different membership than the strategy actually trades.

This test is static + data-free: it AST-extracts the engine-config kwargs from
each adapter's ``StrategyState(...)`` call and each runner's
``run_strategy``/``run_momentum`` call, resolves ``LOCKED[...]`` subscripts
against the real config dicts, and asserts both against a pinned contract. The
contract's concrete numbers are intentionally hardcoded so that changing a
LOCKED value trips this test and forces a conscious review of BOTH sites.
"""
from __future__ import annotations

import ast
from pathlib import Path

from scripts.om25_v3 import LOCKED as OM25
from scripts.tl25_v3 import V3_LOCKED as TL25
from scripts._momentum_engine import BASELINE as L6
from scripts.combo_defensive import LOCKED as COMBO

ROOT = Path(__file__).resolve().parents[1]
EOD = ROOT / "data_pipeline" / "eod_proposal.py"


# The verified contract. regime_panel_none: om25/tl25/l6 pass None (regime is
# either absent or consumed only via the score closure); combo passes the
# engine regime overlay (that's the "defensive" scale-down).
CONTRACT = {
    "om25_v3": dict(top_n=25, exit_buffer=20, drawdown_stop=0.2,
                    weekly_rank_check=False, regime_panel_none=True,
                    bear_exposure=0.0, min_hold_days=0),
    "tl25_v3": dict(top_n=25, exit_buffer=20, drawdown_stop=0.2,
                    weekly_rank_check=True, regime_panel_none=True,
                    bear_exposure=0.0, min_hold_days=0),
    "l6_v2": dict(top_n=24, exit_buffer=0, drawdown_stop=0.0,
                  weekly_rank_check=False, regime_panel_none=True,
                  bear_exposure=0.0, min_hold_days=8),
    "combo_defensive": dict(top_n=24, exit_buffer=0, drawdown_stop=0.0,
                            weekly_rank_check=False, regime_panel_none=False,
                            bear_exposure=0.5, min_hold_days=8),
}

# Which source-level dict name maps to which real dict, inside each adapter.
ADAPTER_DICTS = {
    "om25_v3": {"LOCKED": OM25},
    "tl25_v3": {"V3_LOCKED": TL25},
    "l6_v2": {"BASELINE": L6},
    "combo_defensive": {"LOCKED": COMBO, "OM25_LOCKED": OM25},
}

RUNNERS = {
    "om25_v3": (ROOT / "scripts/run_om25_v3_portfolio.py", "run_strategy",
                {"LOCKED": OM25}),
    "tl25_v3": (ROOT / "scripts/run_tl25_v3_portfolio.py", "run_strategy",
                {"V3_LOCKED": TL25}),
    "l6_v2": (ROOT / "scripts/run_l6_v2_portfolio.py", "run_momentum",
              {"BASELINE": L6}),
    "combo_defensive": (ROOT / "scripts/run_combo_defensive_portfolio.py",
                        "run_strategy", {"LOCKED": COMBO}),
}

_UNRESOLVED = object()


def _resolve(node, dicts):
    """Resolve an AST value node to a Python value, or _UNRESOLVED."""
    if isinstance(node, ast.Constant):
        return node.value
    if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name)
            and isinstance(node.slice, ast.Constant)):
        dname = node.value.id
        if dname in dicts:
            return dicts[dname][node.slice.value]
    return _UNRESOLVED


def _call_kwargs(scope, call_name):
    """First Call to ``call_name`` within ``scope`` → {kwarg: value_node}."""
    for node in ast.walk(scope):
        if isinstance(node, ast.Call):
            f = node.func
            name = f.id if isinstance(f, ast.Name) else getattr(f, "attr", None)
            if name == call_name:
                return {kw.arg: kw.value for kw in node.keywords if kw.arg}
    return None


def _func_def(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"function {name} not found")


def _adapter_config(strategy):
    tree = ast.parse(EOD.read_text())
    fn = _func_def(tree, f"_prepare_{strategy}")
    kw = _call_kwargs(fn, "StrategyState")
    assert kw is not None, f"no StrategyState(...) in _prepare_{strategy}"
    d = ADAPTER_DICTS[strategy]
    regime_node = kw["regime_panel"]
    return {
        "top_n": _resolve(kw["top_n"], d),
        "exit_buffer": _resolve(kw["exit_buffer"], d),
        "drawdown_stop": _resolve(kw["drawdown_stop"], d),
        "weekly_rank_check": _resolve(kw["weekly_rank_check"], d),
        "bear_exposure": _resolve(kw["bear_exposure"], d),
        "min_hold_days": (_resolve(kw["min_hold_days"], d)
                          if "min_hold_days" in kw else 0),
        # None constant -> None; a Name (portfolio_regime) -> not None.
        "regime_panel_none": _resolve(regime_node, d) is None,
    }


class TestAdapterMatchesContract:
    """Each adapter's engine config equals the verified production contract."""

    def _check(self, strategy):
        got = _adapter_config(strategy)
        want = CONTRACT[strategy]
        for key, expected in want.items():
            assert got[key] == expected, (
                f"{strategy}.{key}: adapter has {got[key]!r}, "
                f"contract expects {expected!r}"
            )

    def test_om25_v3(self):
        self._check("om25_v3")

    def test_tl25_v3(self):
        self._check("tl25_v3")

    def test_l6_v2(self):
        self._check("l6_v2")

    def test_combo_defensive(self):
        self._check("combo_defensive")


class TestRunnerRegimeWiringMatchesAdapter:
    """The most dangerous drift is regime wiring / defensive scaling: om25's
    regime_panel=None fix (commit 965c154) and combo's regime overlay. Assert
    the runner's ``regime_panel`` None-ness + ``bear_exposure`` match the
    contract, extracted straight from the runner's engine call."""

    def _runner_kwargs(self, strategy):
        path, call_name, _ = RUNNERS[strategy]
        tree = ast.parse(path.read_text())
        kw = _call_kwargs(tree, call_name)
        assert kw is not None, f"no {call_name}(...) call in {path.name}"
        return kw, RUNNERS[strategy][2]

    def test_regime_panel_none_ness(self):
        for strategy, want in CONTRACT.items():
            kw, _ = self._runner_kwargs(strategy)
            if "regime_panel" not in kw:
                # run_momentum (l6) has no regime arg — that IS regime=None.
                assert want["regime_panel_none"] is True, strategy
                continue
            node = kw["regime_panel"]
            is_none = isinstance(node, ast.Constant) and node.value is None
            assert is_none == want["regime_panel_none"], (
                f"{strategy}: runner regime_panel none={is_none}, "
                f"contract expects none={want['regime_panel_none']}"
            )

    def test_bear_exposure_when_constant_or_locked(self):
        # om25/tl25 pass literal 0.0; combo passes LOCKED["regime_bear_exposure"].
        # l6 goes through run_momentum (no bear arg) — skip.
        for strategy in ("om25_v3", "tl25_v3", "combo_defensive"):
            kw, dicts = self._runner_kwargs(strategy)
            assert "bear_exposure" in kw, strategy
            val = _resolve(kw["bear_exposure"], dicts)
            assert val == CONTRACT[strategy]["bear_exposure"], (
                f"{strategy}: runner bear_exposure={val!r}, "
                f"contract={CONTRACT[strategy]['bear_exposure']!r}"
            )
