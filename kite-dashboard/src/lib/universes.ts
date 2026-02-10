import { Universe, UniverseId } from "./types";

export const UNIVERSES: Record<UniverseId, Universe> = {
  nse500: {
    id: "nse500",
    name: "NSE 500",
    shortName: "NSE 500",
    description: "Full mid+large cap universe",
    stocks: 499,
    riskProfile: "Growth-focused",
  },
  nifty250: {
    id: "nifty250",
    name: "Nifty 250",
    shortName: "N250",
    description: "Large + mid-cap blend",
    stocks: 250,
    riskProfile: "Balanced",
  },
  nifty100: {
    id: "nifty100",
    name: "Nifty 100",
    shortName: "N100",
    description: "Large-cap only",
    stocks: 100,
    riskProfile: "Conservative",
  },
};

export const DEFAULT_UNIVERSE: UniverseId = "nse500";

export function getUniverse(id: UniverseId): Universe {
  return UNIVERSES[id];
}

export function isValidUniverse(id: string): id is UniverseId {
  return id in UNIVERSES;
}

export const UNIVERSE_IDS = Object.keys(UNIVERSES) as UniverseId[];
