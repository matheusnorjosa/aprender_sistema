# Git Worktrees

Work on multiple branches simultaneously without stashing or switching.

## When to Use

- Reviewing PR while working on feature
- Hotfix needed while mid-feature
- Testing changes across branches
- Comparing implementations side-by-side

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

# Review, test, comment
cd ../as-review
python manage.py test

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

## Caveats

- Worktrees share the same `.git` database
- Can't have same branch in two worktrees
- Uncommitted changes stay in their worktree
- Some IDEs need configuration for multiple roots

## Integration with Project

For this project (Windows):

```bash
# Example: Review PR while working on type hints
git worktree add "C:/Users/datsu/Documents/as-review" origin/feat/pr-to-review

# Work on review
cd "C:/Users/datsu/Documents/as-review"
cd v2 && make up  # If Docker needed

# Return and cleanup
cd "C:/Users/datsu/Documents/aprender_sistema"
git worktree remove "C:/Users/datsu/Documents/as-review"
```

## Troubleshooting

### Branch already checked out
```bash
# Error: 'branch' is already checked out at '/path'
# Solution: Remove the other worktree first or use different branch
git worktree list  # Find which worktree has it
```

### Locked worktree
```bash
# If worktree was moved/deleted manually
git worktree prune
```
