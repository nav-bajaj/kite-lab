# Course development exploration

This folder is the working study for a beginner course for Marketworks
subscribers. It does not implement a course platform or publish investment
recommendations.

## Recommended concept

**Marketworks Foundations: From SIP to Stock Sense**

A practical course for a mutual-fund investor who wants to understand Indian
capital markets, evaluate stocks without depending on tips, read the current
market through Marketworks, and build a rules-based paper portfolio on their
own device with Codex or Claude Code.

The core learning loop is:

> **Observe on Marketworks -> explain in plain English -> test a rule -> reflect**

## Documents

- `PLAN.md` — product thesis, scope, experience principles, and decisions.
- `RESEARCH.md` — repo audit, audience evidence, market context, and source log.
- `CURRICULUM.md` — detailed eight-module course blueprint.
- `AI_PORTFOLIO_LAB.md` — provider-neutral Codex/Claude Code capstone design.
- `PILOT.md` — MVP, experiments, instrumentation, and success criteria.
- `TASKS.md` — phased path from study to a validated pilot.
- `_meta.yml` — machine-readable initiative metadata.

## Current recommendation

Run a 20-person, four-week pilot before building a full course CMS. Use
build-time course pages under `/library/courses`, local progress for the pilot,
the existing Learn explainers as prerequisites, and a downloadable AI lab
folder. The pilot should use delayed or synthetic data and paper portfolios
only.

Any public AI portfolio lab, strategy template, model-portfolio comparison, or
performance claim needs legal/compliance review against the current SEBI
Research Analyst framework before publication.
