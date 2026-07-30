# Microstructure Engine — Tasks

## Stage 1 — IV + first-order Greeks (DONE 2026-07-29)

- [x] 19 spec tests (TDD red-first): BS + B76 known values, IV round-trips,
      parity, symmetry, edges, materializer roundtrip
- [x] greeks.py: BS + Black-76, vectorized bisection IV, delta/gamma/vega/theta
- [x] option_greeks_minute + materializer CLI; 651,934 rows materialized
- [x] Worker EOD hook: each session auto-materializes after bars insert
- [x] Forward upgraded to parity-implied (b76-parityfwd-v1): CE/PE gap
      3.4 -> 0.0 vol pts, IV coverage 99.7%; futures de-carry rejected

## Stage 2 — gamma aggregation (readout live, tables next)

- [x] stage2_gamma_profile.py: GEX/1% by strike, max-gamma strike,
      concentration — expiry day pinned 57% single-strike vs trend day 20%
- [x] gamma_profile_daily table + live compute_from_snapshot + /admin
      Options Analytics card via /api/options/live-analytics (2026-07-30)
- [ ] Zero-gamma / walls need Stage 3 dealer-sign assumptions (labeled)

## Stage 3 / 4 — estimated + flow-adjusted positioning (later; assumptions
      surfaced with confidence levels per the vision doc)
