/**
 * Glossary of terms used across Marketworks Insights.
 *
 * Convention: one entry per term, plain-English definition aimed at a
 * smart retail reader who doesn't have a quant background. Keep
 * definitions to 1-3 sentences. Use `related` to point at a learn
 * explainer when the term has a dedicated page; the glossary page
 * renders those as deep-links.
 */

export type GlossaryEntry = {
  /** The display term, used to render the heading. */
  term: string;
  /** URL-safe anchor (slug). Lowercase, hyphenated. */
  anchor: string;
  /** Categorical bucket for grouping on the page (display only). */
  bucket:
    | "market-state"
    | "breadth-momentum"
    | "patterns"
    | "math"
    | "flows-structure"
    | "general";
  /** 1-3 sentence definition. */
  definition: string;
  /** Slug of a related learn explainer (if any). */
  related?: string;
};

export const GLOSSARY: GlossaryEntry[] = [
  // ─────────── market-state ───────────
  {
    term: "VIX (India VIX)",
    anchor: "vix",
    bucket: "market-state",
    definition:
      "NSE's volatility index — annualised expected volatility of Nifty 50 over the next 30 days, computed from option prices. Often called the 'fear index'; a better mental model is 'uncertainty index'.",
    related: "vix",
  },
  {
    term: "Regime",
    anchor: "regime",
    bucket: "market-state",
    definition:
      "A 4-state classification of overall market conditions: TREND_BULL, DRIFT, STRETCHED, STRESS. Conditioning any other signal on regime is usually the single biggest interpretive improvement.",
    related: "regime",
  },
  {
    term: "Stress score",
    anchor: "stress-score",
    bucket: "market-state",
    definition:
      "A 0–100 composite that blends VIX percentile, drawdown depth, % of stocks below 200-DMA, and dispersion z-score. 0 = calm, 100 = panic.",
    related: "stress-score",
  },
  {
    term: "Drawdown",
    anchor: "drawdown",
    bucket: "market-state",
    definition:
      "Percentage decline from the most recent peak. Always negative or zero. Tells you what the journey feels like, not just where you ended up.",
    related: "drawdown",
  },
  {
    term: "Persistence",
    anchor: "persistence",
    bucket: "market-state",
    definition:
      "How many consecutive trading days the current regime has lasted. A 60-day-old TREND_BULL behaves differently from a 5-day-old one — late regimes often have weaker internals.",
  },

  // ─────────── breadth-momentum ───────────
  {
    term: "Breadth",
    anchor: "breadth",
    bucket: "breadth-momentum",
    definition:
      "How many stocks are moving together. Different from the index level, which is a weighted average that can hide narrow participation.",
  },
  {
    term: "% above 200-DMA",
    anchor: "pct-above-200dma",
    bucket: "breadth-momentum",
    definition:
      "The share of stocks in our NSE 500 universe trading above their 200-day moving average. The most widely watched breadth gauge.",
    related: "pct-above-200dma",
  },
  {
    term: "McClellan oscillator",
    anchor: "mcclellan",
    bucket: "breadth-momentum",
    definition:
      "Breadth momentum: a 19-day EMA minus a 39-day EMA of (advances minus declines). Captures whether breadth is accelerating or fading.",
    related: "mcclellan-oscillator",
  },
  {
    term: "Dispersion",
    anchor: "dispersion",
    bucket: "breadth-momentum",
    definition:
      "Cross-sectional standard deviation of daily returns — how scattered stocks are around the average. High = stock-picker's market; low = everything moving together.",
    related: "dispersion",
  },
  {
    term: "Thrust day",
    anchor: "thrust-day",
    bucket: "breadth-momentum",
    definition:
      "A session where >80% of a universe (whole index or one sector) moved in the same direction. Often marks the early phase of a durable up-move.",
  },
  {
    term: "Advance/decline (A/D)",
    anchor: "advance-decline",
    bucket: "breadth-momentum",
    definition:
      "Count of stocks closing up minus count closing down. The raw fuel for McClellan and other breadth-momentum measures.",
  },
  {
    term: "Relative strength (RS)",
    anchor: "rs",
    bucket: "breadth-momentum",
    definition:
      "An asset's return minus a benchmark's return over the same window. Positive RS = outperformed. We compute it for sectors vs Nifty and for individual stocks vs Nifty.",
    related: "sector-rs",
  },

  // ─────────── patterns ───────────
  {
    term: "Breakout",
    anchor: "breakout",
    bucket: "patterns",
    definition:
      "A close above a recent significant high — most commonly the 20-day high, but can extend to 52-week or multi-year highs. Longer base = stronger breakout.",
    related: "breakout",
  },
  {
    term: "Coiled spring",
    anchor: "coiled-spring",
    bucket: "patterns",
    definition:
      "A stock in a tight trading range above both its 50- and 200-DMA, with realised volatility in its own bottom 25%. Energy compressing; resolution can go either way.",
    related: "coiled-spring",
  },
  {
    term: "RS leader",
    anchor: "rs-leader",
    bucket: "patterns",
    definition:
      "Among the top 25 NSE 500 stocks by 6-month return vs Nifty. The screen the Quality Momentum and Trend Leaders portfolios are built on.",
    related: "rs-leader",
  },
  {
    term: "Golden cross / death cross",
    anchor: "golden-cross",
    bucket: "patterns",
    definition:
      "When a stock's 50-DMA crosses above (golden) or below (death) its 200-DMA. A slow signal; widely watched precisely because so many traders watch it.",
  },
  {
    term: "Pullback to 50-DMA",
    anchor: "pullback-50dma",
    bucket: "patterns",
    definition:
      "An uptrending stock dipping back to touch its 50-day average. Classic 'entry on weakness' setup in TREND_BULL conditions.",
  },
  {
    term: "Stretched",
    anchor: "stretched",
    bucket: "patterns",
    definition:
      "A stock trading more than 20% above its 200-DMA. Historically a mean-reversion zone — not a guaranteed reversal, but a context where forward returns thin out.",
  },

  // ─────────── math / statistics ───────────
  {
    term: "Moving average (DMA / SMA / EMA)",
    anchor: "moving-average",
    bucket: "math",
    definition:
      "Average of closing prices over a trailing window. Simple (SMA) averages equally; exponential (EMA) weights recent prices more. 50-DMA, 200-DMA are widely watched levels.",
  },
  {
    term: "Percentile",
    anchor: "percentile",
    bucket: "math",
    definition:
      "Rank of a value within a historical distribution, expressed 0–100. A VIX 92nd percentile reading means VIX is higher than 92% of its trailing 252-day values.",
  },
  {
    term: "Quartile / quintile",
    anchor: "quartile",
    bucket: "math",
    definition:
      "Splits a distribution into 4 (quartile) or 5 (quintile) equal buckets. Q4 of forward returns is the top 25% of outcomes; Q1 is the worst 25%.",
  },
  {
    term: "Z-score",
    anchor: "zscore",
    bucket: "math",
    definition:
      "How many standard deviations a value is from the mean. ±2 is typically called 'unusual'; ±3 is rare. Used inside the stress score and dispersion engine.",
  },
  {
    term: "Information coefficient (IC)",
    anchor: "ic",
    bucket: "math",
    definition:
      "Spearman rank correlation between a feature's value and the realised forward return. A simple measure of whether a signal predicts the order of outcomes. We require positive IC at a horizon before publishing forward-return claims.",
  },
  {
    term: "Conditional distribution / base rate",
    anchor: "base-rate",
    bucket: "math",
    definition:
      "The historical distribution of forward returns conditional on the market being in some state (e.g., 'when stress > 80, what does the next 20-day distribution look like'). The honest way to say 'historically' instead of cherry-picking.",
  },
  {
    term: "Median",
    anchor: "median",
    bucket: "math",
    definition:
      "The middle value of a distribution — 50% above, 50% below. We prefer median to mean for forward-return summaries because medians are robust to outliers (a single COVID day can swing means a lot).",
  },
  {
    term: "Realised volatility",
    anchor: "realised-vol",
    bucket: "math",
    definition:
      "Annualised standard deviation of recent returns. 'How bumpy has the ride been' — backward-looking, in contrast to VIX which is forward-looking.",
  },

  // ─────────── flows-structure ───────────
  {
    term: "FII (Foreign Institutional Investor)",
    anchor: "fii",
    bucket: "flows-structure",
    definition:
      "Non-Indian funds buying / selling Indian equities. NSE publishes daily net FII activity. Persistent flow signs are widely watched — large outflow days tend to coincide with stress.",
  },
  {
    term: "DII (Domestic Institutional Investor)",
    anchor: "dii",
    bucket: "flows-structure",
    definition:
      "Indian mutual funds, insurance companies, and banks. Their flows have grown structurally as Indian SIP money compounds; DII buying often offsets FII selling.",
  },
  {
    term: "Free-float / free-float market cap",
    anchor: "free-float",
    bucket: "flows-structure",
    definition:
      "The portion of a company's shares actually available to trade (excludes promoter, government, strategic holdings). NSE indices weight constituents by free-float, not total, market cap.",
  },
  {
    term: "Index weight",
    anchor: "index-weight",
    bucket: "flows-structure",
    definition:
      "A constituent's share of the cap-weighted index. HDFCBANK at ~11% means a 1% move in HDFCBANK moves the index by ~11 bps before considering other names.",
  },
  {
    term: "Concentration",
    anchor: "concentration",
    bucket: "flows-structure",
    definition:
      "How dependent today's index move is on a few large names. Top-3 share = 80% means three stocks drove the headline; top-3 share = 25% means the move was broadly shared.",
    related: "concentration",
  },
  {
    term: "Rebalance",
    anchor: "rebalance",
    bucket: "flows-structure",
    definition:
      "When the index methodology updates constituent membership or weights. Nifty 50 rebalances semi-annually (March/September); sector indices follow their own schedules.",
  },
  {
    term: "Factsheet",
    anchor: "factsheet",
    bucket: "flows-structure",
    definition:
      "NSE Indices' monthly one-page summary of an index — constituents, free-float market caps, weights, top contributors. Our weights database mirrors these factsheets.",
  },

  // ─────────── general ───────────
  {
    term: "NSE 500",
    anchor: "nse-500",
    bucket: "general",
    definition:
      "The 500 largest Indian companies by free-float market cap, listed on NSE. Our research universe — most of the breadth and pattern engines look across this set.",
  },
  {
    term: "NIFTY 50 / 100 / 250 / 500",
    anchor: "nifty-family",
    bucket: "general",
    definition:
      "Standard NSE size-tier indices. Nifty 50 is the largest 50; Nifty 100 adds 50 more; Nifty 250 is the broader mid-cap layer; Nifty 500 covers the broad market.",
  },
  {
    term: "Universe coverage",
    anchor: "coverage",
    bucket: "general",
    definition:
      "Percentage of a list (e.g., a sector's constituents) for which we have price data. A sector with <70% coverage is flagged as 'partial' — its breadth signals get a confidence asterisk.",
  },
  {
    term: "Survivorship bias",
    anchor: "survivorship",
    bucket: "general",
    definition:
      "When a universe is defined by 'companies that exist today', historical analysis automatically excludes the losers that delisted. A real risk in long-history studies; we flag it where relevant.",
  },
  {
    term: "Watchlist",
    anchor: "watchlist",
    bucket: "general",
    definition:
      "A named list of names that fit a quant-defined setup today. Updated daily. We publish 5: Breakouts, RS Leaders, Coiled Springs, Stretched, Recent Breakdowns.",
  },
  {
    term: "T-1 / T-2",
    anchor: "t-minus",
    bucket: "general",
    definition:
      "Common short-hand for 'one trading day ago' (T-1) or 'two trading days ago' (T-2). Often used to flag that a data source publishes with a lag.",
  },

  // ─────────── insights_v2 stock-level terms ───────────
  {
    term: "ATR (Average True Range)",
    anchor: "atr",
    bucket: "math",
    definition:
      "The average size of a stock's daily trading range over 14 days, including overnight gaps. We show it as a % of price (ATR %) so names of any price are comparable. It measures the size of moves, not their direction.",
    related: "atr",
  },
  {
    term: "Beta",
    anchor: "beta",
    bucket: "math",
    definition:
      "How much a stock tends to move when the market moves, measured against Nifty 50 over 60 days. Beta 1 moves with the index; 1.5 amplifies it; 0.6 dampens it. Captures market-linked movement only, not company-specific risk.",
    related: "beta",
  },
  {
    term: "RSI (Relative Strength Index)",
    anchor: "rsi",
    bucket: "math",
    definition:
      "A 0-100 momentum oscillator (14-day) comparing the size of recent up-moves to down-moves. High RSI means the stock has been rising persistently. Unrelated to RS rank, which compares a stock to the whole universe.",
    related: "extension-risk",
  },
  {
    term: "Turnover",
    anchor: "turnover",
    bucket: "flows-structure",
    definition:
      "The rupee value traded in a stock per day (price x volume), usually a 20-day average in Rs crore. We use it to bucket stocks into liquidity tiers - how easily a name can be traded.",
    related: "liquidity",
  },
  {
    term: "Inflection (momentum)",
    anchor: "inflection",
    bucket: "breadth-momentum",
    definition:
      "A large improvement in a stock's RS rank over ~21 trading days (e.g. rank 312 to 88). Purely an observation that the rank changed - in our validity study this cohort did not beat the baseline forward, so we attach no return claim.",
    related: "rs-rank",
  },
  {
    term: "Extension",
    anchor: "extension",
    bucket: "patterns",
    definition:
      "How far a stock has run above its own moving averages, measured in ATR units. A descriptive state ('stretched vs its own history'), banded Low/Moderate/High/Very high. Extended names did not historically underperform - it is not a mean-reversion signal.",
    related: "extension-risk",
  },
];

export const BUCKET_LABELS: Record<GlossaryEntry["bucket"], string> = {
  "market-state": "Market state",
  "breadth-momentum": "Breadth & momentum",
  "patterns": "Patterns",
  "math": "Math & statistics",
  "flows-structure": "Flows & structure",
  "general": "General",
};
