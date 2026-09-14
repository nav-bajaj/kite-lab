"""Synthetic membership files for the foresight ladder.

Each variant takes the honest point-in-time membership file and adds exactly
one piece of hindsight, so the CAGR step between consecutive rungs prices that
piece. Everything is expressed as a membership CSV
(symbol, effective_from, effective_to) and fed to the unchanged engine through
scripts.universe_membership.resolve_universe -- no engine change, no new score.

  b0  honest          the point-in-time file as built by market_data_spine
  b1  immortal        b0 minus every symbol whose feed dies before the panel end
  b1f fail-only         b0 minus only the symbols that die AFTER a deep drawdown
  b2  early           b1, every surviving ever-member eligible from its first
                      priced session (knowing in advance who would qualify)
  b3  backdated       today's member list, eligible over all history -- the
                      legacy bug that produced the published track records
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO = Path("/Users/navdeep/kite-lab")
sys.path.insert(0, str(REPO))
from scripts.universe_membership import load_membership, members_asof  # noqa: E402

MASTER = REPO / "data/master"
PANEL = MASTER / "panels/pr"
TASK = Path(__file__).resolve().parent.parent
CACHE = TASK / "runs"                 # overridden when running against an alternative panel
OUT = TASK / "runs/membership"
DEAD_TOL_DAYS = 90      # a feed that stops within this of the panel end is live, not delisted
FAIL_DD = 0.60          # drawdown from the trailing 3y peak that makes a death a blow-up rather than a merger


def panel_span() -> pd.DataFrame:
    """symbol -> first/last priced session and the drawdown it died at. Cached."""
    cache = CACHE / "panel_span.csv"
    if cache.exists():
        return pd.read_csv(cache, parse_dates=["first", "last"]).set_index("symbol")
    rows = []
    for f in sorted(PANEL.glob("*_day.csv")):
        d = pd.read_csv(f, usecols=["date", "close"], parse_dates=["date"]).dropna().sort_values("date")
        if d.empty:
            continue
        c = d.set_index("date")["close"]
        peak = c.tail(756).max()   # trailing three years, so a long-dead name is judged against its own era
        rows.append(dict(symbol=f.name[:-8], first=c.index[0], last=c.index[-1], death_dd=float(c.iloc[-1] / peak - 1)))
    df = pd.DataFrame(rows).set_index("symbol")
    cache.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache)
    return df


def deaths(span: pd.DataFrame) -> pd.DataFrame:
    cut = span["last"].max() - pd.Timedelta(days=DEAD_TOL_DAYS)
    return span[span["last"] < cut]


def build(universe: str) -> dict:
    """Write the five membership variants for `universe`; return {tag: path}."""
    src = MASTER / f"membership/{universe}.csv"
    df = load_membership(src)
    span = panel_span()
    dead = deaths(span)
    ever = sorted(set(df["symbol"]))
    dead_here = [s for s in ever if s in dead.index]
    failed = [s for s in dead_here if dead.loc[s, "death_dd"] <= -FAIL_DD]
    alive = [s for s in ever if s not in dead.index]
    OUT.mkdir(parents=True, exist_ok=True)

    def write(tag, frame):
        p = OUT / f"{universe}_{tag}.csv"
        frame.to_csv(p, index=False, date_format="%Y-%m-%d")
        return p

    paths = {"b0": src}
    paths["b1"] = write("b1", df[df["symbol"].isin(alive)])
    paths["b1f"] = write("b1f", df[~df["symbol"].isin(failed)])
    early = pd.DataFrame(dict(symbol=alive))
    early["effective_from"] = [span.loc[s, "first"] if s in span.index else pd.Timestamp("1900-01-01") for s in alive]
    early["effective_to"] = pd.NaT
    early["note"] = "early access: eligible from first priced session"
    paths["b2"] = write("b2", early)
    today = sorted(members_asof(df, span["last"].max()))
    back = pd.DataFrame(dict(symbol=today, effective_from=pd.Timestamp("1900-01-01"), effective_to=pd.NaT,
                             note="backdated: today's list over all history"))
    paths["b3"] = write("b3", back)

    print(f"{universe}: {len(ever)} ever-members | {len(dead_here)} die "
          f"({len(failed)} after a >{100*FAIL_DD:.0f}% drawdown, {len(dead_here)-len(failed)} near their peak) "
          f"| {len(today)} members today", flush=True)
    return paths


if __name__ == "__main__":
    for u in sys.argv[1:] or ["nifty250", "nse500"]:
        build(u)


def turnover_panel() -> pd.DataFrame:
    """Rupee traded value per symbol, from the RAW bhavcopy. Cached.

    Not close x volume off the adjusted panel: volume there is scaled by the
    share-count factor only, so on a dividend the adjusted product understates
    the rupees that actually changed hands (~8% on RELIANCE over the span).
    A liquidity screen has to rank on what a desk would have seen, so the raw
    bhavcopy is the source; the panel's `traded_as` carries the symbol each
    name traded under on each date, which is the join key across renames.
    """
    cache = CACHE / "turnover_all.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    key = []
    for f in sorted(PANEL.glob("*_day.csv")):
        d = pd.read_csv(f, usecols=["date", "traded_as"], parse_dates=["date"])
        d["canonical"] = f.name[:-8]
        key.append(d)
    key = pd.concat(key, ignore_index=True).rename(columns={"traded_as": "symbol"})
    bc = pd.read_parquet(MASTER / "bhavcopy_eq.parquet", columns=["date", "symbol", "series", "close", "volume"])
    bc = bc[bc["series"] == "EQ"]
    bc["tv"] = bc["close"] * bc["volume"]
    j = key.merge(bc[["date", "symbol", "tv"]], on=["date", "symbol"], how="left")
    df = j.pivot_table(index="date", columns="canonical", values="tv", aggfunc="sum").sort_index()
    df.to_parquet(cache)
    return df


def build_liquidity(universe: str, top_n: int, window: int = 63, min_hist: int = 252,
                    min_price: float = 10.0) -> Path:
    """b4 -- a point-in-time investable universe with no index reference at all.

    Monthly, rank every priced name by trailing median rupee turnover and take
    the top `top_n`, breadth-matched to the index it replaces. Uses only data
    available on the ranking date, so it carries no foresight about who would
    later qualify for anything. Its remaining optimism is the price panel's own
    coverage: the panel holds ever-members of the four NSE indices, so names
    that never made any index cannot be selected (PLAN.md, limitation 2).
    """
    tv = turnover_panel()
    close = pd.DataFrame({f.name[:-8]: pd.read_csv(f, usecols=["date", "close"], parse_dates=["date"]).set_index("date")["close"]
                          for f in sorted(PANEL.glob("*_day.csv"))}).reindex(tv.index)
    med = tv.rolling(window, min_periods=window // 2).median()
    hist = close.notna().cumsum()
    dates = pd.DatetimeIndex(sorted({d for d in tv.index}))
    months = pd.Series(dates, index=dates).groupby([dates.year, dates.month]).first()
    picks = {}
    for d in months:
        row = med.loc[d]
        ok = row.notna() & (hist.loc[d] >= min_hist) & (close.loc[d] >= min_price)
        picks[d] = set(row[ok].nlargest(top_n).index)
    rows = []
    for sym in tv.columns:
        run_start = None
        for d in months:
            inn = sym in picks[d]
            if inn and run_start is None:
                run_start = d
            elif not inn and run_start is not None:
                rows.append((sym, run_start, d)); run_start = None   # exclusive end: the first review it drops out
        if run_start is not None:
            rows.append((sym, run_start, pd.NaT))
    out = pd.DataFrame(rows, columns=["symbol", "effective_from", "effective_to"])
    out["note"] = f"top {top_n} by {window}d median turnover"
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{universe}_b4.csv"
    out.to_csv(p, index=False, date_format="%Y-%m-%d")
    print(f"{universe}: b4 top-{top_n} turnover | {out.symbol.nunique()} ever-members, {len(out)} windows", flush=True)
    return p


def build_floor(tag: str, floor: float, window: int = 63, min_hist: int = 252, min_price: float = 10.0) -> Path:
    """b5 -- the investability pool itself: every name clearing a turnover floor,
    no ranking and no breadth cap. This is what the placebo was drawing FROM, and
    the placebo said the drawing is what hurt. Reviewed monthly, point-in-time."""
    tv = turnover_panel()
    close = pd.DataFrame({f.name[:-8]: pd.read_csv(f, usecols=["date", "close"], parse_dates=["date"]).set_index("date")["close"]
                          for f in sorted(PANEL.glob("*_day.csv"))}).reindex(tv.index)
    med = tv.rolling(window, min_periods=window // 2).median()
    hist = close.notna().cumsum()
    idx = tv.index
    months = pd.Series(idx, index=idx).groupby([idx.year, idx.month]).first()
    picks = {d: set(med.columns[(med.loc[d] >= floor) & (hist.loc[d] >= min_hist) & (close.loc[d] >= min_price)])
             for d in months}
    rows = []
    for sym in tv.columns:
        start = None
        for d in months:
            inn = sym in picks[d]
            if inn and start is None:
                start = d
            elif not inn and start is not None:
                rows.append((sym, start, d)); start = None
        if start is not None:
            rows.append((sym, start, pd.NaT))
    out = pd.DataFrame(rows, columns=["symbol", "effective_from", "effective_to"])
    out["note"] = f"investable floor Rs {floor/1e7:.0f} cr"
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{tag}.csv"
    out.to_csv(p, index=False, date_format="%Y-%m-%d")
    n = pd.Series({d: len(v) for d, v in picks.items()})
    print(f"{tag}: floor Rs {floor/1e7:.0f} cr | {out.symbol.nunique()} ever-members | breadth "
          f"{n[n.index >= '2016'].min()}-{n[n.index >= '2016'].max()} (2016+, median {int(n[n.index >= '2016'].median())})", flush=True)
    return p


def build_once_in(universe: str, floor: float = 0.0, window: int = 63) -> Path:
    """b6 -- "once in the index, always eligible".

    A symbol becomes eligible on the date it FIRST enters the index and never
    leaves, optionally subject to a turnover floor thereafter. This is live-
    computable: keep a running list, never delete. It carries no foresight --
    unlike b2 it grants nothing before first inclusion, and unlike the b5 pool
    it admits no name that had not yet qualified at the time.

    It is also immune to the panel-coverage limitation that reversed b5 in
    Phase 4: the rule excludes names that were never index members BY DESIGN, so
    their absence from the panel is the rule working, not a bias.
    """
    df = load_membership(MASTER / f"membership/{universe}.csv")
    first = df.groupby("symbol")["effective_from"].min()
    OUT.mkdir(parents=True, exist_ok=True)
    tag = f"{universe}_oncein" + (f"_f{int(floor/1e7)}" if floor else "")
    if not floor:
        out = pd.DataFrame(dict(symbol=first.index, effective_from=first.values))
        out["effective_to"] = pd.NaT
    else:
        med = turnover_panel().rolling(window, min_periods=window // 2).median()
        idx = med.index
        months = pd.Series(idx, index=idx).groupby([idx.year, idx.month]).first()
        picks = {d: {s for s in first.index[first <= d] if s in med.columns and med.loc[d, s] >= floor} for d in months}
        rows = []
        for sym in first.index:
            start = None
            for d in months:
                inn = sym in picks[d]
                if inn and start is None:
                    start = d
                elif not inn and start is not None:
                    rows.append((sym, start, d)); start = None
            if start is not None:
                rows.append((sym, start, pd.NaT))
        out = pd.DataFrame(rows, columns=["symbol", "effective_from", "effective_to"])
        n = pd.Series({d: len(v) for d, v in picks.items()})
        print(f"  breadth {n[n.index >= '2016'].min()}-{n[n.index >= '2016'].max()} (2016+, median {int(n[n.index >= '2016'].median())})", flush=True)
    out["note"] = f"once in {universe}, always eligible" + (f", turnover >= Rs {floor/1e7:.0f} cr" if floor else "")
    p = OUT / f"{tag}.csv"
    out.to_csv(p, index=False, date_format="%Y-%m-%d")
    print(f"{tag}: {out.symbol.nunique()} ever-members", flush=True)
    return p


def build_decay(universe: str, months: int) -> Path:
    """b7 -- "once in, eligible for N months after demotion".

    Phase 8a found the ex-member sleeve is both growing (46% of the universe in
    2016 -> 60% in 2026, since once-in never removes anyone) and decaying (mean
    trip return +20%/+49% in 2016-17 -> -1%/-1% in 2025-26). An expiry window
    keeps the recently-demoted names, where the recovery effect lives, and drops
    the long-dead. months=0 is plain point-in-time; a large value is once-in.
    """
    df = load_membership(MASTER / f"membership/{universe}.csv")
    off = pd.DateOffset(months=months)
    rows = []
    for sym, g in df.groupby("symbol"):
        for w in g.itertuples():
            end = pd.NaT if pd.isna(w.effective_to) else w.effective_to + off
            rows.append((sym, w.effective_from, end))
    out = pd.DataFrame(rows, columns=["symbol", "effective_from", "effective_to"])
    # windows may now overlap or abut; merge per symbol so the file stays well-formed
    merged = []
    for sym, g in out.groupby("symbol"):
        g = g.sort_values("effective_from")
        cur_a, cur_b = None, None
        for r in g.itertuples():
            if cur_a is None:
                cur_a, cur_b = r.effective_from, r.effective_to
            elif pd.isna(cur_b) or r.effective_from <= cur_b:
                cur_b = pd.NaT if (pd.isna(cur_b) or pd.isna(r.effective_to)) else max(cur_b, r.effective_to)
            else:
                merged.append((sym, cur_a, cur_b)); cur_a, cur_b = r.effective_from, r.effective_to
        merged.append((sym, cur_a, cur_b))
    out = pd.DataFrame(merged, columns=["symbol", "effective_from", "effective_to"])
    out["note"] = f"{universe} + {months}m grace after demotion"
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{universe}_decay{months}.csv"
    out.to_csv(p, index=False, date_format="%Y-%m-%d")
    return p
