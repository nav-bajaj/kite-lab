# Microstructure Engine — Tasks

## Stage 1 — IV + first-order Greeks (measured math)

- [ ] Spec tests: BS known values, IV round-trip, parity, symmetry, edges
- [ ] greeks.py: vectorized BS price / IV inversion / delta gamma vega theta
- [ ] option_greeks_minute table + materializer CLI (assumptions + version cols)
- [ ] Materialize full bar history; validation readout (ATM IV levels, smile,
      gamma peak at ATM, parity residuals)
- [ ] Nightly materialization for each new session (hook or cron)

## Stage 2 — gamma aggregation (next)

- [ ] Gamma-by-strike profile per minute/day; max-gamma strike; concentration
- [ ] Futures-implied forward (Black-76) variant; compare IVs vs Stage 1

## Stage 3 / 4 — estimated + flow-adjusted positioning (later; assumptions
      surfaced with confidence levels per the vision doc)
