#!/usr/bin/env python3
"""Normalize raw scanner output into a uniform findings.json.

Reads each scanner's raw JSON from --input/<tool>.json and emits a flat
list of findings with a common schema:

    {
        "scanner": "...",
        "rule": "...",
        "severity": "critical|high|medium|low|info",
        "file": "<repo-relative-path>",
        "line": <int>,
        "message": "...",
        "snippet": "...",
        "fingerprint": "sha256(rule + file + line + snippet)[:16]",
    }

Also returns "diff" sections (new / carried_over / resolved / expiring)
when --previous is provided, and filters out suppressions from
tools/security/suppressions.yml when --suppressions is provided.

Usage:
    parse_findings.py
        --input   reports/security/<date>/raw/
        --output  reports/security/<date>/findings.json
        [--previous reports/security/<prior>/findings.json]
        [--suppressions tools/security/suppressions.yml]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml  # PyYAML is in requirements.txt
except ImportError:
    yaml = None  # type: ignore[assignment]


# --------------------------------------------------------------------------- #
# Per-scanner adapters
# --------------------------------------------------------------------------- #

SEV_MAP = {
    "CRITICAL": "critical",
    "HIGH": "high",
    "ERROR": "high",
    "MEDIUM": "medium",
    "WARNING": "medium",
    "LOW": "low",
    "INFO": "info",
    "NOTE": "info",
    "UNKNOWN": "medium",
}


def _fingerprint(rule: str, file: str, line: int, snippet: str) -> str:
    raw = f"{rule}|{file}|{line}|{snippet[:200]}".encode("utf-8", errors="replace")
    return hashlib.sha256(raw).hexdigest()[:16]


def _norm_severity(s: str | None) -> str:
    if not s:
        return "medium"
    return SEV_MAP.get(s.upper(), s.lower() if s.lower() in {"critical","high","medium","low","info"} else "medium")


def _load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None


def adapt_gitleaks(data: Any) -> list[dict]:
    out: list[dict] = []
    if not isinstance(data, list):
        return out
    for item in data:
        file = item.get("File", "")
        line = int(item.get("StartLine", 0) or 0)
        rule = item.get("RuleID", "gitleaks")
        snippet = item.get("Match", "") or item.get("Secret", "")
        out.append({
            "scanner": "gitleaks",
            "rule": rule,
            "severity": "critical",  # secrets are always critical
            "file": file,
            "line": line,
            "message": item.get("Description", rule),
            "snippet": snippet,
            "fingerprint": _fingerprint(rule, file, line, snippet),
        })
    return out


def adapt_ruff(data: Any) -> list[dict]:
    out: list[dict] = []
    if not isinstance(data, list):
        return out
    for item in data:
        code = item.get("code", "ruff")
        if not str(code).startswith("S"):
            continue  # only security subset
        file = item.get("filename", "")
        line = int((item.get("location") or {}).get("row") or 0)
        snippet = item.get("code", "")
        out.append({
            "scanner": "ruff",
            "rule": code,
            "severity": "medium",  # ruff S-rules don't carry severity; default medium
            "file": file,
            "line": line,
            "message": item.get("message", ""),
            "snippet": snippet,
            "fingerprint": _fingerprint(code, file, line, item.get("message", "")),
        })
    return out


def adapt_bandit(data: Any) -> list[dict]:
    out: list[dict] = []
    if not isinstance(data, dict):
        return out
    for r in data.get("results", []):
        rule = r.get("test_id", "bandit")
        file = r.get("filename", "")
        line = int(r.get("line_number", 0) or 0)
        snippet = r.get("code", "")[:300]
        sev = _norm_severity(r.get("issue_severity"))
        out.append({
            "scanner": "bandit",
            "rule": rule,
            "severity": sev,
            "file": file,
            "line": line,
            "message": r.get("issue_text", ""),
            "snippet": snippet,
            "fingerprint": _fingerprint(rule, file, line, snippet),
        })
    return out


def adapt_semgrep(data: Any) -> list[dict]:
    out: list[dict] = []
    if not isinstance(data, dict):
        return out
    for r in data.get("results", []):
        rule = r.get("check_id", "semgrep")
        file = r.get("path", "")
        line = int((r.get("start") or {}).get("line") or 0)
        snippet = (r.get("extra") or {}).get("lines", "")[:300]
        sev = _norm_severity((r.get("extra") or {}).get("severity"))
        out.append({
            "scanner": "semgrep",
            "rule": rule,
            "severity": sev,
            "file": file,
            "line": line,
            "message": (r.get("extra") or {}).get("message", ""),
            "snippet": snippet,
            "fingerprint": _fingerprint(rule, file, line, snippet),
        })
    return out


def adapt_pip_audit(data: Any, source: str) -> list[dict]:
    out: list[dict] = []
    if not isinstance(data, dict):
        return out
    for d in data.get("dependencies", []):
        for vuln in d.get("vulns", []) or []:
            vid = vuln.get("id", "PIP-AUDIT")
            sev = "high"  # pip-audit doesn't always include severity; default high
            out.append({
                "scanner": "pip-audit",
                "rule": vid,
                "severity": sev,
                "file": source,
                "line": 0,
                "message": f"{d.get('name')}=={d.get('version')}: {vuln.get('description','')[:200]}",
                "snippet": f"{d.get('name')}=={d.get('version')}",
                "fingerprint": _fingerprint(vid, source, 0, f"{d.get('name')}{d.get('version')}"),
            })
    return out


def adapt_npm_audit(data: Any) -> list[dict]:
    out: list[dict] = []
    if not isinstance(data, dict):
        return out
    advisories = data.get("vulnerabilities", {}) or {}
    for pkg_name, info in advisories.items():
        sev = _norm_severity(info.get("severity"))
        via = info.get("via", [])
        msg_parts = []
        for v in via if isinstance(via, list) else []:
            if isinstance(v, dict):
                msg_parts.append(v.get("title", ""))
        msg = "; ".join(m for m in msg_parts if m)[:200]
        out.append({
            "scanner": "npm-audit",
            "rule": (via[0].get("url") if (isinstance(via, list) and via and isinstance(via[0], dict)) else "NPM-AUDIT"),
            "severity": sev,
            "file": "kite-dashboard/package-lock.json",
            "line": 0,
            "message": f"{pkg_name}: {msg}",
            "snippet": pkg_name,
            "fingerprint": _fingerprint(pkg_name, "kite-dashboard/package-lock.json", 0, msg),
        })
    return out


def adapt_trufflehog(data: Any) -> list[dict]:
    # trufflehog emits one JSON object per line, not a single document. Caller
    # passes the parsed list of objects when available; otherwise we get None.
    out: list[dict] = []
    if not isinstance(data, list):
        return out
    for item in data:
        rule = item.get("DetectorName", "trufflehog")
        file = (item.get("SourceMetadata") or {}).get("Data", {}).get("Filesystem", {}).get("file", "")
        line = int((item.get("SourceMetadata") or {}).get("Data", {}).get("Filesystem", {}).get("line", 0) or 0)
        snippet = (item.get("Raw") or "")[:200]
        out.append({
            "scanner": "trufflehog",
            "rule": rule,
            "severity": "critical",
            "file": file,
            "line": line,
            "message": f"Verified secret detected ({rule})" if item.get("Verified") else f"Unverified secret ({rule})",
            "snippet": snippet,
            "fingerprint": _fingerprint(rule, file, line, snippet),
        })
    return out


def adapt_trivy(data: Any) -> list[dict]:
    out: list[dict] = []
    if not isinstance(data, dict):
        return out
    for res in data.get("Results", []) or []:
        target = res.get("Target", "")
        for v in res.get("Vulnerabilities", []) or []:
            vid = v.get("VulnerabilityID", "TRIVY")
            out.append({
                "scanner": "trivy",
                "rule": vid,
                "severity": _norm_severity(v.get("Severity")),
                "file": target,
                "line": 0,
                "message": f"{v.get('PkgName')}=={v.get('InstalledVersion')}: {v.get('Title','')[:200]}",
                "snippet": f"{v.get('PkgName')}=={v.get('InstalledVersion')}",
                "fingerprint": _fingerprint(vid, target, 0, f"{v.get('PkgName')}{v.get('InstalledVersion')}"),
            })
        for m in res.get("Misconfigurations", []) or []:
            mid = m.get("ID", "TRIVY-MISC")
            out.append({
                "scanner": "trivy",
                "rule": mid,
                "severity": _norm_severity(m.get("Severity")),
                "file": target,
                "line": int(((m.get("CauseMetadata") or {}).get("StartLine")) or 0),
                "message": m.get("Title", "")[:200],
                "snippet": m.get("Description", "")[:300],
                "fingerprint": _fingerprint(mid, target, 0, m.get("Description", "")),
            })
    return out


def _load_trufflehog(path: Path) -> list[dict]:
    """trufflehog emits NDJSON (one object per line)."""
    items: list[dict] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        pass
    return items


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #

def collect(input_dir: Path) -> list[dict]:
    findings: list[dict] = []

    # gitleaks
    findings += adapt_gitleaks(_load_json(input_dir / "gitleaks.json"))

    # ruff
    findings += adapt_ruff(_load_json(input_dir / "ruff.json"))

    # bandit
    findings += adapt_bandit(_load_json(input_dir / "bandit.json"))

    # semgrep
    findings += adapt_semgrep(_load_json(input_dir / "semgrep.json"))

    # pip-audit (root + kite-api)
    findings += adapt_pip_audit(_load_json(input_dir / "pip-audit.json"), "requirements.txt")
    findings += adapt_pip_audit(_load_json(input_dir / "pip-audit-kite-api.json"), "kite-api/requirements.txt")

    # npm audit
    findings += adapt_npm_audit(_load_json(input_dir / "npm-audit.json"))

    # trufflehog (NDJSON)
    findings += adapt_trufflehog(_load_trufflehog(input_dir / "trufflehog.json"))

    # trivy
    findings += adapt_trivy(_load_json(input_dir / "trivy.json"))

    return findings


def load_suppressions(path: Path) -> set[str]:
    if not path or not path.exists() or yaml is None:
        return set()
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    today = date.today().isoformat()
    fingerprints: set[str] = set()
    for s in (data.get("suppressions") or []):
        fp = s.get("fingerprint")
        if not fp:
            continue
        expires = s.get("expires")
        if expires and str(expires) < today:
            # Expired suppression — still suppresses the finding but flag it elsewhere
            pass
        fingerprints.add(fp)
    return fingerprints


def diff_against_previous(current: Iterable[dict], previous_path: Path | None) -> dict:
    cur_index = {f["fingerprint"]: f for f in current}
    prev_index: dict[str, dict] = {}
    if previous_path and previous_path.exists():
        prev_data = _load_json(previous_path)
        for f in (prev_data.get("findings") if isinstance(prev_data, dict) else []) or []:
            prev_index[f["fingerprint"]] = f

    new = [f for fp, f in cur_index.items() if fp not in prev_index]
    carried = [f for fp, f in cur_index.items() if fp in prev_index]
    resolved = [f for fp, f in prev_index.items() if fp not in cur_index]
    return {"new": new, "carried_over": carried, "resolved": resolved}


def expiring_suppressions(suppressions_path: Path) -> list[dict]:
    if not suppressions_path or not suppressions_path.exists() or yaml is None:
        return []
    with suppressions_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    today = date.today().isoformat()
    return [s for s in (data.get("suppressions") or []) if s.get("expires") and str(s["expires"]) < today]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=Path, help="Directory with raw scanner output")
    ap.add_argument("--output", required=True, type=Path, help="Where to write findings.json")
    ap.add_argument("--previous", type=Path, help="Previous findings.json for diff", default=None)
    ap.add_argument("--suppressions", type=Path, help="suppressions.yml path", default=None)
    args = ap.parse_args()

    all_findings = collect(args.input)
    suppressed = load_suppressions(args.suppressions) if args.suppressions else set()
    findings = [f for f in all_findings if f["fingerprint"] not in suppressed]

    diff = diff_against_previous(findings, args.previous)
    expiring = expiring_suppressions(args.suppressions) if args.suppressions else []

    payload = {
        "findings": findings,
        "suppressed_count": len(all_findings) - len(findings),
        "diff": diff,
        "expiring_suppressions": expiring,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)

    print(f"Wrote {len(findings)} findings to {args.output}")
    print(f"  new: {len(diff['new'])}  carried_over: {len(diff['carried_over'])}  resolved: {len(diff['resolved'])}")
    print(f"  suppressed: {payload['suppressed_count']}")
    print(f"  expiring suppressions: {len(expiring)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
