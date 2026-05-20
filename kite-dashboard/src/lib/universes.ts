import { Universe, UniverseId } from "./types";

// Display names for the universe selector. Internal IDs (left of `:`) are
// stable references used by the backend, DB rows, sync scripts, and
// CSV columns — never rename them. Only update `name`/`shortName`/
// `description` if a portfolio is rebranded for users.
//
// `clientVisible: true` means the universe is part of the public product
// surface; non-admin clients can see and select it. `false` means it's a
// legacy research universe — only admin-role users can pick it. The
// frontend filters here; the backend defense-in-depth check is a future
// follow-up (TASKS.md item 2.2).
//
// Ordering here drives the order of the universe selector dropdown.
// The 4 production portfolios come first; the 3 legacy ones follow
// (and are hidden from clients entirely).
export const UNIVERSES: Record<UniverseId, Universe> = {
  om25_v3: {
    id: "om25_v3",
    name: "Quality Momentum",
    shortName: "Quality",
    description: "Regime-aware quality momentum on Nifty 250 — defensive rotation in bear regimes",
    stocks: 25,
    riskProfile: "Quality-tilt, regime-adaptive",
    clientVisible: true,
  },
  tl25_v3: {
    id: "tl25_v3",
    name: "Trend Leaders",
    shortName: "Trend",
    description: "Pure trend-following on NSE 500 — trend quality + drawdown control + 63d momentum",
    stocks: 25,
    riskProfile: "Trend-following",
    clientVisible: true,
  },
  l6_v2: {
    id: "l6_v2",
    name: "Core Momentum",
    shortName: "Core",
    description: "Flagship 6-month momentum on NSE 500 — top 24 weekly-rebalanced",
    stocks: 24,
    riskProfile: "Growth-focused",
    clientVisible: true,
  },
  combo_defensive: {
    id: "combo_defensive",
    name: "Defensive Blend",
    shortName: "Defensive",
    description: "50/50 Core + Quality blend with 50% cash in bear regimes — drawdown-reduced",
    stocks: 24,
    riskProfile: "Drawdown-reduced",
    clientVisible: true,
  },
  nse500: {
    id: "nse500",
    name: "Broad Momentum",
    shortName: "Broad",
    description: "Legacy NSE 500 momentum — research baseline (admin-only)",
    stocks: 499,
    riskProfile: "Growth-focused",
    clientVisible: false,
  },
  nifty250: {
    id: "nifty250",
    name: "Mid-Cap Momentum",
    shortName: "Mid-Cap",
    description: "Nifty 250 momentum — large + mid-cap blend (admin-only)",
    stocks: 250,
    riskProfile: "Balanced",
    clientVisible: false,
  },
  nifty100: {
    id: "nifty100",
    name: "Large-Cap Momentum",
    shortName: "Large-Cap",
    description: "Nifty 100 momentum — large-cap only, lower volatility (admin-only)",
    stocks: 100,
    riskProfile: "Conservative",
    clientVisible: false,
  },
};

// Default landing universe — the flagship production portfolio. Same for
// clients and admins.
export const DEFAULT_UNIVERSE: UniverseId = "l6_v2";

export function getUniverse(id: UniverseId): Universe {
  // eslint-disable-next-line security/detect-object-injection -- id is a typed UniverseId literal; UNIVERSES is a closed Record
  return UNIVERSES[id];
}

export function isValidUniverse(id: string): id is UniverseId {
  return id in UNIVERSES;
}

export const UNIVERSE_IDS = Object.keys(UNIVERSES) as UniverseId[];

/** Universes visible to a given role. Admins see all 7; clients see only
 *  the 4 production portfolios. */
export function getVisibleUniverseIds(role: string | undefined): UniverseId[] {
  if (role === "admin") return UNIVERSE_IDS;
  return UNIVERSE_IDS.filter(
    // eslint-disable-next-line security/detect-object-injection -- id is from UNIVERSE_IDS (closed UniverseId set)
    (id) => UNIVERSES[id].clientVisible,
  );
}
