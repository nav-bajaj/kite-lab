# Stage 3 — signed dealer gamma (GEX sign) — DEFERRED TO END OF CYCLE

> Scheduling: this is the **last** item of the current analytics/strategy
> track. Do it AFTER the outstanding operational + advisory items (GDrive
> offload, divergence monitor, day-plan generator, housekeeping) and once
> the day-type library is larger (it is the deepest, most assumption-laden
> piece and gains directly from more sessions to test the sign against).
> Filed now so the design is fixed before we build it, per the same
> discipline as NOTE_risk_thresholds.md.

## Why this exists

Everything the pipeline computes today is **unsigned** gamma
(`gamma_profile.py`): `gex_cr = gamma × OI × F² × 0.01`, summed positively
across all strikes → total gamma, max-gamma strike, concentration, and the
PIN-GRAVITY / MIXED / DIFFUSE regime label. Concentration tells us *where*
gamma sits, not *who is long or short it*. The daily report says so
explicitly ("measured — no dealer assumptions"). The strategy layer needs
the **sign** of the dealer/writer book, which is a separate, harder object.

## The core problem — and why we can't just port US GEX

The retail US model (SqueezeMetrics/SpotGamma) assumes **dealers long
calls, short puts** → net long gamma near the money → a pinning /
vol-suppressing force. That is an SPX overwriter world.

**NIFTY is structurally the opposite.** Retail are net *buyers* of cheap
OTM weeklies; prop desks / institutions are the *writers*. That makes the
writer complex **default net short gamma** — moves extend, not dampen. A
blind port of the CE-long/PE-short assumption would print the wrong sign on
most NIFTY days. So the standard formula is rejected as a starting point.

Indirect behavioural evidence already supports the short-gamma default: of
6 sessions logged, 5 were trend/diffuse/covering-fuel (max-gamma migrates
*chasing* spot — the short-gamma signature) and only 1 was a genuine
long-gamma pin (Jul-28: concentration 36→57%, spot magnetized, vol crushed,
realized ≪ implied). Pin needs OI *convergence*, not the calendar.

## The approach — sign it from our own tick data, not by assumption

We record raw ticks with `last_qty`, `total buy/sell qty`, and 5-level
depth (Parquet on the worker volume). That is enough to classify who
*initiated* each trade and sign OI changes empirically, which beats any
static assumption. Build order:

1. **Aggressor classification.** For each print, tick-rule / Lee-Ready:
   compare trade price to the prevailing mid (from the recorded 5-level
   book) → buyer-initiated vs seller-initiated. Validate the classifier on
   a day where the answer is obvious (expiry pin CE decay).
2. **Signed ΔOI per strike.** Combine aggressor direction with the OI
   delta per minute bar to infer whether *writers* added or covered at each
   strike/side. Net writer position sign per strike = the dealer-gamma sign
   contribution there.
3. **Signed dealer gamma.** `signed_gex_k = sign_k × gamma_k × OI_k × F²`,
   aggregated → a net dealer-gamma number (long/short) and a signed profile
   across strikes (the zero-gamma flip level, if one exists).
4. **Out-of-sample regime test.** Does the empirical sign match the
   behavioural label on all logged days? Pin day → net long; the four
   trend/diffuse days → net short. If it does, the sign is real signal; if
   it doesn't, the classifier or the OI-attribution is wrong. This is the
   pass/fail gate — no strategy hangs on it until it passes.

Everything ESTIMATED is labeled ESTIMATED in outputs (roadmap rule for
Stage 3).

## What it unblocks (but does not itself build)

The strategy layer's *structure selection*, conditioned on the sign:

- **Net long / pin** (high conc, spot at max-gamma wall, OI converging):
  sell realized-vs-implied — short straddle / iron-fly on the wall, fade
  toward it. Conditioned on **credit thickness** (Aug-04's −55.2 loss was a
  93-pt thin-credit expiry short — the ledger's worst trade).
- **Net short / trend** (diffuse, max-gamma migrating, covering-fuel OI
  drain): moves extend → naked short premium is wrong. Directional debit
  spread with the drift, short put-spread on covering-fuel up-drift (obs.
  hyp. 11), long gamma into gap+trend, or stand aside.

Standing constraints any structure inherits (already measured):
intraday-only (overnight/weekend carry is the dominant risk, −61.2
counterfactual); no near-ATM transactions after 15:15 on expiry; and the
new-timings official-close-vs-tape divergence (settlement risk).

## Deliverables

- `tasks/options_data/research/` probe: aggressor classifier + signed-ΔOI
  attribution + signed profile, run over all recorded sessions (research
  probe, NOT `scripts/` per conventions).
- Written RESULTS with the 6-session (by then more) out-of-sample sign test.
- IF it passes: promote to a Stage-3 `microstructure` function feeding the
  day-plan generator's structure-selection, with sign labeled ESTIMATED.

## Preconditions before starting

- Outstanding items ahead of it done (see TASKS.md ranked list).
- Larger day-type library — the sign test is only meaningful with a spread
  of regimes incl. an intraday runaway and a red day; accrues automatically.
- Founder principle holds throughout: probabilistic, state-conditioned,
  never price-predictive; framed diagnostically.
