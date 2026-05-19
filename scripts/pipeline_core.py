"""Shared data state for the daily pipeline (Phase 2).

The four production portfolio scripts (om25_v3, tl25_v3, l6_v2,
combo_defensive) all read the same underlying panels:

- ``close_panel``  : Date × Symbol close prices from ``nse500_data/``
- ``trade_panel``  : Date × Symbol OHLC/4 trade prices
- ``benchmark``    : NIFTY 100 TR series
- ``regime_panel`` : OM25/COMBO regime state (NIFTY 100 vs 100-DMA with
                      3-day confirmation), built from ``indices_data/NIFTY_100.csv``

Before Phase 2 they each rebuilt these from scratch in their own
subprocess — ~4-8s per portfolio in CSV parsing, ~2s rebuilding the
regime panel. Across the four portfolios that's 20-30s of redundant
load work per pipeline run.

Phase 2 has the orchestrator load all four artefacts once,
``pickle.dump`` them to a temp cache file, and pass the cache path to
each portfolio via ``--shared-state-file <path>``. The portfolios
preserve their existing standalone-CLI behaviour: omit the flag and
they fall back to loading from disk as before.

The cache is regenerated every pipeline run (no stale-cache risk),
written to a tempfile in the pipeline's chosen cache dir, and removed
at the end of the run.
"""
from __future__ import annotations

import pickle
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


CACHE_PROTOCOL = pickle.HIGHEST_PROTOCOL

# Schema version bump this when PipelineState fields change so that an
# old cache from a previous pipeline run is rejected rather than silently
# loaded into incompatible code.
CACHE_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class PipelineState:
    """Frozen container of panels shared across all portfolio builds."""

    close_panel: pd.DataFrame   # Date × Symbol close prices
    trade_panel: pd.DataFrame   # Date × Symbol OHLC/4
    benchmark: pd.Series         # Date → benchmark close
    regime_panel: Optional[pd.Series]  # Date → regime state (or None)
    # Provenance for sanity-checking + golden-master diffs.
    prices_dir: str
    benchmark_path: str
    regime_index_path: str
    captured_at: str
    schema_version: int = CACHE_SCHEMA_VERSION


def load_shared_state(
    prices_dir: Path,
    benchmark_path: Path,
    regime_index_path: Optional[Path] = None,
) -> PipelineState:
    """Read all shared panels from disk. Run once per pipeline."""
    # Local imports keep this module fast to import.
    from scripts.backtest_momentum import load_price_panels, load_benchmark

    close, trade = load_price_panels(Path(prices_dir))
    bench = load_benchmark(Path(benchmark_path))

    regime: Optional[pd.Series] = None
    if regime_index_path is not None:
        from scripts.om25_v3 import build_regime_panel_confirmed

        regime = build_regime_panel_confirmed(Path(regime_index_path))

    return PipelineState(
        close_panel=close,
        trade_panel=trade,
        benchmark=bench,
        regime_panel=regime,
        prices_dir=str(prices_dir),
        benchmark_path=str(benchmark_path),
        regime_index_path=str(regime_index_path) if regime_index_path else "",
        captured_at=datetime.now().isoformat(timespec="seconds"),
    )


def dump_to_cache(state: PipelineState, path: Path) -> None:
    """Serialize state to a local pickle file.

    Pickle is fine here: the cache is written and read by the same
    pipeline run within the same machine — no untrusted-source risk.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump(state, f, protocol=CACHE_PROTOCOL)


def load_from_cache(path: Path) -> PipelineState:
    """Read a previously written cache. Raises on schema mismatch.

    The pickle file is written by ``save_to_cache`` (this same process tree)
    and lives on local disk under our control. We do not load pickles from
    user-supplied or network-fetched paths. R-015.
    """
    with Path(path).open("rb") as f:
        state = pickle.load(f)  # noqa: S301  # local cache file written by us; not untrusted data; R-015
    if not isinstance(state, PipelineState):
        raise TypeError(
            f"shared-state cache at {path} is not a PipelineState "
            f"(got {type(state).__name__})"
        )
    if state.schema_version != CACHE_SCHEMA_VERSION:
        raise ValueError(
            f"shared-state cache schema version mismatch at {path}: "
            f"expected {CACHE_SCHEMA_VERSION}, got {state.schema_version}. "
            f"Regenerate the cache."
        )
    return state


def describe(state: PipelineState) -> str:
    """One-line summary for logging."""
    n_dates = len(state.close_panel)
    n_syms = state.close_panel.shape[1]
    end_date = state.close_panel.index.max() if n_dates else "?"
    has_regime = "with regime" if state.regime_panel is not None else "no regime"
    return (
        f"PipelineState: {n_syms} symbols × {n_dates} dates (last {end_date}), "
        f"{has_regime}, captured {state.captured_at}"
    )


# ---------------------------------------------------------------------------
# CLI: write a cache file for use by portfolio scripts via --shared-state-file
# ---------------------------------------------------------------------------

def _cli() -> int:
    """CLI entry point.

    Re-imports through the canonical module path so that pickled
    objects' qualnames resolve correctly when other scripts load the
    cache. If we used the local symbols here, ``PipelineState`` would
    pickle as ``__main__.PipelineState`` and fail to load in any other
    process.
    """
    import argparse
    import sys

    # Force the canonical module-path bindings before serializing.
    from scripts.pipeline_core import (
        load_shared_state as _load,
        dump_to_cache as _dump,
        describe as _describe,
    )

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prices-dir", type=Path, required=True)
    ap.add_argument("--benchmark", type=Path, required=True)
    ap.add_argument("--regime-index", type=Path, default=None,
                    help="If provided, also build the regime panel")
    ap.add_argument("--output", type=Path, required=True,
                    help="Path to write the pickle cache")
    args = ap.parse_args()

    state = _load(
        prices_dir=args.prices_dir,
        benchmark_path=args.benchmark,
        regime_index_path=args.regime_index,
    )
    _dump(state, args.output)
    print(f"[pipeline_core] wrote {args.output}")
    print(f"[pipeline_core] {_describe(state)}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
