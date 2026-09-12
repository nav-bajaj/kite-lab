"""Session fixtures for the master-store integrity suite (TESTS_DATA.md).

One pass over prices/adjusted_pr + prices/adjusted_tr + prices/bhavcopy (1.6 GB, ~30 s) collects everything groups A and C
need; the Kite ratio census and the panel load are separate session fixtures. Nothing here writes to the store.
"""
from __future__ import annotations

import glob
import json
import os
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(os.environ.get("KITE_LAB_ROOT", Path(__file__).resolve().parents[3]))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_pipeline.master_store import MASTER  # noqa: E402

PR_COLS = ["date", "open", "high", "low", "close", "volume", "traded_as", "factor"]
SHARE_TYPES = ("bonus", "split", "consolidation")
# A 252-session lookback skipped 21 sessions back from the books' 2016 record start reaches ~2014-11; 2014-01-01 is the
# conservative boundary for "inside the data era either book actually scores on".
BOOK_DATA_START = pd.Timestamp("2014-01-01")
JUMP_THRESHOLD = 0.50          # one-session move in the adjusted view that a corporate action ought to explain
TICK = 1.01e-4                 # the adjusted view is stored rounded to 4 dp; one tick of re-derivation slack


class StoreWarning(UserWarning):
    """A warn-severity finding: reported with a count, capped generously so a regression still fails."""


def warn_count(test_id: str, message: str, count: int, cap: int) -> None:
    if count:
        warnings.warn(f"{test_id}: {message} (count={count}, cap={cap})", StoreWarning, stacklevel=2)
    assert count <= cap, f"{test_id}: {message} — count {count} exceeds cap {cap}"


@dataclass
class Scan:
    """Per-symbol integrity summary plus the detail rows the group A and C tests assert on."""
    summary: pd.DataFrame
    sessions: pd.DatetimeIndex
    factor_steps: dict = field(default_factory=dict)          # symbol -> DataFrame(date, ratio)
    unexplained_steps: list = field(default_factory=list)     # (symbol, date, ratio)
    unapplied_events: list = field(default_factory=list)      # (symbol, ex_date, type, factor, is_observed)
    jumps: list = field(default_factory=list)                 # (symbol, date, ret)
    mismatches: list = field(default_factory=list)            # (symbol, date, adjusted, predicted, n_rows_bad)
    schema_errors: list = field(default_factory=list)         # (symbol, problem)


@pytest.fixture(scope="session")
def master() -> Path:
    m = Path(MASTER)
    assert m.is_dir(), f"master store not found at {m}"
    return m


@pytest.fixture(scope="session")
def sessions_calendar(master) -> pd.DatetimeIndex:
    """The NSE session calendar of record: the distinct dates in the bhavcopy archive (what qa_report.py itself uses).
    qa/calendar.csv is NOT the calendar — it is the per-file defect list, checked separately."""
    eq = pd.read_parquet(master / "bhavcopy_eq.parquet", columns=["date"])
    return pd.DatetimeIndex(sorted(eq["date"].dt.normalize().unique()))


@pytest.fixture(scope="session")
def corporate_actions(master) -> pd.DataFrame:
    return pd.read_csv(master / "corporate_actions.csv", parse_dates=["ex_date"])


@pytest.fixture(scope="session")
def manifests(master) -> dict:
    out = {}
    for layer in ("bhavcopy", "kite", "gdf"):
        p = master / f"prices/{layer}_manifest.json"
        out[layer] = json.load(open(p)) if p.exists() else {}
    return out


@pytest.fixture(scope="session")
def ex_dates_by_symbol(corporate_actions, manifests) -> dict:
    """symbol -> sorted ex-dates filed under that symbol or under any ticker its series traded as."""
    by_sym = {s: np.sort(g["ex_date"].values) for s, g in corporate_actions.groupby("symbol")}
    out = {}
    man = manifests["bhavcopy"]
    for sym in set(by_sym) | set(man):
        keys = {sym} | set(man.get(sym, {}).get("traded_as", []) or [])
        parts = [by_sym[k] for k in keys if k in by_sym]
        out[sym] = np.unique(np.concatenate(parts)) if parts else np.array([], dtype="datetime64[ns]")
    return out


@pytest.fixture(scope="session")
def scan(master, corporate_actions, ex_dates_by_symbol) -> Scan:
    share = corporate_actions[corporate_actions["type"].isin(SHARE_TYPES)]
    share_by_sym = {s: g for s, g in share.groupby("symbol")}
    files = sorted(glob.glob(str(master / "prices/adjusted_pr/*.csv")))
    assert files, f"no adjusted_pr files under {master}"
    sc = Scan(summary=pd.DataFrame(), sessions=pd.DatetimeIndex([]))
    rows, all_dates = [], set()
    for f in files:
        sym = os.path.basename(f)[:-4]
        rec = {"symbol": sym}
        try:
            df = pd.read_csv(f)
        except Exception as exc:                                  # noqa: BLE001 — the test reports, it does not recover
            sc.schema_errors.append((sym, f"unreadable: {exc}")); continue
        if list(df.columns) != PR_COLS:
            sc.schema_errors.append((sym, f"columns {list(df.columns)}"))
        if df.empty:
            sc.schema_errors.append((sym, "empty")); continue
        d = pd.to_datetime(df["date"])
        dv = d.values
        n = len(df)
        c = df["close"].to_numpy(float); o = df["open"].to_numpy(float)
        hi = df["high"].to_numpy(float); lo = df["low"].to_numpy(float)
        vol = df["volume"].to_numpy(float); fac = df["factor"].to_numpy(float)
        tol = 2e-4 + 1e-6 * np.abs(c)
        rec.update(
            n=n, first=dv[0], last=dv[-1],
            nonmidnight=int((d.dt.normalize() != d).sum()),
            dup_dates=int(d.duplicated().sum()),
            nonincreasing=int((d.diff().dt.total_seconds().fillna(1) <= 0).sum()),
            close_nan=int(np.isnan(c).sum()), close_nonpositive=int((c <= 0).sum()),
            ohl_nan=int(np.isnan(o).sum() + np.isnan(hi).sum() + np.isnan(lo).sum()),
            high_below_low=int((hi < lo - 5e-5).sum()), low_negative=int((lo < 0).sum()),
            open_outside=int(((o < lo - tol) | (o > hi + tol)).sum()),
            close_outside=int(((c < lo - tol) | (c > hi + tol)).sum()),
            volume_nan=int(np.isnan(vol).sum()), volume_negative=int((vol < 0).sum()),
            factor_nan=int(np.isnan(fac).sum()), factor_nonpositive=int((fac <= 0).sum()),
            factor_last=float(fac[-1]),
        )
        all_dates.update(dv)
        step_i = np.nonzero(np.abs(np.diff(fac)) > 1e-9)[0] + 1
        with np.errstate(invalid="ignore", divide="ignore"):
            ratios = fac[step_i] / fac[step_i - 1]
        sc.factor_steps[sym] = pd.DataFrame({"date": dv[step_i], "ratio": ratios})
        allex = ex_dates_by_symbol.get(sym, np.array([], dtype="datetime64[ns]"))
        n_unexplained = 0
        for k, ix in enumerate(step_i):
            window = (allex > dv[ix - 1] - np.timedelta64(4, "D")) & (allex <= dv[ix] + np.timedelta64(4, "D"))
            if not window.any():
                n_unexplained += 1
                sc.unexplained_steps.append((sym, pd.Timestamp(dv[ix]), float(ratios[k])))
        rec["factor_steps"] = len(step_i)
        rec["steps_unexplained"] = n_unexplained
        # every filed share event inside the span should show up as a step
        g = share_by_sym.get(sym)
        n_unapplied = 0
        if g is not None and n > 1:
            in_span = g[(g["ex_date"].values > dv[0]) & (g["ex_date"].values <= dv[-1])].drop_duplicates(["ex_date", "type"])
            step_dates = dv[step_i]
            for e in in_span.itertuples():
                if pd.isna(e.factor_or_amount) or abs(float(e.factor_or_amount) - 1.0) < 1e-6:
                    continue                                     # a unit factor cannot produce a visible step
                exd = np.datetime64(e.ex_date)
                if not ((step_dates > exd - np.timedelta64(5, "D")) & (step_dates < exd + np.timedelta64(5, "D"))).any():
                    n_unapplied += 1
                    sc.unapplied_events.append((sym, pd.Timestamp(e.ex_date), e.type, float(e.factor_or_amount),
                                                str(e.detail).startswith("observed")))
        rec["events_unapplied"] = n_unapplied
        # one-session moves the adjustment does not explain
        with np.errstate(invalid="ignore", divide="ignore"):
            ret = c[1:] / c[:-1] - 1.0
        for ix in np.nonzero(np.abs(ret) > JUMP_THRESHOLD)[0] + 1:
            exd = dv[ix]
            near = bool(((allex > exd - np.timedelta64(6, "D")) & (allex < exd + np.timedelta64(6, "D"))).any()) if len(allex) else False
            if not near:
                sc.jumps.append((sym, pd.Timestamp(exd), float(ret[ix - 1])))
        # raw x factor identity
        raw_path = master / f"prices/bhavcopy/{sym}.csv"
        if raw_path.exists():
            r = pd.read_csv(raw_path, usecols=["date", "close"])
            rd = pd.to_datetime(r["date"]).values
            aligned = len(rd) == n and bool((rd == dv).all())
            rec["raw_aligned"] = int(aligned)
            if aligned:
                pred = np.round(r["close"].to_numpy(float) * fac, 4)
                err = np.abs(pred - c)
                bad = int((err > TICK).sum())
                rec["adj_mismatch"] = bad
                if bad:
                    k = int(np.argmax(err))
                    sc.mismatches.append((sym, pd.Timestamp(dv[k]), float(c[k]), float(pred[k]), bad))
            else:
                rec["adj_mismatch"] = 0
        else:
            rec["raw_aligned"] = -1; rec["adj_mismatch"] = 0
        # the total-return view beside it
        tr_path = master / f"prices/adjusted_tr/{sym}.csv"
        if tr_path.exists():
            t = pd.read_csv(tr_path, usecols=["date", "factor"])
            td = pd.to_datetime(t["date"]).values
            rec["tr_aligned"] = int(len(td) == n and bool((td == dv).all()))
            rec["tr_above_pr"] = int((t["factor"].to_numpy(float) > fac + 1e-9).sum()) if rec["tr_aligned"] else -1
        else:
            rec["tr_aligned"] = -1; rec["tr_above_pr"] = -1
        rows.append(rec)
    sc.summary = pd.DataFrame(rows).set_index("symbol")
    sc.sessions = pd.DatetimeIndex(sorted(all_dates))
    return sc


@pytest.fixture(scope="session")
def membership(master) -> dict:
    from scripts.universe_membership import load_membership
    out = {}
    for idx in ("nifty250", "nse500", "nifty100", "nifty50"):
        p = master / f"membership/{idx}.csv"
        if p.exists():
            out[idx] = load_membership(p)
    return out


@pytest.fixture(scope="session")
def latest_session(scan) -> pd.Timestamp:
    return scan.sessions[-1]


@pytest.fixture(scope="session")
def current_members(membership, latest_session) -> set:
    from scripts.universe_membership import members_asof
    return members_asof(membership["nifty250"], latest_session)


@pytest.fixture(scope="session")
def panels(master):
    """The exact load scripts/rebuilt_books.py does before a run."""
    from data_pipeline.master_store.views import ensure_panel_views
    from data_pipeline.loaders import load_price_panels
    ensure_panel_views(master)
    return load_price_panels(master / "panels/pr")


@pytest.fixture(scope="session")
def kite_ratio_steps(master, ex_dates_by_symbol, corporate_actions) -> pd.DataFrame:
    """Steps in adjusted_pr.close / kite.close — verify_kite_adjustment's idea applied to the view the books read.

    Columns: symbol, date, step, near_ca, dividend_explained. Kite's series is dividend-adjusted and the price-return
    view is not, so small steps are expected; the tests separate the census (D-36) from share-scale steps (D-37).
    """
    div = corporate_actions[corporate_actions["type"] == "dividend"]
    div_by_sym = {s: g for s, g in div.groupby("symbol")}
    rows = []
    for f in sorted(glob.glob(str(master / "prices/kite/*.csv"))):
        sym = os.path.basename(f)[:-4]
        adj = master / f"prices/adjusted_pr/{sym}.csv"
        if not adj.exists():
            continue
        k = pd.read_csv(f, usecols=["date", "close"], parse_dates=["date"]).drop_duplicates("date", keep="last").set_index("date")["close"]
        a = pd.read_csv(adj, usecols=["date", "close"], parse_dates=["date"]).set_index("date")["close"]
        j = pd.concat([k.rename("k"), a.rename("a")], axis=1, join="inner")
        j = j[(j["k"] > 0) & (j["a"] > 0)]
        if len(j) < 60:
            continue
        ratio = j["a"] / j["k"]
        before = ratio.rolling(5).median().shift(1)
        after = ratio[::-1].rolling(5).median()[::-1]
        step = (after / before).dropna()
        cand = step[(step - 1).abs() > 0.004]
        if not len(cand):
            continue
        first_of_run = ~(cand.index.to_series().diff() <= pd.Timedelta(days=4)).fillna(False).values
        allex = ex_dates_by_symbol.get(sym, np.array([], dtype="datetime64[ns]"))
        dg = div_by_sym.get(sym)
        for d, v in cand[first_of_run].items():
            dd = np.datetime64(d)
            near = bool(((allex > dd - np.timedelta64(6, "D")) & (allex < dd + np.timedelta64(6, "D"))).any()) if len(allex) else False
            explained = False
            if dg is not None:
                w = dg[(dg["ex_date"] >= d - pd.Timedelta(days=8)) & (dg["ex_date"] <= d + pd.Timedelta(days=8))]
                if len(w):
                    loc = j.index.get_loc(d)
                    p_cum = float(j["k"].iloc[max(loc - 1, 0)])
                    size = abs(1.0 - (1.0 / float(v)))
                    for amount in w["factor_or_amount"].dropna().astype(float):
                        if p_cum > 0 and abs(amount / p_cum - size) < 0.03:
                            explained = True; break
            rows.append((sym, pd.Timestamp(d), float(v), near, explained))
    return pd.DataFrame(rows, columns=["symbol", "date", "step", "near_ca", "dividend_explained"])


@pytest.fixture(scope="session")
def book_holdings(master) -> dict:
    """book -> set of held symbols from the newest local runner output, or {} when neither book has been run here."""
    out = {}
    for book in ("mm_v1", "om25_v4"):
        latest = ROOT / f"data/{book}_portfolios/latest.json"
        if not latest.exists():
            continue
        try:
            run = ROOT / f"data/{book}_portfolios" / json.load(open(latest))["path"]
            trades = pd.read_csv(run / f"{book}_trades.csv")
            exits = pd.read_csv(run / f"{book}_exits.csv")
        except Exception:                                          # noqa: BLE001 — absent or half-written output is "no holdings"
            continue
        sym_col = "symbol" if "symbol" in trades.columns else trades.columns[1]
        held = set(trades[sym_col]) - set(exits[sym_col] if sym_col in exits.columns else [])
        if held:
            out[book] = held
    return out


# ===========================================================================
# Book behaviour suite (TESTS_BOOKS.md) — fixtures for test_books_*.py
#
# Names are deliberately distinct from the store-integrity fixtures above
# (`book_panels`, not `panels`) so the two suites share one conftest without
# either shadowing the other.
# ===========================================================================
import subprocess  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import BOOKS, REFERENCE, START  # noqa: E402,F401
from _harness import BookRun, Replay, StoreCtx, build_ctx, load_panels, load_run  # noqa: E402

RUNNER = ROOT / "scripts" / "run_rebuilt_book.py"


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: needs a full book run or the whole price panel")


@pytest.fixture(scope="session")
def runs_dir(tmp_path_factory) -> Path:
    """Where the two book runs land. BOOK_VERIFY_RUNS=<dir> reuses output from an earlier session."""
    override = os.environ.get("BOOK_VERIFY_RUNS")
    if override:
        d = Path(override)
        d.mkdir(parents=True, exist_ok=True)
        return d
    return tmp_path_factory.mktemp("book_runs")


@pytest.fixture(scope="session")
def runs(runs_dir, master) -> dict:
    """book -> BookRun from one fresh `run_rebuilt_book.py --start 2010-01-01` per book."""
    out = {}
    for book in BOOKS:
        target = runs_dir / book
        if not (target / "metrics.json").exists():
            proc = subprocess.run(
                [sys.executable, str(RUNNER), "--book", book, "--start", START, "--output-dir", str(target)],
                cwd=ROOT, capture_output=True, text=True)
            if proc.returncode != 0 or not (target / "metrics.json").exists():
                pytest.fail(f"run_rebuilt_book.py --book {book} failed\n"
                            f"{proc.stdout[-4000:]}\n{proc.stderr[-4000:]}")
        out[book] = load_run(book, target)
    return out


@pytest.fixture(scope="session")
def book_panels(master):
    """Close and trade panels as the books read them, loaded once for the whole session."""
    return load_panels(master)


@pytest.fixture(scope="session")
def ctxs(book_panels, master) -> dict:
    """book -> StoreCtx: an independent re-assembly of the engine's inputs."""
    return {book: build_ctx(book, book_panels, master=master) for book in BOOKS}


@pytest.fixture(scope="session")
def replays(ctxs, runs) -> dict:
    """book -> Replay: the per-rebalance re-derivation, built once."""
    return {book: Replay(ctxs[book], runs[book]).run_all() for book in BOOKS}
