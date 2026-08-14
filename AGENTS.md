# Project Agent Instructions

This file is the shared VoidLabs baseline. Keep project-specific commands and risks
in the repository's own additions rather than expanding this template indefinitely.

## Safe, Proportional Work

- Inspect branch, worktree, and dirty-file state before editing. Preserve unrelated
  changes, stashes, branches, and worktrees.
- Prefer narrow, reversible changes. Resolve exact targets before destructive
  operations and obtain approval when the user has not already authorized them.
- Use the smallest relevant skill and verification set. Routine changes do not need
  an umbrella implementation workflow or multi-persona review.
- Expand review for public ingress, authentication, secrets, migrations, destructive
  data work, novel infrastructure, or broad shared-system impact.
- Use subagents only when independent work can proceed in parallel. Assign distinct
  ownership and keep the parent responsible for integration.

## Git and Plain Worktrees

Use a feature branch for substantial changes. Use plain Git worktrees when isolation
or explicitly requested parallel agents make them useful:

```bash
git fetch origin
git worktree add -b codex/<slug> .worktrees/<slug> origin/main
git worktree list
```

Do not create a worktree for a trivial edit. Before cleanup, verify the worktree is
clean and its commits are merged or otherwise preserved:

```bash
git -C .worktrees/<slug> status --short
git merge-base --is-ancestor <feature-head> origin/main
git worktree remove .worktrees/<slug>
git branch -d codex/<slug>
```

Never remove another task's worktree. Delete remote branches only after merge and
after branch-based deployments no longer track them.

## Development Environment

- Development runs in devcontainers on `devbox.voidlabs.local`; "local" means the
  container, not the Mac.
- Code is bind-mounted under `/srv/fast/code/`.
- Shared scripts and templates live in `/srv/fast/code/voidlabs-devtools`.
- SSH agent forwarding is available. Mutagen may briefly delay file visibility.

Changes to shared bootstrap behavior belong in `voidlabs-devtools`, not only in a
generated project copy.

## Tooling

- Use `rg`/`rg --files` for search.
- Use `uv` with a project-local `.venv` for Python dependencies; never install them
  globally for a repository task.
- Keep secrets out of commits and output. Use Phase-backed runtime injection.
- Use the official Dokploy CLI for Dokploy operations and filter JSON output to the
  safe fields the task needs.

## Verification

Run checks that match the changed surface. Start with `git diff --check`, then add
the relevant formatter, linter, unit test, build, syntax check, or live smoke test.
Configuration and infrastructure changes should verify the real runtime path, not
only static files.

## Issue Tracking

Use `tk` when work or follow-up needs persistent tracking. Do not create Markdown
TODO lists or another tracking system. Trivial one-turn edits with no follow-up do
not need a ticket merely for ceremony.

```bash
tk ready
tk create "Title" -d "Context and acceptance criteria" -t task -p 2
tk start <id>
tk add-note <id> "Progress or blocker"
tk close <id>
```

Include the ticket ID in commit messages when practical.

## Completion

- Review the final diff and commit only task-owned files.
- When the user asks to finish or ship, push the task branch and verify its upstream.
- Merge and clean up branches/worktrees only when requested.
- Do not clear stashes or sweep unrelated files into a commit.
- Report completed work, verification, and genuine remaining operator actions.
