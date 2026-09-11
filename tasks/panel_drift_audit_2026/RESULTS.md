# Panel drift + membership audit

**Run date:** 2026-09-08 · **Panel:** `nse500_data_merged` (2005-01-03 → 2026-08-21)

Follow-on from `tasks/om25_cadence_2026`, which found that OM25 v3's published
OOS figures no longer reproduce. Two questions carried over:

1. Does the same drift hit **L6 v2**?
2. What does **effective-dated membership** actually do to a published number?

Both L6 runs go through the production runner unmodified —
`scripts/run_l6_v2_portfolio.py`, once with its default membership file and
once with `--membership /nonexistent_membership.csv` to force the legacy
snapshot path. No new backtest code.

> **Revision note.** The first version of this page claimed (a) that published
> figures carry ~2–2.5pp of inclusion bias from the legacy path and (b) that
> L6 v2 reproduces cleanly. **Both were wrong**, for the same reason: I used
> membership OFF as the archive-equivalent baseline. It isn't. Corrected
> throughout; the evidence is in §1.

---

## 1. Membership ON *is* the archive. Published figures were never biased by it.

### How universe changes were handled before

They weren't — not in any point-in-time sense. `data/static/*_universe.csv`
was a flat snapshot applied anachronistically to all of history, refreshed by
hand and rarely. From `tasks/universe_membership/PLAN.md`:

> `data/static/*_universe.csv` are point-in-time snapshots applied
> anachronistically: every daily pipeline run recomputes each portfolio from
> 2020 with *today's* universe. Editing the file therefore rewrites the
> published track record… The snapshots were last refreshed 2025-11-06.

That was the bug the task fixed, found 2026-07-09 via the TradingView
comparison (4 of the top 6M performers were unpickable from a stale snapshot).

### How the membership file was seeded — the decisive fact

It was seeded by **backdating the then-current snapshot to 1900-01-01**, then
appending dated rows for the July-2026 reconstitution. Verified against the
archive branch:

| | archive (May-2026) snapshot | today's snapshot | membership rows @1900-01-01 |
|---|---|---|---|
| NSE 500 | 500 | 500 (−34 / +34 vs archive) | 500 — **identical to archive** |
| Nifty 250 | 251 | 250 (−13 / +12 vs archive) | 250 — identical bar `DUMMYHDLVR` |

`DUMMYHDLVR` is a placeholder ticker with no price file in the panel, so it is
inert.

**Therefore membership ON reproduces exactly the universe that produced every
published figure, for every date before the 2026-07-13/15 cutover.** Membership
OFF does not — it backdates *today's* post-reconstitution snapshot.

This is not an inference; the universe_membership task pre-registered it as a
gate and verified it:

> Production L6 config, legacy vs membership mode: `l6_equity.csv`,
> `l6_trades.csv`, `l6_exits.csv` and all dashboard CSVs must be
> **byte-identical** while the price panel ends before the cutover date.
> Verified 2026-07-14.

Confirmed independently here from the trade logs — pre-cutover BUYs:

| | archive | mem ON | mem OFF |
|---|---|---|---|
| OM25 — names *dropped* at the 2026 refresh | 39 | 45 | **0** |
| OM25 — names *added* at the refresh | 0 | 0 | **22** |
| L6 v2 — names *dropped* | — | 249 | **0** |
| L6 v2 — names *added* | — | 0 | **49** |

### So what is the 2–2.5pp I measured?

It is **the anachronism one reconstitution cycle would inject if the July-2026
refresh had been applied the old way** — the size of the bug membership
prevents, not a defect in anything published. The legacy path *today* buys
MCX 8× from 2014 and RADICO 9× from 2017 (Nifty 250 entrants of July 2026), and
on NSE 500 buys CEMPRO 7× from 2022, GALLANTT and BELRISE 5× each. Those are
precisely the leaks `candidate_fn` was built to stop; PLAN.md names AIIL,
LAURUSLABS, MCX, RADICO and CEMPRO as the ones its regression caught.

Useful as a calibration — **a single reconstitution is worth ~2–4pp of fake
CAGR if backdated** — and that is the reason the feature exists. It is not a
reason to restate anything.

### What survives as a real caveat

Nothing processes universe changes *before* 2026-07-13. The file backdates a
2026-vintage snapshot to 1900. So all pre-2026 history still carries whatever
survivorship and inclusion bias that snapshot embeds — already documented in
`tasks/oos_retune_2026/RESULTS.md` ("universe is 2026-vintage… stocks delisted
between 2010-2016 are not in the panel"). **Membership froze that bias; it did
not remove it.** What it buys is that the bias stops *growing* with each future
reconstitution.

---

## 2. L6 v2 — does not cleanly reproduce either

`docs/portfolios.md` publishes L6 v2 at **CAGR 59.4% · Sharpe 1.92 ·
MaxDD −30.0%** over 2020-07-10 → 2026-02-02 (IS-only tune).

| Same window, today | CAGR | Sharpe | Max DD | |
|---|---|---|---|---|
| **Membership ON** | **56.21%** | 1.87 | −29.90% | **like-for-like** |
| Membership OFF (today's snapshot backdated) | 58.45% | 1.92 | −29.46% | not comparable |
| *Published* | *59.4%* | *1.92* | *−30.0%* | |

The OFF row sits closest to the published figure, and that is a **coincidence
of two errors cancelling** — panel drift pulls down, backdated inclusion bias
pushes up. The like-for-like comparison is the ON row: **−3.19pp**.

The same decomposition on OM25 over the identical window makes the pattern
explicit:

| Over 2020-07-10 → 2026-02-02 | OM25 | L6 v2 |
|---|---|---|
| panel drift (archive → today, phase-matched) | **-2.56pp** | **−3.19pp** |
| backdated inclusion bias (mem ON → mem OFF) | +3.71pp | +2.24pp |
| *(OM25 figures phase-matched to the archive grid)* | | |


Both strategies lose ground to the panel; both gain it back from the bias; the
cancellation is what made L6 look clean.

## 3. The drift is concentrated in 2017–2019

Same config, membership held constant (both arms archive-equivalent), archived
OM25 curve vs today by era:

All rows below are phase-matched (`--biweekly-phase 1`, the grid the archive
ran) and membership ON — like-for-like on every dimension except the panel:

| Window | archived | today | verdict |
|---|---|---|---|
| 2010-03 → 2016-12 | 28.59% / 1.60 | 27.19% / 1.43 | close |
| **2017-01 → 2019-12** | **26.14% / 1.60** | **15.03% / 0.76** | **Sharpe halved** |
| 2020-01 → 2026-05 | 52.65% / 1.98 | 50.42% / 1.92 | close |
| OOS_full 2017 → 2026-05 | 43.57% / 1.86 | 38.03% / 1.52 | **−5.54pp** |

**Phase correction.** The first version of this table compared against the
wrong bi-weekly phase (`fridays()[::2]` vs `[1::2]`); 201 of the archive's 296
trade dates fit phase 1, 66 fit phase 0. Phase alone is worth 3.10pp of
OOS_full CAGR, so the original −8.64pp was 5.54pp panel + 3.10pp phase. The
2017–2019 finding is unaffected.

So exposure scales with **how much of a published window sits in 2017–2019**:

| Portfolio | Published window | 2017–2019 share | Like-for-like gap |
|---|---|---|---|
| OM25 v3 | 2017 → 2026 | ~⅓ | **−5.54pp** |
| L6 v2 | 2020-07 → 2026-02 | none | **−3.19pp** |
| TL25 v3 | 2017 → 2026 | ~⅓ | **not checked** |
| COMBO Defensive | — | — | **not checked** |

Not a coverage gap: rows per symbol-year rise smoothly through 2017–2019
(158.9 → 166.7 → 172.6), zero duplicate dates across all 534 files, only NMDC
carries the known phantom-timestamp rows. It is price-level change — replaying
the archived OM25 trade log against today's panel, 104 of 1,414 executions
(7.4%) differ by >0.5%, with clear corporate-action signatures (IRB 2020-07-27
ratio 1.999 = 2:1 split; TRENT 2016-05-09 ratio 1.459; MPHASIS 1.104).

**Unresolved:** whether the new panel is more correct than the old one. Nobody
has established that the 2017–2019 numbers are now *wrong* rather than now
*right*. `tasks/corporate_actions_fix` and `tasks/adjusted_price_series` are
the open threads.

---

## Implications

1. **Universe membership is a non-issue for published figures.** Do not
   restate anything on its account. It reproduces the old universe exactly and
   was gate-verified to do so.
2. **Every production portfolio is exposed to the panel change**, L6 included —
   just in proportion to how much of its published window sits pre-2020.
   OM25 −5.54pp, L6 −3.19pp.
3. **The one decision that matters is whether the current panel is right.**
   Everything else waits on it.
4. **TL25 v3 and COMBO are unchecked** and TL25 shares OM25's window.

## How to rerun

```bash
python scripts/run_l6_v2_portfolio.py --output-dir <dir>                # membership ON = archive-equivalent
python scripts/run_l6_v2_portfolio.py --membership /nonexistent.csv \
    --output-dir <dir>                                                  # legacy path — for bias measurement only
```

Always compare published figures against the **ON** arm.

## Caveats

- L6 v2's published window is an **IS-only tune** (`docs/portfolios.md` says
  so). Reproducing it validates the data path, not the strategy.
- It is not certain which price directory produced L6's published 59.4% —
  `nse500_data_merged` (the runner default) is assumed. If it was the live
  `nse500_data`, the −3.19pp gap needs re-measuring against that panel.
- Survivorship: the membership file backdates a 2026-vintage snapshot, so
  pre-2026 delistings are absent from every arm here. Unchanged from before.
- Sharpe quoted rf=0 to match `docs/portfolios.md`; the L6 runner's own
  `metrics.json` uses rf=5%.
- Artifacts under `runs/` are caught by `.gitignore`'s blanket `*.csv`.
