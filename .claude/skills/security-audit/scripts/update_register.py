#!/usr/bin/env python3
"""Propose risk-register.md updates from an audit findings.json.

This script does NOT mutate risk-register.md directly. It emits a
markdown patch that a human (or the LLM running /security-audit)
reviews and applies. Closure of register rows is always human-only.

What it produces (printed to stdout, also written to a file):

    # Proposed register changes — <date>

    ## Bump "Last reviewed" on existing rows
    - R-002: Last reviewed -> <today>  (re-confirmed by pip-audit)

    ## Proposed new rows
    | ID | Title | Asset | Sev | Likelihood | Status | ... |
    |...| ... | ... | ... |...|...|...|

    ## Suppressions to add (paste into tools/security/suppressions.yml)
    - fingerprint: "abc123..."
      rule: "..."
      ...

Usage:
    update_register.py
        --findings reports/security/<date>/findings.json
        --register docs/security/risk-register.md
        --output  reports/security/<date>/register-proposal.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path


def load_existing_ids(register_md: Path) -> set[str]:
    """Find every R-XXX referenced in the register so we can pick the next free ID."""
    if not register_md.exists():
        return set()
    txt = register_md.read_text(encoding="utf-8")
    return set(re.findall(r"\bR-\d{3}\b", txt))


def next_free_id(existing: set[str], start: int = 13) -> str:
    """Pick the next free R-XXX, starting at R-{start:03d}."""
    n = start
    while f"R-{n:03d}" in existing:
        n += 1
    return f"R-{n:03d}"


def severity_to_register_sev(sev: str) -> str:
    """Map scanner-normalized severity → register's sev rubric."""
    return {
        "critical": "Critical",
        "high": "High",
        "medium": "Med",
        "low": "Low",
        "info": "Low",
    }.get(sev, "Med")


def cluster_findings(findings: list[dict]) -> dict[str, list[dict]]:
    """Group findings by (rule, file) so we propose ONE register row per cluster
    rather than spamming with per-line rows."""
    buckets: dict[str, list[dict]] = defaultdict(list)
    for f in findings:
        key = f"{f['rule']}|{f['file']}"
        buckets[key].append(f)
    return buckets


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--findings", required=True, type=Path)
    ap.add_argument("--register", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()

    payload = json.loads(args.findings.read_text(encoding="utf-8"))
    new_findings = payload.get("diff", {}).get("new", [])
    carried = payload.get("diff", {}).get("carried_over", [])
    resolved = payload.get("diff", {}).get("resolved", [])
    expiring = payload.get("expiring_suppressions", [])

    today = date.today().isoformat()
    existing_ids = load_existing_ids(args.register)

    lines: list[str] = [f"# Proposed register changes — {today}", ""]

    # ---- Bump "Last reviewed" on rows that still apply ---------------------
    # Heuristic: a register row is "still applies" if any carried-over finding
    # references its content (we look for register row IDs in scanner messages,
    # or fall back to a default suggestion).
    if carried:
        lines += [
            "## Bump `Last reviewed` (re-confirmed by this run)",
            "",
            "Carried-over findings indicate these risks are still present. Bump",
            f"`Last reviewed` to `{today}` on the matching rows. (Human verifies the mapping.)",
            "",
        ]
        seen: set[str] = set()
        for f in carried[:50]:  # cap output
            rule = f["rule"]
            if rule in seen:
                continue
            seen.add(rule)
            lines.append(f"- rule `{rule}` at `{f['file']}:{f['line']}`")
        if len(carried) > 50:
            lines.append(f"  …and {len(carried) - 50} more")
        lines.append("")

    # ---- Propose new rows --------------------------------------------------
    if new_findings:
        lines += [
            "## Proposed new register rows",
            "",
            "One row per (rule × file) cluster. Severity inherited from scanner.",
            "Assign the suggested `R-XXX` ID or pick your own. Paste into",
            "`docs/security/risk-register.md`.",
            "",
            "| ID (suggested) | Title | Asset | Sev | Likelihood | Status | Control | Opened |",
            "|---|---|---|---|---|---|---|---|",
        ]
        clusters = cluster_findings(new_findings)
        ids_used = set(existing_ids)
        for key, items in sorted(clusters.items(), key=lambda kv: -len(kv[1])):
            rule, file = key.split("|", 1)
            rep = items[0]
            new_id = next_free_id(ids_used)
            ids_used.add(new_id)
            title = f"{rule} at `{file}`"
            if len(items) > 1:
                title += f" (×{len(items)} occurrences)"
            sev = severity_to_register_sev(rep["severity"])
            asset = "(triage required)"
            lines.append(
                f"| {new_id} | {title} | {asset} | {sev} | Med | Open | "
                f"Triage needed — see report | {today} |"
            )
        lines.append("")

    # ---- Suppressions to add for newly-suppressed accepted-risk findings ---
    if new_findings:
        lines += [
            "## Proposed suppression entries (if accepted)",
            "",
            "Only paste these into `tools/security/suppressions.yml` AFTER you've",
            "decided the finding is accepted/false-positive AND opened the matching",
            "register row.",
            "",
            "```yaml",
        ]
        for f in new_findings[:30]:
            lines.append(f"- fingerprint: \"{f['fingerprint']}\"")
            lines.append(f"  rule: \"{f['rule']}\"")
            lines.append(f"  scanner: \"{f['scanner']}\"")
            lines.append(f"  file: \"{f['file']}\"")
            lines.append(f"  line: {f['line']}")
            lines.append(f"  register: \"R-NEW\"   # set to actual ID after row created")
            lines.append(f"  justification: \"<fill in>\"")
            lines.append(f"  opened: \"{today}\"")
            lines.append(f"  expires: \"<today + 1y>\"")
            lines.append("")
        if len(new_findings) > 30:
            lines.append(f"# … {len(new_findings) - 30} more — see findings.json")
        lines.append("```")
        lines.append("")

    # ---- Resolved findings -------------------------------------------------
    if resolved:
        lines += [
            "## Resolved since last audit",
            "",
            "These findings were present last time and are not present this run.",
            "If they map to register rows in `Mitigating` status, consider flipping",
            "to `Closed` after manual verification.",
            "",
        ]
        for f in resolved[:30]:
            lines.append(f"- `{f['rule']}` at `{f['file']}:{f['line']}` ({f['scanner']})")
        if len(resolved) > 30:
            lines.append(f"  …and {len(resolved) - 30} more")
        lines.append("")

    # ---- Expiring suppressions ---------------------------------------------
    if expiring:
        lines += [
            "## Suppressions past expiry — re-review now",
            "",
            "These entries in `suppressions.yml` have `expires` < today. The",
            "finding is still being suppressed, but the suppression itself is",
            "stale. Re-confirm the justification or remove the entry.",
            "",
        ]
        for s in expiring:
            lines.append(
                f"- `{s.get('rule')}` at `{s.get('file')}:{s.get('line')}` "
                f"(register {s.get('register')}, opened {s.get('opened')}, expired {s.get('expires')})"
            )
        lines.append("")

    if not (new_findings or carried or resolved or expiring):
        lines += [
            "## No changes proposed",
            "",
            "Clean run. Bump `Last reviewed` on any rows you re-verified manually.",
            "",
        ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines)
    args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
