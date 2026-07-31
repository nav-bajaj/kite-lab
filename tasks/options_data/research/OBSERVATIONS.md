# Daily observations log — options program

> One entry per session, written after the EOD analysis. The daily
> report (auto, on the worker volume) holds the numbers; THIS log holds
> the interpretation — what the day looked like, what the regime did,
> what a strategist should remember. After 1-2 months this is the raw
> material strategies are built from. Keep entries honest: mark
> hypotheses as hypotheses, count the sample.

**Entry template**

    ## YYYY-MM-DD (day N) — <one-line day label>
    - Tape: gap/range/close, spot path shape
    - Regime: gamma read (concentration path), OI migration story
    - Vol: ATM IV path, straddle pricing, IV-slide context
    - Paper straddle: final / MAE / underwater; what a live trader felt
    - Depth/friction: anything off-baseline
    - Engine: anomalies, widens, data quality
    - Observations & hypotheses: numbered, with sample-size caveats

---

## 2026-07-28 (day 1) — expiry pin day, the archetype

- Tape: flat open, oscillated ±30 pts around 24000 all day, closed
  23,976 — 3.7 pts from max pain. Range compressed as the day aged.
- Regime: the pin was BUILT intraday — 24000 OI tripled (14.6M ->
  ~50M) while wings stayed flat; gamma concentration climbed 36% ->
  44% -> 57% into the close, max-gamma strike tracking the pin
  (24000 -> 23950 as spot drifted late). Total gamma ~10x a normal
  day (₹4.6-8.0 lakh cr/1%).
- Vol: expiry-day premium visible (ATM IV 14.6/16.8% at 10:00),
  crushing through the day as the pin held.
- Paper straddle: +13.2 (credit 88.3) | MAE **-19.1 at 10:07** |
  underwater 50 min, **last underwater minute 15:11** — nearly ALL
  profit arrived in the final 4 minutes as the pin crushed premium.
  A price-only trader bails at 15:11; the concentration number
  (57%, still rising) said hold. Founder framework case study #1.
- Depth/friction: absolute spreads flat all day but relative cost
  exploded 0.30% -> 1.84% of premium into the close (premium collapse,
  not book widening). Books thinned violently after ~15:20.
- Engine: first full production session; 2.24M ticks, 0 reconnects.
- Observations:
  1. Pin formation is OBSERVABLE live (ATM OI build rate + gamma
     concentration slope). (n=1 expiry)
  2. Expiry-day short-straddle P&L is back-loaded; MAE tolerance must
     survive the morning. (n=1)
  3. Never transact near-ATM options after ~15:15 on expiry day.

## 2026-07-29 (day 2) — gap + trend day, the opposite regime

- Tape: +155-pt gap up over the morning anchor, rallied to 24,225,
  closed 24,241 (+253). The trend's damage was ENTIRELY in the gap —
  post-09:20 the day chopped ±80 pts.
- Regime: textbook covering-fuel — call OI at overrun strikes drained
  to 55-69% of morning base while the next rung up built to 125%;
  gamma DIFFUSE all day (~20-21% concentration), max-gamma loosely
  following spot. OI-drain signal fired 12:49.
- Vol: post-gap IV crush (ATM ~10.2-11.4% after the open).
- Paper straddle: +7.8 (credit 272.7) | MAE -11.6 at 09:40 |
  underwater 86 scattered minutes. Roll rule never triggered — entry
  AFTER the gap avoided the trend entirely. Weakest day of the four,
  but positive: theta beat chop.
- Engine: expiry rollover fully automatic; widen #1 fired on the FIRST
  spot tick of the session (09:15:04); 107 contracts by close.
- Observations:
  4. Gap risk is the short straddle's real enemy this week, not
     intraday trend — intraday entries dodge overnight moves but a
     held-overnight position wouldn't. (n=1 gap day)
  5. Day-1's ITM-put imbalance cluster did NOT replicate (killed).
  6. OI migration cleanly separates trend from pin regimes. (n=2)

## 2026-07-30 (day 3) — quiet range-drift, call-covering undertone

- Tape: flat open, drift up, close 24,296.5 (+0.23%), range 153.
- Regime: DIFFUSE (17-20%), max-gamma static-ish at 24200; call OI
  drained across the traded zone (24200 CE -35%) with 24500 building
  +23% — covering-fuel-lite on a quiet day, and the day again closed
  near highs.
- Vol: IV slide continued 10.31% -> 9.62%; straddle 0.91% to expiry.
- Paper straddle: +16.2 (credit ~239) | MAE -13.3 at 12:33 |
  underwater only 9 min — the cleanest theta day.
- Depth/friction: friction baseline confirmed (0.23-0.25% of premium,
  flat all day; normal-day profile).
- Engine: first live-source bars day; EOD auto-Greeks hook's first
  natural run (32,994 rows, 5s after close).
- Observations:
  7. "Call OI drains in the traded zone -> close near highs" now 2/2.
  8. Friction has two regimes (expiry decay-driven vs normal flat) —
     execution timing only matters on expiry days. (n=3)

## 2026-07-31 (day 4) — second gap-up drift; call capitulation everywhere

- Tape: +81 gap (widen caught it on the first tick), high 24,429,
  close 24,366.8 (+0.29%), range 130.
- Regime: DIFFUSE (15-17%), max-gamma MIGRATED 24300 -> 24400 with
  spot; the loudest covering signature yet — call OI -27%..-70% across
  the entire ladder (24350 CE -70%), puts near-flat. 3/3 on
  "call-drain -> strong close."
- Vol: five-day slide extended: 9.32% -> 8.41% intraday; Tuesday-expiry
  straddle priced just 0.69% (168.7 pts) with a WEEKEND inside it.
- Paper straddle: +18.4 (credit 195.2) | MAE -12.2 at 09:35 (gap
  digestion) | underwater 55 shallow minutes. Best absolute day — but
  see hypothesis 10.
- Engine: first fully-automatic EOD analytics chain (ledger + gamma
  rows + report, 17s after close); first real tick archival (Jul-28
  raw 230MB -> 148MB tar.gz, pruned).
- Observations:
  9. MAE band across 4 sessions: -11..-19 pts, all early-or-midday;
     final P&L always positive and mostly later-loaded. Too early for
     thresholds, but the band is tight so far. (n=4)
  10. RISK/REWARD IS DETERIORATING while results improve: credits
      shrank 273 -> 168 pts as IV slid 10.3% -> 8.4%; straddle vega
      ~20 pts/vol-pt means a mere reversion to Monday's IV costs ~39
      pts against a 168-pt credit; the week's own gaps (+81, +155)
      approach the whole remaining cushion. Four wins were earned in
      fat-premium conditions that no longer exist. The untested loser
      lives in exactly the current conditions.
  11. Diffuse-day strategy question (founder, 07-31): on covering-fuel
      drift days, is a short straddle the right structure at all? A
      regime-matched alternative — short PUT spread (theta + drift
      alignment + defined risk) or re-centering the short strike to
      follow max-gamma migration — would have captured the same days
      with less tail. HYPOTHESIS ONLY (n=3 diffuse days, all up-drift;
      we have zero diffuse-day DOWN moves to test the other side).
      The strategy-spec engine should paper-run straddle vs put-spread
      vs iron-fly side by side, regime-tagged.
  12. For Tuesday's expiry at low IV: iron fly (wings are cheapest at
      IV lows) converts open-ended gap risk into fixed risk while
      keeping pin theta — the natural low-IV expiry adaptation to
      paper-test alongside the straddle.

---

*Next entry: 2026-08-03 (Mon — 08-01/02 are the weekend). Aug-04 expiry (Tue) is the week's key
session: pin-signature out-of-sample test #2, first completed
implied-vs-realized ledger verdict, second expiry MAE path.*
