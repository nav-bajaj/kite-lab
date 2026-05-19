import { Universe, UniverseId } from "./types";

// Display names for the universe selector. Internal IDs (left of `:`) are
// stable references used by the backend, DB rows, sync scripts, and
// CSV columns — never rename them. Only update `name`/`shortName`/
// `description` if a portfolio is rebranded for users.
//
// Ordering here drives the order of the universe selector dropdown.
// The 4 production portfolios come first (those are what the daily
// pipeline builds and most users will look at); the 3 alt-universe
// momentum portfolios follow.
export const UNIVERSES: Record<UniverseId, Universe> = {
  om25_v3: {
    id: "om25_v3",
    name: "Quality Momentum",
    shortName: "Quality",
    description: "Regime-aware quality momentum on Nifty 250 — defensive rotation in bear regimes",
    stocks: 25,
    riskProfile: "Quality-tilt, regime-adaptive",
  },
  tl25_v3: {
    id: "tl25_v3",
    name: "Trend Leaders",
    shortName: "Trend",
    description: "Pure trend-following on NSE 500 — trend quality + drawdown control + 63d momentum",
    stocks: 25,
    riskProfile: "Trend-following",
  },
  l6_v2: {
    id: "l6_v2",
    name: "Core Momentum",
    shortName: "Core",
    description: "Flagship 6-month momentum on NSE 500 — top 24 weekly-rebalanced",
    stocks: 24,
    riskProfile: "Growth-focused",
  },
  combo_defensive: {
    id: "combo_defensive",
    name: "Defensive Blend",
    shortName: "Defensive",
    description: "50/50 Core + Quality blend with 50% cash in bear regimes — drawdown-reduced",
    stocks: 24,
    riskProfile: "Drawdown-reduced",
  },
  nse500: {
    id: "nse500",
    name: "Broad Momentum",
    shortName: "Broad",
    description: "Legacy NSE 500 momentum — research baseline",
    stocks: 499,
    riskProfile: "Growth-focused",
  },
  nifty250: {
    id: "nifty250",
    name: "Mid-Cap Momentum",
    shortName: "Mid-Cap",
    description: "Nifty 250 momentum — large + mid-cap blend",
    stocks: 250,
    riskProfile: "Balanced",
  },
  nifty100: {
    id: "nifty100",
    name: "Large-Cap Momentum",
    shortName: "Large-Cap",
    description: "Nifty 100 momentum — large-cap only, lower volatility",
    stocks: 100,
    riskProfile: "Conservative",
  },
};

// Default landing universe — pick the flagship production portfolio.
export const DEFAULT_UNIVERSE: UniverseId = "l6_v2";

export function getUniverse(id: UniverseId): Universe {
  // eslint-disable-next-line security/detect-object-injection -- id is a typed UniverseId literal; UNIVERSES is a closed Record
  return UNIVERSES[id];
}

export function isValidUniverse(id: string): id is UniverseId {
  return id in UNIVERSES;
}

export const UNIVERSE_IDS = Object.keys(UNIVERSES) as UniverseId[];
