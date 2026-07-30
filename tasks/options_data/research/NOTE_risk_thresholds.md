# Founder note — risk thresholds & the MAE problem (2026-07-30)

## The observation (founder, after three straddle days)

On every day reviewed so far, the short straddle was at some point more
negative than its eventual realized profit. Trading this in real time
therefore requires knowing, in advance, what adverse excursion we are
willing to carry to collect the profit we're targeting — and when to
adjust, roll, or exit. Those calls must be **real-time and
probabilistic, not predictive**: grounded in the accumulated studies
(OI migration, gamma concentration, depth state), not in price alone.

## The numbers (sell ATM straddle 09:20, exit 15:15, real bid/ask)

| Day | Final P&L | MAE (worst) | MAE at | Underwater minutes | Last underwater |
|---|---|---|---|---|---|
| Jul 28 (expiry pin) | +13.2 | **−19.1** | 10:07 | 50 / 356 | **15:11** |
| Jul 29 (gap+trend) | +7.8 | **−11.6** | 09:40 | 86 / 356 | 14:30 |
| Jul 30 (range drift) | +16.3 | **−13.3** | 12:33 | 9 / 356 | 12:36 |

MAE / final-profit ratios: 1.4x, 1.5x, 0.8x.

## Implications

1. **Naive stops destroy this strategy.** Any fixed stop tighter than
   ~20 pts would have converted at least one of three winners into a
   loser; a stop at −12 converts two. Stop placement must come from the
   MAE *distribution conditioned on day-type*, not from a comfort
   number.
2. **The hold decision needs non-price state.** The starkest case: Jul
   28 was underwater at 15:11 and finished +13.2 at 15:15 — expiry-day
   profit arrives almost entirely in the last minutes as the pin
   crushes premium. At the moment price said "bail", the measured state
   said "hold": gamma concentration at its day-peak (57% single-strike)
   and ATM OI still building. Conversely, Jul 29's covering-fuel signal
   (overrun-strike OI drain, fired 12:49) is the class of signal that
   should *lower* the tolerated excursion or trigger the roll.
3. **The framework is probabilistic hold/fold:** at any moment,
   estimate P(position recovers by exit | current regime state) from
   the day-type library, and compare the tolerated remaining excursion
   against that. No price prediction — state-conditioned base rates.

## Research program this defines (feeds the autonomy "judgment" layer)

- **MAE distributions by day-type** — accumulate per-session MAE, MAE
  timing, underwater duration, conditioned on the regime read
  (pin-gravity / diffuse / covering-fuel). Needs the day-type library
  (15–20+ sessions); collection is already automatic.
- **Trigger catalog** — candidate adjust/exit signals to score against
  outcomes: overrun-strike OI drain, gamma-concentration slope,
  ATM-OI build rate, imbalance deviation from baseline, IV path.
  Score each as: when it fired, what holding vs acting would have
  yielded.
- **Threshold table** — the deliverable: for each regime, (a) max
  tolerated excursion, (b) roll trigger, (c) hard stop, each with the
  historical base rate behind it. This table IS the risk configuration
  the founder sets on the future autonomous loop.

Until the library is large enough, every number above is provisional —
the note exists so the framework is fixed before the data arrives, not
fitted after.
