# Product

<!-- impeccable:product-schema 1 -->

<!--
Provenance: written unattended on branch design_reset at the founder's
explicit request ("without significant input from my side"). Facts are
drawn from docs/portfolios.md, CLAUDE.md, ~/marketworks-design/PRODUCT.md
and DESIGN.md, and tasks/design_studies/. Items marked [INFERRED] were
not confirmed by the founder in this session.
-->

## Platform

web

## Stack

delegated: single self-contained static HTML page for this experiment
(`tasks/design_reset/home.html`) — the founder asked for a viewable
one-page mock, not a production integration. Production remains
Next.js (`kite-dashboard`).

## Users

Primary: self-directed Indian retail investors, 22–45 ("Karan"
persona, `~/finance-content-os/brand/personas/karan.md`). Numerate,
time-poor, meet the brand on a phone via Instagram or the web — not at
a terminal. They can already buy stocks (Zerodha/Groww generation);
what they lack is a disciplined system and the temperament to follow
one.

Secondary: the founder operating the content factory; private-beta
clients reading /library and /insights.

## Product Purpose

Marketworks runs rules-based momentum portfolios for Indian equities.
A daily production pipeline (16:30 IST, after close) fetches NSE data,
rebuilds signals, and publishes portfolio holdings and rebalance
instructions to subscribers. The product replaces stock-picking with a
tested, mechanical process the subscriber executes in minutes a week.

Success for this surface: a first-time visitor understands the
mechanism (momentum, rules, evidence), believes the discipline is
real, and requests beta access.

## Positioning

The claim a neighboring product cannot truthfully copy: **the
strategies are validated out-of-sample and published with their full
risk history — drawdowns, slippage, and the rejected experiments
included.** Finfluencers sell conviction; brokers sell access;
Marketworks sells a process with an evidence trail (tuned 2009–2016,
validated 2017–2026, slippage-adjusted at 20 bps).

## Operating Context

- Subscriber ritual: a weekly/bi-weekly rebalance note; the daily
  pipeline runs unattended. Holdings and signals visible in the
  dashboard.
- Private beta with a sign-up allowlist; marketing site is public.
- India-market vocabulary: NSE 500, Nifty, DMA, drawdown, CAGR, SIP
  generation. Prices in INR.

## Capabilities and Constraints

- 4 production portfolios (docs/portfolios.md): Quality Momentum
  (OM25 v3, Nifty 250), Trend Leaders (TL25 v3, NSE 500), Core
  Momentum (L6 v2, NSE 500), Defensive Blend (COMBO, NSE 500).
- Real performance evidence (see Evidence on Hand). All figures are
  backtests net of 0.2% slippage; L6 v2 is IS-tuned, OM25/TL25 are
  OOS-validated.
- HARD RULE (standing founder rule): no fabricated numbers anywhere.
  Every figure on a surface traces to the repo or is visibly labeled
  a placeholder.
- Regulatory status is UNSTATED in the repo. [INFERRED constraint]
  Do not claim SEBI registration, "advisory", or assured returns;
  standard market-risk disclaimers are honest and required in spirit.
- No customer counts, AUM, or testimonials exist. Do not invent them.

## Brand Commitments

- Name: **Marketworks**, wordmark historically lowercase
  "marketworks". Domain marketworks.in.
- Voice (confirmed across content system): calm, sharp, editorial —
  probabilistic, never predictive; teaches the mechanism rather than
  hyping outcomes. Founder's rule: "probabilistic-not-predictive."
- Standing anti-references (from the brand's own record):
  finfluencer panic-thumbnails; purple-gradient fintech-SaaS look;
  dense research-report PDF grids; stock-photo lifestyle imagery.
- The incumbent visual worlds (mist/lichen editorial system in
  ~/marketworks-design; Clay-vivid study on design_studies_clay) are
  EVIDENCE, not authority, for this branch: the founder asked for a
  from-scratch identity. [Founder request, this session]

## Evidence on Hand

Real, citable figures (docs/portfolios.md):

- OM25 v3 "Quality Momentum" — OOS 2017–2026 (9.3y): CAGR 44.78%,
  Sharpe 1.86, MaxDD −36.6%. Nifty 250, bi-weekly + weekly checks.
- TL25 v3 "Trend Leaders" — OOS 2017–2026: CAGR 34.86%, Sharpe 1.53,
  MaxDD −39.0%. NSE 500, trend-quality 3-component score.
- L6 v2 "Core Momentum" — 2020-07→2026-02 (IS): CAGR 59.4%, Sharpe
  1.92, MaxDD −30.0%, turnover 123%.
- Defensive Blend — 50/50 L6+OM25 composite, 50% allocation cut in
  bear regime (NIFTY 100 vs 100-DMA, 3-day confirmation).
- Process facts: daily pipeline at 16:30 IST; 20 bps slippage
  modeled; universes NSE 500 / Nifty 250; drawdown stops at 20%;
  equal-weight 1/N sizing capped 7.5%; a documented list of tested-
  and-rejected ideas (vol targeting, longer lookbacks, volume
  weighting).

Absences future work must not fabricate: testimonials, AUM, client
counts, press, regulatory registrations, live-track record separate
from backtests.

## Product Principles

1. **Evidence over persuasion.** The strongest marketing asset is the
   real research trail — show it, including the losses.
2. **Discipline is the product.** Rules, cadence, and risk controls
   matter more than any single return figure.
3. **Numbers tell stories.** Never a stat without its context (period,
   universe, methodology, slippage).
4. **Probabilistic, never predictive.** No forecasts, no assurance,
   no urgency mechanics.
5. **Respect the reader's intelligence.** The 22–45 Indian audience is
   numerate; explain mechanisms, don't dumb down.

## Accessibility & Inclusion

Body text ≥4.5:1 contrast; tabular figures for numeric columns;
`prefers-reduced-motion` honored. Latin-only for now (Devanagari
deferred — prior brand decision).
