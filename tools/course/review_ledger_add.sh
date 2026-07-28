#!/usr/bin/env bash
# PostToolUse hook (Write|Edit): track learner-facing course files pending
# course-reviewer review. Adds the edited file to the pending-review ledger
# and, on first add, reminds Claude to run the course-reviewer subagent
# before the module is closed. See .claude/skills/course-voice/SKILL.md
# ("The authoring loop") and RUBRIC.md.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LEDGER="$ROOT/tasks/course_development/.review_ledger"

f="$(jq -r '.tool_input.file_path // empty')"
[ -n "$f" ] || exit 0

case "$f" in
  */REVIEW.md) exit 0 ;;
esac
case "$f" in
  "$ROOT"/tasks/course_development/modules/*.md) ;;
  "$ROOT"/tasks/course_development/modules/*.html) ;;
  "$ROOT"/tasks/course_development/CURRICULUM.md) ;;
  *) exit 0 ;;
esac

rel="${f#"$ROOT"/}"
touch "$LEDGER"
if ! grep -qxF "$rel" "$LEDGER"; then
  printf '%s\n' "$rel" >> "$LEDGER"
  jq -n --arg f "$rel" '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:("[course review ledger] " + $f + " was just edited and is now pending review. Before its module is declared done, run the course-reviewer subagent on it (course-voice authoring loop), apply the verdict, then clear it with tools/course/review_ledger_clear.sh once it passes. Batch further edits freely first; this reminder fires once per file per review cycle.")}}'
fi
