#!/usr/bin/env bash
# SessionStart hook: surface course files still pending course-reviewer
# review so unfinished review cycles survive across sessions.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LEDGER="$ROOT/tasks/course_development/.review_ledger"

[ -s "$LEDGER" ] || exit 0

files="$(sort -u "$LEDGER")"
jq -n --arg files "$files" '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:("[course review ledger] Course content edited in earlier sessions is still pending course-reviewer review:\n" + $files + "\nPer the course-voice authoring loop, run the course-reviewer subagent on these before their module is closed, then clear passing files with tools/course/review_ledger_clear.sh.")}}'
