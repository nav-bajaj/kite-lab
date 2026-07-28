#!/usr/bin/env bash
# Clear files from the course pending-review ledger after they pass the
# course-reviewer. Usage:
#   tools/course/review_ledger_clear.sh <repo-relative-path> [...]
#   tools/course/review_ledger_clear.sh --all
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LEDGER="$ROOT/tasks/course_development/.review_ledger"

[ -f "$LEDGER" ] || { echo "ledger empty"; exit 0; }

if [ "${1:-}" = "--all" ]; then
  : > "$LEDGER"
  echo "ledger cleared"
  exit 0
fi

[ $# -gt 0 ] || { echo "usage: $0 <repo-relative-path>... | --all" >&2; exit 1; }

tmp="$(mktemp)"
cp "$LEDGER" "$tmp"
for rel in "$@"; do
  grep -vxF "$rel" "$tmp" > "$tmp.next" || true
  mv "$tmp.next" "$tmp"
done
mv "$tmp" "$LEDGER"
echo "remaining pending:"
cat "$LEDGER"
