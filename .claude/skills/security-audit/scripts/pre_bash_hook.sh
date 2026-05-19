#!/usr/bin/env bash
# Claude Code PreToolUse hook for Bash calls.
#
# Defense-in-depth: if Claude is about to invoke `git commit`, run gitleaks
# on the staged content. If gitleaks finds a secret, abort the tool call
# so Claude can't merely bypass the user's local pre-commit hook (e.g. by
# someone disabling pre-commit or passing --no-verify).
#
# This script is invoked by Claude Code with the tool-call JSON on stdin.
# Exit 0 = allow; exit non-zero = block.
#
# Configured in .claude/settings.json under hooks.PreToolUse.

set -uo pipefail

input=$(cat)

# Pull the command field out of the tool-call JSON. Use python3 because it's
# guaranteed available on macOS + Linux and is dependency-light.
cmd=$(printf "%s" "$input" | python3 -c '
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get("tool_input", {}).get("command", ""))
except Exception:
    pass
' 2>/dev/null)

# Only act on git commit invocations. Anything else passes through.
if ! [[ "$cmd" =~ (^|[[:space:];|&])git[[:space:]]+commit ]]; then
    exit 0
fi

# Find project root. CLAUDE_PROJECT_DIR is set by Claude Code; fall back to git.
project_dir="${CLAUDE_PROJECT_DIR:-}"
if [[ -z "$project_dir" || ! -d "$project_dir" ]]; then
    project_dir="$(git rev-parse --show-toplevel 2>/dev/null)"
fi
if [[ -z "$project_dir" || ! -d "$project_dir" ]]; then
    # Can't locate project; don't block, just allow.
    exit 0
fi

# If gitleaks isn't installed, don't block — pre-commit hook is the
# primary defense and the user may not have installed gitleaks yet.
if ! command -v gitleaks >/dev/null 2>&1; then
    exit 0
fi

# Run gitleaks on the staged content. `protect --staged` is the right mode
# for "about to commit".
cd "$project_dir" || exit 0

config_arg=()
if [[ -f tools/security/.gitleaks.toml ]]; then
    config_arg=("--config" "tools/security/.gitleaks.toml")
fi

if ! gitleaks protect --staged "${config_arg[@]}" --no-banner 2>&1; then
    cat >&2 <<'MSG'
gitleaks blocked this commit — staged content matches a secret pattern.

If this is a real secret:
  1. git restore --staged <file>
  2. Remove the secret value from your working copy
  3. Re-stage and re-commit

If this is a false positive:
  1. Add the path / pattern to tools/security/.gitleaks.toml [allowlist]
  2. Document the decision in docs/security/risk-register.md
  3. Re-stage and re-commit
MSG
    exit 2
fi

exit 0
