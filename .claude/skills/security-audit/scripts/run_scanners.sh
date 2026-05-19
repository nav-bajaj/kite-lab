#!/usr/bin/env bash
# Orchestrate every security scanner and capture raw output.
#
# Usage:
#   run_scanners.sh <output-dir>
#
# Writes:
#   <output-dir>/raw/<tool>.{json,txt}
#   <output-dir>/scanner-exit-codes.json
#
# Individual scanner failures do not abort the whole run. Each tool's exit
# code is captured for parse_findings.py to interpret.

set -uo pipefail   # NOTE: not -e on purpose

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <output-dir>" >&2
  exit 64
fi

OUTDIR="$1"
RAW="$OUTDIR/raw"
mkdir -p "$RAW"

# Resolve repo root (this script lives at .claude/skills/security-audit/scripts/)
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$ROOT"

EXIT_CODES_JSON="$OUTDIR/scanner-exit-codes.json"
echo "{" > "$EXIT_CODES_JSON"
SEP=""

log_exit() {
  local tool="$1"; local code="$2"
  echo "${SEP}  \"$tool\": $code" >> "$EXIT_CODES_JSON"
  SEP=","
}

have() { command -v "$1" >/dev/null 2>&1; }

run_or_skip() {
  local tool_bin="$1"; local tool_name="$2"; shift 2
  if ! have "$tool_bin"; then
    echo "[skip] $tool_name — $tool_bin not installed"
    echo '{"status":"skipped","reason":"binary not installed"}' > "$RAW/$tool_name.json"
    log_exit "$tool_name" "-1"
    return
  fi
  echo "[run]  $tool_name"
  "$@"
  local code=$?
  log_exit "$tool_name" "$code"
  echo "       exit=$code"
}

# ---------------------------------------------------------------------------
# gitleaks — secrets in working tree + git history
# ---------------------------------------------------------------------------
run_or_skip gitleaks gitleaks \
  gitleaks detect \
    --config tools/security/.gitleaks.toml \
    --source . \
    --report-format json \
    --report-path "$RAW/gitleaks.json" \
    --no-banner \
    --exit-code 1

# ---------------------------------------------------------------------------
# ruff S-rules — fast Python security checks
# ---------------------------------------------------------------------------
if have ruff; then
  echo "[run]  ruff (S rules)"
  ruff check --select S --output-format json . > "$RAW/ruff.json" 2>/dev/null
  log_exit ruff $?
else
  echo "[skip] ruff — not installed"
  echo '{"status":"skipped"}' > "$RAW/ruff.json"
  log_exit ruff "-1"
fi

# ---------------------------------------------------------------------------
# bandit — deeper Python AST
# ---------------------------------------------------------------------------
if have bandit; then
  echo "[run]  bandit"
  bandit -r . -c tools/security/bandit.yaml -f json -o "$RAW/bandit.json" -q 2>/dev/null
  log_exit bandit $?
else
  echo "[skip] bandit — not installed"
  echo '{"status":"skipped"}' > "$RAW/bandit.json"
  log_exit bandit "-1"
fi

# ---------------------------------------------------------------------------
# semgrep — project-specific + OWASP rules
# ---------------------------------------------------------------------------
if have semgrep; then
  echo "[run]  semgrep"
  semgrep scan \
    --config tools/security/semgrep.yml \
    --config p/owasp-top-ten \
    --config p/python \
    --config p/javascript \
    --exclude design_ideas \
    --exclude experiments \
    --exclude nifty_100_tests \
    --exclude nifty_250_tests \
    --exclude reports \
    --exclude nse500_data \
    --exclude nse500_data_hourly \
    --exclude nse500_data_historical \
    --exclude indices_data \
    --json --quiet \
    --output "$RAW/semgrep.json" 2>/dev/null
  log_exit semgrep $?
else
  echo "[skip] semgrep — not installed"
  echo '{"status":"skipped"}' > "$RAW/semgrep.json"
  log_exit semgrep "-1"
fi

# ---------------------------------------------------------------------------
# pip-audit — Python CVE scan
# ---------------------------------------------------------------------------
if have pip-audit; then
  echo "[run]  pip-audit (root)"
  pip-audit -r requirements.txt --format json > "$RAW/pip-audit.json" 2>/dev/null
  log_exit pip-audit $?

  if [[ -f kite-api/requirements.txt ]]; then
    echo "[run]  pip-audit (kite-api)"
    pip-audit -r kite-api/requirements.txt --format json > "$RAW/pip-audit-kite-api.json" 2>/dev/null
    log_exit pip-audit-kite-api $?
  fi
else
  echo "[skip] pip-audit — not installed"
  echo '{"status":"skipped"}' > "$RAW/pip-audit.json"
  log_exit pip-audit "-1"
fi

# ---------------------------------------------------------------------------
# npm audit — Node CVE scan (in kite-dashboard)
# ---------------------------------------------------------------------------
if [[ -d kite-dashboard && -f kite-dashboard/package-lock.json ]]; then
  echo "[run]  npm audit"
  ( cd kite-dashboard && npm audit --audit-level=low --json ) > "$RAW/npm-audit.json" 2>/dev/null
  log_exit npm-audit $?
else
  echo "[skip] npm audit — kite-dashboard/package-lock.json not found"
  echo '{"status":"skipped"}' > "$RAW/npm-audit.json"
  log_exit npm-audit "-1"
fi

# ---------------------------------------------------------------------------
# trufflehog — cross-check secret scan
# ---------------------------------------------------------------------------
if have trufflehog; then
  echo "[run]  trufflehog"
  trufflehog filesystem . \
    --json \
    --exclude-paths tools/security/trufflehog-exclude.txt \
    > "$RAW/trufflehog.json" 2>/dev/null
  log_exit trufflehog $?
else
  echo "[skip] trufflehog — not installed"
  echo '{"status":"skipped"}' > "$RAW/trufflehog.json"
  log_exit trufflehog "-1"
fi

# ---------------------------------------------------------------------------
# trivy — filesystem CVE scan + Dockerfile checks
# ---------------------------------------------------------------------------
if have trivy; then
  echo "[run]  trivy fs"
  trivy fs \
    --scanners vuln,misconfig,secret \
    --format json \
    --output "$RAW/trivy.json" \
    --skip-dirs node_modules,.venv,.next,nse500_data,nse500_data_hourly,nse500_data_historical,indices_data,reports,kite-api/venv,kite-api/.venv,kite-dashboard/node_modules,kite-dashboard/.next,design_ideas,experiments \
    --quiet \
    . 2>/dev/null
  log_exit trivy $?
else
  echo "[skip] trivy — not installed"
  echo '{"status":"skipped"}' > "$RAW/trivy.json"
  log_exit trivy "-1"
fi

# ---------------------------------------------------------------------------
echo "" >> "$EXIT_CODES_JSON"
echo "}" >> "$EXIT_CODES_JSON"

echo ""
echo "All scanners complete. Output: $RAW"
echo "Exit codes: $EXIT_CODES_JSON"
