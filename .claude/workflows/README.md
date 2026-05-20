# Workflows

Sequenced playbooks that chain existing agents and skills into product
journeys. Each `.md` here is a markdown procedure an agent (or human)
can follow step by step.

Distinction:

| Concept | Purpose | Lives in |
|---|---|---|
| **Skill** | A self-contained slash command with its own scripts/resources. | `.claude/skills/<name>/SKILL.md` |
| **Agent** | A subagent definition with a system prompt + tool list. | `.claude/agents/<name>.md` |
| **Workflow** | A *procedure* that names which agents/skills to invoke and in what order to deliver a particular outcome. | `.claude/workflows/<name>.md` |

A workflow doesn't run anything itself — it's instructions to Claude (or
a human) about which existing primitives to compose.

## How to invoke

Reference a workflow by name in a prompt:

> "Follow `.claude/workflows/ship-feature.md` for this change."

Or invoke it via the `Skill` tool if you wrap it as a skill later.

## Scaffolded workflows

| File | Purpose | Status |
|---|---|---|
| `ship-feature.md` | Planning → implementation → test → security review → deploy. | scaffold |
| `triage-incident.md` | Production breakage: read logs → reproduce → fix → postmortem. | scaffold |
| `close-research.md` | Take a `tasks/<name>/` from active to RESULTS+archive. | scaffold |

Add new workflows as patterns emerge — don't create them speculatively.
