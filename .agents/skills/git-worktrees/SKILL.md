---
name: git-worktrees
description: Work on multiple branches simultaneously without stashing or switching. Use when reviewing a PR while mid-feature, applying a hotfix without losing context, or comparing implementations side-by-side. Covers create/list/remove and AS v2 (Windows) conventions.
---

# Git Worktrees

On Windows, use absolute paths (`C:/...`) for every worktree directory.

## Core Commands

### Create Worktree

```bash
# For existing branch
git worktree add ../project-hotfix hotfix/urgent-bug

# For new branch
git worktree add -b feat/new-feature ../project-feature main
```

### List Worktrees

```bash
git worktree list
```

### Remove Worktree

```bash
git worktree remove ../project-hotfix
# Or force remove
git worktree remove --force ../project-hotfix
```

## Directory Convention

Organize worktrees predictably:

```
aprender_sistema/          # Main worktree (main branch)
aprender_sistema-hotfix/   # Hotfix worktree
aprender_sistema-review/   # PR review worktree
aprender_sistema-feat-X/   # Feature worktree
```

## Common Workflows

### Workflow 1: Emergency Hotfix

```bash
# You're mid-feature on feat/new-ui
git worktree add -b hotfix/critical ../as-hotfix main

# Work in hotfix worktree
cd ../as-hotfix
# Fix, commit, push, PR

# Return to feature
cd ../aprender_sistema

# Cleanup after merge
git worktree remove ../as-hotfix
```

### Workflow 2: PR Review

```bash
# Create worktree for the PR branch
git fetch origin
git worktree add ../as-review origin/feat/their-feature

# Review, test, comment (v2 is Docker-only, CP-01)
cd ../as-review
cd v2 && make up
docker exec aprender_dev-web-1 pytest apps/core/tests/ -v

# Cleanup
cd ../aprender_sistema
git worktree remove ../as-review
```

### Workflow 3: Compare Implementations

```bash
# Create worktrees for two approaches
git worktree add ../as-approach-a feat/approach-a
git worktree add ../as-approach-b feat/approach-b

# Compare side by side
diff ../as-approach-a/src/feature.py ../as-approach-b/src/feature.py
```

## Best Practices

1. **Name clearly**: Include branch purpose in directory name
2. **Clean up**: Remove worktrees after done
3. **Don't nest**: Keep worktrees as siblings, not children
4. **Share nothing**: Each worktree is independent

## Caveats and Troubleshooting

For shared-`.git` gotchas (branch already checked out, locked/stale worktrees, `git worktree prune`), read `reference/caveats-and-troubleshooting.md`.
