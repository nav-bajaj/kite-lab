# Momentum Cadence Observations (2026-05-13)

**Status:** Headline pick is **weekly** (locked, matches production). This doc
captures detailed observations from the IS cadence sweep that argue for a
**separate monthly-cadence momentum offering** as a sibling product. To be
revisited after the OOS validation phase.

---

## Operational lens (added 2026-05-13)

Cadence isn't just a performance choice — it's an **audience choice**. A
subscriber can only benefit from a strategy if they can execute it for
years. The product matrix needs to consider:

| Cadence | Operational profile | Audience fit | DD profile |
|---|---|---|---|
| **Bi-weekly Fri→Mon** | 2.5 day awareness window; predictable Mon mornings | Broadest — most retail investors | Smoother (mid-cadence) |
| **Weekly Thu→Fri** | Overnight window; faster reaction | Active investors | Sharper signal, deeper DD |
| **Monthly** | One Monday/quarter feel | Set-and-forget; tax-sensitive | Smoothest, similar DD to weekly |

A weekly Thursday→Friday strategy with 25-30% DDs requires a subscriber who:
- Can act on a Thursday close signal by Friday morning
- Has psychological capacity for double-digit drawdowns
- Understands the strategy well enough not to panic-quit mid-DD

That's a narrow audience. **Broader-audience operational profiles often
matter more than ~2pp CAGR** for subscription business retention. A
biweekly L6 (operational tradeoff) might net more LTV-per-subscriber
than a weekly L6 (raw performance optimum) even if backtests favor weekly.

See `DD_REDUCTION_RESEARCH.md` for the related work on DD-compression
levers; the three-tier product framework there ties this operational
lens to specific candidate sibling products.

---

---

## Test setup

- IS window: 2009-09-01 → 2016-12-31 (~7.3 years)
- Universe: NSE 500 (current production)
- Cadence values: weekly / biweekly / monthly (entry signal frequency)
- 8 parameter tracks tested (combinations of L6/L9 × vol_floor 0.01/0.05 ×
  exit_buffer 0/6 with other params locked at IS-best: top_n=24, min_hold=8,
  skip=5, vol_power=0.5 for vf=0.01 tracks)
- 24 backtests total

---

## Per-track results (Sharpe / CAGR / Calmar / Max DD / RT-per-year)

### Track A1_b0 — L6 / vf=0.01 / vp=0.5 / **buffer=0**
| Cadence | Sharpe | CAGR | Calmar | MaxDD | RT/yr |
|---|---|---|---|---|---|
| weekly | 1.46 | 31.4% | 1.18 | -26.5% | 192 |
| biweekly | 1.43 | 30.6% | 1.10 | -27.8% | 164 |
| **monthly** | **1.52** | **32.9%** | **1.27** | **-26.0%** | **106** |

### Track A1_b6 — L6 / vf=0.01 / vp=0.5 / **buffer=6**
| Cadence | Sharpe | CAGR | Calmar | MaxDD | RT/yr |
|---|---|---|---|---|---|
| **weekly** | **1.54** | **33.3%** | **1.33** | **-25.0%** | 139 |
| biweekly | 1.49 | 32.2% | 1.30 | -24.7% | 119 |
| monthly | 1.48 | 31.8% | 1.22 | -25.9% | 87 |

### Track A2_b0 — L6 / vf=0.05 / vp=1.0 / **buffer=0** (closest to **production**)
| Cadence | Sharpe | CAGR | Calmar | MaxDD | RT/yr |
|---|---|---|---|---|---|
| weekly | 1.27 | 27.6% | 0.91 | -30.3% | 185 |
| biweekly | 1.33 | 29.2% | 0.98 | -29.7% | 156 |
| **monthly** | **1.36** | **29.9%** | **1.19** | **-25.2%** | **103** |

### Track A2_b6 — L6 / vf=0.05 / vp=1.0 / **buffer=6**
| Cadence | Sharpe | CAGR | Calmar | MaxDD | RT/yr |
|---|---|---|---|---|---|
| weekly | 1.43 | 31.9% | 1.21 | -26.4% | 131 |
| **biweekly** | **1.44** | **32.1%** | 1.13 | -28.5% | 111 |
| monthly | 1.41 | 31.4% | 1.17 | -27.0% | 83 |

### Track B1_b0 — L9 / vf=0.01 / vp=0.5 / **buffer=0**
| Cadence | Sharpe | CAGR | Calmar | MaxDD | RT/yr |
|---|---|---|---|---|---|
| weekly | 1.37 | 28.0% | 1.01 | -27.7% | 153 |
| **biweekly** | **1.40** | **28.7%** | **1.05** | **-27.4%** | 126 |
| monthly | 1.34 | 27.1% | 0.98 | -27.8% | 83 |

### Track B1_b6 — L9 / vf=0.01 / vp=0.5 / **buffer=6**
| Cadence | Sharpe | CAGR | Calmar | MaxDD | RT/yr |
|---|---|---|---|---|---|
| **weekly** | **1.44** | **29.7%** | **1.06** | -27.9% | 101 |
| biweekly | 1.37 | 27.7% | 0.98 | -28.3% | 84 |
| monthly | 1.40 | 28.5% | 1.04 | -27.5% | 64 |

### Track B2_b0 — L9 / vf=0.05 / vp=1.0 / **buffer=0**
| Cadence | Sharpe | CAGR | Calmar | MaxDD | RT/yr |
|---|---|---|---|---|---|
| **weekly** | **1.30** | 27.6% | 0.99 | -27.9% | 150 |
| biweekly | 1.21 | 25.3% | 0.90 | -28.2% | 125 |
| monthly | 1.30 | 27.4% | 0.97 | -28.3% | 81 |

### Track B2_b6 — L9 / vf=0.05 / vp=1.0 / **buffer=6**
| Cadence | Sharpe | CAGR | Calmar | MaxDD | RT/yr |
|---|---|---|---|---|---|
| weekly | 1.32 | 28.1% | 1.01 | -27.8% | 97 |
| **biweekly** | **1.39** | **30.0%** | **1.08** | -27.7% | 83 |
| monthly | 1.34 | 28.3% | 1.03 | -27.4% | 63 |

---

## Cross-track patterns

### Pattern 1: No single cadence dominates
Across 8 tracks: weekly wins 3, biweekly wins 3, monthly wins 2. Differences
between cadences within a track are small (0.02-0.10 Sharpe). Cadence is a
**second-order lever** — score-shape params (vol_floor, vol_power, buffer)
matter much more.

### Pattern 2: Cadence preference depends on `buffer`
| buffer | weekly wins | biweekly wins | monthly wins |
|---|---|---|---|
| **buf=0** (no buffer) | 1/4 tracks | 1/4 | **2/4** |
| **buf=6** (buffered) | **3/4** | 1/4 | 0/4 |

Interpretation: when exit_buffer=0, you exit immediately on rank drops →
weekly rebalance causes high churn → less-frequent cadences (biweekly,
monthly) compensate. When exit_buffer=6, the buffer already smooths exits →
weekly cadence captures fresh signal without excess churn.

**This is the key insight for an alternative product:** *if you can't or don't
want to use an exit buffer (e.g., for regulatory/operational reasons),
monthly cadence is likely better than weekly.*

### Pattern 3: The single biggest opportunity is in the production track
Track **A2_b0** is the closest analog to current production (L6, vf=0.05,
buf=0). It currently runs at weekly cadence:
- **Current production cadence (weekly):** Sharpe 1.27, CAGR 27.6%, DD -30.3%, 185 RT/yr
- **Monthly alternative:** Sharpe **1.36** (+0.09), CAGR **29.9%** (+2.3pp), DD **-25.2%** (+5.1pp), RT/yr **103** (-44%)

Improvement across all four metrics. Lower turnover → meaningful tax/cost
savings in deployment. This is a clean Pareto-better result on IS (subject
to OOS confirmation).

### Pattern 4: The global IS-best config uses weekly + buffer
Track **A1_b6 weekly** (L6 / vf=0.01 / vp=0.5 / buffer=6 / weekly):
- CAGR 33.26%, Sharpe 1.54, Sortino 1.33, Calmar 1.33, DD -25.0%, RT/yr 139

This combines: vol-normalized scoring (0.01 floor) + mild vol penalty (0.5
power) + buffer-smoothed exits + weekly fresh signal. The buffer absorbs
weekly's natural churn while the weekly cadence keeps signal responsive.

---

## Implications for alternative offerings

### Candidate sibling product: **Monthly Momentum**
- Closest to A2_b0 monthly: L6 / vf=0.05 / vp=1.0 / buffer=0 / **monthly**
- ~44% lower turnover than current weekly production (103 vs 185 RT/yr)
- Better risk-adjusted IS performance (+0.09 Sharpe, +5pp DD)
- **Use case:** Tax-sensitive investors, larger AUM where weekly trading is
  operationally heavy, or "set and forget" investors who don't want to
  monitor a Friday→Monday workflow
- Operates on the SAME signal logic as production — just rebalances less often

### Candidate flagship upgrade: **Buffered L6 Momentum**
- Closest to A1_b6 weekly: L6 / vf=0.01 / vp=0.5 / buffer=6 / weekly
- Stays weekly (operationally identical to production)
- BUT changes vol_floor (0.05 → 0.01) and adds exit_buffer (0 → 6)
- IS lift over current production: +0.27 Sharpe, +5.7pp CAGR, +5pp DD
- **Use case:** Direct upgrade to flagship, contingent on OOS validation

---

## Open questions for later

1. **Does the cadence preference survive OOS?** Especially the A2_b0 monthly
   finding (+0.09 Sharpe on IS). If it survives OOS, monthly momentum is
   genuinely a better product variant.
2. **Cadence × universe interaction.** All tests above used NSE 500. Does
   monthly hold up on Nifty 250 / Nifty 100?
3. **Cadence × min-hold interaction.** min_hold_days=8 with weekly means
   "at least one rebalance cycle." With monthly, min_hold becomes essentially
   no-op since the next rebalance is already 30+ days away. Worth re-testing
   min_hold on monthly tracks.
4. **Bi-weekly's role.** Biweekly wins on 3 tracks but never by much. Is it
   a useful middle ground or just a "best of neither" compromise?
5. **Cost modeling.** With Indian short-term capital gains tax of 20% (since
   FY 2024-25), turnover difference of ~80 RT/yr translates to material
   real-money differences. A proper cost/tax-aware backtest could shift the
   relative rankings significantly.

---

## Locked decision (2026-05-13)

**Weekly** cadence is locked on all 8 tracks for the IS-then-OOS cycle.
This matches current production and keeps the comparison straightforward.

Cadence will be revisited:
- After OOS validation confirms (or refutes) the IS findings above
- As input for the future **Monthly Momentum sibling product** evaluation
- During eventual walk-forward robustness testing

If OOS validation shows the production track (A2_b0) holds up on weekly and
monthly performs ~equally OR better, monthly becomes a serious candidate
for product launch as a low-turnover variant.

---

## Files

- Per-track sweep CSVs: `tasks/MM-tuning/sweeps/L{lb}_vf{floor}_buf{buffer}/is_rebalance.csv`
- Sweep script: `scripts/momentum_sweep.py`
- Engine: `scripts/_momentum_engine.py`
