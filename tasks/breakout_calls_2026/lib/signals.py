"""§2 — the signal tape.

Emits every pivot event the detector finds, labelled, rather than only the
ones that worked. Three labels, from TASKS.md §2:

  E1          price touched the pivot intraday — a resting stop-buy fills
  E2          a close cleared the pivot — buy the next open
  failed_poke E1 fired and E2 never did on that base

The competitor's backtest books an E1 fill price on the E2 subset. Keeping
the two tapes separate is what lets us price that.

Detector anatomy is inherited from `vcp_reference.py` (commit 82d42ef),
`standard_no_l6` tier — that study found the L6 gate subtracts, so it is not
carried forward.

Two deliberate departures from the reference:

1. **Indicators are computed per symbol on that symbol's own dropna'd
   series, never on a wide multi-symbol panel.** With 2,519 symbols and 560
   delisted names a wide panel is dense with interior NaNs, and a rolling()
   over those silently eats whole windows. Per-symbol is immune.
2. **The universe mask is point-in-time**, applied at the entry bar, from
   `universe.py` — not a static membership list.
"""
from __future__ import annotations

import os
import numpy as np
import pandas as pd

from vcp_reference import (  # noqa: E402  - anatomy is inherited verbatim
    FRACTAL_N, BASE_MIN_BARS, BASE_MAX_BARS, PRIOR_ADVANCE_MIN,
    ABOVE_LOW_MIN, NEAR_HIGH_MAX, BREAKOUT_BUFFER, BREAKOUT_VOL_MULT,
    BREAKOUT_WINDOW, TIERS, find_pivots, base_structure, contraction_legs,
)

PANELS = "data/master/prices/adjusted_pr"
TIER = dict(TIERS["standard"])          # standard_no_l6 == standard minus the gate
MIN_BARS = 300


def _indicators(df: pd.DataFrame) -> dict:
    c, h, l, v = df.close, df.high, df.low, df.volume
    return dict(
        s50=c.rolling(50).mean().to_numpy(),
        s150=c.rolling(150).mean().to_numpy(),
        s200=c.rolling(200).mean().to_numpy(),
        s200p=c.rolling(200).mean().shift(21).to_numpy(),
        h52=h.rolling(252).max().to_numpy(),
        l52=l.rolling(252).min().to_numpy(),
        v50=v.rolling(50).mean().to_numpy(),
    )


def _base_ok(pivots, k, pi, bo, h, l, cl, v, cfg):
    """Every anatomy gate except the breakout-day ones. -> (ok, reason, meta)"""
    start = base_structure(pivots, k)
    base_start = pivots[start][0]
    base_len = bo - base_start
    legs = contraction_legs(pivots, start, k)
    pivot_price = pivots[k][2]
    final_low = l[pi + 1: bo].min() if bo > pi + 1 else l[pi]
    final_depth = (pivot_price - final_low) / pivot_price
    depths = [lg["depth"] for lg in legs] + [final_depth]
    meta = dict(base_start=base_start, base_len=base_len, final_low=final_low,
                final_depth=final_depth, n_contractions=len(depths),
                first_depth=depths[0] if depths else np.nan)

    if not (BASE_MIN_BARS <= base_len <= BASE_MAX_BARS):
        return False, "base_length", meta
    if not (cfg["min_contractions"] <= len(depths) <= cfg["max_contractions"]):
        return False, "contraction_count", meta
    if not (cfg["first_leg"][0] <= depths[0] <= cfg["first_leg"][1]):
        return False, "first_leg_depth", meta
    if final_depth >= cfg["final_leg_max"]:
        return False, "final_leg_depth", meta
    if any(depths[i + 1] >= depths[i] * cfg["tighten_ratio"] for i in range(len(depths) - 1)):
        return False, "monotonic_tightening", meta
    pre_lo = l[max(0, base_start - 126): base_start]
    if len(pre_lo) < 30 or (h[base_start] / pre_lo.min() - 1) < PRIOR_ADVANCE_MIN:
        return False, "prior_advance", meta
    if cfg["vol_dryup"] is not None and legs:
        f = legs[0]
        v_first = v[f["hi_idx"]: f["lo_idx"] + 1].mean()
        v_final = v[pi: bo].mean()
        if not (v_final < cfg["vol_dryup"] * v_first):
            return False, "vol_dryup", meta
    if cfg["tight_bars"] is not None:
        t0 = max(base_start, bo - cfg["tight_bars"])
        if (h[t0:bo].max() - l[t0:bo].min()) / pivot_price >= cfg["tight_range"]:
            return False, "tightness", meta
    return True, None, meta


def _trend_ok(i, cl, ind):
    """Stage-2 trend template on the entry bar. NaN-safe."""
    s50, s150, s200, s200p = ind["s50"][i], ind["s150"][i], ind["s200"][i], ind["s200p"][i]
    h52, l52 = ind["h52"][i], ind["l52"][i]
    if np.isnan([s50, s150, s200, s200p, h52, l52]).any():
        return False
    return (cl[i] > s50 > s150 > s200 and s200 > s200p
            and cl[i] >= (1 + ABOVE_LOW_MIN) * l52
            and cl[i] >= (1 - NEAR_HIGH_MAX) * h52)


def scan_symbol(sym: str, elig: set, cfg: dict = TIER) -> list[dict]:
    """All pivot events for one symbol. `elig` is the set of dates on which
    the symbol cleared the point-in-time liquidity floor."""
    f = os.path.join(PANELS, f"{sym}.csv")
    if not os.path.exists(f):
        return []
    df = pd.read_csv(f, parse_dates=["date"]).dropna(subset=["close"]).set_index("date")
    df = df[~df.index.duplicated()].sort_index()
    if len(df) < MIN_BARS:
        return []

    o, h, l, cl, v = (df[c].to_numpy(float) for c in ("open", "high", "low", "close", "volume"))
    dates = df.index
    ind = _indicators(df)
    pivots = find_pivots(h, l)
    n = len(cl)
    out = []
    # No "already in a trade" dedup here on purpose: §2 is the tape of every
    # signal. Which of them a book can actually take is §5's job, and it
    # depends on slot count, so deciding it here would prejudge that.

    for k, ph in enumerate(pivots):
        if ph[1] != "H":
            continue
        pi, _, pivot_price = ph
        trigger = pivot_price * BREAKOUT_BUFFER
        confirm = pi + FRACTAL_N

        # --- E1: first bar a resting stop-buy at the pivot would trigger ---
        e1 = e2 = None
        for j in range(confirm + 1, min(pi + BREAKOUT_WINDOW, n)):
            if h[j] >= trigger:
                e1 = j
                break
        # --- E2: first bar whose CLOSE clears the pivot. The reference
        # abandons the base on a poke-and-fail, and that rule is inherited so
        # the E2 tape stays exactly the study we are comparing against. ---
        for j in range(confirm + 1, min(pi + BREAKOUT_WINDOW, n)):
            if cl[j] > trigger:
                e2 = j
                break
            if h[j] > pivot_price * 1.02 and cl[j] <= pivot_price:
                break
        if e1 is None and e2 is None:
            continue

        for kind, bo in (("E1", e1), ("E2", e2)):
            if bo is None or bo - pi < 2:
                continue
            if kind == "E2" and bo + 1 >= n:
                continue          # E2 fills next open, so it needs a next bar
            if dates[bo] not in elig:
                continue
            # Which bar the gates may look at. E1 fills INTRADAY on `bo`, so
            # that bar's full-day volume and its close do not exist yet at the
            # moment a stop-buy triggers — gating on them would be precisely
            # the look-ahead this task exists to avoid. E1 is therefore judged
            # on data through bo-1. E2's signal IS the close of `bo` and it
            # fills the next open, so `bo` is legitimately available to it.
            g = bo - 1 if kind == "E1" else bo
            if g < 1:
                continue
            # The breakout-volume confirmation (v >= 1.5x the 50-day average)
            # is an END-OF-DAY quantity. E2's signal is the close, so it may
            # use it. A stop-buy that triggers intraday cannot: the day's
            # volume does not exist yet. So E1 is placed on base anatomy and
            # the prior close alone, with no volume confirmation available to
            # it at all.
            #
            # That asymmetry is not a modelling nuisance, it is the finding:
            # you cannot have the pivot fill price AND the volume filter in
            # the same trade. The competitor's default takes both.
            if kind == "E2":
                if np.isnan(ind["v50"][g]) or not (v[g] >= BREAKOUT_VOL_MULT * ind["v50"][g]):
                    continue
            if not _trend_ok(g, cl, ind):
                continue
            ok, reason, meta = _base_ok(pivots, k, pi, bo, h, l, cl, v, cfg)
            if not ok:
                continue

            entry = trigger if kind == "E1" else o[bo + 1]
            # Two different questions. `confirmed_same_bar` asks whether the
            # bar we filled on also closed above. `base_confirmed` asks
            # whether a close ever cleared the pivot on this base at all — and
            # it is the second one that defines a failed poke (TASKS.md §2):
            # a stop-buy that filled on a base which never confirmed.
            confirmed = bool(cl[bo] > trigger)
            base_confirmed = e2 is not None
            out.append(dict(
                symbol=sym, kind=kind,
                signal_date=dates[bo].date().isoformat(),
                entry_date=dates[bo if kind == "E1" else bo + 1].date().isoformat(),
                entry=round(float(entry), 4),
                pivot=round(float(pivot_price), 4),
                stop_ref=round(float(meta["final_low"]), 4),
                confirmed_same_bar=confirmed,
                base_confirmed=base_confirmed,
                failed_poke=bool(kind == "E1" and not base_confirmed),
                bar=bo, base_len=int(meta["base_len"]),
                base_start=dates[meta["base_start"]].date().isoformat(),
                n_contractions=int(meta["n_contractions"]),
                first_depth=round(float(meta["first_depth"]), 4),
                final_depth=round(float(meta["final_depth"]), 4),
                year=dates[bo].year,
            ))
    return out
