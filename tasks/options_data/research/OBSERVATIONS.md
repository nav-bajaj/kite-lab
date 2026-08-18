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

## 2026-08-05 (day 7) — new-cycle open: the V-day that never paid; first NON-expiry loss; ledger goes negative

(Entry written 2026-08-07 from the stored bars/snapshots/ledger — the
journal missed two days; the engine did not.)

- Tape: +16 gap open 24,631, early high 24,662.6, midday slide to
  24,498.2 (~13:44), full V-recovery to an official close of 24,624.7
  (+0.04%). A flat close hiding a 164-pt round trip.
- Regime: DIFFUSE all day (concentration 18% -> 15%), max-gamma STATIC
  at 24600 through all three snapshots — it did not chase the sell-off
  (contrast 08-04, where it migrated with the move). OI: near-flat CEs,
  heavy PE drain at-and-above spot (24600 -33%, 24700 -48%, 24800
  -46%) — put-writer de-grossing into the new cycle, NOT the
  call-covering signature of the drift week. New pattern, unresolved
  direction on the day it appeared.
- Vol: the new regime held. ATM IV 10.16% (09:20) -> 11.68% into the
  midday sell (12:30) -> 10.60% (15:15) — IV rose while spot fell,
  proper two-sided vol behavior; last week's one-way slide is over.
  EOD straddle 274.4 pts = 1.11% to the 08-11 expiry.
- Paper straddle: FIRST NON-EXPIRY LOSS. -19.6 (credit 264.0 @ 24650)
  | MAE -72.3 at 13:44 — second-worst in the ledger, on a full credit
  | underwater 355/356 min, i.e. the ENTIRE hold. The V clawed marks
  back from -72 to -14.8 by the 15:15 exit; costs finished it -19.6.
  A flat-close day that still lost: entry 26 pts under what proved the
  high, then IV markup + path did the damage.
- **CUMULATIVE LEDGER TURNED NEGATIVE**: 8 sessions = six wins +70.2,
  two losses -74.8, net **-4.6**. It was +11.2 after six. Two adjacent
  red days erased five weeks of wins — the short-vol distribution,
  now measured on our own book.
- Divergence (retro-computed): the monitor's first flag. Close-window
  dislocation +69.0 pts vs the day's carry baseline at 15:39 (official
  close 24,624.7 vs parity forward 24,590.8). Spot printed ~100 above
  its 15:15 level into the close while the forward moved ~30 — the
  "melt-up" is largely the close print itself standing rich to where
  derivatives traded. Hyp. 16 series: ~200 -> 150 -> 69.
- Depth/friction: normal-day baseline (0.24-0.25% of premium, flat;
  imbalance +0.25).
- Engine: 2.11M ticks, 34,954 bars, 0 db errors, 1 widen (down-side —
  spot broke >=2 strikes below the 24650 anchor). Divergence monitor +
  day-plan generator MERGED this evening (19:49, post-close): today's
  divergence/day-plan numbers are faithful retro-computation from
  stored data, live in prod from tomorrow. The retro day-plan said
  DIRECTIONAL_DEBIT_SPREAD — its "no naked straddle" half was right
  (straddle lost), its drift half was not (day closed flat). Counts as
  backtest, not track record.
- Observations:
  20. Flat-close days can still lose a short straddle: V-shape = IV
      markup + all-day-underwater path. Final-print P&L is not the
      day's experience; the ledger's underwater column is. (n=1)
  21. PE-side de-grossing (put drain at/above spot, calls flat) is a
      distinct third OI signature after pin-build and call-covering;
      it resolved to neither trend nor pin on day one. (n=1)
  22. MAE -72.3 on a NON-expiry day breaks the "thin-credit expiry
      days are the danger" shortcut (hyp. 17): fat credit did not
      prevent a near-ledger-worst drawdown. Risk conditioning needs
      the regime, not the calendar or the credit alone. (n=8)

## 2026-08-06 (day 8) — tightest day on record; two-sided de-grossing; analytics chain fully live

- Tape: -17 gap open 24,607.8, high 24,676.8, low 24,606.0, close
  24,636.0 (+0.05%). Range 70.8 pts (0.29%) — the narrowest of all 8
  sessions; an inside drift day.
- Regime: DIFFUSE (16% -> 15%), max-gamma parked at 24600 again. OI:
  BOTH sides drained at the near strikes (24550 CE -42% / PE -23%;
  24450 CE -26% / PE -18%) while the wings BUILT (24750 CE +13%,
  24850 PE +17%) — writers stepping out of the middle ahead of the
  08-11 expiry. Two-sided near-strike drain + wing build on the
  tightest day yet: compression signature or routine pre-expiry
  re-positioning? Unresolved. (n=1)
- Vol: IV refused to fade with the quiet tape — 10.94% -> 11.75% ->
  10.86%; straddle 249.9 pts = 1.01% to expiry with a weekend inside.
  Day-plan IV percentile 75% (n=4 prior days): premium rich by this
  short history, on the quietest tape we've recorded.
- Paper straddle: +3.8 (credit 258.1 @ 24650) | MAE -28.2 at 11:30 |
  underwater 339 min, last at 15:02 — a winning day spent ~94% of the
  session underwater. On a 71-pt-range day this credit SHOULD have
  paid fat; it paid 3.8, because IV stayed bid all day. Theta barely
  outran the marks.
- Divergence: NO flag — the first new-timings session without a close
  dislocation (max -35.3 vs baseline at 15:23, -17.7 at the close).
  Series: ~200 -> 150 -> 69 -> none (3/4 flagged, magnitude decaying
  monotonically).
- Depth/friction: baseline (0.23-0.26%; imbalance +0.22).
- Engine: 2.12M ticks, 35,584 bars, 0 db errors, 0 reconnects, 1
  widen; FIRST fully-live run of the merged analytics chain — the EOD
  report now carries the divergence + morning day-plan sections in
  production. Advisory call #1 on the record: DEFINED_RISK_SHORT at
  24600 (diffuse + IV pctile 75 -> wings on). On the day, short
  premium was right and wings would have cost little — a sensible
  first call. (track record n=1)
- Observations:
  23. IV holding ~11% through a 0.29%-range day means the market is
      pricing gap/event risk, not intraday realized. Implied-vs-
      realized verdict #2 arrives at the 08-11 expiry (implied 1.01%
      with the weekend inside). (n=1)
  24. The close-print dislocation is NOT a structural constant: 3/4
      days, decaying 200 -> 150 -> 69 -> 0. Hypothesis: the market is
      adapting to the new close mechanics. The monitor stays either
      way — treat each close on its own evidence. (n=4)
  25. Underwater-minutes is becoming the honest risk metric: the last
      two sessions logged 355 and 339 underwater minutes for -19.6 and
      +3.8 final — vs a ledger median of 86. MAE alone misses the
      grind; any live-size rule must survive being wrong for six
      hours. (n=8)

## 2026-08-07 (day 9) — IV finally pays: best ledger day, back in the green

- Tape: -89 gap open 24,546.7 (the biggest gap of the program), fast
  bounce to a 24,629.8 high by mid-morning, low 24,522.9, close
  24,570.7 (-0.27%). Range 106.9 pts (0.44%) — the gap did the moving;
  the session after it was orbit.
- Regime: DIFFUSE (21% -> 21% -> 20%), max-gamma parked at 24600 for
  the THIRD straight session. Total gamma ₹110k -> 130k -> 120k cr/1%.
- OI: the PE drain went program-wide — puts down at every reported
  strike (24550 -52%, 24650 -66%, 24750 -69%) on a gap-DOWN day, while
  24550 CE built +36% and other CEs sat mixed. Put writers who
  de-grossed into the new cycle (day 7) kept leaving through the
  weekend; the one big build is calls just under spot — overhead
  writing into weakness. Third variation of the de-grossing signature
  in three sessions; still unresolved as a directional tell.
- Vol: gap fear priced then crushed. ATM IV 12.10% (09:20, the richest
  morning of the program) -> 12.04% (12:30) -> 10.59% (15:15) — a
  1.5-vol EOD crush into the weekend. EOD straddle 219.2 pts = 0.89%
  to the 08-11 (Monday) expiry, compressed from 1.01% with the weekend
  now inside it.
- Paper straddle: **+38.0 — BEST DAY IN THE LEDGER** (prior best
  +18.4). Credit 256.1 @ 24600 | MAE only -12.2 at 09:55 | underwater
  110 min, last at 11:23. Sold the richest morning IV of the program
  and realized 0.44%: the whole short-vol thesis in one row.
- **CUMULATIVE LEDGER BACK IN THE GREEN**: 9 sessions = seven wins
  +108.1, two losses -74.8, net **+33.4**. The -4.6 trough lasted
  exactly two sessions; one rich-premium quiet day repaired it.
- Divergence: second consecutive clean close — and the sign FLIPPED.
  Max dislocation -36.5 pts at 15:16 (spot 24,557.0 under forward
  24,615.2), close window -12.3 vs baseline; nothing near the 40-pt
  band. Series: ~200 -> 150 -> 69 -> 0 -> 0.
- Day-plan advisory #2 on the record: DEFINED_RISK_SHORT at 24600
  (diffuse, conc 21%, IV pctile 80% n=5, credit 267). Short premium
  was right — the naked version made +38 and wings would have cost a
  few points of it. Two calls, two sensible. (track record n=2)
- Depth/friction: baseline (0.23-0.24% of premium, flat; imbalance
  +0.13, the softest bid-skew yet — worth one eye).
- Engine: 2.23M ticks, 36,670 bars, 0 db errors, 1 widen. Second
  fully-live day of the analytics chain; report generated clean.
- Observations:
  26. The short-vol payoff finally showed its shape: sell the richest
      IV print (80th pctile) into a tape that realizes 0.44% and the
      ledger's best day appears — +38 on a day the plan flagged
      premium as rich. Hyp. 23's "pricing gap risk" resolved: the gap
      CAME (-89 overnight) and the straddle, entered post-gap at
      09:20, still won fat. The priced risk expired at the open.
      (n=1)
  27. PE de-grossing (hyp. 21) survived a gap-down test: puts drained
      at every strike on the one day put protection should have been
      bid. Whoever is leaving the put side is leaving regardless of
      tape direction — positioning unwind, not view. CE build at
      24550 is the first overhead-write signature since the drift
      week. (n=2)
  28. Two clean closes in a row, and the dislocation's sign flipped
      negative at 15:16 before normalizing by 15:40. Supports hyp. 24
      (market adapting to the new close mechanics) — the monitor's
      baseline-relative design is doing its job either way. (n=5)
  29. Max-gamma has now sat at 24600 for three sessions (conc ~20%,
      below pin threshold) while spot closed 24,625 / 24,636 /
      24,571 — orbiting the strike without the concentration a pin
      regime requires. If Monday's expiry settles near 24600 anyway,
      the pin thesis needs a "weak attractor" variant that doesn't
      key off concentration alone. (n=3, resolves at the 08-11
      expiry)

## 2026-08-10 (day 10) — expiry-eve IV markup sold: new best day, one minute underwater

(The 08-11 expiry fell on Tuesday, not Monday as the previous footer
assumed; Monday was this session.)

- Tape: +14 gap open 24,585, high 24,620, low 24,511.4, close 24,583.8
  (+0.05%). Range 108.5 pts (0.44%) — third quiet drift day in a row.
- Regime: DIFFUSE (22% -> 25%), max-gamma at 24600 for a FOURTH
  straight session (obs. 29 series extends). Total gamma swelling into
  expiry-eve: ₹189k -> 239k -> 191k cr/1%.
- OI: mass CE-side drain at every strike (24400 -65%, 24500 -66%,
  24600 -44%, 24700 -31%) against modest PE bleed — the call-covering
  signature from the drift week, now as expiry-eve de-grossing on a
  flat tape. Writers left the call side wholesale a day before expiry.
- Vol: the overnight markup was the story — ATM IV 10.59% Friday close
  -> 16.99% Monday 09:20 (+6 vols over a weekend that delivered
  nothing), sliding all day to 14.54%. Day-plan IV percentile 83%
  (n=6); EOD straddle 148.7 pts = 0.60% to Tuesday's expiry.
- Paper straddle: **+45.7 — NEW BEST** (beats +38.0 set Friday).
  Credit 196.0 @ 24600 | MAE -0.5 at 09:21 | underwater ONE minute.
  The cleanest short-vol session on record.
- **CUMULATIVE LEDGER: +79.1** (10 sessions, 8W +153.8 / 2L -74.8).
- Day-plan advisory #3: DEFINED_RISK_SHORT at 24600 (diffuse, IV
  pctile 83, credit 186). Right call again — wings would have cost a
  few points of a fat winner. (track record n=3)
- Divergence: clean (max -29.7 at 15:10, close +9.6 vs baseline).
- Depth/friction: baseline; imbalance +0.03, softest yet (second soft
  print in a row — obs. from day 9 stands).
- Engine: 2.15M ticks, 33,535 bars, 0 db errors, 0 widens. (In
  hindsight: the first session of the Saturday-deployed container —
  the process whose SECOND session died next morning.)
- Observations:
  30. Back-to-back best days (+38.0, +45.7) share one shape: an IV
      markup sold into a tape that realizes ~0.44% — and both were
      flagged >=80th IV percentile by the day-plan that morning. The
      measured edge so far is premium LEVEL vs realizing, not
      calendar position. (n=2)
  31. Expiry-eve did not build a pin: calls were drained wholesale
      while concentration stayed diffuse (25%) and the wall sat
      unmoved at 24600. Whatever pins, it wasn't forming the evening
      before. (n=1, resolves next entry)

## 2026-08-11 (day 11) — EXPIRY 3 + the outage: reactor bug takes the morning; the wall finally moves

- **ENGINE INCIDENT — the program's first data loss.** Ticker dead
  from the 09:15 open: KiteTicker's twisted reactor cannot arm a
  second session in one process; every prior day had accidentally
  gotten a fresh container from evening pushes, and the first
  push-free weekend exposed it on expiry morning. The /admin panel
  stayed GREEN throughout (heartbeat fine, last_error None) — the
  founder noticed before the system did. Restored 11:33:41 by manual
  redeploy (2h18m lost). Same-day heal: 09:15-11:35 backfilled from
  Kite minute candles (13,844 hist rows, validated exact against live
  bars on an overlap window) BEFORE the EOD hook, so tonight's
  analytics computed on the full day. Permanently lost: book depth /
  spreads / 10s chain snapshots for the window. Fixes deployed
  post-close: deliberate daily process recycle after EOD (exit 43,
  on_failure restart) + last_error stamped in the dead-ticker loop;
  push-alerting priority raised. Morning numbers below marked (hist)
  where they rest on backfilled bars.
- Tape: open 24,575.1 (-8.7, and within 2 pts of the day's HIGH),
  steady sell to 24,429.2, settle-area close 24,471.7 (-0.46%). Range
  147.6 pts (0.60%) — the biggest range of the three expiries.
- Regime: **the max-gamma wall MIGRATED for the first time in five
  sessions** — 24600 -> 24500 (hist 10:00 read 25%, 13:00 26%, 15:15
  37% = PIN-GRAVITY only in the last hour). Spot settled 24,471.7,
  28 pts under the wall. Obs. 29/31 resolve: the static 24600 magnet
  never held spot — on expiry day the wall CHASED spot down, and
  concentration arrived late where price already was.
- OI: the whole chain drained except 24450 — CE +60% / PE +86% AT the
  settle strike, the sharpest single-strike build recorded. Expiry
  concentration formed at the destination, not the origin.
- Vol: 26.02% (hist) at 09:20 — double any prior morning; 24.26% at
  12:30; the 15:15 48% print is the usual tiny-premium expiry
  artifact. Day-plan (retro-computed on healed data, like day 7 —
  backtest, not track record): REDUCED_SIZE at 24500, MIXED read,
  IV pctile 100%, credit 122. On the day: reduced-size short premium
  centered 24500 would have paid; the 122 credit was NOT the Aug-04
  thin-credit trap (93 pts at ~11 vols) — high-IV expiries are a
  different animal from low-IV ones. (n=2 expiry credit regimes)
- Paper straddle: **NOT COMPUTABLE — the ledger's first hole.** The
  09:20 entry marks at effective prices need the book, and the book
  is in the lost window; a close-based estimate would blend fabricated
  fills into a measured ledger, so the row stays empty by design.
  Ledger holds at +79.1 (10 rows, 8W/2L). MAE/underwater for this
  session are unmeasurable forever.
- Implied-vs-realized verdict #3 (both windows): Friday-EOD implied
  0.89% with the weekend inside vs realized -0.40% Fri-close ->
  settlement — implied more than 2x realized. Final-day implied 0.60%
  vs realized -0.46% — implied still won, but by the thinnest margin
  yet (a 24600 settle-held straddle collected ~20 of 148.7 pre-cost).
  Verdicts now 3/3 for implied-rich, margins 0.69-vs-1.02, then wide,
  now thin. (n=3)
- Divergence: clean close — spot 24,471.7 vs parity forward 24,471.8
  at 15:40, +12.1 vs baseline. Fifth clean close in a row; the
  new-timings dislocation (hyp. 24) looks fully adapted-out at n=7.
- Engine (post-restore): 1.59M ticks, 24,548 live bars, 0 db errors,
  1 widen (down-side, spot broke below the 24600-anchored window).
- Observations:
  32. Pin, when it finally reappeared (n=2 of 3 expiries), was a
      CHASE: wall migration down to spot + late concentration + a
      violent both-sides build at the settle strike. The 07-28
      "gravity" archetype (spot magnetized to a pre-existing wall) did
      not repeat; expiry structure formed around where price already
      was. Two pin mechanisms now hypothesized — gravitational
      (07-28) vs chased (08-11) — and only the first is tradeable in
      advance. (n=2 pins / 3 expiries)
  33. The short-vol margin compresses as IV rises to meet realized:
      verdict margins went fat -> fat -> thin while morning IV went
      ~11% -> ~12% -> 26%. Selling the markup pays until the markup
      is finally justified — position sizing must scale DOWN as the
      percentile rises, exactly opposite the naive
      "richer-premium-sell-more" instinct. (n=3 expiries, weak)
  34. Ops: the monitoring gap was the real failure — 2h18m of green
      panel over a dead feed. A capture-quality alert (phase=capture,
      packets=0, N minutes) is now the cheapest insurance in the
      program. Data-wise the bar layer healed same-day at candle
      resolution; the microstructure layer (book, snapshots) is the
      only thing an outage truly destroys. (n=1, intended to stay
      n=1)

## 2026-08-12 (day 12) — new cycle opens diffuse; the V that closed strong

- Tape: open 24,461.4 (-10.3 gap), sold to 24,266.0 by midday, bought
  back to close 24,436.0 (-35.8, -0.15%). Range 200.0 pts (0.82%) —
  the widest range of the week, and the only session that closed in
  its upper half.
- Regime: DIFFUSE and the most diffuse readings in the library —
  concentration 16.9% -> 14.9% -> 15.0%, max-gamma oscillating
  24500 / 24400 / 24500 with no strike holding it. Total gamma
  ₹66k -> 86k -> 71k cr/1%, an order of magnitude under expiry-day
  levels: the post-expiry chain rebuilt as an open field, exactly the
  question day 11's footer asked.
- OI: the bearish tell, in hindsight. CE BUILT below spot (24250 +78%,
  24350 +102%) while PE drained at every strike (-16/-23/-70/-68/-50%).
  Overhead writing migrating DOWN plus wholesale put de-grossing —
  the structure for the week's slide was laid on its first session.
- Vol: ATM IV 10.68% (09:20) -> 10.73% (12:30) -> 9.77% (15:15). EOD
  ATM straddle (24450) 245.5 pts = 1.00% implied to the 08-18 expiry.
- Paper straddle: **+33.0** (credit 279.9 @ 24400). MAE -6.3 at 09:27,
  underwater 7 minutes. Running ledger **+112.1**.
- Day-plan advisory #4: DIRECTIONAL_DEBIT_SPREAD at 24500 (diffuse,
  IV pctile 12% n=8, credit 274) — i.e. naked short straddle
  discouraged. The naked straddle made +33.0. Miss.
- Divergence: **FLAG** +53.1 pts at 15:33 (baseline -61.6), close
  window +51.3 vs baseline — but note the print sits in the post-15:30
  extended window, not the settlement window.
- Depth/friction: baseline. Spread 0.40 -> 0.38 pts (flat 0.23% of
  premium); imbalance +0.20.
- Engine: 2.33M ticks, 38,081 bars, 0 db errors, 2 widens, 103
  contracts — first unattended morning after the 08-11 recycle fix,
  and it armed clean.

## 2026-08-13 (day 13) — gap down, grind sideways, IV keeps bleeding

- Tape: open 24,383.4 (-52.5 gap), low 24,311.5, high 24,414.9, close
  24,395.8 (-40.1, -0.16%). Range 103.5 pts (0.42%) — the gap was the
  whole day's move; the session itself went nowhere.
- Regime: DIFFUSE, and for the first time this cycle a strike held —
  max-gamma pinned at 24400 across all three snapshots (conc 16.1% /
  17.1% / 15.2%). Total gamma ₹97k -> 104k -> 95k cr/1%.
- OI: CE drained at the money and below (24300 -53%, 24400 -29%,
  24200 -23%) against a flat put side (+4 / -10 / -8 / +2 / -3%).
  Note against day 12: the put drain stopped, the call drain started.
- Vol: 9.79% -> 9.03% -> 8.85%. EOD ATM straddle (24350) 216.6 pts =
  0.89% implied to expiry. Third straight session of IV compression.
- Paper straddle: **+13.7** (credit 232.2 @ 24350). MAE -10.9 at
  12:03, underwater 16 minutes. Running ledger **+125.8**.
- Day-plan advisory #5: DIRECTIONAL_DEBIT_SPREAD at 24400 (diffuse,
  IV pctile 11% n=9, credit 226). Naked straddle again discouraged,
  again paid — a mild miss.
- Divergence: clean (max -36.1 at 14:58, close +13.9 vs baseline).
- Depth/friction: baseline. Spread 0.34-0.36 pts (0.23%); imbalance
  +0.17.
- Engine: 2.23M ticks, 36,614 bars, 0 db errors, 1 widen.

## 2026-08-14 (day 14) — the library's lowest IV; first flat day of the slide

- Tape: open 24,331.7 (-64.2 gap), low 24,298.3, high 24,405.2, close
  24,366.0 (-29.8, -0.12%). Range 106.9 pts (0.44%). Third straight
  session where the gap was the move.
- Regime: DIFFUSE (conc 16.3% / 16.5% / 17.9%), max-gamma 24400 /
  24300 / 24400. Total gamma steps up to ₹160k -> 183k -> 143k cr/1%
  as expiry approaches.
- OI: two-sided wholesale de-grossing into the weekend — every strike
  in the window drained on BOTH sides (CE -58/-71/-58/-32/-32%,
  PE -21/-29/-28/-24/-26%). Nobody carried a position over.
- Vol: 9.05% -> 8.31% -> 8.13%. **IV percentile 0% (n=10)** — the
  lowest ATM IV recorded in the program. EOD ATM straddle (24350)
  179.7 pts = 0.74% implied to expiry.
- Paper straddle: **-1.4** (credit 195.8 @ 24300). MAE -16.7 at 14:02,
  underwater 101 minutes and **still underwater at the 15:15 exit** —
  the first session that never came back. Running ledger **+124.4**.
- Day-plan advisory #6: DIRECTIONAL_DEBIT_SPREAD at 24400 (diffuse,
  IV pctile 0%, credit 184) — naked short premium discouraged on the
  cheapest premium in the library, and it was right. Hit.
- Divergence: **FLAG** -41.5 pts at 15:18 (settlement window), close
  -20.9 vs a -34.5 baseline.
- Depth/friction: baseline. Spread 0.30-0.31 pts (0.23-0.24%);
  imbalance +0.09.
- Engine: 2.30M ticks, 36,669 bars, 0 db errors, 1 widen.

## 2026-08-17 (day 15) — weekend markup again; sold from the open

- Tape: open 24,353.2 (-12.8 gap) within 7 pts of the day's HIGH,
  then a one-way sell to 24,227.0, close 24,287.7 (-78.3, -0.32%).
  Range 132.8 pts (0.55%) — the first session of the week where the
  intraday tape, not the gap, did the damage.
- Regime: **first MIXED morning read since Aug 3** — concentration
  27.4% at 10:00, decaying to 21.8% then 19.7% as the day aged;
  max-gamma 24300 / 24300 / 24400, i.e. the wall drifted UP while
  spot went down. Total gamma ₹248k -> 251k -> 223k cr/1%.
- OI: the call side capitulated everywhere (24300 -69%, 24200 -61%,
  24100 -55%, 24400 -41%, 24500 -28%) against a milder put drain.
  Compare day 12, where calls BUILT: the whole cycle's call structure
  was written and then covered inside four sessions.
- Vol: the weekend markup repeats — 8.13% Friday 15:15 -> **11.60%**
  Monday 09:20 (+3.5 vols over a weekend that delivered a -12.8 gap),
  10.99% at 12:30, 11.51% at 15:15. EOD ATM straddle (24300) 115.7
  pts = 0.48% implied to the next day's expiry.
- Paper straddle: **-2.8** (credit 132.8 @ 24300). MAE -15.2 at 13:15,
  underwater 145 minutes, still underwater at the exit. Running
  ledger **+121.6**.
- Day-plan advisory #7: REDUCED_SIZE at 24300 (MIXED conc 27%, IV
  pctile 45% n=11, credit 123). Half size on a losing session. Hit.
- Divergence: clean (max -32.6 at 15:28, close -20.9 vs a -30.1
  baseline — carry compressing into expiry as it should).
- Depth/friction: absolute spreads tightest yet at 0.26-0.29 pts, but
  the relative cost started to climb intraday (0.25% -> 0.28%);
  imbalance +0.14.
- Engine: 2.40M ticks, 36,172 bars, 0 db errors, 1 widen.

## 2026-08-18 (day 16) — EXPIRY 4: record concentration, and spot ignored it

- Tape: open 24,239.7 (-48.0 gap), high 24,269.5, low 24,154.9,
  **close 24,154.9 = the low** (-132.8, -0.55%). Range 114.6 pts
  (0.47%). No settlement-window bounce at all — the first expiry that
  closed on its low.
- Regime: **PIN-GRAVITY, and the strongest gamma structure ever
  recorded** — concentration 27.7% -> 37.3% -> **47.6%** (prior high
  37% on 08-11), total gamma ₹514k -> 685k -> 581k cr/1%. Max-gamma
  migrated 24250 -> 24200 -> 24200. Spot settled 24,154.9, **45 pts
  BELOW the wall**, at the low, with no reversion.
- OI: the build landed a rung under the wall — 24150 CE **+298%** /
  PE +1% at the settle strike, while 24250 (CE -25 / PE -77%) and
  24350 (CE -50 / PE -79%) emptied. Structure formed at the
  destination again, not at the magnet.
- Vol: 15.99% (09:20) -> 17.12% (12:30) -> 36.97% (15:15, the usual
  tiny-premium expiry artifact — the EOD straddle is 4.9 pts = 0.02%).
  Morning IV percentile 75% (n=12).
- Paper straddle: **+19.7** (credit 82.8 @ 24250 — the **thinnest
  credit on record**, thinner than the 93.0 that produced the ledger's
  worst day). MAE -14.9 at 11:30, underwater 11 minutes.
- **CUMULATIVE LEDGER: +141.3** (15 rows / 16 sessions, 11W +220.3 /
  4L -79.0; the 08-11 outage row stays empty by design).
- Day-plan advisory #8: REDUCED_SIZE at 24250 (MIXED conc 28%, IV
  pctile 75%, credit 76 flagged THIN). Half size on a winner —
  defensible, but the THIN flag pointed at the wrong risk (obs. 38).
- Divergence: **FLAG** -40.6 pts at 15:19 (settlement window); close
  +7.3 vs a -7.1 baseline — carry all but gone at expiry.
- Depth/friction: absolute spreads the tightest on record (0.22-0.24
  pts) while the relative cost ran 0.32% -> 0.76% into the close — the
  cleanest confirmation yet of the standing "no near-ATM transactions
  after 15:15 on expiry" constraint. Book imbalance +0.44, the highest
  recorded (vs +0.03 on day 10).
- Engine: 2.48M ticks, 36,536 bars, 0 db errors, 1 widen, 95/95
  contracts ticking.

### Observations — the 08-18 cycle (days 12-16)

35. **The first sustained DOWN-trend week**, and it fills the library's
    oldest hole. Five consecutive lower closes: 24,471.7 -> 24,435.9
    -> 24,395.9 -> 24,366.0 -> 24,287.7 -> 24,154.9, total -316.8 pts
    (-1.29%). Three of those sessions read DIFFUSE, so the day-plan
    caveat standing since day 7 — "all diffuse days so far were
    UP-drift (n=3); zero down-diffuse tested" — is now answered:
    down-diffuse tested n=3, intraday short straddle made +33.0 /
    +13.7 / -1.4. Diffuse-down did NOT punish short premium the way
    the caveat feared. But the branch's rationale text in
    `day_plan.recommend_structure` ("covering-fuel drift, writers
    re-form a rung up, 4/4 up-drift days closed strong") is now
    descriptively wrong on half its own sample and must be rewritten.
    (n=3 down-diffuse)
36. **Implied was CHEAP on every measured mark, for the first time in
    the program.** EOD straddle vs the realized move to the 08-18
    settlement: 08-12 implied 1.00% vs realized -1.15%; 08-13 0.89%
    vs -0.99%; 08-14 0.74% vs -0.87%; 08-17 0.48% vs -0.55%. 4/4 to
    realized. Program verdicts now stand at 3 cycles implied-rich, 1
    implied-cheap — and the cheap one was the trending cycle. The
    short-vol edge is a range-regime edge, not a constant. (n=4 marks,
    1 cycle)
37. **And yet the intraday straddle made +62.2 across the same five
    sessions.** Those two facts are compatible only one way: premium
    was fairly priced for the multi-day drift and over-priced for the
    session. The arithmetic is direct — the five opens gapped -10.3,
    -52.5, -64.2, -12.8, -48.0 = **-187.8 pts, 59% of the cycle's
    -316.8**, delivered with the market shut. This is the strongest
    evidence yet for the standing intraday-only constraint, and the
    first time it has been measured across a whole cycle rather than
    on one Fri->Mon counterfactual. (n=5)
38. **The thin-credit trap did not spring — and the credit was never
    the variable.** 08-18 sold 82.8, thinner than 08-04's 93.0 that
    lost -55.2 with MAE -78.3, and it paid +19.7 with MAE -14.9. The
    difference is what concentration DID: 08-04 decayed (32% -> 22%,
    pin never formed) while 08-18 built (28% -> 37% -> 48%).
    Provisional refinement of hyp. 10: thin credit is dangerous when
    concentration is DECAYING, not thin credit as such. This is
    sharply testable and it contradicts the current `credit_thin`
    branch, which keys on credit level alone. (n=2, weak)
39. **Record concentration still did not pin.** 47.6% at 15:15 — the
    highest ever — with the wall migrating 24250 -> 24200, and spot
    settled 45 pts below it at the day's low. The OI build was at
    24150 (CE +298%), a rung under the wall. Third straight expiry
    where structure formed where price already was. Obs. 32's
    archetypes now read 1 gravitational (07-28) / 2 chased (08-11,
    08-18) / 1 no-pin (08-04): the archetype the program opened with
    is looking like the outlier, and concentration LEVEL alone is not
    a tradeable pin signal. What might be: concentration level plus
    the wall's own displacement from spot. (n=4 expiries)
40. **Obs. 30 does not survive, and the reason is a measurement bug.**
    It read "the measured edge is premium LEVEL vs realizing" off two
    >=80th-percentile winners. This week: IV percentiles 12 / 11 / 0 /
    45 / 75 against P&L +33.0 / +13.7 / -1.4 / -2.8 / +19.7 — the
    biggest winner came at the 12th percentile. The confound is
    days-to-expiry: 08-12's 279.9 credit is fat because it holds four
    sessions of theta, not because vol is rich. Both
    `day_plan.iv_percentile` (ATM IV vs all history at the same snap)
    and the `credit_min_win` thinness test (a 0-DTE credit compared
    against a 4-DTE one) are DTE-blind, and neither can carry weight
    until they condition on it. (n=5, and a code finding)
41. **The clean-close run ended.** Divergence flagged beyond the 40-pt
    band on 3 of 5 sessions (08-12 +53.1 @15:33, 08-14 -41.5 @15:18,
    08-18 -40.6 @15:19), so day 11's read that hyp. 24 is "fully
    adapted-out at n=7" does not hold at n=12. The shapes differ —
    08-12's print sits in the post-15:30 extended window, the other
    two inside the settlement window — and the carry baseline
    collapsed across the cycle (-61.6 -> -30.1 -> -7.1) exactly as it
    should into expiry. A fixed 40-pt band measured against a
    shrinking baseline is itself DTE-blind; the flag is doing double
    duty for two different phenomena. (n=12)
42. **The MAE library reaches the calibration gate at n=15.** Winners'
    MAE now spans -0.5 to -28.2 (median -12.2) and the two structural
    losers sat far outside it (-78.3, -72.3) — but the week's two
    small losers (-16.7, -15.2) fall INSIDE the winners' band. So MAE
    separates the catastrophic days and cannot separate the marginal
    ones, which is precisely why the founder framework requires
    state-conditioned thresholds rather than price levels. Also worth
    recording: the pattern that motivated the framework — MAE
    exceeding final profit on all three of the first days — has
    reversed, with only 3 of 11 winners now finishing below their own
    drawdown. The n>=15 gate in TASKS.md is MET; calibration can
    begin, conditioned on regime AND days-to-expiry. (n=15)
43. **Day-plan track record, n=8.** This cycle: #4 miss, #5 miss,
    #6 hit, #7 hit, #8 mixed (half size on a winner). The two misses
    share one cause — the diffuse branch refuses naked short premium
    on the strength of an up-drift story (obs. 35) — and the mixed
    call inherits the DTE-blind thin-credit test (obs. 38, 40). The
    advisory's failures are concentrated in exactly the two heuristics
    this cycle falsified, which is the useful kind of failure. (n=8)
44. **Ops: the recycle fix held.** Five consecutive unattended
    sessions since the 08-11 incident — 0 db errors, every contract
    ticking (95-103 of 95-103), 2.2-2.5M ticks a day, and EOD
    materialization + three gamma snapshots + a ledger row landing on
    all five with no intervention. The incident is closed at n=5. Push
    alerting is still unbuilt and remains the top ops gap: the recycle
    fixed THIS failure mode, not the class of silent-death failures.
    (n=5)

---

*Next entry: 2026-08-19 (Wed) — first session of the 08-25 weekly off
a trend cycle rather than a range one. Does the post-expiry chain
rebuild diffuse again (day 12's shape), and does IV hold the expiry-day
markup or resume compressing? Open items carried in: the diffuse-branch
rewrite (obs. 35), DTE-conditioning for IV percentile and credit
thinness (obs. 40), and the n=15 threshold calibration (obs. 42).*
