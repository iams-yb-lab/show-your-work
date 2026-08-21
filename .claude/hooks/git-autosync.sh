#!/usr/bin/env bash
# Stop-hook safety net for Windows <-> Mac sync.
#
# Contract, deliberately narrow:
#   - PUSHES commits that are already made but not yet on origin. Safe and silent.
#   - REFUSES to push the default branch. Every change to this repository arrives
#     as a pull request, admins included, so a session that commits on `main` is
#     told how to turn that into a branch rather than having it pushed for it.
#     There is no bypass: the point of the rule is that it binds the people who
#     could grant themselves one. GitHub cannot enforce this yet (private repo,
#     free org plan -> no rulesets), so this hook is the enforcement.
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

# --- the default branch is never pushed from here -----------------------------
# Read it from the remote rather than assuming; fall back to main.
default="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null)" || default=""
default="${default#origin/}"
[ -z "$default" ] && default="main"

if [ "$branch" = "$default" ]; then
  ahead_d="$(git rev-list --count "origin/$default..HEAD" 2>/dev/null || echo 0)"
  if [ "${ahead_d:-0}" -gt 0 ] 2>/dev/null; then
    warn="$ahead_d commit(s) on '$default' — NOT pushed, this repo is pull-request only. Run: git switch -c <topic> && git push -u origin <topic> && git branch -f $default origin/$default"
  fi
  dirty_d="$(git status --porcelain 2>/dev/null | grep -c . || true)"
  [ "${dirty_d:-0}" -gt 0 ] 2>/dev/null && \
    warn="${warn:+$warn | }$dirty_d uncommitted file(s) — commit them on a branch, not on $default"
  msg="⚠ $warn"
  msg="${msg//\\/\\\\}"; msg="${msg//\"/\\\"}"; msg="${msg//$'\n'/ }"
  [ -n "$warn" ] && printf '{"systemMessage":"git-sync: %s","suppressOutput":true}\n' "$msg"
  exit 0
fi

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
