import {
  EXPLAINERS,
  EXPLAINER_SLUGS,
  EXPLAINERS_BY_CATEGORY,
} from "@/content/insights/learn/_index";
import type { LearnExplainer } from "@/content/insights/learn/_types";

export type { LearnExplainer } from "@/content/insights/learn/_types";

export function getExplainer(slug: string): LearnExplainer | undefined {
  // eslint-disable-next-line security/detect-object-injection
  return EXPLAINERS[slug];
}

export function listExplainerSlugs(): string[] {
  return EXPLAINER_SLUGS;
}

export function listAllExplainers(): LearnExplainer[] {
  // eslint-disable-next-line security/detect-object-injection
  return EXPLAINER_SLUGS.map((s) => EXPLAINERS[s]);
}

export function explainersByCategory(): Record<string, LearnExplainer[]> {
  return EXPLAINERS_BY_CATEGORY;
}
