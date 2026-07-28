# Quantitative visual-pattern specification

Status: curriculum contract for prototype validation. This is not yet the AI
implementation specification.

## Purpose

The course should not teach learners to stare at a chart until a familiar
shape appears. It should teach them to:

1. describe the shape in measurable terms;
2. let a program apply the same definition across a stated universe;
3. inspect the program's numerical diagnostics;
4. confirm that the visual overlay matches those diagnostics; and
5. state what the match does **not** prove.

This follows the research direction established by Lo, Mamaysky, and Wang:
chart-pattern recognition can be made systematic, but visual geometry is
otherwise highly subjective. Their method and evidence do not validate the
teaching thresholds below or establish an Indian-market trading edge. See the
[NBER paper](https://www.nber.org/papers/w7613).

## Scope

The course uses two layers of price observation.

### Layer A — simple landmarks and conditions

These already exist in the Marketworks teaching surface:

1. fresh 20-session closing-high breakout;
2. fresh 252-session closing-high breakout; and
3. coiled-spring / low-volatility pre-breakout condition.

They teach rolling windows, excluding today from a prior high, trend context,
and volatility normalization. They are not treated as geometric chart
patterns.

### Layer B — three geometric pattern families

1. converging triangle breakout;
2. rectangle/base breakout; and
3. bull flag breakout.

These three create a useful beginner taxonomy:

- **compression** — two boundaries converge;
- **range** — two boundaries remain approximately horizontal; and
- **continuation structure** — an impulse is followed by a controlled
  counter-trend consolidation.

The core course excludes double tops/bottoms, cup-and-handle,
head-and-shoulders, wedges, candlestick catalogs, and machine-learned image
classifiers. They may be explored in an advanced pattern-research course after
the learner understands pivots, tolerances, data leakage, and out-of-sample
testing.

## What a pattern match means

A match means:

> The completed price history satisfies this versioned geometric definition as
> of this date.

It does not mean:

- the stock will rise;
- the pattern has a known probability of success;
- the stock is fundamentally attractive;
- the current price offers acceptable risk/reward;
- the learner should enter a trade; or
- the thresholds are optimal.

SEBI's investor material describes technical analysis as analysis of price
movements, trends, and volume. The course keeps that evidence separate from
fundamental due diligence and from personalized action. See
[SEBI's technical-versus-fundamental analysis explainer](https://investor.sebi.gov.in/tech_fund_analysis.html)
and [due-diligence guidance](https://investor.sebi.gov.in/due_diligence.html).

## Shared data contract

### Required inputs

- adjusted daily `open`, `high`, `low`, and `close`;
- completed trading-session date;
- trustworthy daily volume where available;
- symbol and sector;
- Nifty 50 benchmark close;
- frozen universe membership and coverage metadata; and
- at least 260 completed sessions for the full teaching view.

The prototype must state its corporate-action adjustment policy. If reliable
adjusted OHLC is unavailable, geometric patterns are disabled rather than
calculated across artificial split gaps.

### Shared derived fields

- 20-session average true range, `ATR20`;
- 20-session median volume;
- 50-DMA and 200-DMA;
- 126-session return relative to Nifty 50;
- 20-session realized volatility; and
- confirmed swing highs and swing lows.

### Confirmed pivots

A teaching-default pivot uses `k = 3`:

- a pivot high at session `t` has the highest high from `t-3` through `t+3`;
- a pivot low at session `t` has the lowest low from `t-3` through `t+3`; and
- ties use the earliest occurrence and are disclosed.

A pivot is not available until three later sessions have completed. A detector
running as of date `D` may therefore use pivots only through `D-3`. This delay
must be visible because ignoring it creates look-ahead bias.

### Price tolerance and breakout buffer

Teaching defaults:

```text
touch_tolerance = max(0.75 × ATR20, 1.0% × close)
breakout_buffer = 0.25 × ATR20
```

ATR makes the same geometric idea comparable across securities with different
prices and volatility. The percentage floor prevents extremely quiet periods
from producing unrealistically precise lines.

These values are starting definitions, not optimized parameters. The learner
may view a sensitivity comparison, but the core dashboard does not search for
the threshold with the best historical return.

### Fresh breakout event

A positive breakout is fresh only when:

```text
close_today > boundary_today + breakout_buffer
and
close_previous <= boundary_previous + breakout_buffer
```

The event uses a completed close. An intraday move above a boundary is shown as
“testing,” not “breakout.”

### Common context, not common gates

Each detected structure also shows:

- close relative to 50-DMA and 200-DMA;
- 126-session relative strength versus Nifty 50;
- sector relative strength;
- market breadth and regime context;
- volume divided by 20-session median volume, when trustworthy;
- distance from the detected boundary in ATR units; and
- data-quality flags.

These fields are context. They do not silently change the pattern definition.
If a later version adds a trend or volume filter, it receives a new
methodology version.

## Pattern 1 — converging triangle breakout

### Plain-language idea

Recent swing highs form a flat or falling upper boundary while swing lows form
a rising lower boundary. The space between them contracts. A completed close
then moves above the upper boundary.

The family may be labeled:

- **ascending triangle** when the upper boundary is approximately flat; or
- **symmetrical triangle** when the upper boundary falls while the lower
  boundary rises.

The course does not add descending-triangle downside screens.

### Teaching-default search

- candidate windows: 30-60 completed sessions;
- at least two confirmed pivot highs and two confirmed pivot lows;
- fit a line to pivot highs and another to pivot lows;
- upper boundary is flat or falling;
- lower boundary is rising;
- boundaries do not cross inside the candidate window;
- end-of-window distance between boundaries is 40-80% of its starting
  distance;
- at least 70% of closes remain inside the two boundaries after tolerance; and
- a fresh close occurs above the upper boundary plus breakout buffer.

Boundary movement is compared in ATR units across the full window:

- approximately flat: absolute movement is no more than `1 × median ATR20`;
- meaningfully rising/falling: movement is at least `0.5 × median ATR20`.

### Required visual

- candlestick or OHLC chart over the complete candidate window;
- confirmed pivot highs and lows;
- fitted upper and lower boundaries;
- shaded region between the boundaries;
- breakout buffer above the upper line;
- breakout-session marker; and
- note that the last three sessions cannot create confirmed pivots.

### Required diagnostics

- window start and end;
- pivot-high and pivot-low counts;
- upper and lower boundary movement in ATR units;
- starting and ending boundary width;
- compression ratio;
- percentage of closes inside the tolerated structure;
- breakout distance in ATR units;
- volume ratio, if available; and
- every failed criterion.

### Typical rejection reasons

- only one usable high or low;
- boundaries do not converge;
- lower boundary is flat or falling;
- excessive closes occur outside the shape;
- the lines cross before the proposed breakout;
- the close only touched the line; or
- the apparent final pivot was not yet confirmed.

## Pattern 2 — rectangle/base breakout

### Plain-language idea

Price repeatedly tests an approximately horizontal ceiling and floor without
leaving the range. A completed close then moves above the ceiling.

### Teaching-default search

- candidate windows: 20-60 completed sessions;
- at least two confirmed pivot highs and two confirmed pivot lows;
- fit upper and lower boundaries to those pivots;
- total movement of each boundary is no more than `1 × median ATR20`;
- median range width is between `2 ×` and `10 × median ATR20`;
- at least 80% of closes remain inside the range after tolerance;
- the upper boundary remains above the lower boundary throughout; and
- a fresh close occurs above the upper boundary plus breakout buffer.

The lower bound on range width prevents ordinary noise from being labeled a
base. The upper bound prevents a very wide, unstable market from being called
a rectangle merely because its outer extremes are horizontal.

### Required visual

- candidate-window price chart;
- confirmed touches on resistance and support;
- horizontal fitted boundaries;
- tolerated range shaded lightly;
- breakout buffer and session marker; and
- optional volume panel when the source is reliable.

### Required diagnostics

- window length;
- touch counts;
- boundary drift in ATR units;
- range width in ATR units and percentage terms;
- percentage of closes inside the range;
- breakout distance;
- volume ratio; and
- failed criteria.

### Typical rejection reasons

- one extreme created the apparent range;
- support or resistance slopes too much;
- too many closes occur outside the range;
- the range is noise-sized or excessively wide;
- the breakout is intraday only; or
- adjusted-price quality is insufficient.

## Pattern 3 — bull flag breakout

### Plain-language idea

An observable upward impulse is followed by a shorter, controlled flat or
downward consolidation. A completed close then moves above the consolidation's
upper boundary.

“Bull” is the conventional shape name. It does not express a course forecast.

### Teaching-default search

#### Impulse leg

- duration: 5-15 completed sessions;
- start at a confirmed local low or the lowest close in the candidate impulse
  window;
- end at the highest close before the flag begins;
- gain is at least 8% and at least `4 × ATR20` measured at impulse start; and
- the impulse contains more advancing than declining sessions.

#### Flag

- duration: 5-15 completed sessions after the impulse;
- retraces 20-55% of the impulse;
- fitted upper and lower boundaries are flat or falling;
- the two boundary movements differ by no more than `1 × median ATR20`, so the
  channel is approximately parallel;
- at least 70% of closes remain inside the tolerated channel; and
- flag duration does not exceed impulse duration by more than five sessions.

#### Breakout

- a fresh completed close occurs above the flag's upper boundary plus breakout
  buffer; and
- the close has not already fallen below the 55% maximum retracement before
  breakout.

### Required visual

- impulse start and peak markers;
- impulse height;
- flag-window shading;
- fitted upper and lower flag boundaries;
- retracement band;
- breakout buffer and session marker; and
- optional volume panel.

### Required diagnostics

- impulse duration, percentage move, and ATR-normalized move;
- advancing/declining session count during the impulse;
- flag duration;
- retracement percentage;
- upper and lower channel movement;
- percentage of closes inside the flag;
- breakout distance;
- volume ratio; and
- failed criteria.

### Typical rejection reasons

- no sufficiently distinct impulse;
- pullback retraces too little or too much;
- consolidation expands rather than stays parallel;
- breakout occurs after the structure has become stale;
- close remains inside the channel; or
- a single gap accounts for nearly the entire impulse.

## Detector output contract

The dashboard should show one row per candidate and let the learner open its
visual evidence.

Required columns:

```text
symbol
sector
as_of_date
pattern_family
pattern_status
window_start
window_end
breakout_level
close
distance_atr
rs_126d_vs_nifty
market_context
volume_ratio_or_na
data_quality
methodology_version
```

### Pattern status

- **forming** — geometry passes, no completed close has broken the boundary;
- **testing** — intraday high crossed but completed close did not;
- **triggered** — fresh completed-close rule passes;
- **failed after trigger** — within five completed sessions, close returns
  inside the boundary beyond tolerance; or
- **invalid** — data quality or a structural rule fails.

“Failed after trigger” is a later descriptive label. It must not rewrite the
original as-of record.

### No composite score

The core course does not produce a confidence, quality, or buy score. It shows
a criteria matrix:

| Criterion | Pass/fail | Observed value | Required value |
|---|---|---:|---:|
| Minimum pivots |  |  |  |
| Boundary geometry |  |  |  |
| Containment |  |  |  |
| Breakout close |  |  |  |
| Data quality |  |  |  |

This makes disagreement inspectable. A learner can see whether a near-match
failed because of one missing pivot, poor containment, or no completed close.

## Quantitative plus visual acceptance rule

A candidate enters the learner's observation shortlist only if:

1. the program's criteria matrix passes;
2. the overlay uses the same pivots and boundaries as the calculations;
3. the learner can point to every required geometric feature;
4. the as-of date and methodology version are visible; and
5. the learner writes one reason the match could be misleading.

If the numeric detector and visual overlay disagree, the candidate is a
software/data bug to investigate—not an invitation to override the program by
eye.

## Teaching fixtures required

For each family, prepare:

- one clean passing example;
- one near-match rejected for geometry;
- one apparent breakout rejected because only the intraday high crossed;
- one example with a corporate-action or missing-data issue; and
- one candidate whose market/sector context contradicts the pattern.

Each fixture includes a hand-auditable criteria table. Synthetic fixtures
should be used for calculation tests; dated licensed examples may be used for
product walkthroughs.

## Questions for prototype validation

- Can a beginner explain why confirmed pivots arrive with a delay?
- Does ATR normalization help or add too much cognitive load?
- Can learners distinguish forming, testing, triggered, and failed?
- Does a pass/fail criteria matrix reduce subjective overrides?
- Which of the three families generates the most false visual confidence?
- Can learners explain why pattern detection is separate from outcome
  prediction?
- Can the complete Module 4 fit into 60 minutes without rushing relative
  strength?

Thresholds should be changed only to improve definitional clarity or data
robustness during this curriculum phase. Outcome optimization belongs in a
later research and backtesting course.
