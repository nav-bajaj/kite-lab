import { preload } from "swr";
import {
  getPortfolio,
  getHoldings,
  getMetrics,
  getEquityCurve,
  getTradeSummary,
  getPositions,
  getMarketStatus,
  getRebalanceStatus,
} from "./api-client";
import type { UniverseId } from "./types";

// Warm the SWR cache for a route's primary data before the user navigates,
// so the destination page renders from cache on click. Next.js already
// prefetches the route JS on hover; this covers the data.
//
// Keys MUST mirror the corresponding hooks in hooks.ts. A mismatch only
// means a missed warm (the hook just fetches normally), never wrong data.
type Preloader = (universe: UniverseId) => void;

// A Map (not an object literal) so the dynamic `href` lookup isn't an
// object-injection sink — the value is only ever invoked, never assigned.
const ROUTE_PRELOADERS = new Map<string, Preloader>([
  [
    "/dashboard",
    (u) => {
      preload(["portfolio", u], () => getPortfolio(u));
      preload(["holdings", u], () => getHoldings(u));
    },
  ],
  [
    "/performance",
    (u) => {
      preload(["metrics", u], () => getMetrics(u));
      preload(["equity-curve", u], () => getEquityCurve(u));
    },
  ],
  [
    "/positions",
    (u) => {
      preload(["positions", u], () => getPositions(u));
      preload("market-status", () => getMarketStatus());
    },
  ],
  [
    "/rebalance",
    (u) => {
      preload(["rebalance-status", u], () => getRebalanceStatus(u));
    },
  ],
  [
    "/trades",
    (u) => {
      preload(["trade-summary", u], () => getTradeSummary(u));
    },
  ],
]);

export function preloadRoute(href: string, universe: UniverseId) {
  ROUTE_PRELOADERS.get(href)?.(universe);
}
