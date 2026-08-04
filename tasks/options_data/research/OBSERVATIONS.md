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


## 2026-08-03 (day 5) — special 15:40 session; gap+trend into expiry-eve; TWO landmark data points

- Tape: +152 gap up (3rd consecutive up-gap), trend to ~24,580 by 10:13,
  midday fade to VWAP, afternoon recovery; REAL close ~24,598
  (chain-implied). Day change ~+230 pts. Special F&O session ran to
  15:40; capture followed exactly (override worked, removed after).
- DATA FLAG: index feed printed a PHANTOM +200 jump to 24774.30 at
  ~15:29 and froze there through 15:40 (equity/index calc ends 15:30;
  only F&O extended). Verified phantom via parity forward: the chain
  priced the underlying at 24,574-24,602 throughout. Auto-report's
  high/close/day-change for 08-03 are contaminated; Greeks are CLEAN
  (parity forward, not spot). Widen #3 was phantom-triggered — harmless
  by design (widen-only). Follow-up queued: report should cross-check
  spot vs parity forward and flag divergence.
- Regime: DIFFUSE (20->25->25%) — NO pin formed on expiry-eve; the
  midday MIXED reading (founder watched it live) was transient, resolved
  back to diffuse as the afternoon leg ran. BUT: spot ended parked
  almost exactly ON the static max-gamma strike 24600 — tomorrow opens
  with a ready-made pin candidate and spot already at the magnet.
- Vol: THE WEEKEND VEGA WARNING LANDED. IV snapped 8.41% (Fri) ->
  11.52% (Mon open) — +3.1 vol pts. Counterfactual computed from real
  bars: Friday's 168.7-pt straddle held over the weekend = -61.2 pts
  (-36% of credit) at Monday 09:20, from gap + vega together. First
  concrete loss instance in the ledger's counterfactual column;
  hypothesis #10 confirmed in one session. Intraday-only entry dodged
  it entirely.
- Paper straddle: +10.8 (credit 131.9 @ 24550) | MAE only -5.3 at 11:03
  | underwater 85 shallow min. Post-gap entry again neutralized the
  trend (5/5 profitable, but see the counterfactual above for what the
  ledger does NOT measure: overnight risk).
- OI migration: covering-fuel 4/4 — near calls drained (24550 CE -60%)
  while 24850/24950 CE BUILT (+42/+54%); writers re-established two
  rungs up. Puts drained too (rally).
- Engine: biggest day (2.50M ticks, 39,437 bars, 0 errors); 3 widens;
  triple archival (Jul 29/30/31) after the weekend; EOD chain ran at
  15:40 exactly.
- Observations:
  13. Overnight/weekend carry is the short straddle's dominant risk, not
      intraday moves: first measured instance -61.2 pts vs worst
      intraday MAE -19.1 across 5 sessions. Any live strategy is
      intraday-only until the ledger says otherwise. (n=1 carry event)
  14. Phantom index prints are a real failure mode around special
      sessions; parity forward is the authoritative underlying for
      analytics AND the sanity check for spot. (n=1)
  15. Expiry-eve did NOT pin this time (trend day instead) — pin
      formation is not a calendar effect; it needs the OI/gamma
      convergence. Tomorrow tests whether it forms ON expiry day with
      spot starting at max-gamma. (pin sample still n=1)

### CORRECTION (2026-08-03 evening, founder-verified vs NSE)

The 24,774.30 print is the OFFICIAL NSE close — NOT a phantom/bad tick.
My same-evening diagnosis was wrong about the cause. What stands, and
now matters MORE: the derivatives complex (options chain, parity
forward) priced the underlying at ~24,574-24,602 through the entire
15:20-15:40 window — a ~175-200 pt DISLOCATION between the official
index close and where F&O actually traded, on day one of the new NSE
timings (F&O to 15:40, till further notice; the whole market was
confused). Re-labeled findings:

- This was a MARKET-STRUCTURE EVENT, not a data error. The engine
  recorded both sides of the dislocation faithfully — that recording
  may be unique data.
- The queued "phantom guard" is reframed as a spot-vs-parity
  DIVERGENCE MONITOR: divergence can be a bad tick OR a real
  dislocation; either way it must be surfaced, not auto-discarded.
- Day change +407.5 to the official close is correct as reported;
  note the official close level never traded intraday (traded high
  ~24,580 before the closing computation).
- EXPIRY IMPLICATION (tomorrow!): settlement anchors to the official
  close mechanism. If tomorrow's official close can again print
  ~200 pts from where the chain trades at 15:30-15:40, expiry
  settlement can surprise anyone positioned off the tape. Watch the
  final-window basis explicitly; hypothesis 16 below.

  16. Under the new timings, official-close vs derivatives-traded-level
      divergence is a live risk transferred INTO expiry settlement.
      Measure the 15:30-15:40 chain-vs-close basis daily. (n=1)

## 2026-08-04 (day 6) — EXPIRY 2: first LOSS, settlement mechanics decoded, pin thesis humbled

- Tape: first DOWN-gap (-141), rally to 24,648, hard sell to 24,428 low
  (~13:57), then a ~150-pt MELT-UP into the close: 24,463 at 15:26 ->
  24,614.9 official close by 15:28. Day -0.64%, range 220 pts,
  two-sided. Widens BOTH directions (10:56 up, 13:15 down).
- THE FIRST LOSS (and the most valuable ledger row): sold 24600
  straddle 09:20 for just 93.0 pts (expiry thin credit, as hyp. 10
  warned) -> final -55.2 (-59% of credit), MAE -78.3 at 13:57 (4x the
  previous worst), underwater 213/356 minutes. Six-session ledger: five
  wins +66.4, one loss -55.2, net +11.2 — one bad day nearly erased
  five good ones. The short-vol distribution, measured.
- DISCIPLINE CUT BOTH WAYS: the 15:15 exit locked -55.2; holding to
  ~15:28 would have finished ~+78 as the melt-up carried spot back to
  the strike (straddle -> ~15 pts intrinsic). Jul-28 the late hold paid
  WITHIN the window; today it paid AFTER it. n=2 expiries, opposite
  verdicts on late exits — do not touch the exit rule on this evidence;
  gamma-lottery in the final minutes runs both ways.
- SETTLEMENT MECHANICS DECODED (the cutoff experiment): expiring 24500
  CE pinned to ~114.7 = EXACT intrinsic vs the 24,614.9 official close
  from 15:28 through 15:40; PE bled to 0.05. Options converged to
  intrinsic-vs-official-close BEFORE 15:30 and the extended window
  traded at settlement values. EXPIRY_CUTOFF 15:30 empirically
  CONFIRMED — greeks assumption stands.
- CLOSE-PRINT STRUCTURE (hyp. 16, 2nd observation): the official close
  again printed far above the late tape (+150 vs 15:26), but TODAY the
  chain converged to it (parity fwd 24,561@15:26 -> 24,615@15:28,
  matching official). New-timings close dynamics are real and
  recurring; on expiry, settlement forces derivatives into agreement.
  Yesterday's 200-pt divergence remains the non-expiry variant. The
  spot-vs-parity divergence monitor stays essential (still queued).
- PIN TEST #2: NO pin. Concentration 32% -> 28% -> 22% (fell all day);
  max-gamma migrated 24600 -> 24500 chasing the sell-off. Two expiries:
  one textbook pin, one two-sided breaker. Pin formation needs its
  OI-convergence conditions, not the calendar. (pin sample n=1/2)
- Vol: regime shift — ATM IV 17.8% open (gap fear) -> 24% midday panic
  (the 103% 15:15 print is T->0 arithmetic noise, not information).
  Last week's 8-10% world is gone.
- LEDGER VERDICT #1 (implied vs realized, 08-04 cycle): realized beat
  implied — Fri 15:15 implied 0.69% vs Fri->settle realized +1.02%;
  Wed implied 0.91% vs +1.35% realized to settle. The low-IV
  compression UNDER-priced the move; late-week sellers were
  undercompensated, and today collected the bill. First completed
  verdict row.
- Engine: biggest session (2.71M ticks, 40,096 bars, 0 errors), 3
  widens incl. first down-side widen, EOD chain 8s after the 15:40
  close.
- Observations:
  17. Expiry-day short premium at thin credit is the program's worst
      measured trade: credit 93, MAE -78.3. Any expiry-day short-vol
      rule must be regime-AND-credit conditioned. (n=2 expiries)
  18. Settlement basis = official close, established ~15:28-15:30;
      15:30-15:40 F&O trades at settlement values on expiry day.
      (n=1 extended expiry)
  19. Official close prints far from the late continuous tape under the
      new timings (2/2 days, +150 and +200). Anything marked or
      triggered off the 15:20-15:30 tape inherits this risk daily.

---

*Next entry: 2026-08-05 (Wed) — first session of the new expiry cycle (08-11) in the new vol regime; divergence monitor build queued.*
