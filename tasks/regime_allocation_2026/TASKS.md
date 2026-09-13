# Tasks

Owners: 👤 founder · 🤖 agent.

## §0 — pre-committed pass criteria — SIGNED 👤 2026-09-12

Set before any run. A candidate regime rule **passes** only if every row holds
on the **walk-forward** result (§3), not on IS/OOS.

| # | Criterion | Value |
|---|---|---|
| G1 | Walk-forward Sharpe vs always-on over the same 2014-2026 span | ≥ +0.15 |
| G2 | Walk-forward Sharpe vs the rule's own exposure-matched control | ≥ +0.15 |
| G3 | Walk-forward Sharpe vs the same rule's static-OOS Sharpe | within 0.15 |
| G4 | Walk-forward max drawdown, marked to market daily | ≤ 35% |
| G5 | Regime-layer parameter count, all-in | ≤ 4 |
| G6 | Sign of the effect (rule beats always-on) holds in the two alternate splits of §4 | both |
| G7 | Best cell exceeds the Gumbel expected maximum of the trials run | yes |

Turnover, time in cash, and whipsaw count (allocation changes per year) are
reported for every candidate; no gate, but a rule that wins with >12
allocation changes a year is flagged as impractical.

## §1 — harness 🤖

Extend `tasks/trend_screen_2026/lib/run_isos.py` into
`tasks/regime_allocation_2026/lib/harness.py`. One function evaluates one
candidate and returns one row. Nothing else is built until this exists and
reproduces §8's numbers.

- [ ] `regime_series(signal, window, level_cut) -> pd.Series[date -> weight]`
      for the shapes in PLAN §D. Signals A1-A5 computed from
      `breadth.parquet` (A1, A3), `features_t500_ranked.parquet` (A2), and a
      one-off extension of `breadth.symbol_flags` for A4.
- [ ] `evaluate(rule, span) -> dict` — runs `book()` on the tape with
      `wt = weight at entry_date`, plus the exposure-matched control
      (constant `wt = mean weight`), 3 seeds, returns CAGR / maxDD / Sharpe /
      exposure / taken / allocation-changes-per-year for both.
- [ ] `walk_forward(rule_family, params_grid)` — trailing 8-year fit, apply
      forward one year, chain 2014-2026; the fit picks the grid cell with the
      best trailing Sharpe. Returns the chained equity and per-year picks.
- [ ] Forced-exit variant (PLAN §E2): `build_book` gains an optional
      `force_exit: pd.Series[date -> bool]`; when true, every open position is
      closed at that day's close. Keep it additive — absent means unchanged.
- [ ] **Smoke test:** the founder's rule on `pct_above_200 / 63 / median /
      four-bucket {1,1,0.5,0}` must reproduce §8's OOS **21.6% / 36.7% / 0.92**
      to within 0.3pp / 0.5pp / 0.02. Do not proceed until it does.

## §2 — the candidate grid, IS/OOS 🤖

One table, every candidate, IS 2006-2015 and OOS 2016-2026 side by side,
with the exposure-matched control beside each. Count the trials.

- [ ] Signals A1-A5 × windows B{21,42,63,126} × shapes D1-D3, level cut
      fixed at median (C) — that is ≤ 60 candidates. D4 hysteresis is applied
      only to the top 3 afterwards, N ∈ {5, 10, 21}.
- [ ] For D1 the TOPPING weight is **fixed at 0.5** — §8 showed it is not
      determinable, and sweeping it here would be fitting noise.
- [ ] Report: grid median Sharpe, best cell, Gumbel expected max, and how many
      candidates beat always-on OOS. The *family* result is the finding; the
      best cell is a selection artifact until §3.

## §3 — walk-forward, the verdict 🤖

- [ ] Top 5 candidates from §2 by OOS Sharpe *minus* their exposure control,
      each walked forward 2014-2026.
- [ ] Always-on and the exposure control walked over the same span.
- [ ] Per-year table: which cell the trailing fit chose, and what it earned.
      A rule whose chosen cell changes most years is unstable; say so.
- [ ] **Gate G1-G7.** Report pass/fail per criterion per candidate. Expect
      most to fail G3 or G4; that is a result.

## §4 — robustness 🤖

- [ ] Alternate splits: IS 2006-2012 / OOS 2013-2026, and IS 2006-2018 /
      OOS 2019-2026. Sign of the effect for the §3 survivors.
- [ ] Where the rule acts (PLAN §E): entry-only vs entry+forced-exit vs
      entry+rebalance-down, for the best §3 survivor only.
- [ ] Slot count {15, 25, 35} for the best survivor.
- [ ] Cross-signal (PLAN §F): the best survivor applied to the breakout tape.
      Same harness, tape swapped. A regime layer that helps one signal and
      not the other is fit to the first.

## §5 — cost of the rule 🤖

- [ ] For the best survivor: time in cash, turnover vs always-on, allocation
      changes per year, and the ten worst whipsaws (regime flipped and flipped
      back within 21 sessions) with what each cost.
- [ ] Tax drag estimate at STCG 20% / LTCG 12.5% on realised gains vs
      always-on — a regime rule shortens holds and that has a price.

## §6 — write-up 🤖 then 👤

- [ ] RESULTS.md in the template in BRIEF.md. Verdict line first.
- [ ] If any candidate passes G1-G7: its full specification, frozen, with
      the parameter count shown, and the sentence "this rule's weights would
      have been chosen in 2015 as follows" filled in honestly.
- [ ] If none passes: the closest miss, which gate it failed, and by how much.
- [ ] Follow-ups list — anything that wanted a new signal, exit or universe.
