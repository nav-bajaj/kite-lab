import type { LearnExplainer } from "./_types";

import { stressScore } from "./stress-score";
import { regime } from "./regime";
import { sectorRs } from "./sector-rs";
import { sectorBreadth } from "./sector-breadth";
import { mcclellanOscillator } from "./mcclellan-oscillator";
import { pctAbove200dma } from "./pct-above-200dma";
import { dispersion } from "./dispersion";
import { coiledSpring } from "./coiled-spring";
import { breakout } from "./breakout";
import { rsLeader } from "./rs-leader";
import { drawdown } from "./drawdown";
import { vix } from "./vix";
import { concentration } from "./concentration";
import { sustainedUptrend } from "./sustained-uptrend";
import { rsRank } from "./rs-rank";
import { trendScore } from "./trend-score";
import { extensionRisk } from "./extension-risk";
import { volumeConfirmation } from "./volume-confirmation";
import { momentumConsistency } from "./momentum-consistency";
import { atr } from "./atr";
import { beta } from "./beta";
import { liquidity } from "./liquidity";

const ALL: LearnExplainer[] = [
  stressScore,
  regime,
  sectorRs,
  sectorBreadth,
  mcclellanOscillator,
  pctAbove200dma,
  dispersion,
  coiledSpring,
  breakout,
  rsLeader,
  drawdown,
  vix,
  concentration,
  sustainedUptrend,
  // insights_v2 — stock-level analytics
  rsRank,
  trendScore,
  extensionRisk,
  volumeConfirmation,
  momentumConsistency,
  atr,
  beta,
  liquidity,
];

export const EXPLAINERS: Record<string, LearnExplainer> = Object.fromEntries(
  ALL.map((e) => [e.slug, e]),
);

export const EXPLAINER_SLUGS: string[] = ALL.map((e) => e.slug);

export const EXPLAINERS_BY_CATEGORY: Record<string, LearnExplainer[]> =
  ALL.reduce<Record<string, LearnExplainer[]>>((acc, e) => {
    (acc[e.category] ||= []).push(e);
    return acc;
  }, {});
