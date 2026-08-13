#!/usr/bin/env bash
# Stop-hook safety net for Windows <-> Mac sync.
#
# Contract, deliberately narrow:
#   - PUSHES commits that are already made but not yet on origin. Safe and silent.
#   - WARNS about an uncommitted tree; never commits it. Real commits with real
#     messages are Claude's job at meaningful checkpoints (see CLAUDE.md), so
#     this stays out of the history.
#   - WARNS when KiCad lock files exist, because the GUI can be holding unsaved
#     edits that are not on disk and therefore cannot be in any commit. This
#     project already lost a session-30 R12 edit exactly that way.
#
# Always exits 0. A sync helper must never be the reason a turn fails.

set -uo pipefail

# Repo root, derived from this script's own location so it works from any cwd
# and on either machine. .claude/hooks/ -> ../.. is the root.
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)" || exit 0
cd "$root" 2>/dev/null || exit 0

git rev-parse --git-dir >/dev/null 2>&1 || exit 0
git remote get-url origin >/dev/null 2>&1 || exit 0

# Never let a credential prompt hang the turn — fail fast instead.
export GIT_TERMINAL_PROMPT=0
export GCM_INTERACTIVE=never

warn=""
pushed=""

branch="$(git symbolic-ref --quiet --short HEAD 2>/dev/null)" || branch=""
[ -z "$branch" ] && exit 0   # detached HEAD: not our business

# --- push anything already committed but not on the remote --------------------
if git rev-parse --abbrev-ref '@{upstream}' >/dev/null 2>&1; then
  ahead="$(git rev-list --count '@{upstream}..HEAD' 2>/dev/null || echo 0)"
  if [ "${ahead:-0}" -gt 0 ] 2>/dev/null; then
    if err="$(git push --porcelain origin "$branch" 2>&1)"; then
      pushed="pushed $ahead commit(s) to origin/$branch"
    else
      # Most likely the remote moved ahead (edits from the other machine).
      warn="push FAILED — $ahead commit(s) still local only. Run: git pull --rebase && git push"
    fi
  fi
else
  warn="branch '$branch' has no upstream. Run: git push -u origin $branch"
fi

# --- warn on an uncommitted tree (do NOT commit it) --------------------------
dirty="$(git status --porcelain 2>/dev/null | grep -c . || true)"
if [ "${dirty:-0}" -gt 0 ] 2>/dev/null; then
  warn="${warn:+$warn | }$dirty uncommitted file(s) — not on the other machine yet"
fi

# --- warn on KiCad locks: GUI may hold edits that never reached disk ---------
if compgen -G "**/~*.lck" >/dev/null 2>&1 || \
   [ -n "$(find . -name '~*.lck' -not -path './.git/*' -print -quit 2>/dev/null)" ]; then
  warn="${warn:+$warn | }KiCad is OPEN — unsaved GUI edits are not on disk, so they cannot be committed"
fi

# --- report ------------------------------------------------------------------
msg="$pushed"
[ -n "$warn" ] && msg="${msg:+$msg | }⚠ $warn"
[ -z "$msg" ] && exit 0   # nothing to say: stay silent

# Escape for JSON (backslash, then quote, then strip newlines).
msg="${msg//\\/\\\\}"
msg="${msg//\"/\\\"}"
msg="${msg//$'\n'/ }"

printf '{"systemMessage":"git-sync: %s","suppressOutput":true}\n' "$msg"
exit 0
