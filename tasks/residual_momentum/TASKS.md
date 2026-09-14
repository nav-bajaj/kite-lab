# Tasks — residual momentum

Gates inherited from `tasks/mm_rebuild/TASKS.md` §0 (founder-signed
2026-09-10). The operative bar for a score swap is the standing quarterly
challenger protocol: **> 0.10 Sharpe** over the locked rules on the §17 grid,
trailing ten years. G7 (turnover reported; turnover-blind winners flagged)
is live throughout.

## §0 — eligibility diagnostic, before any backtest 🤖

Tests the founder's premise — that a 36-month history requirement would
"miss out on" the mid-cap growth names Nifty 250 keeps admitting — instead
of assuming it in either direction.

At each monthly rebalance, 2016-01-01 to today, over point-in-time Nifty 250
membership:

- [x] a. DONE 2026-09-11: RM-24 drops 7.8 of 246.7 scoreable (3.2%), RM-36 drops 14.8 (6.0%).
- [x] b. DONE 2026-09-11: RM-24 drops 1.64 buffer names / 1.00 book names per rebalance;
      RM-36 drops 3.21 / 2.08, zero at only 13% of rebalances, median excluded rank 17.
      The requirement bites in the middle of the book, not at the edge.
- [x] c. DONE 2026-09-11: **not confirmed.** Mean fwd-12m excess +9.55 pp (RM-36) is an
      overlap artifact — 129 monthly rebalances give ~10 independent 12-month windows;
      de-overlapped the edge is +0.96 pp, positive 4/10, and RM-24's goes to −2.68 pp.
      Carried by ATGL and ADANIGREEN in one 2020-22 episode. fwd-1m sign is unstable.
- [x] d. DONE 2026-09-11: attrition peaks 2018-2022 (5-7 buffer names/month under RM-36),
      mild at both ends of the sample — tracks the reconstitution and IPO calendar.

Reports to `report/`. No strategy decision rides on §0; it sizes the prize
and decides whether RM-24/RM-36 are worth running at all.

**Outcome (`report/S0_FINDINGS.md`)**: the eligibility cost is real and
structural (~8% of the book under RM-36); the forward-return cost is not
demonstrable. So RM-12's advantage is that it costs nothing, not that it
catches winners the others miss. §2 bar is therefore asymmetric — RM-12 need
only match on score quality; RM-24/RM-36 must beat it by enough to earn the
distortion they impose.

## §1 — build the scores 🤖 — DONE 2026-09-11, `report/S1_FINDINGS.md`
- [x] a. NIFTY 100 market factor + leave-one-out sector factor, built from
      point-in-time members only. `lib/residual.py`.
- [x] b. RM-12 built. Scores 246.7 names/rebalance — **identical to MM**, so the
      zero-eligibility-cost claim is confirmed rather than argued.
- [x] c. RM-24 (240.9) and RM-36 (234.3) built.
- [x] d. **RM-12 is clean** (tell +0.259, no negative pinning). PLAN.md's ratio
      argument confirmed monotonically: RM-24 at 50% formation/estimation shows
      real contamination (−0.168), RM-36 at 33% (the paper's ratio) much less
      (−0.083). Treat RM-24 as a compromised arm in §2, not a clean control.
- [x] e. Unplanned: RM-12's +0.259 tell is 6x M12/MM's +0.04 — it tilts toward
      names that rose in the *skipped* month, partly defeating the skip. Not
      degeneracy (wrong sign) but an adverse short-term-reversal exposure MM
      does not carry. Carried into §2 as a live question; skip=42 is the
      sensitivity if it bites.
- [x] f. Also learned: M12 and MM rank near-identically (0.979), so MM's edge
      over plain momentum is not in the ranking. RM-12 is a tilt on momentum
      (0.85); RM-24/RM-36 are genuinely different signals (0.55-0.66).

## §2 — head-to-head 🤖 — DONE 2026-09-11, `report/S2_FINDINGS.md`
- [x] a. All five arms through §22's adopted cell verbatim, `lib/phase2.py`.
      **MM control reproduces its registry number exactly (25.2% / 1.15 / −27%)**,
      so the comparison is valid.
- [x] b. **FAILED.** Static 2016-26: M12 22.8%/0.91/−34%, MM 25.2%/1.15/−27%,
      RM-12 22.1%/1.00/−31%, RM-24 17.3%/0.77/−30%, RM-36 16.9%/0.72/−32%.
      Best residual arm is −0.15 Sharpe against a +0.10 bar. MM wins every
      sub-window. **No arm improves MM's −27% drawdown**, which was the whole
      motivation.
- [x] c. Not run — §2b failed by a margin no process-grid pass would close.
- [x] d. Turnover (G7): RM-12 **2.00x vs MM 2.39x**, a 16% cut that holds at
      every skip. RM-24 3.95x and RM-36 3.19x are far above the standing book.
      The §1 worry that residual ranking would be noisier is refuted for the
      alpha construction and confirmed for the paper-faithful ones.
- [x] e. Pre-registered §1 skip sensitivity: **false alarm.** RM-12 is flat
      from skip 21 to 42 (1.00 → 1.01); the +0.259 tell cost nothing. MM at its
      locked skip=21 beats every cell of the skip grid.
- [x] f. The paper's crash claim does reproduce, but only on RM-24 (skew −0.42
      vs MM −0.84, kurt 5.6 vs 9.6) — and RM-24 pays 7.9 points of CAGR for it.
      The construction that fixes the tail is the one that costs the most
      return; the one that preserves return does not fix the tail.

## §3 — interactions 🤖👤 — NOT RUN, gated on §2 clearing
- [ ] a. Relaxed sector cap on the residual score — two devices, one job.
- [ ] b. Regime gate off.

## §4 — decision 👤
- [ ] Founder call. **Recommendation: close, no change to MECHANICS.md.** The
      honest limit is that market+sector is not FF3 — these results cannot
      separate "does not work here" from "needs the value factor we cannot
      build". Retry is cheap from `lib/residual.py` if fundamentals are ever
      sourced for the PEAD thread.
