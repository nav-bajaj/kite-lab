# minimum_capital_2026

Research + product sizing, 2026-09-06. **No production code was changed.**
Everything here is analysis plus two decisions awaiting the founder.

Start with **`STATE.md`**.

| file | what it is |
|---|---|
| `STATE.md` | **Read first.** Where it landed, what is decided, what is open, how to re-run. |
| `PLAN.md` | Why the work started, how the scope grew, and where the cap is injected per strategy (the design decision that makes the study valid). |
| `RESULTS.md` | Phase 1 — suggested capital and SIP. The client-facing answer. |
| `RESULTS_PRICE_CAP.md` | Phase 2 — the Rs 4,000 cap across OM25 v3, L6 v2, COMBO. Part A is OM25, Part B is L6 + COMBO. |
| `TASKS.md` | Item-by-item status, including everything still open and what was deliberately not done. |
| `runs/` | All script outputs, with an index. |

## The two-line version

Suggest **Rs 5L minimum / Rs 10L recommended**, with a **Rs 10k floor /
Rs 25k recommended monthly SIP**. Rs 1-5L is structurally broken: a 1/25
position at Rs 1L is Rs 4,000 and the books hold Rs 34,000 shares.

A **Rs 4,000 per-share entry cap** would cut that minimum to ~Rs 2L. It
is free for COMBO (+0.18pp CAGR) and OM25 (+0.72pp) but costs L6 1.35pp
of CAGR and 4pp of drawdown. Adoption is an open decision.

## One thing to carry into any future universe-restriction study

The cap sweep on its own is uninterpretable — it is non-monotonic, and
taking its best arm at face value would have selected Rs 2,000 and
shipped an unintended small-cap bet. What made it readable was a
**random-exclusion placebo**: exclude the same number of names at random,
many seeds, and compare. That separates "excluding names costs
opportunity" (it does — 1.2 to 3.4pp depending on the strategy) from
"excluding *expensive* names costs extra" (it does not). Reuse the
control.
