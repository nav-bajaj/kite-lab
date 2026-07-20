# raam_transplant — task breakdown

Owners: 🤖 agent, 👤 Navdeep. Every phase ends with a 👤 checkpoint —
results reviewed and direction confirmed before the next phase starts.

## Phase 0 — Diagnostics (no strategy changes)

| # | Task | Owner | Risk |
|---|---|---|---|
| 0.1 | ~~Data audit + refresh~~ **DONE** — panel through 2026-07-20; found + flagged the local NIFTY 100 regime-path split (repo `indices_data_historical` stale 05-08, insight-engine path fresh) | 🤖 | data-gap |
| 0.2 | ~~Reproduce L6 v2 baseline~~ **DONE** — `baseline_l6.py`; Sharpe 1.90 / MaxDD −29.4 reproduce docs tightly; CAGR 54.5 vs 59.4 = refreshed-panel drift (same engine code path, so data not logic). Turnover/hit are definitional — standardize via `summarise_metrics` in Phase 1 | 🤖 | lookahead |
| 0.3 | ~~Residual-correlation panel~~ **DONE** — `residuals.py` (reusable by-product); rolling L6-book crowding reconstructed 2017→now via `crowding_diagnostic.py` | 🤖 | compute-cost |
| 0.4 | ~~Diagnostic study~~ **DONE** — see G0 verdict below. Fixed a mis-specified breadth metric (top-40-rank breadth is tautologically ~1.0; switched to market-wide) | 🤖 | multiple-comparisons |
| 0.5 | 👤 checkpoint: **G0 verdict — crowding weak-green, breadth-throttle (E2) REFUTED** | 👤 | — |

### G0 verdict (2026-07-20, `runs/crowding_diag_*`)

- **Crowding → forward drawdown:** weak but directionally consistent. Spearman(crowding, fwd_maxdd_20) = **−0.19**; top crowding quintile −7.2% 20d DD vs −6.0% bottom. Forward *return* is flat across crowding buckets (Spearman ≈0) → **de-crowding may trim DD at ~no return cost.** Signal fades past 20d. **E1 proceeds, low prior on a large win.**
- **Breadth → forward outcomes:** **U-shaped, not monotone.** Low breadth (washed-out) = strong forward returns; mid-breadth = worst returns + deepest DD; high breadth = best. A linear breadth throttle (E2) would cut risk at the bullish lows — **refuted.** The only viable breadth signal is a non-linear mid-breadth regime flag, which duplicates the already-rejected `breadth_atlas/combo_3state`. **E2 dropped in its planned form.**
- **By-product:** the crowding gauge is shippable to the insight-engine admin panel regardless of E1's outcome.

## Phase 1 — E1: correlation-penalized selection (L6-DIV)

| # | Task | Owner | Risk |
|---|---|---|---|
| 1.1 | ~~Greedy corr-penalized scorer~~ **DONE** — `e1_l6div.py` (path-dependent greedy run inside score_fn; λ=0 reproduces L6) | 🤖 | lookahead |
| 1.2 | ~~Tune λ on IS, run OOS~~ **DONE** — λ*=1.0; net-of-slip CAGR +0.2/+3.3/+1.7pp OOS, Calmar 2/3 | 🤖 | overfit |
| 1.3 | ~~Gate + robustness~~ **DONE** — `e1_robustness.py`; smooth λ∈[0.5,1.5] plateau (not knife-edge), crowd-window 42/63/126 all positive | 🤖 | — |
| 1.4 | 👤 checkpoint: **E1 = robust qualified PASS** (locked λ=1.0). Turnover gate fails on artifact scale; cost_drag +0.3pp/yr absorbed in improved net CAGR | 👤 | — |

**E1 verdict:** robust, modest improvement — de-crowding L6's book by nudging out the 2-3 most residual-correlated names/week buys ~+1.7pp OOS CAGR and better Calmar in 2/3 windows, net of costs. Helps most in trending/crowding eras (2020-22, 2023-26), neutral-to-slightly-negative in low-momentum chop (2017-19). Not a production decision here — a validated candidate + the crowding gauge (Phase 3) are the deliverables.

## Phase 2 — E2: bottom-up breadth throttle

| # | Task | Owner | Risk |
|---|---|---|---|
| 2.1 | Implement breadth-throttle exposure panel (float regime_panel) | 🤖 | lookahead |
| 2.2 | Tune floor on IS only; rolling-window T1-style battery vs bare L6 | 🤖 | overfit |
| 2.3 | Judge against pre-registered E2 gate; calendar-year DD table | 🤖 | — |
| 2.4 | 👤 checkpoint: E2 verdict + direction | 👤 | — |

## Phase 3 — E3: RC25 standalone (stretch, gated on E1 or E2 passing)

| # | Task | Owner | Risk |
|---|---|---|---|
| 3.1 | Full ranked-composite scorer (M + C + additive T, per-slot cash) | 🤖 | complexity |
| 3.2 | Four-window run; differentiation metrics vs L6/OM25/TL25/COMBO | 🤖 | overfit |
| 3.3 | Judge against om25_alt differentiation bar | 🤖 | — |
| 3.4 | 👤 checkpoint: portfolio-lineup decision | 👤 | product |

## Phase 4 — Close-out

| # | Task | Owner | Risk |
|---|---|---|---|
| 4.1 | RESULTS.md: decision, by-products, verification log | 🤖 | — |
| 4.2 | Failed branches → `docs/failed_experiments.md` | 🤖 | — |
| 4.3 | Optional: crowding-gauge productisation proposal for insight engine (TDD-scoped, separate approval) | 🤖 | scope-creep |
| 4.4 | 👤 checkpoint: merge/archive decision | 👤 | — |
